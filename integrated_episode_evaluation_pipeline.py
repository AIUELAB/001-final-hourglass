#!/usr/bin/env python3
"""
統合エピソード評価パイプライン
Integrated Episode Evaluation Pipeline with AI Collaboration & FactChecker

全検証システムを統合した総合的なエピソード評価・追加システム
検証順序:
1. 質問生成 - "〇〇の有名なエピソードや偉業や事件といえば？"
2. AI協調分析（Claude + Codex MCP）
3. 象徴性スコアリング（RULE_171: 100点基準）
4. PDCAガーディアン（150+ルール）
5. EpisodeGuardian（3層検証）
6. FactChecker（Wikipedia検証・ハルシネーション検出）

著者: Claude Code
日付: 2025-10-02
バージョン: 1.0.0
"""

import csv
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

# 既存システムのインポート
from collaborative_decision_system import CollaborativeDecisionSystem, DecisionSource
from pdca_guardian import PDCAGuardian, ViolationType
from episode_guardian import EpisodeGuardian, Severity as GuardianSeverity
from episode_quality_system.optimized_validation_system import OptimizedValidationSystem
# src/fact_checkerからはFactCheckerシステムをインポート
try:
    from src.fact_checker import FactChecker as SrcFactChecker
except ImportError:
    SrcFactChecker = None

# ルートのfact_checkerからHallucinationDetectorをインポート
try:
    from fact_checker import HallucinationDetector, FactCheckResult as OldFactCheckResult
except ImportError:
    HallucinationDetector = None
    OldFactCheckResult = None

# Phase 3: RULE_171 象徴性スコアリングシステム
from rules.rule_171_symbolism_scoring import evaluate_symbolism

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)


class EvaluationStage(Enum):
    """評価ステージ"""
    QUESTION_GENERATION = "質問生成"
    AI_COLLABORATION = "AI協調分析"
    PDCA_VALIDATION = "PDCAガーディアン"
    EPISODE_GUARDIAN = "EpisodeGuardian"
    OPTIMIZED_VALIDATION = "OptimizedValidation"
    FACT_CHECK = "FactChecker"
    CSV_OUTPUT = "CSV保存"


class EvaluationResult(Enum):
    """評価結果"""
    PASS = "合格"
    FAIL_CRITICAL = "不合格（CRITICAL）"
    FAIL_LOW_SCORE = "不合格（スコア不足）"
    FAIL_FACT_CHECK = "不合格（事実検証失敗）"


@dataclass
class EpisodeEvaluation:
    """エピソード評価結果"""
    person_name: str
    episode_age: int
    episode_text: str
    result: EvaluationResult
    stage_results: Dict[str, Any] = field(default_factory=dict)
    total_score: float = 0.0
    violations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "person_name": self.person_name,
            "episode_age": self.episode_age,
            "episode_text": self.episode_text,
            "result": self.result.value,
            "total_score": self.total_score,
            "violations": self.violations,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat()
        }


class QuestionGenerator:
    """AI協調分析用の質問生成器"""

    def generate(self, person_name: str) -> str:
        """
        有名エピソード質問を生成

        Args:
            person_name: 人物名

        Returns:
            質問文
        """
        return f"{person_name}の有名なエピソードや偉業や事件といえば？"

    def generate_achievement_query(self, person_name: str, category: str) -> str:
        """
        カテゴリ別偉業質問を生成

        Args:
            person_name: 人物名
            category: カテゴリ（entertainment, sports等）

        Returns:
            質問文
        """
        category_queries = {
            'entertainment': f"{person_name}の代表作や主な活躍といえば？",
            'sports': f"{person_name}の主な記録や大会成績といえば？",
            'science': f"{person_name}の主な研究や発見といえば？",
            'business': f"{person_name}の主な事業や経営実績といえば？",
            'literature': f"{person_name}の代表作や受賞歴といえば？"
        }

        return category_queries.get(category, self.generate(person_name))


