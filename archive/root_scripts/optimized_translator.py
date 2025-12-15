#!/usr/bin/env python3
"""
最適化された自動翻訳システム
タイムアウト・レート制限・負荷を考慮した効率的な実装
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests


class OptimizedTranslator:
    """最適化された翻訳システム"""

    def __init__(self):
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        self.max_execution_time = 90  # 90秒制限
        self.batch_size = 20  # 小さめのバッチサイズ
        self.max_batches_per_run = 15  # 1回の実行での最大バッチ数
        self.wait_between_batches = 0.5  # バッチ間待機時間

        # キャッシュとログ
        self.translation_cache = self.load_cache()
        self.processed_ids = self.load_processed_ids()
        self.stats = {
            'start_time': datetime.now(),
            'processed': 0,
            'translated': 0,
            'cached': 0,
            'failed': 0
        }

    def load_cache(self) -> Dict[str, str]:
        """翻訳キャッシュを読み込み"""
        cache_file = Path('translation_cache.json')
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def save_cache(self):
        """翻訳キャッシュを保存"""
        with open('translation_cache.json', 'w', encoding='utf-8') as f:
            json.dump(self.translation_cache, f, ensure_ascii=False, indent=2)

    def load_processed_ids(self) -> set:
        """処理済みIDを読み込み"""
        processed_file = Path('processed_ids.json')
        if processed_file.exists():
            with open(processed_file, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        return set()

    def save_processed_ids(self):
        """処理済みIDを保存"""
        with open('processed_ids.json', 'w', encoding='utf-8') as f:
            json.dump(list(self.processed_ids), f)

    def is_japanese(self, text: str) -> bool:
        """日本語文字を含むか判定"""
        if not text:
            return False
        return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))

    def prioritize_items(self, items: List[Dict]) -> List[Dict]:
        """翻訳優先度でソート"""
        def priority_score(item):
            name = item.get('name', '')
            wikidata_id = item.get('wikidata_id', 'Q999999999')

            # 短い名前を優先（APIが成功しやすい）
            name_score = -len(name)

            # 小さいQIDを優先（有名人の可能性高い）
            try:
                qid_num = int(wikidata_id.replace('Q', ''))
                qid_score = -qid_num
            except:
                qid_score = -999999999

            return (name_score, qid_score)

        return sorted(items, key=priority_score)

    def batch_translate_optimized(self, wikidata_ids: List[str]) -> Dict[str, str]:
        """最適化されたバッチ翻訳"""
        translations = {}

        # キャッシュチェック
        uncached_ids = []
        for wid in wikidata_ids:
            if wid in self.translation_cache:
                translations[wid] = self.translation_cache[wid]
                self.stats['cached'] += 1
            else:
                uncached_ids.append(wid)

        if not uncached_ids:
            return translations

        # SPARQLクエリ構築（最大20件）
        values_clause = ' '.join([f'wd:{wid}' for wid in uncached_ids[:20]])

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

        try:
            response = requests.get(
                self.wikidata_endpoint,
                params={'query': query, 'format': 'json'},
                timeout=10
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
                        self.stats['translated'] += 1
        except Exception as e:
            print(f"  ⚠️ API エラー: {e}")
            self.stats['failed'] += len(uncached_ids)

        return translations

    def run_optimized_translation(self, input_file: str = None) -> Tuple[str, Dict]:
        """最適化された翻訳実行（90秒制限）"""
        start_time = time.time()

        # 入力ファイル決定
        if not input_file:
            translated_files = list(Path('.').glob('partial_translated_*.json'))
            if translated_files:
                input_file = str(sorted(translated_files)[-1])
            else:
                input_file = 'final_12410_with_display_names.json'

        print("🚀 最適化翻訳実行開始（90秒制限）")
        print(f"  入力: {input_file}")

        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)

        # 未翻訳データ抽出（未処理のみ）
        untranslated = []
        for key, value in all_data.items():
            if key in self.processed_ids:
                continue

            if isinstance(value, dict):
                name = value.get('name', '')
                wikidata_id = value.get('wikidata_id', '')

                if name and not self.is_japanese(name) and wikidata_id:
                    untranslated.append({
                        'key': key,
                        'name': name,
                        'wikidata_id': wikidata_id,
                        'data': value
                    })

        # 優先度順にソート
        untranslated = self.prioritize_items(untranslated)

        print(f"  未処理: {len(untranslated)}件")
        print(f"  バッチサイズ: {self.batch_size}")
        print(f"  最大バッチ数: {self.max_batches_per_run}")

        # バッチ処理
        batches_processed = 0
        for batch_start in range(0, len(untranslated), self.batch_size):
            # 時間チェック
            elapsed = time.time() - start_time
            if elapsed > self.max_execution_time:
                print(f"  ⏱️ 制限時間到達 ({elapsed:.1f}秒)")
                break

            if batches_processed >= self.max_batches_per_run:
                print("  📦 最大バッチ数到達")
                break

            batch_end = min(batch_start + self.batch_size, len(untranslated))
            batch = untranslated[batch_start:batch_end]

            # Wikidata IDリスト作成
            wikidata_ids = [item['wikidata_id'] for item in batch]

            print(f"  バッチ {batches_processed + 1}: {len(batch)}件処理...", end='')

            # 翻訳実行
            translations = self.batch_translate_optimized(wikidata_ids)

            # 結果適用
            translated_count = 0
            for item in batch:
                wikidata_id = item['wikidata_id']
                if wikidata_id in translations:
                    japanese_name = translations[wikidata_id]
                    all_data[item['key']]['name'] = japanese_name
                    all_data[item['key']]['original_english_name'] = item['name']
                    translated_count += 1

                # 処理済みマーク
                self.processed_ids.add(item['key'])
                self.stats['processed'] += 1

            print(f" {translated_count}件翻訳")

            batches_processed += 1

            # 待機
            if batch_start + self.batch_size < len(untranslated):
                time.sleep(self.wait_between_batches)

        # 結果保存
        output_file = f"optimized_translated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)

        # キャッシュと処理済みID保存
        self.save_cache()
        self.save_processed_ids()

        # 統計
        elapsed = time.time() - start_time
        self.stats['elapsed'] = elapsed

        print("\n📊 実行結果:")
        print(f"  処理時間: {elapsed:.1f}秒")
        print(f"  処理済み: {self.stats['processed']}件")
        print(f"  翻訳成功: {self.stats['translated']}件")
        print(f"  キャッシュ使用: {self.stats['cached']}件")
        print(f"  失敗: {self.stats['failed']}件")
        print(f"  出力: {output_file}")

        return output_file, self.stats

    def get_remaining_count(self, input_file: str = None) -> int:
        """残り未処理件数を取得"""
        if not input_file:
            translated_files = list(Path('.').glob('optimized_translated_*.json'))
            if translated_files:
                input_file = str(sorted(translated_files)[-1])
            else:
                input_file = 'partial_translated_20250824_162027.json'

        with open(input_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)

        untranslated_count = 0
        for key, value in all_data.items():
            if key in self.processed_ids:
                continue

            if isinstance(value, dict):
                name = value.get('name', '')
                wikidata_id = value.get('wikidata_id', '')

                if name and not self.is_japanese(name) and wikidata_id:
                    untranslated_count += 1

        return untranslated_count


def main():
    """メイン実行"""
    translator = OptimizedTranslator()

    # 残り件数確認
    remaining = translator.get_remaining_count()
    print(f"📊 未処理データ: {remaining:,}件")

    if remaining == 0:
        print("✅ すべてのデータが処理済みです")
        return

    # 実行回数計算
    items_per_run = translator.batch_size * translator.max_batches_per_run
    runs_needed = (remaining + items_per_run - 1) // items_per_run

    print("📈 実行計画:")
    print(f"  1回あたり: 最大{items_per_run}件")
    print(f"  必要実行回数: 約{runs_needed}回")
    print(f"  推定総時間: 約{runs_needed * 1.5:.1f}分")

    # 1回実行
    output_file, stats = translator.run_optimized_translation()

    # 次回実行の案内
    new_remaining = translator.get_remaining_count(output_file)
    if new_remaining > 0:
        print(f"\n💡 残り{new_remaining:,}件")
        print("  次回実行: python3 optimized_translator.py")


if __name__ == "__main__":
    main()
