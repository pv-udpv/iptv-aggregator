#!/usr/bin/env python3
"""
Production Fuzzy Matching with Rapid Fuzz + Taxonomy Normalization

Features:
- rapidfuzz for 10-15x faster matching than difflib
- Channel taxonomy extraction (resolution, country, language, variant)
- Parent/root hierarchy building
- Multi-factor scoring (name + country + resolution)
- SQLite persistence
"""

import json
import sqlite3
import sys
import time
from pathlib import Path
from typing import List, Dict, Optional, Tuple

try:
    from rapidfuzz import fuzz, process
except ImportError:
    print("ERROR: rapidfuzz not installed")
    print("Run: uv pip install rapidfuzz")
    sys.exit(1)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from taxonomy.channel_parser import parse_channel_name, ParsedChannel
from taxonomy.hierarchy import build_hierarchy


# ============================================================================
# Configuration
# ============================================================================

OUTPUT_DIR = Path("output")
DB_PATH = OUTPUT_DIR / "iptv_full.db"
DUMP_PATH = OUTPUT_DIR / "tv_channel_full_dump.json"
RESULT_PATH = OUTPUT_DIR / "matching_results_v2.json"

NAME_SCORE_WEIGHT = 0.75
COUNTRY_BONUS = 0.15
COUNTRY_PENALTY = -0.10
RESOLUTION_BONUS = 0.10

MIN_CONFIDENCE_AUTO = 0.60
MIN_CONFIDENCE_REPORT = 0.50


# ============================================================================
# Channel Loading
# ============================================================================

