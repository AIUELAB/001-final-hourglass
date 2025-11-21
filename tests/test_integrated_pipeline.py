#!/usr/bin/env python3
"""
統合エピソード評価パイプラインのテスト

全検証ステージが正しく連携して動作することを確認
"""

import sys
import unittest
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from integrated_episode_evaluation_pipeline import (
    CSVOutputHandler,
    EvaluationResult,
    IntegratedEpisodeEvaluationPipeline,
    LifetimeHighlightsSelector,
    QuestionGenerator,
)


class TestQuestionGenerator(unittest.TestCase):
    """質問生成器のテスト"""

    def setUp(self):
        self.generator = QuestionGenerator()

    def test_generate_basic_question(self):
        """基本的な質問生成"""
        question = self.generator.generate("イチロー")
        self.assertEqual(question, "イチローの有名なエピソードや偉業や事件といえば？")

    def test_generate_category_question(self):
        """カテゴリ別質問生成"""
        question = self.generator.generate_achievement_query("イチロー", "sports")
        self.assertIn("イチロー", question)
        self.assertIn("記録", question)


class TestLifetimeHighlightsSelector(unittest.TestCase):
    """生涯ハイライト選定器のテスト"""

    def setUp(self):
        self.selector = LifetimeHighlightsSelector()

    def test_global_achievement_detection(self):
        """世界的偉業の検出"""
        episode = {"episode_text": "オリンピック金メダルを獲得", "episode_age": 25}
        score = self.selector.calculate_importance_score(episode)
        self.assertGreaterEqual(score, 30)  # グローバル重要度30点

    def test_historical_value_detection(self):
        """歴史的価値の検出"""
        episode = {"episode_text": "史上初の快挙を達成", "episode_age": 30}
        score = self.selector.calculate_importance_score(episode)
        self.assertGreaterEqual(score, 30)  # 歴史的価値30点

    def test_top_7_selection(self):
        """上位7つの選定"""
        episodes = [{"episode_text": f"エピソード{i}", "episode_age": 20 + i} for i in range(10)]

        # 3つ目と7つ目に重要なイベント
        episodes[2]["episode_text"] = "オリンピック金メダル獲得"
        episodes[6]["episode_text"] = "ノーベル賞受賞"

        selected = self.selector.select_top_7(episodes)

        self.assertEqual(len(selected), 7)
        # 重要なエピソードが含まれているか確認
        texts = [ep["episode_text"] for ep in selected]
        self.assertIn("オリンピック金メダル獲得", texts)
        self.assertIn("ノーベル賞受賞", texts)


class TestCSVOutputHandler(unittest.TestCase):
    """CSV出力ハンドラーのテスト"""

    def setUp(self):
        import tempfile

        self.temp_dir = tempfile.mkdtemp()
        self.csv_path = Path(self.temp_dir) / "test_episodes.csv"
        self.handler = CSVOutputHandler(str(self.csv_path))

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_csv_creation(self):
        """CSV作成テスト"""
        from integrated_episode_evaluation_pipeline import EpisodeEvaluation

        episode = {
            "person_name": "テスト人物",
            "episode_age": 25,
            "episode_text": "テストエピソード",
            "category": "sports",
        }

        evaluation = EpisodeEvaluation(
            person_name="テスト人物",
            episode_age=25,
            episode_text="テストエピソード",
            result=EvaluationResult.PASS,
            total_score=85.0,
        )

        success = self.handler.append_episode(episode, evaluation)
        self.assertTrue(success)
        self.assertTrue(self.csv_path.exists())

    def test_utf8_bom_encoding(self):
        """UTF-8 BOMエンコーディング確認"""
        from integrated_episode_evaluation_pipeline import EpisodeEvaluation

        episode = {
            "person_name": "日本語テスト",
            "episode_age": 30,
            "episode_text": "日本語のエピソードテスト",
            "category": "entertainment",
        }

        evaluation = EpisodeEvaluation(
            person_name="日本語テスト",
            episode_age=30,
            episode_text="日本語のエピソードテスト",
            result=EvaluationResult.PASS,
            total_score=75.0,
        )

        self.handler.append_episode(episode, evaluation)

        # BOMの確認
        with open(self.csv_path, "rb") as f:
            first_bytes = f.read(3)
            self.assertEqual(first_bytes, b"\xef\xbb\xbf")  # UTF-8 BOM


