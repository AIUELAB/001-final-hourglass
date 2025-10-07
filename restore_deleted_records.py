#!/usr/bin/env python3
"""
誤削除レコードの復元

アインシュタイン、マスク、ベゾスの誤削除を修正。
REQUIREMENTS.mdに基づき、国籍による削除は不当と判定。

Author: Final Hourglass Project
Date: 2025-10-08
Version: 1.0.0
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def restore_deleted_records():
    """誤削除された世界的偉人のレコードを復元"""

    csv_path = Path("final_hourglass_week1_6_complete_20251008_072653.csv")

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    # CSV読み込み（UTF-8 BOM対応）
    df = pd.read_csv(csv_path, encoding='utf-8-sig')

    print(f"📊 読み込み完了: {len(df)} records")

    # 復元対象の人物ID
    restore_targets = {
        'P069': 'アルベルト・アインシュタイン',
        'P072': 'イーロン・マスク',
        'P074': 'ジェフ・ベゾス'
    }

    restored_count = 0

    for person_id, person_name in restore_targets.items():
        mask = df['人物ID'] == person_id

        if mask.sum() == 0:
            print(f"⚠️ {person_id} ({person_name}) not found")
            continue

        current_status = df.loc[mask, 'ステータス'].iloc[0]
        current_reason = df.loc[mask, '削除理由'].iloc[0]

        print(f"\n🔍 {person_id} - {person_name}")
        print(f"   現状: {current_status}")
        print(f"   削除理由: {current_reason}")

        if current_status == '削除済み':
            # ステータスを「合格」に復元
            df.loc[mask, 'ステータス'] = '合格'

            # 削除理由をクリア
            df.loc[mask, '削除理由'] = ''

            print(f"   ✅ 復元完了: ステータス「合格」に変更")
            restored_count += 1
        else:
            print(f"   ⏭️ すでに復元済み")

    # 統計情報
    print("\n" + "="*60)
    print("📊 復元後の統計")
    print("="*60)

    status_counts = df['ステータス'].value_counts()
    print(f"合格: {status_counts.get('合格', 0)}")
    print(f"削除済み: {status_counts.get('削除済み', 0)}")
    print(f"不合格: {status_counts.get('不合格', 0)}")

    total = len(df)
    qualified = status_counts.get('合格', 0)
    deleted = status_counts.get('削除済み', 0)

    print(f"\n合格率: {qualified}/{total} = {qualified/total*100:.1f}%")
    print(f"削除率: {deleted}/{total} = {deleted/total*100:.1f}%")

    # CSV出力（復元後）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"final_hourglass_week1_6_restored_{timestamp}.csv"

    with open(output_path, 'w', encoding='utf-8-sig') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ 復元完了: {output_path}")
    print(f"復元件数: {restored_count}")

    return output_path, restored_count


if __name__ == "__main__":
    try:
        output_path, restored_count = restore_deleted_records()

        print("\n" + "="*60)
        print("🎯 次のステップ")
        print("="*60)
        print("1. テスト実行: pytest tests/test_deletion_logic.py -v")
        print("2. すべてのテストがPASSすることを確認")
        print(f"3. 復元後のCSVを確認: {output_path}")

    except Exception as e:
        print(f"❌ エラー: {e}")
        raise
