# IPTVPortal Integration

Модуль для сопоставления каналов из iptv-org с IPTVPortal через fuzzy matching.

## Установка

```bash
# Клонировать репозиторий
git clone https://github.com/pv-udpv/iptv-aggregator.git
cd iptv-aggregator

# Установить зависимости
uv pip install git+https://github.com/pv-udpv/iptvportal-client.git
```

## Использование

### 1. Получить Session ID

Session ID можно получить через браузер или API:

```python
from iptvportal import IPTVPortalClient, IPTVPortalSettings

settings = IPTVPortalSettings(
    api_url="https://api.iptvportal.com/v1",
    username="your_username",
    password="your_password"
)

with IPTVPortalClient(settings) as client:
    print(f"Session ID: {client._session_id}")
```

### 2. Запустить matching

```bash
export IPTVPORTAL_SESSION_ID='bbce5e5653cb4c0199e1e398cde99b16'
python src/matchers/iptvportal_integration.py
```

### 3. Результаты

Результаты сохраняются в `output/iptv_full.db` в таблицу `matched_channels`:

```sql
SELECT 
    local_name,
    portal_name,
    confidence,
    stream_count
FROM matched_channels
WHERE confidence > 0.8
ORDER BY confidence DESC
LIMIT 10;
```

## Архитектура

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────┐
│  iptv-org API   │────▶│  IPTVAggregator  │◀────│ IPTVPortal  │
│  (channels.json)│     │   Matcher        │     │ (tv_channel)│
└─────────────────┘     └──────────────────┘     └─────────────┘
                                │
                                ▼
                        ┌──────────────┐
                        │ SQLite DB    │
                        │ matched_     │
                        │ channels     │
                        └──────────────┘
```

## Алгоритм matching

1. **Загрузка локальных каналов** из `iptv_full.db`
2. **Поиск в IPTVPortal** по имени канала
3. **Расчёт confidence** через SequenceMatcher
4. **Сохранение результатов** в `matched_channels`

## Confidence Score

- **>80%**: Высокая уверенность (exact match)
- **50-80%**: Средняя уверенность (partial match)
- **<50%**: Низкая уверенность (проверить вручную)

## API Reference

### IPTVAggregatorMatcher

```python
matcher = IPTVAggregatorMatcher(
    session_id="...",
    db_path="output/iptv_full.db"
)

with matcher:
    # Получить локальные каналы
    channels = matcher.get_local_channels(limit=100)
    
    # Поиск в IPTVPortal
    results = matcher.search_iptvportal_channel("BBC One")
    
    # Fuzzy match всех каналов
    matches = matcher.fuzzy_match_all(limit=50)
    
    # Сохранить результаты
    matcher.save_matches_to_db(matches)
```