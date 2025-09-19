#!/usr/bin/env python3
"""
Comprehensive Recognition Analysis for Ultra Think Database
Analyzes name_recognition field distribution and identifies patterns in low-recognition entries
"""

import pandas as pd
import numpy as np
import json
from collections import Counter, defaultdict
from datetime import datetime
import re

def load_database():
    """Load the latest Ultra Think database"""
    filename = "ultra_think_FINAL_COMPLETE_FICTIONAL_20250901_005521.csv"
    try:
        df = pd.read_csv(filename)
        print(f"✅ Loaded database: {len(df)} records from {filename}")
        return df
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return None

def analyze_recognition_distribution(df):
    """Analyze the distribution of name_recognition scores"""
    print("\n📊 RECOGNITION SCORE DISTRIBUTION ANALYSIS")
    print("=" * 50)
    
    # Basic statistics
    recognition_scores = df['name_recognition'].dropna()
    
    stats = {
        'total_records': len(df),
        'records_with_recognition': len(recognition_scores),
        'min_score': float(recognition_scores.min()),
        'max_score': float(recognition_scores.max()),
        'mean_score': float(recognition_scores.mean()),
        'median_score': float(recognition_scores.median()),
        'std_score': float(recognition_scores.std())
    }
    
    print(f"Total Records: {stats['total_records']:,}")
    print(f"Records with Recognition Score: {stats['records_with_recognition']:,}")
    print(f"Score Range: {stats['min_score']:.1f} - {stats['max_score']:.1f}")
    print(f"Mean Score: {stats['mean_score']:.2f}")
    print(f"Median Score: {stats['median_score']:.1f}")
    print(f"Standard Deviation: {stats['std_score']:.2f}")
    
    # Score distribution by bins
    print(f"\n📈 SCORE DISTRIBUTION (by ranges)")
    bins = [0, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85, 90, 95, 100]
    counts, _ = np.histogram(recognition_scores, bins=bins)
    
    for i in range(len(bins)-1):
        count = counts[i]
        percentage = (count / len(recognition_scores)) * 100
        print(f"{bins[i]:2d}-{bins[i+1]:2d}: {count:4d} records ({percentage:5.1f}%)")
    
    # Exact score frequency (top 20)
    print(f"\n🔢 TOP 20 EXACT SCORES")
    score_counts = Counter(recognition_scores)
    for score, count in score_counts.most_common(20):
        percentage = (count / len(recognition_scores)) * 100
        print(f"Score {score:4.1f}: {count:4d} records ({percentage:5.1f}%)")
    
    return stats, score_counts

def analyze_low_recognition_patterns(df, threshold=40):
    """Analyze patterns in low-recognition entries"""
    print(f"\n🔍 LOW RECOGNITION ANALYSIS (Score ≤ {threshold})")
    print("=" * 50)
    
    # Filter low recognition entries
    low_rec = df[df['name_recognition'] <= threshold].copy()
    
    print(f"Low Recognition Entries: {len(low_rec):,} ({len(low_rec)/len(df)*100:.1f}% of total)")
    
    # Occupation patterns
    print(f"\n👔 OCCUPATION PATTERNS (Low Recognition)")
    occupation_counts = Counter(low_rec['occupation'].dropna())
    for occ, count in occupation_counts.most_common(15):
        percentage = (count / len(low_rec)) * 100
        print(f"{occ:<25}: {count:4d} ({percentage:5.1f}%)")
    
    # Nationality patterns
    print(f"\n🌍 NATIONALITY PATTERNS (Low Recognition)")
    nationality_counts = Counter(low_rec['nationality'].dropna())
    for nat, count in nationality_counts.most_common(15):
        percentage = (count / len(low_rec)) * 100
        print(f"{nat:<15}: {count:4d} ({percentage:5.1f}%)")
    
    # Name pattern analysis
    print(f"\n📝 NAME PATTERN ANALYSIS (Low Recognition)")
    
    # Check for placeholder-like patterns
    patterns = {
        'underscore_numbers': r'.*_\d+$',
        'sequential_numbers': r'.*\d{3,4}$',
        'generic_person': r'.*(Person|人|Player|選手).*\d+',
        'test_patterns': r'.*(Test|テスト|Sample|サンプル).*',
        'unknown_patterns': r'.*(Unknown|不明|匿名).*',
        'placeholder_patterns': r'.*(Placeholder|プレースホルダー).*'
    }
    
    pattern_results = {}
    for pattern_name, pattern in patterns.items():
        matches = low_rec[
            low_rec['person_name'].str.contains(pattern, na=False, case=False) |
            low_rec['person_name_ja'].str.contains(pattern, na=False, case=False) |
            low_rec['person_name_display'].str.contains(pattern, na=False, case=False)
        ]
        pattern_results[pattern_name] = len(matches)
        if len(matches) > 0:
            print(f"{pattern_name:<20}: {len(matches):4d} matches")
            # Show examples
            for _, row in matches.head(3).iterrows():
                print(f"  Example: {row['person_name']} / {row['person_name_ja']}")
    
    return low_rec, pattern_results

