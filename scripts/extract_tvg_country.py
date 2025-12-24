#!/usr/bin/env python3
"""
Extract country codes from TVG IDs and update database.

Example TVG IDs:
  "3sat.de" → "DE"
  "bbc1.uk" → "GB"
  "cnn.us" → "US"
  "rt.ru" → "RU"
"""

import sqlite3
import re
from pathlib import Path
from typing import Optional
from collections import defaultdict

DB_PATH = Path("output/iptv_full.db")

# Country code mapping
COUNTRY_MAP = {
    'uk': 'GB',
    'us': 'US',
    'ru': 'RU',
    'de': 'DE',
    'fr': 'FR',
    'es': 'ES',
    'it': 'IT',
    'pt': 'PT',
    'gr': 'GR',
    'nl': 'NL',
    'be': 'BE',
    'ch': 'CH',
    'at': 'AT',
    'se': 'SE',
    'no': 'NO',
    'dk': 'DK',
    'fi': 'FI',
    'pl': 'PL',
    'cz': 'CZ',
    'sk': 'SK',
    'hu': 'HU',
    'ro': 'RO',
    'bg': 'BG',
    'hr': 'HR',
    'si': 'SI',
    'ua': 'UA',
    'by': 'BY',
    'kz': 'KZ',
    'tr': 'TR',
    'gr': 'GR',
    'ca': 'CA',
    'mx': 'MX',
    'br': 'BR',
    'ar': 'AR',
    'au': 'AU',
    'nz': 'NZ',
    'jp': 'JP',
    'cn': 'CN',
    'hk': 'HK',
    'kr': 'KR',
    'in': 'IN',
    'pk': 'PK',
    'bd': 'BD',
    'th': 'TH',
    'sg': 'SG',
    'my': 'MY',
    'ph': 'PH',
    'id': 'ID',
    'vn': 'VN',
    'tw': 'TW',
    'il': 'IL',
    'ae': 'AE',
    'sa': 'SA',
    'eg': 'EG',
    'za': 'ZA',
    'ng': 'NG',
}


def extract_country_from_tvg_id(tvg_id: str) -> Optional[str]:
    """
    Extract country code from TVG ID.

    Examples:
      "3sat.de" → "DE"
      "bbc1.uk" → "GB"
      "cnn.us" → "US"
      "rt.ru" → "RU"
    """
    if not tvg_id:
        return None

    tvg_id = tvg_id.lower().strip()

    # Try to extract last part after last dot
    parts = tvg_id.split('.')
    if len(parts) >= 2:
        country_code = parts[-1].strip()

        # Map to ISO 3166-1 alpha-2
        return COUNTRY_MAP.get(country_code, None)

    return None


def main():
    print("=" * 70)
    print("Extracting country codes from TVG IDs")
    print("=" * 70)
    print()

    if not DB_PATH.exists():
        print(f"ERROR: {DB_PATH} not found")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Get all channels with TVG IDs but no country
    print("Querying channels...")
    cursor.execute("""
        SELECT id, name, tvg_id, country_code
        FROM channels
        WHERE tvg_id IS NOT NULL AND tvg_id != ''
        ORDER BY id
    """)

    rows = cursor.fetchall()
    print(f"  Found {len(rows)} channels with TVG IDs")
    print()

    # Extract and update
    updated = 0
    country_stats = defaultdict(int)
    before_stats = defaultdict(int)
    after_stats = defaultdict(int)

    print("Processing...")
    for i, (ch_id, name, tvg_id, old_country) in enumerate(rows):
        if (i + 1) % max(1, len(rows) // 10) == 0:
            print(f"  Progress: {i + 1}/{len(rows)}")

        # Extract country from TVG ID
        new_country = extract_country_from_tvg_id(tvg_id)

        if new_country:
            # Update only if we don't have a country or it's clearly wrong
            if not old_country or old_country in ['TV', 'HD', 'FM', 'DD']:
                cursor.execute("""
                    UPDATE channels SET country_code = ?
                    WHERE id = ?
                """, (new_country, ch_id))
                updated += 1
                country_stats[new_country] += 1

        # Stats collection
        if old_country:
            before_stats[old_country] += 1
        if new_country:
            after_stats[new_country] += 1

    conn.commit()
    conn.close()

    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    print(f"Channels processed:    {len(rows)}")
    print(f"Countries extracted:   {len(country_stats)}")
    print(f"Channels updated:      {updated}")
    print()

    if country_stats:
        print("Extracted countries (top 15):")
        for country, count in sorted(
            country_stats.items(), key=lambda x: x[1], reverse=True
        )[:15]:
            print(f"  {country}: {count:5}")

    print()
    print("✅ Done!")


if __name__ == "__main__":
    main()
