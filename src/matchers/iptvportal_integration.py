#!/usr/bin/env python3
"""
IPTVPortal Integration для IPTV Aggregator
Fuzzy matching каналов из iptv-org с IPTVPortal
"""

import os
import sqlite3
from pathlib import Path
from typing import Any

from iptvportal import IPTVPortalClient, IPTVPortalSettings, QueryService, SQLQueryInput
from iptvportal.exceptions import IPTVPortalError


class IPTVAggregatorMatcher:
    """Сопоставление каналов iptv-org с IPTVPortal tv_channel."""
    
    def __init__(self, session_id: str, db_path: str = "output/iptv_full.db"):
        """
        Args:
            session_id: Session ID для IPTVPortal
            db_path: Путь к SQLite базе с каналами iptv-org
        """
        self.session_id = session_id
        self.db_path = Path(db_path)
        
        # Настройка IPTVPortal клиента
        self.settings = IPTVPortalSettings(
            api_url="https://api.iptvportal.com/v1",
            # Session ID передаётся через headers
        )
        
        self.client = None
        self.service = None
        self.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        # Подключение к локальной базе
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        
        # Подключение к IPTVPortal
        self.client = IPTVPortalClient(self.settings)
        self.client._session_id = self.session_id  # Inject session ID
        self.client.connect()
        
        self.service = QueryService(self.client)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if self.conn:
            self.conn.close()
        if self.client:
            self.client.close()
    
    def get_local_channels(self, limit: int = 100) -> list[dict[str, Any]]:
        """Получить каналы из локальной базы iptv-org."""
        cursor = self.conn.cursor()
        
        query = """
            SELECT 
                c.id,
                c.name,
                c.alt_names,
                c.country,
                c.categories,
                c.logo_url,
                COUNT(s.id) as stream_count
            FROM channels c
            LEFT JOIN streams s ON c.id = s.channel_id
            WHERE s.url IS NOT NULL
            GROUP BY c.id
            ORDER BY stream_count DESC
            LIMIT ?
        """
        
        cursor.execute(query, (limit,))
        
        channels = []
        for row in cursor.fetchall():
            channels.append({
                "id": row["id"],
                "name": row["name"],
                "alt_names": row["alt_names"],
                "country": row["country"],
                "categories": row["categories"],
                "logo_url": row["logo_url"],
                "stream_count": row["stream_count"]
            })
        
        return channels
    
    def search_iptvportal_channel(self, name: str) -> list[dict[str, Any]]:
        """Поиск канала в IPTVPortal по имени."""
        try:
            query_input = SQLQueryInput(
                sql=f"""
                    SELECT id, name, logo_url, country_code
                    FROM tv_channel
                    WHERE name ILIKE '%{name}%'
                    LIMIT 10
                """,
                use_schema_mapping=True,
                use_cache=True
            )
            
            result = self.service.execute_sql(query_input)
            return result.data or []
            
        except IPTVPortalError as e:
            print(f"Error searching for '{name}': {e}")
            return []
    
    def fuzzy_match_all(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        Сопоставить каналы из локальной базы с IPTVPortal.
        
        Returns:
            List of matches with scores
        """
        local_channels = self.get_local_channels(limit)
        matches = []
        
        print(f"Starting fuzzy matching for {len(local_channels)} channels...")
        print()
        
        for i, local_ch in enumerate(local_channels, 1):
            print(f"[{i}/{len(local_channels)}] Matching: {local_ch['name']}")
            
            # Поиск по основному имени
            portal_matches = self.search_iptvportal_channel(local_ch["name"])
            
            if portal_matches:
                best_match = portal_matches[0]
                
                match_record = {
                    "local_id": local_ch["id"],
                    "local_name": local_ch["name"],
                    "portal_id": best_match.get("id"),
                    "portal_name": best_match.get("name"),
                    "confidence": self._calculate_confidence(
                        local_ch["name"], 
                        best_match.get("name", "")
                    ),
                    "stream_count": local_ch["stream_count"],
                    "country": local_ch["country"],
                    "categories": local_ch["categories"]
                }
                
                matches.append(match_record)
                
                print(f"   ✓ Matched with: {best_match.get('name')} "
                      f"(confidence: {match_record['confidence']:.2f})")
            else:
                print(f"   ✗ No matches found")
            
            print()
        
        return matches
    
    def _calculate_confidence(self, name1: str, name2: str) -> float:
        """
        Простой алгоритм расчёта уверенности в совпадении.
        
        В реальности используй: python-Levenshtein, fuzzywuzzy, rapidfuzz
        """
        from difflib import SequenceMatcher
        
        name1_clean = name1.lower().strip()
        name2_clean = name2.lower().strip()
        
        return SequenceMatcher(None, name1_clean, name2_clean).ratio()
    
    def save_matches_to_db(self, matches: list[dict[str, Any]]):
        """Сохранить результаты в таблицу matched_channels."""
        cursor = self.conn.cursor()
        
        # Создаём таблицу для результатов
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS matched_channels (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                local_id TEXT NOT NULL,
                local_name TEXT NOT NULL,
                portal_id INTEGER,
                portal_name TEXT,
                confidence REAL,
                stream_count INTEGER,
                country TEXT,
                categories TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(local_id, portal_id)
            )
        """)
        
        # Вставка результатов
        for match in matches:
            cursor.execute("""
                INSERT OR REPLACE INTO matched_channels
                (local_id, local_name, portal_id, portal_name, 
                 confidence, stream_count, country, categories)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                match["local_id"],
                match["local_name"],
                match.get("portal_id"),
                match.get("portal_name"),
                match["confidence"],
                match["stream_count"],
                match["country"],
                match["categories"]
            ))
        
        self.conn.commit()
        print(f"✓ Saved {len(matches)} matches to database")


def main():
    """Пример использования."""
    
    # Session ID из переменной окружения или напрямую
    session_id = os.environ.get(
        "IPTVPORTAL_SESSION_ID",
        "bbce5e5653cb4c0199e1e398cde99b16"
    )
    
    print("=" * 70)
    print("IPTV AGGREGATOR - IPTVPortal Integration")
    print("=" * 70)
    print()
    print(f"Session ID: {session_id[:20]}...")
    print()
    
    try:
        with IPTVAggregatorMatcher(session_id=session_id) as matcher:
            # Fuzzy match первых 50 каналов
            matches = matcher.fuzzy_match_all(limit=50)
            
            # Статистика
            print("=" * 70)
            print("РЕЗУЛЬТАТЫ:")
            print("=" * 70)
            print(f"Всего обработано: {len(matches)}")
            
            high_confidence = [m for m in matches if m["confidence"] > 0.8]
            print(f"Высокая уверенность (>80%): {len(high_confidence)}")
            
            medium_confidence = [
                m for m in matches 
                if 0.5 < m["confidence"] <= 0.8
            ]
            print(f"Средняя уверенность (50-80%): {len(medium_confidence)}")
            
            # Топ совпадения
            print()
            print("Топ-10 совпадений:")
            sorted_matches = sorted(
                matches, 
                key=lambda x: x["confidence"], 
                reverse=True
            )
            
            for i, match in enumerate(sorted_matches[:10], 1):
                print(f"{i}. {match['local_name']}")
                print(f"   → {match['portal_name']}")
                print(f"   Confidence: {match['confidence']:.2%}")
                print()
            
            # Сохранить в базу
            matcher.save_matches_to_db(matches)
            
    except IPTVPortalError as e:
        print(f"Error: {e}")
        print()
        print("Проверь SESSION_ID и доступ к IPTVPortal API")


if __name__ == "__main__":
    main()