def analyze_minimal_data_entries(df):
    """Analyze entries with minimal or suspicious data"""
    print(f"\n⚠️  MINIMAL DATA ANALYSIS")
    print("=" * 50)
    
    minimal_issues = {
        'empty_person_name': len(df[df['person_name'].isna() | (df['person_name'] == '')]),
        'empty_person_name_ja': len(df[df['person_name_ja'].isna() | (df['person_name_ja'] == '')]),
        'empty_person_name_display': len(df[df['person_name_display'].isna() | (df['person_name_display'] == '')]),
        'missing_birth_year': len(df[df['birth_year'].isna() | (df['birth_year'] == '')]),
        'missing_occupation': len(df[df['occupation'].isna() | (df['occupation'] == '')]),
        'missing_nationality': len(df[df['nationality'].isna() | (df['nationality'] == '')])
    }
    
    print("Missing Field Analysis:")
    for field, count in minimal_issues.items():
        percentage = (count / len(df)) * 100
        print(f"{field:<25}: {count:4d} ({percentage:5.1f}%)")
    
    # Find records with multiple missing fields
    critical_cols = ['person_name', 'person_name_ja', 'person_name_display', 'occupation']
    missing_counts = df[critical_cols].isna().sum(axis=1)
    
    print(f"\nRecords with Multiple Missing Critical Fields:")
    for missing_count in range(1, len(critical_cols) + 1):
        count = len(df[missing_counts == missing_count])
        if count > 0:
            percentage = (count / len(df)) * 100
            print(f"{missing_count} missing fields: {count:4d} ({percentage:5.1f}%)")
    
    # Show examples of problematic entries
    problematic = df[missing_counts >= 2]
    if len(problematic) > 0:
        print(f"\n🚨 PROBLEMATIC ENTRIES (≥2 missing critical fields):")
        for _, row in problematic.head(10).iterrows():
            print(f"  {row['person_id']}: '{row['person_name']}' / '{row['person_name_ja']}' - {row['occupation']}")
    
    return minimal_issues, problematic

def analyze_metadata_anomalies(df):
    """Analyze metadata anomalies that might indicate batch generation"""
    print(f"\n🕒 METADATA ANOMALY ANALYSIS")
    print("=" * 50)
    
    # Check for batch_id patterns
    if 'batch_id' in df.columns:
        batch_patterns = Counter(df['batch_id'].dropna())
        print("Batch ID Patterns:")
        for batch_id, count in batch_patterns.most_common(10):
            percentage = (count / len(df)) * 100
            print(f"{batch_id:<30}: {count:4d} ({percentage:5.1f}%)")
    
    # Check for person_id patterns
    person_ids = df['person_id'].dropna()
    
    # Check for sequential IDs
    numeric_ids = []
    for pid in person_ids:
        match = re.search(r'(\d+)', str(pid))
        if match:
            numeric_ids.append(int(match.group(1)))
    
    if numeric_ids:
        numeric_ids.sort()
        gaps = [numeric_ids[i+1] - numeric_ids[i] for i in range(len(numeric_ids)-1)]
        gap_stats = {
            'sequential_count': sum(1 for gap in gaps if gap == 1),
            'total_gaps': len(gaps),
            'max_gap': max(gaps) if gaps else 0,
            'min_gap': min(gaps) if gaps else 0
        }
        
        print(f"\nPerson ID Sequential Analysis:")
        print(f"Sequential IDs (gap=1): {gap_stats['sequential_count']:,} ({gap_stats['sequential_count']/gap_stats['total_gaps']*100:.1f}%)")
        print(f"Max gap: {gap_stats['max_gap']:,}")
        print(f"Min gap: {gap_stats['min_gap']:,}")
    
    return batch_patterns if 'batch_id' in df.columns else {}, gap_stats if numeric_ids else {}

