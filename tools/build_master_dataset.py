#!/usr/bin/env python3
"""
Build master IPTV dataset from normalized channels + variants.

Outputs:
- channels.parquet: Base channels with primary variant info
- channel_variants.parquet: All variants with metadata
- streams.parquet: Stream URLs with health metrics
- programs.parquet: EPG data (14-day window)
- metadata.json: Dataset statistics
"""

import sys
import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict
import pandas as pd
import logging

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))
from channel_normalizer import ChannelNormalizer

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "output" / "epg.db"
OUT_DIR = ROOT / "data" / "master-dataset"

METADATA = {
    "version": "1.0.0",
    "built_at": datetime.utcnow().isoformat() + "Z",
    "sources": ["iptv-org/database", "iptv-org/epg", "iptvportal"]
}


def run_migrations(conn: sqlite3.Connection):
    """Run SQL migrations to create variant tables"""
    migration_file = ROOT / "migrations" / "001_create_channel_variants.sql"
    
    if not migration_file.exists():
        logger.warning(f"Migration file not found: {migration_file}")
        return
    
    logger.info("Running database migrations...")
    
    with open(migration_file) as f:
        migration_sql = f.read()
    
    # Execute migration (split by ; and filter empty)
    for statement in migration_sql.split(';'):
        statement = statement.strip()
        if statement and not statement.startswith('--'):
            try:
                conn.execute(statement)
            except sqlite3.OperationalError as e:
                # Ignore "table already exists" errors
                if "already exists" not in str(e):
                    raise
    
    conn.commit()
    logger.info("✓ Migrations complete")


