#!/usr/bin/env python3
"""
Group Violation Detection Script
Identifies groups incorrectly registered as persons in the database
"""

import pandas as pd
import re
from typing import List, Dict, Any

def identify_group_violations(csv_file: str) -> Dict[str, Any]:
    """
    Identify groups that are incorrectly registered as persons
    """
    # Load database
    df = pd.read_csv(csv_file, encoding='utf-8-sig')

    # Known group patterns and names
    known_groups = [
        'スカイピース', 'SkyPeace',
        'フィッシャーズ', 'Fischer\'s',
        '東海オンエア', 'Tokai On Air',
        'コムドット', 'Com Dot',
        '水溜りボンド', 'Mizutamari Bond',
        'QuizKnock', 'クイズノック',
        'ばんばんざい',
        'ヴァンゆん',
        'ONE OK ROCK',
        'ARASHI', '嵐',
        'BTS',
        'TWICE',
        'BLACKPINK'
    ]

    # Group indicator patterns
    group_patterns = [
        r'.*ーズ$',  # ~ers (フィッシャーズ等)
        r'.*バンド$',  # bands
        r'.*グループ$',  # groups
        r'.*チーム$',  # teams
        r'.*ユニット$',  # units
    ]

    violations = []

    # Check each record
    for idx, row in df.iterrows():
        person_id = row.get('person_id', '')
        person_name = str(row.get('person_name', ''))
        person_name_display = str(row.get('person_name_display', ''))
        person_name_ja = str(row.get('person_name_ja', ''))
        entity_type = str(row.get('entity_type', ''))

        # Skip if not classified as person
        if entity_type != 'person':
            continue

        is_violation = False
        violation_reason = []

        # Check against known groups
        for group in known_groups:
            if (group in person_name_display or
                group in person_name or
                group in person_name_ja):
                is_violation = True
                violation_reason.append(f"Known group: {group}")
                break

        # Check against group patterns
        if not is_violation:
            for pattern in group_patterns:
                if (re.match(pattern, person_name_display) or
                    re.match(pattern, person_name_ja)):
                    is_violation = True
                    violation_reason.append(f"Group pattern: {pattern}")
                    break

        # Additional heuristics for group detection
        if not is_violation:
            # Check for collective nouns or band-like names
            collective_indicators = [
                'Band', 'Group', 'Team', 'Unit', 'Collective',
                'Duo', 'Trio', 'Quartet',
                'Orchestra', 'Ensemble', 'Crew'
            ]

            for indicator in collective_indicators:
                if indicator in person_name or indicator in person_name_display:
                    is_violation = True
                    violation_reason.append(f"Collective indicator: {indicator}")
                    break

        if is_violation:
            violations.append({
                'person_id': person_id,
                'person_name': person_name,
                'person_name_display': person_name_display,
                'person_name_ja': person_name_ja,
                'entity_type': entity_type,
                'violation_reason': '; '.join(violation_reason),
                'recommendation': 'DELETE - Group incorrectly classified as person'
            })

    return {
        'total_records': len(df),
        'violations_found': len(violations),
        'violation_rate': len(violations) / len(df) * 100,
        'violations': violations
    }

def find_individual_members(csv_file: str, group_name: str) -> List[Dict]:
    """
    Find individual members of a group
    """
    df = pd.read_csv(csv_file, encoding='utf-8-sig')

    members = []
    for idx, row in df.iterrows():
        person_name_display = str(row.get('person_name_display', ''))

        # Look for members with group name in parentheses
        if f"({group_name})" in person_name_display or f"（{group_name}）" in person_name_display:
            members.append({
                'person_id': row.get('person_id', ''),
                'person_name': row.get('person_name', ''),
                'person_name_display': person_name_display,
                'member_status': 'CORRECT - Individual member with group attribution'
            })

    return members

def main():
    """Main analysis function"""
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_MASSIVE_CLEANED_20250912_035645.csv"

    print("🔍 Group Violation Detection Analysis")
    print("=" * 50)

    # Identify violations
    results = identify_group_violations(csv_file)

    print(f"📊 Analysis Results:")
    print(f"Total records analyzed: {results['total_records']:,}")
    print(f"Group violations found: {results['violations_found']}")
    print(f"Violation rate: {results['violation_rate']:.2f}%")
    print()

    # Report violations
    if results['violations']:
        print("🚨 GROUP VIOLATIONS DETECTED:")
        print("-" * 50)

        for violation in results['violations']:
            print(f"ID: {violation['person_id']}")
            print(f"Name: {violation['person_name']}")
            print(f"Display: {violation['person_name_display']}")
            print(f"Japanese: {violation['person_name_ja']}")
            print(f"Reason: {violation['violation_reason']}")
            print(f"Action: {violation['recommendation']}")

            # Check for individual members
            group_candidates = ['スカイピース', 'フィッシャーズ', '東海オンエア', '水溜りボンド']
            for group in group_candidates:
                if group in violation['person_name_display']:
                    members = find_individual_members(csv_file, group)
                    if members:
                        print(f"✅ Individual members found for {group}:")
                        for member in members:
                            print(f"  - {member['person_id']}: {member['person_name_display']}")
                    break

            print("-" * 30)

    # Specific SkyPeace analysis
    print("\n🎯 SKYPIECE (P002026) SPECIFIC ANALYSIS:")
    print("-" * 50)

    skypiece_members = find_individual_members(csv_file, 'スカイピース')
    if skypiece_members:
        print("✅ SkyPeace individual members correctly registered:")
        for member in skypiece_members:
            print(f"  {member['person_id']}: {member['person_name_display']}")

    # Find the violation
    skypiece_violation = next((v for v in results['violations'] if 'P002026' in v['person_id']), None)
    if skypiece_violation:
        print(f"❌ Group violation: P002026 - {skypiece_violation['person_name_display']}")
        print("📋 RECOMMENDATION: DELETE P002026 (group entry)")
        print("📋 KEEP: Individual members with correct group attribution")

    print("\n📝 SUMMARY RECOMMENDATION:")
    print("1. DELETE all group entries identified as violations")
    print("2. PRESERVE individual members with group names in parentheses")
    print("3. IMPLEMENT validation rules to prevent future group registrations")

if __name__ == "__main__":
    main()
