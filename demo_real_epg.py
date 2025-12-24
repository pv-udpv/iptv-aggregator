#!/usr/bin/env python3
"""Demo with REAL EPG scraping from BBC, ITV, Channel 4"""

import asyncio
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from src.models import Base, Channel, Stream, Programme
from src.loaders.iptv_org import IptvOrgLoader
from src.epg.grabber import EpgGrabber
import json
from datetime import datetime


async def run_demo_with_real_epg():
    print("=" * 70)
    print("IPTV Aggregator - REAL EPG Demo")
    print("=" * 70)
    
    # Setup
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    db_path = "output/real_epg.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    
    # Step 1: Load channels from iptv-org (UK only for demo)
    print("\n[1/4] Fetching UK channels from iptv-org/database...")
    loader = IptvOrgLoader()
    
    try:
        metadata = await loader.fetch_metadata()
        
        # Filter UK channels only
        uk_channels = [ch for ch in metadata['channels'] if ch.get('country') == 'UK'][:20]
        metadata['channels'] = uk_channels
        
        # Filter UK streams
        uk_channel_ids = {ch['id'] for ch in uk_channels}
        metadata['streams'] = [s for s in metadata['streams'] if s['channel'] in uk_channel_ids]
        
        print(f"   📊 Found {len(uk_channels)} UK channels")
        
        with Session(engine) as session:
            loader.populate_database(metadata, session, limit=20)
    
    except Exception as e:
        print(f"   ⚠️  Failed to fetch from API: {e}")
        print("   Creating sample UK channels...")
        
        with Session(engine) as session:
            sample_channels = [
                Channel(
                    id="BBC1.uk",
                    name="BBC One",
                    country="UK",
                    categories=json.dumps(["general"]),
                    xmltv_id="BBC1.uk"
                ),
                Channel(
                    id="BBC2.uk",
                    name="BBC Two",
                    country="UK",
                    categories=json.dumps(["general"]),
                    xmltv_id="BBC2.uk"
                ),
                Channel(
                    id="ITV1.uk",
                    name="ITV1",
                    country="UK",
                    categories=json.dumps(["general"]),
                    xmltv_id="ITV1.uk"
                ),
            ]
            
            for ch in sample_channels:
                session.merge(ch)
                
                stream = Stream(
                    channel_id=ch.id,
                    url=f"https://example.com/{ch.id}.m3u8",
                    source="demo",
                    is_working=True,
                    position=0
                )
                session.add(stream)
            
            session.commit()
            print(f"   ✓ Created 3 sample UK channels")
    
    # Step 2: Grab REAL EPG from BBC, ITV, Channel 4
    print("\n[2/4] 🌐 Scraping REAL EPG data...")
    print("   This may take 30-60 seconds...")
    
    grabber = EpgGrabber()
    
    try:
        programmes = await grabber.grab_known_channels(days=3)  # 3 days of EPG
        print(f"\n   ✅ Collected {len(programmes)} real programmes!")
        
        # Insert into database
        with Session(engine) as session:
            for prog in programmes:
                db_prog = Programme(
                    channel_id=prog.channel_id,
                    title=prog.title,
                    description=prog.description,
                    start=prog.start,
                    stop=prog.stop,
                    category=prog.category,
                    icon=prog.icon
                )
                session.add(db_prog)
            
            session.commit()
            print(f"   ✓ Saved {len(programmes)} programmes to database")
    
    except Exception as e:
        print(f"   ⚠️  EPG scraping failed: {e}")
        programmes = []
    
    # Step 3: Generate M3U with EPG
    print("\n[3/4] Generating M3U playlist...")
    
    with Session(engine) as session:
        stmt = select(Channel).join(Stream).distinct()
        channels = session.execute(stmt).scalars().all()
        
        lines = ["#EXTM3U"]
        lines.append('#EXTM3U url-tvg="http://localhost:8000/epg.xml"')
        
        for channel in channels:
            stream = channel.streams[0] if channel.streams else None
            if not stream:
                continue
            
            extinf = f'#EXTINF:-1'
            extinf += f' tvg-id="{channel.id}"'
            extinf += f' tvg-name="{channel.name}"'
            
            if channel.logo_url:
                extinf += f' tvg-logo="{channel.logo_url}"'
            
            if channel.categories:
                cats = json.loads(channel.categories)
                extinf += f' group-title="{cats[0] if cats else "UK"}"'
            
            extinf += f',{channel.name}'
            
            lines.append(extinf)
            lines.append(stream.url)
        
        playlist_path = output_dir / "uk_with_epg.m3u"
        playlist_path.write_text('\n'.join(lines), encoding='utf-8')
        print(f"   ✓ Generated {playlist_path} with {len(channels)} channels")
    
    # Step 4: Export EPG report
    print("\n[4/4] Generating EPG report...")
    
    with Session(engine) as session:
        channels = session.query(Channel).all()
        programmes_count = session.query(Programme).count()
        
        # Group programmes by channel
        epg_report = {
            'generated': datetime.now().isoformat(),
            'total_channels': len(channels),
            'total_programmes': programmes_count,
            'channels': []
        }
        
        for ch in channels:
            ch_progs = session.query(Programme).filter_by(channel_id=ch.id).all()
            
            if ch_progs:
                sample_prog = ch_progs[0]
                epg_report['channels'].append({
                    'id': ch.id,
                    'name': ch.name,
                    'programmes_count': len(ch_progs),
                    'sample_programme': {
                        'title': sample_prog.title,
                        'start': sample_prog.start.isoformat(),
                        'description': sample_prog.description[:100] if sample_prog.description else ""
                    }
                })
        
        report_path = output_dir / "epg_report.json"
        report_path.write_text(
            json.dumps(epg_report, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        print(f"   ✓ Exported {report_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ REAL EPG Demo completed successfully!")
    print("\n📁 Output files:")
    print(f"   - Database:   {db_path}")
    print(f"   - Playlist:   {output_dir / 'uk_with_epg.m3u'}")
    print(f"   - EPG Report: {output_dir / 'epg_report.json'}")
    print("\n📊 Statistics:")
    
    with Session(engine) as session:
        channel_count = session.query(Channel).count()
        stream_count = session.query(Stream).count()
        programme_count = session.query(Programme).count()
        
        print(f"   - Channels:   {channel_count}")
        print(f"   - Streams:    {stream_count}")
        print(f"   - Programmes: {programme_count}")
        
        if programme_count > 0:
            print("\n📺 Sample EPG data:")
            stmt = select(Programme).order_by(Programme.start).limit(5)
            sample_progs = session.execute(stmt).scalars().all()
            
            for prog in sample_progs:
                print(f"   - [{prog.start:%H:%M}] {prog.channel_id}: {prog.title}")
    
    print("\n💡 Quick test:")
    print(f"   sqlite3 {db_path} \"SELECT channel_id, title, start FROM programmes LIMIT 10;\"")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_demo_with_real_epg())