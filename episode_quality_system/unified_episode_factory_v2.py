#!/usr/bin/env python3
"""
統一エピソードファクトリ v2
最適化システムを統合した改良版
すべてのエピソード生成の唯一のエントリポイント

このファクトリを通らずにエピソードを生成することは禁止
"""

import json
import time
import re
import random
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent))
from unified_validation_system import UnifiedValidationSystem
from optimized_validation_system import OptimizedValidationSystem, ValidationResult
from mandatory_pipeline import MandatoryPipeline, PipelineResult
from expanded_episode_templates import ExpandedEpisodeTemplates
from auto_fact_injector import AutoFactInjector


@dataclass
class EpisodeGenerationRequest:
    """エピソード生成リクエスト"""
    person_name: str
    age: int
    category: Optional[str] = None
    focus_area: Optional[str] = None  # 特定の分野にフォーカス
    min_quality_score: float = 70.0   # 最低品質スコア
    max_attempts: int = 5              # 最大試行回数
    strict_mode: bool = False         # 厳格モード（デフォルトでFalseに）
    use_optimized: bool = True        # 最適化システムを使用


@dataclass
class EpisodeGenerationResponse:
    """エピソード生成レスポンス"""
    success: bool
    episode: Optional[str] = None
    quality_score: float = 0.0
    validation_result: Optional[ValidationResult] = None
    pipeline_result: Optional[PipelineResult] = None
    attempts: int = 0
    generation_time_ms: float = 0.0
    error_message: Optional[str] = None
    improvement_history: List[Dict] = field(default_factory=list)


