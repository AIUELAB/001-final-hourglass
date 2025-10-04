#!/usr/bin/env python3
"""
Phase 10改訂版: 社会的影響特化バッチ改善システム

40-50点の社会的影響スコアを持つエピソードを改善する。
RULE_184を使用して社会的影響を+5点以上向上させる。
（当初のRULE_185微調整戦略は効果なし（0%）のため、Phase 9と同じRULE_184を採用）
"""

import csv
import json
import time
from typing import List, Dict
from datetime import datetime
from pathlib import Path

from rules.rule_184_social_impact_llm_improver import apply_rule_184
from rules.rule_179_integrated_evaluation_pipeline import evaluate_episode_integrated


class MicroAdjustmentBatchImprover:
    """Phase 10改訂版: 社会的影響特化バッチ改善システム"""

    def __init__(
        self,
        provider: str = "openai",
        checkpoint_interval: int = 10,
        acceptance_threshold: float = 3.0  # Phase 10: +3点に緩和（40-50点は難易度高）
    ):
        """
        Args:
            provider: LLMプロバイダー ("openai")
            checkpoint_interval: チェックポイント保存間隔
            acceptance_threshold: 受入閾値（社会的影響+3点以上で採用、Phase 10緩和版）
        """
        self.provider = provider
        self.checkpoint_interval = checkpoint_interval
        self.acceptance_threshold = acceptance_threshold

        self.stats = {
            "total_processed": 0,
            "improved": 0,
            "failed": 0,
            "skipped": 0,
            "social_impact_increased": 0,
            "total_score_increased": 0,
            "errors": []
        }

    def load_targets(self, csv_path: str) -> List[Dict]:
        """
        Phase 10.1で抽出したターゲットエピソードを読み込み
        ギャップ（合格までの距離）でソート
        """
        targets = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                targets.append(row)

        # ギャップ昇順でソート（合格に近い方が優先）
        targets.sort(key=lambda x: float(x['gap_to_pass']))
        return targets

    def improve_episode(
        self,
        episode_data: Dict,
        original_episode_text: str
    ) -> Dict:
        """
        1件のエピソードを微調整改善

        Args:
            episode_data: エピソードメタデータ（ID、人物名、年齢等）
            original_episode_text: 元のエピソードテキスト

        Returns:
            {
                "episode_id": str,
                "person_name": str,
                "episode_age": int,
                "original_text": str,
                "improved_text": str,
                "before_total_score": float,
                "after_total_score": float,
                "before_social_impact": float,
                "after_social_impact": float,
                "social_impact_gain": float,
                "adopted": bool,
                "improvement_success": bool,
                "evaluation_success": bool,
                "error": Optional[str]
            }
        """
        episode_id = episode_data['episode_id']
        person_name = episode_data['person_name']
        episode_age = int(episode_data['episode_age'])
        before_total_score = float(episode_data['total_score'])
        before_social_impact = float(episode_data['social_impact_score'])
        gap_to_pass = float(episode_data['gap_to_pass'])

        print(f"\n{'='*80}")
        print(f"🎯 {episode_id}: {person_name} (ギャップ: {gap_to_pass:.1f}点)")
        print(f"{'='*80}")
        print(f"元のスコア - 総合: {before_total_score:.1f}点, 社会的影響: {before_social_impact:.1f}点")

        # RULE_184で社会的影響改善
        print(f"\n🔧 RULE_184による社会的影響改善を実行中...")
        improvement_result = apply_rule_184(
            episode_text=original_episode_text,
            episode_age=episode_age,
            current_total_score=before_total_score,
            current_social_impact=before_social_impact,
            person_name=person_name,
            provider=self.provider
        )

        if not improvement_result["success"]:
            print(f"❌ 改善失敗: {improvement_result['error']}")
            return {
                "episode_id": episode_id,
                "person_name": person_name,
                "episode_age": episode_age,
                "original_text": original_episode_text,
                "improved_text": original_episode_text,
                "before_total_score": before_total_score,
                "after_total_score": before_total_score,
                "before_social_impact": before_social_impact,
                "after_social_impact": before_social_impact,
                "social_impact_gain": 0.0,
                "adopted": False,
                "improvement_success": False,
                "evaluation_success": False,
                "error": improvement_result['error']
            }

        improved_text = improvement_result["improved_text"]
        print(f"✅ 改善成功 ({len(improved_text)}文字)")

        # RULE_179で再評価
        print(f"\n📊 RULE_179による再評価を実行中...")
        eval_result = evaluate_episode_integrated(
            episode_id=episode_id,
            person_name=person_name,
            episode_text=improved_text,
            database_age=episode_age
        )

        # 評価結果を取得
        after_total_score = eval_result.total_score
        after_social_impact = eval_result.social_impact.get('impact_score', before_social_impact)

        print(f"改善後スコア - 総合: {after_total_score:.1f}点, 社会的影響: {after_social_impact:.1f}点")

        # 社会的影響の向上を計算
        social_impact_gain = after_social_impact - before_social_impact
        total_score_gain = after_total_score - before_total_score

        print(f"\n📈 スコア変化:")
        print(f"  社会的影響: {social_impact_gain:+.1f}点")
        print(f"  総合スコア: {total_score_gain:+.1f}点")

        # 改善判定（社会的影響+3点以上なら採用、Phase 10緩和版）
        adopted = social_impact_gain >= self.acceptance_threshold

        if adopted:
            print(f"✅ 改善採用（社会的影響+{social_impact_gain:.1f}点 >= +{self.acceptance_threshold:.1f}点）")
            final_text = improved_text
        else:
            print(f"🔄 ロールバック（社会的影響+{social_impact_gain:.1f}点 < +{self.acceptance_threshold:.1f}点）")
            final_text = original_episode_text
            # ロールバック時はスコアも元に戻す
            after_total_score = before_total_score
            after_social_impact = before_social_impact

        return {
            "episode_id": episode_id,
            "person_name": person_name,
            "episode_age": episode_age,
            "original_text": original_episode_text,
            "improved_text": final_text,
            "before_total_score": before_total_score,
            "after_total_score": after_total_score,
            "before_social_impact": before_social_impact,
            "after_social_impact": after_social_impact,
            "social_impact_gain": social_impact_gain if adopted else 0.0,
            "adopted": adopted,
            "improvement_success": True,
            "evaluation_success": True,
            "error": None
        }

    def process_batch(
        self,
        targets: List[Dict],
        episodes_csv_path: str,
        output_csv_path: str
    ) -> List[Dict]:
        """
        バッチ処理メイン

        Args:
            targets: ターゲットエピソードリスト
            episodes_csv_path: 元のエピソードCSV
            output_csv_path: 出力CSV

        Returns:
            改善結果リスト
        """
        # 元のエピソードを読み込み
        print(f"\n📂 元のエピソードを読み込み中...")
        episodes_dict = {}
        with open(episodes_csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                episodes_dict[row['episode_id']] = row

        print(f"✅ {len(episodes_dict)}件のエピソード読み込み完了")

        results = []
        start_time = time.time()

        for i, target in enumerate(targets, 1):
            episode_id = target['episode_id']

            if episode_id not in episodes_dict:
                print(f"⚠️ エピソード{episode_id}が見つかりません - スキップ")
                self.stats["skipped"] += 1
                continue

            original_data = episodes_dict[episode_id]
            original_text = original_data['episode_text']

            # エピソード改善
            result = self.improve_episode(target, original_text)
            results.append(result)

            # 統計更新
            self.stats["total_processed"] += 1
            if result["adopted"]:
                self.stats["improved"] += 1
                if result["social_impact_gain"] > 0:
                    self.stats["social_impact_increased"] += 1
                if result["after_total_score"] > result["before_total_score"]:
                    self.stats["total_score_increased"] += 1
            elif not result["improvement_success"]:
                self.stats["failed"] += 1
                if result["error"]:
                    self.stats["errors"].append({
                        "episode_id": episode_id,
                        "error": result["error"]
                    })

            # チェックポイント保存
            if i % self.checkpoint_interval == 0:
                self._save_checkpoint(episodes_dict, results, output_csv_path)
                elapsed = time.time() - start_time
                print(f"\n⏱️ 進捗: {i}/{len(targets)} ({i/len(targets)*100:.1f}%) - 経過時間: {elapsed:.1f}秒")

        # 最終保存
        self._save_final_results(episodes_dict, results, output_csv_path)

        elapsed = time.time() - start_time
        print(f"\n⏱️ 総処理時間: {elapsed:.1f}秒")

        return results

    def _save_checkpoint(
        self,
        episodes_dict: Dict,
        results: List[Dict],
        output_csv_path: str
    ):
        """チェックポイント保存"""
        checkpoint_path = f"{output_csv_path}.checkpoint"
        self._write_output_csv(episodes_dict, results, checkpoint_path)
        print(f"💾 チェックポイント保存: {checkpoint_path}")

    def _save_final_results(
        self,
        episodes_dict: Dict,
        results: List[Dict],
        output_csv_path: str
    ):
        """最終結果保存"""
        self._write_output_csv(episodes_dict, results, output_csv_path)
        print(f"\n💾 最終結果保存: {output_csv_path}")

        # 統計情報保存
        stats_path = output_csv_path.replace(".csv", "_stats.json")
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)
        print(f"💾 統計情報保存: {stats_path}")

    def _write_output_csv(
        self,
        episodes_dict: Dict,
        results: List[Dict],
        output_path: str
    ):
        """結果をCSV出力"""
        # 改善結果を辞書化
        improvements = {r["episode_id"]: r for r in results}

        # 全エピソードを出力（改善済み + 未改善）
        output_rows = []
        for episode_id, original in episodes_dict.items():
            if episode_id in improvements:
                result = improvements[episode_id]
                output_rows.append({
                    "episode_id": episode_id,
                    "person_name": result["person_name"],
                    "episode_text": result["improved_text"],
                    "episode_age": result["episode_age"]
                })
            else:
                # 未改善のエピソードはそのまま
                output_rows.append({
                    "episode_id": episode_id,
                    "person_name": original["person_name"],
                    "episode_text": original["episode_text"],
                    "episode_age": original["episode_age"]
                })

        # CSV出力
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['episode_id', 'person_name', 'episode_text', 'episode_age']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(output_rows)


