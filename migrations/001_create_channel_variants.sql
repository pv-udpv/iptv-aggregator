-- Migration: Add base channels and variants tables
-- Purpose: Support channel normalization with variant grouping
-- Author: GitHub Actions
-- Date: 2025-12-24

-- Base channels table (canonical representation)
CREATE TABLE IF NOT EXISTS channels_base (
    canonical_id TEXT PRIMARY KEY,          -- Slugified base name (e.g., "bbc-one")
    base_name TEXT NOT NULL,                -- Normalized name (e.g., "BBC One")
    network TEXT,                           -- Network/broadcaster
    country TEXT,                           -- Primary country (ISO 3166-1)
    category TEXT,                          -- Genre/category
    
    -- Aggregated metadata from best variant
    logo_url TEXT,
    website TEXT,
    
    -- Variant statistics
    total_variants INTEGER DEFAULT 0,
    has_hd INTEGER DEFAULT 0,               -- Boolean: any HD variant exists
    has_uhd INTEGER DEFAULT 0,              -- Boolean: any UHD/4K variant exists
    epg_coverage_pct REAL,                  -- % of variants with EPG data
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Channel variants table (one-to-many with base)
CREATE TABLE IF NOT EXISTS channel_variants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_id TEXT NOT NULL,             -- FK to channels_base
    
    -- Source identification
    source TEXT NOT NULL,                   -- "iptv-org" | "iptvportal"
    source_id TEXT NOT NULL,                -- Original ID from source
    original_name TEXT NOT NULL,            -- Original channel name
    
    -- Extracted variant attributes
    quality TEXT,                           -- "sd", "hd", "fhd", "uhd", "4k", "8k"
    region TEXT,                            -- ISO 3166-1 alpha-2 ("us", "uk", "br")
    language TEXT,                          -- ISO 639-3 ("eng", "rus", "esp")
    feed TEXT,                              -- "east", "west", "+1", "+2"
    technical TEXT,                         -- "hevc", "avc", "h264", "h265"
    
    -- Quality metrics
    is_primary INTEGER DEFAULT 0,          -- Boolean: best quality variant
    normalization_confidence REAL,          -- 0.0-1.0
    
    -- Timestamps
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (canonical_id) REFERENCES channels_base(canonical_id) ON DELETE CASCADE,
    UNIQUE(source, source_id)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_variants_canonical 
    ON channel_variants(canonical_id);

CREATE INDEX IF NOT EXISTS idx_variants_quality 
    ON channel_variants(canonical_id, quality);

CREATE INDEX IF NOT EXISTS idx_variants_source 
    ON channel_variants(source, source_id);

CREATE INDEX IF NOT EXISTS idx_variants_primary 
    ON channel_variants(canonical_id, is_primary);

-- View: Channels with primary variant info
CREATE VIEW IF NOT EXISTS channels_master AS
SELECT 
    b.canonical_id,
    b.base_name,
    b.network,
    b.country,
    b.category,
    
    -- Primary variant (best quality)
    v_primary.source_id as primary_source_id,
    v_primary.source as primary_source,
    v_primary.original_name as primary_name,
    v_primary.quality as primary_quality,
    v_primary.region as primary_region,
    
    -- Variant statistics
    b.total_variants,
    b.has_hd,
    b.has_uhd,
    b.epg_coverage_pct,
    
    -- Metadata
    b.logo_url,
    b.website,
    b.updated_at
    
FROM channels_base b
LEFT JOIN channel_variants v_primary 
    ON b.canonical_id = v_primary.canonical_id 
    AND v_primary.is_primary = 1;

-- View: All variants with base channel info
CREATE VIEW IF NOT EXISTS channel_variants_full AS
SELECT 
    v.id,
    v.canonical_id,
    v.source,
    v.source_id,
    v.original_name,
    
    -- Base channel data
    b.base_name,
    b.network,
    b.country,
    b.category,
    
    -- Variant attributes
    v.quality,
    v.region,
    v.language,
    v.feed,
    v.technical,
    
    -- Flags
    v.is_primary,
    v.normalization_confidence,
    
    -- Metadata
    b.logo_url,
    b.website
    
FROM channel_variants v
INNER JOIN channels_base b ON v.canonical_id = b.canonical_id;

-- Trigger: Update base channel timestamp on variant change
CREATE TRIGGER IF NOT EXISTS update_base_timestamp
AFTER INSERT ON channel_variants
FOR EACH ROW
BEGIN
    UPDATE channels_base 
    SET updated_at = CURRENT_TIMESTAMP,
        total_variants = total_variants + 1
    WHERE canonical_id = NEW.canonical_id;
END;

-- Trigger: Update quality flags on variant insert
CREATE TRIGGER IF NOT EXISTS update_quality_flags
AFTER INSERT ON channel_variants
FOR EACH ROW
BEGIN
    UPDATE channels_base
    SET has_hd = CASE 
            WHEN NEW.quality IN ('hd', 'fhd') THEN 1 
            ELSE has_hd 
        END,
        has_uhd = CASE 
            WHEN NEW.quality IN ('uhd', '4k', '8k') THEN 1 
            ELSE has_uhd 
        END
    WHERE canonical_id = NEW.canonical_id;
END;
