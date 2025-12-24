#!/usr/bin/env python3
"""
Generate M3U playlists with EPG guide information.

Output formats:
1. playlist.m3u8 - standard IPTV playlist
2. playlist_with_epg.m3u8 - with EPG source URLs
3. playlist_by_group.m3u8 - grouped by category
4. playlist_best.m3u8 - only channels with EPG
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from typing import List, Dict, Optional
from urllib.parse import quote

DB_PATH = Path("output/iptv_full.db")
PLAYLIST_DIR = Path("playlists")
EPG_CACHE_DIR = Path("epg/cache")

# EPG provider mapping
EPG_PROVIDERS = {
    "xmltv": "https://epg.xmltv.net/",
    "epg-guide": "https://www.epg-guide.com/xmltv/",
}


def get_channels_from_db() -> List[Dict]:
    """Load channels from database."""
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found")
        return []

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            id, name, tvg_id, tvg_name, tvg_logo,
            group_title, url, country_code, resolution
        FROM channels
        WHERE url IS NOT NULL AND url != ''
        ORDER BY
            CASE WHEN group_title IS NULL THEN 1 ELSE 0 END,
            group_title, name
    """)

    channels = [dict(row) for row in cursor.fetchall()]
    conn.close()

    return channels


def has_epg(tvg_id: Optional[str]) -> bool:
    """Check if EPG exists for TVG ID."""
    if not tvg_id:
        return False

    safe_id = tvg_id.replace('/', '_').replace('\\', '_')
    cache_path = EPG_CACHE_DIR / f"{safe_id}.xml"
    return cache_path.exists()


def get_epg_url(tvg_id: str) -> Optional[str]:
    """Get EPG URL for TVG ID."""
    if not tvg_id:
        return None

    # Try xmltv first
    return f"https://epg.xmltv.net/{tvg_id}.xml.gz"


def escape_m3u_value(value: Optional[str]) -> str:
    """Escape value for M3U attributes."""
    if not value:
        return ""
    # Escape quotes
    return str(value).replace('"', '\\"')


def generate_extinf(channel: Dict) -> str:
    """
    Generate #EXTINF line for M3U.
    Format: #EXTINF:duration,tvg-id="" tvg-name="" tvg-logo="" group-title="",Channel Name
    """
    parts = [
        '#EXTINF:-1',
    ]

    # TVG ID
    if channel.get('tvg_id'):
        tvg_id = escape_m3u_value(channel['tvg_id'])
        parts.append(f'tvg-id="{tvg_id}"')

    # TVG Name (or use channel name)
    tvg_name = channel.get('tvg_name') or channel.get('name', '')
    if tvg_name:
        tvg_name = escape_m3u_value(tvg_name)
        parts.append(f'tvg-name="{tvg_name}"')

    # TVG Logo
    if channel.get('tvg_logo'):
        tvg_logo = escape_m3u_value(channel['tvg_logo'])
        parts.append(f'tvg-logo="{tvg_logo}"')

    # Group
    group = channel.get('group_title', 'Undefined')
    if group:
        group = escape_m3u_value(group)
        parts.append(f'group-title="{group}"')

    # Channel name
    channel_name = escape_m3u_value(channel['name'])
    extinf = ' '.join(parts) + f',{channel_name}'

    return extinf


def generate_playlist_standard(channels: List[Dict]) -> str:
    """Generate standard M3U playlist."""
    lines = ['#EXTM3U']

    for channel in channels:
        extinf = generate_extinf(channel)
        lines.append(extinf)
        lines.append(channel['url'])

    return '\n'.join(lines)


def generate_playlist_with_epg(channels: List[Dict]) -> str:
    """Generate M3U with EPG guide sources."""
    lines = ['#EXTM3U']

    for channel in channels:
        extinf = generate_extinf(channel)
        url = channel['url']

        # Add EPG source if available
        if channel.get('tvg_id'):
            epg_url = get_epg_url(channel['tvg_id'])
            if epg_url:
                url += f" | {epg_url}"

        lines.append(extinf)
        lines.append(url)

    return '\n'.join(lines)


