# EPG Integration Guide

## Overview

Система для загрузки и интеграции Electronic Program Guide (EPG) в IPTV плейлисты.

**Компоненты:**
1. TVG ID extraction из M3U метаданных
2. EPG загрузка с провайдеров (xmltv.net, epg-guide)
3. Локальное кеширование
4. M3U плейлист генерация с EPG ссылками

---

## Pipeline

### 1️⃣ TVG ID Extraction (`scripts/extract_tvg_country.py`)

Парсит TVG ID и извлекает country code:

```
tvg-id="3sat.de"       → country_code = "DE"
tvg-id="bbc1.uk"       → country_code = "GB"
tvg-id="cnn.us"        → country_code = "US"
tvg-id="rt.ru"         → country_code = "RU"
```

**Использование:**
```bash
python scripts/extract_tvg_country.py
```

**Output:**
- Updated `output/iptv_full.db` with country_code filled
- Stats: countries extracted count

---

### 2️⃣ EPG Download (`scripts/download_epg.py`)

Загружает EPG для каждого уникального TVG ID с провайдеров:

**Провайдеры:**
- `xmltv.net`: https://epg.xmltv.net/{tvg_id}.xml.gz
- `epg-guide.com`: https://www.epg-guide.com/xmltv/{tvg_id}.xml.gz

**Кеширование:**
- Локальный кеш в `epg/cache/{tvg_id}.xml`
- TTL: 24 часа (переделается свежий после суток)
- При наличии кеша — не скачивает заново

**Использование:**
```bash
python scripts/download_epg.py
```

**Output:**
- `epg/cache/*.xml` — кеши EPG файлов
- `stats/epg_stats.json` — статистика загрузок

**Пример `stats/epg_stats.json`:**
```json
{
  "timestamp": "2025-12-24T12:00:00",
  "total_tvg_ids": 10464,
  "downloaded": 245,
  "cached": 10219,
  "failed": 0,
  "cache_info": {
    "total_files": 10464,
    "total_size_mb": 1234.56,
    "total_programmes": 2543890
  }
}
```

---

### 3️⃣ M3U Generation (`scripts/generate_m3u_with_epg.py`)

Генерирует M3U плейлисты с EPG интеграцией:

**Плейлисты:**

1. **`playlist.m3u8`** — Стандартный IPTV плейлист
   ```
   #EXTM3U
   #EXTINF:-1 tvg-id="cnn.us" tvg-name="CNN" tvg-logo="..." group-title="News",CNN
   http://example.com/stream
   ```

2. **`playlist_with_epg.m3u8`** — С EPG ссылками
   ```
   #EXTINF:-1 tvg-id="cnn.us" ...,CNN
   http://example.com/stream | https://epg.xmltv.net/cnn.us.xml.gz
   ```

3. **`playlist_by_group.m3u8`** — Сгруппировано по категориям
   ```
   # GROUP: News
   #EXTINF:-1 ...,CNN
   ...
   
   # GROUP: Sports
   #EXTINF:-1 ...,ESPN
   ...
   ```

4. **`playlist_best.m3u8`** — Только каналы с EPG
   ```
   (содержит только каналы, у которых найден EPG)
   ```

**Использование:**
```bash
python scripts/generate_m3u_with_epg.py
```

**Output:**
- `playlists/playlist.m3u8`
- `playlists/playlist_with_epg.m3u8`
- `playlists/playlist_by_group.m3u8`
- `playlists/playlist_best.m3u8` (если есть EPG)
- `stats/epg_playlist_stats.json`

---

## Quick Start

### 1. Локальный запуск полного EPG пайплайна

```bash
cd /opt/pv-udpv/iptv-aggregator
source .venv/bin/activate

# TVG extraction
python scripts/extract_tvg_country.py

# EPG download
python scripts/download_epg.py

# M3U generation
python scripts/generate_m3u_with_epg.py
```

### 2. Через GitHub Actions

```bash
# Запусти full_sync (включает и каналы, и EPG)
gh workflow run sync.yml -f sync_type=full_sync

# Или только EPG
gh workflow run sync.yml -f sync_type=epg_only
```

### 3. Проверка результатов

```bash
# Stats
cat stats/epg_stats.json | jq '.cache_info'

# Плейлист
head -20 playlists/playlist_with_epg.m3u8

# Размеры
ls -lh playlists/
ls -lh epg/cache/ | head -10
```

---

## Database Schema

