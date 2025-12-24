"""Real EPG grabber for BBC, ITV, and other sources"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional
import re


@dataclass
class EpgProgramme:
    channel_id: str
    title: str
    start: datetime
    stop: datetime
    description: str = ""
    category: str = ""
    icon: str = ""


class BaseEpgScraper:
    """Base class for EPG scrapers"""
    
    def __init__(self, channel_id: str, site_id: str):
        self.channel_id = channel_id
        self.site_id = site_id
    
    async def fetch(self, url: str, headers: dict = None) -> str:
        default_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        if headers:
            default_headers.update(headers)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url, 
                headers=default_headers,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    return await resp.text()
                raise Exception(f"HTTP {resp.status} for {url}")
    
    async def scrape(self, days: int = 7) -> list[EpgProgramme]:
        raise NotImplementedError


class BBCEpgScraper(BaseEpgScraper):
    """Real scraper for BBC schedules"""
    
    BASE_URL = "https://www.bbc.co.uk/schedules"
    
    async def scrape(self, days: int = 3) -> list[EpgProgramme]:  # Limit to 3 days for demo
        programmes = []
        
        for day in range(days):
            date = datetime.now() + timedelta(days=day)
            url = f"{self.BASE_URL}/{self.site_id}/{date:%Y/%m/%d}"
            
            try:
                print(f"   Scraping {self.channel_id} - {date:%Y-%m-%d}...")
                html = await self.fetch(url)
                soup = BeautifulSoup(html, 'html.parser')
                
                # BBC structure: div.broadcast
                for item in soup.select('.broadcast'):
                    try:
                        # Extract time
                        time_elem = item.select_one('.broadcast__time')
                        if not time_elem:
                            continue
                        
                        time_text = time_elem.get_text(strip=True)
                        start_time = self._parse_time(date, time_text)
                        
                        # Extract title
                        title_elem = item.select_one('.programme__title')
                        if not title_elem:
                            continue
                        title = title_elem.get_text(strip=True)
                        
                        # Extract duration (estimate 30 min if not found)
                        duration_elem = item.select_one('.programme__duration')
                        duration_mins = 30
                        if duration_elem:
                            duration_text = duration_elem.get_text(strip=True)
                            match = re.search(r'(\d+)\s*min', duration_text)
                            if match:
                                duration_mins = int(match.group(1))
                        
                        stop_time = start_time + timedelta(minutes=duration_mins)
                        
                        # Extract description
                        desc_elem = item.select_one('.programme__synopsis')
                        description = desc_elem.get_text(strip=True) if desc_elem else ""
                        
                        programmes.append(EpgProgramme(
                            channel_id=self.channel_id,
                            title=title,
                            start=start_time,
                            stop=stop_time,
                            description=description,
                            category="General"
                        ))
                    
                    except Exception as e:
                        print(f"      ⚠️  Failed to parse programme: {e}")
                        continue
                
                print(f"      ✓ Found {len([p for p in programmes if p.start.date() == date.date()])} programmes")
            
            except Exception as e:
                print(f"      ⚠️  Failed to scrape {url}: {e}")
                continue
        
        return programmes
    
    def _parse_time(self, date: datetime, time_str: str) -> datetime:
        """Parse time like '20:00' or '8:00pm'"""
        time_str = time_str.strip().lower()
        
        # Handle 24h format
        match = re.match(r'(\d{1,2}):(\d{2})', time_str)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
            return datetime(date.year, date.month, date.day, hour, minute)
        
        return datetime.now()


class ITVEpgScraper(BaseEpgScraper):
    """Real scraper for ITV schedules"""
    
    BASE_URL = "https://www.itv.com/watch"
    
    async def scrape(self, days: int = 3) -> list[EpgProgramme]:
        programmes = []
        
        for day in range(days):
            date = datetime.now() + timedelta(days=day)
            
            # ITV uses channel names in URLs
            channel_name = self._get_channel_name()
            url = f"{self.BASE_URL}/{channel_name}/schedule/{date:%Y-%m-%d}"
            
            try:
                print(f"   Scraping {self.channel_id} - {date:%Y-%m-%d}...")
                html = await self.fetch(url)
                soup = BeautifulSoup(html, 'html.parser')
                
                # ITV structure varies, try common patterns
                items = soup.select('[data-testid*="programme"]') or soup.select('.schedule-item')
                
                for item in items:
                    try:
                        title_elem = item.select_one('[data-testid*="title"]') or item.select_one('.title')
                        if not title_elem:
                            continue
                        
                        title = title_elem.get_text(strip=True)
                        
                        # Try to extract time
                        time_elem = item.select_one('[data-testid*="time"]') or item.select_one('.time')
                        if time_elem:
                            time_text = time_elem.get_text(strip=True)
                            start_time = self._parse_time(date, time_text)
                        else:
                            continue
                        
                        programmes.append(EpgProgramme(
                            channel_id=self.channel_id,
                            title=title,
                            start=start_time,
                            stop=start_time + timedelta(minutes=30),
                            description="",
                            category="General"
                        ))
                    
                    except Exception as e:
                        continue
                
                print(f"      ✓ Found {len([p for p in programmes if p.start.date() == date.date()])} programmes")
            
            except Exception as e:
                print(f"      ⚠️  Failed to scrape {url}: {e}")
                continue
        
        return programmes
    
    def _get_channel_name(self) -> str:
        mapping = {
            'ITV1.uk': 'itv',
            'ITV2.uk': 'itv2',
            'ITV3.uk': 'itv3',
            'ITV4.uk': 'itv4',
        }
        return mapping.get(self.channel_id, 'itv')
    
    def _parse_time(self, date: datetime, time_str: str) -> datetime:
        match = re.match(r'(\d{1,2}):(\d{2})', time_str)
        if match:
            hour, minute = int(match.group(1)), int(match.group(2))
            return datetime(date.year, date.month, date.day, hour, minute)
        return datetime.now()


class Channel4EpgScraper(BaseEpgScraper):
    """Real scraper for Channel 4"""
    
    BASE_URL = "https://www.channel4.com/tv-guide"
    
    async def scrape(self, days: int = 3) -> list[EpgProgramme]:
        programmes = []
        
        for day in range(days):
            date = datetime.now() + timedelta(days=day)
            url = f"{self.BASE_URL}/{date:%Y-%m-%d}"
            
            try:
                print(f"   Scraping {self.channel_id} - {date:%Y-%m-%d}...")
                html = await self.fetch(url)
                soup = BeautifulSoup(html, 'html.parser')
                
                # Sample parsing - adjust based on actual structure
                for item in soup.select('.schedule-item'):
                    try:
                        title = item.select_one('.title').get_text(strip=True)
                        time_text = item.select_one('.time').get_text(strip=True)
                        
                        match = re.match(r'(\d{1,2}):(\d{2})', time_text)
                        if match:
                            hour, minute = int(match.group(1)), int(match.group(2))
                            start_time = datetime(date.year, date.month, date.day, hour, minute)
                            
                            programmes.append(EpgProgramme(
                                channel_id=self.channel_id,
                                title=title,
                                start=start_time,
                                stop=start_time + timedelta(minutes=30),
                                description=""
                            ))
                    except:
                        continue
                
                print(f"      ✓ Found {len([p for p in programmes if p.start.date() == date.date()])} programmes")
            except Exception as e:
                print(f"      ⚠️  Failed to scrape: {e}")
        
        return programmes


class EpgGrabber:
    """Orchestrator for multiple EPG scrapers"""
    
    SCRAPERS = {
        'bbc.co.uk': BBCEpgScraper,
        'itv.com': ITVEpgScraper,
        'channel4.com': Channel4EpgScraper,
    }
    
    # Default channel mappings
    CHANNEL_MAPPINGS = {
        'BBC1.uk': ('bbc.co.uk', 'bbc_one'),
        'BBC2.uk': ('bbc.co.uk', 'bbc_two'),
        'BBCNews.uk': ('bbc.co.uk', 'bbc_news'),
        'ITV1.uk': ('itv.com', 'itv'),
        'ITV2.uk': ('itv.com', 'itv2'),
        'Channel4.uk': ('channel4.com', 'channel4'),
    }
    
    async def grab_all(
        self,
        channels: list[dict],
        days: int = 3,
        max_concurrent: int = 5
    ) -> list[EpgProgramme]:
        """Parallel scraping with concurrency limit"""
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def scrape_with_limit(channel: dict) -> list[EpgProgramme]:
            async with semaphore:
                site = channel.get('site')
                scraper_cls = self.SCRAPERS.get(site)
                
                if not scraper_cls:
                    return []
                
                try:
                    scraper = scraper_cls(channel['xmltv_id'], channel['site_id'])
                    return await scraper.scrape(days)
                except Exception as e:
                    print(f"   ⚠️  Scraper failed for {channel['xmltv_id']}: {e}")
                    return []
        
        tasks = [scrape_with_limit(ch) for ch in channels]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        all_programmes = []
        for result in results:
            if isinstance(result, list):
                all_programmes.extend(result)
        
        return all_programmes
    
    async def grab_known_channels(self, days: int = 3) -> list[EpgProgramme]:
        """Grab EPG for known UK channels"""
        
        channels = [
            {'xmltv_id': ch_id, 'site': site, 'site_id': site_id}
            for ch_id, (site, site_id) in self.CHANNEL_MAPPINGS.items()
        ]
        
        print(f"\n📡 Grabbing EPG for {len(channels)} channels...")
        return await self.grab_all(channels, days=days)