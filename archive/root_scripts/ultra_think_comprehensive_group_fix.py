#!/usr/bin/env python3
"""
Ultra Think 包括的グループ名修正システム
2025年8月29日実装

重大な誤分類を完全修正:
- P000083: たかし → トレンディエンジェルのメンバーとして修正
- LUNA SEA、BTS、Stray Kidsの誤分類を削除
"""

import pandas as pd
import json
from datetime import datetime
from pathlib import Path
import shutil

# 修正対象の定義
FIXES = {
    # P000083: トレンディエンジェルのたかし
    'P000083': {
        'correct_group': 'トレンディエンジェル',
        'occupation': 'お笑い芸人',
        'note': 'トレンディエンジェルのメンバー（2015年M-1優勝）'
    },

    # LUNA SEAの誤分類（全て削除）
    'P000147': {'remove_group': 'LUNA SEA', 'note': 'iJustine - Tech YouTuber'},
    'P001832': {'remove_group': 'LUNA SEA', 'note': 'Jun Itoda - Comedian'},
    'P005503': {'remove_group': 'LUNA SEA', 'note': 'Jaguar Yokota - Female Wrestler'},
    'P010000': {'remove_group': 'LUNA SEA', 'note': 'Jean-Michel Basquiat - Artist'},
    'P010010': {'remove_group': 'LUNA SEA', 'note': 'Julian Schnabel - Film Director'},
    'P030074': {'remove_group': 'LUNA SEA', 'note': 'J Balvin - Reggaeton Artist'},
    'P000638': {'remove_group': 'LUNA SEA', 'note': 'Jeno - K-pop artist'},
    'P000645': {'remove_group': 'LUNA SEA', 'note': 'Jaemin - K-pop artist'},
    'P000672': {'remove_group': 'LUNA SEA', 'note': 'Jisung - K-pop artist'},
    'P000680': {'remove_group': 'LUNA SEA', 'note': 'Justin Bieber - Canadian singer'},
    'P000710': {'remove_group': 'LUNA SEA', 'note': 'Joshua - American singer'},
    'P000729': {'remove_group': 'LUNA SEA', 'note': 'Jeonghan - Korean singer'},

    # BTSの誤分類（全て削除）
    'P000036': {'remove_group': 'BTS', 'note': 'Vaundy - Japanese singer'},
    'P000706': {'remove_group': 'BTS', 'note': 'Jun - Chinese singer'},
    'P001046': {'remove_group': 'BTS', 'note': 'Vernon - American singer'},
    'P004580': {'remove_group': 'BTS', 'note': 'Yuta Jinguji - Japanese singer'},
    'P015916': {'remove_group': 'BTS', 'note': 'Carlos Vives - Colombian singer'},

    # Stray Kidsの誤分類（全て削除）
    'P001009': {'remove_group': 'Stray Kids', 'note': 'Nobu - Japanese comedian'},
    'P002527': {'remove_group': 'Stray Kids', 'note': 'Nobuyuki Hanawa - Japanese comedian'}
}

def find_latest_csv():
    """最新のultra_think CSVファイルを検索"""
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if not csv_files:
        raise FileNotFoundError("No ultra_think CSV files found")

    # 最新のファイルを取得
    latest_file = max(csv_files, key=lambda x: x.stat().st_mtime)
    return latest_file

def apply_fixes(df):
    """修正を適用"""
    fix_log = []

    for person_id, fix_info in FIXES.items():
        if person_id in df['person_id'].values:
            idx = df[df['person_id'] == person_id].index[0]

            if 'correct_group' in fix_info:
                # グループを修正（P000083のケース）
                old_display = df.loc[idx, 'person_name_display']
                base_name = old_display.split(' (')[0] if ' (' in old_display else old_display
                new_display = f"{base_name} ({fix_info['correct_group']})"

                df.loc[idx, 'person_name_display'] = new_display

                fix_log.append({
                    'person_id': person_id,
                    'action': 'corrected',
                    'old': old_display,
                    'new': new_display,
                    'note': fix_info['note']
                })

            elif 'remove_group' in fix_info:
                # グループを削除
                old_display = df.loc[idx, 'person_name_display']

                # グループ名を削除（括弧とその中身を削除）
                if f"({fix_info['remove_group']})" in old_display:
                    new_display = old_display.replace(f" ({fix_info['remove_group']})", "")
                    df.loc[idx, 'person_name_display'] = new_display

                    fix_log.append({
                        'person_id': person_id,
                        'action': 'removed',
                        'old': old_display,
                        'new': new_display,
                        'group_removed': fix_info['remove_group'],
                        'note': fix_info['note']
                    })

    return df, fix_log

