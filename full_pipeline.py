#!/usr/bin/env python3
"""
Пиплайн для сборки базы IPTV-ORG и сохранению в SQLite

Процесс:
1. Мастер плэйлист (https://iptv-org.github.io/iptv/index.m3u)
2. Парсинг M3U и экстракция метаданных
3. Сохранение в SQLite
4. Оптимизация и индексы
"""

import sqlite3
import json
import re
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: uv pip install httpx")
    import sys
    sys.exit(1)


def parse_m3u_line(line):
    """Parse M3U line and extract metadata."""
    
    extinf_match = re.match(r'#EXTINF:([^,]+),(.+)', line)
    if not extinf_match:
        return None
    
    info_str = extinf_match.group(1)
    name = extinf_match.group(2).strip()
    
    # Parse attributes
    attributes = {}
    attr_pattern = r'([a-z-]+)="([^"]*)'r'"'
    for match in re.finditer(attr_pattern, extinf_match.group(1)):
        key = match.group(1).lower()
        value = match.group(2)
        attributes[key] = value
    
    return {
        'name': name,
        'tvg_id': attributes.get('tvg-id', ''),
        'tvg_name': attributes.get('tvg-name', ''),
        'tvg_logo': attributes.get('tvg-logo', ''),
        'group_title': attributes.get('group-title', ''),
        'duration': attributes.get('duration', '-1'),
    }


def download_master_playlist():
    """Download master M3U playlist from IPTV-ORG."""
    
    print("=" * 70)
    print("FULL PIPELINE: IPTV-ORG Database Builder")
    print("=" * 70)
    print()
    
    url = "https://iptv-org.github.io/iptv/index.m3u"
    
    print(f"Step 1: Downloading master playlist...")
    print(f"  URL: {url}")
    print()
    
    try:
        with httpx.Client(timeout=120) as client:
            response = client.get(url)
            response.raise_for_status()
            content = response.text
    except Exception as e:
        print(f"ERROR: Failed to download: {e}")
        return []
    
    lines = content.split('\n')
    print(f"  ✅ Downloaded {len(lines)} lines")
    print()
    
    # Parse M3U
    print(f"Step 2: Parsing M3U...")
    channels = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        if line.startswith('#EXTINF:'):
            metadata = parse_m3u_line(line)
            
            # Next line should be URL
            if i + 1 < len(lines):
                url = lines[i + 1].strip()
                if url and not url.startswith('#'):
                    if metadata:
                        metadata['url'] = url
                        channels.append(metadata)
                    i += 1
        
        i += 1
    
    print(f"  ✅ Parsed {len(channels)} channels")
    print()
    
    return channels


def save_to_sqlite(channels):
    """Save channels to SQLite database."""
    
    print(f"Step 3: Saving to SQLite...")
    
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    db_path = output_dir / "iptv_full.db"
    
    print(f"  Database: {db_path}")
    
    # Drop old DB
    if db_path.exists():
        db_path.unlink()
        print(f"  🗑️ Removed old database")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            tvg_id TEXT,
            tvg_name TEXT,
            tvg_logo TEXT,
            group_title TEXT,
            url TEXT,
            duration TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            normalized_name TEXT,
            resolution TEXT,
            country_code TEXT,
            lang_code TEXT,
            variant TEXT,
            parent_id INTEGER,
            root_id INTEGER,
            is_root BOOLEAN DEFAULT 0,
            is_variant BOOLEAN DEFAULT 0
        )
    """)
    
    # Insert channels
    for i, ch in enumerate(channels):
        cursor.execute("""
            INSERT INTO channels 
            (name, tvg_id, tvg_name, tvg_logo, group_title, url, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            ch['name'],
            ch.get('tvg_id', ''),
            ch.get('tvg_name', ''),
            ch.get('tvg_logo', ''),
            ch.get('group_title', ''),
            ch.get('url', ''),
            ch.get('duration', '-1'),
        ))
        
        if (i + 1) % 5000 == 0:
            print(f"    Progress: {i + 1}/{len(channels)}")
    
    conn.commit()
    
    # Create indexes
    print(f"  Creating indexes...")
    cursor.execute("CREATE INDEX idx_name ON channels(name)")
    cursor.execute("CREATE INDEX idx_normalized_name ON channels(normalized_name)")
    cursor.execute("CREATE INDEX idx_country ON channels(country_code)")
    cursor.execute("CREATE INDEX idx_root_id ON channels(root_id)")
    
    conn.commit()
    conn.close()
    
    print(f"  ✅ Saved {len(channels)} channels")
    print(f"  ✅ Database size: {db_path.stat().st_size / (1024 * 1024):.2f} MB")
    print()


def generate_stats(channels):
    """Generate basic statistics."""
    
    print(f"Step 4: Statistics...")
    print()
    
    # Group by country
    countries = {}
    for ch in channels:
        group = ch.get('group_title', 'Unknown')
        countries[group] = countries.get(group, 0) + 1
    
    print(f"Total channels: {len(channels)}")
    print()
    print(f"Top 15 groups:")
    for group, count in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:15]:
        print(f"  {group[:40]:40s}: {count:5d}")
    
    print()


def main():
    """Main pipeline."""
    
    channels = download_master_playlist()
    
    if not channels:
        print("ERROR: No channels downloaded")
        return
    
    save_to_sqlite(channels)
    generate_stats(channels)
    
    print("=" * 70)
    print("✅ PIPELINE COMPLETED!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. python scripts/migrate_taxonomy.py  - Add taxonomy columns")
    print("  2. python output/production_fuzzy_matching_v2.py  - Match channels")
    print("  3. python scripts/generate_channel_stats.py  - Generate stats")
    print()


if __name__ == "__main__":
    main()