**Таблица `channels`:**
```sql
CREATE TABLE channels (
    id INTEGER PRIMARY KEY,
    name TEXT,
    tvg_id TEXT,              -- TVG ID (e.g., "cnn.us")
    tvg_name TEXT,            -- Channel name from TVG
    tvg_logo TEXT,            -- Logo URL
    group_title TEXT,         -- Category
    url TEXT,                 -- Stream URL
    country_code TEXT,        -- Extracted from TVG ID (e.g., "US")
    resolution TEXT,          -- From taxonomy (sd/hd/fhd/uhd)
    lang_code TEXT,           -- Language code
    variant TEXT,             -- Variant (news/kids/plus/etc)
    ...
);
```

---

## Workflow Schedule

### GitHub Actions (`.github/workflows/sync.yml`)

**Daily:**
- ⏰ 00:00 UTC (03:00 MSK) — EPG sync
  - Download fresh EPG from providers
  - Generate M3U playlists

**Weekly (Sundays):**
- ⏰ 02:00 UTC (05:00 MSK) — Full sync
  - Build IPTV-ORG database
  - Extract taxonomy + country from TVG
  - Download EPG
  - Generate playlists & stats

### Manual Trigger

```bash
# Full sync
gh workflow run sync.yml -f sync_type=full_sync

# Channels only
gh workflow run sync.yml -f sync_type=channels_only

# EPG only
gh workflow run sync.yml -f sync_type=epg_only
```

---

## File Structure

```
.
├── output/
│   └── iptv_full.db          # Channels with metadata & TVG IDs
├── epg/
│   └── cache/
│       ├── cnn.us.xml        # EPG for CNN US
│       ├── bbc1.uk.xml       # EPG for BBC One UK
│       └── ...               # ~10k+ EPG files
├── playlists/
│   ├── playlist.m3u8         # Standard M3U
│   ├── playlist_with_epg.m3u8 # With EPG URLs
│   ├── playlist_by_group.m3u8 # Grouped by category
│   └── playlist_best.m3u8    # Only with EPG
├── scripts/
│   ├── extract_tvg_country.py   # TVG → country extraction
│   ├── download_epg.py          # EPG downloader with cache
│   └── generate_m3u_with_epg.py # M3U generator
└── stats/
    ├── epg_stats.json           # EPG download stats
    └── epg_playlist_stats.json   # Playlist generation stats
```

---

## Statistics

### Current Status

```
Total channels:     10,464
With TVG IDs:       ~10,000
Countries extracted: ~30
EPG cached:         ~10,000 files
Cache size:         ~1.2 GB
Avg prog/channel:   ~250 programmes
```

### M3U Sizes

```
playlist.m3u8              ~2 MB
playlist_with_epg.m3u8    ~15 MB (includes EPG URLs)
playlist_by_group.m3u8    ~3 MB
playlist_best.m3u8        ~1.5 MB (only with EPG)
```

---

## Providers & Limits

### xmltv.net
- **Rate limit:** ~100 req/min
- **Cache:** 24h
- **Availability:** 99%+
- **Format:** XML.GZ

### epg-guide.com
- **Backup provider**
- **Rate limit:** ~50 req/min
- **Cache:** 24h
- **Format:** XML.GZ

---

## Troubleshooting

### No EPG found

```bash
# Check TVG IDs in database
sqlite3 output/iptv_full.db "SELECT COUNT(*) FROM channels WHERE tvg_id IS NOT NULL"

# Check EPG cache
ls -la epg/cache/ | wc -l

# Check download logs
python scripts/download_epg.py --verbose
```

### EPG files too old

```bash
# Force fresh download (clear cache)
rm -rf epg/cache/*
python scripts/download_epg.py
```

### M3U not generating

```bash
# Check database connection
sqlite3 output/iptv_full.db "SELECT COUNT(*) FROM channels"

# Check playlists dir
mkdir -p playlists/
python scripts/generate_m3u_with_epg.py
```

---

## Performance

### Timing (local MacBook Pro M1)

```
TVG extraction:     ~2 sec
EPG download:       ~30 sec (with cache)
M3U generation:     ~3 sec
Total:              ~35 sec
```

### GitHub Actions

```
EPG sync job:       ~2-3 min
Channel sync job:   ~5-10 min
Total workflow:     ~15 min
```

---

## Future Enhancements

- [ ] XMLTV merge (combine EPG from multiple providers)
- [ ] Dedupe programmes across providers
- [ ] Add streaming quality detection (from stream info)
- [ ] EPG validity checking & fallback
- [ ] Support for .ts/.m3u8 playlist formats
- [ ] CloudFlare workers for EPG caching
- [ ] Scheduled EPG updates per provider

---

**Last updated:** 2025-12-24
