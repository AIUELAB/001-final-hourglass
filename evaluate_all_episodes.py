#!/usr/bin/env python3
"""
100エピソード統合評価スクリプト

RULE_179-181を使用してすべてのエピソードを評価し、品質レポートを生成
"""

import sqlite3
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

# rulesディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "rules"))

from rule_179_integrated_evaluation_pipeline import evaluate_episode_integrated
from rule_180_automatic_improvement_engine import improve_episode_automatically
from rule_181_quality_report_generator import generate_quality_report

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


class EpisodeEvaluator:
    """エピソード評価システム"""

    def __init__(self, db_path: str = "episode_database.db"):
        """
        初期化

        Args:
            db_path: データベースファイルパス
        """
        self.db_path = db_path
        self.conn = None

    def connect(self):
        """データベース接続"""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        """データベース切断"""
        if self.conn:
            self.conn.close()

    def get_all_episodes(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        すべてのエピソードを取得

        Args:
            limit: 取得件数制限

        Returns:
            エピソードリスト
        """
        cursor = self.conn.cursor()

        query = """
            SELECT
                e.episode_id,
                e.person_id,
                e.age,
                e.episode_text,
                e.quality_score,
                e.grade,
                p.person_name_ja,
                p.birth_year,
                p.entity_type,
                p.primary_work,
                p.category
            FROM episodes e
            JOIN persons p ON e.person_id = p.person_id
            WHERE e.is_active = 1
            ORDER BY e.created_at
        """

        if limit:
            query += f" LIMIT {limit}"

        cursor.execute(query)
        rows = cursor.fetchall()

        episodes = []
        for row in rows:
            episodes.append({
                "episode_id": row["episode_id"],
                "person_id": row["person_id"],
                "person_name": row["person_name_ja"],
                "age": row["age"],
                "episode_text": row["episode_text"],
                "quality_score": row["quality_score"],
                "grade": row["grade"],
                "birth_year": row["birth_year"],
                "entity_type": row["entity_type"] or "real_person",
                "primary_work": row["primary_work"],
                "category": row["category"]
            })

        return episodes

    def evaluate_episode(self, episode: Dict[str, Any]) -> Dict[str, Any]:
        """
        単一エピソードを評価

        Args:
            episode: エピソードデータ

        Returns:
            評価結果
        """
        logger.info(f"\n{'=' * 80}")
        logger.info(f"📊 評価開始: {episode['episode_id']} - {episode['person_name']}")
        logger.info(f"{'=' * 80}")

        # Phase 1: RULE_179で統合評価
        evaluation_result = evaluate_episode_integrated(
            episode_id=episode["episode_id"],
            person_name=episode["person_name"],
            episode_text=episode["episode_text"],
            database_age=episode["age"],
            birth_year=episode["birth_year"],
            entity_type=episode["entity_type"],
            work_title=episode["primary_work"]
        )

        # EpisodeEvaluationResultを辞書に変換
        evaluation_dict = {
            "passed": evaluation_result.passed,
            "total_score": evaluation_result.total_score,
            "quality_gates": evaluation_result.quality_gates,
            "social_impact": evaluation_result.social_impact,
            "age_flexibility": evaluation_result.age_selection,
            "temporal_consistency": evaluation_result.temporal_consistency,
            "negative_evaluation": evaluation_result.negative_evaluation,
            "fictional_character": evaluation_result.fictional_character,
            "abstract_detection": evaluation_result.abstract_detection,
            "timestamp": evaluation_result.evaluation_timestamp
        }

        # Phase 2: RULE_180で自動改善（不合格の場合のみ）
        improvement_summary = None
        improved_text = episode["episode_text"]

        if not evaluation_result.passed:
            logger.info(f"\n🔧 自動改善を実行...")
            improved_text, improvement_summary = improve_episode_automatically(
                episode["episode_text"],
                evaluation_dict,
                max_iterations=3
            )

            if improvement_summary.get("total_improvements", 0) > 0:
                logger.info(f"✅ {improvement_summary['total_improvements']}件の改善を適用")

        # Phase 3: RULE_181で品質レポート生成
        report = generate_quality_report(
            episode_id=episode["episode_id"],
            person_name=episode["person_name"],
            episode_text=episode["episode_text"],
            evaluation_result=evaluation_dict,
            improvement_summary=improvement_summary
        )

        return {
            "episode_id": episode["episode_id"],
            "person_name": episode["person_name"],
            "original_text": episode["episode_text"],
            "improved_text": improved_text,
            "evaluation": evaluation_dict,  # 辞書形式で返す
            "improvement": improvement_summary,
            "report": report
        }

    def evaluate_all(self, limit: Optional[int] = None) -> Dict[str, Any]:
        """
        すべてのエピソードを評価

        Args:
            limit: 評価件数制限

        Returns:
            統合評価結果
        """
        self.connect()

        try:
            episodes = self.get_all_episodes(limit)
            total_count = len(episodes)

            logger.info(f"\n{'=' * 80}")
            logger.info(f"📊 統合評価開始: {total_count}件のエピソード")
            logger.info(f"{'=' * 80}\n")

            results = []
            statistics = {
                "total_episodes": total_count,
                "passed_count": 0,
                "failed_count": 0,
                "grades": {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0, "F": 0},
                "total_score_sum": 0,
                "improvements_applied": 0,
                "critical_issues": 0,
                "warnings": 0
            }

            for i, episode in enumerate(episodes, 1):
                logger.info(f"\n進捗: {i}/{total_count}")

                result = self.evaluate_episode(episode)
                results.append(result)

                # 統計更新
                evaluation_dict = result["evaluation"]
                report = result["report"]
                summary = report["executive_summary"]

                if evaluation_dict["passed"]:
                    statistics["passed_count"] += 1
                else:
                    statistics["failed_count"] += 1

                grade = summary["quality_grade"]
                statistics["grades"][grade] += 1
                statistics["total_score_sum"] += evaluation_dict["total_score"]
                statistics["critical_issues"] += summary["critical_issues"]
                statistics["warnings"] += summary["warnings"]

                if result["improvement"]:
                    statistics["improvements_applied"] += result["improvement"].get("total_improvements", 0)

            # 平均スコア計算
            statistics["average_score"] = round(
                statistics["total_score_sum"] / max(total_count, 1),
                2
            )

            statistics["pass_rate"] = round(
                statistics["passed_count"] / max(total_count, 1) * 100,
                1
            )

            # 最後のタイムスタンプを使用
            last_timestamp = results[-1]["evaluation"]["timestamp"] if results else datetime.now().isoformat()

            return {
                "statistics": statistics,
                "results": results,
                "timestamp": last_timestamp
            }

        finally:
            self.close()

    def save_results(self, results: Dict[str, Any], output_path: str):
        """
        評価結果を保存

        Args:
            results: 評価結果
            output_path: 出力パス
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"\n📄 評価結果を保存: {output_path}")

    def generate_summary_report(self, results: Dict[str, Any], output_path: str):
        """
        サマリーレポート（Markdown）を生成

        Args:
            results: 評価結果
            output_path: 出力パス
        """
        stats = results["statistics"]

        md_content = f"""# Phase 6 統合評価レポート

**評価日時**: {results.get('timestamp', 'N/A')}
**評価エピソード数**: {stats['total_episodes']}件

---

## 📊 総合統計

| 項目 | 値 |
|-----|-----|
| 合格数 | {stats['passed_count']}件 ({stats['pass_rate']}%) |
| 不合格数 | {stats['failed_count']}件 |
| 平均スコア | {stats['average_score']}点 |
| 重大問題総数 | {stats['critical_issues']}件 |
| 警告総数 | {stats['warnings']}件 |
| 改善適用総数 | {stats['improvements_applied']}件 |

---

## 🎓 品質グレード分布

| グレード | 件数 | 割合 |
|---------|-----|------|
| S (90点以上) | {stats['grades']['S']}件 | {round(stats['grades']['S']/max(stats['total_episodes'],1)*100, 1)}% |
| A (80-89点) | {stats['grades']['A']}件 | {round(stats['grades']['A']/max(stats['total_episodes'],1)*100, 1)}% |
| B (70-79点) | {stats['grades']['B']}件 | {round(stats['grades']['B']/max(stats['total_episodes'],1)*100, 1)}% |
| C (60-69点) | {stats['grades']['C']}件 | {round(stats['grades']['C']/max(stats['total_episodes'],1)*100, 1)}% |
| D (50-59点) | {stats['grades']['D']}件 | {round(stats['grades']['D']/max(stats['total_episodes'],1)*100, 1)}% |
| F (50点未満) | {stats['grades']['F']}件 | {round(stats['grades']['F']/max(stats['total_episodes'],1)*100, 1)}% |

---

## 📋 エピソード別評価結果

| ID | 人物名 | スコア | グレード | 判定 | 改善 |
|----|--------|--------|---------|------|------|
"""

        for result in results["results"]:
            episode_id = result["episode_id"]
            person_name = result["person_name"]
            score = result["evaluation"]["total_score"]
            grade = result["report"]["executive_summary"]["quality_grade"]
            passed = "✅" if result["evaluation"]["passed"] else "❌"
            improvements = result["improvement"].get("total_improvements", 0) if result["improvement"] else 0

            md_content += f"| {episode_id} | {person_name} | {score}点 | {grade} | {passed} | {improvements}件 |\n"

        md_content += f"""
---

## 💡 総合推奨事項

### 優先度: 高

1. **重大問題の修正**: {stats['critical_issues']}件の重大問題があります。時系列矛盾やセンセーショナル表現を優先的に修正してください。

2. **不合格エピソードの改善**: {stats['failed_count']}件のエピソードが品質基準未達です。自動改善提案を参考に修正してください。

### 優先度: 中

3. **抽象表現の具体化**: 多くのエピソードで抽象表現が検出されています。具体的な数値や固有名詞を追加してください。

4. **品質グレードの向上**: 平均スコア{stats['average_score']}点をA（80点）以上に引き上げることを推奨します。

### 成果

- **自動改善適用**: {stats['improvements_applied']}件の改善が自動適用されました。
- **合格率**: {stats['pass_rate']}%のエピソードが品質基準を満たしています。

---

## 🚀 次のステップ

1. 重大問題（CRITICAL）の手動修正
2. 自動改善提案の適用確認
3. 不合格エピソードの再評価
4. A/Bグレード以上の目標設定
5. 定期的な品質モニタリング

---

*このレポートはRULE_179-181による自動評価システムで生成されました。*
"""

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        logger.info(f"📄 サマリーレポートを保存: {output_path}")


