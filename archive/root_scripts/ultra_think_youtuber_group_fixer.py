#!/usr/bin/env python3
"""
Ultra Think YouTuberグループ修正システム
P000111（ふくらP）を含むYouTuberグループメンバーの表示名を修正
"""
import pandas as pd
import json
from datetime import datetime
import re

class YouTuberGroupFixer:
    def __init__(self):
        # YouTuberグループデータベースを読み込み
        with open('youtuber_groups_database.json', 'r', encoding='utf-8') as f:
            self.groups_db = json.load(f)

        # メンバー名からグループ名へのマッピングを作成
        self.member_to_group = {}
        for group_name, group_data in self.groups_db['YouTuberグループ'].items():
            for member in group_data['members']:
                self.member_to_group[member] = group_name

        # 名前のバリエーションも考慮
        if 'name_variations' in self.groups_db:
            for canonical_name, variations in self.groups_db['name_variations'].items():
                if canonical_name in self.member_to_group:
                    group_name = self.member_to_group[canonical_name]
                    for variation in variations:
                        self.member_to_group[variation] = group_name

    def normalize_name(self, name):
        """名前を正規化"""
        if pd.isna(name):
            return ''
        name = str(name).strip()
        # 括弧内の情報を除去
        name = re.sub(r'[\(（].*?[\)）]', '', name).strip()
        return name

    def find_group(self, row):
        """レコードからグループ名を見つける"""
        # person_name, person_name_ja, person_name_displayから検索
        names_to_check = [
            self.normalize_name(row.get('person_name', '')),
            self.normalize_name(row.get('person_name_ja', '')),
            self.normalize_name(row.get('person_name_display', ''))
        ]

        for name in names_to_check:
            if name in self.member_to_group:
                return self.member_to_group[name]

        return None

    def fix_youtuber_groups(self, csv_file):
        """YouTuberグループメンバーの表示名を修正"""
        print(f"📊 {csv_file}を読み込み中...")
        df = pd.read_csv(csv_file)
        print(f"   行数: {len(df)}")

        # YouTuberのみフィルタ
        youtubers = df[df['occupation'] == 'YouTuber'].copy()
        print(f"   YouTuber数: {len(youtubers)}")

        fixed_count = 0
        fixed_records = []

        for idx, row in youtubers.iterrows():
            group_name = self.find_group(row)

            if group_name:
                # グループメンバーを発見
                person_id = row['person_id']
                person_name = row['person_name']
                person_name_ja = row.get('person_name_ja', '')
                current_display = row.get('person_name_display', '')

                # 優先順位: person_name_ja > person_name
                base_name = person_name_ja if person_name_ja else person_name
                base_name = self.normalize_name(base_name)

                # 新しい表示名を生成（重複チェック付き）
                # 個人名とグループ名が同じ場合は括弧を追加しない
                if base_name.lower() == group_name.lower() or base_name == group_name:
                    new_display = base_name
                else:
                    new_display = f"{base_name} ({group_name})"

                # 既に正しく設定されているかチェック
                if current_display != new_display:
                    df.loc[idx, 'person_name_display'] = new_display
                    fixed_count += 1

                    fixed_records.append({
                        'person_id': person_id,
                        'person_name': person_name,
                        'group_name': group_name,
                        'before': current_display,
                        'after': new_display
                    })

                    # 特定の重要メンバーを表示
                    if person_id == 'P000111' or person_name in ['ふくらP', 'Fukura P']:
                        print(f"   🌟 {person_id}: {current_display} → {new_display}")

        print(f"\n✅ {fixed_count}件のYouTuberグループメンバーを修正")

        return df, fixed_records

    def generate_report(self, fixed_records, output_file):
        """修正レポートを生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # グループ別に集計
        groups_summary = {}
        for record in fixed_records:
            group_name = record['group_name']
            if group_name not in groups_summary:
                groups_summary[group_name] = []
            groups_summary[group_name].append(record)

        report = f"""# 🎥 YouTuberグループ修正レポート

**実行日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
**修正件数**: {len(fixed_records)}件

## 📊 グループ別修正内容

"""

        # P000111を特別扱い
        p000111_fixed = False
        for record in fixed_records:
            if record['person_id'] == 'P000111':
                p000111_fixed = True
                report += f"""### 🌟 重要修正: P000111

