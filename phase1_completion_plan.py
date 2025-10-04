#!/usr/bin/env python3
"""
Phase 1完了計画 - 残り35件の戦略的生成
カテゴリーバランスを最適化しながら100件到達を目指す
"""

import csv
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import Counter

class Phase1CompletionPlan:
    def __init__(self):
        self.current_count = 65
        self.target_count = 100
        self.remaining = 35
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 理想的なカテゴリー分布（100件時点）
        self.ideal_distribution = {
            "スポーツ": 15,      # 15%（現在29.2%→削減）
            "ビジネス": 12,      # 12%（現在12.3%→維持）
            "音楽": 10,          # 10%（現在10.8%→維持）
            "科学・研究": 10,    # 10%（現在6.2%→増強）
            "テクノロジー": 8,   # 8%（現在1.5%→大幅増強）
            "文化・芸術": 8,     # 8%（現在1.5%→大幅増強）
            "エンターテインメント": 6,  # 6%
            "映画": 5,           # 5%
            "医学・健康": 5,     # 5%（新規）
            "政治・社会": 5,     # 5%
            "建築・デザイン": 4, # 4%（増強）
            "文学": 3,           # 3%
            "宇宙・探検": 3,     # 3%（新規）
            "教育": 3,           # 3%
            "その他": 3          # 3%
        }

    def analyze_current_state(self) -> Dict:
        """現在の状態を分析"""
        # 実際のデータから現在の分布を取得（簡略化のため固定値使用）
        current_distribution = {
            "スポーツ": 19,
            "ビジネス": 8,
            "音楽": 7,
            "エンターテインメント": 4,
            "映画": 4,
            "科学": 4,
            "漫画": 2,
            "教育": 2,
            "政治": 2,
            "将棋": 2,
            "アニメーション": 2,
            "文学": 2,
            "政治・社会": 2,
            "テクノロジー": 1,
            "伝統芸能": 1,
            "芸術": 1,
            "建築": 1,
            "文化・芸術": 1
        }

        return current_distribution

    def calculate_needed_additions(self) -> Dict[str, int]:
        """必要な追加数を計算"""
        current = self.analyze_current_state()
        needed = {}

        # 理想分布に対して不足しているカテゴリーを特定
        priority_categories = {
            "テクノロジー": 7,      # 1→8件（+7）
            "科学・研究": 6,        # 4→10件（+6）
            "文化・芸術": 6,        # 2→8件（+6）
            "医学・健康": 5,        # 0→5件（+5）
            "建築・デザイン": 3,    # 1→4件（+3）
            "宇宙・探検": 3,        # 0→3件（+3）
            "政治・社会": 2,        # 3→5件（+2）
            "ビジネス": 2,          # 8→10件（+2）
            "教育": 1               # 2→3件（+1）
        }

        total_needed = sum(priority_categories.values())

        # 35件の枠に収まるよう調整
        if total_needed == 35:
            return priority_categories
        elif total_needed > 35:
            # 比率を保ちながら35件に調整
            factor = 35 / total_needed
            adjusted = {}
            allocated = 0
            for cat, count in priority_categories.items():
                adjusted_count = int(count * factor)
                if adjusted_count > 0:
                    adjusted[cat] = adjusted_count
                    allocated += adjusted_count

            # 端数を優先度の高いカテゴリーに割り当て
            remaining = 35 - allocated
            for cat in ["テクノロジー", "科学・研究", "文化・芸術"]:
                if remaining > 0 and cat in adjusted:
                    adjusted[cat] += 1
                    remaining -= 1

            return adjusted

        return priority_categories

    def generate_35_candidates(self) -> List[Dict]:
        """35名の候補者リストを生成"""
        needed = self.calculate_needed_additions()
        candidates = []

        # カテゴリー別候補者プール
        candidate_pools = {
            "テクノロジー": [
                ("イーロン・マスク", 41, "SpaceX Falcon 9再利用可能ロケット成功"),
                ("ビル・ゲイツ", 40, "Windows 95で世界のPC革命"),
                ("マーク・ザッカーバーグ", 28, "Facebook時価総額10兆円達成"),
                ("ジェフ・ベゾス", 35, "Amazon Prime開始"),
                ("ラリー・ペイジ", 30, "Google検索エンジン革命"),
                ("サティア・ナデラ", 47, "Microsoft CEO就任、クラウド転換"),
                ("ジャック・ドーシー", 29, "Twitter創業、リアルタイム情報革命")
            ],
            "科学・研究": [
                ("本庶佑", 76, "PD-1発見でノーベル賞"),
                ("大隅良典", 71, "オートファジー研究でノーベル賞"),
                ("天野浩", 54, "青色LED開発でノーベル賞"),
                ("梶田隆章", 56, "ニュートリノ振動発見でノーベル賞"),
                ("吉野彰", 71, "リチウムイオン電池開発でノーベル賞"),
                ("中村修二", 41, "青色LED実用化")
            ],
            "文化・芸術": [
                ("奈良美智", 40, "NY MoMA日本人最年少個展"),
                ("杉本博司", 42, "写真作品100万ドル取引"),
                ("横尾忠則", 50, "NY MoMA永久収蔵決定"),
                ("宮島達男", 35, "ヴェネツィアビエンナーレ出展"),
                ("森村泰昌", 40, "セルフポートレート芸術確立"),
                ("会田誠", 35, "現代美術界に衝撃")
            ],
            "医学・健康": [
                ("山中伸弥", 50, "iPS細胞でノーベル賞"),
                ("満屋裕明", 35, "世界初エイズ治療薬開発"),
                ("遠藤章", 46, "スタチン発見"),
                ("北里柴三郎", 40, "破傷風血清療法確立"),
                ("野口英世", 33, "黄熱病研究")
            ],
            "建築・デザイン": [
                ("隈研吾", 45, "新国立競技場設計者"),
                ("伊東豊雄", 71, "プリツカー賞受賞"),
                ("妹島和世", 54, "プリツカー賞最年少受賞")
            ],
            "宇宙・探検": [
                ("毛利衛", 44, "日本人初スペースシャトル搭乗"),
                ("若田光一", 50, "日本人初ISS船長"),
                ("野口聡一", 40, "ISS長期滞在成功")
            ],
            "政治・社会": [
                ("緒方貞子", 63, "国連難民高等弁務官就任"),
                ("明石康", 61, "カンボジア和平実現")
            ],
            "ビジネス": [
                ("柳井正", 35, "ユニクロ世界展開開始"),
                ("三木谷浩史", 32, "楽天市場創業")
            ],
            "教育": [
                ("佐藤学", 45, "学びの共同体理論確立")
            ]
        }

        # 必要数に応じて候補者を選定
        for category, count_needed in needed.items():
            if category in candidate_pools:
                pool = candidate_pools[category]
                for i, (name, age, achievement) in enumerate(pool[:count_needed]):
                    candidates.append({
                        "person_name": name,
                        "episode_age": age,
                        "category": category,
                        "achievement": achievement,
                        "batch": (i // 10) + 1  # 10件ずつのバッチに分割
                    })

        return candidates[:35]  # 35件に制限

    def create_batch_schedule(self, candidates: List[Dict]) -> Dict:
        """バッチスケジュールを作成"""
        schedule = {
            "batch_1": {
                "date": "2025-09-30（第1週）",
                "count": 10,
                "candidates": []
            },
            "batch_2": {
                "date": "2025-10-07（第2週）",
                "count": 10,
                "candidates": []
            },
            "batch_3": {
                "date": "2025-10-14（第3週）",
                "count": 10,
                "candidates": []
            },
            "batch_4": {
                "date": "2025-10-21（第4週）",
                "count": 5,
                "candidates": []
            }
        }

        # カテゴリーバランスを考慮してバッチに配分
        batch_sizes = [10, 10, 10, 5]
        current_batch = 1
        batch_count = 0

        for candidate in candidates:
            if batch_count >= batch_sizes[current_batch - 1]:
                current_batch += 1
                batch_count = 0

            schedule[f"batch_{current_batch}"]["candidates"].append(candidate)
            batch_count += 1

        return schedule

    def generate_completion_report(self, candidates: List[Dict], schedule: Dict) -> None:
        """完了計画レポートを生成"""
        report_file = f"phase1_completion_report_{self.timestamp}.md"

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("# Phase 1完了計画レポート\n\n")
            f.write(f"**生成日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M')}\n\n")

            # 概要
            f.write("## 📊 概要\n\n")
            f.write(f"- **現在のエピソード数**: {self.current_count}件\n")
            f.write(f"- **目標**: {self.target_count}件\n")
            f.write(f"- **必要追加数**: {self.remaining}件\n")
            f.write(f"- **推定完了日**: 2025年10月21日（4週間）\n\n")

            # カテゴリー最適化計画
            f.write("## 🎯 カテゴリー最適化計画\n\n")
            f.write("| カテゴリー | 現在 | 目標 | 追加必要数 |\n")
            f.write("|-----------|------|------|------------|\n")

            needed = self.calculate_needed_additions()
            for category, count in sorted(needed.items(), key=lambda x: x[1], reverse=True):
                current = self.analyze_current_state().get(category, 0)
                target = current + count
                f.write(f"| {category} | {current} | {target} | +{count} |\n")

            # バッチスケジュール
            f.write("\n## 📅 週次バッチスケジュール\n\n")
            for batch_name, batch_info in schedule.items():
                f.write(f"### {batch_info['date']} - {batch_info['count']}件\n\n")

                # カテゴリー別集計
                categories = Counter(c['category'] for c in batch_info['candidates'])
                for category, count in categories.most_common():
                    f.write(f"- {category}: {count}件\n")
                    # 具体的な人物名
                    persons = [c['person_name'] for c in batch_info['candidates']
                             if c['category'] == category]
                    for person in persons[:3]:  # 最初の3名のみ表示
                        f.write(f"  - {person}\n")
                    if len(persons) > 3:
                        f.write(f"  - 他{len(persons)-3}名\n")
                f.write("\n")

            # 品質基準
            f.write("## ✅ 品質保証基準\n\n")
            f.write("すべてのエピソードは以下の基準を満たします：\n\n")
            f.write("1. **文字数**: 140-200文字（推奨150-180文字）\n")
            f.write("2. **必須要素**:\n")
            f.write("   - 「あなたと同じ○○歳のとき」で開始\n")
            f.write("   - 具体的な数値を3つ以上含む\n")
            f.write("   - 事実に基づいた正確な情報\n")
            f.write("3. **スコア基準**:\n")
            f.write("   - weighted_score ≥ 7.0\n")
            f.write("   - fact_check_status = verified\n\n")

            # 実行手順
            f.write("## 🚀 実行手順\n\n")
            f.write("```bash\n")
            f.write("# 毎週月曜日の実行\n")
            f.write("python3 weekly_episode_generator_fixed.py\n")
            f.write("python3 auto_merge_system.py\n")
            f.write("\n# または自動スケジューラーを使用\n")
            f.write("python3 episode_scheduler.py\n")
            f.write("```\n\n")

            # 期待される成果
            f.write("## 🎊 期待される成果\n\n")
            f.write("- **Phase 1完了**: 100件のエピソード\n")
            f.write("- **カテゴリーバランス**: 最適化された分布\n")
            f.write("- **品質**: 100%有効率維持\n")
            f.write("- **基盤確立**: Phase 2への準備完了\n")

        print(f"📄 レポート生成: {report_file}")

    def save_candidate_data(self, candidates: List[Dict]) -> None:
        """候補者データを保存"""
        # JSON形式で保存
        json_file = f"phase1_candidates_{self.timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump({
                "generation_date": datetime.now().isoformat(),
                "total_candidates": len(candidates),
                "candidates": candidates
            }, f, ensure_ascii=False, indent=2)

        # CSV形式でも保存
        csv_file = f"phase1_candidates_{self.timestamp}.csv"
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            if candidates:
                fieldnames = candidates[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(candidates)

        print(f"📁 候補者データ保存:")
        print(f"   - JSON: {json_file}")
        print(f"   - CSV: {csv_file}")

    def show_summary(self, candidates: List[Dict], schedule: Dict) -> None:
        """サマリーを表示"""
        print("\n" + "="*60)
        print("🎯 Phase 1完了計画サマリー")
        print("="*60)

        print(f"\n📊 現在の状況:")
        print(f"   - 現在: {self.current_count}件")
        print(f"   - 目標: {self.target_count}件")
        print(f"   - 必要: {self.remaining}件")

        print(f"\n📅 スケジュール:")
        for batch_name, batch_info in schedule.items():
            print(f"   - {batch_info['date']}: {batch_info['count']}件")

        # カテゴリー別集計
        categories = Counter(c['category'] for c in candidates)
        print(f"\n📂 カテゴリー別追加予定:")
        for category, count in categories.most_common(5):
            print(f"   - {category}: {count}件")
        if len(categories) > 5:
            others = sum(count for cat, count in categories.items()
                        if cat not in [c[0] for c in categories.most_common(5)])
            print(f"   - その他: {others}件")

        print(f"\n✨ Phase 1完了予定: 2025年10月21日")

    def run(self) -> None:
        """Phase 1完了計画を実行"""
        print("🚀 Phase 1完了計画生成システム")
        print("="*60)

        # 35名の候補者を生成
        candidates = self.generate_35_candidates()

        # バッチスケジュールを作成
        schedule = self.create_batch_schedule(candidates)

        # データ保存
        self.save_candidate_data(candidates)

        # レポート生成
        self.generate_completion_report(candidates, schedule)

        # サマリー表示
        self.show_summary(candidates, schedule)

        print("\n✅ Phase 1完了計画の生成が完了しました！")
        print("📌 次のアクション:")
        print("   1. phase1_completion_report_*.md を確認")
        print("   2. 週次バッチ生成を開始")
        print("   3. スケジューラーで自動化")

def main():
    planner = Phase1CompletionPlan()
    planner.run()

if __name__ == "__main__":
    main()