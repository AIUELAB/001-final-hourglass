#!/usr/bin/env python3
"""
Pattern D違反のbirth_year修正スクリプト
"""
import pandas as pd
from pathlib import Path

# ファイルパス
CSV_PATH = Path("/Users/admin/Documents/AIUELAB/001-final-hourglass/preserved/data/MASTER_EPISODES_CURRENT.csv")

# 修正対象リスト（person_name: 正しいbirth_year）
CORRECTIONS = {
    "ニューマン・ポール": 1925,      # ポール・ニューマン俳優
    "ジョン・ダリー": 1966,          # ゴルファー
    "ジョン・マッケンロー": 1959,    # テニス選手
    "高田延彦": 1962,                # プロレスラー
    "ロジャー・バニスター": 1929,    # 陸上選手
    "ズビグニェフ・ボニエク": 1956,  # サッカー選手
    "ニキ・ラウダ": 1949,            # F1ドライバー
    "ジム・ブラウン": 1936,          # NFL選手
    "ホセ・カンセコ": 1964,          # 野球選手
    "田中理恵": 1987,                # 体操選手
    "水島努": 1965,                  # アニメ監督
    "イバン・レンドル": 1960,        # テニス選手
    "ジョー・モンタナ": 1956,        # NFL選手
    "マッツ・ヴィランデル": 1964,    # テニス選手
    "フランク・トーマス": 1968,      # 野球選手
    "りんたろう": 1941,              # アニメ監督
    "谷口浩美": 1960,                # マラソン選手
    "緒方孝市": 1968,                # 野球選手
    "坂上二郎": 1934,                # コメディアン
    "パット・ラフター": 1972,        # テニス選手
    "岡本太郎": 1911,                # 芸術家
    "ケイト・スミス": 1907,          # 歌手（Web調査で確認）
    "ロバート・ルイス": 1909,        # 俳優・演出家（Web調査で確認）
    "モンタナ・ジョー": 1956,        # ジョー・モンタナと同一人物
}

def main():
    print("=" * 60)
    print("Pattern D違反 birth_year 修正")
    print("=" * 60)

    # CSV読み込み
    df = pd.read_csv(CSV_PATH)
    print(f"読み込み完了: {len(df)} 行")

    # 修正前の状態を記録
    corrections_made = []

    for person_name, correct_birth_year in CORRECTIONS.items():
        # 対象行を特定
        mask = df['person_name'] == person_name
        matching_rows = df[mask]

        if len(matching_rows) == 0:
            print(f"[SKIP] {person_name}: CSVに存在しません")
            continue

        # 現在のbirth_year値を取得（最初の行から）
        current_birth_year = matching_rows['birth_year'].iloc[0]

        # 既に正しい値の場合はスキップ
        if pd.notna(current_birth_year) and int(current_birth_year) == correct_birth_year:
            print(f"[OK] {person_name}: 既に正しい値 ({correct_birth_year})")
            continue

        # 修正実行
        df.loc[mask, 'birth_year'] = correct_birth_year
        affected_count = len(matching_rows)

        old_val = int(current_birth_year) if pd.notna(current_birth_year) else "N/A"
        corrections_made.append({
            'person_name': person_name,
            'old_value': old_val,
            'new_value': correct_birth_year,
            'rows_affected': affected_count
        })
        print(f"[FIX] {person_name}: {old_val} → {correct_birth_year} ({affected_count}行)")

    # CSV保存
    if corrections_made:
        df.to_csv(CSV_PATH, index=False)
        print("\n" + "=" * 60)
        print(f"保存完了: {len(corrections_made)} 人の修正")
        print("=" * 60)

        # サマリー
        total_rows = sum(c['rows_affected'] for c in corrections_made)
        print(f"\n修正サマリー:")
        print(f"  - 修正人物数: {len(corrections_made)}")
        print(f"  - 修正行数: {total_rows}")
    else:
        print("\n修正対象なし")

if __name__ == "__main__":
    main()
