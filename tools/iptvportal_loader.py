#!/usr/bin/env python3
"""
IPTVPortal JSONSQL API client
Docs: https://iptvportal.ru/doc/api/
"""
import os
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IPTVPortalClient:
    """IPTVPortal JSONSQL API client with session-based auth"""
    
    def __init__(
        self, 
        session_id: str,
        base_url: str = "https://adstat.admin.iptvportal.ru/api/jsonsql/",
        timeout: int = 30
    ):
        self.base_url = base_url
        self.timeout = timeout
        self.session = self._create_session(session_id)
    
    def _create_session(self, session_id: str) -> requests.Session:
        """Create requests session with retry logic and auth header"""
        session = requests.Session()
        
        # IPTVPortal требует специфичный заголовок
        session.headers.update({
            'Iptvportal-Authorization': f'sessionid={session_id}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        
        # Retry strategy для нестабильных сетей
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
    
    def _jsonrpc_request(
        self, 
        method: str, 
        params: Dict[str, Any],
        request_id: int = 1
    ) -> Dict[str, Any]:
        """Execute JSONRPC 2.0 request"""
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params
        }
        
        logger.debug(f"Request: {json.dumps(payload, ensure_ascii=False)}")
        
        try:
            response = self.session.post(
                self.base_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "error" in data:
                raise ValueError(f"API Error: {data['error'].get('message', data['error'])}")
            
            return data.get("result", {})
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error: {e}")
            raise
    
    def select(
        self, 
        table: str,
        columns: List[str] = None,
        where: Dict[str, Any] = None,
        order: List[str] = None,
        limit: int = None,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        SELECT query via JSONRPC
        
        Example:
            client.select(
                table="channels",
                columns=["id", "name", "logo_url"],
                where={"is_active": True},
                order=["name"],
                limit=100
            )
        """
        params = {
            "from": [table],
            "data": columns or ["*"]
        }
        
        if where:
            params["where"] = where
        
        if order:
            params["order"] = order
        
        if limit:
            params["limit"] = limit
            params["offset"] = offset
        
        result = self._jsonrpc_request("select", params)
        return result.get("data", [])
    
    def get_channels(
        self, 
        active_only: bool = True,
        limit: int = None
    ) -> List[Dict[str, Any]]:
        """Fetch all channels from IPTVPortal"""
        where = {"is_active": True} if active_only else None
        
        return self.select(
            table="channels",
            columns=["id", "name", "logo_url", "epg_id", "category", "country"],
            where=where,
            order=["name"],
            limit=limit
        )
    
    def get_channel_stats(
        self, 
        channel_id: int,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get usage statistics for channel"""
        return self.select(
            table="channel_stats",
            where={
                "channel_id": channel_id,
                "date": {
                    ">=": f"NOW() - INTERVAL '{days} days'"
                }
            }
        )


def export_channels_csv(output_path: Path):
    """Export IPTVPortal channels to CSV"""
    import pandas as pd
    
    session_id = os.getenv("IPTVPORTAL_SESSION_ID")
    if not session_id:
        raise ValueError("IPTVPORTAL_SESSION_ID environment variable required")
    
    client = IPTVPortalClient(session_id=session_id)
    
    logger.info("Fetching channels from IPTVPortal...")
    channels = client.get_channels(active_only=True)
    
    df = pd.DataFrame(channels)
    df.to_csv(output_path, index=False, encoding='utf-8')
    
    logger.info(f"✓ Exported {len(df)} channels to {output_path}")
    return df


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default="output/portal_channels.csv")
    args = parser.parse_args()
    
    args.output.parent.mkdir(parents=True, exist_ok=True)
    export_channels_csv(args.output)
