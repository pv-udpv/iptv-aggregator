#!/usr/bin/env python3
"""Validate IPTVPortal session before data loading."""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

try:
    from iptvportal_loader import IPTVPortalClient
except ImportError:
    print("Error: iptvportal_loader module not found")
    sys.exit(1)


def main():
    session_id = os.getenv("IPTVPORTAL_SESSION_ID")
    
    if not session_id:
        print("Error: IPTVPORTAL_SESSION_ID environment variable not set")
        return False
    
    print("Validating IPTVPortal session...")
    
    try:
        client = IPTVPortalClient(session_id=session_id)
        
        # Test with simple query (limit 1)
        channels = client.get_channels(active_only=True, limit=1)
        
        if channels:
            print(f"✓ Session valid! Test query returned {len(channels)} channel(s)")
            return True
        else:
            print("✗ Session appears valid but returned no data")
            return False
            
    except Exception as e:
        print(f"✗ Session validation failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
