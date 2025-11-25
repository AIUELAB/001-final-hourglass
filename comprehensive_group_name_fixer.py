#!/usr/bin/env python3
"""
Comprehensive Group Name Fixer for Ultra Think Database
包括的グループ名修正システム

This system fixes all group member display names to ensure consistent
parenthetical notation across the database.
"""

import pandas as pd
import numpy as np
import json
from datetime import datetime
from typing import Dict, List, Tuple, Any
import shutil
from group_member_database import (
    GROUP_MEMBERS_DATABASE,
    get_group_for_person,
    get_correct_display_name,
    should_have_group_notation
)

class ComprehensiveGroupNameFixer:
    """グループ名の括弧表記を包括的に修正"""

    def __init__(self, csv_file: str):
        self.csv_file = csv_file
        self.df = None
        self.fix_log = []
        self.statistics = {
            'total_records': 0,
            'groups_found': 0,
            'fixes_applied': 0,
            'already_correct': 0,
            'inconsistencies_fixed': 0,
            'groups_processed': set(),
            'fixed_by_group': {}
        }

    def load_data(self):
        """データベースを読み込み"""
        print(f"📂 Loading database from {self.csv_file}...")
        self.df = pd.read_csv(self.csv_file, encoding='utf-8')
        self.statistics['total_records'] = len(self.df)
        print(f"✅ Loaded {len(self.df)} records")

    def analyze_current_state(self):
        """現在の括弧表記状況を分析"""
        print("\n🔍 Analyzing current group notation state...")

        analysis = {
            'missing_notation': [],
            'has_notation': [],
            'inconsistent_groups': {}
        }

        # グループメンバーをチェック
        for group, members in GROUP_MEMBERS_DATABASE.items():
            group_status = {'with_notation': [], 'without_notation': []}

            for person_id, member_name in members.items():
                record = self.df[self.df['person_id'] == person_id]
                if not record.empty:
                    display = record.iloc[0]['person_name_display']
                    has_notation = f'({group})' in display or f'（{group}）' in display

                    if has_notation:
                        group_status['with_notation'].append({
                            'person_id': person_id,
                            'name': member_name,
                            'display': display
                        })
                        analysis['has_notation'].append(person_id)
                    else:
                        group_status['without_notation'].append({
                            'person_id': person_id,
                            'name': member_name,
                            'display': display
                        })
                        analysis['missing_notation'].append(person_id)

            # グループ内の不一致をチェック
            if group_status['with_notation'] and group_status['without_notation']:
                analysis['inconsistent_groups'][group] = group_status
                self.statistics['inconsistencies_fixed'] += len(group_status['without_notation'])

        # 統計を更新
        self.statistics['groups_found'] = len(GROUP_MEMBERS_DATABASE)

        # 分析結果を表示
        print(f"\n📊 Current State Analysis:")
        print(f"   Total groups defined: {len(GROUP_MEMBERS_DATABASE)}")
        print(f"   Members with notation: {len(analysis['has_notation'])}")
        print(f"   Members missing notation: {len(analysis['missing_notation'])}")
        print(f"   Groups with inconsistencies: {len(analysis['inconsistent_groups'])}")

        if analysis['inconsistent_groups']:
            print(f"\n⚠️ Inconsistent Groups:")
            for group, status in analysis['inconsistent_groups'].items():
                print(f"   {group}:")
                print(f"     ✅ With notation: {len(status['with_notation'])}")
                print(f"     ❌ Missing notation: {len(status['without_notation'])}")
                for member in status['without_notation'][:3]:  # Show first 3
                    print(f"        - {member['person_id']}: {member['display']}")

        return analysis

    def fix_group_notations(self):
        """すべてのグループメンバーの表記を修正"""
        print("\n🔧 Fixing group notations...")

        fixes_applied = 0
        already_correct = 0

        # すべてのグループをチェック
        for group, members in GROUP_MEMBERS_DATABASE.items():
            group_fixes = 0

            for person_id, member_name in members.items():
                # レコードを検索
                mask = self.df['person_id'] == person_id
                if not self.df[mask].empty:
                    idx = self.df[mask].index[0]
                    current_display = self.df.loc[idx, 'person_name_display']

                    # 正しい表記を生成
                    correct_display = get_correct_display_name(person_id, current_display)

                    # 修正が必要か確認
                    if current_display != correct_display:
                        # 修正を適用
                        self.df.loc[idx, 'person_name_display'] = correct_display

                        # ログに記録
                        self.fix_log.append({
                            'person_id': person_id,
                            'person_name': self.df.loc[idx, 'person_name'],
                            'group': group,
                            'before': current_display,
                            'after': correct_display,
                            'timestamp': datetime.now().isoformat()
                        })

                        fixes_applied += 1
                        group_fixes += 1

                        print(f"   ✅ Fixed {person_id}: {current_display} → {correct_display}")
                    else:
                        already_correct += 1

            if group_fixes > 0:
                self.statistics['groups_processed'].add(group)
                self.statistics['fixed_by_group'][group] = group_fixes

        self.statistics['fixes_applied'] = fixes_applied
        self.statistics['already_correct'] = already_correct

        print(f"\n📈 Fix Summary:")
        print(f"   Total fixes applied: {fixes_applied}")
        print(f"   Already correct: {already_correct}")
        print(f"   Groups processed: {len(self.statistics['groups_processed'])}")

    def verify_consistency(self):
        """修正後の一貫性を検証"""
        print("\n✅ Verifying consistency...")

        inconsistencies = []

        for group, members in GROUP_MEMBERS_DATABASE.items():
            group_displays = []

            for person_id in members.keys():
                record = self.df[self.df['person_id'] == person_id]
                if not record.empty:
                    display = record.iloc[0]['person_name_display']
                    has_notation = f'({group})' in display or f'（{group}）' in display
                    group_displays.append((person_id, display, has_notation))

            # チェック: すべてのメンバーが同じ形式か
            notations = [d[2] for d in group_displays]
            if notations and not all(notations):
                inconsistencies.append({
                    'group': group,
                    'members': group_displays
                })

        if inconsistencies:
            print(f"⚠️ Found {len(inconsistencies)} groups with remaining inconsistencies")
            for inc in inconsistencies:
                print(f"   {inc['group']}: Check members")
        else:
            print("✅ All groups are now consistent!")

        return len(inconsistencies) == 0

    def save_results(self):
        """修正結果を保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # 修正済みデータベースを保存
        output_file = f"ultra_think_GROUP_FIXED_{timestamp}.csv"
        self.df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n💾 Fixed database saved to {output_file}")

        # 修正ログを保存
        if self.fix_log:
            log_file = f"group_fix_log_{timestamp}.json"
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump(self.fix_log, f, ensure_ascii=False, indent=2)
            print(f"📝 Fix log saved to {log_file}")

        # 統計を保存
        stats_file = f"group_fix_stats_{timestamp}.json"
        self.statistics['groups_processed'] = list(self.statistics['groups_processed'])
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(self.statistics, f, ensure_ascii=False, indent=2)
        print(f"📊 Statistics saved to {stats_file}")

        return output_file

    def generate_report(self):
        """修正レポートを生成"""
        print("\n" + "="*60)
        print("GROUP NAME FIX REPORT")
        print("="*60)

        print(f"\n📊 Overall Statistics:")
        print(f"   Total records: {self.statistics['total_records']:,}")
        print(f"   Groups in database: {self.statistics['groups_found']}")
        print(f"   Fixes applied: {self.statistics['fixes_applied']}")
        print(f"   Already correct: {self.statistics['already_correct']}")
        print(f"   Inconsistencies fixed: {self.statistics['inconsistencies_fixed']}")

        if self.statistics['fixed_by_group']:
            print(f"\n🎯 Fixes by Group:")
            for group, count in sorted(self.statistics['fixed_by_group'].items(),
                                      key=lambda x: x[1], reverse=True):
                print(f"   {group}: {count} fixes")

        if self.fix_log:
            print(f"\n📝 Sample Fixes (first 10):")
            for fix in self.fix_log[:10]:
                print(f"   {fix['person_id']} ({fix['group']}): {fix['before']} → {fix['after']}")

        # P000008の確認
        p000008 = self.df[self.df['person_id'] == 'P000008']
        if not p000008.empty:
            print(f"\n🎯 P000008 (Fukase) Status:")
            print(f"   Display Name: {p000008.iloc[0]['person_name_display']}")
            if '(SEKAI NO OWARI)' in p000008.iloc[0]['person_name_display']:
                print(f"   ✅ Successfully fixed!")
            else:
                print(f"   ⚠️ Still needs attention")

    def run(self):
        """完全な修正プロセスを実行"""
        print("="*60)
        print("COMPREHENSIVE GROUP NAME FIXER")
        print("="*60)

        # データを読み込み
        self.load_data()

        # 現状を分析
        analysis = self.analyze_current_state()

        # 修正を適用
        self.fix_group_notations()

        # 一貫性を検証
        is_consistent = self.verify_consistency()

        # 結果を保存
        output_file = self.save_results()

        # レポートを生成
        self.generate_report()

        print(f"\n✅ Process complete!")
        print(f"   Output file: {output_file}")

        return output_file, self.statistics


def main():
    # 最新のクリーンデータベースを処理
    csv_file = 'ultra_think_FINAL_CLEAN_20250831_175741.csv'

    fixer = ComprehensiveGroupNameFixer(csv_file)
    output_file, stats = fixer.run()

    print(f"\n🚀 Next steps:")
    print(f"   1. Review the fixed database: {output_file}")
    print(f"   2. Sync to Google Sheets: python3 direct_sync.py {output_file}")
    print(f"   3. Check the fix log for details")

    return output_file


if __name__ == "__main__":
    main()
