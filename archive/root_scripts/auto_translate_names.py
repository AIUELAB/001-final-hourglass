#!/usr/bin/env python3
"""
未翻訳データ自動翻訳システム
既存のWikidata IDを使用して日本語名を自動取得
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import pandas as pd
import requests


class AutoTranslateNames:
    """未翻訳データの自動翻訳システム"""

    def __init__(self):
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        self.stats = {
            'total_processed': 0,
            'successfully_translated': 0,
            'already_japanese': 0,
            'translation_failed': 0,
            'no_wikidata_id': 0,
            'start_time': datetime.now()
        }
        self.translation_cache = {}

    def is_japanese(self, text: str) -> bool:
        """日本語文字を含むか判定"""
        if not text:
            return False
        return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))

    def is_english(self, text: str) -> bool:
        """英語（ASCII文字のみ）か判定"""
        if not text:
            return False
        return bool(re.match(r'^[a-zA-Z\s\-\.\']+$', text))

    def get_japanese_name_from_wikidata(self, wikidata_id: str) -> Optional[str]:
        """Wikidata IDから日本語名を取得"""

        # キャッシュチェック
        if wikidata_id in self.translation_cache:
            return self.translation_cache[wikidata_id]

        # クリーンなWikidata ID取得
        if wikidata_id.startswith('http'):
            wikidata_id = wikidata_id.split('/')[-1]

        query = f"""
        SELECT ?itemLabel_ja ?itemLabel_en ?itemAltLabel_ja
        WHERE {{
          wd:{wikidata_id} rdfs:label ?itemLabel_ja .
          FILTER(LANG(?itemLabel_ja) = "ja")
          OPTIONAL {{
            wd:{wikidata_id} rdfs:label ?itemLabel_en .
            FILTER(LANG(?itemLabel_en) = "en")
          }}
          OPTIONAL {{
            wd:{wikidata_id} skos:altLabel ?itemAltLabel_ja .
            FILTER(LANG(?itemAltLabel_ja) = "ja")
          }}
        }}
        LIMIT 1
        """

        try:
            response = requests.get(
                self.wikidata_endpoint,
                params={'query': query, 'format': 'json'},
                timeout=10
            )

            if response.status_code == 200:
                results = response.json()
                bindings = results.get('results', {}).get('bindings', [])

                if bindings:
                    item = bindings[0]
                    japanese_name = item.get('itemLabel_ja', {}).get('value', '')

                    # キャッシュに保存
                    self.translation_cache[wikidata_id] = japanese_name
                    return japanese_name

        except Exception as e:
            print(f"  ⚠️ Wikidata取得エラー ({wikidata_id}): {e}")

        return None

    def batch_translate_from_wikidata(self, wikidata_ids: List[str]) -> Dict[str, str]:
        """複数のWikidata IDから日本語名を一括取得"""

        # 空リストの処理
        if not wikidata_ids:
            return {}

        # クリーンなID取得
        clean_ids = []
        for wid in wikidata_ids:
            if wid:
                if wid.startswith('http'):
                    clean_ids.append(wid.split('/')[-1])
                else:
                    clean_ids.append(wid)

        if not clean_ids:
            return {}

        # VALUES句を使用して一括クエリ
        values_clause = ' '.join([f'wd:{wid}' for wid in clean_ids[:50]])  # 最大50件

        query = f"""
        SELECT ?item ?itemLabel_ja ?itemLabel_en
        WHERE {{
          VALUES ?item {{ {values_clause} }}
          OPTIONAL {{
            ?item rdfs:label ?itemLabel_ja .
            FILTER(LANG(?itemLabel_ja) = "ja")
          }}
          OPTIONAL {{
            ?item rdfs:label ?itemLabel_en .
            FILTER(LANG(?itemLabel_en) = "en")
          }}
        }}
        """

        translations = {}

        try:
            response = requests.get(
                self.wikidata_endpoint,
                params={'query': query, 'format': 'json'},
                timeout=30
            )

            if response.status_code == 200:
                results = response.json()
                bindings = results.get('results', {}).get('bindings', [])

                for item in bindings:
                    wikidata_url = item.get('item', {}).get('value', '')
                    wikidata_id = wikidata_url.split('/')[-1]
                    japanese_name = item.get('itemLabel_ja', {}).get('value', '')

                    if japanese_name:
                        translations[wikidata_id] = japanese_name
                        self.translation_cache[wikidata_id] = japanese_name

        except Exception as e:
            print(f"  ⚠️ バッチ翻訳エラー: {e}")

        return translations

    def process_data(self, data: Any, batch_size: int = 50) -> Tuple[Dict, Dict]:
        """
        データを処理して未翻訳の名前を日本語に変換
        """
        print("🔄 未翻訳データの自動翻訳開始")

        # データ形式の判定と変換
        if isinstance(data, dict):
            # 辞書形式の場合、値のリストに変換
            data_list = list(data.values())
            is_dict_format = True
            original_keys = list(data.keys())
        else:
            data_list = data
            is_dict_format = False
            original_keys = []

        print(f"  総レコード数: {len(data_list)}")

        updated_data = []
        translation_log = []

        # まず未翻訳データを特定
        untranslated = []
        for i, person in enumerate(data_list):
            # personが辞書でない場合はスキップ
            if not isinstance(person, dict):
                continue

            name = person.get('name', '')
            wikidata_id = person.get('wikidata_id', '')

            if not self.is_japanese(name) and wikidata_id:
                untranslated.append((i, person))

        print(f"  未翻訳レコード: {len(untranslated)}")

        # バッチ処理で翻訳
        for batch_start in range(0, len(untranslated), batch_size):
            batch_end = min(batch_start + batch_size, len(untranslated))
            batch = untranslated[batch_start:batch_end]

            # Wikidata IDのリストを作成
            wikidata_ids = [p[1].get('wikidata_id', '') for p in batch]

            print(f"\n  バッチ {batch_start//batch_size + 1}: {len(batch)}件処理中...")

            # 一括翻訳
            translations = self.batch_translate_from_wikidata(wikidata_ids)

            # 結果を適用
            for idx, person in batch:
                wikidata_id = person.get('wikidata_id', '')
                original_name = person.get('name', '')

                if wikidata_id in translations:
                    japanese_name = translations[wikidata_id]
                    if japanese_name and japanese_name != original_name:
                        person['name'] = japanese_name
                        person['original_english_name'] = original_name
                        self.stats['successfully_translated'] += 1

                        translation_log.append({
                            'id': person.get('id', ''),
                            'wikidata_id': wikidata_id,
                            'original_name': original_name,
                            'japanese_name': japanese_name,
                            'category': person.get('category', '')
                        })

                        print(f"    ✅ {original_name} → {japanese_name}")
                else:
                    self.stats['translation_failed'] += 1

            # レート制限対策
            time.sleep(1)

        # すべてのデータを更新済みリストに追加
        for person in data_list:
            if not isinstance(person, dict):
                updated_data.append(person)
                continue

            self.stats['total_processed'] += 1

            name = person.get('name', '')
            if self.is_japanese(name):
                self.stats['already_japanese'] += 1
            elif not person.get('wikidata_id'):
                self.stats['no_wikidata_id'] += 1

            updated_data.append(person)

        # 元の形式に戻す
        if is_dict_format:
            updated_dict = {}
            for key, value in zip(original_keys, updated_data):
                updated_dict[key] = value
            result_data = updated_dict
        else:
            result_data = updated_data

        # 統計と翻訳ログを返す
        return result_data, {
            'stats': self.stats,
            'translations': translation_log
        }

    def save_results(self, data: Union[List[Dict], Dict], log: Dict, output_prefix: str = "auto_translated"):
        """翻訳結果を保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSONファイルに保存
        json_path = f"{output_prefix}_{timestamp}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # CSVファイルに保存（辞書形式の場合は値のリストに変換）
        csv_path = f"{output_prefix}_{timestamp}.csv"
        if isinstance(data, dict):
            df = pd.DataFrame(list(data.values()))
        else:
            df = pd.DataFrame(data)
        df.to_csv(csv_path, index=False, encoding='utf-8')

        # 翻訳ログを保存
        log_path = f"{output_prefix}_log_{timestamp}.json"
        with open(log_path, 'w', encoding='utf-8') as f:
            json.dump(log, f, ensure_ascii=False, indent=2)

        # レポート生成
        report = self.generate_report(log)
        report_path = f"{output_prefix}_report_{timestamp}.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)

        print("\n📁 ファイル保存完了:")
        print(f"  - データ: {json_path}")
        print(f"  - CSV: {csv_path}")
        print(f"  - ログ: {log_path}")
        print(f"  - レポート: {report_path}")

        return json_path, csv_path, log_path, report_path

    def generate_report(self, log: Dict) -> str:
        """翻訳レポートを生成"""
        stats = log.get('stats', {})
        translations = log.get('translations', [])

        elapsed = datetime.now() - stats.get('start_time', datetime.now())

        report = f"""# 自動翻訳実行レポート

## 実行日時
{datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}

## 処理統計
- **総処理レコード数**: {stats.get('total_processed', 0):,}
- **既に日本語**: {stats.get('already_japanese', 0):,} ({stats.get('already_japanese', 0)/max(stats.get('total_processed', 1),1)*100:.1f}%)
- **翻訳成功**: {stats.get('successfully_translated', 0):,} ({stats.get('successfully_translated', 0)/max(stats.get('total_processed', 1),1)*100:.1f}%)
- **翻訳失敗**: {stats.get('translation_failed', 0):,} ({stats.get('translation_failed', 0)/max(stats.get('total_processed', 1),1)*100:.1f}%)
- **Wikidata IDなし**: {stats.get('no_wikidata_id', 0):,}

## 処理時間
{elapsed}

## 翻訳例（最初の20件）
| Wikidata ID | 英語名 | 日本語名 | カテゴリー |
|-------------|--------|----------|------------|
"""

        for item in translations[:20]:
            report += f"| {item['wikidata_id']} | {item['original_name']} | {item['japanese_name']} | {item['category']} |\n"

        if len(translations) > 20:
            report += f"\n*他 {len(translations) - 20}件の翻訳完了*\n"

        report += f"""
## 品質改善率
- **翻訳前の英語名率**: {(stats.get('total_processed', 0) - stats.get('already_japanese', 0))/max(stats.get('total_processed', 1),1)*100:.1f}%
- **翻訳後の英語名率**: {(stats.get('total_processed', 0) - stats.get('already_japanese', 0) - stats.get('successfully_translated', 0))/max(stats.get('total_processed', 1),1)*100:.1f}%
- **改善率**: {stats.get('successfully_translated', 0)/max(stats.get('total_processed', 1) - stats.get('already_japanese', 0),1)*100:.1f}%

## 推奨事項
"""

        if stats.get('translation_failed', 0) > 0:
            report += "- 翻訳失敗したレコードのWikidata IDを確認してください\n"
        if stats.get('no_wikidata_id', 0) > 0:
            report += "- Wikidata IDが欠落しているレコードの補完が必要です\n"

        return report


def main():
    """メイン実行関数"""
    translator = AutoTranslateNames()

    # 最新のデータファイルを読み込み
    print("📂 データファイル読み込み中...")

    # 利用可能なファイルを確認
    json_files = list(Path('.').glob('final_12410_with_display_names.json'))
    if not json_files:
        json_files = list(Path('.').glob('comprehensive_fixed_*.json'))

    if not json_files:
        print("❌ 処理対象のJSONファイルが見つかりません")
        return

    # 最新のファイルを使用
    input_file = sorted(json_files)[-1]
    print(f"  入力ファイル: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # バックアップ作成
    backup_path = f"backup_before_translate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  バックアップ: {backup_path}")

    # 翻訳実行
    updated_data, log = translator.process_data(data)

    # 結果保存
    translator.save_results(updated_data, log)

    print("\n✅ 自動翻訳処理完了")


if __name__ == "__main__":
    main()
