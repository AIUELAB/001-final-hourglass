#!/usr/bin/env python3
"""
Ultra Think Database Duplicate Root Cause Analyzer

Comprehensive analysis of all duplicate types in the Ultra Think database:
- Exact name matches
- Similar names (fuzzy matching)
- Same person with different representations
- Group members appearing multiple times
- Partial name matches
- Data quality evaluation
- Root cause identification
"""

import pandas as pd
import json
import re
from collections import defaultdict, Counter
from difflib import SequenceMatcher
from datetime import datetime
from typing import Dict, List, Tuple, Set
import unicodedata


class DuplicateRootCauseAnalyzer:
    """Comprehensive duplicate analysis and root cause identification."""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = None
        self.analysis_results = {}
        self.duplicate_groups = {}
        self.quality_metrics = {}
        self.root_causes = {}

    def load_data(self):
        """Load CSV data with proper encoding."""
        print("Loading CSV data...")
        self.df = pd.read_csv(self.csv_path, encoding='utf-8')
        print(f"Loaded {len(self.df)} records")

    def normalize_name(self, name: str) -> str:
        """Normalize names for comparison."""
        if pd.isna(name) or not name:
            return ""

        # Unicode normalization
        name = unicodedata.normalize('NFKC', str(name))

        # Remove common prefixes/suffixes
        name = re.sub(r'^(Mr\.|Ms\.|Dr\.|Prof\.)\s*', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s*(Jr\.|Sr\.|III|IV|V)$', '', name, flags=re.IGNORECASE)

        # Remove extra spaces and convert to lowercase for comparison
        name = ' '.join(name.split()).lower()

        return name

    def extract_base_name(self, name: str) -> str:
        """Extract base name without group/band information."""
        if pd.isna(name) or not name:
            return ""

        # Remove group information in parentheses
        base = re.sub(r'\s*\([^)]*\)', '', str(name))

        # Remove common group indicators
        base = re.sub(r'\s*(from|of|ex-|元)\s*.*$', '', base, flags=re.IGNORECASE)

        return base.strip()

    def similarity_score(self, name1: str, name2: str) -> float:
        """Calculate similarity score between two names."""
        return SequenceMatcher(None, name1, name2).ratio()

    def analyze_exact_duplicates(self):
        """Find exact name duplicates across all name fields."""
        print("Analyzing exact duplicates...")

        exact_duplicates = {}

        # Check each name field
        name_fields = ['person_name', 'person_name_display', 'person_name_ja']

        for field in name_fields:
            if field in self.df.columns:
                # Group by normalized names
                normalized = self.df[field].apply(self.normalize_name)
                groups = self.df.groupby(normalized).groups

                # Find groups with multiple entries
                field_duplicates = {
                    name: indices.tolist()
                    for name, indices in groups.items()
                    if len(indices) > 1 and name != ""
                }

                exact_duplicates[field] = field_duplicates

        self.duplicate_groups['exact'] = exact_duplicates

    def analyze_similar_names(self, threshold: float = 0.8):
        """Find similar names using fuzzy matching."""
        print("Analyzing similar names with fuzzy matching...")

        similar_groups = defaultdict(list)
        name_fields = ['person_name', 'person_name_display', 'person_name_ja']

        for field in name_fields:
            if field not in self.df.columns:
                continue

            names = self.df[field].dropna().unique()
            processed = set()

            for i, name1 in enumerate(names):
                if name1 in processed:
                    continue

                group = [name1]
                processed.add(name1)

                for name2 in names[i+1:]:
                    if name2 in processed:
                        continue

                    similarity = self.similarity_score(
                        self.normalize_name(name1),
                        self.normalize_name(name2)
                    )

                    if similarity >= threshold:
                        group.append(name2)
                        processed.add(name2)

                if len(group) > 1:
                    similar_groups[f"{field}_group_{len(similar_groups)}"] = group

        self.duplicate_groups['similar'] = dict(similar_groups)

    def analyze_base_name_duplicates(self):
        """Find same person with different representations (e.g., with/without group info)."""
        print("Analyzing base name duplicates...")

        base_name_groups = defaultdict(list)

        # Extract base names and group by them
        for idx, row in self.df.iterrows():
            base_names = set()

            for field in ['person_name', 'person_name_display', 'person_name_ja']:
                if field in row and pd.notna(row[field]):
                    base = self.extract_base_name(row[field])
                    if base:
                        base_names.add(self.normalize_name(base))

            # Add to groups for each base name
            for base_name in base_names:
                if base_name:
                    base_name_groups[base_name].append(idx)

        # Filter groups with multiple entries
        base_duplicates = {
            base_name: indices
            for base_name, indices in base_name_groups.items()
            if len(indices) > 1
        }

        self.duplicate_groups['base_name'] = base_duplicates

    def analyze_group_member_duplicates(self):
        """Find group members appearing multiple times."""
        print("Analyzing group member duplicates...")

        group_pattern = re.compile(r'\(([^)]+)\)')
        member_appearances = defaultdict(list)

        for idx, row in self.df.iterrows():
            for field in ['person_name', 'person_name_display', 'person_name_ja']:
                if field in row and pd.notna(row[field]):
                    name = str(row[field])

                    # Extract group information
                    matches = group_pattern.findall(name)
                    if matches:
                        # This person is associated with groups
                        base_name = self.extract_base_name(name)
                        if base_name:
                            member_appearances[self.normalize_name(base_name)].append({
                                'index': idx,
                                'name': name,
                                'groups': matches,
                                'field': field
                            })

        # Find members appearing in multiple contexts
        group_duplicates = {
            member: appearances
            for member, appearances in member_appearances.items()
            if len(appearances) > 1
        }

        self.duplicate_groups['group_members'] = group_duplicates

    def analyze_partial_matches(self):
        """Find partial name matches."""
        print("Analyzing partial matches...")

        partial_groups = defaultdict(list)

        # Get all unique names
        all_names = set()
        for field in ['person_name', 'person_name_display', 'person_name_ja']:
            if field in self.df.columns:
                names = self.df[field].dropna().unique()
                all_names.update(names)

        all_names = list(all_names)

        # Find partial matches
        for i, name1 in enumerate(all_names):
            normalized1 = self.normalize_name(name1)
            if len(normalized1) < 3:  # Skip very short names
                continue

            for name2 in all_names[i+1:]:
                normalized2 = self.normalize_name(name2)
                if len(normalized2) < 3:
                    continue

                # Check if one name is contained in another
                if normalized1 in normalized2 or normalized2 in normalized1:
                    # Check if it's not just a substring match
                    if abs(len(normalized1) - len(normalized2)) > 2:
                        key = f"partial_{len(partial_groups)}"
                        partial_groups[key] = [name1, name2]

        self.duplicate_groups['partial'] = dict(partial_groups)

    def evaluate_data_quality(self):
        """Evaluate data quality metrics for duplicate resolution."""
        print("Evaluating data quality metrics...")

        quality_fields = [
            'birth_year', 'nationality', 'occupation', 'name_recognition',
            'accuracy_score', 'impact_score', 'person_name_ja'
        ]

        quality_scores = {}

        for idx, row in self.df.iterrows():
            score = 0
            details = {}

            # Field completeness (40% of quality score)
            filled_fields = sum(1 for field in quality_fields if pd.notna(row.get(field)) and str(row.get(field)).strip())
            completeness = (filled_fields / len(quality_fields)) * 40
            score += completeness
            details['completeness'] = completeness

            # Data accuracy indicators (30% of quality score)
            accuracy_score = row.get('accuracy_score', 0)
            if pd.notna(accuracy_score):
                accuracy = (float(accuracy_score) / 100) * 30
                score += accuracy
                details['accuracy'] = accuracy

            # Name quality (30% of quality score)
            name_quality = 0
            # Japanese name exists and looks proper
            if pd.notna(row.get('person_name_ja')) and len(str(row.get('person_name_ja')).strip()) > 0:
                name_quality += 15
            # Display name is different from base name (indicates processing)
            if (pd.notna(row.get('person_name_display')) and
                pd.notna(row.get('person_name')) and
                str(row.get('person_name_display')) != str(row.get('person_name'))):
                name_quality += 15
            score += name_quality
            details['name_quality'] = name_quality

            quality_scores[idx] = {
                'total_score': score,
                'details': details
            }

        self.quality_metrics = quality_scores

    def identify_root_causes(self):
        """Identify patterns and root causes of duplication."""
        print("Identifying root causes...")

        causes = {
            'data_source_conflicts': [],
            'naming_convention_issues': [],
            'import_merge_problems': [],
            'translation_inconsistencies': [],
            'group_vs_individual_confusion': [],
            'batch_processing_issues': []
        }

        # Analyze batch sources
        batch_sources = self.df['extended_data'].apply(
            lambda x: json.loads(x).get('original_batch_id', '') if pd.notna(x) else ''
        )
        batch_counts = Counter(batch_sources)

        # Check for batch processing issues
        if len(batch_counts) > 10:
            causes['batch_processing_issues'].append({
                'issue': 'Multiple batch sources detected',
                'count': len(batch_counts),
                'top_batches': dict(batch_counts.most_common(5))
            })

        # Analyze name field inconsistencies
        name_inconsistencies = 0
        for idx, row in self.df.iterrows():
            person_name = str(row.get('person_name', ''))
            display_name = str(row.get('person_name_display', ''))
            ja_name = str(row.get('person_name_ja', ''))

            # Check for translation inconsistencies
            if person_name and ja_name and person_name != ja_name:
                # Check if they look like different people entirely
                similarity = self.similarity_score(
                    self.normalize_name(person_name),
                    self.normalize_name(ja_name)
                )
                if similarity < 0.3:
                    name_inconsistencies += 1

        if name_inconsistencies > 50:
            causes['translation_inconsistencies'].append({
                'issue': 'High number of inconsistent name translations',
                'count': name_inconsistencies
            })

        # Check for group vs individual confusion
        group_indicators = self.df['person_name_display'].str.contains(r'\(.*\)', na=False).sum()
        if group_indicators > len(self.df) * 0.3:
            causes['group_vs_individual_confusion'].append({
                'issue': 'High percentage of entries with group indicators',
                'percentage': (group_indicators / len(self.df)) * 100
            })

        self.root_causes = causes

    def analyze_all_duplicates(self):
        """Run comprehensive duplicate analysis."""
        print("Starting comprehensive duplicate analysis...")

        self.load_data()
        self.analyze_exact_duplicates()
        self.analyze_similar_names()
        self.analyze_base_name_duplicates()
        self.analyze_group_member_duplicates()
        self.analyze_partial_matches()
        self.evaluate_data_quality()
        self.identify_root_causes()

    def generate_detailed_report(self):
        """Generate comprehensive analysis report."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Count total duplicates
        total_exact = sum(len(groups) for groups in self.duplicate_groups.get('exact', {}).values())
        total_similar = len(self.duplicate_groups.get('similar', {}))
        total_base_name = len(self.duplicate_groups.get('base_name', {}))
        total_group_members = len(self.duplicate_groups.get('group_members', {}))
        total_partial = len(self.duplicate_groups.get('partial', {}))

        report = {
            'analysis_timestamp': timestamp,
            'dataset_info': {
                'total_records': len(self.df),
                'unique_person_ids': self.df['person_id'].nunique(),
                'unique_person_names': self.df['person_name'].nunique(),
                'unique_display_names': self.df['person_name_display'].nunique(),
                'unique_japanese_names': self.df['person_name_ja'].nunique()
            },
            'duplicate_summary': {
                'exact_duplicates': {
                    'count': total_exact,
                    'groups': len([g for groups in self.duplicate_groups.get('exact', {}).values() for g in groups.keys()])
                },
                'similar_name_groups': total_similar,
                'base_name_duplicates': total_base_name,
                'group_member_duplicates': total_group_members,
                'partial_matches': total_partial
            },
            'duplicate_details': self.duplicate_groups,
            'quality_analysis': {
                'average_quality_score': sum(q['total_score'] for q in self.quality_metrics.values()) / len(self.quality_metrics),
                'high_quality_records': sum(1 for q in self.quality_metrics.values() if q['total_score'] > 80),
                'low_quality_records': sum(1 for q in self.quality_metrics.values() if q['total_score'] < 50)
            },
            'root_causes': self.root_causes,
            'recommendations': self.generate_recommendations()
        }

        return report

    def generate_recommendations(self):
        """Generate recommendations for duplicate resolution."""
        return {
            'immediate_actions': [
                'Remove exact duplicates keeping highest quality record',
                'Merge similar names with quality-based selection',
                'Standardize group member naming conventions',
                'Resolve translation inconsistencies'
            ],
            'prevention_strategies': [
                'Implement name normalization during import',
                'Add duplicate detection validation rules',
                'Standardize batch processing procedures',
                'Create name translation validation system'
            ],
            'quality_improvements': [
                'Prioritize records with higher accuracy_score',
                'Favor records with complete birth_year data',
                'Choose records with proper Japanese name translations',
                'Maintain records with better nationality information'
            ]
        }

    def find_high_confidence_duplicates(self):
        """Identify duplicates with high confidence for immediate removal."""
        print("Identifying high-confidence duplicates...")

        high_confidence = []

        # Exact matches with same person_id pattern
        for field, groups in self.duplicate_groups.get('exact', {}).items():
            for name, indices in groups.items():
                if len(indices) > 1:
                    records = self.df.iloc[indices]

                    # Check if they have different person_ids but are clearly the same person
                    if records['person_id'].nunique() > 1:
                        # Sort by quality score
                        quality_scores = [self.quality_metrics[idx]['total_score'] for idx in indices]
                        best_idx = indices[quality_scores.index(max(quality_scores))]
                        duplicates_to_remove = [idx for idx in indices if idx != best_idx]

                        high_confidence.append({
                            'type': 'exact_match',
                            'field': field,
                            'name': name,
                            'keep_record': best_idx,
                            'remove_records': duplicates_to_remove,
                            'confidence': 0.95
                        })

        return high_confidence

    def export_results(self):
        """Export analysis results to files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Generate comprehensive report
        report = self.generate_detailed_report()

        # Save JSON report
        json_path = f"DUPLICATE_ROOT_CAUSE_ANALYSIS_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False, default=str)

        # Generate markdown summary
        md_content = self.generate_markdown_report(report)
        md_path = f"DUPLICATE_ROOT_CAUSE_ANALYSIS_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        # Export high-confidence duplicates for immediate action
        high_confidence = self.find_high_confidence_duplicates()
        hc_path = f"HIGH_CONFIDENCE_DUPLICATES_{timestamp}.json"
        with open(hc_path, 'w', encoding='utf-8') as f:
            json.dump(high_confidence, f, indent=2, ensure_ascii=False, default=str)

        print(f"Analysis complete! Results saved to:")
        print(f"- Detailed JSON: {json_path}")
        print(f"- Summary Report: {md_path}")
        print(f"- High Confidence: {hc_path}")

        return json_path, md_path, hc_path

    def generate_markdown_report(self, report: dict) -> str:
        """Generate markdown summary report."""
        md = f"""# Ultra Think Database Duplicate Root Cause Analysis

## Analysis Summary
**Analysis Date**: {report['analysis_timestamp']}
**Dataset**: {report['dataset_info']['total_records']} total records

## Duplicate Detection Results

### Overview
- **Exact Duplicates**: {report['duplicate_summary']['exact_duplicates']['count']} records in {report['duplicate_summary']['exact_duplicates']['groups']} groups
- **Similar Name Groups**: {report['duplicate_summary']['similar_name_groups']} groups
- **Base Name Duplicates**: {report['duplicate_summary']['base_name_duplicates']} groups
- **Group Member Duplicates**: {report['duplicate_summary']['group_member_duplicates']} members
- **Partial Matches**: {report['duplicate_summary']['partial_matches']} pairs

### Data Quality Assessment
- **Average Quality Score**: {report['quality_analysis']['average_quality_score']:.1f}/100
- **High Quality Records** (>80): {report['quality_analysis']['high_quality_records']}
- **Low Quality Records** (<50): {report['quality_analysis']['low_quality_records']}

## Root Cause Analysis

### Identified Patterns
"""

        for cause_type, causes in report['root_causes'].items():
            if causes:
                md += f"\n#### {cause_type.replace('_', ' ').title()}\n"
                for cause in causes:
                    if isinstance(cause, dict):
                        md += f"- **{cause.get('issue', 'Unknown issue')}**"
                        if 'count' in cause:
                            md += f" (Count: {cause['count']})"
                        if 'percentage' in cause:
                            md += f" (Percentage: {cause['percentage']:.1f}%)"
                        md += "\n"

        md += f"""
## Recommendations

### Immediate Actions
"""
        for action in report['recommendations']['immediate_actions']:
            md += f"- {action}\n"

        md += f"""
### Prevention Strategies
"""
        for strategy in report['recommendations']['prevention_strategies']:
            md += f"- {strategy}\n"

        md += f"""
### Quality Improvement Guidelines
"""
        for guideline in report['recommendations']['quality_improvements']:
            md += f"- {guideline}\n"

        return md


def main():
    """Main execution function."""
    csv_path = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_FOREIGN_NAMES_CORRECTED_20250831_140703.csv"

    analyzer = DuplicateRootCauseAnalyzer(csv_path)

    try:
        analyzer.analyze_all_duplicates()
        json_path, md_path, hc_path = analyzer.export_results()

        print("\n" + "="*60)
        print("DUPLICATE ROOT CAUSE ANALYSIS COMPLETE")
        print("="*60)

        # Print summary statistics
        report = analyzer.generate_detailed_report()
        print(f"\nDataset: {report['dataset_info']['total_records']} records")
        print(f"Exact duplicates: {report['duplicate_summary']['exact_duplicates']['count']}")
        print(f"Similar groups: {report['duplicate_summary']['similar_name_groups']}")
        print(f"Base name duplicates: {report['duplicate_summary']['base_name_duplicates']}")
        print(f"Group member duplicates: {report['duplicate_summary']['group_member_duplicates']}")
        print(f"Partial matches: {report['duplicate_summary']['partial_matches']}")

        print(f"\nAverage quality score: {report['quality_analysis']['average_quality_score']:.1f}/100")
        print(f"High quality records: {report['quality_analysis']['high_quality_records']}")
        print(f"Low quality records: {report['quality_analysis']['low_quality_records']}")

        return True

    except Exception as e:
        print(f"Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    main()
