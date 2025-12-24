#!/usr/bin/env python3
"""Demo script with sample data"""

import asyncio
from pathlib import Path
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from src.models import Base, Channel, Stream
from src.loaders.iptv_org import IptvOrgLoader
import json


async def run_demo():
    print("=" * 70)
    print("IPTV Aggregator - Demo Run")
    print("=" * 70)
    
    # Setup
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    db_path = "output/demo.db"
    engine = create_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    
    # Step 1: Load sample data from iptv-org
    print("\n[1/3] Fetching sample channels from iptv-org/database...")
    loader = IptvOrgLoader()
    
    try:
        metadata = await loader.fetch_metadata()
        print(f"   📊 Available: {len(metadata['channels'])} channels")
        print(f"   📊 Available: {len(metadata['streams'])} streams")
        
        with Session(engine) as session:
            loader.populate_database(metadata, session, limit=50)  # Load first 50
    
    except Exception as e:
        print(f"   ⚠️  Failed to fetch from API: {e}")
        print("   Using fallback sample data...")
        
        # Fallback: create sample channels
        with Session(engine) as session:
            sample_channels = [
                Channel(
                    id="BBC1.uk",
                    name="BBC One",
                    country="UK",
                    categories=json.dumps(["general"]),
                    logo_url="https://example.com/bbc1.png",
                    xmltv_id="BBC1.uk"
                ),
                Channel(
                    id="CNN.us",
                    name="CNN",
                    country="US",
                    categories=json.dumps(["news"]),
                    logo_url="https://example.com/cnn.png",
                    xmltv_id="CNN.us"
                ),
            ]
            
            for ch in sample_channels:
                session.merge(ch)
                
                # Add sample stream
                stream = Stream(
                    channel_id=ch.id,
                    url=f"https://example.com/stream/{ch.id}.m3u8",
                    source="demo",
                    is_working=True,
                    position=0
                )
                session.add(stream)
            
            session.commit()
            print(f"   ✓ Created 2 sample channels")
    
    # Step 2: Generate M3U playlist
    print("\n[2/3] Generating M3U playlist...")
    
    with Session(engine) as session:
        stmt = select(Channel).join(Stream).distinct()
        channels = session.execute(stmt).scalars().all()
        
        lines = ["#EXTM3U"]
        lines.append('#EXTM3U url-tvg="http://localhost:8000/guide.xml"')
        
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
                extinf += f' group-title="{cats[0] if cats else "General"}"'
            
            extinf += f',{channel.name}'
            
            lines.append(extinf)
            lines.append(stream.url)
        
        playlist_path = output_dir / "demo.m3u"
        playlist_path.write_text('\n'.join(lines), encoding='utf-8')
        print(f"   ✓ Generated {playlist_path} with {len(channels)} channels")
    
    # Step 3: Export metadata
    print("\n[3/3] Exporting metadata...")
    
    with Session(engine) as session:
        channels = session.query(Channel).all()
        
        data = {
            'version': '1.0',
            'total_channels': len(channels),
            'channels': []
        }
        
        for ch in channels:
            data['channels'].append({
                'id': ch.id,
                'name': ch.name,
                'country': ch.country,
                'logo': ch.logo_url,
                'categories': json.loads(ch.categories) if ch.categories else [],
                'streams_count': len(ch.streams)
            })
        
        metadata_path = output_dir / "demo_metadata.json"
        metadata_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        print(f"   ✓ Exported {metadata_path}")
    
    # Summary
    print("\n" + "=" * 70)
    print("✅ Demo completed successfully!")
    print("\n📁 Output files:")
    print(f"   - Database:  {db_path}")
    print(f"   - Playlist:  {output_dir / 'demo.m3u'}")
    print(f"   - Metadata:  {output_dir / 'demo_metadata.json'}")
    print("\n📊 Statistics:")
    
    with Session(engine) as session:
        channel_count = session.query(Channel).count()
        stream_count = session.query(Stream).count()
        print(f"   - Channels: {channel_count}")
        print(f"   - Streams:  {stream_count}")
    
    print("\n💡 Quick test:")
    print(f"   cat {output_dir / 'demo.m3u'}")
    print(f"   cat {output_dir / 'demo_metadata.json'}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_demo())