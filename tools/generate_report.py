#!/usr/bin/env python3
"""Generate dataset report with statistics and quality metrics"""
import sys
from pathlib import Path
import pandas as pd
import json
from datetime import datetime


def generate_report(dataset_dir: Path, output_path: Path):
    """Generate markdown report"""
    # Load metadata
    with open(dataset_dir / "metadata.json") as f:
        meta = json.load(f)
    
    # Load datasets
    channels = pd.read_parquet(dataset_dir / "channels.parquet")
    streams = pd.read_parquet(dataset_dir / "streams.parquet")
    programs = pd.read_parquet(dataset_dir / "programs.parquet")
    
    # Build report
    report = []
    report.append("# IPTV Master Dataset Report\n")
    report.append(f"**Generated**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    report.append(f"**Version**: {meta['version']}\n")
    report.append(f"**Build Time**: {meta['built_at']}\n")
    report.append("\n## Dataset Statistics\n")
    report.append(f"- **Channels**: {len(channels):,}\n")
    report.append(f"- **Streams**: {len(streams):,}\n")
    report.append(f"- **Programs**: {len(programs):,}\n")
    
    # Channel breakdown
    if 'country' in channels.columns:
        report.append("\n### Top 10 Countries by Channels\n")
        top_countries = channels['country'].value_counts().head(10)
        for country, count in top_countries.items():
            report.append(f"- {country}: {count:,}\n")
    
    # Quality metrics
    if 'quality_score' in channels.columns:
        avg_quality = channels['quality_score'].mean()
        report.append(f"\n### Quality Metrics\n")
        report.append(f"- Average quality score: {avg_quality:.3f}\n")
        high_quality = len(channels[channels['quality_score'] >= 0.8])
        report.append(f"- High quality channels (≥0.8): {high_quality:,}\n")
    
    # EPG coverage
    channels_with_epg = channels[
        channels['channel_id'].isin(programs['channel_id'])
    ]
    epg_coverage = len(channels_with_epg) / len(channels) * 100
    report.append(f"\n### EPG Coverage\n")
    report.append(f"- Channels with EPG: {len(channels_with_epg):,} ({epg_coverage:.1f}%)\n")
    
    # Write report
    output_path.write_text("".join(report))
    print(f"✓ Report written to {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: generate_report.py <dataset_dir> <output_path>")
        sys.exit(1)
    
    dataset_dir = Path(sys.argv[1])
    output_path = Path(sys.argv[2])
    generate_report(dataset_dir, output_path)
