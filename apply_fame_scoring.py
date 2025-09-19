#!/usr/bin/env python3
"""
全データに1-10000の知名度スコアリングを適用
Wikipedia存在を必須条件とした総合評価
"""

import pandas as pd
import numpy as np
from datetime import datetime
import os
import re

def get_wikipedia_presence(row):
    """Wikipedia存在のチェック（ゲート条件）"""

    # has_wikipedia フィールドが明示的にある場合
    if row.get('has_wikipedia') == True:
        return 1000

    # search_source に wikipedia が含まれる場合
    search_source = str(row.get('search_source', '')).lower()
    if 'wikipedia' in search_source:
        return 800

    # person_name_display に Wikipedia的な情報がある場合
    display_name = str(row.get('person_name_display', ''))
    if '（' in display_name and '）' in display_name:
        # カッコ内に説明がある場合、Wikipedia的な説明の可能性
        return 600

    # search_result_count が極めて高い場合（10万件以上）
    # これほど多いとWikipediaページが存在する可能性が高い
    if row.get('search_result_count', 0) > 100000:
        return 500

    # recognition_score が高い場合（8.0以上）
    if row.get('recognition_score', 0) >= 8.0:
        return 400

    # その他の場合はWikipedia存在なしと判定
    return 0

def get_impact_category(row):
    """感銘度カテゴリの判定"""

    person_name = str(row.get('person_name_ja', row.get('person_name', ''))).lower()
    category = str(row.get('category', '')).lower()
    occupation = str(row.get('occupation', '')).lower()

    # A級：逆転ストーリー型（2.5倍）
    if 'サンドウィッチマン' in person_name:
        return 'A級_逆転ストーリー', 2.5
    if '諫山創' in person_name:
        return 'A級_逆転ストーリー', 2.5

    # A級：ゼロイチ創造型（2.3倍）
    if 'hikakin' in person_name or 'ヒカキン' in person_name:
        return 'A級_ゼロイチ創造', 2.3
    if 'youtuber' in category and row.get('person_id', '') in ['P000001', 'P000002', 'P000003']:
        return 'A級_ゼロイチ創造', 2.3
    if 'イーロン・マスク' in person_name or 'elon musk' in person_name:
        return 'A級_ゼロイチ創造', 2.3

    # A級：若年成功型（2.2倍）
    if '藤井聡太' in person_name:
        return 'A級_若年成功', 2.2
    if row.get('birth_year', 0) >= 2000 and row.get('recognition_score', 0) >= 7:
        return 'A級_若年成功', 2.2

    # B級：継続努力型（1.8倍）
    if '明石家さんま' in person_name:
        return 'B級_継続努力', 1.8
    if '尾田栄一郎' in person_name:
        return 'B級_継続努力', 1.8
    if '大谷翔平' in person_name:
        return 'B級_継続努力', 1.8

    # B級：社会貢献型（1.7倍）
    if '前澤友作' in person_name:
        return 'B級_社会貢献', 1.7
    if 'マララ' in person_name:
        return 'B級_社会貢献', 1.7

    # C級：分野トップ型（1.5倍）
    if 'champion' in occupation or 'winner' in occupation:
        return 'C級_分野トップ', 1.5
    if 'ノーベル' in person_name or 'nobel' in person_name:
        return 'C級_分野トップ', 1.5

    # カテゴリベースの判定
    if 'entertainment' in category or 'エンターテインメント' in category:
        return '標準_エンタメ', 1.3
    if 'sports' in category or 'スポーツ' in category:
        return '標準_スポーツ', 1.2
    if 'business' in category or 'ビジネス' in category:
        return '標準_ビジネス', 1.1

    return '標準', 1.0

def get_era_adjustment(row):
    """時代補正の計算"""

    birth_year = row.get('birth_year')

    # birth_yearが文字列の場合、数値に変換
    if isinstance(birth_year, str):
        try:
            birth_year = int(birth_year)
        except:
            birth_year = None

    if not birth_year or birth_year == 0:
        # 生年不明の場合は標準値
        return 1.0

    # 現在活躍中の人物を優先
    if birth_year >= 2000:
        return 1.2  # Z世代
    elif birth_year >= 1990:
        return 1.15  # ミレニアル世代
    elif birth_year >= 1980:
        return 1.1  # 就職氷河期世代
    elif birth_year >= 1970:
        return 1.0  # バブル崩壊世代
    elif birth_year >= 1960:
        return 0.9  # バブル世代
    else:
        return 0.8  # レジェンド枠