- **person_id**: P000111
- **メンバー名**: {record['person_name']}
- **グループ**: {record['group_name']}
- **修正前**: {record['before']}
- **修正後**: **{record['after']}** ✅

"""
                break

        # グループごとに表示
        for group_name, members in sorted(groups_summary.items()):
            report += f"### {group_name} ({len(members)}名)\n\n"
            report += "| person_id | メンバー名 | 修正前 | 修正後 |\n"
            report += "|-----------|-----------|--------|--------|\n"

            for member in members:
                # P000111は既に表示済み
                if member['person_id'] != 'P000111':
                    report += f"| {member['person_id']} | {member['person_name']} | "
                    report += f"{member['before'] or '(空白)'} | {member['after']} |\n"

            report += "\n"

        # 統計
        report += f"""## 📈 統計

- **修正されたグループ数**: {len(groups_summary)}
- **修正されたメンバー数**: {len(fixed_records)}
- **P000111（ふくらP）**: {'✅ 修正完了' if p000111_fixed else '❌ 未発見'}

## 🔍 主要グループの修正状況

"""

        # 主要グループの状況
        major_groups = ['QuizKnock', 'フィッシャーズ', '東海オンエア', 'コムドット', 'スカイピース']
        for group in major_groups:
            if group in groups_summary:
                count = len(groups_summary[group])
                report += f"- **{group}**: {count}名修正 ✅\n"
            else:
                report += f"- **{group}**: 0名（未発見）\n"

        report += f"""

## 💾 出力ファイル

- **修正済みCSV**: {output_file}
- **修正ログ**: youtuber_group_fix_log_{timestamp}.json

---
*レポート生成: {datetime.now().isoformat()}*
"""

        report_file = f'YOUTUBER_GROUP_FIX_REPORT_{timestamp}.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"📄 レポート生成: {report_file}")

        return report_file

def main():
    print("=" * 80)
    print("🚀 Ultra Think YouTuberグループ修正システム起動")
    print("=" * 80)

    fixer = YouTuberGroupFixer()

    # 最新のCSVファイルを処理
    csv_file = 'ultra_think_HAJIME_FIXED_20250828_194909.csv'

    # バックアップを作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_before_youtuber_group_fix_{timestamp}.csv'
    df_backup = pd.read_csv(csv_file)
    df_backup.to_csv(backup_file, index=False)
    print(f"💾 バックアップ作成: {backup_file}")

    # 修正実行
    df_fixed, fixed_records = fixer.fix_youtuber_groups(csv_file)

    # 出力ファイル名を生成
    output_file = f'ultra_think_YOUTUBER_GROUPS_FIXED_{timestamp}.csv'
    df_fixed.to_csv(output_file, index=False)
    print(f"✅ 修正済みファイル: {output_file}")

    # 修正ログを保存
    log_file = f'youtuber_group_fix_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump(fixed_records, f, ensure_ascii=False, indent=2)
    print(f"📝 修正ログ: {log_file}")

    # レポート生成
    report_file = fixer.generate_report(fixed_records, output_file)

    # 統計を表示
    print("\n" + "=" * 80)
    print("📊 修正統計")
    print("=" * 80)

    # グループ別集計
    groups_count = {}
    for record in fixed_records:
        group_name = record['group_name']
        groups_count[group_name] = groups_count.get(group_name, 0) + 1

    print(f"修正されたグループ数: {len(groups_count)}")
    print("\nグループ別修正数:")
    for group_name, count in sorted(groups_count.items(), key=lambda x: x[1], reverse=True):
        print(f"  {group_name}: {count}名")

    # P000111の確認
    print("\n" + "=" * 80)
    p000111_fixed = any(r['person_id'] == 'P000111' for r in fixed_records)
    if p000111_fixed:
        p_record = next(r for r in fixed_records if r['person_id'] == 'P000111')
        print(f"🌟 P000111（ふくらP）修正完了!")
        print(f"   → {p_record['after']}")

    print("\n✨ YouTuberグループ修正完了!")
    print(f"📊 合計 {len(fixed_records)} 件のレコードを修正しました")

if __name__ == '__main__':
    main()
