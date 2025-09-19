#!/usr/bin/env python3
"""
重要人物の生年月日を個別収集（シンプル版）
"""

import pandas as pd
import time
from datetime import datetime

# 手動で調査した生年月日情報
birth_data = {
    'イーロン・マスク': ('1971-06-28', 1971),
    '藤井聡太': ('2002-07-19', 2002),
    '志村けん': ('1950-02-20', 1950),
    'ジョン・ポール・ジョーンズ': ('1946-01-03', 1946),
    '高木ブー': ('1933-03-08', 1933),
    'ジェシー': ('1996-06-11', 1996),  # SixTONESメンバー
    '国分太一': ('1974-09-02', 1974),
    '岸優太': ('1995-09-29', 1995),  # King & Prince
    'しずちゃん': ('1979-02-04', 1979),  # 山崎静代
    'Jake': ('2002-11-15', 2002),  # ENHYPEN
    'ダディー・ヤンキー': ('1977-02-03', 1977),
    'おたけ': ('1972-01-25', 1972),  # ダチョウ倶楽部
    'オースティン・バトラー': ('1991-08-17', 1991),
    '松村北斗': ('1995-06-18', 1995),  # SixTONES
    '森本慎太郎': ('1997-07-14', 1997),  # SixTONES
    'グレタ・ガーウィグ': ('1983-08-04', 1983),
    'エリオット・ペイジ': ('1987-02-21', 1987),
    '京本大我': ('1994-12-03', 1994),  # SixTONES
    'ブラック・コーヒー': ('1976-03-11', 1976),  # DJ Black Coffee
    'フレディ・マーキュリー': ('1946-09-05', 1946),
    'マーク・アンソニー': ('1968-09-16', 1968),
    'DK': ('1997-02-18', 1997),  # SEVENTEEN
    'ジョーダン・ピール': ('1979-02-21', 1979),
    'ジム・キャリー': ('1962-01-17', 1962),
    'フワちゃん': ('1993-11-26', 1993),
    '長瀬智也': ('1978-11-07', 1978),
    '城島茂': ('1970-11-17', 1970),
    'デンゼル・ワシントン': ('1954-12-28', 1954),
    'ロバート・エガース': ('1983-07-07', 1983),
    '髙地優吾': ('1994-03-08', 1994),  # SixTONES
    'チャドウィック・ボーズマン': ('1976-11-29', 1976),
    'サミュエル・L・ジャクソン': ('1948-12-21', 1948),
    '坂本昌行': ('1971-07-24', 1971),  # V6
    '井ノ原快彦': ('1976-05-17', 1976),  # V6
    '松岡昌宏': ('1977-01-11', 1977),  # TOKIO
    'クリステン・スチュワート': ('1990-04-09', 1990),
    '長野博': ('1972-10-09', 1972),  # V6
    'ニコラス・ケイジ': ('1964-01-07', 1964),
    'ランディ・ローズ': ('1956-12-06', 1956),
    'カルロス・ガルデル': ('1890-12-11', 1890),
    '森田剛': ('1979-02-20', 1979),  # V6
    'トム・ハンクス': ('1956-07-09', 1956),
    '荒井注': ('1928-07-01', 1928),
    '多部未華子': ('1989-01-25', 1989),
    '小泉今日子': ('1966-02-04', 1966),
    'アデル': ('1988-05-05', 1988),
    'マドンナ': ('1958-08-16', 1958),
    'マーゴット・ロビー': ('1990-07-02', 1990)
}

def main():
    # CSVファイルを読み込み
    input_file = 'ultra_think_WITH_BIRTH_DATES_BATCH6_20250917_100511.csv'
    print(f"Loading {input_file}...")

    df = pd.read_csv(input_file, encoding='utf-8-sig')
    print(f"Total records: {len(df)}")

    # 更新カウンタ
    updated_count = 0

    # 各人物の生年月日を更新
    for name, (birth_date, birth_year) in birth_data.items():
        # 該当する人物を検索
        mask = df['person_name_display'] == name

        if mask.any():
            # birth_dateを更新
            df.loc[mask, 'birth_date'] = birth_date
            df.loc[mask, 'birth_year_int'] = float(birth_year)
            updated_count += mask.sum()
            print(f"✓ Updated {name}: {birth_date}")
        else:
            print(f"✗ Not found: {name}")

    print(f"\n=== Summary ===")
    print(f"Updated {updated_count} records")

    # 更新されたCSVを保存
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f'ultra_think_WITH_BIRTH_DATES_SIMPLE_{timestamp}.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"Saved to {output_file}")

    # 統計を表示
    print("\n=== Final Statistics ===")
    print(f"Total records: {len(df)}")
    print(f"Records with birth_date: {df['birth_date'].notna().sum()} ({df['birth_date'].notna().sum()/len(df)*100:.1f}%)")
    print(f"Records with birth_year_int: {df['birth_year_int'].notna().sum()} ({df['birth_year_int'].notna().sum()/len(df)*100:.1f}%)")

if __name__ == '__main__':
    main()