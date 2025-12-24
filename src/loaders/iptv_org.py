"""Loader for iptv-org/database API"""

import asyncio
import json
import aiohttp
from typing import Any
from sqlalchemy.orm import Session
from src.models import Channel, Stream


class IptvOrgLoader:
    """Load channels and streams from iptv-org/database API"""
    
    API_BASE = "https://iptv-org.github.io/api"
    
    async def fetch_metadata(self) -> dict[str, Any]:
        """Fetch all metadata from iptv-org API"""
        async with aiohttp.ClientSession() as session:
            channels, streams, logos = await asyncio.gather(
                self._fetch_json(session, "channels.json"),
                self._fetch_json(session, "streams.json"),
                self._fetch_json(session, "logos.json")
            )
        
        logos_map = {lg['channel']: lg['url'] for lg in logos}
        
        return {
            'channels': channels,
            'streams': streams,
            'logos_map': logos_map
        }
    
    async def _fetch_json(self, session: aiohttp.ClientSession, endpoint: str) -> list[dict]:
        url = f"{self.API_BASE}/{endpoint}"
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to fetch {endpoint}: {resp.status}")
            return await resp.json()
    
    def populate_database(self, metadata: dict[str, Any], session: Session, limit: int = 100) -> int:
        """Populate SQLite database with channels and streams"""
        
        logos_map = metadata['logos_map']
        
        # Insert channels (limited for demo)
        count = 0
        for ch_data in metadata['channels'][:limit]:
            ch_id = ch_data['id']
            
            channel = Channel(
                id=ch_id,
                name=ch_data['name'],
                alt_names=json.dumps(ch_data.get('alt_names', [])),
                country=ch_data.get('country'),
                categories=json.dumps(ch_data.get('categories', [])),
                logo_url=logos_map.get(ch_id),
                website=ch_data.get('website'),
                is_nsfw=ch_data.get('is_nsfw', False),
                xmltv_id=ch_id
            )
            
            session.merge(channel)
            count += 1
        
        # Insert streams
        stream_count = 0
        for stream_data in metadata['streams']:
            if stream_data['channel'] not in [ch['id'] for ch in metadata['channels'][:limit]]:
                continue
                
            stream = Stream(
                channel_id=stream_data['channel'],
                url=stream_data['url'],
                source="iptv-org",
                is_working=stream_data.get('status') == 'online',
                position=stream_count
            )
            session.add(stream)
            stream_count += 1
        
        session.commit()
        print(f"✓ Imported {count} channels, {stream_count} streams from iptv-org")
        return count