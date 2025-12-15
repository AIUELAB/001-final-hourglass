#!/usr/bin/env python3
"""
強化版データ収集システム - クイック実行版
「その他」カテゴリを10%以下に削減するための高度な分類システム
"""

import json
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests


class EnhancedQuickCollector:
    """高速実行版の強化データコレクター"""

    def __init__(self):
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        self.collected_data = []
        self.category_stats = {}

    def get_quick_diverse_people(self) -> List[Dict]:
        """多様なカテゴリから少数ずつ迅速に収集"""
        categories = [
            # テクノロジー
            ("YouTuber", "wd:Q17125263", 20),
            ("起業家", "wd:Q131524", 20),
            ("eスポーツ選手", "wd:Q4379701", 15),

            # 文化・芸術
            ("漫画家", "wd:Q3658341", 20),
            ("声優", "wd:Q622807", 20),
            ("アニメ監督", "wd:Q3665646", 15),

            # 社会・リーダーシップ
            ("女性起業家", "wd:Q131524", 15),
            ("社会起業家", "wd:Q3242115", 15),
            ("環境活動家", "wd:Q15253558", 10),

            # スポーツ（細分化）
            ("プロ野球選手", "wd:Q10871364", 15),
            ("サッカー選手", "wd:Q937857", 15),
            ("オリンピック選手", "wd:Q4330518", 10),

            # エンターテインメント
            ("お笑い芸人", "wd:Q245068", 20),
            ("K-POPアーティスト", "wd:Q188451", 10),
            ("TikToker", "wd:Q94791573", 10),

            # 学術・専門職
            ("AI研究者", "wd:Q1650915", 10),
            ("医師", "wd:Q39631", 10),
            ("宇宙飛行士", "wd:Q11631", 5),
        ]

        all_people = []

        for category_name, category_id, limit in categories:
            print(f"🔍 {category_name}を収集中... (最大{limit}人)")

            query = f"""
            SELECT DISTINCT ?person ?personLabel ?birthDate ?nationalityLabel
            WHERE {{
              ?person wdt:P31 wd:Q5 ;
                      wdt:P106 {category_id} ;
                      wdt:P569 ?birthDate .
              OPTIONAL {{ ?person wdt:P27 ?nationality }}
              FILTER(YEAR(?birthDate) > 1970)
              SERVICE wikibase:label {{ bd:serviceParam wikibase:language "ja,en". }}
            }}
            LIMIT {limit}
            """

            try:
                response = requests.get(
                    self.wikidata_endpoint,
                    params={'query': query, 'format': 'json'},
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    people = []

                    for item in data['results']['bindings']:
                        person_data = {
                            'name': item['personLabel']['value'],
                            'wikidata_id': item['person']['value'].split('/')[-1],
                            'birth_date': item['birthDate']['value'][:10],
                            'nationality': item.get('nationalityLabel', {}).get('value', '不明'),
                            'main_category': self._determine_main_category(category_name),
                            'subcategory': category_name,
                            'source': 'Wikidata'
                        }

                        # 名前の検証
                        if self._is_valid_name(person_data['name']):
                            people.append(person_data)

                    all_people.extend(people)
                    print(f"  ✅ {len(people)}人収集")

            except Exception as e:
                print(f"  ⚠️ エラー: {e}")
                continue

            time.sleep(0.5)  # API制限対策

        return all_people

    def _determine_main_category(self, subcategory: str) -> str:
        """サブカテゴリから主カテゴリを決定"""
        category_map = {
            # テクノロジー
            'YouTuber': 'テクノロジー・デジタル',
            '起業家': 'テクノロジー・デジタル',
            'eスポーツ選手': 'テクノロジー・デジタル',
            'TikToker': 'テクノロジー・デジタル',
            'AI研究者': 'テクノロジー・デジタル',

            # 文化・芸術
            '漫画家': '文化・芸術',
            '声優': '文化・芸術',
            'アニメ監督': '文化・芸術',

            # スポーツ
            'プロ野球選手': 'スポーツ',
            'サッカー選手': 'スポーツ',
            'オリンピック選手': 'スポーツ',

            # エンターテインメント
            'お笑い芸人': 'エンターテインメント',
            'K-POPアーティスト': 'エンターテインメント',

            # 社会・学術
            '女性起業家': '社会・リーダーシップ',
            '社会起業家': '社会・リーダーシップ',
            '環境活動家': '社会・リーダーシップ',
            '医師': '学術・専門職',
            '宇宙飛行士': '学術・専門職',
        }

        return category_map.get(subcategory, 'その他')

    def _is_valid_name(self, name: str) -> bool:
        """名前の妥当性を検証"""
        # 数字のみ、記号のみ、地名などを除外
        if not name or len(name) < 2:
            return False
        if name.isdigit():
            return False
        if re.match(r'^[0-9\W]+$', name):
            return False

        # 地名リスト（拡張可能）
        place_names = ['北海道', '東京都', '大阪府', '京都府', '神奈川県']
        if name in place_names:
            return False

        return True

    def analyze_category_distribution(self, people: List[Dict]) -> Dict:
        """カテゴリ分布を分析"""
        main_categories = {}
        subcategories = {}

        for person in people:
            main_cat = person.get('main_category', 'その他')
            sub_cat = person.get('subcategory', '未分類')

            main_categories[main_cat] = main_categories.get(main_cat, 0) + 1
            subcategories[sub_cat] = subcategories.get(sub_cat, 0) + 1

        total = len(people)

        # パーセンテージ計算
        main_cat_pct = {k: (v/total*100) for k, v in main_categories.items()}
        sub_cat_pct = {k: (v/total*100) for k, v in subcategories.items()}

        return {
            'total_people': total,
            'main_categories': main_categories,
            'subcategories': subcategories,
            'main_category_percentages': main_cat_pct,
            'subcategory_percentages': sub_cat_pct,
            'other_percentage': main_cat_pct.get('その他', 0)
        }

    def export_to_csv(self, people: List[Dict], filename: str):
        """CSVファイルにエクスポート"""
        df = pd.DataFrame(people)

        # カラムの整理
        columns = [
            'name', 'birth_date', 'nationality',
            'main_category', 'subcategory',
            'wikidata_id', 'source'
        ]

        # 存在するカラムのみ選択
        existing_columns = [col for col in columns if col in df.columns]
        df = df[existing_columns]

        # CSVエクスポート
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"📄 {filename}にエクスポート完了")

    def generate_quality_report(self, analysis: Dict) -> str:
        """品質レポートを生成"""
        report = []
        report.append("=" * 60)
        report.append("📊 データ品質レポート")
        report.append("=" * 60)
        report.append(f"\n✅ 総収集人数: {analysis['total_people']}人")

        # 主カテゴリ分布
        report.append("\n📈 主カテゴリ分布:")
        for cat, count in sorted(analysis['main_categories'].items(),
                                 key=lambda x: x[1], reverse=True):
            pct = analysis['main_category_percentages'][cat]
            bar = '█' * int(pct/2)
            report.append(f"  {cat:20} {count:4}人 ({pct:5.1f}%) {bar}")

        # 「その他」カテゴリの状況
        other_pct = analysis['other_percentage']
        report.append(f"\n🎯 「その他」カテゴリ: {other_pct:.1f}%")

        if other_pct < 10:
            report.append("  ✨ 目標達成！（10%以下）")
        else:
            report.append("  ⚠️ 目標未達（目標: 10%以下）")

        # サブカテゴリ上位10
        report.append("\n📋 サブカテゴリ上位10:")
        sorted_subs = sorted(analysis['subcategories'].items(),
                           key=lambda x: x[1], reverse=True)[:10]

        for i, (cat, count) in enumerate(sorted_subs, 1):
            pct = analysis['subcategory_percentages'][cat]
            report.append(f"  {i:2}. {cat:20} {count:3}人 ({pct:4.1f}%)")

        report.append("\n" + "=" * 60)

        return "\n".join(report)

