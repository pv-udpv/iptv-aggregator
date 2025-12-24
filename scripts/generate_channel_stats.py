#!/usr/bin/env python3
"""
Generate channel statistics with taxonomy breakdown.
Works with current channels table schema.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import defaultdict

DB_PATH = Path("output/iptv_full.db")


def generate_stats() -> None:
    print("=" * 70)
    print("📊 Generating channel statistics with taxonomy")
    print("=" * 70)
    print()

    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    stats = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "channels": {},
        "taxonomy": {},
        "hierarchy": {},
        "matching": {},
        "countries": {},
    }

    # === General channel stats ===
    print("Collecting general stats...")
    
    cursor.execute("SELECT COUNT(*) FROM channels")
    total_channels = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM channels WHERE url IS NOT NULL")
    channels_with_urls = cursor.fetchone()[0]

    stats["channels"] = {
        "total": total_channels,
        "with_urls": channels_with_urls,
        "without_urls": total_channels - channels_with_urls,
    }

    # === Taxonomy stats ===
    print("Collecting taxonomy stats...")

    cursor.execute("""
        SELECT 
            resolution,
            COUNT(*) as count
        FROM channels
        WHERE resolution IS NOT NULL
        GROUP BY resolution
        ORDER BY count DESC
    """)
    stats["taxonomy"]["by_resolution"] = {
        row[0]: row[1] for row in cursor.fetchall()
    }

    cursor.execute("""
        SELECT 
            country_code,
            COUNT(*) as count
        FROM channels
        WHERE country_code IS NOT NULL
        GROUP BY country_code
        ORDER BY count DESC
        LIMIT 30
    """)
    stats["taxonomy"]["by_country"] = {
        row[0]: row[1] for row in cursor.fetchall()
    }

    cursor.execute("""
        SELECT 
            variant,
            COUNT(*) as count
        FROM channels
        WHERE variant IS NOT NULL
        GROUP BY variant
        ORDER BY count DESC
    """)
    stats["taxonomy"]["by_variant"] = {
        row[0]: row[1] for row in cursor.fetchall()
    }

    cursor.execute("""
        SELECT 
            lang_code,
            COUNT(*) as count
        FROM channels
        WHERE lang_code IS NOT NULL
        GROUP BY lang_code
        ORDER BY count DESC
        LIMIT 20
    """)
    stats["taxonomy"]["by_language"] = {
        row[0]: row[1] for row in cursor.fetchall()
    }

    # === Hierarchy stats ===
    print("Collecting hierarchy stats...")

    cursor.execute("""
        SELECT COUNT(*) FROM channels WHERE is_root = 1
    """)
    total_roots = cursor.fetchone()[0]
    stats["hierarchy"]["total_roots"] = total_roots

    cursor.execute("""
        SELECT COUNT(*) FROM channels WHERE is_variant = 1
    """)
    total_variants = cursor.fetchone()[0]
    stats["hierarchy"]["total_variants"] = total_variants

    # Top roots by variant count
    cursor.execute("""
        SELECT 
            root_id,
            COUNT(*) as count
        FROM channels
        WHERE is_variant = 1 AND root_id IS NOT NULL
        GROUP BY root_id
        ORDER BY count DESC
        LIMIT 30
    """)
    
    roots_with_variants = {}
    for root_id, variant_count in cursor.fetchall():
        cursor.execute(
            "SELECT name FROM channels WHERE id = ?",
            (root_id,),
        )
        row = cursor.fetchone()
        if row:
            roots_with_variants[str(root_id)] = {
                "name": row[0],
                "variant_count": variant_count,
            }

    stats["hierarchy"]["roots_with_variants"] = roots_with_variants

    # === Group distribution ===
    print("Collecting group distribution...")
    
    cursor.execute("""
        SELECT 
            group_title,
            COUNT(*) as count
        FROM channels
        WHERE group_title IS NOT NULL AND group_title != ''
        GROUP BY group_title
        ORDER BY count DESC
        LIMIT 30
    """)
    
    stats["groups"] = {row[0]: row[1] for row in cursor.fetchall()}

    conn.close()

    # === Save ===
    print()
    print("Saving stats...")

    stats_dir = Path("stats")
    stats_dir.mkdir(exist_ok=True)

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    stats_path = stats_dir / f"channels_{timestamp}.json"

    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    # Also save as latest
    latest_path = stats_dir / "channels_latest.json"
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"✅ {stats_path}")
    print(f"✅ {latest_path}")
    print()

    # === Report ===
    print("=" * 70)
    print("STATISTICS SUMMARY")
    print("=" * 70)
    print()

    print(f"Total channels:          {stats['channels']['total']:,}")
    print(f"With URLs:               {stats['channels']['with_urls']:,}")
    print()

    print("Taxonomy:")
    print(f"  By resolution:         {len(stats['taxonomy']['by_resolution'])} types")
    for res, count in stats['taxonomy']['by_resolution'].items():
        print(f"    {res:5}: {count:6,}")

    print(f"  By country:            {len(stats['taxonomy']['by_country'])} countries (top 10)")
    for country, count in list(stats['taxonomy']['by_country'].items())[:10]:
        print(f"    {country}: {count:6,}")

    if stats['taxonomy']['by_variant']:
        print(f"  By variant:            {len(stats['taxonomy']['by_variant'])} types")
        for variant, count in stats['taxonomy']['by_variant'].items():
            print(f"    {variant:15}: {count:6,}")

    if stats['taxonomy']['by_language']:
        print(f"  By language:           {len(stats['taxonomy']['by_language'])} languages")
        for lang, count in stats['taxonomy']['by_language'].items():
            print(f"    {lang:5}: {count:6,}")

    print()
    print("Hierarchy:")
    print(f"  Root channels:         {stats['hierarchy']['total_roots']:,}")
    print(f"  Variant channels:      {stats['hierarchy']['total_variants']:,}")

    if stats['hierarchy']['roots_with_variants']:
        print(f"  Roots with variants:   {len(stats['hierarchy']['roots_with_variants'])}")
        print("    Top 5:")
        for root_id, info in list(stats['hierarchy']['roots_with_variants'].items())[:5]:
            print(f"      {info['name']:30} ({info['variant_count']} variants)")

    print()
    
    if stats['groups']:
        print(f"Top groups ({len(stats['groups'])})")
        for group, count in list(stats['groups'].items())[:10]:
            print(f"  {group[:40]:40}: {count:6,}")

    print()
    print("✅ Done!")


if __name__ == "__main__":
    generate_stats()
