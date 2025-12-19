#!/usr/bin/env python3
"""
バッチLLM評価スクリプト

複数エピソードを一括でLLM評価し、結果をCSVに保存する。
コスト効率化とレート制限対策を考慮した設計。

Usage:
    # ドライラン（対象確認のみ）
    python scripts/batch_llm_evaluate.py --dry-run --count 10

    # 実行（評価済みスキップ、結果保存）
    python scripts/batch_llm_evaluate.py --execute --count 50 --save

    # 全件評価（評価済みも再評価）
    python scripts/batch_llm_evaluate.py --execute --count 100 --no-skip-evaluated --save
"""

import argparse
import csv
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class BatchLLMEvaluator:
    """バッチLLM評価クラス"""

    def __init__(
        self,
        csv_path: Optional[str] = None,
        delay: float = 1.0,
        save_to_csv: bool = False,
    ):
        """
        Args:
            csv_path: CSVファイルのパス
            delay: API呼び出し間隔（秒）
            save_to_csv: 結果をCSVに保存するか
        """
        self.csv_path = Path(csv_path or project_root / "preserved/data/MASTER_EPISODES_CURRENT.csv")
        self.delay = delay
        self.save_to_csv = save_to_csv
        self.stats = {
            "total": 0,
            "success": 0,
            "skipped": 0,
            "error": 0,
            "already_evaluated": 0,
        }
        self.results: List[Dict] = []
        self.episodes: List[Dict] = []

        # LLMスコアのフィールドマッピング（日本語軸名→CSVカラム名）
        self.llm_field_mapping = {
            "記憶性": "llm_memorability_score",
            "共感性": "llm_empathy_score",
            "意外性": "llm_surprise_score",
            "生成品質": "llm_generation_quality_score",
            "教育的価値": "llm_educational_value",
            "ストーリー品質": "llm_storytelling_quality",
            "事実密度": "llm_factual_density",
        }

    def load_episodes(self) -> None:
        """CSVからエピソードを読み込み"""
        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSVファイルが見つかりません: {self.csv_path}")

        with open(self.csv_path, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self.episodes = list(reader)

        print(f"✅ {len(self.episodes)}件のエピソードを読み込み")

    def save_episodes(self) -> None:
        """エピソードをCSVに保存"""
        if not self.episodes:
            return

        fieldnames = list(self.episodes[0].keys())

        # バックアップ作成
        backup_path = self.csv_path.with_suffix(".csv.backup")
        import shutil

        shutil.copy(self.csv_path, backup_path)

        with open(self.csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.episodes)

        print(f"✅ CSVに保存完了: {self.csv_path}")

    def is_already_evaluated(self, episode: Dict) -> bool:
        """エピソードが既に評価済みかどうかを判定"""
        evaluated_at = episode.get("llm_evaluated_at", "")
        return bool(evaluated_at and evaluated_at.strip())

    def get_target_episodes(
        self,
        count: int,
        skip_evaluated: bool = True,
        filter_person_type: Optional[str] = None,
    ) -> List[Dict]:
        """評価対象エピソードを取得

        Args:
            count: 取得件数
            skip_evaluated: 評価済みをスキップするか
            filter_person_type: 人物タイプでフィルタ（REAL/FICTIONAL）

        Returns:
            評価対象エピソードのリスト
        """
        targets = []

        for ep in self.episodes:
            # episode_textがないものはスキップ
            episode_text = ep.get("episode_text", "")
            if not episode_text or len(episode_text) < 50:
                continue

            # 人物タイプでフィルタ
            if filter_person_type:
                if ep.get("person_type") != filter_person_type:
                    continue

            # 評価済みスキップ
            if skip_evaluated and self.is_already_evaluated(ep):
                continue

            targets.append(ep)

            if len(targets) >= count:
                break

        return targets

    def evaluate_single(
        self,
        episode: Dict,
        client,
        calibrate: bool = True,
    ) -> Optional[Dict]:
        """単一エピソードを評価

        Args:
            episode: エピソードデータ
            client: Anthropicクライアント
            calibrate: キャリブレーションを行うか

        Returns:
            評価結果（失敗時はNone）
        """
        from backend.app.utils.score_calculator import (
            calculate_hybrid_rule_scores,
            calculate_hybrid_scores_dynamic,
            detect_episode_characteristics,
            evaluate_with_llm,
        )

        episode_text = str(episode.get("episode_text", ""))
        episode_id = episode.get("episode_id", "")
        person_id = episode.get("person_id", "")
        person_name = episode.get("person_name", "")

        try:
            # 特性検出
            chars = detect_episode_characteristics(episode_text)

            # ルールベーススコア
            rule_scores = calculate_hybrid_rule_scores(episode)

            # LLM評価
            llm_scores = evaluate_with_llm(episode_text, client=client, calibrate=calibrate)

            if llm_scores is None:
                return None

            # ハイブリッドスコア（動的重み）
            hybrid_scores = calculate_hybrid_scores_dynamic(episode, llm_scores, use_dynamic_weights=True)

            return {
                "episode_id": episode_id,
                "person_id": person_id,
                "person_name": person_name,
                "characteristics": chars,
                "rule_scores": rule_scores,
                "llm_scores": llm_scores,
                "hybrid_scores": hybrid_scores,
            }

        except Exception as e:
            print(f"\n  ⚠️ 評価エラー ({person_name}): {e}")
            return None

    def update_episode_with_scores(self, episode_id: str, llm_scores: Dict) -> bool:
        """エピソードデータをLLMスコアで更新

        Args:
            episode_id: エピソードの一意ID
            llm_scores: LLM評価結果

        Returns:
            更新成功かどうか
        """
        for ep in self.episodes:
            if ep.get("episode_id") == episode_id:
                # LLMスコアを保存
                for jp_name, eng_col in self.llm_field_mapping.items():
                    if jp_name in llm_scores:
                        ep[eng_col] = str(round(llm_scores[jp_name], 2))

                # 評価日時を保存
                ep["llm_evaluated_at"] = datetime.now().isoformat()
                return True

        return False

    def evaluate_batch(
        self,
        count: int = 50,
        skip_evaluated: bool = True,
        filter_person_type: Optional[str] = None,
        calibrate: bool = True,
        dry_run: bool = False,
    ) -> Dict:
        """バッチ評価を実行

        Args:
            count: 評価件数
            skip_evaluated: 評価済みをスキップするか
            filter_person_type: 人物タイプでフィルタ
            calibrate: キャリブレーションを行うか
            dry_run: ドライランモード

        Returns:
            評価結果サマリー
        """
        # エピソード読み込み
        self.load_episodes()

        # 評価対象を取得
        targets = self.get_target_episodes(
            count=count,
            skip_evaluated=skip_evaluated,
            filter_person_type=filter_person_type,
        )

        self.stats["total"] = len(targets)

        # 評価済みの数をカウント
        if skip_evaluated:
            evaluated_count = sum(1 for ep in self.episodes if self.is_already_evaluated(ep))
            self.stats["already_evaluated"] = evaluated_count
            print(f"📊 評価済み: {evaluated_count}件（スキップ対象）")

        print(f"📊 評価対象: {len(targets)}件")

        if dry_run:
            print("\n🔍 ドライランモード（実行しません）")
            print("\n対象エピソード:")
            for i, ep in enumerate(targets[:20], 1):
                person_name = ep.get("person_name", "不明")
                age = ep.get("age", "?")
                episode_type = ep.get("episode_type", "?")
                print(f"  {i}. {person_name} ({age}歳) - {episode_type}")

            if len(targets) > 20:
                print(f"  ... 他 {len(targets) - 20}件")

            return self.stats

        if not targets:
            print("⚠️ 評価対象がありません")
            return self.stats

        # Anthropicクライアント初期化
        try:
            import anthropic

            client = anthropic.Anthropic()
        except Exception as e:
            print(f"❌ Anthropic APIクライアント作成失敗: {e}")
            return self.stats

        # バッチ評価実行
        print(f"\n🚀 バッチ評価開始（{len(targets)}件）")
        start_time = time.time()

        for i, episode in enumerate(targets):
            person_name = episode.get("person_name", "不明")
            print(f"\r評価中: [{i + 1}/{len(targets)}] {person_name[:20]:<20}", end="", flush=True)

            result = self.evaluate_single(episode, client, calibrate=calibrate)

            if result:
                self.stats["success"] += 1
                self.results.append(result)

                # CSVに保存する場合、エピソードデータを更新
                if self.save_to_csv:
                    self.update_episode_with_scores(
                        result["episode_id"],
                        result["llm_scores"],
                    )
            else:
                self.stats["error"] += 1

            # レート制限対策
            if i < len(targets) - 1:
                time.sleep(self.delay)

        elapsed = time.time() - start_time
        print(f"\n\n✅ 評価完了（{elapsed:.1f}秒）")

        # CSVに保存
        if self.save_to_csv and self.stats["success"] > 0:
            self.save_episodes()

        return self.stats

    def generate_report(self, output_dir: Optional[str] = None) -> str:
        """評価レポートを生成

        Args:
            output_dir: 出力ディレクトリ

        Returns:
            レポートファイルのパス
        """
        output_path = Path(output_dir or project_root / "reports")
        output_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = output_path / f"batch_llm_evaluate_{timestamp}.json"

        report = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "results": self.results,
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2, default=str)

        print(f"📄 レポート保存: {report_path}")
        return str(report_path)