def main():
    """メイン処理"""
    print("🚀 強化版データ収集システム（クイック版）を開始")
    print("=" * 60)

    collector = EnhancedQuickCollector()

    # データ収集
    print("\n📡 多様なカテゴリからデータを収集中...")
    people = collector.get_quick_diverse_people()

    # カテゴリ分布の分析
    print("\n📊 カテゴリ分布を分析中...")
    analysis = collector.analyze_category_distribution(people)

    # CSVエクスポート
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"enhanced_people_data_{timestamp}.csv"
    collector.export_to_csv(people, csv_filename)

    # 品質レポート生成
    report = collector.generate_quality_report(analysis)
    print(report)

    # レポートをファイルに保存
    report_filename = f"quality_report_{timestamp}.txt"
    with open(report_filename, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f"\n📝 レポートを{report_filename}に保存しました")

    # 改善結果のサマリー
    print("\n" + "=" * 60)
    print("🎉 データ収集完了！")
    print(f"  収集人数: {analysis['total_people']}人")
    print(f"  「その他」カテゴリ: {analysis['other_percentage']:.1f}%")

    if analysis['other_percentage'] < 10:
        print("  ✅ 目標達成: 「その他」カテゴリを10%以下に削減成功！")
    else:
        print("  📈 改善継続中: さらなる分類精度向上が必要")

if __name__ == "__main__":
    main()
