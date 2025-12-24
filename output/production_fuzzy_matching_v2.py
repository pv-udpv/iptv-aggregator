#!/usr/bin/env python3
"""
Production Fuzzy Matching with Rapid Fuzz + Taxonomy Normalization

Features:
- rapidfuzz for taxonomy parsing and matching
- Channel taxonomy extraction (resolution, country, language, variant)
- Parent/root hierarchy building
- SQLite persistence with taxonomy columns
- Works with IPTV-ORG channels
"""

import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional

try:
    from rapidfuzz import fuzz
except ImportError:
    print("ERROR: rapidfuzz not installed")
    print("Run: uv pip install rapidfuzz")
    sys.exit(1)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from taxonomy.channel_parser import parse_channel_name
from taxonomy.hierarchy import build_hierarchy


# ============================================================================
# Configuration
# ============================================================================

OUTPUT_DIR = Path("output")
DB_PATH = OUTPUT_DIR / "iptv_full.db"
RESULT_PATH = OUTPUT_DIR / "matching_results_v2.json"


# ============================================================================
# Channel Loading and Enrichment
# ============================================================================

def load_and_enrich_channels() -> List[dict]:
    """Load channels from SQLite and enrich with taxonomy."""
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found")
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        cursor.execute("SELECT id, name FROM channels ORDER BY id")
        rows = cursor.fetchall()
        channels = [dict(row) for row in rows]
    except sqlite3.OperationalError as e:
        print(f"ERROR querying channels: {e}")
        conn.close()
        return []

    conn.close()

    print(f"✓ Loaded {len(channels)} channels")

    # Enrich with taxonomy parsing
    for ch in channels:
        parsed = parse_channel_name(ch["name"])
        ch["normalized_name"] = parsed.normalized_name
        ch["resolution"] = parsed.resolution
        ch["country_code"] = parsed.country_code
        ch["lang_code"] = parsed.lang_code
        ch["variant"] = parsed.variant
        ch["is_root"] = 0
        ch["is_variant"] = 0
        ch["parent_id"] = None
        ch["root_id"] = None
        ch["stream_count"] = 0

    return channels


# ============================================================================
# Database Update
# ============================================================================

