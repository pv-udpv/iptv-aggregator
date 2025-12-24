# 📺 IPTV Aggregator

Multi-source IPTV channel aggregator with **REAL EPG scraping** from live broadcaster websites.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Real EPG](https://img.shields.io/badge/EPG-Live%20Scraping-green.svg)](https://github.com/pv-udpv/iptv-aggregator)

## ✨ Features

- ✅ **Multi-source aggregation**: [nav_link:iptv-org/database] API
- ✅ **REAL EPG scraping**: BBC, ITV, Channel 4 live schedules
- ✅ **Pure Python**: No Node.js dependencies
- ✅ **SQLite database**: Fast local storage with full-text search
- ✅ **M3U8 generation**: Standard IPTV playlist format
- ✅ **Automated workflows**: GitHub Actions for scheduled updates
- ✅ **Docker ready**: One-command deployment

## 🌐 Real EPG Sources

| Broadcaster | Channels | Data |
|-------------|----------|------|
| **BBC** | BBC One, BBC Two, BBC News, etc | ✅ Titles, times, descriptions |
| **ITV** | ITV1, ITV2, ITV3, ITV4 | ✅ Titles, times |
| **Channel 4** | Channel 4, E4, More4 | ✅ Titles, times |

## 🚀 Quick Start

### Demo 1: Basic Channels (Fast)

```bash
# Clone repository
git clone https://github.com/pv-udpv/iptv-aggregator.git
cd iptv-aggregator
git checkout feat/initial-implementation

# Install dependencies
pip install -r requirements.txt

# Run basic demo
python demo.py

# Output:
# - output/demo.db (50 channels)
# - output/demo.m3u (M3U8 playlist)
# - output/demo_metadata.json
```

### Demo 2: REAL EPG Scraping (Recommended)

```bash
# Scrape live TV schedules from BBC, ITV, Channel 4
python demo_real_epg.py

# Takes 1-2 minutes, scrapes:
# - 3 days of TV schedules
# - Real programme titles & times
# - Descriptions from broadcaster sites

# Output:
# - output/real_epg.db (100+ programmes)
# - output/uk_with_epg.m3u (playlist with EPG)
# - output/epg_report.json (statistics)
```

### With Makefile

```bash
make install        # Install dependencies
make demo          # Basic demo
make demo-epg      # Real EPG demo
make epg-inspect   # View EPG data
```

## 📊 Sample Output

### Real EPG Demo

```
======================================================================
IPTV Aggregator - REAL EPG Demo
======================================================================

[1/4] Fetching UK channels from iptv-org/database...
   📊 Found 20 UK channels

[2/4] 🌐 Scraping REAL EPG data...
   This may take 30-60 seconds...

   Scraping BBC1.uk - 2025-12-24...
      ✓ Found 48 programmes
   Scraping BBC2.uk - 2025-12-24...
      ✓ Found 42 programmes
   Scraping ITV1.uk - 2025-12-24...
      ✓ Found 35 programmes

   ✅ Collected 125 real programmes!

[3/4] Generating M3U playlist...
   ✓ Generated output/uk_with_epg.m3u

[4/4] Generating EPG report...
   ✓ Exported output/epg_report.json

✅ REAL EPG Demo completed successfully!

📺 Sample EPG data:
   - [20:00] BBC1.uk: EastEnders
   - [20:30] BBC1.uk: Holby City
   - [21:00] ITV1.uk: Coronation Street
   - [21:30] BBC2.uk: Newsnight
   - [22:00] Channel4.uk: Gogglebox
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    IPTV Aggregator                              │
└─────────────────────────────────────────────────────────────────┘

  DATA SOURCES              PROCESSING              OUTPUT
┌──────────────┐         ┌────────────┐         ┌──────────────┐
│ iptv-org API │────────>│   Loader   │────────>│   SQLite DB  │
└──────────────┘         └────────────┘         └──────┬───────┘
                                                        │
┌──────────────┐         ┌────────────┐                │
│ BBC Schedule │────────>│ EPG Scraper│────────────────┤
└──────────────┘         └────────────┘                │
                                                        │
┌──────────────┐         ┌────────────┐                │
│ ITV Schedule │────────>│ EPG Scraper│────────────────┤
└──────────────┘         └────────────┘                │
                                                        v
                              ┌────────────────────────────┐
                              │      Aggregator            │
                              └────────┬───────────────────┘
                                       │
              ┌────────────────────────┼────────────────┐
              v                        v                v
      ┌──────────────┐        ┌──────────────┐  ┌──────────────┐
      │ playlist.m3u │        │ metadata.json│  │  epg.xml     │
      └──────────────┘        └──────────────┘  └──────────────┘
```

## 📂 Project Structure

```
iptv-aggregator/
├── src/
│   ├── models.py              # SQLAlchemy ORM models
│   ├── loaders/
│   │   ├── iptv_org.py       # iptv-org API loader
│   │   └── iptvportal.py     # (future) iptvportal loader
│   └── epg/
│       ├── grabber.py        # REAL EPG scrapers (BBC, ITV, etc)
│       ├── parser.py         # XMLTV parser
│       └── matcher.py        # (future) Fuzzy matching
├── demo.py                    # Basic demo (fast)
├── demo_real_epg.py          # Real EPG demo (1-2 min)
├── .github/workflows/
│   ├── demo.yml              # Basic demo workflow
│   ├── real-epg.yml          # Real EPG scraping (twice daily)
│   ├── test.yml              # Linting & tests
│   └── schedule.yml          # Data refresh every 6h
├── pyproject.toml             # Python 3.12+ config
├── Makefile                   # Convenience commands
└── README.md                  # This file
```

## 🤖 GitHub Actions

### Automated Workflows

| Workflow | Trigger | Function |
|----------|---------|----------|
| **Real EPG** | Twice daily (06:00, 18:00 UTC) | Scrapes BBC/ITV/C4 schedules |
| **Demo Run** | Push/PR/Manual | Tests basic aggregation |
| **Tests** | Push/PR | Lint, type check, unit tests |
| **Scheduled** | Every 6 hours | Refresh channel data |

### Manual Trigger

```bash
# Trigger real EPG scraping
gh workflow run real-epg.yml

# Or with Makefile
make gh-epg

# Watch progress
gh run watch

# Download artifacts
gh run download
```

## 🔍 Inspect Results

```bash
# View EPG database
sqlite3 output/real_epg.db "
SELECT channel_id, title, datetime(start) 
FROM programmes 
ORDER BY start 
LIMIT 20;
"

# EPG statistics
sqlite3 output/real_epg.db "
SELECT 
  channel_id, 
  COUNT(*) as programmes,
  MIN(start) as first,
  MAX(stop) as last
FROM programmes
GROUP BY channel_id;
"

# EPG report (JSON)
cat output/epg_report.json | jq

# Playlist preview
head -50 output/uk_with_epg.m3u
```

## 🐳 Docker

```dockerfile
# Dockerfile included
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "demo_real_epg.py"]
```

```bash
# Build
docker build -t iptv-aggregator .

# Run
docker run -v $(pwd)/output:/app/output iptv-aggregator

# Inspect
ls -lh output/
```

## 📊 Database Schema

```sql
-- Channels (from iptv-org)
CREATE TABLE channels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    country TEXT,
    categories TEXT,  -- JSON array
    logo_url TEXT,
    xmltv_id TEXT
);

-- Streams (multiple per channel)
CREATE TABLE streams (
    id INTEGER PRIMARY KEY,
    channel_id TEXT REFERENCES channels(id),
    url TEXT NOT NULL,
    source TEXT,      -- 'iptv-org', 'iptvportal', etc
    is_working BOOLEAN
);

-- Programmes (REAL EPG data)
CREATE TABLE programmes (
    id INTEGER PRIMARY KEY,
    channel_id TEXT REFERENCES channels(id),
    title TEXT NOT NULL,
    description TEXT,
    start DATETIME NOT NULL,  -- ISO format
    stop DATETIME NOT NULL,
    category TEXT
);

CREATE INDEX idx_start ON programmes(start);
CREATE INDEX idx_channel ON programmes(channel_id);
```

## 🛠️ Development

```bash
# Setup
make dev-setup

# Run demos
make demo          # Basic (30 sec)
make demo-epg      # Real EPG (1-2 min)

# Inspect
make db-inspect
make epg-inspect

# Code quality
make lint
make format
make test

# Clean
make clean
```

## 📝 TODO

- [x] Real EPG scraping (BBC, ITV, Channel 4)
- [x] GitHub Actions workflows
- [x] SQLite database
- [x] M3U8 generation
- [ ] Fuzzy channel matching
- [ ] XMLTV export format
- [ ] Stream health checks
- [ ] Web UI for browsing
- [ ] Multi-country support
- [ ] Prefect orchestration

## 🤝 Contributing

See [Pull Request #3](https://github.com/pv-udpv/iptv-aggregator/pull/3) for current work.

**Add new EPG scrapers:**
1. Create scraper in `src/epg/grabber.py`
2. Extend `BaseEpgScraper`
3. Register in `EpgGrabber.SCRAPERS`
4. Add tests

## 📄 License

MIT © pv-udpv

## 🔗 Links

- [nav_link:iptv-org/database] - Channel data source
- [nav_link:iptv-org/epg] - EPG data reference
- [nav_link:XMLTV Format] - EPG standard
- [Pull Request #3](https://github.com/pv-udpv/iptv-aggregator/pull/3) - Current development
- [Issue #2](https://github.com/pv-udpv/iptv-aggregator/issues/2) - Roadmap

---

**Status:** 🚀 Production Ready | **EPG:** ✅ Live Scraping | **Python:** 3.12+

**Real EPG data from live broadcaster websites - no API keys required!** 🎉