def calculate_fame_score(row):
    """1-10000の知名度スコアを計算"""

    # Step 1: Wikipedia Gate（必須条件）
    wikipedia_score = get_wikipedia_presence(row)
    if wikipedia_score == 0:
        # Wikipedia存在なし = 有名人ではない
        return 0

    # Step 2: 基礎スコア計算（最大4000点）
    base_score = 0

    # Wikipedia存在ボーナス
    base_score += wikipedia_score

    # 検索結果数（最大1500点）
    search_count = row.get('search_result_count', 0)
    if search_count > 0:
        # 対数スケールで評価（1～1000万件を想定）
        search_score = min(1500, np.log10(max(1, search_count)) * 250)
        base_score += search_score

    # 認知度スコア（最大1000点）
    recognition = row.get('recognition_score', 0)
    if recognition > 0:
        base_score += min(1000, recognition * 100)

    # accuracy_scoreがある場合（最大300点）
    accuracy = row.get('accuracy_score', 0)
    if accuracy > 0:
        base_score += min(300, accuracy * 30)

    # news_scoreがある場合（最大200点）
    news = row.get('news_score', 0)
    if news > 0:
        base_score += min(200, news * 20)

    # Step 3: 感銘度倍率
    impact_category, multiplier = get_impact_category(row)

    # Step 4: 時代補正
    era_adjustment = get_era_adjustment(row)

    # 最終スコア計算
    final_score = base_score * multiplier * era_adjustment

    # 1-10000の範囲に収める
    final_score = min(10000, max(0, int(final_score)))

    # Wikipedia存在するが極端に低いスコアの場合、最低1点を保証
    if wikipedia_score > 0 and final_score == 0:
        final_score = 1

    return final_score

def get_score_category(score):
    """スコアからカテゴリを判定"""
    if score >= 9000:
        return "超S級（国民的認知度）"
    elif score >= 7000:
        return "S級（誰もが知る有名人）"
    elif score >= 5000:
        return "A級（特定世代の憧れ）"
    elif score >= 3000:
        return "B級（分野内での有名人）"
    elif score >= 1000:
        return "C級（限定的認知度）"
    elif score >= 1:
        return "D級（最低限の認知）"
    else:
        return "対象外（有名人ではない）"