def identify_deletion_candidates(df, recognition_threshold=35):
    """Identify strong candidates for deletion based on multiple criteria"""
    print(f"\n🎯 DELETION CANDIDATE IDENTIFICATION")
    print("=" * 50)
    
    deletion_criteria = {}
    
    # 1. Extremely low recognition (bottom 5%)
    low_percentile = np.percentile(df['name_recognition'].dropna(), 5)
    extremely_low_rec = df[df['name_recognition'] <= low_percentile]
    deletion_criteria['extremely_low_recognition'] = len(extremely_low_rec)
    
    # 2. Empty critical fields
    empty_name = df[df['person_name'].isna() | (df['person_name'] == '')]
    deletion_criteria['empty_person_name'] = len(empty_name)
    
    # 3. Placeholder patterns in names
    placeholder_patterns = [
        r'.*_\d{3,4}$',           # name_1234
        r'.*(Test|テスト).*',       # test entries
        r'.*(Unknown|不明).*',     # unknown entries
        r'P_UNKNOWN.*',           # P_UNKNOWN patterns
        r'.*プレースホルダー.*'      # placeholder in Japanese
    ]
    
    pattern_matches = pd.Series([False] * len(df))
    for pattern in placeholder_patterns:
        pattern_matches |= (
            df['person_name'].str.contains(pattern, na=False, case=False) |
            df['person_name_ja'].str.contains(pattern, na=False, case=False) |
            df['person_name_display'].str.contains(pattern, na=False, case=False)
        )
    
    placeholder_names = df[pattern_matches]
    deletion_criteria['placeholder_patterns'] = len(placeholder_names)
    
    # 4. Combined high-risk criteria
    high_risk = df[
        (df['name_recognition'] <= recognition_threshold) &
        (
            (df['person_name'].isna() | (df['person_name'] == '')) |
            pattern_matches |
            (df['occupation'].isna() | (df['occupation'] == ''))
        )
    ]
    deletion_criteria['high_risk_combined'] = len(high_risk)
    
    print("Deletion Candidate Categories:")
    for criteria, count in deletion_criteria.items():
        percentage = (count / len(df)) * 100
        print(f"{criteria:<25}: {count:4d} ({percentage:5.1f}%)")
    
    # Show specific examples for each category
    print(f"\n📋 SPECIFIC EXAMPLES")
    
    if len(extremely_low_rec) > 0:
        print(f"\nExtremely Low Recognition (≤{low_percentile:.1f}):")
        for _, row in extremely_low_rec.head(5).iterrows():
            print(f"  {row['person_id']}: {row['person_name']} / {row['person_name_ja']} (Score: {row['name_recognition']})")
    
    if len(empty_name) > 0:
        print(f"\nEmpty Person Name:")
        for _, row in empty_name.head(5).iterrows():
            print(f"  {row['person_id']}: '{row['person_name']}' / {row['person_name_ja']}")
    
    if len(placeholder_names) > 0:
        print(f"\nPlaceholder Patterns:")
        for _, row in placeholder_names.head(5).iterrows():
            print(f"  {row['person_id']}: {row['person_name']} / {row['person_name_ja']}")
    
    return deletion_criteria, high_risk

def analyze_correlation_patterns(df):
    """Analyze correlations between recognition scores and other fields"""
    print(f"\n🔗 CORRELATION ANALYSIS")
    print("=" * 50)
    
    # Recognition score by occupation
    print("Average Recognition Score by Occupation (Top 15):")
    occ_recognition = df.groupby('occupation')['name_recognition'].agg(['mean', 'count']).round(2)
    occ_recognition = occ_recognition[occ_recognition['count'] >= 5]  # Only occupations with 5+ entries
    occ_recognition_sorted = occ_recognition.sort_values('mean', ascending=False)
    
    for occ, row in occ_recognition_sorted.head(15).iterrows():
        print(f"{occ:<25}: {row['mean']:5.1f} (n={row['count']:3d})")
    
    # Recognition score by nationality
    print(f"\nAverage Recognition Score by Nationality (Top 10):")
    nat_recognition = df.groupby('nationality')['name_recognition'].agg(['mean', 'count']).round(2)
    nat_recognition = nat_recognition[nat_recognition['count'] >= 10]  # Only nationalities with 10+ entries
    nat_recognition_sorted = nat_recognition.sort_values('mean', ascending=False)
    
    for nat, row in nat_recognition_sorted.head(10).iterrows():
        print(f"{nat:<15}: {row['mean']:5.1f} (n={row['count']:3d})")
    
    # Low recognition occupations (potential red flags)
    print(f"\nLowest Recognition Occupations (Potential Red Flags):")
    low_occ = occ_recognition_sorted.tail(10)
    for occ, row in low_occ.iterrows():
        print(f"{occ:<25}: {row['mean']:5.1f} (n={row['count']:3d})")
    
    return occ_recognition_sorted, nat_recognition_sorted

