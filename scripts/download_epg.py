#!/usr/bin/env python3
"""
Download EPG (Electronic Program Guide) for TV channels using TVG IDs.

Supported sources:
1. xmltv.net - community EPG database
2. epg-guide.com - aggregated EPG
3. Local cache with fallback

Process:
1. Query unique TVG IDs from channels
2. For each TVG ID, try to fetch EPG from providers
3. Cache locally with metadata
4. Generate stats
"""

import sqlite3
import json
import sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional, Dict, List

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: uv pip install httpx")
    sys.exit(1)

DB_PATH = Path("output/iptv_full.db")
EPG_CACHE_DIR = Path("epg/cache")
EPG_STATS_PATH = Path("stats/epg_stats.json")

# EPG providers
EPG_PROVIDERS = [
    {
        "name": "xmltv",
        "base_url": "https://epg.xmltv.net/",
        "template": "{base_url}{tvg_id}.xml.gz",
        "format": "xml",
        "timeout": 30,
    },
    {
        "name": "epg-guide",
        "base_url": "https://www.epg-guide.com/xmltv/",
        "template": "{base_url}{tvg_id}.xml.gz",
        "format": "xml",
        "timeout": 30,
    },
]

# Cache validity (hours)
CACHE_VALIDITY = 24


def get_unique_tvg_ids() -> List[str]:
    """Get unique TVG IDs from database."""
    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found")
        return []

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT tvg_id
        FROM channels
        WHERE tvg_id IS NOT NULL AND tvg_id != ''
        ORDER BY tvg_id
    """)

    tvg_ids = [row[0] for row in cursor.fetchall()]
    conn.close()

    return tvg_ids


def get_cache_path(tvg_id: str) -> Path:
    """Get cache file path for TVG ID."""
    # Sanitize TVG ID for filename
    safe_id = tvg_id.replace('/', '_').replace('\\', '_')
    return EPG_CACHE_DIR / f"{safe_id}.xml"


def is_cache_valid(cache_path: Path) -> bool:
    """Check if cache file is still valid."""
    if not cache_path.exists():
        return False

    # Check age
    age_hours = (datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)).total_seconds() / 3600
    return age_hours < CACHE_VALIDITY


def download_epg(tvg_id: str, client: httpx.Client) -> Optional[bytes]:
    """
    Try to download EPG for a TVG ID from providers.
    Returns decompressed XML content or None.
    """
    import gzip

    for provider in EPG_PROVIDERS:
        url = provider["template"].format(
            base_url=provider["base_url"],
            tvg_id=tvg_id,
        )

        try:
            response = client.get(url, timeout=provider["timeout"])
            if response.status_code == 200:
                # Decompress if gzip
                if url.endswith('.gz'):
                    try:
                        return gzip.decompress(response.content)
                    except Exception:
                        pass
                return response.content
        except Exception as e:
            # Silent fail, try next provider
            pass

    return None


def parse_epg_xml(content: bytes) -> Dict:
    """
    Parse EPG XML and extract basic info.
    Returns dict with stats.
    """
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(content)

        # Count programs
        programmes = root.findall('programme')
        channels = root.findall('channel')

        return {
            "channels": len(channels),
            "programmes": len(programmes),
            "valid": True,
        }
    except Exception:
        return {"valid": False}


def main():
    print("=" * 70)
    print("📺 EPG Downloader")
    print("=" * 70)
    print()

    # Create cache dir
    EPG_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Get unique TVG IDs
    print("[1/4] Querying TVG IDs from database...")
    print()

    tvg_ids = get_unique_tvg_ids()
    print(f"  Found {len(tvg_ids)} unique TVG IDs")
    print()

    if not tvg_ids:
        print("ERROR: No TVG IDs found")
        return

    # Download EPG
    print("[2/4] Downloading EPG from providers...")
    print()

    stats = {
        "timestamp": datetime.now().isoformat(),
        "total_tvg_ids": len(tvg_ids),
        "downloaded": 0,
        "cached": 0,
        "failed": 0,
        "by_provider": defaultdict(int),
        "epg_stats": {},
    }

    with httpx.Client(timeout=30) as client:
        for i, tvg_id in enumerate(tvg_ids):
            if (i + 1) % max(1, len(tvg_ids) // 10) == 0:
                print(f"  Progress: {i + 1}/{len(tvg_ids)}")

            cache_path = get_cache_path(tvg_id)

            # Check cache first
            if is_cache_valid(cache_path):
                stats["cached"] += 1
                continue

            # Download
            content = download_epg(tvg_id, client)
            if content:
                # Save to cache
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                with open(cache_path, 'wb') as f:
                    f.write(content)

                # Parse and store stats
                epg_info = parse_epg_xml(content)
                stats["epg_stats"][tvg_id] = epg_info
                stats["downloaded"] += 1
            else:
                stats["failed"] += 1

    print()

    # Generate stats
    print("[3/4] Generating statistics...")
    print()

    # Count valid EPG files
    epg_files = list(EPG_CACHE_DIR.glob("*.xml"))
    total_size = sum(f.stat().st_size for f in epg_files) / (1024 * 1024)  # MB
    total_programmes = sum(
        v.get("programmes", 0) for v in stats["epg_stats"].values()
    )

    stats["cache_info"] = {
        "total_files": len(epg_files),
        "total_size_mb": round(total_size, 2),
        "total_programmes": total_programmes,
    }

    # Save stats
    print("[4/4] Saving statistics...")
    print()

    EPG_STATS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(EPG_STATS_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False, default=str)

    print(f"✓ Stats saved: {EPG_STATS_PATH}")
    print()

    # Report
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    print(f"TVG IDs total:         {stats['total_tvg_ids']}")
    print(f"Downloaded (new):      {stats['downloaded']}")
    print(f"From cache:            {stats['cached']}")
    print(f"Failed:                {stats['failed']}")
    print()

    print("Cache:")
    print(f"  Files:               {stats['cache_info']['total_files']}")
    print(f"  Total size:          {stats['cache_info']['total_size_mb']:.2f} MB")
    print(f"  Total programmes:    {stats['cache_info']['total_programmes']:,}")
    print()

    if stats["downloaded"] > 0:
        avg_programmes = total_programmes / stats["downloaded"]
        print(f"Average programmes per EPG: {avg_programmes:.0f}")

    print()
    print("✅ Done!")


if __name__ == "__main__":
    main()
