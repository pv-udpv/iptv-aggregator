"""Core data models for IPTV aggregator."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class StreamQuality(str, Enum):
    """Stream quality levels."""
    HD = "1080p"
    FHD = "720p"
    SD = "480p"
    AUTO = "auto"


@dataclass
class Stream:
    """Individual stream source."""
    url: str
    source: str  # 'iptv-org', 'iptvportal', 'custom'
    quality: StreamQuality = StreamQuality.AUTO
    user_agent: Optional[str] = None
    referrer: Optional[str] = None
    labels: dict = field(default_factory=dict)  # {'bitrate': 5000, ...}


@dataclass
class Channel:
    """Unified channel representation."""
    id: str  # e.g., "BBC1.uk"
    name: str  # Canonical name
    alt_names: list[str] = field(default_factory=list)  # Aliases
    group: str = "Misc"  # Category
    logo: Optional[str] = None  # Logo URL
    country: str = "XX"  # ISO 3166-1 alpha-2
    is_nsfw: bool = False
    
    # Multi-source streams
    streams: list[Stream] = field(default_factory=list)
    
    # EPG reference
    epg_id: Optional[str] = None  # For guide matching
    website: Optional[str] = None
    network: Optional[str] = None
    owners: Optional[str] = None


@dataclass
class Programme:
    """EPG programme entry."""
    channel_id: str
    title: str
    description: str = ""
    start: Optional[datetime] = None
    stop: Optional[datetime] = None
    category: str = ""
    icon: Optional[str] = None
    rating: Optional[str] = None
    episode_num: Optional[str] = None
