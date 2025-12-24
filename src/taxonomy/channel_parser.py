"""
Channel name parser with resolution, country, language, and variant extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import List, Optional


@dataclass
class ParsedChannel:
    """Extracted channel metadata from raw name."""
    raw_name: str
    base_name: str
    normalized_name: str
    resolution: Optional[str]  # sd/hd/fhd/uhd/4k
    country_code: Optional[str]  # ISO 2-letter code
    lang_code: Optional[str]  # language code (ru, en, etc.)
    variant: Optional[str]  # plus, plus1, plus2, kids, news, east, west, etc.
    tags: List[str]  # list of extracted tags


# Resolution patterns (order matters: more specific first)
RESOLUTION_PATTERNS = [
    (re.compile(r'\b(4k|uhd)\b', re.I), 'uhd'),
    (re.compile(r'\b(fhd|full\s*hd|1080p?)\b', re.I), 'fhd'),
    (re.compile(r'\bhd\b', re.I), 'hd'),
    (re.compile(r'\bsd\b', re.I), 'sd'),
]

# Country code: 2-letter uppercase codes
COUNTRY_CODE_RE = re.compile(r'\b([A-Z]{2})\b')

# Language codes
LANG_CODE_RE = re.compile(r'\b(EN|RU|ES|DE|FR|PT|IT|UA|BY|KZ)\b', re.I)

# Variant patterns
VARIANT_PATTERNS = [
    (re.compile(r'\b\+1\b'), 'plus1'),
    (re.compile(r'\b\+2\b'), 'plus2'),
    (re.compile(r'\bplus\b', re.I), 'plus'),
    (re.compile(r'\b(kids|child|junior)\b', re.I), 'kids'),
    (re.compile(r'\bnews\b', re.I), 'news'),
    (re.compile(r'\b(east|west|north|south)\b', re.I), 'region'),
]

# Common noise words/patterns
NOISE_RE = re.compile(
    r'\b(TV|канал|channel|телеканал|HD|FHD|FULL\s*HD|4K|UHD|1080p?|720p?)\b',
    re.I,
)


def parse_channel_name(name: str) -> ParsedChannel:
    """
    Parse channel name and extract metadata.

    Example:
        "CNN HD RU" -> ParsedChannel(
            base_name="CNN",
            normalized_name="cnn",
            resolution="hd",
            country_code="RU",
            lang_code=None,
            variant=None,
            tags=["hd", "country:RU"]
        )
    """
    if not name:
        return ParsedChannel(
            raw_name=name,
            base_name="",
            normalized_name="",
            resolution=None,
            country_code=None,
            lang_code=None,
            variant=None,
            tags=[],
        )

    raw = name.strip()
    work = raw

    tags: List[str] = []

    # 1. Extract resolution
    resolution = None
    for pattern, val in RESOLUTION_PATTERNS:
        if pattern.search(work):
            resolution = val
            tags.append(val)
            work = pattern.sub(' ', work)
            break  # Take first match

    # 2. Extract country code (2-letter uppercase, e.g., RU, US, DE)
    country_code = None
    m = COUNTRY_CODE_RE.search(work)
    if m:
        country_code = m.group(1).upper()
        tags.append(f'country:{country_code}')
        work = COUNTRY_CODE_RE.sub(' ', work)

    # 3. Extract language code
    lang_code = None
    m = LANG_CODE_RE.search(work)
    if m:
        lang_code = m.group(1).lower()
        tags.append(f'lang:{lang_code}')
        work = LANG_CODE_RE.sub(' ', work)

    # 4. Extract variant
    variant = None
    for pattern, val in VARIANT_PATTERNS:
        if pattern.search(work):
            variant = val
            tags.append(f'variant:{val}')
            work = pattern.sub(' ', work)
            break  # Take first match

    # 5. Remove noise words
    work = NOISE_RE.sub(' ', work)

    # 6. Cleanup whitespace
    work = re.sub(r'\s+', ' ', work).strip()

    base_name = work
    normalized_name = work.lower()

    return ParsedChannel(
        raw_name=raw,
        base_name=base_name,
        normalized_name=normalized_name,
        resolution=resolution,
        country_code=country_code,
        lang_code=lang_code,
        variant=variant,
        tags=tags,
    )


# Test examples (can be run as: python -m pytest tests/test_channel_parser.py)
if __name__ == "__main__":
    test_cases = [
        "CNN",
        "BBC One HD",
        "Discovery Channel 4K",
        "RTL HD DE",
        "Cartoon Network Kids RU",
        "Eurosport HD +1",
        "Sky News East",
        "NHK World EN",
        "РТР 24",
        "Первый канал HD RU",
    ]
    for name in test_cases:
        parsed = parse_channel_name(name)
        print(f"{name:30} -> {parsed.base_name:20} res={parsed.resolution:4} "
              f"country={parsed.country_code} variant={parsed.variant}")
