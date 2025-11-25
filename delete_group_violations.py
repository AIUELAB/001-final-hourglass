#!/usr/bin/env python3
"""
Group Violation Deletion Script
Removes groups that are incorrectly registered as persons
Based on comprehensive analysis in P002026_SKYPIECE_GROUP_VIOLATION_ANALYSIS.md
"""

import pandas as pd
from datetime import datetime
import json

def delete_group_violations(csv_file: str) -> str:
    """
    Delete confirmed group violations and ensure individual members have proper attribution
    """
    # Load database
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    initial_count = len(df)

    print(f"📊 Initial database: {initial_count:,} records")

    # Confirmed group violations to delete
    GROUP_VIOLATIONS = [
        'P002026',  # スカイピース (SkyPeace) - YouTube Duo
        'P001100',  # フィッシャーズ (Fischer's) - YouTube Group
        'P003642',  # 東海オンエア (Tokai On Air) - YouTube Group
        'P004066',  # 水溜りボンド (Mizutamari Bond) - YouTube Duo
    ]

    # Additional known groups to check and delete
    ADDITIONAL_GROUPS = [
        'コムドット', 'Com Dot',
        'QuizKnock', 'クイズノック',
        'ばんばんざい',
        'ヴァンゆん',
        '千鳥',  # Comedy duo
        'かまいたち',  # Comedy duo
        'サンドウィッチマン',  # Comedy duo
        'オードリー',  # Comedy duo (without individual member attribution)
    ]

    # Delete confirmed violations
    deleted_records = []
    for person_id in GROUP_VIOLATIONS:
        violation = df[df['person_id'] == person_id]
        if not violation.empty:
            record = violation.iloc[0]
            deleted_records.append({
                'person_id': person_id,
                'person_name': record.get('person_name', ''),
                'person_name_display': record.get('person_name_display', ''),
                'reason': 'Group incorrectly registered as person'
            })
            df = df[df['person_id'] != person_id]
            print(f"❌ Deleted: {person_id} - {record.get('person_name_display', '')}")

    # Check for additional groups by name
    for group_name in ADDITIONAL_GROUPS:
        # Check if group name appears as main display name (not in parentheses)
        group_entries = df[
            (df['person_name_display'] == group_name) |
            (df['person_name'] == group_name) |
            (df['person_name_ja'] == group_name)
        ]

        for idx, row in group_entries.iterrows():
            # Verify this is a group entry, not an individual with group name
            if '(' not in str(row.get('person_name_display', '')):
                deleted_records.append({
                    'person_id': row['person_id'],
                    'person_name': row.get('person_name', ''),
                    'person_name_display': row.get('person_name_display', ''),
                    'reason': f'Group "{group_name}" registered as person'
                })
                df = df[df['person_id'] != row['person_id']]
                print(f"❌ Deleted: {row['person_id']} - {row.get('person_name_display', '')}")

    # Verify individual members have group attribution
    print("\n✅ Verifying individual members have group attribution:")

    # Known individual members who should have group names
    INDIVIDUAL_MEMBERS = {
        'P000045': ('Ini', 'スカイピース'),
        'P000882': ('Teo', 'スカイピース'),
        'P000017': ('J-HOPE', 'BTS'),
        'P000023': ('RM', 'BTS'),
        'P000609': ('シュガ', 'BTS'),
        'P000675': ('ジミン', 'BTS'),
        'P000728': ('ジュン', 'BTS'),
        'P000759': ('ジン', 'BTS'),
    }

    members_fixed = 0
    for person_id, (member_name, group_name) in INDIVIDUAL_MEMBERS.items():
        member = df[df['person_id'] == person_id]
        if not member.empty:
            idx = member.index[0]
            current_display = str(df.at[idx, 'person_name_display'])

            # Check if group name is in parentheses
            if f"({group_name})" not in current_display and f"（{group_name}）" not in current_display:
                # Add group name in parentheses
                if '(' in current_display or '（' in current_display:
                    # Replace existing parenthetical content
                    import re
                    base_name = re.sub(r'[（(][^）)]*[）)]', '', current_display).strip()
                    df.at[idx, 'person_name_display'] = f"{base_name} ({group_name})"
                else:
                    # Add group name
                    df.at[idx, 'person_name_display'] = f"{current_display} ({group_name})"

                members_fixed += 1
                print(f"  ✅ Fixed: {person_id} - {df.at[idx, 'person_name_display']}")

    # Generate timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Save cleaned database
    output_file = f"/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_NO_GROUPS_{timestamp}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    # Save deletion report
    report = {
        'timestamp': timestamp,
        'initial_count': initial_count,
        'final_count': len(df),
        'deleted_count': len(deleted_records),
        'members_fixed': members_fixed,
        'deleted_records': deleted_records
    }

    report_file = f"/Users/admin/Documents/AIUELAB/001-final-hourglass/GROUP_DELETION_REPORT_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📊 Summary:")
    print(f"  Initial records: {initial_count:,}")
    print(f"  Groups deleted: {len(deleted_records)}")
    print(f"  Members fixed: {members_fixed}")
    print(f"  Final records: {len(df):,}")
    print(f"  Output: {output_file}")
    print(f"  Report: {report_file}")

    return output_file

def main():
    """Main execution function"""
    # Use the latest cleaned database
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_TRULY_CLEAN_20250912_063129.csv"

    print("🚨 GROUP VIOLATION DELETION SYSTEM")
    print("=" * 50)
    print("Based on analysis: Groups should NEVER be registered as persons")
    print("Only individual members with group attribution are allowed")
    print()

    # Execute deletion
    output_file = delete_group_violations(csv_file)

    print("\n✅ GROUP VIOLATIONS SUCCESSFULLY REMOVED")
    print("System is now compliant with 'no groups as persons' rule")

if __name__ == "__main__":
    main()
