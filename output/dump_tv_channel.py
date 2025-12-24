#!/usr/bin/env python3
"""
Дамп tv_channel из IPTVPortal для sync workflow
Этот скрипт вызывается из GitHub Actions workflow (sync.yml)
"""

import os
import json
import sys
from pathlib import Path
from datetime import datetime

try:
    import httpx
except ImportError:
    print("ERROR: httpx not installed. Run: uv pip install httpx")
    sys.exit(1)


def dump_tv_channel():
    """Дамп tv_channel из IPTVPortal используя httpx."""
    
    print("=" * 70)
    print("IPTVPortal TV_CHANNEL - ДАМП")
    print("=" * 70)
    print()
    
    session_id = os.environ.get("IPTVPORTAL_SESSION_ID")
    
    if not session_id:
        print("ERROR: IPTVPORTAL_SESSION_ID not set")
        print("Set environment variable before running:")
        print("  export IPTVPORTAL_SESSION_ID='...'")
        sys.exit(1)
    
    print(f"📡 Using session ID: {session_id[:20]}...")
    print()
    
    try:
        # Используем httpx для прямого запроса
        base_url = "https://iptvportal.pro/api"
        headers = {
            "User-Agent": "IPTV-Aggregator/1.0",
            "Content-Type": "application/json",
        }
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "select",
            "params": {
                "data": ["*"],
                "from": "tv_channel",
                "order_by": ["id"]
            }
        }
        
        # Добавляем session_id в заголовки
        headers["X-Session"] = session_id
        
        print(f"🔄 Requesting: {base_url}")
        print(f"   Payload: select all tv_channel")
        print()
        
        with httpx.Client(timeout=60) as client:
            response = client.post(base_url, json=payload, headers=headers)
            
            print(f"   Status: {response.status_code}")
            
            if response.status_code != 200:
                print(f"   ERROR: {response.text}")
                sys.exit(1)
            
            data = response.json()
            
            # Проверяем результат
            if "error" in data:
                print(f"   ERROR: {data['error']}")
                sys.exit(1)
            
            channels = data.get("result", [])
            print(f"   ✅ Got {len(channels)} channels")
        
        if not channels:
            print()
            print("⚠️  WARNING: Got 0 channels. Check your SESSION_ID.")
            print()
            # Создаём пустой дамп для workflow не упал
            channels = []
        
        # Сохраняем JSON
        output_dir = Path("output")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_path = output_dir / "tv_channel_full_dump.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(channels, f, indent=2, ensure_ascii=False)
        
        print(f"💾 Saved: {json_path}")
        print()
        
        # Статистика
        if channels:
            print("=" * 70)
            print("📊 STATISTICS:")
            print("=" * 70)
            print()
            print(f"Total channels: {len(channels)}")
            
            # Топ страны
            countries = {}
            for ch in channels:
                country = ch.get('country_code', 'Unknown')
                countries[country] = countries.get(country, 0) + 1
            
            print()
            print("Top countries:")
            for country, count in sorted(countries.items(), key=lambda x: x[1], reverse=True)[:10]:
                print(f"  {country:3s}: {count:5d} channels")
            
            print()
            print("Sample channels:")
            for i, ch in enumerate(channels[:5], 1):
                name = ch.get('name', 'Unknown')[:50]
                ch_id = ch.get('id', 'N/A')
                print(f"  {i}. [{ch_id:5}] {name}")
        
        print()
        print("=" * 70)
        print("✅ DONE!")
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    dump_tv_channel()
