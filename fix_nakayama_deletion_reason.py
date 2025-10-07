#!/usr/bin/env python3
"""
中山啓子の削除理由を修正

削除理由が削除理由カラムではなくエピソード本文に記載されている問題を修正。

Author: Final Hourglass Project
Date: 2025-10-08
"""

import pandas as pd
from pathlib import Path
from datetime import datetime


def fix_nakayama_deletion_reason():
    """中山啓子の削除理由を正しいカラムに移動"""

    csv_path = Path("final_hourglass_week1_6_restored_20251008_074931.csv")

    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path, encoding='utf-8-sig')

    print(f"📊 読み込み完了: {len(df)} records")

    # 中山啓子のレコードを特定
    mask = df['人物ID'] == 'P037'

    if mask.sum() == 0:
        raise ValueError("P037 (中山啓子) not found")

    # 現在の状態を確認
    current_episode = df.loc[mask, 'エピソード本文'].iloc[0]
    current_reason = df.loc[mask, '削除理由'].iloc[0]

    print(f"\n🔍 P037 - 中山啓子")
    print(f"   エピソード本文: {current_episode}")
    print(f"   削除理由: '{current_reason}' (type: {type(current_reason)})")

    # 削除理由を正しく設定
    df.loc[mask, '削除理由'] = '検証不可能な架空人物のため削除'

    # エピソード本文をクリア（削除済みレコードなのでエピソードは不要）
    df.loc[mask, 'エピソード本文'] = ''

    print(f"   ✅ 修正完了: 削除理由を正しいカラムに設定")

    # CSV出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"final_hourglass_week1_6_final_{timestamp}.csv"

    with open(output_path, 'w', encoding='utf-8-sig') as f:
        df.to_csv(f, index=False)

    print(f"\n✅ 修正完了: {output_path}")

    return output_path


if __name__ == "__main__":
    try:
        output_path = fix_nakayama_deletion_reason()

        print("\n" + "="*60)
        print("🎯 次のステップ")
        print("="*60)
        print("1. テスト再実行: pytest tests/test_deletion_logic.py -v")
        print("2. すべてのテストがPASSすることを確認")

    except Exception as e:
        print(f"❌ エラー: {e}")
        raise