def persist_taxonomy_to_db(channels: List[dict]) -> None:
    """Update database with taxonomy and hierarchy data."""
    if not DB_PATH.exists():
        print("ERROR: Database not found")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    print("Updating database with taxonomy...")

    # Update each channel
    for i, ch in enumerate(channels):
        if (i + 1) % max(1, len(channels) // 10) == 0:
            print(f"  Progress: {i + 1}/{len(channels)}")

        cursor.execute("""
            UPDATE channels SET
                normalized_name = ?,
                resolution = ?,
                country_code = ?,
                lang_code = ?,
                variant = ?,
                parent_id = ?,
                root_id = ?,
                is_root = ?,
                is_variant = ?
            WHERE id = ?
        """, (
            ch["normalized_name"],
            ch["resolution"],
            ch["country_code"],
            ch["lang_code"],
            ch["variant"],
            ch["parent_id"],
            ch["root_id"],
            ch["is_root"],
            ch["is_variant"],
            ch["id"],
        ))

    conn.commit()
    conn.close()

    print(f"✓ Updated {len(channels)} channels in database")


# ============================================================================
# Statistics
# ============================================================================

def calculate_stats(channels: List[dict]) -> dict:
    """Calculate taxonomy statistics."""
    stats = {
        "total_channels": len(channels),
        "total_roots": sum(1 for ch in channels if ch.get("is_root", 0)),
        "total_variants": sum(1 for ch in channels if ch.get("is_variant", 0)),
        "by_resolution": {},
        "by_country": {},
        "by_variant": {},
        "by_language": {},
    }

    # Resolution breakdown
    for ch in channels:
        res = ch.get("resolution") or "unknown"
        stats["by_resolution"][res] = stats["by_resolution"].get(res, 0) + 1

    # Country breakdown
    for ch in channels:
        country = ch.get("country_code") or "unknown"
        stats["by_country"][country] = stats["by_country"].get(country, 0) + 1

    # Variant breakdown
    for ch in channels:
        variant = ch.get("variant") or "none"
        stats["by_variant"][variant] = stats["by_variant"].get(variant, 0) + 1

    # Language breakdown
    for ch in channels:
        lang = ch.get("lang_code") or "unknown"
        stats["by_language"][lang] = stats["by_language"].get(lang, 0) + 1

    # Sort by count
    stats["by_resolution"] = dict(
        sorted(stats["by_resolution"].items(), key=lambda x: x[1], reverse=True)
    )
    stats["by_country"] = dict(
        sorted(stats["by_country"].items(), key=lambda x: x[1], reverse=True)[:30]
    )
    stats["by_variant"] = dict(
        sorted(stats["by_variant"].items(), key=lambda x: x[1], reverse=True)
    )
    stats["by_language"] = dict(
        sorted(stats["by_language"].items(), key=lambda x: x[1], reverse=True)[:20]
    )

    return stats


# ============================================================================
# Main Pipeline
# ============================================================================

def main() -> None:
    print("=" * 70)
    print("PRODUCTION FUZZY MATCHING v2 (with rapidfuzz + taxonomy)")
    print("=" * 70)
    print()

    start_time = time.time()

    # [1] Load and enrich channels
    print("[1/4] Loading and enriching channels with taxonomy...")
    print()

    channels = load_and_enrich_channels()
    if not channels:
        print("ERROR: No channels to process")
        return

    print()

    # [2] Build hierarchy
    print("[2/4] Building hierarchy...")
    print()

    build_hierarchy(channels)

    roots = sum(1 for ch in channels if ch.get("is_root", 0))
    variants = sum(1 for ch in channels if ch.get("is_variant", 0))

    print(f"  Total: {len(channels)}")
    print(f"  Roots: {roots}")
    print(f"  Variants: {variants}")
    print()

    # [3] Show examples
    print("[3/4] Sample parsing results:")
    print()

    for ch in channels[:5]:
        print(
            f"  {ch['name']:40} → "
            f"{ch['normalized_name']:20} "
            f"[res={ch['resolution'] or '-':4}] "
            f"[country={ch['country_code'] or '-':2}] "
            f"[var={ch['variant'] or '-':6}]"
        )

    print()

    # [4] Persist to database
    print("[4/4] Persisting to database...")
    print()

    persist_taxonomy_to_db(channels)
    print()

    # Calculate stats
    stats = calculate_stats(channels)

    elapsed = time.time() - start_time

    # Save results
    result = {
        "timestamp": time.time(),
        "processing_time_sec": round(elapsed, 1),
        "stats": stats,
        "samples": [
            {
                "id": ch["id"],
                "name": ch["name"],
                "normalized_name": ch["normalized_name"],
                "resolution": ch["resolution"],
                "country_code": ch["country_code"],
                "lang_code": ch["lang_code"],
                "variant": ch["variant"],
                "is_root": ch["is_root"],
                "root_id": ch["root_id"],
            }
            for ch in channels[:100]
        ],
    }

    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✓ Results saved: {RESULT_PATH}")
    print()

    # === Report ===
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    print(f"Total channels:   {stats['total_channels']}")
    print(f"Root channels:    {stats['total_roots']}")
    print(f"Variant channels: {stats['total_variants']}")
    print()

    print("Resolution distribution:")
    for res, count in list(stats["by_resolution"].items())[:10]:
        pct = round(count / len(channels) * 100)
        print(f"  {res:10}: {count:5} ({pct}%)")

    print()

    print("Country distribution (top 10):")
    for country, count in list(stats["by_country"].items())[:10]:
        pct = round(count / len(channels) * 100)
        print(f"  {country:3}: {count:5} ({pct}%)")

    print()

    if stats["by_variant"]["none"] < len(channels):
        print("Variant distribution:")
        for variant, count in list(stats["by_variant"].items())[:10]:
            if variant != "none":
                pct = round(count / len(channels) * 100)
                print(f"  {variant:15}: {count:5} ({pct}%)")

    print()
    print(f"Processing time: {elapsed:.1f} sec")
    print()

    print("✅ Done!")


if __name__ == "__main__":
    main()
