#!/usr/bin/env python3
"""
Phase 9: 社会的影響特化バッチ改善システム

社会的影響スコア<40点のエピソードを優先的に改善する。
RULE_184を使用して社会的影響を強化。
"""

import csv
import json
import time
from typing import List, Dict
from datetime import datetime
from pathlib import Path

from rules.rule_184_social_impact_llm_improver import apply_rule_184
from rules.rule_179_integrated_evaluation_pipeline import evaluate_episode_integrated


class SocialImpactBatchImprover:
    """社会的影響特化バッチ改善システム"""

    def __init__(
        self,
        provider: str = "openai",
        checkpoint_interval: int = 10,
        social_impact_threshold: float = 40.0
    ):
        """
        Args:
            provider: LLMプロバイダー ("openai" or "anthropic")
            checkpoint_interval: チェックポイント保存間隔
            social_impact_threshold: 社会的影響の閾値（これ未満を改善対象）
        """
        self.provider = provider
        self.checkpoint_interval = checkpoint_interval
        self.social_impact_threshold = social_impact_threshold

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
        Phase 9.1で抽出したターゲットエピソードを読み込み
        社会的影響スコアでフィルタリング
        """
        targets = []
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                social_impact = float(row['social_impact_score'])
                if social_impact < self.social_impact_threshold:
                    targets.append(row)

        # 社会的影響昇順でソート（低い方が優先）
        targets.sort(key=lambda x: float(x['social_impact_score']))
        return targets

    def improve_episode(
        self,
        episode_data: Dict,
        original_episode_text: str
    ) -> Dict:
        """
        1件のエピソードを改善

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

        print(f"\n{'='*80}")
        print(f"Processing: {episode_id} - {person_name} ({episode_age}歳)")
        print(f"  改善前: 総合{before_total_score:.1f}点, 社会的影響{before_social_impact:.1f}点")

        # RULE_184で改善
        print(f"  🔄 RULE_184で社会的影響を改善中...")
        improvement_result = apply_rule_184(
            episode_text=original_episode_text,
            episode_age=episode_age,
            current_total_score=before_total_score,
            current_social_impact=before_social_impact,
            person_name=person_name,
            provider=self.provider
        )

        if not improvement_result["success"]:
            print(f"  ❌ 改善失敗: {improvement_result['error']}")
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
                "improvement_success": False,
                "evaluation_success": False,
                "error": improvement_result["error"]
            }

        improved_text = improvement_result["improved_text"]
        print(f"  ✅ 改善完了: {len(original_episode_text)}文字 → {len(improved_text)}文字")

        # RULE_179で再評価
        print(f"  📊 RULE_179で再評価中...")
        eval_result = evaluate_episode_integrated(
            episode_id=episode_id,
            person_name=person_name,
            episode_text=improved_text,
            database_age=episode_age
        )

        if not hasattr(eval_result, 'total_score'):
            print(f"  ⚠️ 評価失敗: 評価結果が不正です")
            return {
                "episode_id": episode_id,
                "person_name": person_name,
                "episode_age": episode_age,
                "original_text": original_episode_text,
                "improved_text": improved_text,
                "before_total_score": before_total_score,
                "after_total_score": before_total_score,
                "before_social_impact": before_social_impact,
                "after_social_impact": before_social_impact,
                "improvement_success": True,
                "evaluation_success": False,
                "error": "Evaluation result invalid"
            }

        after_total_score = eval_result.total_score
        # social_impactから社会的影響スコアを取得
        after_social_impact = eval_result.social_impact.get('impact_score', before_social_impact)

        social_impact_gain = after_social_impact - before_social_impact
        total_score_gain = after_total_score - before_total_score

        print(f"  改善後: 総合{after_total_score:.1f}点 ({total_score_gain:+.1f}), "
              f"社会的影響{after_social_impact:.1f}点 ({social_impact_gain:+.1f})")

        # 改善判定（社会的影響+5点以上なら採用）
        if social_impact_gain >= 5.0:
            print(f"  ✅ 改善採用: 社会的影響{social_impact_gain:+.1f}点向上")
            adopted = True
        else:
            print(f"  ❌ 改善不採用: 社会的影響{social_impact_gain:+.1f}点（+5点未満）")
            # ロールバック
            improved_text = original_episode_text
            after_total_score = before_total_score
            after_social_impact = before_social_impact
            adopted = False

        return {
            "episode_id": episode_id,
            "person_name": person_name,
            "episode_age": episode_age,
            "original_text": original_episode_text,
            "improved_text": improved_text,
            "before_total_score": before_total_score,
            "after_total_score": after_total_score,
            "before_social_impact": before_social_impact,
            "after_social_impact": after_social_impact,
            "improvement_success": True,
            "evaluation_success": True,
            "adopted": adopted,
            "error": None
        }

    def process_batch(
        self,
        targets: List[Dict],
        episodes_csv: str,
        output_csv: str,
        test_mode: bool = False
    ) -> Dict:
        """
        バッチ処理メイン

        Args:
            targets: ターゲットエピソードリスト
            episodes_csv: 元のエピソードCSV
            output_csv: 出力CSVパス
            test_mode: テストモード（5件のみ処理）

        Returns:
            統計情報
        """
        # 元のエピソードテキストを読み込み
        episode_texts = self._load_episode_texts(episodes_csv)

        # テストモードなら5件に制限
        if test_mode:
            targets = targets[:5]
            print(f"\n🧪 テストモード: {len(targets)}件を処理")

        print(f"\n{'='*80}")
        print(f"Phase 9 バッチ改善開始")
        print(f"{'='*80}")
        print(f"対象件数: {len(targets)}件")
        print(f"プロバイダー: {self.provider}")
        print(f"社会的影響閾値: {self.social_impact_threshold}点未満")
        print(f"改善採用基準: 社会的影響+5点以上")

        results = []
        start_time = time.time()

        for i, target in enumerate(targets, 1):
            episode_id = target['episode_id']
            original_text = episode_texts.get(episode_id, "")

            if not original_text:
                print(f"\n⚠️ エピソードテキストが見つかりません: {episode_id}")
                self.stats["skipped"] += 1
                continue

            # 改善実行
            result = self.improve_episode(target, original_text)
            results.append(result)

            self.stats["total_processed"] += 1

            if result["improvement_success"] and result["evaluation_success"]:
                if result.get("adopted", False):
                    self.stats["improved"] += 1
                    if result["after_social_impact"] > result["before_social_impact"]:
                        self.stats["social_impact_increased"] += 1
                    if result["after_total_score"] > result["before_total_score"]:
                        self.stats["total_score_increased"] += 1
                else:
                    self.stats["failed"] += 1
            else:
                self.stats["failed"] += 1
                if result["error"]:
                    self.stats["errors"].append({
                        "episode_id": episode_id,
                        "error": result["error"]
                    })

            # チェックポイント保存
            if i % self.checkpoint_interval == 0:
                checkpoint_path = output_csv.replace('.csv', f'_checkpoint_{i}.csv')
                self._save_checkpoint(results, checkpoint_path)
                print(f"\n💾 Checkpoint {i}: {checkpoint_path}")

        # 最終保存
        self._save_results(results, output_csv, episodes_csv)

        elapsed = time.time() - start_time
        self.stats["elapsed_seconds"] = elapsed
        self.stats["elapsed_minutes"] = elapsed / 60

        return self.stats

    def _load_episode_texts(self, csv_path: str) -> Dict[str, str]:
        """元のエピソードCSVからテキストを読み込み"""
        episodes = {}
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                episodes[row['episode_id']] = row['episode_text']
        return episodes

    def _save_checkpoint(self, results: List[Dict], checkpoint_path: str):
        """チェックポイント保存"""
        with open(checkpoint_path, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = [
                'episode_id', 'person_name', 'episode_age',
                'improved_text', 'character_count',
                'before_total_score', 'after_total_score',
                'before_social_impact', 'after_social_impact',
                'adopted'
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow({
                    'episode_id': r['episode_id'],
                    'person_name': r['person_name'],
                    'episode_age': r['episode_age'],
                    'improved_text': r['improved_text'],
                    'character_count': len(r['improved_text']),
                    'before_total_score': r['before_total_score'],
                    'after_total_score': r['after_total_score'],
                    'before_social_impact': r['before_social_impact'],
                    'after_social_impact': r['after_social_impact'],
                    'adopted': r.get('adopted', False)
                })

    def _save_results(self, results: List[Dict], output_csv: str, original_csv: str):
        """最終結果を保存"""
        # 改善されたエピソードテキストでCSVを更新
        original_data = {}
        with open(original_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                original_data[row['episode_id']] = row

        # 改善結果を反映
        for result in results:
            episode_id = result['episode_id']
            if episode_id in original_data:
                original_data[episode_id]['episode_text'] = result['improved_text']

        # 保存
        with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = list(original_data[next(iter(original_data))].keys())
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for episode_id in sorted(original_data.keys()):
                writer.writerow(original_data[episode_id])

        # 統計JSON保存
        stats_path = output_csv.replace('.csv', '_stats.json')
        with open(stats_path, 'w', encoding='utf-8') as f:
            json.dump(self.stats, f, ensure_ascii=False, indent=2)


def main():
    """メイン実行"""
    import argparse

    parser = argparse.ArgumentParser(description="Phase 9: 社会的影響特化バッチ改善")
    parser.add_argument('--test', action='store_true', help='テストモード（5件のみ）')
    parser.add_argument('--provider', default='openai', choices=['openai', 'anthropic'])
    args = parser.parse_args()

    # 初期化
    improver = SocialImpactBatchImprover(
        provider=args.provider,
        checkpoint_interval=10,
        social_impact_threshold=40.0
    )

    # ターゲット読み込み
    targets_csv = "episodes_phase9_targets.csv"
    targets = improver.load_targets(targets_csv)

    print(f"\n読み込み完了: {len(targets)}件（社会的影響<40点）")

    # バッチ処理
    original_csv = "episodes_phase8_complete.csv"
    if args.test:
        output_csv = "episodes_phase9_test5.csv"
    else:
        output_csv = "episodes_phase9_complete.csv"

    stats = improver.process_batch(
        targets=targets,
        episodes_csv=original_csv,
        output_csv=output_csv,
        test_mode=args.test
    )

    # 結果表示
    print(f"\n{'='*80}")
    print(f"Phase 9 バッチ改善完了")
    print(f"{'='*80}")
    print(f"処理件数: {stats['total_processed']}件")
    print(f"改善成功: {stats['improved']}件 ({stats['improved']/max(stats['total_processed'],1)*100:.1f}%)")
    print(f"改善失敗: {stats['failed']}件")
    print(f"スキップ: {stats['skipped']}件")
    print(f"社会的影響向上: {stats['social_impact_increased']}件")
    print(f"総合スコア向上: {stats['total_score_increased']}件")
    print(f"処理時間: {stats['elapsed_seconds']:.1f}秒 ({stats['elapsed_minutes']:.1f}分)")
    print(f"\n出力ファイル: {output_csv}")
    print(f"統計ファイル: {output_csv.replace('.csv', '_stats.json')}")


if __name__ == "__main__":
    main()
