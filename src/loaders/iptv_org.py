"""Loader for iptv-org/database API."""

import asyncio
import re
from pathlib import Path
from typing import Any

import aiohttp

from ..models import Channel, Stream, StreamQuality


class IptvOrgLoader:
    """Fetch channels and streams from iptv-org/database API."""

    API_BASE = "https://iptv-org.github.io/api"
    GITHUB_RAW = "https://raw.githubusercontent.com/iptv-org/iptv/master"

    def __init__(self, cache_dir: Path = Path("cache")):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(exist_ok=True)

    async def fetch_channels(self) -> list[dict[str, Any]]:
        """Fetch channels.json from API."""
        url = f"{self.API_BASE}/channels.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def fetch_streams(self) -> list[dict[str, Any]]:
        """Fetch streams.json from API."""
        url = f"{self.API_BASE}/streams.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def fetch_guides(self) -> list[dict[str, Any]]:
        """Fetch guides.json (EPG mappings)."""
        url = f"{self.API_BASE}/guides.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                resp.raise_for_status()
                return await resp.json()

    async def fetch_logos(self) -> dict[str, str]:
        """Fetch logos.json and return channel_id -> logo_url mapping."""
        url = f"{self.API_BASE}/logos.json"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                resp.raise_for_status()
                logos = await resp.json()
                return {logo["channel"]: logo["src"] for logo in logos}

    async def fetch_all(self) -> dict[str, Any]:
        """Fetch all metadata in parallel."""
        channels, streams, guides, logos = await asyncio.gather(
            self.fetch_channels(),
            self.fetch_streams(),
            self.fetch_guides(),
            self.fetch_logos(),
        )
        return {
            "channels": channels,
            "streams": streams,
            "guides": guides,
            "logos": logos,
        }

    def build_channels(self, metadata: dict[str, Any]) -> list[Channel]:
        """Convert API data to Channel objects."""
        channels_data = metadata["channels"]
        streams_data = metadata["streams"]
        logos_map = metadata["logos"]
        guides_map = {g["channel"]: g for g in metadata["guides"]}

        # Build streams lookup: channel_id -> [streams]
        streams_by_channel: dict[str, list[dict[str, Any]]] = {}
        for stream in streams_data:
            ch_id = stream["channel"]
            if ch_id not in streams_by_channel:
                streams_by_channel[ch_id] = []
            streams_by_channel[ch_id].append(stream)

        # Build Channel objects
        channels = []
        for ch_data in channels_data:
            ch_id = ch_data["id"]
            
            # Parse alt_names
            alt_names = ch_data.get("alt_names", [])
            if isinstance(alt_names, str):
                alt_names = [n.strip() for n in alt_names.split("|") if n.strip()]
            
            # Parse categories
            categories = ch_data.get("categories", [])
            if isinstance(categories, str):
                categories = [c.strip() for c in categories.split(";") if c.strip()]
            group = categories[0] if categories else "Misc"

            # Build streams
            streams = []
            for s in streams_by_channel.get(ch_id, []):
                streams.append(
                    Stream(
                        url=s["url"],
                        source="iptv-org",
                        quality=StreamQuality.AUTO,
                    )
                )

            # EPG ID from guides
            epg_id = guides_map.get(ch_id, {}).get("site_id")

            channel = Channel(
                id=ch_id,
                name=ch_data["name"],
                alt_names=alt_names,
                group=group,
                logo=logos_map.get(ch_id),
                country=ch_data.get("country", "XX"),
                is_nsfw=ch_data.get("is_nsfw", False),
                streams=streams,
                epg_id=epg_id,
                website=ch_data.get("website"),
                network=ch_data.get("network"),
                owners=ch_data.get("owners"),
            )
            channels.append(channel)

        return channels
