#!/usr/bin/env python3
"""
全エピソードのスロット算出スクリプト

年齢に基づいてスロットを割り当てる
"""

import pandas as pd
from pathlib import Path
from datetime import datetime

CSV_PATH = Path(__file__).parent.parent / "MASTER_EPISODES_CURRENT.csv"
BACKUP_PATH = Path(__file__).parent.parent / f"MASTER_EPISODES_CURRENT_backup_before_slot_calculation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"


def calculate_slot(age: float) -> int:
    """
    年齢からスロットを算出

    スロット分類:
    - Slot 1: 0-5歳
    - Slot 10: 6-15歳
    - Slot 20: 16-25歳
    - Slot 30: 26-35歳
    - Slot 40: 36-45歳
    - Slot 50: 46-55歳
    - Slot 60: 56歳以上
    """
    if pd.isna(age):
        return None

    age = float(age)

    if age <= 5:
        return 1
    elif age <= 15:
        return 10
    elif age <= 25:
        return 20
    elif age <= 35:
        return 30
    elif age <= 45:
        return 40
    elif age <= 55:
        return 50
    else:
        return 60


def estimate_character_age(row: pd.Series) -> float:
    """
    架空キャラクターの年齢を推定

    エピソード内容から年齢を推定する
    """
    person_name = str(row.get('person_name', '')).lower()
    episode_text = str(row.get('episode_text', '')).lower()

    # 既知のキャラクター設定年齢
    character_ages = {
        '鉄腕アトム': 10,  # 小学生設定
        'マリオ': 30,  # 成人の配管工
        'ルパン三世': 30,  # 成人の怪盗
        'ドラえもん': 10,  # 小学5年生のび太と一緒
        'ピカチュウ': 10,  # サトシが10歳で受け取った
        'ウルトラマン': 30,  # 成人のハヤタ隊員と一体化
        'アンパンマン': 5,  # 子供向けヒーロー
        'ガンダム': 15,  # 15歳のアムロが搭乗
    }

    # キャラクター名で年齢推定
    for char_name, age in character_ages.items():
        if char_name.lower() in person_name:
            return float(age)

    # エピソードテキストから年齢を推定
    if '小学' in episode_text or '10歳' in episode_text:
        return 10.0
    elif '15歳' in episode_text or '中学' in episode_text:
        return 15.0
    elif '成人' in episode_text or '大人' in episode_text:
        return 30.0
    elif '子供' in episode_text or '子ども' in episode_text:
        return 10.0

    # デフォルトは成人設定
    return 30.0


def main():
    print("=" * 80)
    print("📊 全エピソードのスロット算出")
    print("=" * 80)
    print()

    # Step 1: CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print()

    # Step 2: 既存のスロットを確認
    print("Step 2: 既存スロット確認中...")
    existing_count = df['slot'].notna().sum()
    print(f"  既存スロットあり: {existing_count}件")
    print(f"  既存スロットなし: {len(df) - existing_count}件")
    print()

    # スロットなしのエピソードを表示
    if len(df) - existing_count > 0:
        print("  スロットなしエピソード:")
        no_slot = df[df['slot'].isna()]
        for idx, row in no_slot.iterrows():
            print(f"    - {row['person_name']} (年齢: {row['age']})")
        print()

    # Step 3: バックアップ作成
    print("Step 3: バックアップ作成中...")
    df.to_csv(BACKUP_PATH, index=False, encoding='utf-8-sig')
    print(f"  ✅ バックアップ作成: {BACKUP_PATH}")
    print()

    # Step 4: スロット算出
    print("Step 4: スロット算出中...")
    updated_count = 0

    for idx, row in df.iterrows():
        age = row.get('age')

        # 年齢がNaNの場合は推定
        if pd.isna(age):
            estimated_age = estimate_character_age(row)
            print(f"  年齢推定: {row['person_name']} → {estimated_age}歳")
            df.at[idx, 'age'] = estimated_age
            age = estimated_age

        # スロット算出
        slot = calculate_slot(age)

        # スロットが未設定または変更された場合
        if pd.isna(row.get('slot')) or row.get('slot') != slot:
            df.at[idx, 'slot'] = slot
            updated_count += 1

    print(f"  ✅ スロット更新: {updated_count}件")
    print()

    # Step 5: 統計情報
    print("=" * 80)
    print("Step 5: 統計情報")
    print("=" * 80)
    print()

    print("スロット分布:")
    for slot in sorted(df['slot'].dropna().unique()):
        slot_df = df[df['slot'] == slot]
        ages = slot_df['age'].dropna()
        if len(ages) > 0:
            print(f"  Slot {int(slot):2d}: 年齢 {ages.min():.0f}-{ages.max():.0f}歳 ({len(slot_df):,}件)")
    print()

    # スロットなしが残っているか確認
    remaining_no_slot = df['slot'].isna().sum()
    print(f"スロットなし: {remaining_no_slot}件")
    print()

    # Step 6: CSVに保存
    print("Step 6: CSVファイルへの保存")
    df.to_csv(CSV_PATH, index=False, encoding='utf-8-sig')
    print(f"  ✅ 保存完了: {CSV_PATH}")
    print()

    print("=" * 80)
    print("✅ 全エピソードのスロット算出が完了しました！")
    print("=" * 80)


if __name__ == "__main__":
    main()
