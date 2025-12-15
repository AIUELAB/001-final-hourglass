#!/usr/bin/env python3
"""
Wikidata SPARQLを使用した確定生年データ取得
推定なし、確実なデータのみを収集
"""

import pandas as pd
import requests
import json
import time
from datetime import datetime
from typing import Optional, Dict
import urllib.parse

class WikidataBirthCollector:
    """Wikidataから確定生年データのみを取得"""

    def __init__(self):
        self.endpoint = "https://query.wikidata.org/sparql"
        self.headers = {
            'User-Agent': 'BirthDataCollector/1.0 (Educational Purpose)',
            'Accept': 'application/sparql-results+json'
        }

    def search_person(self, name_ja: str, name_en: str = None) -> Optional[Dict]:
        """Wikidataから人物の生年月日を検索"""

        # 日本語名で検索
        query = f"""
        SELECT ?person ?personLabel ?birthDate ?source WHERE {{
            ?person rdfs:label "{name_ja}"@ja .
            ?person wdt:P31 wd:Q5 .  # instance of human
            ?person wdt:P569 ?birthDate .  # date of birth
            OPTIONAL {{ ?person wdt:P1343 ?source }}  # described by source
            SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en". }}
        }}
        LIMIT 1
        """

        try:
            response = requests.get(
                self.endpoint,
                params={'query': query, 'format': 'json'},
                headers=self.headers,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data['results']['bindings']:
                    result = data['results']['bindings'][0]
                    birth_date_str = result['birthDate']['value']

                    # 日付パースして標準形式に
                    if 'T' in birth_date_str:
                        birth_date = birth_date_str.split('T')[0]
                    else:
                        birth_date = birth_date_str

                    # 年のみ抽出
                    year = int(birth_date.split('-')[0])

                    return {
                        'birth_date': birth_date,
                        'birth_year': year,
                        'source': 'Wikidata',
                        'wikidata_id': result['person']['value'].split('/')[-1],
                        'confidence': 100  # Wikidataは確定データ
                    }

        except Exception as e:
            print(f"  ⚠️ Wikidata検索エラー: {name_ja} - {str(e)}")

        return None

    def process_csv(self, csv_file: str):
        """CSVファイルを処理してWikidataからデータ取得"""

        print("=" * 80)
        print("🌐 Wikidata SPARQLによる確定データ取得")
        print("=" * 80)

        # データ読み込み
        df = pd.read_csv(csv_file, encoding='utf-8-sig')
        total = len(df)

        # birth_year_intカラムがない場合は追加
        if 'birth_year_int' not in df.columns:
            df['birth_year_int'] = None
            print("⚠️ birth_year_intカラムを追加しました")

        # birth_dateカラムがない場合は追加
        if 'birth_date' not in df.columns:
            df['birth_date'] = None
            print("⚠️ birth_dateカラムを追加しました")

        # 生年データがない記録を対象
        no_birth_mask = df['birth_year_int'].isna()
        targets = df[no_birth_mask]

        print(f"\n📊 処理対象:")
        print(f"  - 総レコード数: {total:,}")
        print(f"  - 生年データなし: {len(targets):,}")

        # 処理開始
        success_count = 0
        birth_date_count = 0
        birth_year_count = 0
        processed = 0

        # データソース記録用の新しい列を追加
        if 'data_source' not in df.columns:
            df['data_source'] = None
        if 'wikidata_id' not in df.columns:
            df['wikidata_id'] = None

        print(f"\n🔍 Wikidata検索開始...")
        print("-" * 80)

        for idx, row in targets.iterrows():
            processed += 1
            person_name_ja = row['person_name_ja']
            person_name_en = row.get('person_name_en', '')

            # Wikidataから検索
            result = self.search_person(person_name_ja, person_name_en)

            if result:
                success_count += 1
                df.at[idx, 'birth_year_int'] = result['birth_year']
                df.at[idx, 'data_source'] = 'Wikidata'
                df.at[idx, 'wikidata_id'] = result['wikidata_id']

                if result.get('birth_date'):
                    df.at[idx, 'birth_date'] = result['birth_date']
                    birth_date_count += 1
                    print(f"[{processed:4d}/{len(targets)}] ✅ {person_name_ja}: {result['birth_date']} (Wikidata)")
                else:
                    birth_year_count += 1
                    print(f"[{processed:4d}/{len(targets)}] 📅 {person_name_ja}: {result['birth_year']}年 (Wikidata)")
            else:
                print(f"[{processed:4d}/{len(targets)}] ⚪ {person_name_ja}: データなし")

            # レート制限対策
            time.sleep(0.5)

            # 進捗表示
            if processed % 50 == 0:
                print(f"\n📊 進捗: {processed}/{len(targets)} ({processed/len(targets)*100:.1f}%)")
                print(f"   成功: {success_count} | 生年月日: {birth_date_count} | 生年: {birth_year_count}\n")

        # 結果保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"ultra_think_WITH_WIKIDATA_{timestamp}.csv"
        df.to_csv(output_file, index=False, encoding='utf-8-sig')

        # 結果サマリー
        print("\n" + "=" * 80)
        print("📊 Wikidata取得結果")
        print("=" * 80)
        print(f"✅ 成功: {success_count:,}件")
        print(f"  - 生年月日: {birth_date_count:,}件")
        print(f"  - 生年のみ: {birth_year_count:,}件")

        # カバー率計算
        total_with_birth = df['birth_year_int'].notna().sum()
        coverage = total_with_birth / total * 100

        print(f"\n📈 カバー率: {coverage:.1f}%")
        print(f"💾 保存先: {output_file}")

        # データ品質レポート
        self.generate_quality_report(df)

        return df

    def generate_quality_report(self, df: pd.DataFrame):
        """データ品質レポート生成"""

        report = {
            'total_records': int(len(df)),
            'with_birth_year': int(df['birth_year_int'].notna().sum()),
            'with_birth_date': int(df['birth_date'].notna().sum()) if 'birth_date' in df.columns else 0,
            'sources': {
                'Wikipedia': int(len(df[df['data_source'] == 'Wikipedia'])) if 'data_source' in df.columns else 0,
                'Wikidata': int(len(df[df['data_source'] == 'Wikidata'])) if 'data_source' in df.columns else 0,
                'Unknown': int(len(df[df['data_source'].isna()])) if 'data_source' in df.columns else len(df)
            },
            'quality_principles': [
                '✅ 確定データのみ使用',
                '✅ 出典明記',
                '✅ 検証可能性確保',
                '❌ 推定値なし',
                '❌ 仮定なし'
            ]
        }

        # レポート出力
        report_file = f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📊 品質レポート: {report_file}")

        # 品質原則の表示
        print("\n📋 データ品質原則:")
        for principle in report['quality_principles']:
            print(f"  {principle}")

if __name__ == "__main__":
    # 最新のCSVファイルを入力
    input_file = "ultra_think_COMPLETE_20250912_042500.csv"

    collector = WikidataBirthCollector()
    result_df = collector.process_csv(input_file)
