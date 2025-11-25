#!/usr/bin/env python3
"""
感銘を与える有名人物収集システム
現代の10代〜50代が共感し、「自分も頑張ろう」と思える人物を選出
エンターテインメント、文化・芸術、政治・社会を強化
"""

import concurrent.futures
import hashlib
import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import requests


@dataclass
class InspirationalPerson:
    """感銘を与える人物データ構造"""
    name: str
    birth_date: str
    nationality: str
    occupation: str
    main_category: str
    subcategory: str
    wikidata_id: str = ""
    description: str = ""
    inspirational_points: List[str] = None  # なぜ感銘を与えるか
    target_age_group: List[str] = None  # どの世代に響くか

    def to_dict(self) -> Dict:
        data = asdict(self)
        if self.inspirational_points is None:
            data['inspirational_points'] = []
        if self.target_age_group is None:
            data['target_age_group'] = []
        return data

class InspirationalPersonCollector:
    """感銘を与える人物を収集するシステム"""

    def __init__(self):
        self.wikidata_endpoint = "https://query.wikidata.org/sparql"
        self.stats = {
            'total_collected': 0,
            'by_category': {},
            'by_age_group': {
                '10代向け': 0,
                '20代向け': 0,
                '30代向け': 0,
                '40代向け': 0,
                '50代向け': 0
            }
        }

    def collect_balanced_inspirational_people(self) -> List[InspirationalPerson]:
        """バランスの取れた感銘を与える人物を収集"""
        print("🌟 感銘を与える有名人物収集システム")
        print("📊 エンターテインメント・文化・社会を重点強化")
        print("=" * 60)

        # バランスを改善したカテゴリ計画（合計12,410人想定）
        category_plan = [
            # ===== エンターテインメント（3,000人に増強）=====
            # 日本のエンターテイナー
            ("お笑い芸人", "wd:Q245068", "エンターテインメント", 300,
             ["努力", "挫折からの復活", "独自のスタイル確立"], ["20代", "30代", "40代"]),

            ("アイドル", "wd:Q4220920", "エンターテインメント", 250,
             ["夢の実現", "努力の継続", "ファンとの絆"], ["10代", "20代", "30代"]),

            ("俳優", "wd:Q33999", "エンターテインメント", 400,
             ["演技への情熱", "役作りの努力", "長期的キャリア"], ["20代", "30代", "40代"]),

            ("声優", "wd:Q622807", "エンターテインメント", 200,
             ["声の演技", "アニメ文化への貢献", "多才な活動"], ["10代", "20代", "30代"]),

            ("歌手", "wd:Q177220", "エンターテインメント", 400,
             ["音楽への情熱", "メッセージ性", "時代を超える楽曲"], ["全世代"]),

            ("ミュージシャン", "wd:Q639669", "エンターテインメント", 300,
             ["独自の音楽性", "楽器の技術", "バンド活動"], ["20代", "30代", "40代"]),

            # 現代のエンターテイナー
            ("YouTuber", "wd:Q17125263", "エンターテインメント", 400,
             ["新しいメディア開拓", "独立独歩", "若くして成功"], ["10代", "20代"]),

            ("TikToker", "wd:Q94791573", "エンターテインメント", 250,
             ["Z世代の代表", "創造性", "短期間での成功"], ["10代", "20代"]),

            ("VTuber", "wd:Q87135691", "エンターテインメント", 100,
             ["新しい表現形態", "デジタルネイティブ", "グローバル展開"], ["10代", "20代"]),

            ("eスポーツ選手", "wd:Q4379701", "エンターテインメント", 200,
             ["新しい職業", "世界での活躍", "ゲームのプロ化"], ["10代", "20代"]),

            ("インフルエンサー", "wd:Q54888449", "エンターテインメント", 200,
             ["SNS活用", "個人ブランド", "影響力"], ["10代", "20代", "30代"]),

            # ===== 文化・芸術（3,000人に増強）=====
            ("漫画家", "wd:Q3658341", "文化・芸術", 400,
             ["作品の創造", "長期連載", "世界への影響"], ["全世代"]),

            ("アニメ監督", "wd:Q3665646", "文化・芸術", 200,
             ["映像表現", "作品へのこだわり", "日本文化の発信"], ["20代", "30代", "40代"]),

            ("ゲームクリエイター", "wd:Q4618975", "文化・芸術", 250,
             ["インタラクティブ芸術", "技術と芸術の融合", "世界的成功"], ["20代", "30代"]),

            ("イラストレーター", "wd:Q644687", "文化・芸術", 200,
             ["視覚表現", "SNSでの活躍", "商業との両立"], ["10代", "20代", "30代"]),

            ("小説家", "wd:Q6625963", "文化・芸術", 300,
             ["物語の創造", "想像力", "長期的な執筆活動"], ["30代", "40代", "50代"]),

            ("映画監督", "wd:Q2526255", "文化・芸術", 300,
             ["映像作品", "独自の世界観", "国際的評価"], ["30代", "40代", "50代"]),

            ("写真家", "wd:Q33231", "文化・芸術", 250,
             ["瞬間の芸術", "世界の記録", "表現力"], ["30代", "40代"]),

            ("デザイナー", "wd:Q2962070", "文化・芸術", 300,
             ["創造性", "問題解決", "美と機能"], ["20代", "30代", "40代"]),

            ("建築家", "wd:Q42973", "文化・芸術", 200,
             ["空間創造", "社会貢献", "芸術と技術"], ["30代", "40代", "50代"]),

            ("ダンサー", "wd:Q5716684", "文化・芸術", 200,
             ["身体表現", "努力と鍛錬", "舞台での輝き"], ["10代", "20代", "30代"]),

            ("書道家", "wd:Q3997704", "文化・芸術", 100,
             ["伝統文化", "精神性", "技術の継承"], ["40代", "50代"]),

            ("陶芸家", "wd:Q7605362", "文化・芸術", 100,
             ["伝統工芸", "創造性", "職人精神"], ["40代", "50代"]),

            # ===== 政治・社会（2,500人に増強）=====
            ("社会起業家", "wd:Q3242115", "政治・社会", 400,
             ["社会問題解決", "ビジネスと社会貢献", "イノベーション"], ["20代", "30代", "40代"]),

            ("環境活動家", "wd:Q15253558", "政治・社会", 300,
             ["地球環境保護", "未来への責任", "行動力"], ["10代", "20代", "30代"]),

            ("NPO創設者", "wd:Q163740", "政治・社会", 250,
             ["非営利活動", "社会貢献", "ボランティア精神"], ["30代", "40代", "50代"]),

            ("若手政治家", "wd:Q82955", "政治・社会", 200,
             ["政治改革", "若い世代の代表", "変革への挑戦"], ["20代", "30代", "40代"]),

            ("人権活動家", "wd:Q1476215", "政治・社会", 250,
             ["平等への戦い", "正義の追求", "勇気ある行動"], ["全世代"]),

            ("ジャーナリスト", "wd:Q1930187", "政治・社会", 300,
             ["真実の追求", "社会への警鐘", "情報発信"], ["30代", "40代", "50代"]),

            ("教育者", "wd:Q37226", "政治・社会", 300,
             ["次世代育成", "知識の伝達", "人材育成"], ["30代", "40代", "50代"]),

            ("医療従事者", "wd:Q39631", "政治・社会", 200,
             ["命を救う", "献身的な活動", "専門性"], ["全世代"]),

            ("平和活動家", "wd:Q15895020", "政治・社会", 150,
             ["戦争反対", "対話の促進", "国際協力"], ["40代", "50代"]),

            ("フェミニスト", "wd:Q17706731", "政治・社会", 150,
             ["男女平等", "社会変革", "意識改革"], ["20代", "30代", "40代"]),

            # ===== スポーツ（2,000人）=====
            ("サッカー選手", "wd:Q937857", "スポーツ", 400,
             ["チームワーク", "国際的活躍", "努力の結晶"], ["10代", "20代", "30代"]),

            ("野球選手", "wd:Q10871364", "スポーツ", 400,
             ["継続的努力", "チーム貢献", "記録への挑戦"], ["全世代"]),

            ("テニス選手", "wd:Q10833314", "スポーツ", 200,
             ["個人競技", "メンタル強化", "世界ランキング"], ["20代", "30代"]),

            ("陸上選手", "wd:Q11513337", "スポーツ", 200,
             ["自己記録更新", "肉体の限界挑戦", "オリンピック"], ["10代", "20代"]),

            ("水泳選手", "wd:Q10843402", "スポーツ", 150,
             ["記録への挑戦", "継続的トレーニング", "水との対話"], ["10代", "20代"]),

            ("体操選手", "wd:Q13381863", "スポーツ", 150,
             ["身体能力", "美しさと力強さ", "技の追求"], ["10代", "20代"]),

            ("フィギュアスケート選手", "wd:Q13219587", "スポーツ", 150,
             ["芸術性", "技術と表現", "プレッシャーとの戦い"], ["10代", "20代", "30代"]),

            ("格闘家", "wd:Q11338576", "スポーツ", 200,
             ["精神力", "肉体鍛錬", "勝負への執念"], ["20代", "30代"]),

            ("パラリンピック選手", "wd:Q4330518", "スポーツ", 150,
             ["障害を乗り越える", "不屈の精神", "希望を与える"], ["全世代"]),

            # ===== ビジネス・テクノロジー（1,910人）=====
            ("起業家", "wd:Q131524", "ビジネス", 500,
             ["ゼロからの創業", "リスクテイク", "イノベーション"], ["20代", "30代", "40代"]),

            ("プログラマー", "wd:Q5482740", "テクノロジー", 300,
             ["コード創造", "問題解決", "技術革新"], ["20代", "30代"]),

            ("AI研究者", "wd:Q1650915", "テクノロジー", 200,
             ["未来技術", "研究開発", "社会変革"], ["20代", "30代", "40代"]),

            ("投資家", "wd:Q557880", "ビジネス", 200,
             ["資産形成", "企業支援", "経済への貢献"], ["30代", "40代", "50代"]),

            ("女性起業家", "wd:Q131524", "ビジネス", 200,
             ["ガラスの天井を破る", "女性の活躍", "ロールモデル"], ["20代", "30代", "40代"]),

            ("ベンチャーキャピタリスト", "wd:Q2917655", "ビジネス", 150,
             ["スタートアップ支援", "未来への投資", "起業家育成"], ["30代", "40代"]),

            ("データサイエンティスト", "wd:Q2374463", "テクノロジー", 150,
             ["データ分析", "意思決定支援", "新しい職業"], ["20代", "30代"]),

            ("UXデザイナー", "wd:Q2165278", "テクノロジー", 110,
             ["ユーザー体験", "デザイン思考", "問題解決"], ["20代", "30代"]),

            ("マーケター", "wd:Q15994440", "ビジネス", 100,
             ["市場開拓", "ブランド構築", "消費者理解"], ["20代", "30代", "40代"])
        ]

        all_people = []

        # 並列処理で収集
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = []

            for (occupation, wikidata_id, category, limit,
                 inspirational_points, target_ages) in category_plan:

                future = executor.submit(
                    self._collect_inspirational_category,
                    occupation, wikidata_id, category, limit,
                    inspirational_points, target_ages
                )
                futures.append(future)

            # 結果を収集
            for future in concurrent.futures.as_completed(futures):
                try:
                    people = future.result()
                    all_people.extend(people)
                    self._update_stats(people)
                    self._print_progress()
                except Exception as e:
                    print(f"  ⚠️ エラー: {e}")

        return all_people

    def _collect_inspirational_category(
        self, occupation: str, wikidata_id: str, category: str,
        limit: int, inspirational_points: List[str], target_ages: List[str]
    ) -> List[InspirationalPerson]:
        """感銘を与える人物をカテゴリごとに収集"""

        print(f"🔍 {occupation}を収集中... (目標: {limit}人)")

        # より詳細な情報を取得するクエリ
        query = f"""
        SELECT DISTINCT ?person ?personLabel ?birthDate
               ?nationalityLabel ?description ?image
        WHERE {{
          ?person wdt:P31 wd:Q5 ;
                  wdt:P106 {wikidata_id} ;
                  wdt:P569 ?birthDate .
          OPTIONAL {{ ?person wdt:P27 ?nationality }}
          OPTIONAL {{ ?person wdt:P18 ?image }}
          OPTIONAL {{ ?person schema:description ?description
                     FILTER(LANG(?description) = "ja") }}

          # 1970年以降生まれを優先（現代の人物）
          FILTER(YEAR(?birthDate) > 1970)

          SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "ja,en".
          }}
        }}
        LIMIT {limit * 2}
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

                for item in data['results']['bindings'][:limit]:
                    person = InspirationalPerson(
                        name=item['personLabel']['value'],
                        birth_date=item.get('birthDate', {}).get('value', '')[:10],
                        nationality=item.get('nationalityLabel', {}).get('value', ''),
                        occupation=occupation,
                        main_category=category,
                        subcategory=occupation,
                        wikidata_id=item['person']['value'].split('/')[-1],
                        description=item.get('description', {}).get('value', ''),
                        inspirational_points=inspirational_points,
                        target_age_group=target_ages
                    )

                    if self._validate_inspirational_person(person):
                        people.append(person)

                print(f"  ✅ {occupation}: {len(people)}人収集")
                return people

        except Exception as e:
            print(f"  ⚠️ {occupation}エラー: {str(e)[:50]}")

        return []

    def _validate_inspirational_person(self, person: InspirationalPerson) -> bool:
        """感銘を与える人物として適切か検証"""
        # 基本的な名前検証
        if not person.name or len(person.name) < 2:
            return False
        if person.name.isdigit():
            return False

        # 生年検証（現代の人物を優先）
        if person.birth_date:
            try:
                year = int(person.birth_date[:4])
                # 1900年以降生まれ（現代の人物）
                if year < 1900 or year > 2024:
                    return False
            except:
                return False

        return True

    def _update_stats(self, people: List[InspirationalPerson]):
        """統計を更新"""
        for person in people:
            self.stats['total_collected'] += 1

            # カテゴリ別統計
            cat = person.main_category
            self.stats['by_category'][cat] = self.stats['by_category'].get(cat, 0) + 1

            # 世代別統計
            if person.target_age_group:
                for age_group in person.target_age_group:
                    if age_group == "全世代":
                        for key in self.stats['by_age_group']:
                            self.stats['by_age_group'][key] += 0.2  # 全世代は各世代に0.2カウント
                    elif age_group in ["10代", "20代", "30代", "40代", "50代"]:
                        key = f"{age_group}向け"
                        self.stats['by_age_group'][key] += 1

    def _print_progress(self):
        """進捗を表示"""
        total = self.stats['total_collected']
        if total % 100 == 0:  # 100人ごとに表示
            print(f"  📊 現在の収集数: {total}人")

    def generate_inspirational_report(self, people: List[InspirationalPerson]) -> str:
        """感銘レポートを生成"""
        report = []
        report.append("=" * 60)
        report.append("🌟 感銘を与える有名人物 収集レポート")
        report.append("=" * 60)

        report.append(f"\n✅ 総収集数: {len(people)}人")

        # カテゴリバランス
        report.append("\n📊 カテゴリバランス（改善版）:")
        total = len(people)
        for cat, count in sorted(self.stats['by_category'].items(),
                                key=lambda x: x[1], reverse=True):
            pct = count / total * 100 if total > 0 else 0
            bar = '█' * int(pct/2)
            report.append(f"  {cat:20} {count:5}人 ({pct:5.1f}%) {bar}")

        # 世代別カバレッジ
        report.append("\n🎯 世代別カバレッジ:")
        for age_group, count in self.stats['by_age_group'].items():
            report.append(f"  {age_group}: {int(count)}人")

        # 感銘ポイントの例
        report.append("\n💡 なぜ感銘を与えるか（例）:")
        sample_points = set()
        for person in people[:50]:  # 最初の50人から
            if person.inspirational_points:
                for point in person.inspirational_points[:2]:
                    sample_points.add(point)

        for i, point in enumerate(list(sample_points)[:10], 1):
            report.append(f"  {i}. {point}")

        report.append("\n" + "=" * 60)

        return "\n".join(report)

    def export_to_csv(self, people: List[InspirationalPerson], filename: str):
        """CSVエクスポート（感銘ポイント付き）"""
        data = []
        for person in people:
            row = person.to_dict()
            # リストを文字列に変換
            row['inspirational_points'] = '、'.join(row.get('inspirational_points', []))
            row['target_age_group'] = '、'.join(row.get('target_age_group', []))
            data.append(row)

        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        print(f"\n📄 CSVエクスポート完了: {filename}")

def main():
    """メイン処理"""
    print("=" * 60)
    print("🌟 感銘を与える有名人物収集システム")
    print("🎯 10代〜50代が「自分も頑張ろう」と思える人物を選出")
    print("=" * 60)

    collector = InspirationalPersonCollector()

    # デモ版: 500人収集
    people = collector.collect_balanced_inspirational_people()

    # レポート生成
    report = collector.generate_inspirational_report(people[:500])  # デモは500人
    print(report)

    # エクスポート
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_filename = f"inspirational_people_{timestamp}.csv"
    collector.export_to_csv(people[:500], csv_filename)

    print("\n" + "=" * 60)
    print("✅ 感銘を与える人物の収集完了！")
    print(f"  収集人数: {min(len(people), 500)}人")
    print("  バランス: エンタメ・文化・社会を強化")
    print("  世代カバー: 10代〜50代すべてに対応")
    print("=" * 60)

if __name__ == "__main__":
    main()
