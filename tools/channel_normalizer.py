#!/usr/bin/env python3
"""
Multi-stage channel name normalization for IPTV aggregation.

Handles:
- Quality variants (SD, HD, FHD, UHD, 4K, 8K)
- Region codes (US, UK, BR, RU, etc.)
- Language codes (ENG, RUS, ESP, etc.)
- Time-shift feeds (East, West, +1, +2)
- Technical formats (HEVC, H.264, AAC)

Inspired by IPTV naming patterns and broadcast standards.
"""

import re
import unicodedata
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


class ChannelVariant(Enum):
    """Types of channel variants"""
    QUALITY = "quality"      # HD, FHD, UHD, 4K, SD
    REGION = "region"        # US, UK, BR, RU, etc.
    LANGUAGE = "language"    # ENG, RUS, ESP, etc.
    FEED = "feed"           # East, West, +1, +2
    TECHNICAL = "technical"  # HEVC, H264, AAC


@dataclass
class ChannelNormalized:
    """Normalized channel representation"""
    original_name: str
    base_name: str                    # "BBC One"
    canonical_id: str                 # "bbc-one"
    variants: Dict[str, str] = field(default_factory=dict)  # {"quality": "hd", "region": "uk"}
    confidence: float = 0.0           # 0.0-1.0


