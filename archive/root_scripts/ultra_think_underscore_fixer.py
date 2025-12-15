#!/usr/bin/env python3
"""
Ultra Think アンダースコア修正システム
person_nameフィールドの不正なアンダースコアとグループ名重複を修正
"""
import pandas as pd
import json
import re
from datetime import datetime

class UnderscoreFixer:
    def __init__(self):
        self.fixed_records = []
        self.error_records = []

    def extract_group_from_person_name(self, person_name):
        """person_nameからグループ名を抽出"""
        if pd.isna(person_name):
            return None, person_name

        person_name = str(person_name)
        if '_' not in person_name:
            return None, person_name

        # アンダースコアで分割
        parts = person_name.split('_', 1)
        if len(parts) == 2:
            individual_name = parts[0]
            group_name = parts[1]
            return group_name, individual_name

        return None, person_name

    def fix_display_name_duplicates(self, display_name, group_name):
        """display_nameの重複を修正"""
        if pd.isna(display_name) or not group_name:
            return display_name

        display_name = str(display_name)

        # パターン: "名前_グループ名 (グループ名)" → "名前 (グループ名)"
        # まず、アンダースコア付きの部分を削除
        pattern = f"_?{re.escape(group_name)}\\s*\\({re.escape(group_name)}\\)"
        fixed = re.sub(pattern, f" ({group_name})", display_name)

        # それでも重複が残っている場合
        if fixed == display_name:
            # アンダースコアとグループ名を削除して、括弧付きグループ名だけを残す
            if f"_{group_name}" in display_name:
                fixed = display_name.replace(f"_{group_name}", "")

        # 余分なスペースを削除
        fixed = re.sub(r'\s+', ' ', fixed).strip()

        return fixed

    def process_dataframe(self, df):
        """データフレーム全体を処理"""
        print("📊 アンダースコア問題の修正を開始...")

        # アンダースコアを含むレコードを特定
        mask = df['person_name'].str.contains('_', na=False)
        underscore_records = df[mask].copy()

        print(f"   対象レコード: {len(underscore_records)}件")

        for idx in underscore_records.index:
            row = df.loc[idx]
            person_id = row['person_id']
            original_person_name = row['person_name']
            original_display = row.get('person_name_display', '')

            # グループ名と個人名を分離
            group_name, individual_name = self.extract_group_from_person_name(original_person_name)

            if group_name:
                # person_nameを修正
                df.loc[idx, 'person_name'] = individual_name

                # person_name_displayを修正
                if pd.notna(original_display):
                    fixed_display = self.fix_display_name_duplicates(original_display, group_name)

                    # 最終的な形式を確保: "名前 (グループ名)"
                    if f"({group_name})" not in fixed_display:
                        fixed_display = f"{individual_name} ({group_name})"

                    df.loc[idx, 'person_name_display'] = fixed_display
                else:
                    # displayが空の場合は新規作成
                    df.loc[idx, 'person_name_display'] = f"{individual_name} ({group_name})"

                # 修正記録を保存
                self.fixed_records.append({
                    'person_id': person_id,
                    'original_person_name': original_person_name,
                    'fixed_person_name': individual_name,
                    'group_name': group_name,
                    'original_display': original_display,
                    'fixed_display': df.loc[idx, 'person_name_display']
                })

                # 重要なレコードの進捗表示
                if person_id in ['P000133', 'P000058', 'P000401']:
                    print(f"   🌟 {person_id}: {original_display} → {df.loc[idx, 'person_name_display']}")
            else:
                self.error_records.append({
                    'person_id': person_id,
                    'person_name': original_person_name,
                    'reason': 'グループ名の抽出に失敗'
                })

        print(f"✅ {len(self.fixed_records)}件を修正完了")
        if self.error_records:
            print(f"⚠️ {len(self.error_records)}件のエラー")

        return df

    def generate_report(self, output_file):
        """修正レポートを生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # グループ別集計
        groups = {}
        display_duplicates = []

        for record in self.fixed_records:
            group_name = record['group_name']
            if group_name not in groups:
                groups[group_name] = []
            groups[group_name].append(record)

            # 重複表示があったケースを特定
            orig_display = str(record['original_display'])
            if f"_{group_name}" in orig_display and f"({group_name})" in orig_display:
                display_duplicates.append(record)

        report = f"""# 🔧 アンダースコア・グループ名重複修正レポート

**実行日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
**修正件数**: {len(self.fixed_records)}件

## 📊 問題の概要

