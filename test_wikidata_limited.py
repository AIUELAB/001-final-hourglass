#!/usr/bin/env python3
"""
Wikidata SPARQLを使用した確定生年データ取得（限定テスト版）
100件のみで動作確認
"""

import pandas as pd
from wikidata_birth_collector import WikidataBirthCollector
from datetime import datetime

def test_limited():
    """限定的なテスト実行"""

    print("=" * 80)
    print("🧪 Wikidata SPARQL限定テスト（100件）")
    print("=" * 80)

    # 入力ファイル
    input_file = "ultra_think_COMPLETE_20250912_042500.csv"

    # データ読み込み
    df = pd.read_csv(input_file, encoding='utf-8-sig')

    # カラム追加
    if 'birth_year_int' not in df.columns:
        df['birth_year_int'] = None
    if 'birth_date' not in df.columns:
        df['birth_date'] = None

    # 100件に限定
    test_df = df.head(100).copy()

    # 一時ファイルに保存
    temp_file = f"test_wikidata_input_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    test_df.to_csv(temp_file, index=False, encoding='utf-8-sig')

    print(f"📝 テストファイル作成: {temp_file}")
    print(f"📊 テストレコード数: {len(test_df)}")

    # Wikidata収集実行
    collector = WikidataBirthCollector()
    result_df = collector.process_csv(temp_file)

    print("\n🎯 テスト完了")

    return result_df

if __name__ == "__main__":
    test_limited()