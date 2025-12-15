#!/usr/bin/env python3
"""
次週分のエピソード候補リスト生成システム
優先カテゴリーに基づいた人物選定
"""

import csv
import json
from datetime import datetime
from typing import Dict, List, Tuple
from collections import Counter

class NextWeekCandidates:
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.master_file = "master/episodes_master_current.csv"

        # 優先カテゴリーと目標件数
        self.priority_categories = {
            "テクノロジー": 2,
            "建築・デザイン": 2,
            "文化・芸術": 2,
            "医学・健康": 2,  # 新規カテゴリー
            "宇宙・探検": 1,  # 新規カテゴリー
            "社会起業": 1      # 新規カテゴリー
        }

    def load_existing_persons(self) -> set:
        """既存の人物名を読み込み"""
        existing = set()
        try:
            with open(self.master_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    existing.add(row['person_name'])
        except FileNotFoundError:
            print("⚠️ マスターファイルが見つかりません")

        return existing

    def generate_candidates(self) -> List[Dict]:
        """次週の候補者リストを生成"""
        existing = self.load_existing_persons()
        candidates = []

        # カテゴリー別候補者
        candidate_pool = {
            "テクノロジー": [
                {"name": "イーロン・マスク", "age": 41, "achievement": "SpaceXでFalcon 9の再利用可能ロケット開発に成功"},
                {"name": "ビル・ゲイツ", "age": 40, "achievement": "Windows 95をリリースし、PCを一般家庭に普及"},
                {"name": "マーク・ザッカーバーグ", "age": 28, "achievement": "Facebook IPOで時価総額10兆円企業へ"},
                {"name": "ジェフ・ベゾス", "age": 35, "achievement": "Amazon Prime開始で小売業界に革命"},
            ],
            "建築・デザイン": [
                {"name": "隈研吾", "age": 45, "achievement": "新国立競技場の設計者に選定"},
                {"name": "伊東豊雄", "age": 71, "achievement": "プリツカー賞受賞で日本建築の評価を世界に"},
                {"name": "イサム・ノグチ", "age": 46, "achievement": "札幌モエレ沼公園の設計開始"},
                {"name": "フランク・ゲーリー", "age": 68, "achievement": "グッゲンハイム美術館ビルバオで建築の概念を変革"},
            ],
            "文化・芸術": [
                {"name": "奈良美智", "age": 40, "achievement": "ニューヨークMoMAで日本人最年少個展"},
                {"name": "杉本博司", "age": 42, "achievement": "写真作品が100万ドルで取引される日本人初の写真家"},
                {"name": "蜷川幸雄", "age": 40, "achievement": "ロンドンで日本演劇初の大規模公演を成功"},
                {"name": "千住明", "age": 30, "achievement": "映画音楽で日本アカデミー賞最優秀音楽賞"},
            ],
            "医学・健康": [
                {"name": "本庶佑", "age": 76, "achievement": "PD-1発見でノーベル生理学・医学賞受賞"},
                {"name": "大隅良典", "age": 71, "achievement": "オートファジー研究でノーベル賞単独受賞"},
                {"name": "満屋裕明", "age": 35, "achievement": "世界初のエイズ治療薬AZTを開発"},
                {"name": "遠藤章", "age": 46, "achievement": "スタチン発見で心臓病死亡率を半減"},
            ],
            "宇宙・探検": [
                {"name": "毛利衛", "age": 44, "achievement": "日本人初のスペースシャトル搭乗で宇宙実験"},
                {"name": "向井千秋", "age": 42, "achievement": "日本人女性初の宇宙飛行士としてミッション成功"},
                {"name": "野口聡一", "age": 40, "achievement": "ISS長期滞在で船外活動3回成功"},
                {"name": "若田光一", "age": 50, "achievement": "日本人初のISS船長就任"},
            ],
            "社会起業": [
                {"name": "ムハマド・ユヌス", "age": 43, "achievement": "グラミン銀行でマイクロファイナンス革命"},
                {"name": "ワンガリ・マータイ", "age": 37, "achievement": "グリーンベルト運動で3000万本植樹"},
                {"name": "山口絵理子", "age": 25, "achievement": "マザーハウスでバングラデシュ製品を世界展開"},
                {"name": "駒崎弘樹", "age": 25, "achievement": "フローレンスで病児保育問題を解決"},
            ]
        }

        # 優先カテゴリーから候補選定
        for category, count in self.priority_categories.items():
            if category in candidate_pool:
                pool = candidate_pool[category]
                selected = 0

                for candidate in pool:
                    if candidate["name"] not in existing and selected < count:
                        candidates.append({
                            "person_name": candidate["name"],
                            "episode_age": candidate["age"],
                            "category": category,
                            "key_achievement": candidate["achievement"],
                            "priority": "高",
                            "reason": f"{category}カテゴリーの強化"
                        })
                        selected += 1

        return candidates[:10]  # 週10件に制限

    def create_episode_templates(self, candidates: List[Dict]) -> List[Dict]:
        """エピソードテンプレートを作成"""
        templates = []

        episode_texts = {
            "イーロン・マスク": "あなたと同じ41歳のとき、イーロン・マスクはSpaceXでFalcon 9ロケットの垂直着陸に成功し、宇宙開発の歴史を変えた。打ち上げコストを100分の1に削減し、年間18回の打ち上げを実現。テスラも同時期に黒字化を達成し、時価総額1000億ドルを突破。火星移住という人類の夢を現実的な目標に変えた革新者。",

            "ビル・ゲイツ": "あなたと同じ40歳のとき、ビル・ゲイツはWindows 95を世界同時発売し、4日間で100万本を売り上げる記録を樹立した。インターネットエクスプローラーを標準搭載し、世界のPC普及率を5%から50%へ押し上げた。個人資産も400億ドルに到達し、後の慈善活動で世界の医療と教育を変革する基盤を築いた。",

            "隈研吾": "あなたと同じ45歳のとき、隈研吾は「負ける建築」の思想を提唱し、新国立競技場の設計者に選ばれた。木材を多用した「生きる建築」で世界30カ国200以上のプロジェクトを手がけ、建築界のノーベル賞とされるAIAゴールドメダルを日本人として初受賞。自然と調和する日本建築の新しい可能性を世界に示した。",

            "本庶佑": "あなたと同じ76歳のとき、本庶佑はPD-1分子の発見によりノーベル生理学・医学賞を受賞した。がん免疫療法という新しい治療法を確立し、従来は数ヶ月だった末期がん患者の5年生存率を20%以上に改善。オプジーボの開発により年間100万人のがん患者に希望を与え、医学の歴史に革命をもたらした。",

            "毛利衛": "あなたと同じ44歳のとき、毛利衛は日本人初のスペースシャトル搭乗員としてエンデバー号で宇宙へ飛び立った。8日間で43の実験を完遂し、特に無重力下でのたんぱく質結晶生成に成功。「宇宙からは国境線は見えなかった」の名言を残し、日本の宇宙開発を先導。後に日本科学未来館館長として次世代育成に貢献。",
        }

        for candidate in candidates:
            name = candidate["person_name"]
            if name in episode_texts:
                text = episode_texts[name]
            else:
                # デフォルトテンプレート
                text = f"あなたと同じ{candidate['episode_age']}歳のとき、{name}は{candidate['key_achievement']}。[詳細な数値と影響を追加予定]"

            templates.append({
                **candidate,
                "episode_text_template": text,
                "character_count": len(text),
                "status": "テンプレート準備完了" if len(text) >= 140 else "要編集"
            })

        return templates

    def save_candidates_file(self, candidates: List[Dict]) -> None:
        """候補者リストをファイルに保存"""
        output_file = f"next_week_candidates_{self.timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump({
                "generation_date": datetime.now().isoformat(),
                "total_candidates": len(candidates),
                "priority_categories": self.priority_categories,
                "candidates": candidates
            }, f, ensure_ascii=False, indent=2)

        print(f"📁 候補者リスト保存: {output_file}")

    def save_csv_template(self, templates: List[Dict]) -> None:
        """CSVテンプレートを生成"""
        output_file = f"next_week_template_{self.timestamp}.csv"

        fieldnames = [
            'person_name', 'episode_age', 'category', 'priority',
            'key_achievement', 'character_count', 'status', 'episode_text_template'
        ]

        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for template in templates:
                writer.writerow({
                    'person_name': template['person_name'],
                    'episode_age': template['episode_age'],
                    'category': template['category'],
                    'priority': template['priority'],
                    'key_achievement': template['key_achievement'],
                    'character_count': template['character_count'],
                    'status': template['status'],
                    'episode_text_template': template.get('episode_text_template', '')
                })

        print(f"📁 CSVテンプレート保存: {output_file}")

    def show_summary(self, candidates: List[Dict]) -> None:
        """サマリーを表示"""
        print("\n" + "="*60)
        print("📋 次週エピソード候補リスト")
        print("="*60)

        print(f"\n📊 候補者数: {len(candidates)}名")

        # カテゴリー別集計
        categories = Counter(c['category'] for c in candidates)
        print("\n📂 カテゴリー内訳:")
        for category, count in categories.most_common():
            print(f"   - {category}: {count}名")

        print("\n👥 候補者一覧:")
        for i, candidate in enumerate(candidates, 1):
            status = "✅" if candidate.get('character_count', 0) >= 140 else "📝"
            print(f"   {i:2d}. {status} {candidate['person_name']} ({candidate['category']}) "
                  f"- {candidate['episode_age']}歳")
            print(f"       └─ {candidate['key_achievement']}")

        # 準備状況
        ready = sum(1 for c in candidates if c.get('status') == 'テンプレート準備完了')
        print(f"\n✅ 準備完了: {ready}/{len(candidates)}件")
        print(f"📝 要編集: {len(candidates) - ready}件")

    def run(self) -> None:
        """候補者リスト生成を実行"""
        print("🚀 次週エピソード候補者選定システム")
        print("="*60)

        # 候補者生成
        candidates = self.generate_candidates()

        # テンプレート作成
        templates = self.create_episode_templates(candidates)

        # ファイル保存
        self.save_candidates_file(templates)
        self.save_csv_template(templates)

        # サマリー表示
        self.show_summary(templates)

        print("\n✨ 候補者リスト生成完了！")
        print("📌 次のステップ:")
        print("   1. CSVテンプレートを確認")
        print("   2. 必要に応じてエピソード文を編集")
        print("   3. weekly_episode_generator_fixed.py に組み込み")

def main():
    generator = NextWeekCandidates()
    generator.run()

if __name__ == "__main__":
    main()
