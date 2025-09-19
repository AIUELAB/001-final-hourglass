#!/usr/bin/env python3
"""
Foreign Name Display Analyzer for Ultra Think Database
外国語表記問題の包括的分析ツール

This script analyzes person_name_display field inconsistencies and identifies:
1. Pure alphabet names (PSY, BTS, etc.)
2. Mixed format with parentheses
3. Incorrect katakana transliterations
4. Duplicate person entries
"""

import pandas as pd
import json
import re
from collections import defaultdict
from typing import Dict, List, Tuple
import unicodedata

class ForeignNameAnalyzer:
    """Analyze foreign name display issues in Ultra Think database"""
    
    def __init__(self, csv_file: str):
        """Initialize analyzer with CSV file"""
        self.csv_file = csv_file
        self.df = None
        self.issues = {
            "total_issues": 0,
            "duplicate_persons": [],
            "pure_alphabet": [],
            "mixed_format": [],
            "incorrect_katakana": [],
            "japanese_with_english": [],
            "statistics": {}
        }
        
    def load_data(self):
        """Load CSV data"""
        print(f"Loading data from {self.csv_file}...")
        self.df = pd.read_csv(self.csv_file, encoding='utf-8')
        print(f"Loaded {len(self.df)} records")
        
    def contains_alphabet(self, text: str) -> bool:
        """Check if text contains Latin alphabet characters"""
        if pd.isna(text):
            return False
        return bool(re.search(r'[A-Za-z]', str(text)))
    
    def contains_katakana(self, text: str) -> bool:
        """Check if text contains katakana characters"""
        if pd.isna(text):
            return False
        return bool(re.search(r'[ァ-ヶー]', str(text)))
    
    def is_pure_alphabet(self, text: str) -> bool:
        """Check if text is pure alphabet (with spaces, hyphens, parentheses)"""
        if pd.isna(text):
            return False
        # Remove spaces, hyphens, parentheses and check if only alphabet remains
        cleaned = re.sub(r'[\s\-\(\)（）]', '', str(text))
        return bool(cleaned) and cleaned.isalpha() and cleaned.isascii()
    
    def has_parentheses(self, text: str) -> bool:
        """Check if text has parentheses (either ASCII or full-width)"""
        if pd.isna(text):
            return False
        return bool(re.search(r'[\(\)（）]', str(text)))
    
    def analyze_foreign_names(self):
        """Analyze all foreign name display issues"""
        print("\n=== Analyzing Foreign Name Display Issues ===")
        
        # Filter records with alphabet in person_name_display
        alphabet_records = self.df[self.df['person_name_display'].apply(self.contains_alphabet)]
        print(f"Found {len(alphabet_records)} records with alphabet characters")
        
        # Analyze each record
        for idx, row in alphabet_records.iterrows():
            person_id = row['person_id']
            display_name = row['person_name_display']
            person_name = row.get('person_name', '')
            person_name_ja = row.get('person_name_ja', '')
            nationality = row.get('nationality', '')
            occupation = row.get('occupation', '')
            
            # Categorize the issue
            if self.is_pure_alphabet(display_name):
                self.issues['pure_alphabet'].append({
                    'id': person_id,
                    'current': display_name,
                    'person_name': person_name,
                    'person_name_ja': person_name_ja,
                    'nationality': nationality,
                    'occupation': occupation,
                    'recommendation': self.get_recommendation(row)
                })
            elif self.has_parentheses(display_name):
                self.issues['mixed_format'].append({
                    'id': person_id,
                    'current': display_name,
                    'person_name': person_name,
                    'nationality': nationality,
                    'occupation': occupation,
                    'recommendation': f"Standardize format: {self.standardize_parentheses(display_name)}"
                })
            
        # Check for Japanese people with English display names
        japanese_with_english = self.df[
            (self.df['nationality'] == '日本') & 
            (self.df['person_name_display'].apply(self.contains_alphabet))
        ]
        
        for idx, row in japanese_with_english.iterrows():
            self.issues['japanese_with_english'].append({
                'id': row['person_id'],
                'current': row['person_name_display'],
                'person_name': row.get('person_name', ''),
                'person_name_ja': row.get('person_name_ja', ''),
                'recommendation': f"Use Japanese: {row.get('person_name_ja', row.get('person_name', ''))}"
            })
        
    def find_duplicates(self):
        """Find duplicate person entries"""
        print("\n=== Finding Duplicate Persons ===")
        
        # Group by person_name to find duplicates
        name_groups = defaultdict(list)
        
        for idx, row in self.df.iterrows():
            person_name = str(row.get('person_name', '')).strip()
            if person_name and person_name != 'nan':
                name_groups[person_name].append({
                    'id': row['person_id'],
                    'display': row.get('person_name_display', ''),
                    'nationality': row.get('nationality', '')
                })
        
        # Find groups with multiple IDs
        for name, entries in name_groups.items():
            if len(entries) > 1:
                # Check if they're likely the same person
                if self.are_same_person(entries):
                    self.issues['duplicate_persons'].append({
                        'name': name,
                        'ids': [e['id'] for e in entries],
                        'displays': [e['display'] for e in entries],
                        'count': len(entries)
                    })
        
        # Special check for known problematic cases
        self.check_known_duplicates()
        
    def check_known_duplicates(self):
        """Check for known duplicate cases like PSY, BTS members"""
        known_duplicates = {
            'PSY': ['PSY', 'サイ', 'Psy'],
            'RM': ['RM', 'アールエム', 'Rap Monster'],
            'Jin': ['Jin', 'ジン', 'Jin (BTS)'],
            'Suga': ['Suga', 'シュガ', 'SUGA'],
            'J-Hope': ['J-Hope', 'ジェイホープ', 'j-hope'],
            'Jimin': ['Jimin', 'ジミン', 'JIMIN'],
            'V': ['V', 'ヴィ', 'V (BTS)'],
            'Jungkook': ['Jungkook', 'ジョングク', 'Jung Kook']
        }
        
        for canonical_name, variants in known_duplicates.items():
            found_ids = []
            found_displays = []
            
            for variant in variants:
                matches = self.df[
                    (self.df['person_name_display'].str.contains(variant, na=False, case=False)) |
                    (self.df['person_name'].str.contains(variant, na=False, case=False))
                ]
                
                for idx, row in matches.iterrows():
                    if row['person_id'] not in found_ids:
                        found_ids.append(row['person_id'])
                        found_displays.append(row['person_name_display'])
            
            if len(found_ids) > 1:
                # Check if not already in duplicates
                existing = False
                for dup in self.issues['duplicate_persons']:
                    if set(found_ids).intersection(set(dup['ids'])):
                        existing = True
                        break
                
                if not existing:
                    self.issues['duplicate_persons'].append({
                        'name': canonical_name,
                        'ids': found_ids,
                        'displays': found_displays,
                        'count': len(found_ids),
                        'type': 'known_variant'
                    })
    
    def analyze_katakana_issues(self):
        """Analyze incorrect katakana transliterations"""
        print("\n=== Analyzing Katakana Issues ===")
        
        # K-pop artists that should use alphabet
        kpop_katakana_errors = {
            'サイ': 'PSY',
            'ビーティーエス': 'BTS',
            'ブラックピンク': 'BLACKPINK',
            'トゥワイス': 'TWICE',
            'セブンティーン': 'SEVENTEEN',
            'ストレイキッズ': 'Stray Kids',
            'エンハイプン': 'ENHYPEN',
            'アイヴ': 'IVE',
            'ル・セラフィム': 'LE SSERAFIM'
        }
        
        for katakana, correct in kpop_katakana_errors.items():
            matches = self.df[self.df['person_name_display'].str.contains(katakana, na=False)]
            
            for idx, row in matches.iterrows():
                # Check if Korean nationality
                if row.get('nationality', '') == '韓国':
                    self.issues['incorrect_katakana'].append({
                        'id': row['person_id'],
                        'current': row['person_name_display'],
                        'should_be': correct,
                        'reason': 'K-pop artists use original alphabet names in Japan',
                        'nationality': row.get('nationality', '')
                    })
    
    def are_same_person(self, entries: List[Dict]) -> bool:
        """Determine if entries are likely the same person"""
        # If all have same nationality, likely same person
        nationalities = set(e['nationality'] for e in entries)
        if len(nationalities) == 1:
            return True
        
        # If display names are variants of each other
        displays = [e['display'] for e in entries]
        if self.are_name_variants(displays):
            return True
        
        return False
    
    def are_name_variants(self, names: List[str]) -> bool:
        """Check if names are variants of each other"""
        # Simple check - if one contains the other
        for i, name1 in enumerate(names):
            for name2 in names[i+1:]:
                if name1 in name2 or name2 in name1:
                    return True
        return False
    
    def get_recommendation(self, row: pd.Series) -> str:
        """Get recommendation for a specific row"""
        nationality = row.get('nationality', '')
        occupation = str(row.get('occupation', ''))
        display = row.get('person_name_display', '')
        
        # K-pop/Korean entertainment
        if nationality == '韓国' and any(term in occupation for term in ['歌手', 'アイドル', 'K-POP', 'ラッパー']):
            return f"Keep original: {display} (K-pop convention)"
        
        # Western artists
        if nationality in ['アメリカ', 'イギリス', 'フランス', 'ドイツ', 'カナダ']:
            # Should use katakana
            if self.contains_katakana(display):
                return f"Keep katakana: {display}"
            else:
                return f"Convert to katakana (Western artist convention)"
        
        # Japanese artists
        if nationality == '日本':
            if row.get('person_name_ja'):
                return f"Use Japanese: {row.get('person_name_ja')}"
            else:
                return "Check established stage name convention"
        
        return "Requires manual review"
    
    def standardize_parentheses(self, text: str) -> str:
        """Standardize parentheses format"""
        # Convert full-width to half-width parentheses
        text = text.replace('（', ' (').replace('）', ')')
        # Ensure single space before opening parenthesis
        text = re.sub(r'\s*\(', ' (', text)
        text = re.sub(r'^\s+', '', text)  # Remove leading space
        return text
    
    def generate_statistics(self):
        """Generate statistics about the issues"""
        self.issues['statistics'] = {
            'total_records': len(self.df),
            'records_with_alphabet': len(self.df[self.df['person_name_display'].apply(self.contains_alphabet)]),
            'pure_alphabet_count': len(self.issues['pure_alphabet']),
            'mixed_format_count': len(self.issues['mixed_format']),
            'incorrect_katakana_count': len(self.issues['incorrect_katakana']),
            'japanese_with_english_count': len(self.issues['japanese_with_english']),
            'duplicate_persons_count': len(self.issues['duplicate_persons']),
            'total_duplicate_ids': sum(d['count'] for d in self.issues['duplicate_persons']),
            'nationalities_affected': self.get_affected_nationalities()
        }
        
        self.issues['total_issues'] = (
            self.issues['statistics']['pure_alphabet_count'] +
            self.issues['statistics']['mixed_format_count'] +
            self.issues['statistics']['incorrect_katakana_count'] +
            self.issues['statistics']['japanese_with_english_count']
        )
    
    def get_affected_nationalities(self) -> Dict[str, int]:
        """Get count of issues by nationality"""
        nationality_counts = defaultdict(int)
        
        for issue in self.issues['pure_alphabet']:
            nationality_counts[issue.get('nationality', 'Unknown')] += 1
        
        for issue in self.issues['japanese_with_english']:
            nationality_counts['日本'] += 1
        
        return dict(nationality_counts)
    
    def save_reports(self):
        """Save analysis reports"""
        # Save JSON report
        json_file = 'foreign_name_analysis_report.json'
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(self.issues, f, ensure_ascii=False, indent=2)
        print(f"\nSaved detailed analysis to {json_file}")
        
        # Save duplicate persons CSV
        if self.issues['duplicate_persons']:
            duplicates_df = pd.DataFrame(self.issues['duplicate_persons'])
            duplicates_df.to_csv('duplicate_persons_list.csv', index=False, encoding='utf-8')
            print(f"Saved duplicate persons to duplicate_persons_list.csv")
        
        # Save summary report
        self.save_summary_report()
    
    def save_summary_report(self):
        """Save human-readable summary report"""
        report_file = 'foreign_name_issues_summary.md'
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Foreign Name Display Issues - Summary Report\n\n")
            f.write(f"## Statistics\n\n")
            f.write(f"- Total Records: {self.issues['statistics']['total_records']}\n")
            f.write(f"- Records with Alphabet: {self.issues['statistics']['records_with_alphabet']}\n")
            f.write(f"- Total Issues Found: {self.issues['total_issues']}\n\n")
            
            f.write("### Issue Breakdown\n\n")
            f.write(f"- Pure Alphabet Names: {self.issues['statistics']['pure_alphabet_count']}\n")
            f.write(f"- Mixed Format (with parentheses): {self.issues['statistics']['mixed_format_count']}\n")
            f.write(f"- Incorrect Katakana: {self.issues['statistics']['incorrect_katakana_count']}\n")
            f.write(f"- Japanese with English Display: {self.issues['statistics']['japanese_with_english_count']}\n")
            f.write(f"- Duplicate Persons: {self.issues['statistics']['duplicate_persons_count']} groups ({self.issues['statistics']['total_duplicate_ids']} total IDs)\n\n")
            
            f.write("## Key Findings\n\n")
            
            # Duplicate persons
            if self.issues['duplicate_persons']:
                f.write("### Duplicate Persons Requiring Merge\n\n")
                for dup in self.issues['duplicate_persons'][:10]:  # Top 10
                    f.write(f"- **{dup['name']}**: {dup['count']} IDs {dup['ids']}\n")
                    f.write(f"  - Displays: {', '.join(dup['displays'])}\n")
                f.write("\n")
            
            # K-pop issues
            kpop_issues = [i for i in self.issues['incorrect_katakana'] if i.get('nationality') == '韓国']
            if kpop_issues:
                f.write("### K-pop Artists Using Katakana (Should Use Alphabet)\n\n")
                for issue in kpop_issues[:10]:
                    f.write(f"- {issue['id']}: {issue['current']} → {issue['should_be']}\n")
                f.write("\n")
            
            # Japanese with English
            if self.issues['japanese_with_english']:
                f.write(f"### Japanese Artists Using English Display ({len(self.issues['japanese_with_english'])} cases)\n\n")
                for issue in self.issues['japanese_with_english'][:10]:
                    f.write(f"- {issue['id']}: {issue['current']} → {issue['recommendation']}\n")
                f.write("\n")
            
            f.write("## Recommendations\n\n")
            f.write("1. **Merge Duplicate Persons**: Consolidate duplicate IDs for same persons\n")
            f.write("2. **K-pop Convention**: Use original alphabet names for all K-pop artists\n")
            f.write("3. **Japanese Artists**: Use person_name_ja when available\n")
            f.write("4. **Western Artists**: Convert to established katakana forms\n")
            f.write("5. **Implement Wikipedia Authority**: Use Wikipedia Japan page titles as canonical source\n")
        
        print(f"Saved summary report to {report_file}")
    
    def run_analysis(self):
        """Run complete analysis"""
        self.load_data()
        self.analyze_foreign_names()
        self.find_duplicates()
        self.analyze_katakana_issues()
        self.generate_statistics()
        self.save_reports()
        
        # Print summary
        print("\n" + "="*60)
        print("ANALYSIS COMPLETE")
        print("="*60)
        print(f"Total Issues Found: {self.issues['total_issues']}")
        print(f"Duplicate Person Groups: {len(self.issues['duplicate_persons'])}")
        print(f"Pure Alphabet Names: {len(self.issues['pure_alphabet'])}")
        print(f"Japanese with English: {len(self.issues['japanese_with_english'])}")
        print(f"Incorrect Katakana: {len(self.issues['incorrect_katakana'])}")
        print("\nReports saved:")
        print("- foreign_name_analysis_report.json (detailed)")
        print("- duplicate_persons_list.csv (duplicates)")
        print("- foreign_name_issues_summary.md (summary)")


def main():
    """Main execution"""
    csv_file = '/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_LATEST_DATABASE_20250831.csv'
    
    analyzer = ForeignNameAnalyzer(csv_file)
    analyzer.run_analysis()


if __name__ == "__main__":
    main()