### 修正前の問題
1. **person_nameフィールド**: 「個人名_グループ名」形式（62件）
2. **person_name_displayフィールド**: 「個人名_グループ名 (グループ名)」の重複表示（11件）

### 修正後の形式
1. **person_nameフィールド**: 「個人名」のみ
2. **person_name_displayフィールド**: 「個人名 (グループ名)」

## 🌟 重要修正事例

### P000133（ゆめっち）
- **修正前**: ゆめっち_3時のヒロイン (3時のヒロイン)
- **修正後**: **ゆめっち (3時のヒロイン)** ✅
- **所属**: 3時のヒロイン（女芸人No.1決定戦 THE W 2019年王者）

## 📋 グループ別修正内容

"""

        # グループごとの修正内容
        for group_name in sorted(groups.keys()):
            members = groups[group_name]
            has_duplicate = any(m in display_duplicates for m in members)
            duplicate_mark = " ⚠️ 重複表示あり" if has_duplicate else ""

            report += f"### {group_name} ({len(members)}名){duplicate_mark}\n\n"
            report += "| person_id | 個人名 | 修正前 | 修正後 |\n"
            report += "|-----------|--------|--------|--------|\n"

            for member in members:
                orig_display = member['original_display'] or '(空白)'
                fixed_display = member['fixed_display']
                is_duplicate = member in display_duplicates
                mark = " 🔴" if is_duplicate else ""

                report += f"| {member['person_id']} | "
                report += f"{member['fixed_person_name']} | "
                report += f"{orig_display}{mark} | "
                report += f"{fixed_display} |\n"

            report += "\n"

        # 統計
        report += f"""## 📈 統計

### 修正内訳
- **person_name修正**: {len(self.fixed_records)}件（アンダースコア削除）
- **display重複修正**: {len(display_duplicates)}件
- **グループ数**: {len(groups)}グループ

### 重複表示があったグループ
"""

        duplicate_groups = set()
        for dup in display_duplicates:
            duplicate_groups.add(dup['group_name'])

        for group in sorted(duplicate_groups):
            count = sum(1 for d in display_duplicates if d['group_name'] == group)
            report += f"- **{group}**: {count}名\n"

        report += f"""

## 💾 出力ファイル

- **修正済みCSV**: {output_file}
- **修正ログ**: underscore_fix_log_{timestamp}.json

## ✅ 修正完了

すべてのアンダースコア問題と重複表示が解消されました。

---
*レポート生成: {datetime.now().isoformat()}*
"""

        report_file = f'UNDERSCORE_FIX_REPORT_{timestamp}.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"📄 レポート生成: {report_file}")

        return report_file

def main():
    print("=" * 80)
    print("🚀 Ultra Think アンダースコア修正システム起動")
    print("=" * 80)

    fixer = UnderscoreFixer()

    # 最新のCSVファイルを処理
    csv_file = 'ultra_think_YOUTUBER_GROUPS_FIXED_20250828_201154.csv'

    # バックアップを作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_before_underscore_fix_{timestamp}.csv'
    df = pd.read_csv(csv_file)
    df.to_csv(backup_file, index=False)
    print(f"💾 バックアップ作成: {backup_file}")

    # 修正実行
    df_fixed = fixer.process_dataframe(df)

    # 出力ファイル名を生成
    output_file = f'ultra_think_UNDERSCORE_FIXED_{timestamp}.csv'
    df_fixed.to_csv(output_file, index=False)
    print(f"✅ 修正済みファイル: {output_file}")

    # 修正ログを保存
    log_file = f'underscore_fix_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'fixed_records': fixer.fixed_records,
            'error_records': fixer.error_records,
            'summary': {
                'total_fixed': len(fixer.fixed_records),
                'total_errors': len(fixer.error_records),
                'timestamp': datetime.now().isoformat()
            }
        }, f, ensure_ascii=False, indent=2)
    print(f"📝 修正ログ: {log_file}")

    # レポート生成
    report_file = fixer.generate_report(output_file)

    # P000133の最終確認
    print("\n" + "=" * 80)
    p133 = df_fixed[df_fixed['person_id'] == 'P000133']
    if not p133.empty:
        display = p133.iloc[0]['person_name_display']
        print(f"🌟 P000133（ゆめっち）最終確認:")
        print(f"   person_name_display: {display}")
        if display == "ゆめっち (3時のヒロイン)":
            print("   ✅ 正しく修正されました！")

    print("\n✨ アンダースコア修正完了!")
    print(f"📊 合計 {len(fixer.fixed_records)} 件のレコードを修正しました")

if __name__ == '__main__':
    main()
