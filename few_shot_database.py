"""
Few-Shot Example Database
=========================

合格済みエピソード(100個)からカテゴリ別の高品質例を抽出し、
Few-Shot Learning用のデータベースを構築する。

Phase 1: Foundation - Few-Shot Database Construction
"""

import csv
import json
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from pathlib import Path
import re
import logging

# パフォーマンス最適化のインポート
from src.performance_optimizations import FewShotCacheOptimizer

logger = logging.getLogger(__name__)


@dataclass
class FewShotExample:
    """Few-Shot学習用のエピソード例"""
    episode_id: str
    person_name: str
    age: int
    episode_text: str
    category: str
    character_count: int
    emotional_impact_score: float
    specificity_score: float

    # 5要素の推定スコア（既存データから逆算）
    estimated_turning_point: float = 10.0  # 転換点
    estimated_unexpectedness: float = 7.0  # 意外性
    estimated_risk_taking: float = 7.0     # リスクテイキング
    estimated_empathy: float = 7.0         # 共感性
    estimated_sensational: float = 10.0    # センセーショナル度

    # キーワード分析
    has_anxiety_keywords: bool = False
    has_risk_keywords: bool = False
    has_turning_point_keywords: bool = False
    numerical_data_count: int = 0

    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return asdict(self)


class FewShotDatabase:
    """Few-Shot例のデータベース"""

    # カテゴリマッピング（正規化）
    CATEGORY_MAPPING = {
        'エンターテインメント': 'entertainment',
        'ビジネス': 'business',
        'スポーツ': 'sports',
        '科学': 'science',
        '音楽': 'music',
        'テクノロジー': 'technology',
        '文学': 'literature',
        '政治': 'politics',
        '映画': 'film',
        'アニメ': 'anime',
        '漫画': 'manga',
        '建築': 'architecture',
        '文化': 'culture',
        '教育': 'education',
    }

    # 不安・葛藤キーワード
    ANXIETY_KEYWORDS = [
        '本当に', '不安', '懸念', '心配', '葛藤', '?', 'だろうか',
        'できるのか', '疑問', '批判', '反対', '無理', '懐疑'
    ]

    # リスクキーワード
    RISK_KEYWORDS = [
        '初めて', '前例なく', '無名', '断行', '挑戦', '賭け', '決断',
        '覚悟', '逆境', '挫折', '乗り越え', 'ハンデ', '若さ'
    ]

    # 転機キーワード
    TURNING_POINT_KEYWORDS = [
        '転機', '決断', 'もたらした', '切り開いた', '押し上げた',
        '確立した', '達成した', '成し遂げた', '築いた', '実現した'
    ]

    def __init__(self, csv_path: str = "episodes_validated_100_20251001.csv"):
        """初期化"""
        self.csv_path = Path(csv_path)
        self.examples: List[FewShotExample] = []
        self.category_index: Dict[str, List[FewShotExample]] = {}

        # パフォーマンス最適化: キャッシュオプティマイザーの初期化
        self.cache_optimizer = FewShotCacheOptimizer()
        logger.info("✅ FewShotCacheOptimizer initialized")

    def load_from_csv(self) -> None:
        """CSVファイルから読み込み"""
        print(f"📂 Reading from {self.csv_path}...")

        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                example = self._parse_row(row)
                if example:
                    self.examples.append(example)

        print(f"✅ Loaded {len(self.examples)} examples")
        self._build_category_index()

    def _parse_row(self, row: Dict) -> Optional[FewShotExample]:
        """CSVの行をFewShotExampleに変換"""
        try:
            # 基本情報
            episode_id = row['episode_id']
            person_name = row['person_name']
            age = int(row['episode_age'])
            episode_text = row['episode_text']
            category = row['category']
            character_count = int(row['character_count'])

            # スコア情報
            emotional_impact = float(row.get('emotional_impact_score', 0.5))
            specificity = float(row.get('specificity_score', 0.5))

            # キーワード分析
            has_anxiety = self._has_keywords(episode_text, self.ANXIETY_KEYWORDS)
            has_risk = self._has_keywords(episode_text, self.RISK_KEYWORDS)
            has_turning_point = self._has_keywords(episode_text, self.TURNING_POINT_KEYWORDS)
            numerical_count = self._count_numbers(episode_text)

            # 5要素スコアの推定（キーワードベース）
            turning_point_score = 10.0 if has_turning_point else 8.0
            unexpectedness_score = 7.0 if has_risk else 5.0
            risk_taking_score = 7.0 if has_risk else 3.0
            empathy_score = 7.0 if has_anxiety else 3.0
            sensational_score = min(10.0, 4.0 + (numerical_count * 2))

            return FewShotExample(
                episode_id=episode_id,
                person_name=person_name,
                age=age,
                episode_text=episode_text,
                category=category,
                character_count=character_count,
                emotional_impact_score=emotional_impact,
                specificity_score=specificity,
                estimated_turning_point=turning_point_score,
                estimated_unexpectedness=unexpectedness_score,
                estimated_risk_taking=risk_taking_score,
                estimated_empathy=empathy_score,
                estimated_sensational=sensational_score,
                has_anxiety_keywords=has_anxiety,
                has_risk_keywords=has_risk,
                has_turning_point_keywords=has_turning_point,
                numerical_data_count=numerical_count
            )
        except (KeyError, ValueError) as e:
            print(f"⚠️ Error parsing row: {e}")
            return None

    def _has_keywords(self, text: str, keywords: List[str]) -> bool:
        """キーワードの存在チェック"""
        return any(kw in text for kw in keywords)

    def _count_numbers(self, text: str) -> int:
        """数値の出現回数をカウント"""
        # 数値パターン: 1234, 1,234, 1.234, 100万, 10億 等
        patterns = [
            r'\d+[,，]\d+',  # カンマ区切り
            r'\d+億',
            r'\d+万',
            r'\d+千',
            r'\d+%',
            r'\d+\.?\d*',  # 小数
        ]

        count = 0
        for pattern in patterns:
            matches = re.findall(pattern, text)
            count += len(matches)

        return count

    def _build_category_index(self) -> None:
        """カテゴリ別インデックスを構築"""
        print("📊 Building category index...")

        for example in self.examples:
            category = example.category
            if category not in self.category_index:
                self.category_index[category] = []
            self.category_index[category].append(example)

        # 統計を表示
        print("\n📈 Category Statistics:")
        for category, examples in sorted(self.category_index.items()):
            print(f"  {category}: {len(examples)} examples")

    def get_best_examples(
        self,
        category: str,
        n: int = 3,
        min_score: float = 30.0
    ) -> List[FewShotExample]:
        """
        カテゴリ別の最良例を取得（キャッシュ対応版）

        Args:
            category: カテゴリ名
            n: 取得する例の数
            min_score: 最低スコア（5要素合計の推定値）

        Returns:
            上位n個のFewShotExample
        """
        # キャッシュキー生成
        cache_key = f"examples:{category}:{n}:{min_score}"

        # キャッシュチェック
        cached_result = self.cache_optimizer.example_cache.get(cache_key)
        if cached_result is not None:
            logger.debug(f"✅ Cache hit: {category}")
            return cached_result

        # キャッシュミス: 元の処理を実行
        logger.debug(f"⚠️ Cache miss: {category}")
        result = self._get_best_examples_uncached(category, n, min_score)

        # キャッシュに保存
        self.cache_optimizer.example_cache.set(cache_key, result)

        return result

    def _get_best_examples_uncached(
        self,
        category: str,
        n: int = 3,
        min_score: float = 30.0
    ) -> List[FewShotExample]:
        """
        カテゴリ別の最良例を取得（キャッシュなし版）

        Args:
            category: カテゴリ名
            n: 取得する例の数
            min_score: 最低スコア（5要素合計の推定値）

        Returns:
            上位n個のFewShotExample
        """
        if category not in self.category_index:
            # カテゴリが見つからない場合は全例から選択
            print(f"⚠️ Category '{category}' not found, using all examples")
            candidates = self.examples
        else:
            candidates = self.category_index[category]

        # 5要素スコアの合計で評価
        def calculate_total_score(ex: FewShotExample) -> float:
            return (
                ex.estimated_turning_point +
                ex.estimated_unexpectedness +
                ex.estimated_risk_taking +
                ex.estimated_empathy +
                ex.estimated_sensational
            )

        # スコアでソート
        scored = [(ex, calculate_total_score(ex)) for ex in candidates]
        scored.sort(key=lambda x: x[1], reverse=True)

        # 最低スコア以上の例を選択
        filtered = [(ex, score) for ex, score in scored if score >= min_score]

        # 上位n個を返す
        return [ex for ex, _ in filtered[:n]]

    def get_example_by_person(self, person_name: str) -> Optional[FewShotExample]:
        """人物名で例を検索"""
        for example in self.examples:
            if example.person_name == person_name:
                return example
        return None

    def get_cache_stats(self) -> Dict:
        """
        キャッシュ統計を取得

        Returns:
            キャッシュヒット率、ミス率などの統計情報
        """
        return self.cache_optimizer.get_cache_stats()

    def export_to_json(self, output_path: str = "few_shot_database.json") -> None:
        """JSON形式でエクスポート"""
        print(f"\n💾 Exporting to {output_path}...")

        data = {
            'total_examples': len(self.examples),
            'categories': list(self.category_index.keys()),
            'examples': [ex.to_dict() for ex in self.examples],
            'category_index': {
                cat: [ex.episode_id for ex in exs]
                for cat, exs in self.category_index.items()
            }
        }

        output_file = Path(output_path)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"✅ Exported {len(self.examples)} examples to {output_file}")

    def analyze_success_patterns(self) -> Dict:
        """成功パターンを分析"""
        print("\n🔍 Analyzing success patterns...")

        total = len(self.examples)
        with_anxiety = sum(1 for ex in self.examples if ex.has_anxiety_keywords)
        with_risk = sum(1 for ex in self.examples if ex.has_risk_keywords)
        with_turning_point = sum(1 for ex in self.examples if ex.has_turning_point_keywords)
        avg_numbers = sum(ex.numerical_data_count for ex in self.examples) / total

        analysis = {
            'total_examples': total,
            'anxiety_keywords_ratio': with_anxiety / total,
            'risk_keywords_ratio': with_risk / total,
            'turning_point_keywords_ratio': with_turning_point / total,
            'average_numerical_data': avg_numbers,
            'average_character_count': sum(ex.character_count for ex in self.examples) / total
        }

        print(f"  Total examples: {total}")
        print(f"  Anxiety keywords: {with_anxiety}/{total} ({with_anxiety/total*100:.1f}%)")
        print(f"  Risk keywords: {with_risk}/{total} ({with_risk/total*100:.1f}%)")
        print(f"  Turning point keywords: {with_turning_point}/{total} ({with_turning_point/total*100:.1f}%)")
        print(f"  Average numbers: {avg_numbers:.2f}")
        print(f"  Average chars: {analysis['average_character_count']:.1f}")

        return analysis


