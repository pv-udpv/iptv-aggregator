#!/usr/bin/env python3
"""Validate master dataset integrity"""
import sys
from pathlib import Path
import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


def validate(dataset_dir: Path) -> bool:
    """Run validation rules on master dataset"""
    errors = []
    warnings = []
    
    try:
        # Load datasets
        logger.info("Loading datasets...")
        channels = pd.read_parquet(dataset_dir / "channels.parquet")
        streams = pd.read_parquet(dataset_dir / "streams.parquet")
        programs = pd.read_parquet(dataset_dir / "programs.parquet")
        
        # Rule 1: All stream.channel must exist in channels
        orphan_streams = streams[~streams['channel'].isin(channels['channel_id'])]
        if len(orphan_streams) > 0:
            errors.append(f"❌ {len(orphan_streams)} orphan streams (no matching channel)")
        
        # Rule 2: Programs.channel_id must exist
        orphan_programs = programs[~programs['channel_id'].isin(channels['channel_id'])]
        if len(orphan_programs) > 0:
            errors.append(f"❌ {len(orphan_programs)} orphan programs")
        
        # Rule 3: Quality scores in valid range
        if 'quality_score' in channels.columns:
            invalid_scores = channels[
                (channels['quality_score'] < 0) | (channels['quality_score'] > 1)
            ]
            if len(invalid_scores) > 0:
                errors.append(f"❌ {len(invalid_scores)} invalid quality_scores")
        
        # Rule 4: No duplicate channel IDs
        if channels['channel_id'].duplicated().any():
            errors.append("❌ Duplicate channel_ids found")
        
        # Warnings
        channels_without_streams = channels[
            ~channels['channel_id'].isin(streams['channel'])
        ]
        if len(channels_without_streams) > 0:
            warnings.append(
                f"⚠️  {len(channels_without_streams)} channels without streams"
            )
        
        channels_without_epg = channels[
            ~channels['channel_id'].isin(programs['channel_id'])
        ]
        if len(channels_without_epg) > 0:
            warnings.append(
                f"⚠️  {len(channels_without_epg)} channels without EPG data"
            )
        
        # Report
        if errors:
            logger.error("\n".join(errors))
        if warnings:
            logger.warning("\n".join(warnings))
        
        if not errors:
            logger.info("✅ All validation checks passed")
            logger.info(f"   - {len(channels)} channels")
            logger.info(f"   - {len(streams)} streams")
            logger.info(f"   - {len(programs)} programs")
            return True
        else:
            return False
            
    except Exception as e:
        logger.error(f"Validation failed: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: validate_dataset.py <dataset_dir>")
        sys.exit(1)
    
    dataset_dir = Path(sys.argv[1])
    sys.exit(0 if validate(dataset_dir) else 1)
