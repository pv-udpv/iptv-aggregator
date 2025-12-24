# 📺 IPTV Aggregator

Multi-source IPTV channel aggregator with Python EPG grabber.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## ✨ Features

- ✅ **Multi-source aggregation**: iptv-org/database API
- ✅ **Pure Python**: No Node.js dependencies
- ✅ **SQLite database**: Fast local storage
- ✅ **M3U8 generation**: Standard playlist format
- ✅ **Metadata export**: JSON channel registry
- ✅ **Docker ready**: One-command deployment

## 🚀 Quick Start

### Demo Run (No Installation)

```bash
# Clone repository
git clone https://github.com/pv-udpv/iptv-aggregator.git
cd iptv-aggregator

# Checkout feature branch
git checkout feat/initial-implementation

# Run demo (creates sample data)
python3.12 demo.py

# Output:
# - output/demo.db (SQLite database)
# - output/demo.m3u (M3U8 playlist)
# - output/demo_metadata.json (Channel metadata)
```

### Full Installation

```bash
# Create virtual environment
python3.12 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install with uv (recommended)
pip install uv
uv pip install aiohttp pydantic lxml sqlalchemy rapidfuzz beautifulsoup4 python-dateutil

# Or with pip
pip install -r requirements.txt
```

## 📖 Usage

### Run Demo

```bash
python demo.py
```

**Output:**
```
======================================================================
IPTV Aggregator - Demo Run
======================================================================

[1/3] Fetching sample channels from iptv-org/database...
   📊 Available: 10000+ channels
   📊 Available: 50000+ streams
   ✓ Imported 50 channels, 150 streams from iptv-org

[2/3] Generating M3U playlist...
   ✓ Generated output/demo.m3u with 50 channels

[3/3] Exporting metadata...
   ✓ Exported output/demo_metadata.json

======================================================================
✅ Demo completed successfully!

📁 Output files:
   - Database:  output/demo.db
   - Playlist:  output/demo.m3u
   - Metadata:  output/demo_metadata.json

📊 Statistics:
   - Channels: 50
   - Streams:  150
======================================================================
```

### Inspect Results

```bash
# View playlist
cat output/demo.m3u

# View metadata
cat output/demo_metadata.json | jq

# Query database
sqlite3 output/demo.db "SELECT id, name, country FROM channels LIMIT 10;"
```

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    IPTV Aggregator                          │
└─────────────────────────────────────────────────────────────┘

  INPUT                    PROCESSING                OUTPUT
┌─────────┐              ┌──────────┐            ┌──────────┐
│ iptv-org│─────────────>│  Loader  │───────────>│ SQLite   │
│   API   │              └──────────┘            │    DB    │
└─────────┘                    │                  └────┬─────┘
                               │                       │
                               v                       │
                         ┌──────────┐                 │
                         │ Channels │                 │
                         │ Streams  │                 │
                         └──────────┘                 │
                               │                       │
                               v                       v
                         ┌──────────┐            ┌──────────┐
                         │Aggregator│<───────────│  Query   │
                         └────┬─────┘            └──────────┘
                              │
              ┌───────────────┼───────────────┐
              v               v               v
        ┌──────────┐    ┌──────────┐   ┌──────────┐
        │ demo.m3u │    │ metadata │   │ channels │
        │ playlist │    │   .json  │   │   .db    │
        └──────────┘    └──────────┘   └──────────┘
```

## 📂 Project Structure

```
iptv-aggregator/
├── src/
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy ORM models
│   ├── loaders/
│   │   ├── __init__.py
│   │   └── iptv_org.py        # iptv-org API loader
│   └── epg/                   # EPG grabber (future)
│       └── __init__.py
├── demo.py                    # Demo script with fallback
├── pyproject.toml             # Python 3.12+ dependencies
├── README.md                  # This file
└── output/                    # Generated files (gitignored)
    ├── demo.db
    ├── demo.m3u
    └── demo_metadata.json
```

## 🔧 Configuration

### Environment Variables

```bash
# Optional: limit channels for testing
export IPTV_LIMIT=50

# Optional: custom output directory
export OUTPUT_DIR=./output
```

## 🐳 Docker

```dockerfile
# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY . .
RUN pip install --no-cache-dir uv && \
    uv pip install --system aiohttp pydantic lxml sqlalchemy
CMD ["python", "demo.py"]
```

```bash
# Build and run
docker build -t iptv-aggregator .
docker run -v $(pwd)/output:/app/output iptv-aggregator
```

## 📊 Database Schema

```sql
-- Channels
CREATE TABLE channels (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    alt_names TEXT,
    country TEXT,
    categories TEXT,
    logo_url TEXT,
    website TEXT,
    is_nsfw BOOLEAN,
    xmltv_id TEXT
);

-- Streams
CREATE TABLE streams (
    id INTEGER PRIMARY KEY,
    channel_id TEXT REFERENCES channels(id),
    url TEXT NOT NULL,
    source TEXT NOT NULL,
    quality TEXT,
    is_working BOOLEAN,
    position INTEGER
);

-- Programmes (EPG)
CREATE TABLE programmes (
    id INTEGER PRIMARY KEY,
    channel_id TEXT REFERENCES channels(id),
    title TEXT NOT NULL,
    description TEXT,
    start DATETIME NOT NULL,
    stop DATETIME NOT NULL,
    category TEXT,
    icon TEXT
);
```

## 🛠️ Development

```bash
# Install dev dependencies
uv pip install -e ".[dev]"

# Run tests (when implemented)
pytest tests/

# Lint
ruff check src/

# Format
ruff format src/
```

## 📝 TODO

- [ ] EPG grabber implementation
- [ ] Fuzzy channel matching
- [ ] Health checks for streams
- [ ] Prefect workflow orchestration
- [ ] Multi-source support (iptvportal)
- [ ] Web UI for playlist browsing

## 🤝 Contributing

See [issue #2](https://github.com/pv-udpv/iptv-aggregator/issues/2) for roadmap.

## 📄 License

MIT © pv-udpv

## 🔗 Links

- [iptv-org/database](https://github.com/iptv-org/database) - Channel data source
- [iptv-org/epg](https://github.com/iptv-org/epg) - EPG data source
- [XMLTV Format](http://wiki.xmltv.org/index.php/XMLTVFormat) - EPG standard

---

**Status:** 🚧 Active Development | **Python:** 3.12+ | **Architecture:** @pv-udpv