#!/usr/bin/env python3
"""
RULE_181: 品質レポート生成（Quality Report Generator）

RULE_179の評価結果とRULE_180の改善結果を統合して包括的な品質レポートを生成
- 評価サマリー（合格/不合格、総合スコア）
- ルール別詳細分析
- 改善提案と自動修正内容
- 視覚的なスコア表示
- エクスポート機能（JSON、Markdown、HTML）

レポート構成:
1. Executive Summary - 総合評価サマリー
2. Rule-by-Rule Analysis - ルール別詳細分析
3. Improvement Actions - 改善アクション一覧
4. Statistical Overview - 統計的概観
5. Recommendations - 推奨事項
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class QualityMetrics:
    """品質メトリクス"""
    total_score: float
    passed_rules: int
    failed_rules: int
    critical_issues: int
    warnings: int
    improvements_applied: int
    quality_grade: str  # S, A, B, C, D, F


class QualityReportGenerator:
    """
    品質レポート生成エンジン

    RULE_179とRULE_180の結果を統合して包括的なレポートを生成
    """

    # 品質グレード基準
    GRADE_THRESHOLDS = {
        'S': 90.0,
        'A': 80.0,
        'B': 70.0,
        'C': 60.0,
        'D': 50.0,
        'F': 0.0
    }

    # ルールの重要度
    RULE_PRIORITIES = {
        'RULE_172': 'HIGH',      # 社会的インパクト
        'RULE_173': 'MEDIUM',    # 年齢選択
        'RULE_174': 'CRITICAL',  # 時系列整合性
        'RULE_175': 'CRITICAL',  # ネガティブ評価
        'RULE_176': 'HIGH',      # 架空キャラクター
        'RULE_177': 'MEDIUM',    # 抽象表現
        'RULE_178': 'LOW',       # MCPコレクター
    }

    def __init__(self):
        """初期化"""
        self.report_timestamp = datetime.now().isoformat()

    def generate_report(
        self,
        episode_id: str,
        person_name: str,
        episode_text: str,
        evaluation_result: Dict[str, Any],
        improvement_summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        包括的な品質レポートを生成

        Args:
            episode_id: エピソードID
            person_name: 人物名
            episode_text: エピソードテキスト
            evaluation_result: RULE_179の評価結果
            improvement_summary: RULE_180の改善サマリー

        Returns:
            包括的な品質レポート
        """
        logger.info(f"📊 品質レポート生成開始: {episode_id}")

        # 1. Executive Summary
        executive_summary = self._generate_executive_summary(
            evaluation_result, improvement_summary
        )

        # 2. Rule-by-Rule Analysis
        rule_analysis = self._generate_rule_analysis(evaluation_result)

        # 3. Improvement Actions
        improvement_actions = self._generate_improvement_section(improvement_summary)

        # 4. Statistical Overview
        statistical_overview = self._generate_statistics(
            evaluation_result, improvement_summary
        )

        # 5. Recommendations
        recommendations = self._generate_recommendations(
            evaluation_result, improvement_summary
        )

        report = {
            "report_metadata": {
                "episode_id": episode_id,
                "person_name": person_name,
                "episode_text": episode_text,
                "generated_at": self.report_timestamp,
                "report_version": "1.0"
            },
            "executive_summary": executive_summary,
            "rule_analysis": rule_analysis,
            "improvement_actions": improvement_actions,
            "statistical_overview": statistical_overview,
            "recommendations": recommendations,
            "raw_evaluation": evaluation_result,
            "raw_improvement": improvement_summary
        }

        logger.info(f"✅ 品質レポート生成完了")
        return report

    def _generate_executive_summary(
        self,
        evaluation: Dict[str, Any],
        improvement: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Executive Summaryを生成

        Args:
            evaluation: 評価結果
            improvement: 改善サマリー

        Returns:
            Executive Summary
        """
        total_score = evaluation.get("total_score", 0)
        passed = evaluation.get("passed", False)
        quality_gates = evaluation.get("quality_gates", {})

        # 品質グレード計算
        grade = self._calculate_grade(total_score)

        # 合格/不合格ルール数
        passed_rules = sum(1 for passed in quality_gates.values() if passed)
        failed_rules = len(quality_gates) - passed_rules

        # 重大度別カウント
        critical_issues = 0
        warnings = 0

        if evaluation.get("temporal_consistency"):
            inconsistencies = evaluation["temporal_consistency"].get("inconsistencies", [])
            for issue in inconsistencies:
                if issue.get("severity") == "CRITICAL":
                    critical_issues += 1
                else:
                    warnings += 1

        if evaluation.get("negative_evaluation"):
            issues = evaluation["negative_evaluation"].get("issues", [])
            for issue in issues:
                if issue.get("severity") == "CRITICAL":
                    critical_issues += 1
                else:
                    warnings += 1

        # 改善適用数
        improvements_applied = 0
        if improvement:
            improvements_applied = improvement.get("total_improvements", 0)

        return {
            "overall_status": "✅ 合格" if passed else "❌ 不合格",
            "total_score": total_score,
            "quality_grade": grade,
            "passed_rules": passed_rules,
            "failed_rules": failed_rules,
            "critical_issues": critical_issues,
            "warnings": warnings,
            "improvements_applied": improvements_applied,
            "verdict": self._generate_verdict(grade, passed, critical_issues)
        }

    def _calculate_grade(self, score: float) -> str:
        """
        スコアから品質グレードを計算

        Args:
            score: 総合スコア

        Returns:
            品質グレード (S, A, B, C, D, F)
        """
        for grade, threshold in self.GRADE_THRESHOLDS.items():
            if score >= threshold:
                return grade
        return 'F'

    def _generate_verdict(self, grade: str, passed: bool, critical_issues: int) -> str:
        """
        総合判定文を生成

        Args:
            grade: 品質グレード
            passed: 合格/不合格
            critical_issues: 重大問題数

        Returns:
            判定文
        """
        if grade in ['S', 'A'] and passed and critical_issues == 0:
            return "優秀な品質。本番環境へのデプロイ推奨。"
        elif grade == 'B' and passed and critical_issues == 0:
            return "良好な品質。軽微な改善後にデプロイ可能。"
        elif grade == 'C' and critical_issues == 0:
            return "最低限の品質基準を満たしているが、改善推奨。"
        elif critical_issues > 0:
            return f"重大問題{critical_issues}件あり。修正必須。"
        else:
            return "品質基準未達。大幅な改善が必要。"

    def _generate_rule_analysis(self, evaluation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        ルール別詳細分析を生成

        Args:
            evaluation: 評価結果

        Returns:
            ルール別分析リスト
        """
        analysis = []
        quality_gates = evaluation.get("quality_gates", {})

        # RULE_172: 社会的インパクト
        if "social_impact" in evaluation:
            social = evaluation["social_impact"]
            analysis.append({
                "rule_id": "RULE_172",
                "rule_name": "社会的インパクト評価",
                "priority": self.RULE_PRIORITIES.get("RULE_172", "MEDIUM"),
                "passed": quality_gates.get("social_impact", False),
                "score": social.get("impact_score", 0),
                "details": {
                    "search_volume": social.get("search_volume_score", 0),
                    "wikipedia_languages": social.get("wikipedia_languages", 0),
                    "news_articles": social.get("news_articles_count", 0),
                    "social_buzz": social.get("social_buzz_score", 0)
                },
                "message": f"インパクトスコア: {social.get('impact_score', 0)}点"
            })

        # RULE_173: 年齢選択
        if "age_flexibility" in evaluation:
            age = evaluation["age_flexibility"]
            analysis.append({
                "rule_id": "RULE_173",
                "rule_name": "年齢選択の柔軟性",
                "priority": self.RULE_PRIORITIES.get("RULE_173", "MEDIUM"),
                "passed": quality_gates.get("age_flexibility", False),
                "score": 100 if age.get("passed", False) else 0,
                "details": {
                    "selected_age": age.get("selected_age"),
                    "alternatives": age.get("alternative_ages", [])
                },
                "message": f"選択年齢: {age.get('selected_age')}歳"
            })

        # RULE_174: 時系列整合性
        if "temporal_consistency" in evaluation:
            temporal = evaluation["temporal_consistency"]
            inconsistencies = temporal.get("inconsistencies", [])
            analysis.append({
                "rule_id": "RULE_174",
                "rule_name": "時系列整合性チェック",
                "priority": self.RULE_PRIORITIES.get("RULE_174", "CRITICAL"),
                "passed": quality_gates.get("temporal_consistency", False),
                "score": 100 if temporal.get("passed", False) else 0,
                "details": {
                    "inconsistencies_count": len(inconsistencies),
                    "issues": inconsistencies
                },
                "message": f"矛盾検出: {len(inconsistencies)}件"
            })

        # RULE_175: ネガティブ評価
        if "negative_evaluation" in evaluation and evaluation["negative_evaluation"]:
            negative = evaluation["negative_evaluation"]
            issues = negative.get("issues", [])
            analysis.append({
                "rule_id": "RULE_175",
                "rule_name": "ネガティブエピソード評価",
                "priority": self.RULE_PRIORITIES.get("RULE_175", "CRITICAL"),
                "passed": quality_gates.get("negative_evaluation", False),
                "score": negative.get("total_score", 0),
                "details": {
                    "total_issues": len(issues),
                    "sensational_count": negative.get("sensational_count", 0),
                    "defamatory_count": negative.get("defamatory_count", 0)
                },
                "message": f"問題表現: {len(issues)}件"
            })

        # RULE_176: 架空キャラクター
        if "fictional_character" in evaluation and evaluation["fictional_character"]:
            fictional = evaluation["fictional_character"]
            analysis.append({
                "rule_id": "RULE_176",
                "rule_name": "架空キャラクター評価",
                "priority": self.RULE_PRIORITIES.get("RULE_176", "HIGH"),
                "passed": quality_gates.get("fictional_character", False),
                "score": fictional.get("cultural_impact_score", 0),
                "details": {
                    "is_fictional": fictional.get("is_fictional", False),
                    "cultural_impact": fictional.get("cultural_impact_score", 0),
                    "work_title": fictional.get("work_title")
                },
                "message": fictional.get("message", "実在人物")
            })

        # RULE_177: 抽象表現
        if "abstract_detection" in evaluation:
            abstract = evaluation["abstract_detection"]
            analysis.append({
                "rule_id": "RULE_177",
                "rule_name": "抽象表現検出",
                "priority": self.RULE_PRIORITIES.get("RULE_177", "MEDIUM"),
                "passed": quality_gates.get("abstract_detection", False),
                "score": abstract.get("concreteness_score", 0),
                "details": {
                    "abstract_count": abstract.get("abstract_count", 0),
                    "expressions": abstract.get("abstract_expressions", [])
                },
                "message": f"具体性スコア: {abstract.get('concreteness_score', 0)}点"
            })

        return analysis

    def _generate_improvement_section(
        self,
        improvement: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        改善アクションセクションを生成

        Args:
            improvement: 改善サマリー

        Returns:
            改善アクション情報
        """
        if not improvement:
            return {
                "improvements_applied": False,
                "total_improvements": 0,
                "actions": []
            }

        return {
            "improvements_applied": True,
            "total_improvements": improvement.get("total_improvements", 0),
            "by_severity": improvement.get("by_severity", {}),
            "by_rule": improvement.get("by_rule", {}),
            "actions": improvement.get("actions", [])
        }

    def _generate_statistics(
        self,
        evaluation: Dict[str, Any],
        improvement: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        統計的概観を生成

        Args:
            evaluation: 評価結果
            improvement: 改善サマリー

        Returns:
            統計情報
        """
        quality_gates = evaluation.get("quality_gates", {})

        stats = {
            "total_rules_evaluated": len(quality_gates),
            "pass_rate": round(
                sum(1 for p in quality_gates.values() if p) / max(len(quality_gates), 1) * 100,
                1
            ),
            "total_score": evaluation.get("total_score", 0),
            "score_breakdown": self._calculate_score_breakdown(evaluation)
        }

        if improvement:
            stats["improvement_rate"] = round(
                improvement.get("total_improvements", 0) / max(len(quality_gates), 1) * 100,
                1
            )

        return stats

    def _calculate_score_breakdown(self, evaluation: Dict[str, Any]) -> Dict[str, float]:
        """
        スコア内訳を計算

        Args:
            evaluation: 評価結果

        Returns:
            スコア内訳
        """
        breakdown = {}

        if "social_impact" in evaluation and evaluation["social_impact"]:
            breakdown["social_impact"] = evaluation["social_impact"].get("impact_score", 0) * 0.25

        if "temporal_consistency" in evaluation and evaluation["temporal_consistency"]:
            temporal_score = 100 if evaluation["temporal_consistency"].get("passed", False) else 0
            breakdown["temporal_consistency"] = temporal_score * 0.20

        if "negative_evaluation" in evaluation and evaluation["negative_evaluation"]:
            breakdown["negative_evaluation"] = evaluation["negative_evaluation"].get("total_score", 70) * 0.20

        if "abstract_detection" in evaluation and evaluation["abstract_detection"]:
            breakdown["abstract_detection"] = evaluation["abstract_detection"].get("concreteness_score", 70) * 0.15

        if "fictional_character" in evaluation and evaluation["fictional_character"]:
            breakdown["fictional_character"] = evaluation["fictional_character"].get("cultural_impact_score", 70) * 0.20

        return breakdown

    def _generate_recommendations(
        self,
        evaluation: Dict[str, Any],
        improvement: Optional[Dict[str, Any]]
    ) -> List[str]:
        """
        推奨事項を生成

        Args:
            evaluation: 評価結果
            improvement: 改善サマリー

        Returns:
            推奨事項リスト
        """
        recommendations = []
        quality_gates = evaluation.get("quality_gates", {})

        # 社会的インパクトが低い
        if not quality_gates.get("social_impact", False):
            recommendations.append(
                "社会的インパクトが低いです。より著名な人物や出来事を選択することを推奨します。"
            )

        # 時系列矛盾がある
        if not quality_gates.get("temporal_consistency", False):
            recommendations.append(
                "時系列矛盾が検出されました。年齢と出来事の整合性を確認してください。"
            )

        # ネガティブ表現が多い
        if not quality_gates.get("negative_evaluation", False):
            recommendations.append(
                "センセーショナルまたは侮辱的な表現が含まれています。客観的な記述に修正してください。"
            )

        # 抽象表現が多い
        if not quality_gates.get("abstract_detection", False):
            recommendations.append(
                "抽象的な表現が多く含まれています。具体的な数値や固有名詞を追加してください。"
            )

        # 改善が適用された
        if improvement and improvement.get("total_improvements", 0) > 0:
            recommendations.append(
                f"{improvement['total_improvements']}件の自動改善が適用されました。改善内容を確認してください。"
            )

        # すべて合格
        if all(quality_gates.values()):
            recommendations.append(
                "すべての品質基準を満たしています。優秀な品質です。"
            )

        return recommendations

    def export_to_json(self, report: Dict[str, Any], filepath: str) -> None:
        """
        レポートをJSON形式でエクスポート

        Args:
            report: 品質レポート
            filepath: 出力ファイルパス
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"📄 JSONレポート出力: {filepath}")

    def export_to_markdown(self, report: Dict[str, Any], filepath: str) -> None:
        """
        レポートをMarkdown形式でエクスポート

        Args:
            report: 品質レポート
            filepath: 出力ファイルパス
        """
        metadata = report["report_metadata"]
        summary = report["executive_summary"]
        rules = report["rule_analysis"]
        improvements = report["improvement_actions"]
        stats = report["statistical_overview"]
        recommendations = report["recommendations"]

        md_content = f"""# 品質レポート: {metadata['episode_id']}

**生成日時**: {metadata['generated_at']}
**人物名**: {metadata['person_name']}

---

## Executive Summary

| 項目 | 値 |
|-----|-----|
| 総合判定 | {summary['overall_status']} |
| 総合スコア | {summary['total_score']}点 |
| 品質グレード | **{summary['quality_grade']}** |
| 合格ルール | {summary['passed_rules']}件 |
| 不合格ルール | {summary['failed_rules']}件 |
| 重大問題 | {summary['critical_issues']}件 |
| 警告 | {summary['warnings']}件 |
| 改善適用 | {summary['improvements_applied']}件 |

**総合判定**: {summary['verdict']}

---

## エピソードテキスト

```
{metadata['episode_text']}
```

---

## ルール別詳細分析

"""

        for rule in rules:
            status = "✅ 合格" if rule['passed'] else "❌ 不合格"
            md_content += f"""### {rule['rule_id']}: {rule['rule_name']}

- **優先度**: {rule['priority']}
- **判定**: {status}
- **スコア**: {rule['score']}点
- **メッセージ**: {rule['message']}

"""

        md_content += f"""---

## 改善アクション

"""

        if improvements['improvements_applied']:
            md_content += f"""**総改善数**: {improvements['total_improvements']}件

| ルール | 元のテキスト | 改善後 | 理由 |
|-------|------------|-------|------|
"""
            for action in improvements['actions']:
                md_content += f"| {action['rule_id']} | {action['original']} | {action['improved']} | {action['reason']} |\n"
        else:
            md_content += "改善は適用されていません。\n"

        md_content += f"""
---

## 統計的概観

- **評価ルール数**: {stats['total_rules_evaluated']}件
- **合格率**: {stats['pass_rate']}%
- **総合スコア**: {stats['total_score']}点

---

## 推奨事項

"""

        for i, rec in enumerate(recommendations, 1):
            md_content += f"{i}. {rec}\n"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"📄 Markdownレポート出力: {filepath}")


# グローバルレポート生成エンジン
report_generator = QualityReportGenerator()


def generate_quality_report(
    episode_id: str,
    person_name: str,
    episode_text: str,
    evaluation_result: Dict[str, Any],
    improvement_summary: Optional[Dict[str, Any]] = None,
    export_format: Optional[str] = None,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    品質レポートを生成（外部インターフェース）

    Args:
        episode_id: エピソードID
        person_name: 人物名
        episode_text: エピソードテキスト
        evaluation_result: RULE_179の評価結果
        improvement_summary: RULE_180の改善サマリー
        export_format: エクスポート形式 ('json', 'markdown')
        output_path: 出力ファイルパス

    Returns:
        品質レポート
    """
    report = report_generator.generate_report(
        episode_id, person_name, episode_text,
        evaluation_result, improvement_summary
    )

    # エクスポート
    if export_format and output_path:
        if export_format == 'json':
            report_generator.export_to_json(report, output_path)
        elif export_format == 'markdown':
            report_generator.export_to_markdown(report, output_path)

    return report


if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    print("=" * 80)
    print("RULE_181: 品質レポート生成 - テスト実行")
    print("=" * 80)
    print()

    # テストケース（RULE_179とRULE_180の結果を想定）
    test_evaluation = {
        "passed": False,
        "total_score": 66.8,
        "quality_gates": {
            "social_impact": True,
            "age_flexibility": True,
            "temporal_consistency": False,
            "negative_evaluation": True,
            "abstract_detection": False,
            "fictional_character": True
        },
        "social_impact": {
            "passed": True,
            "impact_score": 75,
            "search_volume_score": 80,
            "wikipedia_languages": 5,
            "news_articles_count": 100,
            "social_buzz_score": 70
        },
        "age_flexibility": {
            "passed": True,
            "selected_age": 28,
            "alternative_ages": [27, 29]
        },
        "temporal_consistency": {
            "passed": False,
            "inconsistencies": [
                {
                    "severity": "CRITICAL",
                    "message": "18歳でノーベル賞は不可能（最年少記録: 25歳）",
                    "evidence": "18歳、ノーベル"
                }
            ]
        },
        "negative_evaluation": {
            "passed": True,
            "total_score": 85,
            "issues": [],
            "sensational_count": 0,
            "defamatory_count": 0
        },
        "abstract_detection": {
            "passed": False,
            "concreteness_score": 55,
            "abstract_count": 5,
            "abstract_expressions": [
                {"expression": "多くの", "category": "量"},
                {"expression": "素晴らしい", "category": "評価"}
            ]
        },
        "fictional_character": {
            "passed": True,
            "is_fictional": False,
            "cultural_impact_score": 0,
            "message": "実在人物"
        }
    }

    test_improvement = {
        "total_improvements": 3,
        "by_severity": {"CRITICAL": 1, "WARNING": 2, "INFO": 0},
        "by_rule": {"RULE_174": 1, "RULE_177": 2},
        "actions": [
            {
                "rule_id": "RULE_174",
                "type": "temporal_inconsistency",
                "severity": "CRITICAL",
                "original": "18歳",
                "improved": "25歳",
                "reason": "時系列矛盾修正: 18歳でノーベルは不可能（最年少記録: 25歳）"
            },
            {
                "rule_id": "RULE_177",
                "type": "abstract_expression",
                "severity": "WARNING",
                "original": "多くの",
                "improved": "3つの",
                "reason": "抽象表現の具体化: 具体的な数値に"
            },
            {
                "rule_id": "RULE_177",
                "type": "abstract_expression",
                "severity": "WARNING",
                "original": "素晴らしい",
                "improved": "[削除]",
                "reason": "抽象表現の具体化: 客観的事実に"
            }
        ]
    }

    # レポート生成
    report = generate_quality_report(
        episode_id="EP001",
        person_name="大谷翔平",
        episode_text="あなたと同じ28歳のとき、大谷翔平はMLBでア・リーグMVPを受賞した。",
        evaluation_result=test_evaluation,
        improvement_summary=test_improvement
    )

    # Executive Summaryの表示
    print("📊 Executive Summary")
    print("=" * 80)
    summary = report["executive_summary"]
    print(f"  総合判定: {summary['overall_status']}")
    print(f"  総合スコア: {summary['total_score']}点")
    print(f"  品質グレード: {summary['quality_grade']}")
    print(f"  合格ルール: {summary['passed_rules']}件 / 不合格: {summary['failed_rules']}件")
    print(f"  重大問題: {summary['critical_issues']}件 / 警告: {summary['warnings']}件")
    print(f"  改善適用: {summary['improvements_applied']}件")
    print(f"  判定: {summary['verdict']}")
    print()

    # Rule Analysis
    print("📋 ルール別分析")
    print("=" * 80)
    for rule in report["rule_analysis"]:
        status = "✅" if rule['passed'] else "❌"
        print(f"  {status} {rule['rule_id']}: {rule['rule_name']}")
        print(f"     優先度: {rule['priority']} | スコア: {rule['score']}点")
        print(f"     {rule['message']}")
        print()

    # Recommendations
    print("💡 推奨事項")
    print("=" * 80)
    for i, rec in enumerate(report["recommendations"], 1):
        print(f"  {i}. {rec}")
    print()

    # エクスポートテスト
    print("📄 エクスポートテスト")
    print("=" * 80)

    # JSON出力
    report_generator.export_to_json(report, "test_quality_report.json")

    # Markdown出力
    report_generator.export_to_markdown(report, "test_quality_report.md")

    print()
    print("=" * 80)
    print("✅ テスト完了")
    print("=" * 80)
