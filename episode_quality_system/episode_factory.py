#!/usr/bin/env python3
"""
EpisodeFactory - エピソード生成統合システム
すべての品質システムを統合し、高品質なエピソードを生成
"""

import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path
import sys
from datetime import datetime

# 他のモジュールをインポート
sys.path.append(str(Path(__file__).parent))
from template_blocker import TemplateBlocker
from auto_fact_injector import AutoFactInjector
from quality_guardian_v2 import QualityGuardianV2, QualityLevel
from realtime_validator import RealTimeValidator, ValidationStatus


@dataclass
class EpisodeRequest:
    """エピソード生成リクエスト"""
    person_name: str
    age: int
    category: Optional[str] = None
    achievement_focus: Optional[str] = None  # 特定の実績にフォーカス


@dataclass
class EpisodeResponse:
    """エピソード生成レスポンス"""
    episode: str
    quality_score: int
    quality_level: str
    generation_time: float
    improvement_history: List[Dict]
    final_validation: Dict


class EpisodeFactory:
    """エピソード生成統合システム"""

    def __init__(self, facts_db_path: str = None):
        """
        初期化

        Args:
            facts_db_path: person_facts.jsonのパス
        """
        # 各システムを初期化
        self.template_blocker = TemplateBlocker()
        self.auto_fact_injector = AutoFactInjector(facts_db_path)
        self.quality_guardian = QualityGuardianV2()
        self.realtime_validator = RealTimeValidator()

        # 事実データベースを読み込み
        if facts_db_path is None:
            facts_db_path = Path(__file__).parent / "data" / "person_facts.json"
        self.facts_db = self._load_facts_database(facts_db_path)

        # 生成設定
        self.MAX_ITERATIONS = 5  # 最大改善回数
        self.TARGET_SCORE = 85   # 目標品質スコア

    def _load_facts_database(self, path: str) -> Dict:
        """
        事実データベースを読み込み

        Args:
            path: JSONファイルのパス

        Returns:
            事実データベース
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("persons", {})
        except FileNotFoundError:
            print(f"警告: {path} が見つかりません")
            return {}

    def generate_episode(self, request: EpisodeRequest) -> EpisodeResponse:
        """
        エピソードを生成

        Args:
            request: エピソード生成リクエスト

        Returns:
            エピソード生成レスポンス
        """
        start_time = datetime.now()
        improvement_history = []

        # 初期エピソードを生成
        episode = self._create_initial_episode(request)
        improvement_history.append({
            "iteration": 0,
            "type": "initial",
            "episode": episode,
            "score": 0
        })

        # 品質改善ループ
        for iteration in range(1, self.MAX_ITERATIONS + 1):
            # リアルタイム検証
            rt_validation = self.realtime_validator.validate_full_episode(episode)

            # ブロックレベルの違反があれば即座に修正
            if rt_validation["status"] == ValidationStatus.BLOCK:
                episode = self._fix_blocking_issues(episode, rt_validation)
                improvement_history.append({
                    "iteration": iteration,
                    "type": "block_fix",
                    "episode": episode,
                    "violations": rt_validation["violations"]
                })
                continue

            # 品質チェック
            quality_report = self.quality_guardian.check_quality(
                episode,
                request.person_name,
                request.age,
                auto_improve=True
            )

            improvement_history.append({
                "iteration": iteration,
                "type": "quality_check",
                "episode": episode,
                "score": quality_report.score,
                "level": quality_report.level.value
            })

            # 目標スコアに達したら終了
            if quality_report.score >= self.TARGET_SCORE:
                break

            # 改善されたエピソードがあれば使用
            if quality_report.improved_episode:
                episode = quality_report.improved_episode
            else:
                # 手動で改善を試みる
                episode = self._manual_improvement(
                    episode,
                    request.person_name,
                    request.age,
                    quality_report
                )

        # 最終検証
        final_validation = self._final_validation(episode)

        # 生成時間計算
        generation_time = (datetime.now() - start_time).total_seconds()

        return EpisodeResponse(
            episode=episode,
            quality_score=final_validation["score"],
            quality_level=final_validation["level"],
            generation_time=generation_time,
            improvement_history=improvement_history,
            final_validation=final_validation
        )

    def _create_initial_episode(self, request: EpisodeRequest) -> str:
        """
        初期エピソードを作成

        Args:
            request: リクエスト

        Returns:
            初期エピソード
        """
        if request.person_name not in self.facts_db:
            return f"あなたと同じ{request.age}歳のとき、{request.person_name}は活躍した。"

        person_data = self.facts_db[request.person_name]
        facts = person_data.get("facts", {})

        # カテゴリから適切な事実を選択
        selected_facts = []

        # 実績を優先
        if "achievements" in facts and facts["achievements"]:
            # 年齢に関連する実績を探す
            age_related = None
            for achievement in facts["achievements"]:
                if str(request.age) in achievement:
                    age_related = achievement
                    break

            if age_related:
                selected_facts.append(age_related)
            else:
                # 最も重要そうな実績を選択
                selected_facts.append(facts["achievements"][0])

        # 数値データを追加
        if "numbers" in facts and facts["numbers"] and len(selected_facts) < 2:
            selected_facts.append(facts["numbers"][0])

        # エピソードを構築
        if selected_facts:
            main_fact = selected_facts[0]
            additional_facts = selected_facts[1:] if len(selected_facts) > 1 else []

            episode = f"あなたと同じ{request.age}歳のとき、{request.person_name}は{main_fact}"

            for fact in additional_facts:
                episode += f"また{fact}"

            # 句点で終了
            if not episode.endswith("。"):
                episode += "。"

            return episode

        return f"あなたと同じ{request.age}歳のとき、{request.person_name}は重要な成果を残した。"

    def _fix_blocking_issues(self, episode: str, validation: Dict) -> str:
        """
        ブロッキング問題を修正

        Args:
            episode: エピソード
            validation: 検証結果

        Returns:
            修正されたエピソード
        """
        fixed = episode

        for violation in validation["violations"]:
            if violation["status"] == ValidationStatus.BLOCK:
                # 定型文を削除
                if "その後も" in violation["message"]:
                    fixed = re.sub(r'その後も[^。]*。?', '', fixed)
                elif "多くの" in violation["message"]:
                    fixed = re.sub(r'多くの[^。]*影響[^。]*。?', '', fixed)
                elif "日付" in violation["message"] or "時刻" in violation["message"]:
                    # 日付・時刻を削除
                    fixed = re.sub(r'\d{4}年\d{1,2}月\d{1,2}日', '', fixed)
                    fixed = re.sub(r'午[前後]\d+時\d*分?', '', fixed)

        # 余分なスペースを削除
        fixed = re.sub(r'\s+', '', fixed)

        return fixed

    def _manual_improvement(self, episode: str, person_name: str,
                          age: int, quality_report) -> str:
        """
        手動で改善

        Args:
            episode: エピソード
            person_name: 人物名
            age: 年齢
            quality_report: 品質レポート

        Returns:
            改善されたエピソード
        """
        # 文字数が不足している場合、事実を注入
        if len(episode) < 132:
            improved, _ = self.auto_fact_injector.inject_facts(
                episode, person_name, age
            )
            return improved

        # 主観的表現を削除
        subjective_terms = ["素晴らしい", "凄い", "驚くべき", "感動的"]
        for term in subjective_terms:
            episode = episode.replace(term, "")

        # 曖昧表現を具体化（可能な限り）
        episode = re.sub(r'多くの', '', episode)
        episode = re.sub(r'様々な', '', episode)

        # 名詞終了を修正
        if re.search(r'(革命児|先駆者|巨人|天才|レジェンド)。$', episode):
            episode = re.sub(r'(革命児|先駆者|巨人|天才|レジェンド)。$',
                            r'\1となった。', episode)

        return episode

    def _final_validation(self, episode: str) -> Dict:
        """
        最終検証

        Args:
            episode: エピソード

        Returns:
            検証結果
        """
        # すべてのシステムで最終チェック
        validation = {
            "episode": episode,
            "length": len(episode),
            "score": 0,
            "level": "unknown",
            "checks": {}
        }

        # Template Blocker
        should_block, violations = self.template_blocker.check_episode(episode)
        validation["checks"]["template_blocker"] = {
            "passed": not should_block,
            "violations": len(violations)
        }

        # RealTime Validator
        rt_validation = self.realtime_validator.validate_full_episode(episode)
        validation["checks"]["realtime_validator"] = {
            "passed": rt_validation["is_valid"],
            "status": rt_validation["status"].value,
            "violations": len(rt_validation["violations"])
        }

        # Quality Guardian
        quality_report = self.quality_guardian.check_quality(
            episode, auto_improve=False
        )
        validation["score"] = quality_report.score
        validation["level"] = quality_report.level.value
        validation["checks"]["quality_guardian"] = {
            "score": quality_report.score,
            "level": quality_report.level.value
        }

        # 総合判定
        validation["overall_pass"] = (
            not should_block and
            rt_validation["is_valid"] and
            quality_report.score >= 70
        )

        return validation

    def batch_generate(self, requests: List[EpisodeRequest]) -> List[EpisodeResponse]:
        """
        複数エピソードを一括生成

        Args:
            requests: リクエストのリスト

        Returns:
            レスポンスのリスト
        """
        responses = []
        for request in requests:
            response = self.generate_episode(request)
            responses.append(response)
        return responses

    def get_generation_report(self, responses: List[EpisodeResponse]) -> Dict:
        """
        生成レポートを取得

        Args:
            responses: レスポンスのリスト

        Returns:
            レポート
        """
        if not responses:
            return {}

        total = len(responses)
        avg_score = sum(r.quality_score for r in responses) / total
        avg_time = sum(r.generation_time for r in responses) / total

        level_counts = {}
        for response in responses:
            level = response.quality_level
            level_counts[level] = level_counts.get(level, 0) + 1

        return {
            "total_generated": total,
            "average_score": avg_score,
            "average_time": avg_time,
            "level_distribution": level_counts,
            "success_rate": sum(1 for r in responses if r.quality_score >= 70) / total * 100
        }


def test_episode_factory():
    """テスト実行"""
    factory = EpisodeFactory()

    # テストリクエスト
    test_requests = [
        EpisodeRequest(person_name="大谷翔平", age=25),
        EpisodeRequest(person_name="松井秀喜", age=31),
        EpisodeRequest(person_name="イチロー", age=27),
        EpisodeRequest(person_name="未知の人物", age=30)  # データベースにない人物
    ]

    responses = []

    for i, request in enumerate(test_requests, 1):
        print(f"\n{'='*60}")
        print(f"テストケース {i}: {request.person_name} ({request.age}歳)")

        # エピソード生成
        response = factory.generate_episode(request)
        responses.append(response)

        print(f"\n生成されたエピソード:")
        print(f"  {response.episode}")
        print(f"\n品質スコア: {response.quality_score}/100 ({response.quality_level})")
        print(f"生成時間: {response.generation_time:.2f}秒")

        # 改善履歴
        print(f"\n改善履歴:")
        for history in response.improvement_history:
            if "score" in history:
                print(f"  Iteration {history['iteration']}: "
                      f"Score={history['score']}, Type={history['type']}")

        # 最終検証結果
        print(f"\n最終検証:")
        for system, result in response.final_validation["checks"].items():
            status = "✅" if result.get("passed", result.get("score", 0) >= 70) else "❌"
            print(f"  {system}: {status}")

    # 生成レポート
    print(f"\n{'='*60}")
    print("生成レポート:")
    report = factory.get_generation_report(responses)
    print(f"  総生成数: {report['total_generated']}")
    print(f"  平均スコア: {report['average_score']:.1f}")
    print(f"  平均生成時間: {report['average_time']:.2f}秒")
    print(f"  成功率: {report['success_rate']:.1f}%")
    print(f"  品質レベル分布:")
    for level, count in report['level_distribution'].items():
        print(f"    {level}: {count}")


if __name__ == "__main__":
    test_episode_factory()