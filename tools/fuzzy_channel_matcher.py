#!/usr/bin/env python3
"""
Enhanced fuzzy channel matcher with pre-normalization.

Features:
- Multi-stage normalization before matching
- Vectorized fuzzy matching (RapidFuzz)
- Base channel + variants grouping
- Match quality classification
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd
import numpy as np
from rapidfuzz import process, fuzz
import logging

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent))
from channel_normalizer import ChannelNormalizer, ChannelNormalized

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class FuzzyChannelMatcher:
    """
    Enhanced fuzzy matcher with channel normalization.
    
    Workflow:
    1. Normalize both datasets (remove SD/HD/region markers)
    2. Fuzzy match on base names (vectorized)
    3. Group by canonical_id
    4. Select best variant per group
    """
    
    def __init__(self, threshold: float = 85.0, max_workers: int = -1):
        """
        Args:
            threshold: Minimum match score (0-100)
            max_workers: CPU cores for parallel processing (-1 = all)
        """
        self.threshold = threshold
        self.max_workers = max_workers
        self.normalizer = ChannelNormalizer()
    
    def match_with_normalization(
        self,
        iptv_org_df: pd.DataFrame,
        portal_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Multi-stage matching with normalization.
        
        Args:
            iptv_org_df: DataFrame with columns ['id', 'name']
            portal_df: DataFrame with columns ['id', 'name']
            
        Returns:
            DataFrame with match results and variant metadata
        """
        # Validate input
        self._validate_dataframe(iptv_org_df, "iptv-org")
        self._validate_dataframe(portal_df, "portal")
        
        # Stage 1: Normalize
        logger.info(f"Normalizing {len(iptv_org_df)} iptv-org channels...")
        iptv_normalized = [
            self.normalizer.normalize(str(name)) 
            for name in iptv_org_df['name']
        ]
        
        logger.info(f"Normalizing {len(portal_df)} portal channels...")
        portal_normalized = [
            self.normalizer.normalize(str(name)) 
            for name in portal_df['name']
        ]
        
        # Stage 2: Fuzzy match on base_name (vectorized)
        logger.info("Fuzzy matching base names...")
        iptv_base_names = [n.base_name for n in iptv_normalized]
        portal_base_names = [n.base_name for n in portal_normalized]
        
        # RapidFuzz cdist for batch processing (10-100x faster than loop)
        scores = process.cdist(
            iptv_base_names, 
            portal_base_names, 
            scorer=fuzz.token_sort_ratio,
            workers=self.max_workers,
            score_cutoff=self.threshold  # Filter low scores early
        )
        
        # Find best matches above threshold
        best_idx = np.argmax(scores, axis=1)
        best_scores = np.max(scores, axis=1)
        
        # Stage 3: Build matches dataframe
        logger.info(f"Building match results (threshold={self.threshold})...")
        matches = []
        
        for i, (iptv_norm, score, portal_idx) in enumerate(
            zip(iptv_normalized, best_scores, best_idx)
        ):
            if score >= self.threshold:
                portal_norm = portal_normalized[portal_idx]
                
                matches.append({
                    # Original identifiers
                    'iptv_org_id': iptv_org_df.iloc[i]['id'],
                    'iptv_org_name': iptv_norm.original_name,
                    'portal_id': portal_df.iloc[portal_idx]['id'],
                    'portal_name': portal_norm.original_name,
                    
                    # Normalized data
                    'base_name': iptv_norm.base_name,
                    'canonical_id': iptv_norm.canonical_id,
                    
                    # Variants (JSON strings for CSV export)
                    'iptv_variants': str(iptv_norm.variants),
                    'portal_variants': str(portal_norm.variants),
                    
                    # Matching metadata
                    'match_score': round(score / 100.0, 4),
                    'normalization_confidence': round(
                        (iptv_norm.confidence + portal_norm.confidence) / 2, 4
                    ),
                    'match_type': self._classify_match(iptv_norm, portal_norm, score)
                })
        
        logger.info(f"✓ Found {len(matches)} matches (from {len(iptv_org_df)} channels)")
        
        return pd.DataFrame(matches)
    
    def _validate_dataframe(self, df: pd.DataFrame, name: str):
        """Validate input DataFrame structure"""
        if df is None or df.empty:
            raise ValueError(f"{name} DataFrame is empty")
        
        required_cols = ['id', 'name']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            raise ValueError(f"{name} DataFrame missing columns: {missing_cols}")
    
    def _classify_match(self, iptv: ChannelNormalized, portal: ChannelNormalized, score: float) -> str:
        """
        Classify match quality for debugging/analysis.
        
        Returns:
            "exact" | "same_variant" | "different_variant" | "fuzzy"
        """
        if score >= 98:
            return "exact"
        elif iptv.canonical_id == portal.canonical_id:
            if iptv.variants == portal.variants:
                return "same_variant"
            else:
                return "different_variant"
        else:
            return "fuzzy"


def main():
    """CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Fuzzy match IPTV channels with normalization"
    )
    parser.add_argument(
        "--iptv-org", 
        type=Path, 
        required=True,
        help="Path to iptv-org channels CSV (columns: id, name)"
    )
    parser.add_argument(
        "--portal", 
        type=Path, 
        required=True,
        help="Path to portal channels CSV (columns: id, name)"
    )
    parser.add_argument(
        "--output", 
        type=Path, 
        default=Path("output/matches.csv"),
        help="Output path for matches CSV"
    )
    parser.add_argument(
        "--threshold", 
        type=float, 
        default=85.0,
        help="Minimum match score (0-100)"
    )
    parser.add_argument(
        "--max-workers", 
        type=int, 
        default=-1,
        help="CPU cores for parallel processing (-1 = all)"
    )
    
    args = parser.parse_args()
    
    # Load data
    logger.info(f"Loading iptv-org from {args.iptv_org}")
    iptv_org_df = pd.read_csv(args.iptv_org)
    
    logger.info(f"Loading portal from {args.portal}")
    portal_df = pd.read_csv(args.portal)
    
    # Match
    matcher = FuzzyChannelMatcher(
        threshold=args.threshold,
        max_workers=args.max_workers
    )
    
    matches_df = matcher.match_with_normalization(iptv_org_df, portal_df)
    
    # Save
    args.output.parent.mkdir(parents=True, exist_ok=True)
    matches_df.to_csv(args.output, index=False)
    
    logger.info(f"✓ Saved {len(matches_df)} matches to {args.output}")
    
    # Stats
    print("\n" + "="*60)
    print("Match Statistics")
    print("="*60)
    print(f"Total iptv-org channels: {len(iptv_org_df)}")
    print(f"Total portal channels:   {len(portal_df)}")
    print(f"Matches found:           {len(matches_df)}")
    print(f"Match rate:              {len(matches_df)/len(iptv_org_df)*100:.1f}%")
    print("\nMatch type breakdown:")
    print(matches_df['match_type'].value_counts())
    print("\nScore distribution:")
    print(matches_df['match_score'].describe())


if __name__ == "__main__":
    main()