def build_base_channels_and_variants(conn: sqlite3.Connection):
    """
    Populate channels_base and channel_variants tables from raw data.
    """
    logger.info("Building base channels and variants...")
    
    normalizer = ChannelNormalizer()
    
    # Load raw channels from both sources
    try:
        iptv_channels = pd.read_sql("SELECT * FROM iptv_channels", conn)
    except:
        # Fallback: load from CSV
        csv_path = ROOT / "output" / "raw" / "channels.csv"
        if csv_path.exists():
            iptv_channels = pd.read_csv(csv_path)
        else:
            logger.error("No iptv_channels table or CSV found")
            return
    
    try:
        portal_channels = pd.read_sql("SELECT * FROM portal_channels", conn)
    except:
        csv_path = ROOT / "output" / "raw" / "portal_channels.csv"
        if csv_path.exists():
            portal_channels = pd.read_csv(csv_path)
        else:
            logger.warning("No portal_channels found, continuing with iptv-org only")
            portal_channels = pd.DataFrame(columns=['id', 'name'])
    
    # Normalize all channels
    all_normalized = []
    
    logger.info(f"Normalizing {len(iptv_channels)} iptv-org channels...")
    for _, row in iptv_channels.iterrows():
        norm = normalizer.normalize(str(row['name']))
        if norm.canonical_id:  # Skip empty
            all_normalized.append({
                'source': 'iptv-org',
                'source_id': str(row['id']),
                'normalized': norm
            })
    
    logger.info(f"Normalizing {len(portal_channels)} portal channels...")
    for _, row in portal_channels.iterrows():
        norm = normalizer.normalize(str(row['name']))
        if norm.canonical_id:
            all_normalized.append({
                'source': 'iptvportal',
                'source_id': str(row['id']),
                'normalized': norm
            })
    
    # Group by canonical_id
    logger.info("Grouping variants by canonical ID...")
    groups = normalizer.group_variants([
        item['normalized'] for item in all_normalized
    ])
    
    logger.info(f"Found {len(groups)} unique base channels")
    
    # Insert base channels + variants
    inserted_base = 0
    inserted_variants = 0
    
    for canonical_id, variants in groups.items():
        primary = normalizer.select_primary_variant(variants)
        
        # Insert base channel
        conn.execute("""
            INSERT OR REPLACE INTO channels_base 
            (canonical_id, base_name, total_variants, has_hd, has_uhd)
            VALUES (?, ?, ?, ?, ?)
        """, (
            canonical_id,
            primary.base_name,
            len(variants),
            any(v.variants.get('quality') in ['hd', 'fhd'] for v in variants),
            any(v.variants.get('quality') in ['uhd', '4k', '8k'] for v in variants)
        ))
        inserted_base += 1
        
        # Insert all variants for this base channel
        for item in all_normalized:
            if item['normalized'].canonical_id == canonical_id:
                norm = item['normalized']
                
                conn.execute("""
                    INSERT OR REPLACE INTO channel_variants
                    (canonical_id, source, source_id, original_name, 
                     quality, region, language, feed, technical,
                     is_primary, normalization_confidence)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    canonical_id,
                    item['source'],
                    item['source_id'],
                    norm.original_name,
                    norm.variants.get('quality'),
                    norm.variants.get('region'),
                    norm.variants.get('language'),
                    norm.variants.get('feed'),
                    norm.variants.get('technical'),
                    1 if norm == primary else 0,
                    norm.confidence
                ))
                inserted_variants += 1
    
    conn.commit()
    
    logger.info(f"✓ Inserted {inserted_base} base channels")
    logger.info(f"✓ Inserted {inserted_variants} variants")


def export_parquet(conn: sqlite3.Connection, view: str, filename: str, description: str) -> int:
    """Export SQLite view/table to Parquet"""
    try:
        df = pd.read_sql(f"SELECT * FROM {view}", conn)
        logger.info(f"{description}: {len(df)} rows")
        
        out_path = OUT_DIR / filename
        df.to_parquet(
            out_path, 
            index=False,
            compression='snappy',
            engine='pyarrow'
        )
        
        size_mb = out_path.stat().st_size / 1024 / 1024
        logger.info(f"✓ Exported to {out_path} ({size_mb:.2f} MB)")
        return len(df)
        
    except Exception as e:
        logger.error(f"Failed to export {view}: {e}")
        return 0


def export_json_metadata(stats: Dict[str, int]):
    """Write dataset metadata"""
    meta = {**METADATA, "stats": stats}
    meta_path = OUT_DIR / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    logger.info(f"✓ Metadata written to {meta_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Build master IPTV dataset with channel variants"
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=DB_PATH,
        help="Path to SQLite database"
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=OUT_DIR,
        help="Output directory for Parquet files"
    )
    
    args = parser.parse_args()
    
    global DB_PATH, OUT_DIR
    DB_PATH = args.db
    OUT_DIR = args.output
    
    if not DB_PATH.exists():
        logger.error(f"Database not found: {DB_PATH}")
        return 1
    
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Step 1: Run migrations
        run_migrations(conn)
        
        # Step 2: Build base channels + variants
        build_base_channels_and_variants(conn)
        
        # Step 3: Export datasets
        stats = {}
        
        stats["channels"] = export_parquet(
            conn, "channels_master", "channels.parquet", "Base Channels"
        )
        
        stats["variants"] = export_parquet(
            conn, "channel_variants_full", "channel_variants.parquet", "Channel Variants"
        )
        
        # Optional: streams and programs (if tables exist)
        try:
            stats["streams"] = export_parquet(
                conn, "streams_master", "streams.parquet", "Streams"
            )
        except:
            logger.warning("streams_master view not found, skipping")
            stats["streams"] = 0
        
        try:
            stats["programs"] = export_parquet(
                conn, "programs_master", "programs.parquet", "Programs (EPG)"
            )
        except:
            logger.warning("programs_master view not found, skipping")
            stats["programs"] = 0
        
        # Step 4: Write metadata
        export_json_metadata(stats)
        
        # Summary
        print("\n" + "="*60)
        print("Master Dataset Build Complete!")
        print("="*60)
        print(f"Location:        {OUT_DIR}")
        print(f"Base channels:   {stats['channels']:,}")
        print(f"Total variants:  {stats['variants']:,}")
        print(f"Streams:         {stats.get('streams', 0):,}")
        print(f"EPG programs:    {stats.get('programs', 0):,}")
        print("="*60 + "\n")
        
        return 0
        
    except Exception as e:
        logger.error(f"Build failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
        
    finally:
        conn.close()


if __name__ == "__main__":
    sys.exit(main())