def main():
    """メイン処理"""
    print("=" * 60)
    print("🎯 Few-Shot Database Construction")
    print("=" * 60)

    # データベース構築
    db = FewShotDatabase()
    db.load_from_csv()

    # 成功パターン分析
    analysis = db.analyze_success_patterns()

    # カテゴリ別のベスト例を表示
    print("\n" + "=" * 60)
    print("🌟 Top 3 Examples by Category")
    print("=" * 60)

    for category in ['エンターテインメント', 'ビジネス', 'スポーツ', '科学']:
        print(f"\n📁 {category}:")
        best = db.get_best_examples(category, n=3)
        for i, ex in enumerate(best, 1):
            total_score = (
                ex.estimated_turning_point +
                ex.estimated_unexpectedness +
                ex.estimated_risk_taking +
                ex.estimated_empathy +
                ex.estimated_sensational
            )
            print(f"  {i}. {ex.person_name} ({ex.age}歳) - 推定{total_score:.0f}点")
            print(f"     {ex.episode_text[:80]}...")

    # 特定の人物例を表示（計画書で使用した例）
    print("\n" + "=" * 60)
    print("📝 Reference Examples (from plan)")
    print("=" * 60)

    reference_people = ['新垣結衣', '松下幸之助', 'イチロー', 'HIKAKIN']
    for person in reference_people:
        ex = db.get_example_by_person(person)
        if ex:
            print(f"\n✅ {person} ({ex.age}歳) - {ex.category}")
            print(f"   不安: {ex.has_anxiety_keywords}, リスク: {ex.has_risk_keywords}")
            print(f"   数値: {ex.numerical_data_count}個, 文字数: {ex.character_count}")
            print(f"   テキスト: {ex.episode_text}")

    # JSONエクスポート
    db.export_to_json()

    print("\n" + "=" * 60)
    print("✅ Few-Shot Database Construction Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
