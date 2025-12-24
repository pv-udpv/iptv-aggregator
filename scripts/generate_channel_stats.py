#!/usr/bin/env python3
"""
Generate channel statistics with taxonomy breakdown.
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
    cursor.execute("SELECT COUNT(*) FROM channels")
    total_channels = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(DISTINCT c.id)
        FROM channels c
        JOIN streams s ON c.id = s.channel_id
        WHERE s.url IS NOT NULL
    """)
    channels_with_streams = cursor.fetchone()[0]

    stats["channels"] = {
        "total": total_channels,
        "with_streams": channels_with_streams,
        "without_streams": total_channels - channels_with_streams,
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
    stats["hierarchy"]["total_roots"] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT COUNT(*) FROM channels WHERE is_variant = 1
    """)
    stats["hierarchy"]["total_variants"] = cursor.fetchone()[0]

    cursor.execute("""
        SELECT 
            root_id,
            COUNT(*) as count
        FROM channels
        WHERE is_variant = 1
        GROUP BY root_id
        ORDER BY count DESC
        LIMIT 30
    """)
    variant_distribution = cursor.fetchall()

    cursor.execute("""
        SELECT id, name, COUNT(s.id) as stream_count
        FROM channels c
        LEFT JOIN streams s ON c.id = s.channel_id
        WHERE c.is_root = 1
        GROUP BY c.id
        ORDER BY stream_count DESC
        LIMIT 30
    """)

    roots_with_variants = {}
    for root_id, variant_count in variant_distribution:
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

    # === Matching stats ===
    print("Collecting matching stats...")

    try:
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(CASE WHEN confidence >= 0.9 THEN 1 END) as high_conf,
                COUNT(CASE WHEN confidence BETWEEN 0.7 AND 0.89 THEN 1 END) as medium_conf,
                COUNT(CASE WHEN confidence < 0.7 THEN 1 END) as low_conf,
                AVG(confidence) as avg_conf
            FROM matched_channels
        """)

        row = cursor.fetchone()
        if row and row[0] > 0:
            stats["matching"] = {
                "total_matched": row[0],
                "high_confidence": row[1],
                "medium_confidence": row[2],
                "low_confidence": row[3],
                "average_confidence": round(row[4], 3),
                "match_rate": round(
                    row[0] / channels_with_streams * 100, 1
                ) if channels_with_streams > 0 else 0,
            }
    except sqlite3.OperationalError:
        pass

    # === Top countries ===
    print("Collecting country distribution...")

    cursor.execute("""
        SELECT 
            country_code,
            COUNT(*) as count
        FROM channels
        WHERE country_code IS NOT NULL
        GROUP BY country_code
        ORDER BY count DESC
        LIMIT 20
    """)

    stats["countries"] = {row[0]: row[1] for row in cursor.fetchall()}

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

    print(f"✓ {stats_path}")
    print(f"✓ {latest_path}")
    print()

    # === Report ===
    print("=" * 70)
    print("STATISTICS SUMMARY")
    print("=" * 70)
    print()

    print(f"Total channels:          {stats['channels']['total']:,}")
    print(f"With streams:            {stats['channels']['with_streams']:,}")
    print()

    print("Taxonomy:")
    print(f"  By resolution:         {len(stats['taxonomy']['by_resolution'])} types")
    for res, count in stats['taxonomy']['by_resolution'].items():
        print(f"    {res:5}: {count:6,}")

    print(f"  By country:            {len(stats['taxonomy']['by_country'])} countries (top 10)")
    for country, count in list(stats['taxonomy']['by_country'].items())[:10]:
        print(f"    {country}: {count:6,}")

    print(f"  By variant:            {len(stats['taxonomy']['by_variant'])} types")
    for variant, count in stats['taxonomy']['by_variant'].items():
        print(f"    {variant:15}: {count:6,}")

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

    if stats['matching']:
        print("Matching:")
        print(f"  Total matched:         {stats['matching']['total_matched']:,}")
        print(f"  Match rate:            {stats['matching']['match_rate']}%")
        print(f"  Avg confidence:        {stats['matching']['average_confidence']:.3f}")
        print(f"  High (0.9+):           {stats['matching']['high_confidence']:,}")
        print(f"  Medium (0.7-0.89):     {stats['matching']['medium_confidence']:,}")
        print(f"  Low (<0.7):            {stats['matching']['low_confidence']:,}")

    print()
    print("✅ Done!")


if __name__ == "__main__":
    generate_stats()