def main():
    parser = argparse.ArgumentParser(description="バッチLLM評価スクリプト")
    parser.add_argument("--count", type=int, default=50, help="評価件数（デフォルト: 50）")
    parser.add_argument("--delay", type=float, default=1.0, help="API呼び出し間隔（秒、デフォルト: 1.0）")
    parser.add_argument(
        "--skip-evaluated",
        action="store_true",
        default=True,
        help="評価済みをスキップ（デフォルト: ON）",
    )
    parser.add_argument(
        "--no-skip-evaluated",
        action="store_true",
        help="評価済みも再評価",
    )
    parser.add_argument("--person-type", choices=["REAL", "FICTIONAL"], help="人物タイプでフィルタ")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（対象確認のみ）")
    parser.add_argument("--execute", action="store_true", help="実際に評価を実行")
    parser.add_argument("--save", action="store_true", help="結果をCSVに保存")
    parser.add_argument("--no-calibrate", action="store_true", help="キャリブレーションを無効化")
    parser.add_argument("--csv-path", help="CSVファイルのパス")

    args = parser.parse_args()

    # 実行モードチェック
    if not args.dry_run and not args.execute:
        print("⚠️ --dry-run または --execute を指定してください")
        print("\n使用例:")
        print("  # ドライラン（対象確認）")
        print("  python scripts/batch_llm_evaluate.py --dry-run --count 10")
        print("\n  # 実行（評価済みスキップ、結果保存）")
        print("  python scripts/batch_llm_evaluate.py --execute --count 50 --save")
        return

    print("=" * 70)
    print("バッチLLM評価")
    print("=" * 70)

    # 評価済みスキップの判定
    skip_evaluated = args.skip_evaluated and not args.no_skip_evaluated

    print(f"評価件数: {args.count}")
    print(f"API間隔: {args.delay}秒")
    print(f"評価済みスキップ: {'ON' if skip_evaluated else 'OFF'}")
    print(f"CSV保存: {'ON' if args.save else 'OFF'}")
    if args.person_type:
        print(f"人物タイプ: {args.person_type}")

    # バッチ評価実行
    evaluator = BatchLLMEvaluator(
        csv_path=args.csv_path,
        delay=args.delay,
        save_to_csv=args.save,
    )

    stats = evaluator.evaluate_batch(
        count=args.count,
        skip_evaluated=skip_evaluated,
        filter_person_type=args.person_type,
        calibrate=not args.no_calibrate,
        dry_run=args.dry_run,
    )

    # 結果サマリー
    print("\n" + "=" * 70)
    print("結果サマリー")
    print("=" * 70)
    print(f"対象件数: {stats['total']}")
    print(f"成功: {stats['success']}")
    print(f"エラー: {stats['error']}")
    if stats.get("already_evaluated"):
        print(f"評価済み（スキップ対象）: {stats['already_evaluated']}")

    # レポート生成（実行時のみ）
    if args.execute and evaluator.results:
        evaluator.generate_report()


if __name__ == "__main__":
    main()
