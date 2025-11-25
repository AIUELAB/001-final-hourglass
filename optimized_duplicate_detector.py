#!/usr/bin/env python3
"""
Optimized Duplicate Detector for Ultra Think Database
最適化された重複検出システム

This is a faster version focusing on the most important duplicate patterns.
"""

import pandas as pd
import numpy as np
import json
from collections import defaultdict
from datetime import datetime
import time

class OptimizedDuplicateDetector:
    """Fast duplicate detection focusing on key patterns"""

    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.df = None
        self.duplicates = {
            'exact_person_id': [],
            'exact_name': [],
            'similar_display': [],
            'korean_variants': [],
            'summary': {}
        }

    def load_data(self):
        """Load data efficiently"""
        print(f"Loading data from {self.csv_file}...")
        self.df = pd.read_csv(self.csv_file, encoding='utf-8')
        print(f"Loaded {len(self.df)} records")

        # Clean and normalize
        for col in ['person_name', 'person_name_display', 'person_name_ja']:
            if col in self.df.columns:
                self.df[col] = self.df[col].fillna('').astype(str).str.strip()

    def detect_exact_duplicates(self):
        """Fast detection of exact duplicates"""
        print("\n=== Detecting Exact Duplicates ===")
        start_time = time.time()

        # 1. Duplicate person_ids
        person_id_counts = self.df['person_id'].value_counts()
        duplicate_ids = person_id_counts[person_id_counts > 1]

        for person_id, count in duplicate_ids.items():
            duplicate_rows = self.df[self.df['person_id'] == person_id]
            self.duplicates['exact_person_id'].append({
                'person_id': person_id,
                'count': count,
                'indices': duplicate_rows.index.tolist(),
                'names': duplicate_rows['person_name'].tolist()
            })

        # 2. Exact name duplicates (different person_ids)
        name_groups = self.df.groupby('person_name')['person_id'].apply(list).to_dict()

        for name, person_ids in name_groups.items():
            if len(set(person_ids)) > 1:  # Different person_ids
                self.duplicates['exact_name'].append({
                    'name': name,
                    'person_ids': list(set(person_ids)),
                    'count': len(person_ids)
                })

        elapsed = time.time() - start_time
        print(f"Found {len(self.duplicates['exact_person_id'])} person_id duplicates")
        print(f"Found {len(self.duplicates['exact_name'])} exact name duplicates")
        print(f"Time: {elapsed:.2f} seconds")

    def detect_korean_variants(self):
        """Detect Korean artist name variants"""
        print("\n=== Detecting Korean Artist Variants ===")
        start_time = time.time()

        # Known problematic Korean artists
        korean_patterns = {
            'PSY': ['サイ', 'Psy', 'PSY'],
            'BTS': ['防弾少年団', 'バンタン', 'BTS'],
            'RM': ['アールエム', 'RM', 'Rap Monster'],
            'Jin': ['ジン', 'Jin'],
            'Suga': ['シュガ', 'Suga', 'SUGA'],
            'J-Hope': ['ジェイホープ', 'J-Hope', 'j-hope'],
            'Jimin': ['ジミン', 'Jimin', 'JIMIN'],
            'V': ['ヴィ', 'V', 'ブイ'],
            'Jungkook': ['ジョングク', 'Jungkook', 'Jung Kook'],
            'IU': ['アイユー', 'IU'],
            'G-Dragon': ['G-DRAGON', 'G-Dragon', 'ジードラゴン'],
            'BLACKPINK': ['ブラックピンク', 'BLACKPINK'],
            'TWICE': ['トゥワイス', 'TWICE'],
            'SEVENTEEN': ['セブンティーン', 'SEVENTEEN']
        }

        for canonical, variants in korean_patterns.items():
            found_records = []

            # Search in all name fields
            for variant in variants:
                mask = (
                    self.df['person_name'].str.contains(variant, na=False, case=False) |
                    self.df['person_name_display'].str.contains(variant, na=False, case=False) |
                    self.df['person_name_ja'].str.contains(variant, na=False, case=False)
                )

                matches = self.df[mask]
                for idx, row in matches.iterrows():
                    found_records.append({
                        'person_id': row['person_id'],
                        'person_name': row['person_name'],
                        'person_name_display': row['person_name_display'],
                        'matched_variant': variant
                    })

            if len(found_records) > 1:
                unique_ids = list(set(r['person_id'] for r in found_records))
                if len(unique_ids) > 1:
                    self.duplicates['korean_variants'].append({
                        'canonical': canonical,
                        'person_ids': unique_ids,
                        'records': found_records,
                        'count': len(unique_ids)
                    })

        elapsed = time.time() - start_time
        print(f"Found {len(self.duplicates['korean_variants'])} Korean artist variant groups")
        print(f"Time: {elapsed:.2f} seconds")

    def detect_similar_display_names(self):
        """Detect similar display names (faster algorithm)"""
        print("\n=== Detecting Similar Display Names ===")
        start_time = time.time()

        # Group by first 3 characters of display name for faster comparison
        display_groups = defaultdict(list)

        for idx, row in self.df.iterrows():
            display = row['person_name_display']
            if len(display) >= 3:
                key = display[:3]
                display_groups[key].append({
                    'person_id': row['person_id'],
                    'display': display,
                    'name': row['person_name']
                })

        # Check within groups
        found_similar = []
        for key, group in display_groups.items():
            if len(group) > 1:
                # Check for exact matches within group
                display_map = defaultdict(list)
                for item in group:
                    display_map[item['display']].append(item)

                for display, items in display_map.items():
                    if len(items) > 1:
                        unique_ids = list(set(item['person_id'] for item in items))
                        if len(unique_ids) > 1:
                            found_similar.append({
                                'display': display,
                                'person_ids': unique_ids,
                                'count': len(unique_ids)
                            })

        self.duplicates['similar_display'] = found_similar

        elapsed = time.time() - start_time
        print(f"Found {len(found_similar)} similar display name groups")
        print(f"Time: {elapsed:.2f} seconds")

    def analyze_quality(self):
        """Analyze quality of duplicate records to determine which to keep"""
        print("\n=== Analyzing Record Quality ===")

        quality_analysis = []

        # Analyze exact name duplicates
        for dup in self.duplicates['exact_name'][:10]:  # Sample first 10
            person_ids = dup['person_ids']
            records = self.df[self.df['person_id'].isin(person_ids)]

            analysis = {
                'name': dup['name'],
                'person_ids': person_ids,
                'quality_scores': []
            }

            for idx, record in records.iterrows():
                # Calculate quality score
                score = 0
                score += 10 if record['accuracy_score'] > 80 else 5
                score += 10 if pd.notna(record['age']) else 0  # Use age instead of birth_year
                score += 10 if pd.notna(record['nationality']) else 0
                score += 10 if len(str(record['occupation'])) > 10 else 5
                score += 10 if pd.notna(record['person_name_ja']) else 0
                score += 10 if record['name_recognition'] > 50 else 5

                analysis['quality_scores'].append({
                    'person_id': record['person_id'],
                    'score': score,
                    'accuracy': record['accuracy_score'],
                    'recognition': record['name_recognition']
                })

            # Sort by quality score
            analysis['quality_scores'].sort(key=lambda x: x['score'], reverse=True)
            analysis['best_record'] = analysis['quality_scores'][0]['person_id']

            quality_analysis.append(analysis)

        return quality_analysis

    def generate_summary(self):
        """Generate summary statistics"""
        total_duplicates = 0
        affected_records = set()

        # Count all duplicates
        for dup in self.duplicates['exact_person_id']:
            total_duplicates += dup['count'] - 1
            affected_records.update(dup['indices'])

        for dup in self.duplicates['exact_name']:
            total_duplicates += len(dup['person_ids']) - 1
            for pid in dup['person_ids']:
                affected_records.update(self.df[self.df['person_id'] == pid].index.tolist())

        for dup in self.duplicates['korean_variants']:
            total_duplicates += len(dup['person_ids']) - 1
            for pid in dup['person_ids']:
                affected_records.update(self.df[self.df['person_id'] == pid].index.tolist())

        self.duplicates['summary'] = {
            'total_records': len(self.df),
            'duplicate_records': total_duplicates,
            'affected_records': len(affected_records),
            'duplicate_rate': (total_duplicates / len(self.df)) * 100,
            'exact_person_id_groups': len(self.duplicates['exact_person_id']),
            'exact_name_groups': len(self.duplicates['exact_name']),
            'korean_variant_groups': len(self.duplicates['korean_variants']),
            'similar_display_groups': len(self.duplicates['similar_display'])
        }

    def save_report(self):
        """Save detection report"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Save JSON report
        report_file = f"duplicate_report_{timestamp}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            # Convert to serializable format
            report_data = {
                'summary': self.duplicates['summary'],
                'exact_person_id': self.duplicates['exact_person_id'][:20],  # Top 20
                'exact_name': self.duplicates['exact_name'][:20],
                'korean_variants': self.duplicates['korean_variants'],
                'similar_display': self.duplicates['similar_display'][:20]
            }
            json.dump(report_data, f, ensure_ascii=False, indent=2)

        print(f"\nReport saved to {report_file}")

        # Save high-priority duplicates CSV
        high_priority = []

        # Add exact duplicates
        for dup in self.duplicates['exact_person_id']:
            high_priority.append({
                'type': 'exact_person_id',
                'identifier': dup['person_id'],
                'count': dup['count'],
                'action': 'merge'
            })

        # Add Korean variants
        for dup in self.duplicates['korean_variants']:
            high_priority.append({
                'type': 'korean_variant',
                'identifier': dup['canonical'],
                'count': dup['count'],
                'action': 'standardize'
            })

        if high_priority:
            priority_df = pd.DataFrame(high_priority)
            priority_file = f"high_priority_duplicates_{timestamp}.csv"
            priority_df.to_csv(priority_file, index=False, encoding='utf-8')
            print(f"High priority duplicates saved to {priority_file}")

    def print_summary(self):
        """Print summary to console"""
        print("\n" + "="*60)
        print("DUPLICATE DETECTION SUMMARY")
        print("="*60)

        s = self.duplicates['summary']
        print(f"\nTotal Records: {s['total_records']:,}")
        print(f"Duplicate Records: {s['duplicate_records']:,}")
        print(f"Affected Records: {s['affected_records']:,}")
        print(f"Duplicate Rate: {s['duplicate_rate']:.2f}%")

        print(f"\nDuplicate Types:")
        print(f"- Exact Person ID: {s['exact_person_id_groups']} groups")
        print(f"- Exact Name: {s['exact_name_groups']} groups")
        print(f"- Korean Variants: {s['korean_variant_groups']} groups")
        print(f"- Similar Display: {s['similar_display_groups']} groups")

        # Show samples
        print(f"\n=== Sample Duplicates ===")

        if self.duplicates['exact_person_id']:
            print(f"\nExact Person ID Duplicates:")
            for dup in self.duplicates['exact_person_id'][:3]:
                print(f"  - {dup['person_id']}: {dup['count']} copies")

        if self.duplicates['exact_name']:
            print(f"\nExact Name Duplicates:")
            for dup in self.duplicates['exact_name'][:3]:
                print(f"  - {dup['name']}: {dup['count']} records ({', '.join(dup['person_ids'][:3])})")

        if self.duplicates['korean_variants']:
            print(f"\nKorean Artist Variants:")
            for dup in self.duplicates['korean_variants'][:3]:
                print(f"  - {dup['canonical']}: {dup['count']} variants ({', '.join(dup['person_ids'][:3])})")

    def run(self):
        """Run optimized detection"""
        start_total = time.time()

        self.load_data()
        self.detect_exact_duplicates()
        self.detect_korean_variants()
        self.detect_similar_display_names()

        # Analyze quality
        quality_analysis = self.analyze_quality()

        # Generate summary
        self.generate_summary()

        # Print results
        self.print_summary()

        # Print quality analysis sample
        if quality_analysis:
            print(f"\n=== Quality Analysis (Sample) ===")
            for analysis in quality_analysis[:3]:
                print(f"\n{analysis['name']}:")
                print(f"  Best record: {analysis['best_record']}")
                for score_data in analysis['quality_scores'][:2]:
                    print(f"    - {score_data['person_id']}: Quality={score_data['score']}, "
                          f"Accuracy={score_data['accuracy']}, Recognition={score_data['recognition']}")

        # Save report
        self.save_report()

        total_time = time.time() - start_total
        print(f"\n✅ Total execution time: {total_time:.2f} seconds")

        return self.duplicates


def main():
    csv_file = '/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_FOREIGN_NAMES_CORRECTED_20250831_140703.csv'

    detector = OptimizedDuplicateDetector(csv_file)
    duplicates = detector.run()


if __name__ == "__main__":
    main()