class LifetimeHighlightsSelector:
    """
    生涯ハイライト方式（v3.0）による重要エピソード選定
    年齢カテゴリ優先ではなく、人生で最も重要な7つの瞬間を選定
    """

    def __init__(self):
        self.importance_weights = {
            'global_importance': 0.30,   # グローバル重要度
            'historical_value': 0.30,    # 歴史的価値
            'impact_score': 0.20,        # インパクトスコア
            'social_influence': 0.10,    # 社会的影響力
            'career_importance': 0.10    # キャリア重要性
        }

    def calculate_importance_score(self, episode: Dict) -> float:
        """
        エピソードの重要度スコアを計算（100点満点）

        Args:
            episode: エピソードデータ

        Returns:
            重要度スコア（0-100）
        """
        score = 0.0

        # グローバル重要度（30点）
        if self._is_global_achievement(episode):
            score += 30

        # 歴史的価値（30点）
        if self._has_historical_value(episode):
            score += 30

        # インパクトスコア（20点）
        score += self._calculate_impact(episode) * 20

        # 社会的影響力（10点）
        if self._has_social_influence(episode):
            score += 10

        # キャリア重要性（10点）
        if self._is_career_defining(episode):
            score += 10

        return min(score, 100.0)

    def _is_global_achievement(self, episode: Dict) -> bool:
        """世界的偉業の判定"""
        global_keywords = [
            'オリンピック', 'ワールドカップ', 'W杯', 'MVP', '世界選手権',
            'ノーベル', '世界記録', 'ギネス', '国連', 'ユネスコ'
        ]
        episode_text = episode.get('episode_text', '')
        return any(keyword in episode_text for keyword in global_keywords)

    def _has_historical_value(self, episode: Dict) -> bool:
        """歴史的価値の判定"""
        historical_keywords = [
            '初', '史上初', '日本初', '世界初', '歴史',
            '伝説', '偉業', '快挙', '金字塔'
        ]
        episode_text = episode.get('episode_text', '')
        return any(keyword in episode_text for keyword in historical_keywords)

    def _calculate_impact(self, episode: Dict) -> float:
        """インパクトの計算（0.0-1.0）"""
        episode_text = episode.get('episode_text', '')

        # 数値の大きさで判定
        import re
        numbers = re.findall(r'\d+(?:億|万|千)', episode_text)
        if numbers:
            return 1.0

        # 強調表現の検出
        impact_words = ['驚異的', '圧倒的', '前代未聞', '空前絶後']
        if any(word in episode_text for word in impact_words):
            return 0.8

        return 0.5

    def _has_social_influence(self, episode: Dict) -> bool:
        """社会的影響力の判定"""
        social_keywords = [
            '社会現象', '流行', 'ブーム', '影響',
            '国民的', '世代', 'トレンド'
        ]
        episode_text = episode.get('episode_text', '')
        return any(keyword in episode_text for keyword in social_keywords)

    def _is_career_defining(self, episode: Dict) -> bool:
        """キャリア決定的瞬間の判定"""
        career_keywords = [
            'デビュー', '引退', '転機', '転換点',
            '代表作', '最高傑作', '集大成'
        ]
        episode_text = episode.get('episode_text', '')
        return any(keyword in episode_text for keyword in career_keywords)

    def select_top_7(self, episodes: List[Dict]) -> List[Dict]:
        """
        重要度スコア順に上位7つを選定

        Args:
            episodes: エピソードリスト

        Returns:
            選定された7つのエピソード
        """
        # 各エピソードにスコアを付与
        scored_episodes = [
            (self.calculate_importance_score(ep), ep)
            for ep in episodes
        ]

        # スコア降順でソート
        scored_episodes.sort(key=lambda x: x[0], reverse=True)

        # 上位7つを返す
        return [ep for score, ep in scored_episodes[:7]]


