#!/usr/bin/env python3
"""
Fact Freshness Checker
データベースの鮮度を監視し、更新が必要な人物を検出
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import sys

# PDCAガーディアンのインポート
sys.path.append(str(Path(__file__).parent))
from pdca_guardian import PDCAGuardian
from enhanced_selection_algorithm import EnhancedSelectionAlgorithm


class FactFreshnessChecker:
    """データ鮮度チェッカー"""

    def __init__(self, database_path: str = "verified_facts_database_103persons.json"):
        self.database_path = database_path
        self.current_year = datetime.now().year
        self.pdca_guardian = PDCAGuardian()
        self.selection_algorithm = EnhancedSelectionAlgorithm()

        # 鮮度基準
        self.freshness_thresholds = {
            'critical': 3,  # 3年以上古い
            'warning': 2,   # 2年以上古い
            'info': 1       # 1年以上古い
        }

        # カテゴリ別の更新頻度要求
        self.category_update_requirements = {
            'スポーツ': 1,      # 毎年更新推奨
            '政治': 2,          # 2年ごと
            'エンタメ': 1,      # 毎年
            '科学・技術': 2,    # 2年ごと
            '文化・芸術': 3,    # 3年ごと
            'その他': 2         # 2年ごと
        }

        self.database = self._load_database()

    def _load_database(self) -> Dict:
        """データベースの読み込み"""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('verified_facts', {})
        except FileNotFoundError:
            print(f"警告: {self.database_path}が見つかりません")
            return {}

    def check_person_freshness(self, person_name: str, person_data: Dict) -> Dict:
        """
        個人のデータ鮮度をチェック

        Args:
            person_name: 人物名
            person_data: 人物データ

        Returns:
            鮮度チェック結果
        """
        facts = person_data.get('facts', [])
        if not facts:
            return {
                'person_name': person_name,
                'status': 'NO_DATA',
                'severity': 'critical',
                'message': 'データが存在しません'
            }

        # 最新の事実の年を取得
        latest_year = 0
        for fact in facts:
            year = self.selection_algorithm._extract_year(fact)
            latest_year = max(latest_year, year)

        # 鮮度評価
        years_old = self.current_year - latest_year
        severity = self._determine_severity(years_old)

        # カテゴリ別の要求チェック
        category = self._determine_category(person_name)
        required_freshness = self.category_update_requirements.get(category, 2)

        needs_update = years_old >= required_freshness

        # 最新の偉業があるかチェック（既知の重要イベント）
        missing_achievements = self._check_missing_achievements(person_name, facts)

        return {
            'person_name': person_name,
            'person_id': person_data.get('person_id', 'UNKNOWN'),
            'latest_data_year': latest_year,
            'years_old': years_old,
            'severity': severity,
            'category': category,
            'needs_update': needs_update,
            'missing_achievements': missing_achievements,
            'recommendation': self._generate_recommendation(person_name, years_old, missing_achievements)
        }

    def _determine_severity(self, years_old: int) -> str:
        """鮮度の深刻度を判定"""
        if years_old >= self.freshness_thresholds['critical']:
            return 'critical'
        elif years_old >= self.freshness_thresholds['warning']:
            return 'warning'
        elif years_old >= self.freshness_thresholds['info']:
            return 'info'
        return 'good'

    def _determine_category(self, person_name: str) -> str:
        """人物のカテゴリを判定"""
        categories = {
            'スポーツ': ['大谷翔平', 'イチロー', '羽生結弦', '吉田沙保里'],
            '政治': ['安倍晋三', '小泉純一郎', '田中角栄'],
            'エンタメ': ['HIKAKIN', 'Ado', 'あいみょん', '松田聖子'],
            '科学・技術': ['山中伸弥', '本庶佑'],
            '文化・芸術': ['宮崎駿', '黒澤明', '村上春樹', '北野武']
        }

        for category, names in categories.items():
            if person_name in names:
                return category
        return 'その他'

    def _check_missing_achievements(self, person_name: str, facts: List[Dict]) -> List[str]:
        """既知の重要な偉業が欠落していないかチェック"""
        missing = []

        # 2024年の重要な偉業（ハードコード）
        known_2024_achievements = {
            '大谷翔平': ['50-50達成', 'ワールドシリーズ優勝', '3度目MVP'],
            '藤井聡太': ['八冠達成'],
            # 他の人物の2024年偉業も追加可能
        }

        if person_name in known_2024_achievements:
            achievements = known_2024_achievements[person_name]
            fact_texts = ' '.join([f.get('fact', '') for f in facts])

            for achievement in achievements:
                if achievement not in fact_texts:
                    missing.append(achievement)

        return missing

    def _generate_recommendation(self, person_name: str, years_old: int, missing: List[str]) -> str:
        """更新推奨事項を生成"""
        if missing:
            return f"緊急更新必要: {', '.join(missing)}が欠落"
        elif years_old >= 3:
            return f"更新強く推奨: {years_old}年前のデータ"
        elif years_old >= 2:
            return f"更新推奨: 最新データは{self.current_year - years_old}年"
        elif years_old >= 1:
            return "定期更新を検討"
        return "データは最新"

    def generate_freshness_report(self) -> Dict:
        """
        全体の鮮度レポートを生成

        Returns:
            鮮度レポート
        """
        results = {
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_persons': len(self.database),
            'persons_needing_update': [],
            'critical_updates': [],
            'statistics': {
                'critical': 0,
                'warning': 0,
                'info': 0,
                'good': 0
            }
        }

        # 各人物をチェック
        for person_name, person_data in self.database.items():
            check_result = self.check_person_freshness(person_name, person_data)

            if check_result['needs_update']:
                results['persons_needing_update'].append(check_result)

            if check_result['severity'] == 'critical':
                results['critical_updates'].append({
                    'name': person_name,
                    'reason': check_result['recommendation']
                })

            # 統計更新
            severity = check_result['severity']
            if severity in results['statistics']:
                results['statistics'][severity] += 1

        # サマリー追加
        results['summary'] = {
            'update_needed_count': len(results['persons_needing_update']),
            'critical_count': results['statistics']['critical'],
            'freshness_score': self._calculate_freshness_score(results['statistics'])
        }

        return results

    def _calculate_freshness_score(self, statistics: Dict) -> float:
        """全体の鮮度スコアを計算（0-100）"""
        total = sum(statistics.values())
        if total == 0:
            return 0

        weights = {
            'good': 100,
            'info': 75,
            'warning': 50,
            'critical': 0
        }

        score = sum(statistics[level] * weights[level] for level in weights)
        return score / total

    def save_report(self, report: Dict, output_path: str = None):
        """レポートを保存"""
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = f"freshness_report_{timestamp}.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"📄 鮮度レポート保存: {output_path}")

    def print_summary(self, report: Dict):
        """レポートのサマリーを表示"""
        print("\n" + "=" * 60)
        print("📊 データ鮮度レポート")
        print("=" * 60)

        print(f"\n総人物数: {report['total_persons']}")
        print(f"更新必要: {report['summary']['update_needed_count']}人")
        print(f"緊急更新: {report['summary']['critical_count']}人")
        print(f"鮮度スコア: {report['summary']['freshness_score']:.1f}/100")

        if report['critical_updates']:
            print("\n🚨 緊急更新が必要な人物:")
            for item in report['critical_updates'][:5]:  # 上位5件
                print(f"  - {item['name']}: {item['reason']}")

        print("\n📈 鮮度分布:")
        stats = report['statistics']
        total = sum(stats.values())
        for level, count in stats.items():
            percentage = (count / total * 100) if total > 0 else 0
            bar = "█" * int(percentage / 2)
            print(f"  {level:8}: {bar} {count:3}人 ({percentage:.1f}%)")


def main():
    """メイン処理"""
    print("=" * 60)
    print("Fact Freshness Checker - データ鮮度チェッカー")
    print("=" * 60)

    checker = FactFreshnessChecker()

    # 特定の人物をチェック（例：大谷翔平）
    if '大谷翔平' in checker.database:
        print("\n【大谷翔平の鮮度チェック】")
        result = checker.check_person_freshness('大谷翔平', checker.database['大谷翔平'])
        print(f"最新データ: {result['latest_data_year']}年")
        print(f"鮮度: {result['years_old']}年前")
        print(f"深刻度: {result['severity']}")
        print(f"推奨事項: {result['recommendation']}")

        if result['missing_achievements']:
            print(f"欠落している偉業: {', '.join(result['missing_achievements'])}")

    # 全体レポート生成
    print("\n📝 全体鮮度レポート生成中...")
    report = checker.generate_freshness_report()

    # サマリー表示
    checker.print_summary(report)

    # レポート保存
    checker.save_report(report)

    print("\n✅ データ鮮度チェック完了！")


if __name__ == "__main__":
    main()