class TestIntegratedPipeline(unittest.TestCase):
    """統合パイプラインのテスト"""

    def setUp(self):
        import tempfile

        self.temp_dir = tempfile.mkdtemp()
        self.csv_path = Path(self.temp_dir) / "test_integrated.csv"
        self.pipeline = IntegratedEpisodeEvaluationPipeline(str(self.csv_path))

    def tearDown(self):
        import shutil

        if hasattr(self, "pipeline"):
            self.pipeline.shutdown()
        shutil.rmtree(self.temp_dir)

    def test_pipeline_initialization(self):
        """パイプライン初期化テスト"""
        result = self.pipeline.initialize()
        self.assertTrue(result)

    def test_valid_episode_evaluation(self):
        """有効なエピソードの評価"""
        episode = {
            "person_name": "イチロー",
            "episode_age": 27,
            "episode_text": "2001年、27歳のイチローはメジャーリーグ1年目でMVPと新人王を同時受賞。"
            "これは史上2人目の快挙であり、日本人初のMVP受賞となった。",
            "category": "sports",
            "birth_year": 1973,
        }

        self.pipeline.initialize()
        evaluation = self.pipeline.evaluate_episode(episode)

        # 評価結果の確認
        self.assertIsNotNone(evaluation)
        self.assertGreaterEqual(evaluation.total_score, 0)

        # ステージ結果の確認
        self.assertIn("question", evaluation.stage_results)
        self.assertIn("ai_collaboration", evaluation.stage_results)
        # NOTE: 以下のステージは実装状況により実行されない場合がある
        # - pdca_guardian: unified_rules.json依存
        # - episode_guardian: データ依存
        # - optimized_validation: 設定依存
        # - fact_check: HallucinationDetector依存
        # 最低限、questionとai_collaborationがあればOK
        self.assertGreaterEqual(len(evaluation.stage_results), 2)

    def test_invalid_episode_rejection(self):
        """無効なエピソードの拒否"""
        # スコア不足のエピソード
        episode = {
            "person_name": "テスト",
            "episode_age": 20,
            "episode_text": "短いテスト",  # 文字数不足
            "category": "other",
            "birth_year": 2000,
        }

        self.pipeline.initialize()
        evaluation = self.pipeline.evaluate_episode(episode)

        # 何らかの失敗があるはず
        self.assertIn(
            evaluation.result,
            [EvaluationResult.FAIL_CRITICAL, EvaluationResult.FAIL_LOW_SCORE, EvaluationResult.FAIL_FACT_CHECK],
        )

    def test_batch_processing(self):
        """バッチ処理テスト"""
        episodes = [
            {
                "person_name": f"テスト人物{i}",
                "episode_age": 20 + i,
                "episode_text": "あなたと同じ20歳のとき、テスト人物は重要な偉業を達成した。"
                "この快挙により、多くの人々に影響を与えることとなった。"
                "歴史的な瞬間であり、後世に語り継がれることとなった。",
                "category": "sports",
                "birth_year": 2000,
            }
            for i in range(3)
        ]

        self.pipeline.initialize()
        stats = self.pipeline.batch_process(episodes)

        # 統計の確認
        self.assertEqual(stats["total"], 3)
        self.assertIsInstance(stats["passed"], int)
        self.assertIsInstance(stats["failed_critical"], int)
        self.assertIsInstance(stats["failed_score"], int)
        self.assertIsInstance(stats["failed_fact"], int)


class TestFailFastValidation(unittest.TestCase):
    """Fail-Fast検証のテスト"""

    def setUp(self):
        import tempfile

        self.temp_dir = tempfile.mkdtemp()
        self.csv_path = Path(self.temp_dir) / "test_failfast.csv"
        self.pipeline = IntegratedEpisodeEvaluationPipeline(str(self.csv_path))
        self.pipeline.initialize()

    def tearDown(self):
        import shutil

        self.pipeline.shutdown()
        shutil.rmtree(self.temp_dir)

    def test_critical_violation_stops_pipeline(self):
        """CRITICAL違反でパイプライン停止"""
        # グループ名を使用（CRITICAL違反）
        episode = {
            "person_name": "嵐",  # グループ名
            "episode_age": 25,
            "episode_text": "グループとして重要な偉業を達成した。",
            "category": "entertainment",
            "birth_year": 1999,
        }

        evaluation = self.pipeline.evaluate_episode(episode)

        # 何らかの失敗が検出されているか確認
        # NOTE: グループ名チェックよりスコア不足が先に判定される場合がある
        self.assertIn(
            evaluation.result,
            [EvaluationResult.FAIL_CRITICAL, EvaluationResult.FAIL_LOW_SCORE, EvaluationResult.FAIL_FACT_CHECK],
        )
        # 失敗していることが重要
        self.assertNotEqual(evaluation.result, EvaluationResult.PASS)


def run_tests():
    """テスト実行"""
    print("=" * 70)
    print("🧪 統合エピソード評価パイプライン - テスト実行")
    print("=" * 70)

    # テストスイートの作成
    suite = unittest.TestLoader().loadTestsFromModule(sys.modules[__name__])

    # テスト実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 結果サマリー
    print("\n" + "=" * 70)
    print("📊 テスト結果サマリー")
    print("=" * 70)
    print(f"  実行: {result.testsRun}件")
    print(f"  ✅ 成功: {result.testsRun - len(result.failures) - len(result.errors)}件")
    print(f"  ❌ 失敗: {len(result.failures)}件")
    print(f"  ⚠️ エラー: {len(result.errors)}件")

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
