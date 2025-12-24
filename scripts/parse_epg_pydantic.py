#!/usr/bin/env python3
"""
EPG Parser using Pydantic-XML (XMLTV format).

Parse EPG XML files into typed Pydantic models.

Usage:
    python scripts/parse_epg_pydantic.py <epg_file.xml>
    python scripts/parse_epg_pydantic.py epg/cache/cnn.us.xml
"""

import sys
import gzip
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime
from collections import defaultdict

try:
    from pydantic_xml import BaseXmlModel, element, attr
    from pydantic import Field
except ImportError:
    print("ERROR: pydantic-xml not installed")
    print("Install: uv pip install pydantic-xml")
    sys.exit(1)


# ============================================================================
# XMLTV Schema Models
# ============================================================================

class DisplayName(BaseXmlModel, tag='display-name'):
    """Channel display name with optional language."""
    value: str = Field(default='', alias='__text__')
    lang: Optional[str] = attr(name='lang', default=None)


class Icon(BaseXmlModel, tag='icon'):
    """Channel icon/logo."""
    src: str = attr()
    width: Optional[int] = attr(default=None)
    height: Optional[int] = attr(default=None)


class Url(BaseXmlModel, tag='url'):
    """Channel website URL."""
    value: str = Field(default='', alias='__text__')


class Channel(BaseXmlModel, tag='channel'):
    """EPG Channel definition."""
    id: str = attr()
    display_names: List[DisplayName] = element(tag='display-name', default_factory=list)
    icons: List[Icon] = element(tag='icon', default_factory=list)
    urls: List[Url] = element(tag='url', default_factory=list)
    country: Optional[str] = element(default=None)
    language: Optional[str] = element(default=None)

    @property
    def primary_name(self) -> str:
        """Get primary display name (first or any)."""
        if self.display_names:
            return self.display_names[0].value
        return self.id

    @property
    def icon_url(self) -> Optional[str]:
        """Get first icon URL if available."""
        if self.icons:
            return self.icons[0].src
        return None


class Credit(BaseXmlModel, tag='credits'):
    """Programme credits (director, actor, etc)."""
    directors: List[str] = element(tag='director', default_factory=list)
    actors: List[str] = element(tag='actor', default_factory=list)
    writers: List[str] = element(tag='writer', default_factory=list)
    adapters: List[str] = element(tag='adapter', default_factory=list)
    producers: List[str] = element(tag='producer', default_factory=list)
    composers: List[str] = element(tag='composer', default_factory=list)
    editors: List[str] = element(tag='editor', default_factory=list)


class Rating(BaseXmlModel, tag='rating'):
    """Content rating (MPAA, VCHIP, etc)."""
    system: str = attr()
    value: str = element(tag='value', default='')
    icons: List[Icon] = element(tag='icon', default_factory=list)


class StarRating(BaseXmlModel, tag='star-rating'):
    """Star rating (1-5 stars)."""
    system: Optional[str] = attr(default=None)
    value: str = element(tag='value', default='')


class Review(BaseXmlModel, tag='review'):
    """Programme review."""
    type: str = attr()
    source: Optional[str] = attr(default=None)
    reviewer: Optional[str] = attr(default=None)
    lang: Optional[str] = attr(name='lang', default=None)
    value: str = Field(default='', alias='__text__')


class Image(BaseXmlModel, tag='image'):
    """Programme image/poster."""
    type: str = attr()
    size: Optional[str] = attr(default=None)
    orient: Optional[str] = attr(default=None)
    value: str = Field(default='', alias='__text__')


class ArchiveUrl(BaseXmlModel, tag='url'):
    """Video archive URL."""
    system: str = attr()
    value: str = Field(default='', alias='__text__')


class Video(BaseXmlModel, tag='video'):
    """Video information."""
    present: str = attr(default='yes')
    colour: Optional[str] = element(tag='colour', default=None)
    aspect: Optional[str] = element(tag='aspect', default=None)
    quality: Optional[str] = element(tag='quality', default=None)


class Audio(BaseXmlModel, tag='audio'):
    """Audio information."""
    present: str = attr(default='yes')
    stereo: Optional[str] = element(tag='stereo', default=None)


class PreviouslyShown(BaseXmlModel, tag='previously-shown'):
    """When programme was previously shown."""
    start: Optional[str] = attr(default=None)
    channel: Optional[str] = attr(default=None)


class SubTitle(BaseXmlModel, tag='sub-title'):
    """Programme subtitle/episode title."""
    lang: Optional[str] = attr(name='lang', default=None)
    value: str = Field(default='', alias='__text__')


class Description(BaseXmlModel, tag='desc'):
    """Programme description."""
    lang: Optional[str] = attr(name='lang', default=None)
    value: str = Field(default='', alias='__text__')


class Category(BaseXmlModel, tag='category'):
    """Programme category."""
    lang: Optional[str] = attr(name='lang', default=None)
    value: str = Field(default='', alias='__text__')


class Title(BaseXmlModel, tag='title'):
    """Programme title."""
    lang: Optional[str] = attr(name='lang', default=None)
    value: str = Field(default='', alias='__text__')


