#!/usr/bin/env python3
"""
お笑い芸人グループ名修正の品質検証レポート
"""
import pandas as pd
import json
from datetime import datetime

def generate_quality_report():
    # 修正前後のファイルを読み込み
    before_df = pd.read_csv('ultra_think_FAST_VALIDATED_20250828_181901.csv')
    after_df = pd.read_csv('ultra_think_COMEDY_GROUPS_FIXED_20250828_190550.csv')

    # お笑い芸人のみフィルタ
    before_comedians = before_df[before_df['occupation'] == 'お笑い芸人'].copy()
    after_comedians = after_df[after_df['occupation'] == 'お笑い芸人'].copy()

    # 統計を計算
    stats = {
        'total_comedians': len(after_comedians),
        'before_with_groups': 0,
        'after_with_groups': 0,
        'newly_added_groups': 0,
        'corrected_groups': 0,
        'p000057_status': None
    }

    # グループ名の有無をカウント
    for _, row in before_comedians.iterrows():
        if '(' in str(row['person_name_display']) and ')' in str(row['person_name_display']):
            stats['before_with_groups'] += 1

    for _, row in after_comedians.iterrows():
        if '(' in str(row['person_name_display']) and ')' in str(row['person_name_display']):
            stats['after_with_groups'] += 1

    # 変更を検出
    changes = []
    for idx in after_comedians.index:
        person_id = after_comedians.loc[idx, 'person_id']
        before_row = before_comedians[before_comedians['person_id'] == person_id]

        if not before_row.empty:
            before_display = before_row.iloc[0]['person_name_display']
            after_display = after_comedians.loc[idx, 'person_name_display']

            if before_display != after_display:
                changes.append({
                    'person_id': person_id,
                    'person_name': after_comedians.loc[idx, 'person_name'],
                    'person_name_ja': after_comedians.loc[idx, 'person_name_ja'],
                    'before': before_display,
                    'after': after_display
                })

                # グループが新規追加されたか
                if '(' not in str(before_display) and '(' in str(after_display):
                    stats['newly_added_groups'] += 1
                # グループが修正されたか
                elif '(' in str(before_display) and '(' in str(after_display):
                    stats['corrected_groups'] += 1

    # P000057の状態を確認
    p000057_after = after_comedians[after_comedians['person_id'] == 'P000057']
    if not p000057_after.empty:
        stats['p000057_status'] = {
            'person_name': p000057_after.iloc[0]['person_name'],
            'person_name_ja': p000057_after.iloc[0]['person_name_ja'],
            'person_name_display': p000057_after.iloc[0]['person_name_display'],
            'has_group': '(ジャングルポケット)' in str(p000057_after.iloc[0]['person_name_display'])
        }

    # レポートを生成
    report_lines = [
        "# 🎭 お笑い芸人グループ名修正 品質検証レポート",
        "",
        f"**実行日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}",
        "",
        "## 📊 全体統計",
        "",
        f"- **お笑い芸人総数**: {stats['total_comedians']}人",
        f"- **修正前のグループ表示**: {stats['before_with_groups']}人",
        f"- **修正後のグループ表示**: {stats['after_with_groups']}人",
        f"- **増加数**: +{stats['after_with_groups'] - stats['before_with_groups']}人",
        f"- **新規グループ追加**: {stats['newly_added_groups']}人",
        f"- **グループ名修正**: {stats['corrected_groups']}人",
        "",
        "## 🎯 P000057（おたけ）の状態",
        ""
    ]

    if stats['p000057_status']:
        p = stats['p000057_status']
        report_lines.extend([
            f"- **person_name**: {p['person_name']}",
            f"- **person_name_ja**: {p['person_name_ja']}",
            f"- **person_name_display**: {p['person_name_display']}",
            f"- **ジャングルポケット表示**: {'✅ あり' if p['has_group'] else '❌ なし'}",
            ""
        ])
    else:
        report_lines.append("⚠️ P000057が見つかりませんでした\n")

    # 主要な変更例
    report_lines.extend([
        "## 📝 主要な変更例（最初の20件）",
        ""
    ])

    for change in changes[:20]:
        report_lines.append(f"- **{change['person_id']}**: {change['before']} → {change['after']}")

    if len(changes) > 20:
        report_lines.append(f"\n... 他{len(changes) - 20}件の変更")

    # 改善率
    improvement_rate = ((stats['after_with_groups'] - stats['before_with_groups']) / stats['total_comedians']) * 100

    report_lines.extend([
        "",
        "## 📈 改善指標",
        "",
        f"- **グループ表示率（修正前）**: {(stats['before_with_groups'] / stats['total_comedians'] * 100):.1f}%",
        f"- **グループ表示率（修正後）**: {(stats['after_with_groups'] / stats['total_comedians'] * 100):.1f}%",
        f"- **改善率**: +{improvement_rate:.1f}%",
        "",
        "## 🔍 残存課題",
        "",
        f"- **グループ未表示**: {stats['total_comedians'] - stats['after_with_groups']}人（{((stats['total_comedians'] - stats['after_with_groups']) / stats['total_comedians'] * 100):.1f}%）",
        "  - 主にピン芸人や新規グループメンバー",
        "  - groups_database.jsonへの追加登録が必要",
        "",
        "## ✅ 結論",
        "",
        f"1. **P000057（おたけ）**: {'正常にジャングルポケット表示を追加' if stats['p000057_status'] and stats['p000057_status']['has_group'] else '修正が必要'}",
        f"2. **全体改善**: {len(changes)}件の修正を実施",
        f"3. **グループ表示率**: {(stats['before_with_groups'] / stats['total_comedians'] * 100):.1f}% → {(stats['after_with_groups'] / stats['total_comedians'] * 100):.1f}%",
        "",
        "---",
        f"*レポート生成: {datetime.now().isoformat()}*"
    ])

    # レポートを保存
    report_content = '\n'.join(report_lines)
    report_file = f'COMEDY_GROUPS_QUALITY_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'

    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report_content)

    print(report_content)

    # 統計をJSONでも保存
    with open('comedy_groups_quality_stats.json', 'w', encoding='utf-8') as f:
        json.dump({
            'stats': stats,
            'changes_count': len(changes),
            'changes_sample': changes[:10]
        }, f, ensure_ascii=False, indent=2)

    return report_file, stats

if __name__ == "__main__":
    report_file, stats = generate_quality_report()
    print(f"\n📁 レポート保存先: {report_file}")
