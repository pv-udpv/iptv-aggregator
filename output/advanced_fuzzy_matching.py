#!/usr/bin/env python3
"""
Advanced Fuzzy Matching с rapidfuzz и нормализацией
- Rapidfuzz для скорости (10-15x faster)
- Экстракция quality tags (SD/HD/UHD/4K)
- Экстракция country codes
- Нормализация имён каналов
"""

import json
import sqlite3
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import time

try:
    from rapidfuzz import fuzz, process
except ImportError:
    print("ERROR: rapidfuzz не установлен")
    print("Установи: uv pip install rapidfuzz")
    exit(1)

print("=" * 70)
print("ADVANCED FUZZY MATCHING")
print("=" * 70)
print()

# === Паттерны для нормализации ===

# Quality tags
QUALITY_PATTERNS = [
    r'\b(SD|HD|FHD|UHD|4K|8K)\b',
    r'\b(\d{3,4}p)\b',  # 720p, 1080p, 2160p
    r'\bHEVC\b',
]

# Country codes (ISO 3166-1)
COUNTRY_PATTERNS = [
    r'\b([A-Z]{2})\b',  # US, UK, RU, DE, etc.
    r'\(([A-Z]{2})\)',  # (US), (UK)
    r'\[([A-Z]{2})\]',  # [US], [UK]
]

# Common channel suffixes to remove
SUFFIXES = [
    r'\bTV\b',
    r'\bHD\b',
    r'\bPlus\b',
    r'\b\+\b',
    r'\bChannel\b',
]

@dataclass
class ChannelInfo:
    """Распарсенная информация о канале."""
    name: str
    normalized_name: str
    quality: Optional[str] = None
    country: Optional[str] = None
    original_name: str = ""

def extract_quality(name: str) -> Tuple[str, Optional[str]]:
    """
    Извлечь quality tag из имени.
    
    Returns:
        (cleaned_name, quality)
    """
    quality = None
    
    for pattern in QUALITY_PATTERNS:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            quality = match.group(1).upper()
            name = re.sub(pattern, '', name, flags=re.IGNORECASE)
            break
    
    return name.strip(), quality

def extract_country(name: str) -> Tuple[str, Optional[str]]:
    """
    Извлечь country code из имени.
    
    Returns:
        (cleaned_name, country)
    """
    country = None
    
    for pattern in COUNTRY_PATTERNS:
        match = re.search(pattern, name)
        if match:
            potential_country = match.group(1)
            
            # Фильтруем ложные срабатывания (общие сокращения)
            false_positives = {'TV', 'HD', 'SD', 'FM', 'AM', 'BR', 'LA'}
            if potential_country not in false_positives:
                country = potential_country
                name = re.sub(pattern, '', name)
                break
    
    return name.strip(), country

def normalize_name(name: str) -> str:
    """
    Нормализовать имя канала для сравнения.
    
    - Lowercase
    - Remove quality tags
    - Remove country codes
    - Remove common suffixes
    - Remove extra spaces/punctuation
    """
    # Lowercase
    name = name.lower()
    
    # Extract and remove quality
    name, _ = extract_quality(name)
    
    # Extract and remove country
    name, _ = extract_country(name)
    
    # Remove common suffixes
    for suffix in SUFFIXES:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)
    
    # Remove special chars (except spaces)
    name = re.sub(r'[^\w\s]', '', name)
    
    # Normalize spaces
    name = re.sub(r'\s+', ' ', name)
    
    return name.strip()

def parse_channel(name: str) -> ChannelInfo:
    """Полный парсинг канала."""
    original = name
    
    # Extract quality
    name, quality = extract_quality(name)
    
    # Extract country
    name, country = extract_country(name)
    
    # Normalize
    normalized = normalize_name(original)
    
    return ChannelInfo(
        name=name.strip(),
        normalized_name=normalized,
        quality=quality,
        country=country,
        original_name=original
    )

# === Загрузка данных ===

print("[1/4] Загрузка IPTVPortal каналов...")

portal_dump_path = Path("output/tv_channel_full_dump.json")

if not portal_dump_path.exists():
    print(f"ERROR: {portal_dump_path} не найден")
    exit(1)

with open(portal_dump_path, 'r', encoding='utf-8') as f:
    portal_data = json.load(f)

portal_channels = portal_data['records']
print(f"  ✓ Загружено: {len(portal_channels):,} каналов")
print()

# Парсим и создаём индекс
print("  Создание индекса с нормализацией...")