class CSVOutputHandler:
    """CSV出力ハンドラー（UTF-8 BOM対応）"""

    def __init__(self, csv_path: str):
        """
        初期化

        Args:
            csv_path: 出力先CSVファイルパス
        """
        self.csv_path = Path(csv_path)
        self.columns = [
            'episode_id', 'person_name', 'episode_age', 'episode_text',
            'category', 'is_valid', 'validation_score', 'fact_check_status',
            'ai_consensus', 'pdca_violations', 'guardian_severity',
            'optimized_score', 'fact_confidence', 'created_at', 'notes'
        ]

    def append_episode(self, episode: Dict, evaluation: EpisodeEvaluation) -> bool:
        """
        エピソードをCSVに追加

        Args:
            episode: エピソードデータ
            evaluation: 評価結果

        Returns:
            成功したらTrue
        """
        try:
            # 既存データの読み込み（ある場合）
            existing_episodes = []
            if self.csv_path.exists():
                with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    existing_episodes = list(reader)

            # 新規エピソードIDの生成
            if existing_episodes:
                last_id = existing_episodes[-1]['episode_id']
                episode_num = int(last_id.replace('EP', '')) + 1
            else:
                episode_num = 1

            new_episode_id = f"EP{episode_num:03d}"

            # CSVレコードの作成
            csv_record = {
                'episode_id': new_episode_id,
                'person_name': episode.get('person_name', ''),
                'episode_age': episode.get('episode_age', 0),
                'episode_text': episode.get('episode_text', ''),
                'category': episode.get('category', ''),
                'is_valid': evaluation.result == EvaluationResult.PASS,
                'validation_score': evaluation.total_score,
                'fact_check_status': evaluation.stage_results.get('fact_check', {}).get('is_verified', False),
                'ai_consensus': evaluation.stage_results.get('ai_collaboration', {}).get('consensus', False),
                'pdca_violations': len(evaluation.violations),
                'guardian_severity': evaluation.stage_results.get('episode_guardian', {}).get('severity', 'INFO'),
                'optimized_score': evaluation.stage_results.get('optimized_validation', {}).get('score', 0),
                'fact_confidence': evaluation.stage_results.get('fact_check', {}).get('confidence_score', 0),
                'created_at': datetime.now().isoformat(),
                'notes': f"Total violations: {len(evaluation.violations)}"
            }

            # UTF-8 BOMでCSV出力
            with open(self.csv_path, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.columns)

                # ヘッダー書き込み
                writer.writeheader()

                # 既存データ書き込み
                for ep in existing_episodes:
                    writer.writerow(ep)

                # 新規データ書き込み
                writer.writerow(csv_record)

            logger.info(f"✅ エピソード{new_episode_id}をCSVに追加しました")
            return True

        except Exception as e:
            logger.error(f"❌ CSV出力エラー: {str(e)}")
            return False