def main():
    """メイン実行"""
    print("=" * 80)
    print("Phase 10改訂版: 社会的影響特化バッチ改善システム（RULE_184使用）")
    print("=" * 80)

    # バッチ改善システム初期化
    improver = MicroAdjustmentBatchImprover(
        provider="openai",
        checkpoint_interval=10,
        acceptance_threshold=3.0  # Phase 10: +3点に緩和（RULE_184使用）
    )

    # Phase 10ターゲット読み込み
    print("\n📂 Phase 10ターゲットを読み込み中...")
    targets = improver.load_targets("episodes_phase10_targets.csv")
    print(f"✅ {len(targets)}件のターゲットエピソード読み込み完了")

    # バッチ処理実行
    print("\n🚀 バッチ処理を開始...")
    results = improver.process_batch(
        targets=targets,
        episodes_csv_path="episodes_phase9_complete.csv",
        output_csv_path="episodes_phase10_complete.csv"
    )

    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 Phase 10バッチ処理完了")
    print("=" * 80)

    print(f"\n処理統計:")
    print(f"  総処理数: {improver.stats['total_processed']}件")
    print(f"  改善採用: {improver.stats['improved']}件")
    print(f"  改善失敗: {improver.stats['failed']}件")
    print(f"  スキップ: {improver.stats['skipped']}件")

    print(f"\n改善効果:")
    print(f"  社会的影響向上: {improver.stats['social_impact_increased']}件")
    print(f"  総合スコア向上: {improver.stats['total_score_increased']}件")

    if improver.stats['errors']:
        print(f"\nエラー詳細:")
        for error in improver.stats['errors']:
            print(f"  {error['episode_id']}: {error['error']}")

    # Top改善エピソード表示
    successful_improvements = [
        r for r in results
        if r["adopted"] and r["social_impact_gain"] > 0
    ]

    if successful_improvements:
        print(f"\n" + "=" * 80)
        print(f"🏆 Top 10改善エピソード")
        print(f"=" * 80)

        successful_improvements.sort(
            key=lambda x: x["social_impact_gain"],
            reverse=True
        )

        print(f"\n{'順位':<4} {'ID':<8} {'人物名':<20} {'社会的影響向上':<12}")
        print("-" * 80)

        for i, r in enumerate(successful_improvements[:10], 1):
            print(f"{i:<4} {r['episode_id']:<8} {r['person_name']:<20} "
                  f"{r['social_impact_gain']:+.1f}点")

    print(f"\n" + "=" * 80)
    print(f"✅ Phase 10完了")
    print(f"=" * 80)


if __name__ == "__main__":
    main()
