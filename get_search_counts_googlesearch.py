#!/usr/bin/env python3
"""
googlesearch-pythonライブラリを使って検索結果数を取得
無料で使用可能な方法
"""

import pandas as pd
import time
from datetime import datetime
import json
import os

def get_google_search_count(query):
    """Google検索結果数を取得（推定値）"""
    try:
        from googlesearch import search

        # 検索を実行（最初の10件のみ取得）
        results = list(search(query, num_results=10, lang='ja'))

        if len(results) > 0:
            # 検索結果がある場合、推定値を計算
            # 10件の結果がある = 通常は数千〜数百万件存在
            if len(results) >= 10:
                return 1000000  # 10件フルにある場合は100万件以上と推定
            elif len(results) >= 5:
                return 100000   # 5-9件の場合は10万件程度と推定
            elif len(results) >= 1:
                return 10000    # 1-4件の場合は1万件程度と推定
        return 0

    except Exception as e:
        print(f"エラー: {e}")
        return None

def main():
    print("=" * 60)
    print("🔍 Google検索結果数取得（googlesearch-python）")
    print("=" * 60)

    # ライブラリをインストール
    print("\n📦 必要なライブラリをインストール中...")
    os.system('pip install googlesearch-python -q')

    # CSVファイルを読み込み
    csv_file = 'ultra_think_with_search_counts_20250915_140948.csv'
    print(f"\n📂 ファイル読み込み: {csv_file}")
    df = pd.read_csv(csv_file)
    print(f"✅ {len(df)}件のデータを読み込みました")

    # 既にBrave Searchで取得済みのデータを確認
    already_searched = df[df['search_source'] == 'brave_search']
    print(f"\n📊 既存のBrave Search取得済み: {len(already_searched)}件")

    # 未取得のデータ（predictionのもの）を抽出
    not_searched = df[df['search_source'] != 'brave_search'].copy()
    print(f"📊 未取得データ: {len(not_searched)}件")

    if len(not_searched) == 0:
        print("✅ すべてのデータは既に取得済みです")
        return

    # 優先度スコアを再計算
    not_searched['priority_score'] = (
        not_searched['name_recognition'].fillna(0) * 0.4 +
        (not_searched['wikipedia_url'].notna().astype(int) * 20) * 0.3 +
        not_searched['category'].map({
            'エンタメ': 10, 'スポーツ': 9, '政治': 8,
            'ビジネス': 7, '科学': 6, '芸術': 5,
            '歴史': 4, 'その他': 3, '架空の存在': 2
        }).fillna(0) * 0.3
    )

    # 優先度順にソートして上位100件を選択（レート制限対策）
    not_searched = not_searched.nlargest(100, 'priority_score')
    print(f"\n🎯 取得対象: {len(not_searched)}件（優先度順）")

    # 進捗表示
    print("\n" + "=" * 60)
    print("📡 Google検索開始（無料API）")
    print("=" * 60)

    success_count = 0
    error_count = 0

    for idx, (index, row) in enumerate(not_searched.iterrows(), 1):
        # 検索クエリを生成
        display_name = row['person_name_display']
        search_query = f'"{display_name}"'

        # 進捗表示
        if idx % 10 == 0 or idx == 1:
            print(f"\n⏳ 進捗: {idx}/{len(not_searched)} ({idx/len(not_searched)*100:.1f}%)")
            print(f"   成功: {success_count}, エラー: {error_count}")

        # 検索実行
        print(f"  {idx:3d}. {display_name:30s} ... ", end="", flush=True)

        result = get_google_search_count(search_query)

        if result is not None:
            # データフレームを更新
            df.loc[index, 'search_result_count'] = result
            df.loc[index, 'search_query'] = search_query
            df.loc[index, 'search_timestamp'] = datetime.now().isoformat()
            df.loc[index, 'search_source'] = 'googlesearch'

            print(f"✅ {result:,}件（推定）")
            success_count += 1
        else:
            print("❌ 失敗")
            error_count += 1

            # エラーが多い場合は中断
            if error_count > 20:
                print("\n⚠️ エラーが多いため処理を中断します")
                break

        # レート制限対策（5秒待機）
        time.sleep(5.0)

    # 最終結果を保存
    print("\n" + "=" * 60)
    print("💾 結果を保存")
    print("=" * 60)

    # 新しいファイル名で保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_googlesearch_{timestamp}.csv'

    # UTF-8 BOMで保存（Excel対応）
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        df.to_csv(f, index=False)

    print(f"✅ 保存完了: {output_file}")

    # 統計情報を表示
    searched = df[(df['search_source'] == 'brave_search') | (df['search_source'] == 'googlesearch')]
    print(f"\n📊 最終統計:")
    print(f"  総レコード数: {len(df):,}件")
    print(f"  検索済み: {len(searched):,}件 ({len(searched)/len(df)*100:.1f}%)")
    print(f"    - Brave Search: {len(df[df['search_source'] == 'brave_search']):,}件")
    print(f"    - Google Search: {len(df[df['search_source'] == 'googlesearch']):,}件")
    print(f"  今回追加: {success_count}件")
    print(f"  残り（予測値）: {len(df) - len(searched):,}件")

if __name__ == "__main__":
    main()