def generate_comprehensive_report(df, stats, deletion_criteria, low_rec_df):
    """Generate comprehensive analysis report"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    report = {
        'analysis_timestamp': timestamp,
        'database_info': {
            'filename': 'ultra_think_FINAL_COMPLETE_FICTIONAL_20250901_005521.csv',
            'total_records': len(df),
            'analysis_date': datetime.now().isoformat()
        },
        'recognition_statistics': stats,
        'deletion_analysis': deletion_criteria,
        'low_recognition_summary': {
            'threshold_40_count': len(df[df['name_recognition'] <= 40]),
            'threshold_35_count': len(df[df['name_recognition'] <= 35]),
            'bottom_10_percent': len(df[df['name_recognition'] <= np.percentile(df['name_recognition'].dropna(), 10)]),
            'bottom_5_percent': len(df[df['name_recognition'] <= np.percentile(df['name_recognition'].dropna(), 5)])
        },
        'quality_flags': {
            'extremely_low_recognition': len(df[df['name_recognition'] <= 30]),
            'missing_critical_data': len(df[(df['person_name'].isna()) | (df['person_name'] == '')]),
            'suspicious_patterns': deletion_criteria['placeholder_patterns']
        },
        'recommendations': {
            'safe_deletion_threshold': 35,
            'review_required_threshold': 40,
            'estimated_false_positives': 'Low (most score=35 entries are legitimate VTubers/YouTubers)',
            'priority_deletion_categories': [
                'Empty person_name fields',
                'Placeholder patterns (P_UNKNOWN, _digits)',
                'Test/Sample entries'
            ]
        }
    }
    
    # Save detailed report
    report_filename = f"COMPREHENSIVE_RECOGNITION_ANALYSIS_{timestamp}.json"
    with open(report_filename, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 REPORT SAVED: {report_filename}")
    
    return report, report_filename

def main():
    """Main analysis function"""
    print("🔍 ULTRA THINK DATABASE COMPREHENSIVE RECOGNITION ANALYSIS")
    print("=" * 60)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Load database
    df = load_database()
    if df is None:
        return
    
    # 1. Recognition distribution analysis
    stats, score_counts = analyze_recognition_distribution(df)
    
    # 2. Low recognition pattern analysis
    low_rec_df, pattern_results = analyze_low_recognition_patterns(df, threshold=40)
    
    # 3. Minimal data analysis
    minimal_issues, problematic_entries = analyze_minimal_data_entries(df)
    
    # 4. Metadata anomaly analysis
    batch_patterns, id_patterns = analyze_metadata_anomalies(df)
    
    # 5. Correlation analysis
    occ_correlation, nat_correlation = analyze_correlation_patterns(df)
    
    # 6. Deletion candidate identification
    deletion_criteria, high_risk_entries = identify_deletion_candidates(df, recognition_threshold=35)
    
    # 7. Generate comprehensive report
    report, report_filename = generate_comprehensive_report(df, stats, deletion_criteria, low_rec_df)
    
    print(f"\n🎯 FINAL RECOMMENDATIONS")
    print("=" * 50)
    print("1. SAFE TO DELETE:")
    print("   - Empty person_name entries (immediate deletion)")
    print("   - Confirmed placeholder patterns (P_UNKNOWN, _digits)")
    print("   - Test/Sample entries")
    print(f"   - Estimated total: ~{deletion_criteria['high_risk_combined']} records")
    
    print("\n2. REQUIRES REVIEW:")
    print("   - Score ≤35 VTubers/YouTubers (legitimate but low recognition)")
    print("   - Foreign musicians with score 35 (verify legitimacy)")
    print("   - Missing birth year + low score combination")
    
    print("\n3. KEEP:")
    print("   - All scores >40 (generally legitimate)")
    print("   - Known Japanese entertainers regardless of score")
    print("   - Historical figures even with missing birth years")
    
    print(f"\n📊 ANALYSIS COMPLETE - Report saved as: {report_filename}")

if __name__ == "__main__":
    main()