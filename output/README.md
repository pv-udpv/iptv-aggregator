# 🎬 IPTV Aggregator - Результаты демо-запуска

Автоматически сгенерировано: 2025-12-24 08:57 MSK

## 📊 Статистика

- **Каналов**: 100
- **Стримов**: 40  
- **Стран**: 41

## 📁 Файлы

### 1. `playlist.m3u`
М3U8 плейлист для IPTV плееров (VLC, Kodi, Perfect Player)

**Использование:**
```bash
# VLC
vlc output/playlist.m3u

# Или открыть URL
vlc https://raw.githubusercontent.com/pv-udpv/iptv-aggregator/main/output/playlist.m3u
```

### 2. `iptv.db`
SQLite база данных с каналами и стримами

**Структура:**
- `channels` - информация о каналах
- `streams` - URLs стримов

**Запросы:**
```sql
-- Все каналы
SELECT * FROM channels;

-- Каналы по стране
SELECT * FROM channels WHERE country = 'ES';

-- Каналы с рабочими стримами
SELECT c.name, s.url 
FROM channels c 
JOIN streams s ON c.id = s.channel_id 
WHERE s.is_working = 1;
```

### 3. `metadata.json`
Метаданные проекта и статистика

## 🚀 Следующие шаги

### Расширение до полной версии:

1. **Загрузить все 38,723 канала**
   ```python
   channels_sample = channels_data  # Убрать [:100]
   ```

2. **Добавить EPG (телепрограмма)**
   ```bash
   docker run -v ./channels.xml:/epg/channels.xml ghcr.io/iptv-org/epg:master
   ```

3. **Fuzzy matching с iptvportal**
   ```python
   python fuzzy_match.py
   ```

4. **Автоматическое обновление**
   ```yaml
   # .github/workflows/update.yml
   schedule:
     - cron: '0 */6 * * *'  # Каждые 6 часов
   ```

## 🔗 Источники данных

- [iptv-org/iptv](https://github.com/iptv-org/iptv) - База каналов
- [iptv-org/api](https://github.com/iptv-org/api) - JSON API
- [iptv-org/epg](https://github.com/iptv-org/epg) - EPG grabber

## 📝 Лицензия

MIT - см. родительский проект