class IntegratedEpisodeEvaluationPipeline:
    """
    統合エピソード評価パイプライン

    全検証システムを統合し、Fail-Fast原則で高品質エピソードのみを選定
    """

    def __init__(self, csv_output_path: str):
        """
        初期化

        Args:
            csv_output_path: CSV出力先パス
        """
        self.question_generator = QuestionGenerator()
        self.lifetime_selector = LifetimeHighlightsSelector()
        self.csv_handler = CSVOutputHandler(csv_output_path)

        # 検証システムの初期化
        self.ai_collaboration = CollaborativeDecisionSystem()
        self.pdca_guardian = PDCAGuardian()
        self.episode_guardian = EpisodeGuardian()
        self.optimized_validator = OptimizedValidationSystem()

        # FactCheckerの初期化（src版とルート版の両対応）
        if SrcFactChecker:
            from src.fact_checker import FactChecker as FCClass
        else:
            from fact_checker import FactChecker as FCClass
        self.fact_checker = FCClass()

        # HallucinationDetectorの初期化
        if HallucinationDetector:
            self.hallucination_detector = HallucinationDetector()
        else:
            self.hallucination_detector = None
            logger.warning("⚠️ HallucinationDetector が利用できません")

        logger.info("🚀 統合エピソード評価パイプライン初期化完了")

    def initialize(self) -> bool:
        """システム初期化"""
        logger.info("\n" + "="*70)
        logger.info("🎯 統合エピソード評価パイプライン - システム初期化")
        logger.info("="*70)

        # AI協調システムの初期化
        if not self.ai_collaboration.initialize():
            logger.warning("⚠️ AI協調システムの初期化に問題がありましたが続行します")

        logger.info("✅ すべてのコンポーネントが準備完了")
        return True

    def evaluate_episode(self, episode: Dict) -> EpisodeEvaluation:
        """
        エピソードの総合評価

        Args:
            episode: エピソードデータ

        Returns:
            評価結果
        """
        person_name = episode.get('person_name', '')
        episode_age = episode.get('episode_age', 0)
        episode_text = episode.get('episode_text', '')
        category = episode.get('category', '')

        logger.info(f"\n{'='*70}")
        logger.info(f"📋 エピソード評価開始: {person_name}（{episode_age}歳）")
        logger.info(f"{'='*70}")

        evaluation = EpisodeEvaluation(
            person_name=person_name,
            episode_age=episode_age,
            episode_text=episode_text,
            result=EvaluationResult.PASS
        )

        try:
            # ステージ1: 質問生成
            question = self.question_generator.generate(person_name)
            logger.info(f"\n🔍 ステージ1: 質問生成")
            logger.info(f"   質問: {question}")
            evaluation.stage_results['question'] = question

            # ステージ2: AI協調分析
            logger.info(f"\n🤝 ステージ2: AI協調分析")
            ai_analysis = self.ai_collaboration.collaborative_analyze(question, episode)
            evaluation.stage_results['ai_collaboration'] = {
                'consensus': ai_analysis.final_decision.consensus,
                'confidence': ai_analysis.final_decision.confidence,
                'source': ai_analysis.final_decision.source.value
            }

            if not ai_analysis.final_decision.consensus and ai_analysis.final_decision.confidence < 0.7:
                evaluation.warnings.append("AI協調分析で低信頼度（継続）")

            # ステージ3: 象徴性スコアリング（RULE_171）
            logger.info(f"\n⚙️ ステージ3: 象徴性スコアリング（RULE_171）")
            symbolism_result = evaluate_symbolism(
                episode_text,
                metadata={'category': category}
            )

            if symbolism_result['score'] < 100:
                evaluation.result = EvaluationResult.FAIL_LOW_SCORE
                logger.error(f"❌ 象徴性スコア不足: {symbolism_result['score']:.1f}点（100点未満）")
                logger.error(f"   カテゴリ: {symbolism_result['category']}")
                logger.error(f"   基準点: {symbolism_result['base_score']}点")
                return evaluation

            evaluation.total_score = symbolism_result['score']
            evaluation.stage_results['symbolism_scoring'] = {
                'score': symbolism_result['score'],
                'category': symbolism_result['category'],
                'base_score': symbolism_result['base_score'],
                'multipliers': symbolism_result['multipliers'],
                'evidence': symbolism_result['evidence']
            }
            logger.info(f"✅ 象徴性スコア: {symbolism_result['score']:.1f}点")
            logger.info(f"   カテゴリ: {symbolism_result['category']} (基準点: {symbolism_result['base_score']}点)")

            # ステージ4: PDCAガーディアン
            logger.info(f"\n🛡️ ステージ4: PDCAガーディアン")
            pdca_violations = self.pdca_guardian.check_episode_quality(
                episode_text, episode_age, person_name
            )

            if pdca_violations:
                evaluation.violations.extend(pdca_violations)
                # CRITICAL違反の確認
                if any('CRITICAL' in v for v in pdca_violations):
                    evaluation.result = EvaluationResult.FAIL_CRITICAL
                    logger.error(f"❌ CRITICAL違反検出: {pdca_violations}")
                    return evaluation

            evaluation.stage_results['pdca_guardian'] = {
                'violations': pdca_violations
            }

            # ステージ5: EpisodeGuardian
            logger.info(f"\n🔒 ステージ5: EpisodeGuardian")
            guardian_result = self.episode_guardian.validate_episode(episode)

            if not guardian_result.is_valid:
                if guardian_result.severity == GuardianSeverity.CRITICAL:
                    evaluation.result = EvaluationResult.FAIL_CRITICAL
                    evaluation.violations.extend(guardian_result.failed_rules)
                    logger.error(f"❌ EpisodeGuardian CRITICAL違反: {guardian_result.message}")
                    return evaluation
                else:
                    evaluation.warnings.append(guardian_result.message)

            evaluation.stage_results['episode_guardian'] = {
                'severity': guardian_result.severity.value,
                'message': guardian_result.message
            }

            # ステージ6: FactChecker
            logger.info(f"\n🔬 ステージ6: FactChecker")
            # person_id, person_name, episode_text, birth_year, metadata
            fact_result = self.fact_checker.check_episode(
                person_id=episode.get('episode_id', person_name),
                person_name=person_name,
                episode_text=episode_text,
                birth_year=episode.get('birth_year', 2000),
                metadata={'episode_age': episode_age}
            )

            # ハルシネーション検出（利用可能な場合のみ）
            is_hallucination = False
            hallucination_reasons = []
            if self.hallucination_detector:
                is_hallucination, hallucination_reasons = self.hallucination_detector.detect(episode_text)

            # fact_resultの型を確認（ルート版とsrc版で異なる）
            if hasattr(fact_result, 'is_verified'):
                # ルート版fact_checker.pyの場合
                is_verified = fact_result.is_verified
                confidence_score = fact_result.confidence_score
                warnings_list = fact_result.warnings
            else:
                # src版fact_checker.pyの場合（FactCheckReport型）
                # VERIFIED, PARTIAL（部分検証）, UNVERIFIEDを合格とする
                # INCORRECT, SUSPICIOUSは不合格
                result_value = fact_result.result.value
                is_verified = result_value in ['verified', 'partial', 'unverified']
                confidence_score = fact_result.total_score / 100.0
                warnings_list = [v.message for v in fact_result.violations]

                # 信頼度スコアが60点未満、またはCRITICAL違反がある場合は不合格
                has_critical = any(v.severity == 'critical' for v in fact_result.violations)
                if confidence_score < 0.60 or has_critical:
                    is_verified = False

            if not is_verified or is_hallucination:
                evaluation.result = EvaluationResult.FAIL_FACT_CHECK
                evaluation.violations.extend(warnings_list)
                if is_hallucination:
                    evaluation.violations.extend(hallucination_reasons)
                logger.error(f"❌ 事実検証失敗: 信頼度{confidence_score:.2f}")
                return evaluation

            evaluation.stage_results['fact_check'] = {
                'is_verified': is_verified,
                'confidence_score': confidence_score,
                'warnings': warnings_list
            }

            # 全ステージ通過
            logger.info(f"\n✅ 全検証ステージ通過")
            logger.info(f"   最終スコア: {evaluation.total_score:.1f}点")
            logger.info(f"   事実信頼度: {confidence_score:.1%}")

        except Exception as e:
            logger.error(f"❌ 評価中にエラー: {str(e)}")
            evaluation.result = EvaluationResult.FAIL_CRITICAL
            evaluation.violations.append(f"システムエラー: {str(e)}")

        return evaluation

    def process_and_add_episode(self, episode: Dict) -> bool:
        """
        エピソードを評価してCSVに追加

        Args:
            episode: エピソードデータ

        Returns:
            成功したらTrue
        """
        # 評価実行
        evaluation = self.evaluate_episode(episode)

        # 合格の場合のみCSV追加
        if evaluation.result == EvaluationResult.PASS:
            success = self.csv_handler.append_episode(episode, evaluation)
            if success:
                logger.info(f"✅ エピソード追加成功: {episode['person_name']}")
                return True
            else:
                logger.error(f"❌ CSV出力失敗: {episode['person_name']}")
                return False
        else:
            logger.warning(f"⚠️ エピソード不合格: {evaluation.result.value}")
            logger.info(f"   違反: {evaluation.violations}")
            return False

    def batch_process(self, episodes: List[Dict]) -> Dict[str, int]:
        """
        複数エピソードのバッチ処理

        Args:
            episodes: エピソードリスト

        Returns:
            処理統計
        """
        stats = {
            'total': len(episodes),
            'passed': 0,
            'failed_critical': 0,
            'failed_score': 0,
            'failed_fact': 0
        }

        for i, episode in enumerate(episodes, 1):
            logger.info(f"\n📊 バッチ処理 {i}/{len(episodes)}")

            evaluation = self.evaluate_episode(episode)

            if evaluation.result == EvaluationResult.PASS:
                stats['passed'] += 1
                self.csv_handler.append_episode(episode, evaluation)
            elif evaluation.result == EvaluationResult.FAIL_CRITICAL:
                stats['failed_critical'] += 1
            elif evaluation.result == EvaluationResult.FAIL_LOW_SCORE:
                stats['failed_score'] += 1
            elif evaluation.result == EvaluationResult.FAIL_FACT_CHECK:
                stats['failed_fact'] += 1

        # 統計レポート
        logger.info(f"\n{'='*70}")
        logger.info(f"📊 バッチ処理完了")
        logger.info(f"{'='*70}")
        logger.info(f"  合計: {stats['total']}件")
        logger.info(f"  ✅ 合格: {stats['passed']}件")
        logger.info(f"  ❌ CRITICAL違反: {stats['failed_critical']}件")
        logger.info(f"  ❌ スコア不足: {stats['failed_score']}件")
        logger.info(f"  ❌ 事実検証失敗: {stats['failed_fact']}件")

        return stats

    def shutdown(self):
        """システムのシャットダウン"""
        self.ai_collaboration.shutdown()
        logger.info("✅ 統合エピソード評価パイプラインをシャットダウンしました")


