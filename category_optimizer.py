#!/usr/bin/env python3
"""
カテゴリーバランス最適化システム
自動的に不足カテゴリーを検出し、バランスを最適化
"""

import csv
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from collections import Counter
import math

class CategoryOptimizer:
    def __init__(self):
        self.master_file = self.find_master_file()
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 理想的なカテゴリー分布（Phase 1: 100件時点）
        self.ideal_distribution_phase1 = {
            "スポーツ": 0.15,
            "ビジネス": 0.12,
            "音楽": 0.10,
            "科学・研究": 0.10,
            "テクノロジー": 0.08,
            "文化・芸術": 0.08,
            "エンターテインメント": 0.06,
            "映画": 0.05,
            "医学・健康": 0.05,
            "政治・社会": 0.05,
            "建築・デザイン": 0.04,
            "文学": 0.03,
            "宇宙・探検": 0.03,
            "教育": 0.03,
            "その他": 0.03
        }

        # Phase 2（500件）での理想分布
        self.ideal_distribution_phase2 = {
            "スポーツ": 0.12,
            "ビジネス": 0.10,
            "音楽": 0.08,
            "科学・研究": 0.10,
            "テクノロジー": 0.10,
            "文化・芸術": 0.08,
            "エンターテインメント": 0.08,
            "映画": 0.06,
            "医学・健康": 0.06,
            "政治・社会": 0.06,
            "建築・デザイン": 0.04,
            "文学": 0.04,
            "宇宙・探検": 0.03,
            "教育": 0.03,
            "社会起業": 0.02
        }

    def find_master_file(self) -> Optional[str]:
        """マスターファイルを検索"""
        candidates = [
            "master/episodes_master_current.csv",
            "episodes_master_current.csv"
        ]

        for file in candidates:
            if os.path.exists(file):
                return file

        # 最新のマスターファイルを検索
        files = [f for f in os.listdir('.') if 'episodes_master_' in f and f.endswith('.csv')]
        if files:
            return sorted(files)[-1]

        return None

    def analyze_current_distribution(self) -> Tuple[Dict[str, float], int]:
        """現在のカテゴリー分布を分析"""
        if not self.master_file or not os.path.exists(self.master_file):
            return {}, 0

        categories = []
        with open(self.master_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                categories.append(row.get('category', '不明'))

        total = len(categories)
        counter = Counter(categories)

        distribution = {}
        for category, count in counter.items():
            distribution[category] = count / total if total > 0 else 0

        return distribution, total

    def calculate_deviation(self, current: Dict[str, float], ideal: Dict[str, float]) -> Dict[str, float]:
        """理想分布からの偏差を計算"""
        deviation = {}

        for category, ideal_ratio in ideal.items():
            current_ratio = current.get(category, 0)
            deviation[category] = ideal_ratio - current_ratio

        return deviation

    def prioritize_categories(self, total_count: int) -> List[Tuple[str, int, str]]:
        """優先すべきカテゴリーと必要追加数を決定"""
        current_dist, current_total = self.analyze_current_distribution()

        # フェーズに応じた理想分布を選択
        if current_total < 100:
            ideal_dist = self.ideal_distribution_phase1
            target_total = 100
        elif current_total < 500:
            ideal_dist = self.ideal_distribution_phase2
            target_total = 500
        else:
            ideal_dist = self.ideal_distribution_phase2
            target_total = 1000

        deviation = self.calculate_deviation(current_dist, ideal_dist)

        # 優先順位付け
        priorities = []
        for category, dev in sorted(deviation.items(), key=lambda x: x[1], reverse=True):
            if dev > 0:  # 不足しているカテゴリーのみ
                # 必要追加数を計算
                ideal_count = math.ceil(target_total * ideal_dist[category])
                current_count = int(current_total * current_dist.get(category, 0))
                needed = ideal_count - current_count

                if needed > 0:
                    # 優先度を決定
                    if dev > 0.05:
                        priority = "🔴 最優先"
                    elif dev > 0.03:
                        priority = "🟡 優先"
                    else:
                        priority = "🟢 通常"

                    priorities.append((category, needed, priority))

        return priorities

    def generate_optimization_plan(self, batch_size: int = 10) -> Dict:
        """最適化計画を生成"""
        current_dist, current_total = self.analyze_current_distribution()
        priorities = self.prioritize_categories(current_total)

        # バッチごとの配分を計画
        plan = {
            "current_status": {
                "total": current_total,
                "distribution": current_dist
            },
            "optimization_targets": [],
            "batch_allocation": []
        }

        # 最適化ターゲット
        for category, needed, priority in priorities[:10]:  # 上位10カテゴリー
            plan["optimization_targets"].append({
                "category": category,
                "current_ratio": f"{current_dist.get(category, 0)*100:.1f}%",
                "ideal_ratio": f"{self.get_ideal_ratio(category, current_total)*100:.1f}%",
                "needed_count": needed,
                "priority": priority
            })

        # バッチ配分計画
        remaining = batch_size
        batch = []
        for category, needed, _ in priorities:
            if remaining > 0:
                allocation = min(remaining, min(needed, 3))  # 1バッチ最大3件/カテゴリー
                if allocation > 0:
                    batch.append({
                        "category": category,
                        "count": allocation
                    })
                    remaining -= allocation

        plan["batch_allocation"] = batch

        return plan

    def get_ideal_ratio(self, category: str, total: int) -> float:
        """総数に応じた理想比率を取得"""
        if total < 100:
            return self.ideal_distribution_phase1.get(category, 0.01)
        else:
            return self.ideal_distribution_phase2.get(category, 0.01)

    def calculate_balance_score(self) -> float:
        """カテゴリーバランススコアを計算（100点満点）"""
        current_dist, total = self.analyze_current_distribution()

        if total == 0:
            return 0

        # 理想分布を選択
        ideal_dist = self.ideal_distribution_phase1 if total < 100 else self.ideal_distribution_phase2

        # 偏差の二乗和を計算
        deviation_sum = 0
        for category in ideal_dist:
            ideal_ratio = ideal_dist[category]
            current_ratio = current_dist.get(category, 0)
            deviation_sum += (ideal_ratio - current_ratio) ** 2

        # スコア計算（偏差が小さいほど高スコア）
        max_deviation = len(ideal_dist) * 0.1 ** 2  # 最大偏差の仮定
        score = max(0, 100 * (1 - deviation_sum / max_deviation))

        return round(score, 1)

    def generate_recommendations(self) -> List[str]:
        """改善推奨事項を生成"""
        priorities = self.prioritize_categories(100)
        recommendations = []

        # 最優先カテゴリーの推奨
        critical = [p for p in priorities if "最優先" in p[2]]
        if critical:
            categories = ", ".join([p[0] for p in critical[:3]])
            recommendations.append(f"🔴 {categories}のエピソードを優先的に追加")

        # バランススコアに基づく推奨
        score = self.calculate_balance_score()
        if score < 70:
            recommendations.append("⚠️ カテゴリーバランスの大幅な改善が必要")
        elif score < 85:
            recommendations.append("📊 カテゴリーバランスの微調整を推奨")
        else:
            recommendations.append("✅ カテゴリーバランスは良好")

        # 過剰カテゴリーの警告
        current_dist, _ = self.analyze_current_distribution()
        for category, ratio in current_dist.items():
            ideal_ratio = self.get_ideal_ratio(category, 100)
            if ratio > ideal_ratio * 1.5:  # 理想の1.5倍以上
                recommendations.append(f"⚠️ {category}が過剰（{ratio*100:.1f}%）")

        return recommendations

    def save_optimization_report(self, plan: Dict) -> None:
        """最適化レポートを保存"""
        report_file = f"category_optimization_{self.timestamp}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "balance_score": self.calculate_balance_score(),
                "recommendations": self.generate_recommendations(),
                "optimization_plan": plan
            }, f, ensure_ascii=False, indent=2)

        print(f"📄 最適化レポート保存: {report_file}")

    def visualize_distribution(self) -> None:
        """分布を視覚化（テキストベース）"""
        current_dist, total = self.analyze_current_distribution()

        print("\n" + "="*60)
        print("📊 カテゴリー分布の視覚化")
        print("="*60)

        # カテゴリーを比率順にソート
        sorted_cats = sorted(current_dist.items(), key=lambda x: x[1], reverse=True)

        for category, ratio in sorted_cats[:10]:  # 上位10カテゴリー
            ideal_ratio = self.get_ideal_ratio(category, total)

            # バーグラフ
            current_bar = "█" * int(ratio * 50)
            ideal_marker = "|" if ideal_ratio < ratio else "│"
            ideal_pos = int(ideal_ratio * 50)

            print(f"\n{category:15s}")
            print(f"現在: {current_bar} {ratio*100:.1f}%")
            print(f"理想: {' ' * ideal_pos}{ideal_marker} {ideal_ratio*100:.1f}%")

            # 状態表示
            if ratio > ideal_ratio * 1.3:
                status = "🔴 過剰"
            elif ratio < ideal_ratio * 0.7:
                status = "🟡 不足"
            else:
                status = "🟢 適正"
            print(f"状態: {status}")

    def run_optimization(self) -> None:
        """最適化を実行"""
        print("🎯 カテゴリーバランス最適化システム")
        print("="*60)

        # 現在の状態を分析
        current_dist, total = self.analyze_current_distribution()

        if total == 0:
            print("❌ データが見つかりません")
            return

        print(f"\n📊 現在の状態:")
        print(f"   - 総エピソード数: {total}件")
        print(f"   - カテゴリー数: {len(current_dist)}種類")
        print(f"   - バランススコア: {self.calculate_balance_score()}点/100点")

        # 最適化計画を生成
        plan = self.generate_optimization_plan()

        print(f"\n🎯 最適化ターゲット（上位5件）:")
        for target in plan["optimization_targets"][:5]:
            print(f"   {target['priority']} {target['category']}: "
                  f"現在{target['current_ratio']} → 理想{target['ideal_ratio']} "
                  f"（+{target['needed_count']}件必要）")

        print(f"\n📋 次回バッチ配分案（10件）:")
        for allocation in plan["batch_allocation"]:
            print(f"   - {allocation['category']}: {allocation['count']}件")

        # 推奨事項
        print(f"\n💡 推奨事項:")
        for rec in self.generate_recommendations():
            print(f"   {rec}")

        # レポート保存
        self.save_optimization_report(plan)

        # 分布の視覚化
        self.visualize_distribution()

        print("\n✅ カテゴリー最適化分析完了！")

def main():
    optimizer = CategoryOptimizer()
    optimizer.run_optimization()

if __name__ == "__main__":
    main()