class ChannelNormalizer:
    """
    Multi-stage normalization for IPTV channel names.
    
    Examples:
        >>> normalizer = ChannelNormalizer()
        >>> result = normalizer.normalize("NL| NPO 3 FHD HEVC")
        >>> result.base_name
        'NPO 3'
        >>> result.variants
        {'quality': 'fhd', 'region': 'nl', 'technical': 'hevc'}
    """
    
    # Regex patterns for various naming conventions
    PATTERNS = {
        # Quality markers
        "quality": re.compile(
            r'\b(SD|HD|FHD|FULL[ -]?HD|UHD|ULTRA[ -]?HD|4K|8K|HQ|LQ)\b',
            re.IGNORECASE
        ),
        
        # ISO 3166-1 alpha-2 country codes + common variants
        "region": re.compile(
            r'\b(US|USA|UK|GB|BR|RU|DE|FR|IT|ES|NL|BE|PL|SE|NO|FI|DK|CZ|SK|HU|RO|BG|UA|BY|KZ|'
            r'AR|MX|CL|CO|PE|VE|IN|CN|JP|KR|TW|HK|SG|MY|TH|VN|ID|PH|AU|NZ|ZA|EG|NG|KE|MA|TN|DZ|'
            r'SA|AE|IL|TR|IR|IQ|SY|JO|LB|KW|QA|BH|OM|YE|AF|PK|BD|LK|NP|MM|KH|LA|MN|KP)\b',
            re.IGNORECASE
        ),
        
        # ISO 639 language codes (alpha-3)
        "language": re.compile(
            r'\b(ENG|RUS|ESP|POR|FRA|FRE|DEU|GER|ITA|POL|NED|DUT|SWE|NOR|FIN|DAN|CES|CZE|SLK|SLO|'
            r'HUN|RON|RUM|BUL|UKR|BEL|KAZ|ARA|HEB|TUR|PER|FAS|HIN|CHI|ZHO|JPN|KOR|THA|VIE|IND|'
            r'MAL|MSA|BUR|MYA|KHM|LAO|MON)\b',
            re.IGNORECASE
        ),
        
        # Time-shift feeds and regional variants
        "feed": re.compile(
            r'\b(East|West|North|South|Central|Atlantic|Pacific|Mountain|'
            r'\+[1-9]h?|[+-][0-9]{1,2})\b',
            re.IGNORECASE
        ),
        
        # Video/audio codecs and formats
        "technical": re.compile(
            r'\b(HEVC|H\.?264|H\.?265|AVC|VP9|AV1|AAC|AC3|DTS|E?-?AC3|'
            r'MPEG[24]?|DVB-?[TSC]?|ATSC)\b',
            re.IGNORECASE
        ),
        
        # Separators and noise
        "noise": re.compile(
            r'[\[\](){}|:•·\-_]+'
        ),
        
        # Country prefix patterns (e.g., "NL| NPO 3")
        "country_prefix": re.compile(
            r'^[A-Z]{2,3}[|:\s]+',
            re.IGNORECASE
        ),
        
        # Special markers (||CHANNEL|| format)
        "special_markers": re.compile(
            r'\|\|([^|]+)\|\|'
        ),
        
        # Numbers that might be part of channel name vs suffixes
        "trailing_numbers": re.compile(
            r'\s+[0-9]+\s*$'
        )
    }
    
    def normalize(self, channel_name: str) -> ChannelNormalized:
        """
        Full normalization pipeline.
        
        Args:
            channel_name: Original channel name
            
        Returns:
            ChannelNormalized with base_name, canonical_id, and variants
        """
        if not channel_name or not channel_name.strip():
            return ChannelNormalized(
                original_name=channel_name,
                base_name="",
                canonical_id="",
                variants={},
                confidence=0.0
            )
        
        original = channel_name
        name = channel_name.strip()
        variants = {}
        
        # Step 1: Extract special markers (||CHANNEL||)
        special_match = self.PATTERNS["special_markers"].search(name)
        if special_match:
            name = special_match.group(1)
        
        # Step 2: Remove country prefix (NL|, US:, etc.)
        prefix_match = self.PATTERNS["country_prefix"].match(name)
        if prefix_match:
            prefix = prefix_match.group(0).strip('|: \t')
            if len(prefix) <= 3:  # Only if it looks like country code
                variants['region'] = prefix.lower()
            name = self.PATTERNS["country_prefix"].sub("", name)
        
        # Step 3: Extract variants (order matters!)
        # Quality must be extracted before technical (HEVC might contain H)
        for variant_type in ["quality", "technical", "region", "language", "feed"]:
            matches = self.PATTERNS[variant_type].findall(name)
            if matches:
                # Take first match as primary variant
                variant_value = matches[0].lower().replace('.', '').replace(' ', '')
                
                # Normalize common aliases
                variant_value = self._normalize_variant_value(variant_type, variant_value)
                
                if variant_value:
                    variants[variant_type] = variant_value
                
                # Remove all matches from name
                name = self.PATTERNS[variant_type].sub("", name)
        
        # Step 4: Clean noise (brackets, separators, etc.)
        name = self.PATTERNS["noise"].sub(" ", name)
        
        # Step 5: Normalize whitespace
        base_name = " ".join(name.split()).strip()
        
        # Step 6: Generate canonical ID (slugify)
        canonical_id = self._slugify(base_name)
        
        # Step 7: Calculate confidence
        confidence = self._calculate_confidence(original, base_name, variants)
        
        return ChannelNormalized(
            original_name=original,
            base_name=base_name,
            canonical_id=canonical_id,
            variants=variants,
            confidence=confidence
        )
    
    def _normalize_variant_value(self, variant_type: str, value: str) -> str:
        """Normalize variant values to canonical forms"""
        value = value.lower()
        
        # Quality aliases
        if variant_type == "quality":
            quality_map = {
                'fullhd': 'fhd',
                'ultrahd': 'uhd',
                'hq': 'hd',
                'lq': 'sd'
            }
            return quality_map.get(value, value)
        
        # Region aliases
        if variant_type == "region":
            region_map = {
                'usa': 'us',
                'gb': 'uk',
                'ger': 'de',
                'fre': 'fr'
            }
            return region_map.get(value, value)
        
        # Language aliases
        if variant_type == "language":
            lang_map = {
                'fre': 'fra',
                'ger': 'deu',
                'dut': 'nld',
                'cze': 'ces',
                'slo': 'slk',
                'rum': 'ron',
                'chi': 'zho',
                'bur': 'mya'
            }
            return lang_map.get(value, value)
        
        # Technical aliases
        if variant_type == "technical":
            tech_map = {
                'h264': 'avc',
                'h265': 'hevc',
                'eac3': 'ac3'
            }
            return tech_map.get(value, value)
        
        return value
    
    def _slugify(self, text: str) -> str:
        """Convert to URL-safe canonical ID"""
        if not text:
            return ""
        
        # Remove accents
        text = unicodedata.normalize('NFKD', text)
        text = text.encode('ascii', 'ignore').decode('ascii')
        
        # Lowercase and replace spaces/special chars with dash
        text = re.sub(r'[^\w\s-]', '', text.lower())
        text = re.sub(r'[-\s]+', '-', text).strip('-')
        
        return text
    
    def _calculate_confidence(self, original: str, base: str, variants: Dict[str, str]) -> float:
        """
        Calculate confidence score for normalization quality.
        
        Higher score = more confident in the normalization.
        """
        if not base:
            return 0.0
        
        # Base score from length ratio (penalize too much removal)
        length_ratio = len(base) / max(len(original), 1)
        score = length_ratio * 0.6
        
        # Bonus for extracted variants (shows we understood the format)
        variant_bonus = min(len(variants) * 0.08, 0.3)
        score += variant_bonus
        
        # Bonus if base name looks reasonable (3+ chars, has letters)
        if len(base) >= 3 and re.search(r'[a-zA-Z]', base):
            score += 0.1
        
        # Penalty if too much was removed (might be over-normalization)
        if length_ratio < 0.3:
            score *= 0.7
        
        return min(score, 1.0)
    
    def group_variants(self, channels: List[ChannelNormalized]) -> Dict[str, List[ChannelNormalized]]:
        """
        Group channels by canonical_id to identify variants.
        
        Returns:
            {
                "bbc-one": [
                    ChannelNormalized(base="BBC One", variants={"quality": "hd"}),
                    ChannelNormalized(base="BBC One", variants={"quality": "sd"}),
                ]
            }
        """
        groups = defaultdict(list)
        
        for channel in channels:
            if channel.canonical_id:  # Skip empty/invalid
                groups[channel.canonical_id].append(channel)
        
        return dict(groups)
    
    def select_primary_variant(self, variants: List[ChannelNormalized]) -> ChannelNormalized:
        """
        Select primary (best quality) variant from group.
        
        Priority: 8K > UHD/4K > FHD > HD > SD
        """
        if not variants:
            raise ValueError("Cannot select primary from empty variant list")
        
        quality_priority = {
            "8k": 7,
            "uhd": 6,
            "4k": 5,
            "fhd": 4,
            "hd": 3,
            "sd": 2,
            "": 1  # No quality specified
        }
        
        def score_variant(v: ChannelNormalized) -> Tuple[int, float, int]:
            quality = v.variants.get("quality", "")
            quality_score = quality_priority.get(quality, 0)
            
            # Prefer variants with more metadata
            metadata_count = len(v.variants)
            
            return (quality_score, v.confidence, metadata_count)
        
        return max(variants, key=score_variant)


if __name__ == "__main__":
    # Demo usage
    normalizer = ChannelNormalizer()
    
    test_cases = [
        "NL| NPO 3 FHD HEVC",
        "BBC One HD UK",
        "Discovery Channel 4K",
        "||CNN International||",
        "ESPN USA East +1",
        "Первый канал HD RUS",
        "TV5 Monde FHD FRA",
        "[BR] Globo SD H.264",
    ]
    
    print("Channel Normalization Demo")
    print("=" * 80)
    
    for name in test_cases:
        result = normalizer.normalize(name)
        print(f"\nOriginal: {result.original_name}")
        print(f"Base:     {result.base_name}")
        print(f"ID:       {result.canonical_id}")
        print(f"Variants: {result.variants}")
        print(f"Confidence: {result.confidence:.2f}")