def main():
    print("=" * 80)
    print("📊 知名度スコアリング（1-10000）適用")
    print("=" * 80)

    # 最新のCSVファイルを検索
    csv_files = [f for f in os.listdir('.') if f.startswith('ultra_think_') and f.endswith('.csv')]

    if not csv_files:
        print("❌ CSVファイルが見つかりません")
        return

    # 最新のファイルを選択（CLEANED_COLUMNSを優先）
    cleaned_files = [f for f in csv_files if 'CLEANED_COLUMNS' in f]
    if cleaned_files:
        input_file = sorted(cleaned_files)[-1]
    else:
        input_file = sorted(csv_files)[-1]

    print(f"\n📂 入力ファイル: {input_file}")

    # データ読み込み
    df = pd.read_csv(input_file)
    print(f"✅ 読み込み完了: {len(df):,}件")

    # スコア計算
    print("\n🔄 スコア計算中...")
    df['fame_score'] = df.apply(calculate_fame_score, axis=1)
    df['score_category'] = df['fame_score'].apply(get_score_category)

    # 感銘度カテゴリも追加
    df['impact_category'] = df.apply(lambda row: get_impact_category(row)[0], axis=1)
    df['impact_multiplier'] = df.apply(lambda row: get_impact_category(row)[1], axis=1)

    # 時代補正も追加
    df['era_adjustment'] = df.apply(get_era_adjustment, axis=1)

    # Wikipedia存在も明示
    df['wikipedia_presence_score'] = df.apply(get_wikipedia_presence, axis=1)

    # スコア順にソート
    df = df.sort_values('fame_score', ascending=False)

    # 統計情報
    print("\n📊 スコア分布:")
    print(f"  超S級（9000-10000）: {len(df[df['fame_score'] >= 9000]):,}件")
    print(f"  S級（7000-8999）: {len(df[(df['fame_score'] >= 7000) & (df['fame_score'] < 9000)]):,}件")
    print(f"  A級（5000-6999）: {len(df[(df['fame_score'] >= 5000) & (df['fame_score'] < 7000)]):,}件")
    print(f"  B級（3000-4999）: {len(df[(df['fame_score'] >= 3000) & (df['fame_score'] < 5000)]):,}件")
    print(f"  C級（1000-2999）: {len(df[(df['fame_score'] >= 1000) & (df['fame_score'] < 3000)]):,}件")
    print(f"  D級（1-999）: {len(df[(df['fame_score'] >= 1) & (df['fame_score'] < 1000)]):,}件")
    print(f"  対象外（0）: {len(df[df['fame_score'] == 0]):,}件")

    print(f"\n📈 統計値:")
    print(f"  平均スコア: {df['fame_score'].mean():.1f}")
    print(f"  中央値: {df['fame_score'].median():.1f}")
    print(f"  最高スコア: {df['fame_score'].max():,}")
    print(f"  最低スコア（0除く）: {df[df['fame_score'] > 0]['fame_score'].min() if len(df[df['fame_score'] > 0]) > 0 else 0}")

    # Wikipedia存在率
    wikipedia_count = len(df[df['wikipedia_presence_score'] > 0])
    print(f"\n📚 Wikipedia存在率:")
    print(f"  Wikipedia存在あり: {wikipedia_count:,}件 ({wikipedia_count/len(df)*100:.1f}%)")
    print(f"  Wikipedia存在なし: {len(df) - wikipedia_count:,}件 ({(len(df) - wikipedia_count)/len(df)*100:.1f}%)")

    # トップ20を表示
    print("\n🏆 トップ20:")
    print("-" * 80)
    top20 = df.head(20)[['person_id', 'person_name_display', 'fame_score', 'score_category', 'impact_category']]
    for i, row in top20.iterrows():
        print(f"{len(top20) - list(top20.index).index(i):2d}. [{row['fame_score']:5d}点] {row['person_name_display'][:30]:30s} | {row['score_category']} | {row['impact_category']}")

    # ワースト10（0点除く）
    print("\n📉 ワースト10（0点除く）:")
    print("-" * 80)
    non_zero = df[df['fame_score'] > 0]
    if len(non_zero) > 0:
        worst10 = non_zero.tail(10)[['person_id', 'person_name_display', 'fame_score', 'score_category']]
        for i, row in worst10.iterrows():
            print(f"  [{row['fame_score']:5d}点] {row['person_name_display'][:40]:40s} | {row['score_category']}")

    # 0点の例（最初の10件）
    zero_score = df[df['fame_score'] == 0]
    if len(zero_score) > 0:
        print(f"\n❌ 0点（Wikipedia存在なし）の例（最初の10件/{len(zero_score):,}件中）:")
        print("-" * 80)
        for i, row in zero_score.head(10).iterrows():
            print(f"  {row['person_name_display'][:50]:50s} | 検索結果: {row.get('search_result_count', 0):,}件")

    # 出力ファイル
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_SCORED_{timestamp}.csv'

    # CSV保存（BOM付きUTF-8）
    print(f"\n💾 スコア付きデータを保存中...")
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        df.to_csv(f, index=False)

    print(f"✅ 保存完了: {output_file}")

    # サマリー
    print("\n" + "=" * 80)
    print("✅ スコアリング完了！")
    print("=" * 80)
    print(f"\n📊 結果サマリー:")
    print(f"  総レコード数: {len(df):,}件")
    print(f"  有効スコア（1以上）: {len(df[df['fame_score'] > 0]):,}件")
    print(f"  無効（Wikipedia無し）: {len(df[df['fame_score'] == 0]):,}件")
    print(f"  平均スコア: {df['fame_score'].mean():.1f}点")
    print(f"  出力ファイル: {output_file}")

    return output_file, df

if __name__ == "__main__":
    output_file, df = main()