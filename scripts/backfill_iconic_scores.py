#!/usr/bin/env python3
"""
象徴性スコアバックフィルスクリプト

既存エピソードの欠損している象徴性スコアを計算・更新する。
IconicScoreCalculatorを使用してテキスト分析ベースでスコアを算出。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from tqdm import tqdm

from scripts.sage.quality.evaluator import IconicScoreCalculator

# パス
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"


def main():
    print("=== 象徴性スコア バックフィル ===\n")

    # CSV読み込み
    print("CSVデータ読み込み中...")
    df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig", low_memory=False)
    print(f"総エピソード数: {len(df)}")

    # 象徴性スコアを数値に変換
    df["象徴性スコア"] = pd.to_numeric(df["象徴性スコア"], errors="coerce")

    # 欠損/0のインデックスを取得
    mask = df["象徴性スコア"].isna() | (df["象徴性スコア"] == 0)
    missing_indices = df[mask].index.tolist()
    print(f"要更新エピソード: {len(missing_indices)}")

    if len(missing_indices) == 0:
        print("更新対象なし。終了します。")
        return

    # IconicScoreCalculator初期化
    calculator = IconicScoreCalculator()
    print("IconicScoreCalculator初期化完了")

    # バッチ処理
    updated_count = 0
    for idx in tqdm(missing_indices, desc="象徴スコア計算"):
        row = df.loc[idx]

        # 必要なデータを取得
        text = str(row.get("episode_text", "") or "")
        person_name = str(row.get("person_name", "") or "")
        age = row.get("episode_age")

        # 年齢を整数に変換
        try:
            age = int(float(age)) if pd.notna(age) else 0
        except (ValueError, TypeError):
            age = 0

        # スコア計算
        if text:
            score = calculator.calculate(text=text, person_name=person_name, age=age)
            df.at[idx, "象徴性スコア"] = round(score, 1)
            updated_count += 1

    print(f"\n更新完了: {updated_count}件")

    # CSV書き込み
    print("CSVに書き込み中...")
    df.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")
    print(f"✓ 保存完了: {MASTER_CSV}")

    # 統計確認
    iconic = pd.to_numeric(df["象徴性スコア"], errors="coerce")
    print("\n=== 更新後統計 ===")
    print(f"平均スコア: {iconic.mean():.2f}")
    print(f"最小: {iconic.min():.1f}, 最大: {iconic.max():.1f}")
    print(f"欠損: {iconic.isna().sum()}")


if __name__ == "__main__":
    main()