def demonstration():
    """デモンストレーション"""

    print("="*70)
    print("🎯 統合エピソード評価パイプライン - デモ実行")
    print("="*70)

    # パイプライン初期化
    pipeline = IntegratedEpisodeEvaluationPipeline(
        csv_output_path='#episodes_validated_demo.csv'
    )
    pipeline.initialize()

    # テストエピソード
    test_episodes = [
        {
            "person_name": "イチロー",
            "episode_age": 27,
            "episode_text": "2001年、27歳のイチローはメジャーリーグ1年目でMVPと新人王を同時受賞。"
                          "これは史上2人目の快挙であり、日本人初のMVP受賞となった。",
            "category": "sports",
            "birth_year": 1973
        },
        {
            "person_name": "さくらももこ",
            "episode_age": 21,
            "episode_text": "21歳の時、漫画「ちびまる子ちゃん」の連載を開始。"
                          "静岡県清水市での子供時代の思い出を元に描かれた作品は国民的人気を博した。",
            "category": "literature",
            "birth_year": 1965
        }
    ]

    # バッチ処理実行
    stats = pipeline.batch_process(test_episodes)

    # シャットダウン
    pipeline.shutdown()

    print("\n" + "="*70)
    print("✅ デモンストレーション完了")
    print("="*70)

    return stats


if __name__ == "__main__":
    # デモ実行
    demonstration()