def generate_playlist_by_group(channels: List[Dict]) -> str:
    """Generate M3U grouped by category."""
    lines = ['#EXTM3U']

    # Group channels
    grouped = defaultdict(list)
    for channel in channels:
        group = channel.get('group_title') or 'Undefined'
        grouped[group].append(channel)

    # Generate playlists grouped
    for group in sorted(grouped.keys()):
        # Group comment
        lines.append(f"# GROUP: {group}")
        lines.append('')

        for channel in grouped[group]:
            extinf = generate_extinf(channel)
            lines.append(extinf)
            lines.append(channel['url'])
            lines.append('')

    return '\n'.join(lines)


def generate_playlist_best(channels: List[Dict]) -> str:
    """Generate M3U with only channels that have EPG."""
    # Filter channels with EPG
    with_epg = [
        ch for ch in channels
        if has_epg(ch.get('tvg_id'))
    ]

    lines = ['#EXTM3U']

    for channel in with_epg:
        extinf = generate_extinf(channel)
        url = channel['url']

        # Add EPG source
        epg_url = get_epg_url(channel['tvg_id'])
        if epg_url:
            url += f" | {epg_url}"

        lines.append(extinf)
        lines.append(url)

    return '\n'.join(lines)


def main():
    print("=" * 70)
    print("📽 Generating M3U Playlists with EPG")
    print("=" * 70)
    print()

    # Load channels
    print("[1/4] Loading channels from database...")
    print()

    channels = get_channels_from_db()
    print(f"  Found {len(channels)} channels with URLs")

    channels_with_epg = sum(1 for ch in channels if has_epg(ch.get('tvg_id')))
    print(f"  With EPG: {channels_with_epg}")
    print()

    if not channels:
        print("ERROR: No channels found")
        return

    # Create output dir
    PLAYLIST_DIR.mkdir(parents=True, exist_ok=True)

    # Generate playlists
    print("[2/4] Generating playlists...")
    print()

    playlists = {
        "playlist.m3u8": ("Standard M3U", generate_playlist_standard),
        "playlist_with_epg.m3u8": ("With EPG guides", generate_playlist_with_epg),
        "playlist_by_group.m3u8": ("Grouped by category", generate_playlist_by_group),
    }

    if channels_with_epg > 0:
        playlists["playlist_best.m3u8"] = ("With EPG only", generate_playlist_best)

    stats = {
        "timestamp": datetime.now().isoformat(),
        "total_channels": len(channels),
        "channels_with_epg": channels_with_epg,
        "playlists": {},
    }

    for filename, (description, generator) in playlists.items():
        print(f"  Generating: {filename}")
        content = generator(channels)
        path = PLAYLIST_DIR / filename
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

        lines = len(content.split('\n'))
        stats["playlists"][filename] = {
            "description": description,
            "size_kb": len(content) / 1024,
            "lines": lines,
        }

    print()

    # Generate stats
    print("[3/4] Generating statistics...")
    print()

    stats_path = Path("stats/epg_playlist_stats.json")
    stats_path.parent.mkdir(parents=True, exist_ok=True)
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"✓ Stats saved: {stats_path}")
    print()

    # Report
    print("[4/4] Report")
    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    print(f"Channels total:        {len(channels)}")
    print(f"With EPG:              {channels_with_epg} ({channels_with_epg*100//len(channels)}%)")
    print()

    print("Playlists generated:")
    for filename, info in stats["playlists"].items():
        size_mb = info["size_kb"] / 1024
        print(f"  {filename:30} - {info['description']:25} ({size_mb:.2f} MB, {info['lines']} lines)")

    print()
    print(f"Output directory: {PLAYLIST_DIR.resolve()}")
    print()
    print("✅ Done!")


if __name__ == "__main__":
    main()
