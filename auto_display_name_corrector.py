#!/usr/bin/env python3
"""
Automatic Display Name Corrector
外国語表記自動修正システム

This system automatically corrects display names in the Ultra Think database
using Wikipedia authority and cultural context rules.
"""

import pandas as pd
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import os
import shutil

# Import our custom modules
from wikipedia_japan_authority import WikipediaJapanAuthority
from foreign_name_display_rules import ForeignNameDisplayRules

class AutoDisplayNameCorrector:
    """Automatic display name correction system"""
    
    def __init__(self, use_wikipedia: bool = True):
        """
        Initialize the corrector
        
        Args:
            use_wikipedia: Whether to use Wikipedia API (may be slow)
        """
        self.use_wikipedia = use_wikipedia
        self.rules_engine = ForeignNameDisplayRules()
        self.wikipedia_authority = WikipediaJapanAuthority() if use_wikipedia else None
        self.corrections_log = []
        self.statistics = {
            'total_processed': 0,
            'corrections_made': 0,
            'wikipedia_validated': 0,
            'rule_based_corrections': 0,
            'duplicates_found': 0,
            'errors': 0
        }
        
    def load_database(self, csv_file: str) -> pd.DataFrame:
        """Load the database CSV file"""
        print(f"Loading database from {csv_file}...")
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"Loaded {len(df)} records")
        return df
    
    def create_backup(self, csv_file: str) -> str:
        """Create a backup of the original file"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"backup_before_foreign_name_correction_{timestamp}.csv"
        
        print(f"Creating backup: {backup_file}")
        shutil.copy2(csv_file, backup_file)
        
        return backup_file
    
    def identify_correction_candidates(self, df: pd.DataFrame) -> pd.DataFrame:
        """Identify records that need correction"""
        print("\nIdentifying correction candidates...")
        
        candidates = []
        
        # 1. Records with alphabet in display name
        alphabet_mask = df['person_name_display'].str.contains(r'[A-Za-z]', na=False)
        
        # 2. Korean nationals with katakana display
        korean_katakana_mask = (
            (df['nationality'] == '韓国') & 
            df['person_name_display'].str.contains(r'[ァ-ヶー]', na=False)
        )
        
        # 3. Japanese with pure English display (no Japanese characters)
        japanese_english_mask = (
            (df['nationality'] == '日本') & 
            df['person_name_display'].str.match(r'^[A-Za-z\s\-\(\)]+$', na=False)
        )
        
        # Combine all candidates
        candidates_mask = alphabet_mask | korean_katakana_mask | japanese_english_mask
        candidates_df = df[candidates_mask].copy()
        
        print(f"Found {len(candidates_df)} candidates for correction:")
        print(f"  - With alphabet: {alphabet_mask.sum()}")
        print(f"  - Korean with katakana: {korean_katakana_mask.sum()}")
        print(f"  - Japanese with English: {japanese_english_mask.sum()}")
        
        return candidates_df
    
    def correct_display_name(self, person_data: Dict) -> Dict:
        """
        Correct a single person's display name
        
        Returns:
            Dictionary with correction details
        """
        person_id = person_data.get('person_id')
        current_display = person_data.get('person_name_display', '')
        
        # First apply cultural rules
        rule_result = self.rules_engine.apply_display_rules(person_data)
        
        corrected_display = rule_result['corrected_display']
        reasoning = rule_result['reasoning']
        confidence = rule_result['confidence']
        source = 'cultural_rules'
        
        # If Wikipedia is enabled and confidence is not high enough, check Wikipedia
        if self.use_wikipedia and confidence < 0.9:
            try:
                wiki_result = self.wikipedia_authority.get_canonical_name(
                    current_display,
                    person_data.get('nationality'),
                    person_data.get('occupation')
                )
                
                if wiki_result['confidence'] > confidence:
                    corrected_display = wiki_result['canonical_name']
                    reasoning = wiki_result['reasoning']
                    confidence = wiki_result['confidence']
                    source = 'wikipedia'
                    self.statistics['wikipedia_validated'] += 1
                
            except Exception as e:
                print(f"Wikipedia lookup failed for {person_id}: {e}")
        
        # Record the correction
        correction = {
            'person_id': person_id,
            'original': current_display,
            'corrected': corrected_display,
            'changed': current_display != corrected_display,
            'source': source,
            'reasoning': reasoning,
            'confidence': confidence,
            'nationality': person_data.get('nationality'),
            'occupation': person_data.get('occupation')
        }
        
        if correction['changed']:
            self.statistics['corrections_made'] += 1
            if source == 'cultural_rules':
                self.statistics['rule_based_corrections'] += 1
        
        self.corrections_log.append(correction)
        
        return correction
    
    def apply_corrections_batch(self, df: pd.DataFrame, candidates_df: pd.DataFrame) -> pd.DataFrame:
        """Apply corrections to all candidates"""
        print("\nApplying corrections...")
        
        corrected_df = df.copy()
        
        for idx, row in candidates_df.iterrows():
            self.statistics['total_processed'] += 1
            
            # Convert row to dict
            person_data = row.to_dict()
            
            # Get correction
            correction = self.correct_display_name(person_data)
            
            # Apply correction to dataframe
            if correction['changed']:
                corrected_df.loc[idx, 'person_name_display'] = correction['corrected']
                print(f"  {correction['person_id']}: {correction['original']} → {correction['corrected']}")
            
            # Progress indicator
            if self.statistics['total_processed'] % 50 == 0:
                print(f"  Processed {self.statistics['total_processed']} records...")
            
            # Rate limiting for Wikipedia API
            if self.use_wikipedia and self.statistics['total_processed'] % 10 == 0:
                time.sleep(0.5)
        
        return corrected_df
    
    def merge_duplicates(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
        """Identify and merge duplicate persons"""
        print("\nIdentifying duplicates...")
        
        # Group by normalized person_name to find duplicates
        duplicates = []
        merged_df = df.copy()
        
        # Known duplicate patterns
        duplicate_patterns = [
            ('PSY', ['PSY', 'サイ', 'Psy']),
            ('RM', ['RM', 'アールエム', 'Rap Monster']),
            ('Jin', ['Jin', 'ジン']),
            ('Suga', ['Suga', 'シュガ', 'SUGA']),
            ('J-Hope', ['J-Hope', 'ジェイホープ', 'j-hope']),
            ('Jimin', ['Jimin', 'ジミン', 'JIMIN']),
            ('V', ['V', 'ヴィ']),
            ('Jungkook', ['Jungkook', 'ジョングク', 'Jung Kook'])
        ]
        
        for canonical_name, variants in duplicate_patterns:
            # Find all matching records
            mask = merged_df['person_name_display'].isin(variants) | merged_df['person_name'].isin(variants)
            matches = merged_df[mask]
            
            if len(matches) > 1:
                # Keep the first ID, mark others for removal
                keep_id = matches.iloc[0]['person_id']
                remove_ids = matches.iloc[1:]['person_id'].tolist()
                
                if remove_ids:
                    duplicates.append({
                        'canonical_name': canonical_name,
                        'keep_id': keep_id,
                        'remove_ids': remove_ids,
                        'count': len(matches)
                    })
                    
                    # Remove duplicates from dataframe
                    merged_df = merged_df[~merged_df['person_id'].isin(remove_ids)]
                    
                    self.statistics['duplicates_found'] += len(remove_ids)
        
        print(f"Found and merged {self.statistics['duplicates_found']} duplicate records")
        
        return merged_df, duplicates
    
    def generate_report(self, output_file: str = None):
        """Generate detailed correction report"""
        report_file = output_file or f"foreign_name_correction_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Foreign Name Display Correction Report\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # Statistics
            f.write("## Statistics\n\n")
            f.write(f"- Total Records Processed: {self.statistics['total_processed']}\n")
            f.write(f"- Corrections Made: {self.statistics['corrections_made']}\n")
            f.write(f"- Wikipedia Validated: {self.statistics['wikipedia_validated']}\n")
            f.write(f"- Rule-based Corrections: {self.statistics['rule_based_corrections']}\n")
            f.write(f"- Duplicates Merged: {self.statistics['duplicates_found']}\n")
            f.write(f"- Errors: {self.statistics['errors']}\n\n")
            
            # Correction rate
            if self.statistics['total_processed'] > 0:
                correction_rate = (self.statistics['corrections_made'] / self.statistics['total_processed']) * 100
                f.write(f"**Correction Rate**: {correction_rate:.1f}%\n\n")
            
            # Sample corrections
            f.write("## Sample Corrections\n\n")
            
            # Group by nationality
            corrections_by_nationality = {}
            for correction in self.corrections_log:
                if correction['changed']:
                    nationality = correction.get('nationality', 'Unknown')
                    if nationality not in corrections_by_nationality:
                        corrections_by_nationality[nationality] = []
                    corrections_by_nationality[nationality].append(correction)
            
            for nationality, corrections in sorted(corrections_by_nationality.items()):
                f.write(f"### {nationality}\n\n")
                for correction in corrections[:5]:  # Show first 5 per nationality
                    f.write(f"- **{correction['person_id']}**: {correction['original']} → {correction['corrected']}\n")
                    f.write(f"  - Source: {correction['source']}\n")
                    f.write(f"  - Confidence: {correction['confidence']:.2f}\n")
                    f.write(f"  - Reasoning: {correction['reasoning']}\n\n")
                
                if len(corrections) > 5:
                    f.write(f"  *...and {len(corrections) - 5} more*\n\n")
            
            # High confidence corrections
            f.write("## High Confidence Corrections (≥0.9)\n\n")
            high_confidence = [c for c in self.corrections_log if c['changed'] and c['confidence'] >= 0.9]
            for correction in high_confidence[:10]:
                f.write(f"- {correction['person_id']}: {correction['original']} → {correction['corrected']} ({correction['confidence']:.2f})\n")
            
            f.write(f"\nTotal high confidence corrections: {len(high_confidence)}\n")
        
        print(f"\nReport saved to {report_file}")
        
        # Save detailed corrections log
        log_file = f"corrections_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(self.corrections_log, f, ensure_ascii=False, indent=2)
        print(f"Detailed log saved to {log_file}")
    
    def process_database(self, input_file: str, output_file: str = None):
        """
        Main processing function
        
        Args:
            input_file: Input CSV file path
            output_file: Output CSV file path (optional)
        """
        print("="*60)
        print("FOREIGN NAME DISPLAY CORRECTION SYSTEM")
        print("="*60)
        
        # Create backup
        backup_file = self.create_backup(input_file)
        
        # Load database
        df = self.load_database(input_file)
        
        # Identify candidates
        candidates_df = self.identify_correction_candidates(df)
        
        if len(candidates_df) == 0:
            print("No correction candidates found.")
            return
        
        # Apply corrections
        corrected_df = self.apply_corrections_batch(df, candidates_df)
        
        # Merge duplicates
        final_df, duplicates = self.merge_duplicates(corrected_df)
        
        # Save corrected database
        if output_file is None:
            output_file = f"ultra_think_FOREIGN_NAMES_CORRECTED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        print(f"\nSaving corrected database to {output_file}...")
        final_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"Saved {len(final_df)} records")
        
        # Generate report
        self.generate_report()
        
        # Print summary
        print("\n" + "="*60)
        print("CORRECTION COMPLETE")
        print("="*60)
        print(f"Original file: {input_file}")
        print(f"Backup file: {backup_file}")
        print(f"Corrected file: {output_file}")
        print(f"Total corrections: {self.statistics['corrections_made']}")
        print(f"Duplicates merged: {self.statistics['duplicates_found']}")
        print(f"Final record count: {len(final_df)}")


def main():
    """Main execution"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Correct foreign name display issues')
    parser.add_argument('--input', '-i', 
                       default='/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_LATEST_DATABASE_20250831.csv',
                       help='Input CSV file')
    parser.add_argument('--output', '-o', 
                       help='Output CSV file (optional)')
    parser.add_argument('--no-wikipedia', action='store_true',
                       help='Skip Wikipedia validation (faster)')
    
    args = parser.parse_args()
    
    # Create corrector
    corrector = AutoDisplayNameCorrector(use_wikipedia=not args.no_wikipedia)
    
    # Process database
    corrector.process_database(args.input, args.output)


if __name__ == "__main__":
    main()