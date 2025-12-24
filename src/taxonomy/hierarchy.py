"""
Channel hierarchy builder: assigns parent_id, root_id, is_root, is_variant.
"""

from __future__ import annotations

from collections import defaultdict
from typing import List, Dict


def build_hierarchy(channels: List[dict]) -> None:
    """
    Build parent/root hierarchy for channels in-place.

    Modifies channels to have:
    - root_id: ID of the root channel in the group
    - parent_id: ID of the parent (for variants)
    - is_root: bool, 1 if this is root
    - is_variant: bool, 1 if this is a variant

    Logic:
    1. Group channels by normalized_name (base name)
    2. Per group, find root:
       - Prefer channels without variant
       - Among those, prefer highest stream_count (or lowest id as tiebreaker)
    3. All other channels in group get parent_id = root.id, is_variant = 1
    """
    # Group by normalized_name
    buckets: Dict[str, List[dict]] = defaultdict(list)

    for ch in channels:
        key = ch.get("normalized_name") or ""
        if not key:
            # Fallback: use parsed.base_name if available
            if "parsed" in ch:
                key = ch["parsed"].base_name.lower()
        if not key:
            # Last resort: skip
            continue

        buckets[key].append(ch)

    # Process each bucket
    for bucket_key, bucket in buckets.items():
        if not bucket:
            continue

        # Candidates for root: no variant (or if all have variant, take any)
        candidates = [ch for ch in bucket if not ch.get("variant")]
        if not candidates:
            candidates = bucket

        # Select root: max stream_count, then min id
        root = max(
            candidates,
            key=lambda ch: (
                ch.get("stream_count", 0),
                -ch.get("id", 0),
            ),
        )

        root_id = root["id"]

        # Mark root
        root["root_id"] = root_id
        root["parent_id"] = None
        root["is_root"] = 1
        root["is_variant"] = 0

        # Mark variants
        for ch in bucket:
            if ch is root:
                continue
            ch["root_id"] = root_id
            ch["parent_id"] = root_id
            ch["is_root"] = 0
            ch["is_variant"] = 1
