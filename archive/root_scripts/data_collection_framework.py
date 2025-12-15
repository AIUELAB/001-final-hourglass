#!/usr/bin/env python3
"""
データ収集品質保証フレームワーク
再発防止のための統一的なSPARQLクエリテンプレートと品質チェック機能
"""

import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import requests


class DataCollectionFramework:
    """データ収集の品質を保証するフレームワーク"""

    def __init__(self):
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        self.quality_checks = {
            'japanese_label': 0,
            'english_label': 0,
            'no_label': 0,
            'mixed_language': 0
        }

    @staticmethod
    def create_sparql_template(occupation_id: str, nationality_id: str = None) -> str:
        """
        標準化されたSPARQLクエリテンプレートを生成
        必ず日本語優先で、英語フォールバック付き
        """
        nationality_filter = f"wdt:P27 wd:{nationality_id} ;" if nationality_id else ""

        template = f"""
        SELECT DISTINCT ?person ?personLabel ?personLabel_ja ?personLabel_en
               ?birthDate ?deathDate ?occupationLabel ?nationalityLabel
        WHERE {{
          ?person wdt:P31 wd:Q5 ;
                  wdt:P106 wd:{occupation_id} ;
                  {nationality_filter}
                  wdt:P569 ?birthDate .
          OPTIONAL {{ ?person wdt:P570 ?deathDate }}
          OPTIONAL {{ ?person wdt:P106 ?occupation }}
          OPTIONAL {{ ?person wdt:P27 ?nationality }}

          # 日本語ラベルを明示的に取得
          OPTIONAL {{ ?person rdfs:label ?personLabel_ja . FILTER(LANG(?personLabel_ja) = "ja") }}
          # 英語ラベルを明示的に取得（フォールバック用）
          OPTIONAL {{ ?person rdfs:label ?personLabel_en . FILTER(LANG(?personLabel_en) = "en") }}

          # サービスラベル（互換性のため）
          SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "ja,en" .
          }}
        }}
        LIMIT 100
        """
        return template

    def validate_query_language_support(self, query: str) -> Dict[str, bool]:
        """
        SPARQLクエリが適切な言語サポートを持っているか検証
        """
        validations = {
            'has_service_label': 'SERVICE wikibase:label' in query,
            'has_japanese_priority': 'ja,en' in query or 'ja' in query,
            'has_explicit_ja_filter': 'FILTER(LANG' in query and 'ja' in query,
            'has_fallback': 'en' in query
        }

        validations['is_valid'] = (
            validations['has_service_label'] and
            validations['has_japanese_priority']
        )

        return validations

    def analyze_data_language(self, data: List[Dict]) -> Dict[str, int]:
        """
        収集されたデータの言語分布を分析
        """
        stats = {
            'total': len(data),
            'japanese': 0,
            'english': 0,
            'mixed': 0,
            'none': 0
        }

        for item in data:
            name = item.get('name', '')
            if not name:
                stats['none'] += 1
            elif self._is_japanese(name):
                stats['japanese'] += 1
            elif self._is_english(name):
                stats['english'] += 1
            else:
                stats['mixed'] += 1

        return stats

    def _is_japanese(self, text: str) -> bool:
        """日本語文字（ひらがな、カタカナ、漢字）を含むか判定"""
        return bool(re.search(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]', text))

    def _is_english(self, text: str) -> bool:
        """英語（ASCII文字のみ）か判定"""
        return bool(re.match(r'^[a-zA-Z\s\-\.\']+$', text))

    def execute_safe_query(self, query: str) -> List[Dict]:
        """
        言語検証付きでクエリを実行
        """
        # クエリの言語サポートを検証
        validation = self.validate_query_language_support(query)
        if not validation['is_valid']:
            print("⚠️ 警告: クエリに適切な言語設定がありません")
            print(f"  検証結果: {validation}")

            # クエリを自動修正
            if not validation['has_service_label']:
                query += '\nSERVICE wikibase:label { bd:serviceParam wikibase:language "ja,en" . }'

        # クエリ実行
        try:
            response = requests.get(
                self.wikidata_endpoint,
                params={'query': query, 'format': 'json'},
                timeout=30
            )

            if response.status_code == 200:
                results = response.json()
                items = results.get('results', {}).get('bindings', [])

                # 結果を処理して日本語を優先
                processed_items = []
                for item in items:
                    processed = self._process_item_with_language_priority(item)
                    processed_items.append(processed)

                return processed_items
            else:
                print(f"❌ クエリ実行エラー: {response.status_code}")
                return []

        except Exception as e:
            print(f"❌ クエリ実行エラー: {e}")
            return []

    def _process_item_with_language_priority(self, item: Dict) -> Dict:
        """
        アイテムを処理し、日本語ラベルを優先的に使用
        """
        # 日本語ラベルを優先
        name_ja = item.get('personLabel_ja', {}).get('value', '')
        name_en = item.get('personLabel_en', {}).get('value', '')
        name_default = item.get('personLabel', {}).get('value', '')

        # 優先順位: 日本語 > デフォルト > 英語
        name = name_ja or name_default or name_en

        # Wikidata IDのままの場合は英語名を使用
        if name.startswith('Q') and name[1:].isdigit():
            name = name_en or name

        return {
            'name': name,
            'original_name_ja': name_ja,
            'original_name_en': name_en,
            'wikidata_id': item.get('person', {}).get('value', '').split('/')[-1],
            'birth_date': item.get('birthDate', {}).get('value', ''),
            'death_date': item.get('deathDate', {}).get('value', ''),
            'occupation': item.get('occupationLabel', {}).get('value', ''),
            'nationality': item.get('nationalityLabel', {}).get('value', '')
        }

    def generate_quality_report(self, data: List[Dict]) -> str:
        """
        データ品質レポートを生成
        """
        stats = self.analyze_data_language(data)

        report = f"""
# データ収集品質レポート

## 言語分布
- 総レコード数: {stats['total']}
- 日本語名: {stats['japanese']} ({stats['japanese']/max(stats['total'],1)*100:.1f}%)
- 英語名: {stats['english']} ({stats['english']/max(stats['total'],1)*100:.1f}%)
- 混合/その他: {stats['mixed']} ({stats['mixed']/max(stats['total'],1)*100:.1f}%)
- 名前なし: {stats['none']} ({stats['none']/max(stats['total'],1)*100:.1f}%)

## 品質評価
- 日本語カバー率: {stats['japanese']/max(stats['total'],1)*100:.1f}%
- 品質スコア: {'✅ 良好' if stats['japanese']/max(stats['total'],1) > 0.7 else '⚠️ 要改善'}

## 推奨事項
"""
        if stats['japanese']/max(stats['total'],1) < 0.7:
            report += "- SPARQLクエリの言語設定を確認してください\n"
            report += "- SERVICE wikibase:labelに'ja,en'の順序を指定してください\n"
            report += "- 明示的な日本語ラベル取得を追加してください\n"

        return report


def demonstrate_framework():
    """フレームワークの使用例"""
    framework = DataCollectionFramework()

    # 1. 標準化されたクエリテンプレートの生成
    print("📋 標準化されたSPARQLクエリテンプレート生成")
    query = framework.create_sparql_template(
        occupation_id="Q33999",  # 俳優
        nationality_id="Q17"      # 日本
    )
    print(query[:500] + "...")

    # 2. クエリの言語サポート検証
    print("\n🔍 クエリの言語サポート検証")
    validation = framework.validate_query_language_support(query)
    for key, value in validation.items():
        print(f"  {key}: {value}")

    # 3. サンプルデータで言語分析
    print("\n📊 サンプルデータの言語分析")
    sample_data = [
        {'name': '山田太郎'},
        {'name': 'John Smith'},
        {'name': '田中花子'},
        {'name': 'Mary Johnson'},
        {'name': '佐藤健'}
    ]
    stats = framework.analyze_data_language(sample_data)
    print(f"  日本語: {stats['japanese']}/{stats['total']}")
    print(f"  英語: {stats['english']}/{stats['total']}")

    print("\n✅ データ収集フレームワークの準備完了")


if __name__ == "__main__":
    demonstrate_framework()