def update_groups_database():
    """groups_database.jsonを更新"""
    groups_file = Path('groups_database.json')

    if groups_file.exists():
        with open(groups_file, 'r', encoding='utf-8') as f:
            groups_db = json.load(f)
    else:
        groups_db = {}

    # トレンディエンジェルを追加/更新
    groups_db['トレンディエンジェル'] = {
        'members': ['たかし', '斎藤司'],
        'type': 'comedy',
        'notes': 'M-1グランプリ2015年優勝'
    }

    # 誤ったメンバーを削除
    # LUNA SEA、BTS、Stray Kidsから無関係な人を削除する処理はgroups_databaseには不要
    # （そもそも正しいメンバーのみを登録すべき）

    with open(groups_file, 'w', encoding='utf-8') as f:
        json.dump(groups_db, f, ensure_ascii=False, indent=2)

    return groups_db

def main():
    print("🚀 Ultra Think 包括的グループ名修正システム起動")
    print("=" * 60)

    # 最新のCSVファイルを検索
    csv_file = find_latest_csv()
    print(f"📂 対象ファイル: {csv_file}")

    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backup_before_comprehensive_fix_{timestamp}.csv"
    shutil.copy(csv_file, backup_file)
    print(f"💾 バックアップ作成: {backup_file}")

    # データ読み込み
    df = pd.read_csv(csv_file)
    print(f"📊 レコード数: {len(df)}")

    # 修正を適用
    df_fixed, fix_log = apply_fixes(df)
    print(f"\n✅ {len(fix_log)}件の修正を実行")

    # 修正ログを表示
    print("\n📝 修正詳細:")
    print("-" * 60)
    for fix in fix_log:
        if fix['action'] == 'corrected':
            print(f"✅ {fix['person_id']}: {fix['old']} → {fix['new']}")
            print(f"   Note: {fix['note']}")
        elif fix['action'] == 'removed':
            print(f"❌ {fix['person_id']}: Removed ({fix['group_removed']})")
            print(f"   {fix['old']} → {fix['new']}")
            print(f"   Note: {fix['note']}")

    # groups_database.jsonを更新
    print("\n📚 groups_database.json を更新中...")
    groups_db = update_groups_database()
    print("✅ トレンディエンジェルを追加")

    # 新しいCSVファイルとして保存
    output_file = f"ultra_think_COMPREHENSIVE_FIX_{timestamp}.csv"
    df_fixed.to_csv(output_file, index=False)
    print(f"\n💾 修正済みファイル: {output_file}")

    # 修正レポートを保存
    report_file = f"COMPREHENSIVE_FIX_REPORT_{timestamp}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': timestamp,
            'source_file': str(csv_file),
            'output_file': output_file,
            'backup_file': backup_file,
            'total_fixes': len(fix_log),
            'fixes': fix_log
        }, f, ensure_ascii=False, indent=2)

    print(f"📄 レポート保存: {report_file}")

    # 統計情報
    print("\n📊 修正統計:")
    print(f"  - トレンディエンジェル追加: 1件")
    print(f"  - LUNA SEA誤分類削除: {len([f for f in fix_log if f.get('group_removed') == 'LUNA SEA'])}件")
    print(f"  - BTS誤分類削除: {len([f for f in fix_log if f.get('group_removed') == 'BTS'])}件")
    print(f"  - Stray Kids誤分類削除: {len([f for f in fix_log if f.get('group_removed') == 'Stray Kids'])}件")

    print("\n✅ 修正完了！次は force_sync_with_validation.py を実行してください")

    return output_file

if __name__ == "__main__":
    output_file = main()
