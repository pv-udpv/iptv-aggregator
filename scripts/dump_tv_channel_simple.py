#!/usr/bin/env python3
"""
Простой дамп tv_channel из IPTVPortal используя iptvportal-client
"""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime


def dump_tv_channel_simple():
    """Дамп tv_channel используя прямые запросы."""
    
    print("=" * 70)
    print("IPTVPortal TV_CHANNEL - ПРОСТОЙ ДАМП")
    print("=" * 70)
    print()
    
    # Чита из README iptvportal-client о том, что нужны эти переменные
    session_id = os.environ.get("IPTVPORTAL_SESSION_ID")
    domain = os.environ.get("IPTVPORTAL_DOMAIN", "")
    username = os.environ.get("IPTVPORTAL_USERNAME", "")
    password = os.environ.get("IPTVPORTAL_PASSWORD", "")
    
    # Если нет session_id, попробуем через клиент
    if not session_id and (username and password and domain):
        print("Сессия ID не найден, пробую авторизоваться...")
        print(f"Domain: {domain}")
        print(f"Username: {username}")
        print()
        
        try:
            from iptvportal import IPTVPortalClient, IPTVPortalSettings
            
            settings = IPTVPortalSettings(
                domain=domain,
                username=username,
                password=password
            )
            
            with IPTVPortalClient(settings) as client:
                session_id = client._session_id
                print(f"✅ Авторизация успешна!")
                print(f"   Session ID: {session_id[:20]}...")
                print()
        except Exception as e:
            print(f"❌ Ошибка авторизации: {e}")
            return
    
    elif not session_id:
        # Используем заглушку для демо
        session_id = "bbce5e5653cb4c0199e1e398cde99b16"
        print(f"⚠️  Используется демо Session ID: {session_id[:20]}...")
        print()
    
    # Используем iptvportal-client
    try:
        from iptvportal import IPTVPortalClient, IPTVPortalSettings
        from iptvportal.jsonsql.builder import QueryBuilder
        
        # Настройки (если есть domain)
        if domain:
            settings = IPTVPortalSettings(domain=domain)
        else:
            # Пробуем с дефолтными настройками
            settings = IPTVPortalSettings()
        
        print("📡 Подключение к IPTVPortal...")
        
        with IPTVPortalClient(settings) as client:
            # Inject session ID если есть
            if session_id:
                client._session_id = session_id
            
            # Простой запрос SELECT * FROM tv_channel
            query = QueryBuilder()
            
            # Пробуем получить все каналы
            print("   Запрос: SELECT * FROM tv_channel ORDER BY id")
            print()
            
            result = client.execute({
                "jsonrpc": "2.0",
                "id": 1,
                "method": "select",
                "params": {
                    "data": ["*"],
                    "from": "tv_channel",
                    "order_by": ["id"]
                }
            })
            
            channels = result if isinstance(result, list) else []
            
            print(f"✅ Получено каналов: {len(channels)}")
            print()
            
            if not channels:
                print("⚠️  Пустой результат. Проверь:")
                print("   - SESSION_ID валиден")
                print("   - DOMAIN правильный")
                print("   - Доступ к таблице tv_channel")
                return
            
            # Сохраняем
            output_path = Path("output/iptvportal")
            output_path.mkdir(parents=True, exist_ok=True)
            
            # JSON
            json_path = output_path / "tv_channel_full.json"
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(channels, f, indent=2, ensure_ascii=False)
            
            print(f"💾 JSON сохранён: {json_path}")
            
            # SQLite
            db_path = output_path / "tv_channel_full.db"
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            
            # Создаём таблицу
            if channels:
                fields = list(channels[0].keys())
                
                field_defs = []
                for field in fields:
                    if field == 'id':
                        field_defs.append(f"{field} INTEGER PRIMARY KEY")
                    elif field in ['archive_days', 'position']:
                        field_defs.append(f"{field} INTEGER")
                    elif field in ['is_catchup', 'is_active', 'is_locked']:
                        field_defs.append(f"{field} BOOLEAN")
                    else:
                        field_defs.append(f"{field} TEXT")
                
                create_sql = f"""
                    CREATE TABLE IF NOT EXISTS tv_channel (
                        {', '.join(field_defs)}
                    )
                """
                
                cursor.execute(create_sql)
                
                # Вставка
                placeholders = ', '.join(['?' for _ in fields])
                insert_sql = f"""
                    INSERT OR REPLACE INTO tv_channel 
                    ({', '.join(fields)}) 
                    VALUES ({placeholders})
                """
                
                for ch in channels:
                    values = [ch.get(f) for f in fields]
                    cursor.execute(insert_sql, values)
                
                conn.commit()
                
                print(f"💾 SQLite сохранён: {db_path}")
                print()
            
            # Статистика
            print("=" * 70)
            print("📊 СТАТИСТИКА:")
            print("=" * 70)
            print()
            
            if channels:
                first = channels[0]
                print(f"Полей: {len(first)}")
                print()
                print("Поля:")
                for i, field in enumerate(first.keys(), 1):
                    print(f"  {i:2d}. {field}")
                
                print()
                print("Первые 5 каналов:")
                for i, ch in enumerate(channels[:5], 1):
                    name = ch.get('name', 'Unknown')
                    ch_id = ch.get('id', 'N/A')
                    country = ch.get('country_code', 'N/A')
                    print(f"  {i}. [{ch_id:5}] {name:40s} ({country})")
                
                # Страны
                country_stats = {}
                for ch in channels:
                    cc = ch.get('country_code', 'Unknown')
                    country_stats[cc] = country_stats.get(cc, 0) + 1
                
                print()
                print(f"Стран: {len(country_stats)}")
                
                sorted_c = sorted(country_stats.items(), key=lambda x: x[1], reverse=True)
                print()
                print("Топ-10 стран:")
                for country, count in sorted_c[:10]:
                    print(f"  {country:3s}: {count:4d} каналов")
            
            print()
            print("=" * 70)
            print("✅ ДАМП ЗАВЕРШЁН!")
            print("=" * 70)
            
            conn.close()
            
    except ImportError:
        print("❌ iptvportal-client не установлен!")
        print()
        print("Установи:")
        print("  uv pip install git+https://github.com/pv-udpv/iptvportal-client.git")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    dump_tv_channel_simple()