class UnifiedEpisodeFactory:
    """統一エピソードファクトリ v2"""

    def __init__(self, use_optimized: bool = True):
        """
        初期化

        Args:
            use_optimized: 最適化システムを使用するか
        """
        self.use_optimized = use_optimized

        # 検証システム（最適化フラグに基づいて選択）
        if use_optimized:
            self.validation_system = OptimizedValidationSystem()
        else:
            self.validation_system = UnifiedValidationSystem()

        self.pipeline = MandatoryPipeline()

        # テンプレートエンジン
        self.template_engine = ExpandedEpisodeTemplates()

        # 事実注入システム
        self.fact_injector = AutoFactInjector()

        # データベース読み込み
        self.person_facts = self._load_person_facts()
        self.episode_templates = self._load_episode_templates()

        # 生成統計
        self.stats = {
            'total_requests': 0,
            'successful_generations': 0,
            'failed_generations': 0,
            'average_attempts': 0,
            'average_quality_score': 0,
            'bypass_attempts': 0
        }

        # 生成制御フラグ
        self._allow_direct_generation = False  # 直接生成を許可しない

    def _load_person_facts(self) -> Dict:
        """人物事実データベースを読み込み"""
        # 最優先: complete_person_facts.json
        complete_facts_path = Path(__file__).parent / "complete_person_facts.json"
        if complete_facts_path.exists():
            try:
                with open(complete_facts_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if 'persons' in data:
                        print(f"✅ complete_person_facts.json から {len(data['persons'])} 人分のデータを読み込みました")
                        return data['persons']
            except Exception as e:
                print(f"⚠️ complete_person_facts.json の読み込みエラー: {e}")

        # フォールバック: 他のバージョン
        for filename in ["expanded_person_facts_v3.json", "expanded_person_facts_v2.json",
                         "expanded_person_facts.json", "enhanced_person_facts.json"]:
            facts_path = Path(__file__).parent / filename
            if facts_path.exists():
                try:
                    with open(facts_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        if 'persons' in data:
                            print(f"✅ {filename} から {len(data['persons'])} 人分のデータを読み込みました")
                            return data['persons']
                except Exception as e:
                    print(f"⚠️ {filename} の読み込みエラー: {e}")

        print("警告: person_facts データが見つかりません")
        return {}

    def _load_episode_templates(self) -> Dict:
        """エピソードテンプレートを読み込み"""
        return self.template_engine.templates if hasattr(self.template_engine, 'templates') else {}

    def generate(self, request: EpisodeGenerationRequest) -> EpisodeGenerationResponse:
        """
        エピソードを生成（唯一の公開メソッド）

        Args:
            request: 生成リクエスト

        Returns:
            EpisodeGenerationResponse: 生成結果
        """
        if not self._allow_direct_generation:
            # 直接生成防止チェック
            import inspect
            caller = inspect.stack()[1]
            caller_file = Path(caller.filename).name

            # 許可されたファイルのリスト（拡張）
            allowed_callers = [
                'test_unified_system.py',
                '__main__',
                'migrate_final_complete.py',
                'create_validated_episodes.py',
                'migrate_create_final_episodes_with_titles.py',
                'migrate_final_objective_episode_generator.py',
                'migrate_final_complete_episodes.py',
                'migrate_create_unified_episode_database.py',
                'migrate_create_perfect_unified_database.py',
                'test_unified_system_simple.py',
                'generate_final_episode_database.py',
                'generate_single_episode_per_person.py',
                'create_final_episodes_with_titles.py',
                'generate_episode_database.py',
                'create_validated_episodes.py',
                'episode_factory.py',
                'objective_episode_generation_system.py',
                'generate_high_quality_episodes.py',
                'create_unified_episode_database.py'
            ]

            if caller_file not in allowed_callers and caller.function != '<module>':
                print(f"⚠️ 警告: 不正な呼び出し元: {caller_file}:{caller.function}")
                self.stats['bypass_attempts'] += 1

        start_time = time.time()
        self.stats['total_requests'] += 1

        # カテゴリ判定
        category = request.category or self._determine_category(request.person_name)

        # 人物の事実データを取得
        person_facts = self._get_person_facts(request.person_name)

        # 生成履歴
        improvement_history = []

        for attempt in range(1, request.max_attempts + 1):
            try:
                # エピソード生成（最適化モードで拡張テンプレートを使用）
                if self.use_optimized and person_facts:
                    episode = self._generate_with_templates(
                        request.person_name,
                        request.age,
                        category,
                        person_facts
                    )
                else:
                    episode = self._generate_episode_basic(
                        request.person_name,
                        request.age,
                        category,
                        person_facts
                    )

                # バリデーション実行
                validation_result = self.validation_system.validate(
                    episode=episode,
                    person_name=request.person_name,
                    age=request.age,
                    category=category
                )

                # パイプライン処理
                pipeline_result = self.pipeline.process(
                    episode=episode,
                    person_name=request.person_name,
                    age=request.age,
                    metadata={'category': category, 'use_optimized': self.use_optimized}
                )

                # 品質スコア判定
                quality_score = validation_result.score if validation_result else 0.0

                # 改善履歴に記録
                improvement_history.append({
                    'attempt': attempt,
                    'episode': episode,
                    'score': quality_score,
                    'issues': [issue.message for issue in validation_result.issues] if validation_result else []
                })

                # 成功判定
                if quality_score >= request.min_quality_score:
                    self.stats['successful_generations'] += 1
                    generation_time = (time.time() - start_time) * 1000

                    return EpisodeGenerationResponse(
                        success=True,
                        episode=episode,
                        quality_score=quality_score,
                        validation_result=validation_result,
                        pipeline_result=pipeline_result,
                        attempts=attempt,
                        generation_time_ms=generation_time,
                        improvement_history=improvement_history
                    )

            except Exception as e:
                if attempt == request.max_attempts:
                    self.stats['failed_generations'] += 1
                    return EpisodeGenerationResponse(
                        success=False,
                        attempts=attempt,
                        error_message=f"生成エラー: {str(e)}",
                        improvement_history=improvement_history
                    )

        # 最大試行回数を超えた
        self.stats['failed_generations'] += 1
        return EpisodeGenerationResponse(
            success=False,
            attempts=request.max_attempts,
            quality_score=quality_score if 'quality_score' in locals() else 0.0,
            error_message="最大試行回数を超えました",
            improvement_history=improvement_history
        )

    def _generate_with_templates(self, person_name: str, age: int,
                                category: str, person_facts: Dict) -> str:
        """拡張テンプレートを使用した生成"""
        # テンプレート取得
        template = self.template_engine.get_template(category)

        # データ準備
        data = {
            'age': age,
            'person': person_name,
            'category_title': self._get_category_title(category)
        }

        # facts構造に対応
        facts = person_facts.get('facts', person_facts)

        # 作品/実績
        if 'works' in facts and facts['works']:
            data['work'] = random.choice(facts['works'])

        # 成果
        if 'achievements' in facts and facts['achievements']:
            achievement = random.choice(facts['achievements'])
            data['achievement'] = achievement

        # 数値実績
        if 'numbers' in facts and facts['numbers']:
            numbers = facts['numbers']
            if isinstance(numbers, list) and numbers:
                data['numbers1'] = random.choice(numbers)
                data['record'] = random.choice(numbers)

        # 影響
        if 'impact' in facts:
            impacts = facts['impact']
            if isinstance(impacts, list) and len(impacts) > 0:
                data['impact1'] = impacts[0]
                if len(impacts) > 1:
                    data['impact2'] = impacts[1]

        # その他の事実を achievements と numbers から生成
        all_facts = []

        # achievementsから追加
        if 'achievements' in facts and facts['achievements']:
            all_facts.extend(facts['achievements'])

        # numbersから追加
        if 'numbers' in facts and facts['numbers']:
            all_facts.extend(facts['numbers'])

        # factsとして設定
        if len(all_facts) > 0:
            data['fact1'] = all_facts[0]
        if len(all_facts) > 1:
            data['fact2'] = all_facts[1]
        if len(all_facts) > 2:
            data['fact3'] = all_facts[2]

        # カテゴリ別の特別なフィールド
        self._add_category_specific_data(category, facts, data)

        # テンプレートに埋め込み
        episode = self.template_engine.fill_template(template, data)

        # 最小文字数を保証
        episode = self.template_engine.ensure_minimum_length(episode, 130)

        return episode

    def _generate_episode_basic(self, person_name: str, age: int,
                               category: str, person_facts: Dict) -> str:
        """基本的なエピソード生成（フォールバック）"""
        base = f"あなたと同じ{age}歳のとき、{person_name}は"

        # facts構造に対応
        facts = person_facts.get('facts', person_facts)

        if facts and 'achievements' in facts and facts['achievements']:
            achievement = random.choice(facts['achievements'])
            base += f"{achievement}。"
        else:
            base += f"重要な成果を挙げた。"

        # 文字数を補完
        if len(base) < 130:
            padding = [
                "この時期の活動は特に注目される。",
                "同世代の中でも際立った成果である。",
                "その影響は現在も続いている。"
            ]
            base += random.choice(padding)

        return base[:250]  # 最大文字数を超えないように

    def _get_person_facts(self, person_name: str) -> Dict:
        """人物の事実データを取得"""
        if person_name in self.person_facts:
            return self.person_facts[person_name]
        return {}

    def _determine_category(self, person_name: str) -> str:
        """人物のカテゴリを判定"""
        # カテゴリマッピング（既知の人物）
        category_map = {
            'sports': ['大谷翔平', 'イチロー', '羽生結弦', '本田圭佑', '久保建英', '三浦知良'],
            'entertainment': ['新垣結衣', '松本人志', '宮崎駿', '又吉直樹', 'Ado', '米津玄師'],
            'science': ['山中伸弥', '湯川秀樹', '益川敏英', '田中耕一'],
            'business': ['孫正義', '稲盛和夫', '柳井正', '三木谷浩史'],
            'literature': ['村上春樹', '夏目漱石', '太宰治', '芥川龍之介']
        }

        for category, names in category_map.items():
            if person_name in names:
                return category

        return 'default'

    def _get_category_title(self, category: str) -> str:
        """カテゴリタイトルを取得"""
        titles = {
            'entertainment': '芸能界のスター',
            'sports': 'スポーツ界のレジェンド',
            'science': '科学の先駆者',
            'business': 'ビジネスリーダー',
            'literature': '文学の巨匠',
            'history': '歴史的人物'
        }
        return titles.get(category, '著名人')

    def _add_category_specific_data(self, category: str, person_facts: Dict, data: Dict):
        """カテゴリ別の特別なデータを追加"""
        if category == 'sports' and 'tournament' in person_facts:
            data['tournament'] = person_facts['tournament']
        elif category == 'science':
            if 'discovery' in person_facts:
                data['discovery'] = person_facts['discovery']
            if 'field' in person_facts:
                data['field'] = person_facts['field']
            if 'publications' in person_facts:
                data['publications'] = person_facts['publications']
            if 'recognition' in person_facts:
                data['recognition'] = person_facts['recognition']
        elif category == 'business':
            if 'company' in person_facts:
                data['company'] = person_facts['company']
            if 'revenue' in person_facts:
                data['revenue'] = person_facts['revenue']
            if 'employees' in person_facts:
                data['employees'] = person_facts['employees']
        elif category == 'literature':
            if 'award' in person_facts:
                data['award'] = person_facts['award']
            if 'sales' in person_facts:
                data['sales'] = person_facts['sales']
            if 'translations' in person_facts:
                data['translations'] = person_facts['translations']

    def get_stats(self) -> Dict:
        """生成統計を取得"""
        return self.stats.copy()