portal_parsed = []
portal_index = {}

for ch in portal_channels:
    name = ch.get('name', '')
    if not name:
        continue
    
    parsed = parse_channel(name)
    parsed_data = {
        'id': ch['id'],
        'original_name': name,
        'parsed': parsed,
        'raw': ch
    }
    
    portal_parsed.append(parsed_data)
    portal_index[parsed.normalized_name] = parsed_data

print(f"  ✓ Индекс создан: {len(portal_index):,} уникальных нормализованных имён")
print()

# Примеры парсинга
print("  Примеры нормализации:")
examples = [
    "BBC One HD (UK)",
    "CNN US 1080p",
    "RT Documentary UHD",
    "Discovery Channel 4K",
    "Fox Sports+ HD"
]

for ex in examples:
    parsed = parse_channel(ex)
    print(f"    {ex:30s} → {parsed.normalized_name:20s} | Q:{parsed.quality or 'None':4s} | C:{parsed.country or 'None'}")

print()

# === Загрузка локальных каналов ===

print("[2/4] Загрузка локальных каналов...")

db_path = Path("output/iptv_full.db")

if not db_path.exists():
    print(f"WARNING: {db_path} не найден, используем mock данные")
    
    local_channels = [
        {'id': 'bbc1.uk', 'name': 'BBC One HD', 'country': 'GB', 'stream_count': 10},
        {'id': 'cnn.us', 'name': 'CNN', 'country': 'US', 'stream_count': 8},
        {'id': 'rt.ru', 'name': 'RT Documentary', 'country': 'RU', 'stream_count': 5},
    ]
else:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            c.id, c.name, c.alt_names, c.country, 
            c.categories, c.logo_url,
            COUNT(s.id) as stream_count
        FROM channels c
        LEFT JOIN streams s ON c.id = s.channel_id
        WHERE s.url IS NOT NULL
        GROUP BY c.id
        HAVING stream_count > 0
        ORDER BY stream_count DESC
    """)
    
    local_channels = [dict(row) for row in cursor.fetchall()]
    conn.close()

print(f"  ✓ Загружено: {len(local_channels):,} каналов")
print()

# Парсим локальные каналы
print("  Парсинг локальных каналов...")

local_parsed = []

for ch in local_channels:
    parsed = parse_channel(ch['name'])
    local_parsed.append({
        'id': ch['id'],
        'original_name': ch['name'],
        'parsed': parsed,
        'raw': ch
    })

print(f"  ✓ Распарсено: {len(local_parsed):,} каналов")
print()

# === Fuzzy Matching ===

print("[3/4] Fuzzy Matching с rapidfuzz...")
print()

def calculate_match_score(local_ch: dict, portal_ch: dict) -> float:
    """
    Рассчитать комплексный score matching.
    
    Компоненты:
    - Name similarity: 70%
    - Country match: 20%
    - Quality match: 10%
    """
    local_parsed = local_ch['parsed']
    portal_parsed = portal_ch['parsed']
    
    # Name similarity (rapidfuzz)
    name_score = fuzz.token_sort_ratio(
        local_parsed.normalized_name,
        portal_parsed.normalized_name
    ) / 100.0
    
    # Country match
    country_score = 0.0
    if local_parsed.country and portal_parsed.country:
        country_score = 1.0 if local_parsed.country == portal_parsed.country else 0.0
    elif not local_parsed.country and not portal_parsed.country:
        country_score = 0.5  # Оба без кода - средний балл
    
    # Quality match
    quality_score = 0.0
    if local_parsed.quality and portal_parsed.quality:
        quality_score = 1.0 if local_parsed.quality == portal_parsed.quality else 0.0
    elif not local_parsed.quality and not portal_parsed.quality:
        quality_score = 0.5
    
    # Weighted sum
    total_score = (
        name_score * 0.7 +
        country_score * 0.2 +
        quality_score * 0.1
    )
    
    return total_score

matches = []
no_matches = []
start_time = time.time()

total = len(local_parsed)
checkpoint = max(1, total // 20)

print(f"Обработка {total:,} каналов...")
print()

for i, local_ch in enumerate(local_parsed, 1):
    # Progress
    if i % checkpoint == 0 or i == 1:
        elapsed = time.time() - start_time
        rate = i / elapsed if elapsed > 0 else 0
        eta = (total - i) / rate if rate > 0 else 0
        progress = (i / total) * 100
        
        print(f"  [{i:,}/{total:,}] {progress:.1f}% | "
              f"Rate: {rate:.0f} ch/s | "
              f"ETA: {eta:.1f}s")
    
    local_parsed_data = local_ch['parsed']
    
    # 1. Exact match в индексе
    exact_match = portal_index.get(local_parsed_data.normalized_name)
    
    if exact_match:
        # Exact match
        match = {
            'local_id': local_ch['id'],
            'local_name': local_ch['original_name'],
            'local_normalized': local_parsed_data.normalized_name,
            'local_quality': local_parsed_data.quality,
            'local_country': local_parsed_data.country,
            'portal_id': exact_match['id'],
            'portal_name': exact_match['original_name'],
            'portal_normalized': exact_match['parsed'].normalized_name,
            'portal_quality': exact_match['parsed'].quality,
            'portal_country': exact_match['parsed'].country,
            'confidence': 1.0,
            'match_type': 'exact',
            'stream_count': local_ch['raw'].get('stream_count', 0)
        }
        matches.append(match)
    else:
        # 2. Rapidfuzz search
        # Готовим список для поиска
        choices = [(ch['parsed'].normalized_name, ch) for ch in portal_parsed]
        
        # Извлекаем топ-1 с rapidfuzz
        result = process.extractOne(
            local_parsed_data.normalized_name,
            choices,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=60  # Минимум 60%
        )
        
        if result:
            matched_name, best_portal, base_score = result[0], result[1], result[2] / 100.0
            
            # Рассчитываем комплексный score
            total_score = calculate_match_score(local_ch, best_portal)
            
            if total_score >= 0.6:  # Порог 60%
                match = {
                    'local_id': local_ch['id'],
                    'local_name': local_ch['original_name'],
                    'local_normalized': local_parsed_data.normalized_name,
                    'local_quality': local_parsed_data.quality,
                    'local_country': local_parsed_data.country,
                    'portal_id': best_portal['id'],
                    'portal_name': best_portal['original_name'],
                    'portal_normalized': best_portal['parsed'].normalized_name,
                    'portal_quality': best_portal['parsed'].quality,
                    'portal_country': best_portal['parsed'].country,
                    'confidence': total_score,
                    'match_type': 'fuzzy',
                    'stream_count': local_ch['raw'].get('stream_count', 0),
                    'name_score': base_score,
                    'country_match': local_parsed_data.country == best_portal['parsed'].country if local_parsed_data.country and best_portal['parsed'].country else None,
                    'quality_match': local_parsed_data.quality == best_portal['parsed'].quality if local_parsed_data.quality and best_portal['parsed'].quality else None
                }
                matches.append(match)
            else:
                no_matches.append({
                    'id': local_ch['id'],
                    'name': local_ch['original_name'],
                    'stream_count': local_ch['raw'].get('stream_count', 0),
                    'best_score': total_score
                })
        else:
            no_matches.append({
                'id': local_ch['id'],
                'name': local_ch['original_name'],
                'stream_count': local_ch['raw'].get('stream_count', 0),
                'best_score': 0.0
            })

elapsed_total = time.time() - start_time

print()
print(f"✓ Matching завершён за {elapsed_total:.1f} сек ({elapsed_total/60:.1f} мин)")
print()

# === Сохранение ===

print("[4/4] Сохранение результатов...")
print()

results_json = {
    'total_local': len(local_parsed),
    'total_portal': len(portal_parsed),
    'matched': len(matches),
    'unmatched': len(no_matches),
    'match_rate': len(matches) / len(local_parsed) * 100 if local_parsed else 0,
    'processing_time_sec': elapsed_total,
    'processing_speed': len(local_parsed) / elapsed_total if elapsed_total > 0 else 0,
    'matches': matches,
    'no_matches': no_matches[:100]
}

with open('output/matching_results.json', 'w', encoding='utf-8') as f:
    json.dump(results_json, f, indent=2, ensure_ascii=False)

print(f"  ✓ JSON: output/matching_results.json")
print()

# Сохранить в SQLite (если база есть)
if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS matched_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            local_id TEXT NOT NULL,
            local_name TEXT NOT NULL,
            local_normalized TEXT,
            local_quality TEXT,
            local_country TEXT,
            portal_id INTEGER,
            portal_name TEXT,
            portal_normalized TEXT,
            portal_quality TEXT,
            portal_country TEXT,
            confidence REAL,
            match_type TEXT,
            stream_count INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(local_id, portal_id)
        )
    """)
    
    # Индексы
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_confidence ON matched_channels(confidence)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_match_type ON matched_channels(match_type)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_quality ON matched_channels(local_quality, portal_quality)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_country ON matched_channels(local_country, portal_country)")
    
    # Вставка
    for match in matches:
        cursor.execute("""
            INSERT OR REPLACE INTO matched_channels
            (local_id, local_name, local_normalized, local_quality, local_country,
             portal_id, portal_name, portal_normalized, portal_quality, portal_country,
             confidence, match_type, stream_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            match['local_id'],
            match['local_name'],
            match['local_normalized'],
            match['local_quality'],
            match['local_country'],
            match['portal_id'],
            match['portal_name'],
            match['portal_normalized'],
            match['portal_quality'],
            match['portal_country'],
            match['confidence'],
            match['match_type'],
            match['stream_count']
        ))
    
    conn.commit()
    conn.close()
    
    print(f"  ✓ SQLite: output/iptv_full.db (таблица matched_channels)")
    print()

# === Статистика ===

print("=" * 70)
print("РЕЗУЛЬТАТЫ")
print("=" * 70)
print()

print(f"Локальные каналы:  {len(local_parsed):,}")
print(f"IPTVPortal каналы: {len(portal_parsed):,}")
print()

print(f"Совпадения:        {len(matches):,} ({len(matches)/len(local_parsed)*100:.1f}%)")
print(f"Не найдено:        {len(no_matches):,} ({len(no_matches)/len(local_parsed)*100:.1f}%)")
print()

print(f"Скорость:          {results_json['processing_speed']:.0f} каналов/сек")
print(f"Время:             {elapsed_total:.1f} сек ({elapsed_total/60:.1f} мин)")
print()

# По типам
exact = [m for m in matches if m['match_type'] == 'exact']
fuzzy = [m for m in matches if m['match_type'] == 'fuzzy']

print(f"Exact matches:     {len(exact):,}")
print(f"Fuzzy matches:     {len(fuzzy):,}")
print()

# По confidence
high = [m for m in matches if m['confidence'] >= 0.9]
medium = [m for m in matches if 0.7 <= m['confidence'] < 0.9]
low = [m for m in matches if m['confidence'] < 0.7]

print("Confidence breakdown:")
print(f"  Высокая (≥90%):  {len(high):,} ({len(high)/len(matches)*100:.1f}%)")
print(f"  Средняя (70-89%): {len(medium):,} ({len(medium)/len(matches)*100:.1f}%)")
print(f"  Низкая (<70%):   {len(low):,} ({len(low)/len(matches)*100:.1f}%)")
print()

# Quality extraction stats
with_quality = [m for m in matches if m['local_quality'] or m['portal_quality']]
quality_match = [m for m in matches if m['local_quality'] and m['portal_quality'] and m['local_quality'] == m['portal_quality']]

print("Quality tags:")
print(f"  Извлечено:       {len(with_quality):,}")
print(f"  Совпадений:      {len(quality_match):,}")
print()

# Country extraction stats
with_country = [m for m in matches if m['local_country'] or m['portal_country']]
country_match = [m for m in matches if m['local_country'] and m['portal_country'] and m['local_country'] == m['portal_country']]

print("Country codes:")
print(f"  Извлечено:       {len(with_country):,}")
print(f"  Совпадений:      {len(country_match):,}")
print()

# Топ-20 совпадений
print("Топ-10 совпадений:")
print()

sorted_matches = sorted(matches, key=lambda x: (x['confidence'], x['stream_count']), reverse=True)

for i, m in enumerate(sorted_matches[:10], 1):
    quality_str = f"Q:{m['local_quality'] or '?'}→{m['portal_quality'] or '?'}" if m['local_quality'] or m['portal_quality'] else ""
    country_str = f"C:{m['local_country'] or '?'}→{m['portal_country'] or '?'}" if m['local_country'] or m['portal_country'] else ""
    
    print(f"{i:2d}. {m['local_name']}")
    print(f"    → {m['portal_name']}")
    print(f"    Conf: {m['confidence']:.2%} | Type: {m['match_type']} | {quality_str} | {country_str}")
    print()

print("=" * 70)
print("✅ Готово!")
print()
print("Результаты:")
print("  📊 output/matching_results.json")
print("  📊 output/iptv_full.db (таблица matched_channels)")
print()
print("SQL запросы:")
print("  sqlite3 output/iptv_full.db")
print('  > SELECT local_name, portal_name, confidence, local_quality, portal_quality')
print('    FROM matched_channels WHERE confidence > 0.9 LIMIT 10;')
