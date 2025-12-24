# pullrun.sh - Universal Command Runner

## Что это?

**pullrun.sh** — универсальный скрипт для запуска любых команд с автоматическим:
- `git pull origin main`
- Активация `.venv`
- Проверка/установка зависимостей
- Замер времени выполнения

---

## Quick Start

### 1. Сделай исполняемым (один раз)

```bash
cd /opt/pv-udpv/iptv-aggregator
git pull origin main
chmod +x pullrun.sh
```

### 2. Запускай любые команды

```bash
# TVG extraction
./pullrun.sh python scripts/extract_tvg_country.py

# EPG download
./pullrun.sh python scripts/download_epg.py

# M3U generation
./pullrun.sh python scripts/generate_m3u_with_epg.py

# EPG parser test
./pullrun.sh python scripts/parse_epg_pydantic.py epg/cache/cnn.us.xml

# Channel stats
./pullrun.sh python scripts/generate_channel_stats.py

# Fuzzy matching
./pullrun.sh python output/production_fuzzy_matching_v2.py
```

---

## Примеры

### Одна команда

```bash
./pullrun.sh python scripts/download_epg.py
```

**Что происходит:**
1. ✅ Git pull
2. ✅ Activate .venv
3. ✅ Check deps
4. ✅ Run `python scripts/download_epg.py`
5. ✅ Show duration

### Цепочка команд

```bash
./pullrun.sh bash -c "python scripts/download_epg.py && python scripts/generate_m3u_with_epg.py"
```

### С аргументами

```bash
./pullrun.sh python scripts/parse_epg_pydantic.py epg/cache/bbc1.uk.xml
```

### Shell команды

```bash
./pullrun.sh ls -lh playlists/
./pullrun.sh cat stats/epg_stats.json
./pullrun.sh du -sh epg/cache/
```

---

## Что внутри?

```bash
[1/4] Git pull...              # всегда свежий код
[2/4] Checking .venv...        # создаст если нет
[3/4] Activating .venv...      # активирует окружение
[3.5/4] Checking deps...       # установит если чего-то нет
[4/4] Running command...       # выполнит твою команду

✓ Success
⏱  Duration: 15s
```

---

## Частые сценарии

### Full EPG Pipeline

```bash
./pullrun.sh bash -c '
  python scripts/extract_tvg_country.py && 
  python scripts/download_epg.py && 
  python scripts/generate_m3u_with_epg.py
'
```

### Stats Generation

```bash
./pullrun.sh python scripts/generate_channel_stats.py
```

### Test EPG Parser

```bash
./pullrun.sh python scripts/parse_epg_pydantic.py epg/cache/cnn.us.xml
```

### Check Playlists

```bash
./pullrun.sh head -20 playlists/playlist_with_epg.m3u8
```

---

## Features

✅ **Always fresh code** — git pull перед каждым запуском  
✅ **Auto .venv** — активирует или создаст если нет  
✅ **Smart deps check** — установит если чего-то не хватает  
✅ **Duration tracking** — показывает сколько заняло  
✅ **Colored output** — красиво и наглядно  
✅ **Error handling** — exit on error с proper status codes  

---

## Aliases (опционально)

Добавь в `~/.bashrc` или `~/.zshrc`:

```bash
alias pr='./pullrun.sh'
alias pr-epg='./pullrun.sh python scripts/download_epg.py'
alias pr-m3u='./pullrun.sh python scripts/generate_m3u_with_epg.py'
alias pr-stats='./pullrun.sh python scripts/generate_channel_stats.py'
alias pr-tvg='./pullrun.sh python scripts/extract_tvg_country.py'
```

Теперь просто:

```bash
pr python scripts/download_epg.py
pr-epg
pr-m3u
pr-stats
```

---

## Troubleshooting

### Permission denied

```bash
chmod +x pullrun.sh
```

### Git pull fails

```bash
cd /opt/pv-udpv/iptv-aggregator
git status
git stash  # если есть изменения
git pull origin main
```

### Missing dependencies

```bash
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Command not found

```bash
# Всегда запускай из корня проекта
cd /opt/pv-udpv/iptv-aggregator
./pullrun.sh <command>
```

---

## Environment Variables

Можно передавать через:

```bash
IPTVPORTAL_SESSION_ID=xxx ./pullrun.sh python output/dump_tv_channel.py
```

Или экспортировать:

```bash
export IPTVPORTAL_SESSION_ID=xxx
./pullrun.sh python output/dump_tv_channel.py
```

---

## CI/CD Integration

Можно использовать в GitHub Actions:

```yaml
- name: Run EPG sync
  run: |
    chmod +x pullrun.sh
    ./pullrun.sh python scripts/download_epg.py
```

Или в cron:

```bash
0 0 * * * cd /opt/pv-udpv/iptv-aggregator && ./pullrun.sh python scripts/download_epg.py
```

---

## Summary

**Теперь ты всегда знаешь что делать:**

```bash
cd /opt/pv-udpv/iptv-aggregator
./pullrun.sh <любая команда>
```

🚀 Profit!

---

**Last updated:** 2025-12-24