class Programme(BaseXmlModel, tag='programme'):
    """EPG Programme (broadcast schedule entry)."""
    start: str = attr()
    stop: str = attr()
    channel: str = attr()
    clumpidx: Optional[str] = attr(default=None)
    vpsstart: Optional[str] = attr(default=None)
    vpsstart: Optional[str] = attr(default=None)
    showview: Optional[str] = attr(default=None)
    videoplus: Optional[str] = attr(default=None)
    pdc: Optional[str] = attr(default=None)

    titles: List[Title] = element(tag='title', default_factory=list)
    subtitles: List[SubTitle] = element(tag='sub-title', default_factory=list)
    descriptions: List[Description] = element(tag='desc', default_factory=list)
    categories: List[Category] = element(tag='category', default_factory=list)
    keywords: List[str] = element(tag='keyword', default_factory=list)
    language: Optional[str] = element(tag='language', default=None)
    orig_language: Optional[str] = element(tag='orig-language', default=None)
    length: Optional[str] = element(tag='length', default=None)
    icon: Optional[Icon] = element(tag='icon', default=None)
    url: Optional[str] = element(tag='url', default=None)
    country: Optional[str] = element(tag='country', default=None)
    episode_num: Optional[str] = element(tag='episode-num', default=None)
    video: Optional[Video] = element(tag='video', default=None)
    audio: Optional[Audio] = element(tag='audio', default=None)
    previously_shown: Optional[PreviouslyShown] = element(tag='previously-shown', default=None)
    premiere: Optional[str] = element(tag='premiere', default=None)
    last_chance: Optional[str] = element(tag='last-chance', default=None)
    new: Optional[str] = element(tag='new', default=None)
    subtitles_info: Optional[str] = element(tag='subtitles', default=None)
    rating: Optional[Rating] = element(tag='rating', default=None)
    star_rating: Optional[StarRating] = element(tag='star-rating', default=None)
    review: Optional[Review] = element(tag='review', default=None)
    image: Optional[Image] = element(tag='image', default=None)
    credits: Optional[Credit] = element(tag='credits', default=None)

    @property
    def primary_title(self) -> str:
        """Get primary title."""
        if self.titles:
            return self.titles[0].value
        return 'Unknown'

    @property
    def primary_description(self) -> Optional[str]:
        """Get primary description."""
        if self.descriptions:
            return self.descriptions[0].value
        return None

    def get_start_dt(self) -> datetime:
        """Parse start time (XMLTV format: YYYYMMDDHHmmss +HHMM)."""
        # Format: 20251224000000 +0000
        dt_str = self.start.split()[0]
        return datetime.strptime(dt_str, '%Y%m%d%H%M%S')

    def get_stop_dt(self) -> datetime:
        """Parse stop time."""
        dt_str = self.stop.split()[0]
        return datetime.strptime(dt_str, '%Y%m%d%H%M%S')

    def duration_minutes(self) -> int:
        """Calculate duration in minutes."""
        start = self.get_start_dt()
        stop = self.get_stop_dt()
        return int((stop - start).total_seconds() / 60)


class Tv(BaseXmlModel, tag='tv'):
    """Root XMLTV document."""
    channels: List[Channel] = element(tag='channel', default_factory=list)
    programmes: List[Programme] = element(tag='programme', default_factory=list)


# ============================================================================
# Utilities
# ============================================================================

def load_epg(filepath: Path) -> Tv:
    """Load and parse EPG file (XML or gzipped)."""
    if filepath.suffix == '.gz':
        with gzip.open(filepath, 'rt', encoding='utf-8') as f:
            content = f.read()
    else:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

    return Tv.from_xml(content)


def print_stats(epg: Tv) -> None:
    """Print EPG statistics."""
    print("=" * 70)
    print("📺 EPG Statistics")
    print("=" * 70)
    print()

    print(f"Channels: {len(epg.channels)}")
    print(f"Programmes: {len(epg.programmes)}")
    print()

    if epg.channels:
        print("Channels:")
        for ch in epg.channels[:5]:
            print(f"  {ch.id:20} {ch.primary_name:30} logo={bool(ch.icon_url)}")
        if len(epg.channels) > 5:
            print(f"  ... and {len(epg.channels) - 5} more")

    print()

    if epg.programmes:
        print("Programmes sample:")
        for prog in epg.programmes[:5]:
            start = prog.get_start_dt().strftime('%Y-%m-%d %H:%M')
            duration = prog.duration_minutes()
            print(
                f"  {start} [{duration:3}min] {prog.channel:15} "
                f"{prog.primary_title[:40]}..."
            )

        print()

        # Category stats
        categories = defaultdict(int)
        for prog in epg.programmes:
            for cat in prog.categories:
                categories[cat.value] += 1

        print(f"Categories ({len(categories)}):")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {cat:30}: {count:5}")

    print()
    print("✅ Done!")


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/parse_epg_pydantic.py <epg_file.xml>")
        print()
        print("Examples:")
        print("  python scripts/parse_epg_pydantic.py epg/cache/cnn.us.xml")
        print("  python scripts/parse_epg_pydantic.py epg/cache/bbc1.uk.xml.gz")
        sys.exit(1)

    filepath = Path(sys.argv[1])

    if not filepath.exists():
        print(f"ERROR: File not found: {filepath}")
        sys.exit(1)

    print(f"Parsing EPG: {filepath}")
    print()

    try:
        epg = load_epg(filepath)
        print_stats(epg)
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
