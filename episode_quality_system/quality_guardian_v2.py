#!/usr/bin/env python3
"""
QualityGuardianV2 - 品質保証エンジンV2
すべての品質基準を統合的にチェックし、エピソードを改善
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
import sys

# 他のモジュールをインポート
sys.path.append(str(Path(__file__).parent))
from template_blocker import TemplateBlocker, ViolationType
from auto_fact_injector import AutoFactInjector


class QualityLevel(Enum):
    """品質レベル"""
    EXCELLENT = "excellent"  # 90-100点
    GOOD = "good"           # 70-89点
    ACCEPTABLE = "acceptable"  # 50-69点
    POOR = "poor"           # 30-49点
    REJECT = "reject"       # 0-29点


@dataclass
class QualityReport:
    """品質レポート"""
    score: int
    level: QualityLevel
    violations: List[Dict]
    suggestions: List[str]
    improved_episode: Optional[str] = None
    metrics: Dict = None


class QualityGuardianV2:
    """品質保証エンジンV2"""

    def __init__(self):
        """初期化"""
        self.template_blocker = TemplateBlocker()
        self.auto_fact_injector = AutoFactInjector()

        # 品質スコアリング設定
        self.scoring_weights = {
            "no_template": 30,      # 定型文なし
            "has_facts": 25,        # 事実あり
            "correct_length": 15,   # 適切な文字数
            "no_noun_ending": 10,   # 名詞終了なし
            "no_date_noise": 10,    # 日付ノイズなし
            "specific": 5,          # 具体的
            "objective": 5          # 客観的
        }

        # PDCA Guardian準拠の文字数
        self.MIN_LENGTH = 132
        self.MAX_LENGTH = 250
        self.IDEAL_LENGTH = 180

    def check_quality(self, episode_text: str, person_name: str = None,
                     age: int = None, auto_improve: bool = True) -> QualityReport:
        """
        エピソードの品質をチェック

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名（改善用）
            age: 年齢（改善用）
            auto_improve: 自動改善を行うか

        Returns:
            品質レポート
        """
        # 初期スコア
        score = 100
        violations = []
        suggestions = []
        improved_episode = None

        # メトリクス収集
        metrics = {
            "length": len(episode_text),
            "has_template": False,
            "has_facts": False,
            "has_noun_ending": False,
            "has_date_noise": False,
            "is_specific": False,
            "is_objective": False
        }

        # 1. TemplateBlockerでチェック
        should_block, template_violations = self.template_blocker.check_episode(episode_text)

        for violation in template_violations:
            # 違反タイプごとにスコア減点
            if violation.type == ViolationType.TEMPLATE:
                score -= 10
                metrics["has_template"] = True
            elif violation.type == ViolationType.NOUN_ENDING:
                score -= 5
                metrics["has_noun_ending"] = True
            elif violation.type == ViolationType.DATE_NOISE:
                score -= 5
                metrics["has_date_noise"] = True
            elif violation.type in [ViolationType.SUBJECTIVE, ViolationType.VAGUE]:
                score -= 3

            violations.append({
                "type": violation.type.value,
                "text": violation.matched_text,
                "severity": violation.severity,
                "suggestion": violation.suggestion
            })

        # 2. 文字数チェック
        length = len(episode_text)
        if length < self.MIN_LENGTH:
            score -= 15
            violations.append({
                "type": "文字数不足",
                "text": f"{length}文字",
                "severity": "critical",
                "suggestion": f"最低{self.MIN_LENGTH}文字必要（現在{length}文字）"
            })
        elif length > self.MAX_LENGTH:
            score -= 10
            violations.append({
                "type": "文字数超過",
                "text": f"{length}文字",
                "severity": "major",
                "suggestion": f"最大{self.MAX_LENGTH}文字まで（現在{length}文字）"
            })
        else:
            # 理想的な長さに近いほど高得点
            length_diff = abs(self.IDEAL_LENGTH - length)
            if length_diff < 20:
                score += 5  # ボーナス

        # 3. 事実の存在チェック
        fact_patterns = [
            r'\d+[年本回個]',       # 数値＋単位
            r'\d+[\.\,]\d+',        # 小数点・カンマ付き数値
            r'「[^」]+」',          # タイトル
            r'優勝|受賞|達成|記録|獲得|樹立',  # 実績キーワード
            r'MVP|賞|タイトル|王',  # 称号
        ]

        has_facts = False
        for pattern in fact_patterns:
            if re.search(pattern, episode_text):
                has_facts = True
                break

        if has_facts:
            metrics["has_facts"] = True
        else:
            score -= 20
            violations.append({
                "type": "事実不足",
                "text": "具体的な事実・数値なし",
                "severity": "critical",
                "suggestion": "具体的な記録、数値、実績を含める"
            })

        # 4. 具体性チェック
        vague_terms = ["多く", "たくさん", "様々", "いくつも", "幅広い"]
        vague_count = sum(1 for term in vague_terms if term in episode_text)
        if vague_count == 0:
            metrics["is_specific"] = True
        else:
            score -= vague_count * 2

        # 5. 客観性チェック
        subjective_terms = ["素晴らしい", "凄い", "驚くべき", "感動的", "見事な"]
        subjective_count = sum(1 for term in subjective_terms if term in episode_text)
        if subjective_count == 0:
            metrics["is_objective"] = True
        else:
            score -= subjective_count * 3

        # 6. 自動改善
        if auto_improve and person_name and score < 70:
            improved_episode = self._improve_episode(
                episode_text, person_name, age, violations
            )

            # 改善後の再評価
            if improved_episode and improved_episode != episode_text:
                # 改善版を再チェック（無限ループ防止のため auto_improve=False）
                improved_report = self.check_quality(
                    improved_episode, person_name, age, auto_improve=False
                )

                if improved_report.score > score:
                    # 改善成功
                    suggestions.append(f"自動改善により品質スコアが {score} → {improved_report.score} に向上")
                    improved_episode = improved_episode
                else:
                    # 改善失敗
                    improved_episode = None

        # レベル判定
        level = self._determine_level(score)

        # 提案作成
        if not suggestions:
            suggestions = self._generate_suggestions(violations, metrics)

        return QualityReport(
            score=max(0, min(100, score)),  # 0-100の範囲に制限
            level=level,
            violations=violations,
            suggestions=suggestions,
            improved_episode=improved_episode,
            metrics=metrics
        )

    def _determine_level(self, score: int) -> QualityLevel:
        """
        スコアから品質レベルを判定

        Args:
            score: スコア（0-100）

        Returns:
            品質レベル
        """
        if score >= 90:
            return QualityLevel.EXCELLENT
        elif score >= 70:
            return QualityLevel.GOOD
        elif score >= 50:
            return QualityLevel.ACCEPTABLE
        elif score >= 30:
            return QualityLevel.POOR
        else:
            return QualityLevel.REJECT

    def _improve_episode(self, episode: str, person_name: str,
                        age: int, violations: List[Dict]) -> Optional[str]:
        """
        エピソードを自動改善

        Args:
            episode: エピソード
            person_name: 人物名
            age: 年齢
            violations: 違反リスト

        Returns:
            改善されたエピソード（改善できない場合はNone）
        """
        improved = episode

        # 定型文や不足がある場合、事実を注入
        has_critical_violations = any(
            v["severity"] == "critical" for v in violations
        )

        if has_critical_violations and person_name:
            # AutoFactInjectorで改善
            improved, facts_used = self.auto_fact_injector.inject_facts(
                improved, person_name, age
            )

        # 名詞終了の修正
        noun_endings = ['革命児', '先駆者', '開拓者', 'レジェンド', 'カリスマ']
        for noun in noun_endings:
            if improved.rstrip('。').endswith(noun):
                improved = improved.rstrip('。').rstrip(noun)
                improved += f"{noun}となった。"

        # 日付ノイズの削除
        date_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',
            r'\d{1,2}月\d{1,2}日',
            r'午前\d+時',
            r'午後\d+時',
            r'\d+時\d+分'
        ]
        for pattern in date_patterns:
            improved = re.sub(pattern, '', improved)

        # 余分なスペースを削除
        improved = re.sub(r'\s+', '', improved)

        # 文末が句点で終わることを確認
        if improved and not improved.endswith('。'):
            improved += '。'

        return improved if improved != episode else None

    def _generate_suggestions(self, violations: List[Dict],
                             metrics: Dict) -> List[str]:
        """
        改善提案を生成

        Args:
            violations: 違反リスト
            metrics: メトリクス

        Returns:
            提案リスト
        """
        suggestions = []

        # 重大な違反から優先的に提案
        critical_violations = [v for v in violations if v["severity"] == "critical"]
        major_violations = [v for v in violations if v["severity"] == "major"]

        if critical_violations:
            suggestions.append("🔴 重大な問題を最優先で修正してください:")
            for v in critical_violations[:3]:  # 上位3件
                suggestions.append(f"  • {v['type']}: {v['suggestion']}")

        if major_violations:
            suggestions.append("🟡 以下の問題も修正が必要です:")
            for v in major_violations[:3]:  # 上位3件
                suggestions.append(f"  • {v['type']}: {v['suggestion']}")

        # 一般的な改善提案
        if not metrics.get("has_facts"):
            suggestions.append("💡 具体的な数値、記録、実績を追加してください")

        if metrics.get("length", 0) < self.MIN_LENGTH:
            suggestions.append(f"💡 文字数を{self.MIN_LENGTH}文字以上に増やしてください")

        if not metrics.get("is_objective"):
            suggestions.append("💡 主観的な表現を客観的な事実に置き換えてください")

        return suggestions

    def batch_check(self, episodes: List[Dict]) -> List[QualityReport]:
        """
        複数エピソードを一括チェック

        Args:
            episodes: エピソードリスト [{text, person_name, age}, ...]

        Returns:
            品質レポートのリスト
        """
        reports = []

        for episode_data in episodes:
            report = self.check_quality(
                episode_data.get("text", ""),
                episode_data.get("person_name"),
                episode_data.get("age"),
                auto_improve=True
            )
            reports.append(report)

        return reports

    def get_summary_report(self, reports: List[QualityReport]) -> Dict:
        """
        サマリーレポートを生成

        Args:
            reports: 品質レポートのリスト

        Returns:
            サマリー辞書
        """
        total = len(reports)
        if total == 0:
            return {}

        summary = {
            "total": total,
            "average_score": sum(r.score for r in reports) / total,
            "level_distribution": {
                QualityLevel.EXCELLENT.value: 0,
                QualityLevel.GOOD.value: 0,
                QualityLevel.ACCEPTABLE.value: 0,
                QualityLevel.POOR.value: 0,
                QualityLevel.REJECT.value: 0
            },
            "common_violations": {},
            "improvement_rate": 0
        }

        # レベル分布
        for report in reports:
            summary["level_distribution"][report.level.value] += 1

        # 共通違反の集計
        violation_counts = {}
        for report in reports:
            for violation in report.violations:
                vtype = violation["type"]
                violation_counts[vtype] = violation_counts.get(vtype, 0) + 1

        summary["common_violations"] = dict(
            sorted(violation_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        )

        # 改善率
        improved_count = sum(1 for r in reports if r.improved_episode)
        summary["improvement_rate"] = (improved_count / total) * 100 if total > 0 else 0

        return summary


def test_quality_guardian():
    """テスト実行"""
    guardian = QualityGuardianV2()

    # テストケース
    test_episodes = [
        {
            "text": "あなたと同じ25歳のとき、彼は素晴らしい功績を残した。その後も活躍を続け、多くの人に影響を与えた革命児。",
            "person_name": "大谷翔平",
            "age": 25,
            "description": "定型文・主観的表現・名詞終了"
        },
        {
            "text": "あなたと同じ30歳のとき、大谷翔平は44本塁打を記録し、同時に10勝も達成した。",
            "person_name": "大谷翔平",
            "age": 30,
            "description": "短いが事実あり"
        },
        {
            "text": "あなたと同じ31歳のとき、松井秀喜はヤンキースで31本塁打を記録し、日本人野手として初めて100打点を達成した。この年のワールドシリーズではMVPを獲得し、日本人初の快挙となった。",
            "person_name": "松井秀喜",
            "age": 31,
            "description": "良質なエピソード"
        }
    ]

    reports = []
    for i, episode_data in enumerate(test_episodes, 1):
        print(f"\n{'='*60}")
        print(f"テストケース {i}: {episode_data['description']}")
        print(f"元のエピソード: {episode_data['text']}")
        print(f"文字数: {len(episode_data['text'])}")

        # 品質チェック
        report = guardian.check_quality(
            episode_data["text"],
            episode_data.get("person_name"),
            episode_data.get("age"),
            auto_improve=True
        )
        reports.append(report)

        print(f"\n品質スコア: {report.score}/100 ({report.level.value})")

        if report.violations:
            print(f"\n違反検出:")
            for v in report.violations[:5]:  # 上位5件
                severity_mark = {"critical": "🔴", "major": "🟡", "minor": "🟢"}.get(v["severity"], "")
                print(f"  {severity_mark} [{v['type']}] {v['text'][:30]}...")

        if report.suggestions:
            print(f"\n改善提案:")
            for suggestion in report.suggestions:
                print(f"  {suggestion}")

        if report.improved_episode:
            print(f"\n改善後のエピソード:")
            print(f"  {report.improved_episode}")
            print(f"  文字数: {len(report.improved_episode)}")

    # サマリーレポート
    print(f"\n{'='*60}")
    print("サマリーレポート")
    summary = guardian.get_summary_report(reports)
    print(f"  総エピソード数: {summary['total']}")
    print(f"  平均スコア: {summary['average_score']:.1f}")
    print(f"  品質レベル分布:")
    for level, count in summary['level_distribution'].items():
        print(f"    {level}: {count}")
    print(f"  改善率: {summary['improvement_rate']:.1f}%")
    if summary['common_violations']:
        print(f"  頻出違反:")
        for vtype, count in summary['common_violations'].items():
            print(f"    {vtype}: {count}件")


if __name__ == "__main__":
    test_quality_guardian()
