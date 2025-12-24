#!/usr/bin/env python3
"""
Генерация статистики по каналам
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

print("=" * 70)
print("📊 Генерация статистики по каналам")
print("=" * 70)
print()

# Подключение к базе
db_path = Path("output/iptv_full.db")

if not db_path.exists():
    print(f"ERROR: {db_path} не найден")
    exit(1)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

stats = {
    "generated_at": datetime.utcnow().isoformat() + "Z",
    "channels": {},
    "matching": {},
    "countries": {},
    "categories": {}
}

# === Общая статистика каналов ===
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
    "without_streams": total_channels - channels_with_streams
}

# === Статистика matching ===
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
        "match_rate": round(row[0] / channels_with_streams * 100, 1) if channels_with_streams > 0 else 0
    }

# === Статистика по странам ===
cursor.execute("""
    SELECT 
        country,
        COUNT(*) as count
    FROM channels
    WHERE country IS NOT NULL
    GROUP BY country
    ORDER BY count DESC
    LIMIT 20
""")

stats["countries"] = {
    row[0]: row[1] for row in cursor.fetchall()
}

# === Статистика по категориям ===
cursor.execute("""
    SELECT 
        categories,
        COUNT(*) as count
    FROM channels
    WHERE categories IS NOT NULL
    GROUP BY categories
    ORDER BY count DESC
    LIMIT 20
""")

stats["categories"] = {
    row[0]: row[1] for row in cursor.fetchall()
}

conn.close()

# Сохранить
stats_dir = Path("stats")
stats_dir.mkdir(exist_ok=True)

timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
stats_path = stats_dir / f"channels_{timestamp}.json"

with open(stats_path, 'w', encoding='utf-8') as f:
    json.dump(stats, f, indent=2, ensure_ascii=False)

# Также latest
latest_path = stats_dir / "channels_latest.json"
with open(latest_path, 'w', encoding='utf-8') as f:
    json.dump(stats, f, indent=2, ensure_ascii=False)

print(f"✅ Статистика сохранена:")
print(f"   📊 {stats_path}")
print(f"   📊 {latest_path}")
print()

print("Краткая сводка:")
print(f"  Всего каналов: {stats['channels']['total']:,}")
print(f"  Со стримами: {stats['channels']['with_streams']:,}")

if stats.get('matching'):
    print(f"  Matched: {stats['matching']['total_matched']:,} ({stats['matching']['match_rate']}%)")
    print(f"  Avg confidence: {stats['matching']['average_confidence']:.1%}")

print()
print(f"  Топ-5 стран:")
for country, count in list(stats['countries'].items())[:5]:
    print(f"    {country}: {count:,}")
