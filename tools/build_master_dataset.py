#!/usr/bin/env python3
"""
Builds master IPTV dataset from consolidated epg.db
Exports: channels.parquet, streams.parquet, programs.parquet
"""
from pathlib import Path
import sqlite3
import pandas as pd
import logging
from datetime import datetime
import json

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


def export_parquet(conn: sqlite3.Connection, view: str, filename: str, description: str) -> int:
    """Export SQLite view/table to Parquet with metadata"""
    try:
        df = pd.read_sql(f"SELECT * FROM {view}", conn)
        logger.info(f"{description}: {len(df)} rows")
        
        # Parquet metadata
        out_path = OUT_DIR / filename
        df.to_parquet(
            out_path, 
            index=False,
            compression='snappy',
            engine='pyarrow',
            row_group_size=64*1024*1024  # 64MB row groups
        )
        
        size_mb = out_path.stat().st_size / 1024 / 1024
        logger.info(f"✓ Exported to {out_path} ({size_mb:.2f} MB)")
        return len(df)
    except Exception as e:
        logger.error(f"Failed to export {view}: {e}")
        raise


def export_json_metadata(stats: dict):
    """Write dataset metadata for consumers"""
    meta = {**METADATA, "stats": stats}
    meta_path = OUT_DIR / "metadata.json"
    meta_path.write_text(json.dumps(meta, indent=2))
    logger.info(f"✓ Metadata written to {meta_path}")


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Database not found: {DB_PATH}")
    
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    try:
        stats = {}
        stats["channels"] = export_parquet(
            conn, "channels_master", "channels.parquet", "Channels"
        )
        stats["streams"] = export_parquet(
            conn, "streams_master", "streams.parquet", "Streams"
        )
        stats["programs"] = export_parquet(
            conn, "programs_master", "programs.parquet", "Programs (EPG)"
        )
        
        export_json_metadata(stats)
        
        logger.info(f"\n{'='*60}")
        logger.info("Master dataset build complete!")
        logger.info(f"Location: {OUT_DIR}")
        logger.info(f"Total channels: {stats['channels']:,}")
        logger.info(f"Total streams: {stats['streams']:,}")
        logger.info(f"EPG programs: {stats['programs']:,}")
        logger.info(f"{'='*60}\n")
        
    finally:
        conn.close()


if __name__ == "__main__":
    main()