def main():
    """メイン処理"""
    evaluator = EpisodeEvaluator()

    # すべてのエピソードを評価（テストのため最初の3件のみ）
    logger.info("\n🚀 Phase 6 統合評価システム実行開始\n")

    results = evaluator.evaluate_all(limit=3)  # テスト用に3件に制限

    # 結果を保存
    evaluator.save_results(results, "phase6_evaluation_results.json")

    # サマリーレポート生成
    evaluator.generate_summary_report(results, "PHASE6_EVALUATION_REPORT.md")

    # 統計サマリー表示
    stats = results["statistics"]

    print("\n" + "=" * 80)
    print("📊 Phase 6 統合評価完了")
    print("=" * 80)
    print(f"\n総評価数: {stats['total_episodes']}件")
    print(f"合格: {stats['passed_count']}件 ({stats['pass_rate']}%)")
    print(f"不合格: {stats['failed_count']}件")
    print(f"平均スコア: {stats['average_score']}点")
    print(f"\n品質グレード分布:")
    for grade in ['S', 'A', 'B', 'C', 'D', 'F']:
        count = stats['grades'][grade]
        if count > 0:
            print(f"  {grade}: {count}件")
    print(f"\n重大問題: {stats['critical_issues']}件")
    print(f"警告: {stats['warnings']}件")
    print(f"改善適用: {stats['improvements_applied']}件")
    print("\n" + "=" * 80)


if __name__ == "__main__":
    main()