def load_iptv_portal_channels() -> List[dict]:
    """Load channels from IPTVPortal dump JSON."""
    if not DUMP_PATH.exists():
        print(f"ERROR: {DUMP_PATH} not found")
        return []

    with open(DUMP_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    records = data.get("records", [])
    print(f"✓ Loaded {len(records)} IPTVPortal channels")
    return records


def load_local_channels() -> List[dict]:
    """Load channels from SQLite (iptv-org)."""
    if not DB_PATH.exists():
        print(f"WARNING: {DB_PATH} not found, using mock data")
        return [
            {"id": 1, "name": "BBC One", "stream_count": 5},
            {"id": 2, "name": "RT", "stream_count": 3},
            {"id": 3, "name": "CNN", "stream_count": 2},
        ]

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    try:
        cur.execute("""
            SELECT id, name, COUNT(s.id) as stream_count
            FROM channels c
            LEFT JOIN streams s ON c.id = s.channel_id
            GROUP BY c.id
            ORDER BY c.id
        """)
        rows = cur.fetchall()
        channels = [dict(row) for row in rows]
    except sqlite3.OperationalError as e:
        print(f"ERROR querying channels: {e}")
        conn.close()
        return []

    conn.close()

    print(f"✓ Loaded {len(channels)} local (iptv-org) channels")
    return channels


# ============================================================================
# Taxonomy Enrichment
# ============================================================================

def enrich_with_taxonomy(channels: List[dict]) -> None:
    """Parse channel names and enrich with taxonomy metadata."""
    for ch in channels:
        parsed = parse_channel_name(ch["name"])
        ch["parsed"] = parsed
        ch["normalized_name"] = parsed.normalized_name
        ch["resolution"] = parsed.resolution
        ch["country_code"] = parsed.country_code
        ch["lang_code"] = parsed.lang_code
        ch["variant"] = parsed.variant


# ============================================================================
# Scoring
# ============================================================================

def base_name_confidence(local_parsed: ParsedChannel, portal_parsed: ParsedChannel) -> float:
    """Calculate name similarity score using rapidfuzz."""
    n1 = local_parsed.base_name.lower()
    n2 = portal_parsed.base_name.lower()

    if not n1 or not n2:
        return 0.0

    score = fuzz.token_sort_ratio(n1, n2)
    return score / 100.0


def combined_score(local_ch: dict, portal_ch: dict) -> float:
    """
    Calculate combined matching score with multiple factors.

    Factors:
    - Name similarity (75%)
    - Country match bonus/penalty (15%)
    - Resolution match bonus (10%)
    """
    # Name similarity
    name_score = base_name_confidence(
        local_ch["parsed"],
        portal_ch["parsed"],
    )

    # Country bonus/penalty
    country_bonus = 0.0
    lc = local_ch["parsed"].country_code
    pc = portal_ch["parsed"].country_code

    if lc and pc:
        if lc == pc:
            country_bonus = COUNTRY_BONUS
        else:
            country_bonus = COUNTRY_PENALTY

    # Resolution bonus
    res_bonus = 0.0
    lr = local_ch["parsed"].resolution
    pr = portal_ch["parsed"].resolution

    if lr and pr and lr == pr:
        res_bonus = RESOLUTION_BONUS

    # Weighted sum
    score = (
        name_score * NAME_SCORE_WEIGHT
        + country_bonus
        + res_bonus
    )

    return max(0.0, min(1.0, score))


# ============================================================================
# Fast Matching with RapidFuzz
# ============================================================================

def index_portal_channels(channels: List[dict]) -> Tuple[List[str], Dict[str, dict]]:
    """Create searchable index for portal channels."""
    names = [ch["normalized_name"] for ch in channels]
    by_name = {ch["normalized_name"]: ch for ch in channels}
    return names, by_name


def match_one_channel(
    local_ch: dict,
    portal_names: List[str],
    portal_by_name: Dict[str, dict],
    score_cutoff: float = MIN_CONFIDENCE_AUTO,
) -> Optional[dict]:
    """
    Find best match for local channel in portal channels.

    Uses rapidfuzz for fast initial filtering, then combined_score for ranking.
    """
    # Fast initial search with rapidfuzz
    best = process.extractOne(
        local_ch["parsed"].base_name.lower(),
        portal_names,
        scorer=fuzz.token_sort_ratio,
        score_cutoff=score_cutoff * 100,
    )

    if not best:
        return None

    match_name, _, _ = best
    portal_ch = portal_by_name[match_name]

    # Refined scoring with multi-factor logic
    score = combined_score(local_ch, portal_ch)

    if score < score_cutoff:
        return None

    return {
        "local_id": local_ch["id"],
        "local_name": local_ch["name"],
        "local_normalized": local_ch["normalized_name"],
        "local_resolution": local_ch["resolution"],
        "local_country": local_ch["country_code"],
        "local_lang": local_ch["lang_code"],
        "local_variant": local_ch["variant"],
        "portal_id": portal_ch["id"],
        "portal_name": portal_ch["name"],
        "portal_normalized": portal_ch["normalized_name"],
        "portal_resolution": portal_ch["resolution"],
        "portal_country": portal_ch["country_code"],
        "portal_lang": portal_ch["lang_code"],
        "portal_variant": portal_ch["variant"],
        "confidence": round(score, 3),
        "match_type": (
            "exact"
            if local_ch["normalized_name"] == portal_ch["normalized_name"]
            else "fuzzy"
        ),
    }


# ============================================================================
# Main Pipeline
# ============================================================================

def main() -> None:
    print("=" * 70)
    print("PRODUCTION FUZZY MATCHING v2 (with rapidfuzz + taxonomy)")
    print("=" * 70)
    print()

    start_time = time.time()

    # [1] Load channels
    print("[1/5] Loading channels...")
    print()

    portal_channels = load_iptv_portal_channels()
    local_channels = load_local_channels()

    if not portal_channels or not local_channels:
        print("ERROR: No channels to match")
        return

    print()

    # [2] Enrich with taxonomy
    print("[2/5] Enriching with taxonomy...")
    print()

    enrich_with_taxonomy(portal_channels)
    enrich_with_taxonomy(local_channels)

    # Show examples
    print("Examples:")
    for ch in local_channels[:3]:
        p = ch["parsed"]
        print(
            f"  {ch['name']:30} -> {p.base_name:20} "
            f"[res={p.resolution or '-':3}] [country={p.country_code or '-'}] "
            f"[var={p.variant or '-'}]"
        )

    print()

    # [3] Build hierarchy
    print("[3/5] Building hierarchy...")
    print()

    build_hierarchy(portal_channels)
    build_hierarchy(local_channels)

    roots_portal = sum(1 for ch in portal_channels if ch.get("is_root", 0))
    variants_portal = sum(1 for ch in portal_channels if ch.get("is_variant", 0))

    print(f"Portal channels: {len(portal_channels)}")
    print(f"  - Roots: {roots_portal}")
    print(f"  - Variants: {variants_portal}")
    print()

    # [4] Index and match
    print("[4/5] Matching channels...")
    print()

    portal_names, portal_by_name = index_portal_channels(portal_channels)

    matches: List[dict] = []
    unmatched: List[dict] = []

    for i, local_ch in enumerate(local_channels):
        # Progress
        if (i + 1) % max(1, len(local_channels) // 10) == 0:
            elapsed = time.time() - start_time
            rate = (i + 1) / elapsed
            eta = (len(local_channels) - i - 1) / rate if rate > 0 else 0
            print(
                f"  [{i+1}/{len(local_channels):4}] "
                f"{(i+1)*100//len(local_channels):3}% | "
                f"Rate: {rate:8.1f} ch/s | "
                f"ETA: {eta/60:5.1f}min"
            )

        match = match_one_channel(
            local_ch,
            portal_names,
            portal_by_name,
            score_cutoff=MIN_CONFIDENCE_AUTO,
        )

        if match:
            matches.append(match)
        else:
            unmatched.append({
                "local_id": local_ch["id"],
                "local_name": local_ch["name"],
                "local_normalized": local_ch["normalized_name"],
            })

    print()

    # [5] Report and persist
    print("[5/5] Generating report...")
    print()

    elapsed = time.time() - start_time

    result = {
        "source": "IPTVPortal ⟷ iptv-org",
        "timestamp": time.time(),
        "processing_time_sec": round(elapsed, 1),
        "total_local": len(local_channels),
        "total_portal": len(portal_channels),
        "matched": len(matches),
        "unmatched": len(unmatched),
        "match_rate": round(len(matches) / len(local_channels) * 100, 1) if local_channels else 0,
        "config": {
            "name_weight": NAME_SCORE_WEIGHT,
            "country_bonus": COUNTRY_BONUS,
            "country_penalty": COUNTRY_PENALTY,
            "resolution_bonus": RESOLUTION_BONUS,
            "min_confidence_auto": MIN_CONFIDENCE_AUTO,
        },
        "stats": {
            "exact_matches": sum(1 for m in matches if m["match_type"] == "exact"),
            "fuzzy_matches": sum(1 for m in matches if m["match_type"] == "fuzzy"),
            "avg_confidence": round(
                sum(m["confidence"] for m in matches) / len(matches), 3
            ) if matches else 0.0,
            "confidence_distribution": {
                "high (0.9+)": sum(1 for m in matches if m["confidence"] >= 0.9),
                "medium (0.7-0.89)": sum(1 for m in matches if 0.7 <= m["confidence"] < 0.9),
                "low (0.5-0.69)": sum(1 for m in matches if 0.5 <= m["confidence"] < 0.7),
            },
        },
        "matches": matches[:100],  # Top 100 for report
        "unmatched": unmatched[:50],  # Top 50 unmatched
    }

    # Save to file
    with open(RESULT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"✓ Results saved: {RESULT_PATH}")
    print()

    # === Report ===
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print()

    print(f"Local:           {result['total_local']}")
    print(f"Portal:          {result['total_portal']}")
    print(f"Matched:         {result['matched']} ({result['match_rate']}%)")
    print(f"Unmatched:       {result['unmatched']}")
    print()

    print("Match types:")
    print(f"  Exact:  {result['stats']['exact_matches']}")
    print(f"  Fuzzy:  {result['stats']['fuzzy_matches']}")
    print()

    print("Confidence distribution:")
    for label, count in result['stats']['confidence_distribution'].items():
        print(f"  {label:20}: {count:4}")
    print()

    print(f"Average confidence: {result['stats']['avg_confidence']:.3f}")
    print(f"Processing time: {result['processing_time_sec']:.1f} sec")
    print()

    if result['matches']:
        print("Top-10 matches:")
        for i, m in enumerate(matches[:10], 1):
            print(
                f"  {i:2}. {m['local_name']:30} → "
                f"{m['portal_name']:30} ({m['confidence']:.0%})"
            )
        print()

    print("✅ Done!")


if __name__ == "__main__":
    main()
