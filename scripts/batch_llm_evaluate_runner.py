#!/usr/bin/env python3
"""
耐障害バッチLLM評価ランナー（既存スクリプト非改変）

目的:
- `scripts/batch_llm_evaluate.py` のロジックはそのまま利用しつつ、
  途中停止（タイムアウト/セッション切断/手動停止）に強い運用を可能にする。

主な追加機能:
- 5分ごとのチェックポイント保存（CSVへ安全に書き込み）
- 失敗時の軽いリトライ（指数バックオフ + ジッタ）
- SIGINT/SIGTERM を受けたときに、できるだけ安全に保存して終了

注意:
- このランナーは「途中まで評価した分も失わない」ために、途中でCSVへ保存します。
  そのため “全件完了まで一切保存しない” という厳密なトランザクションにはなりません。
  ただし、各保存はバックアップ作成 → 書き込み（既存実装）で安全性を担保します。

Usage:
  # 5分ごとにチェックポイント保存しながら実行（評価済みはスキップ）
  python scripts/batch_llm_evaluate_runner.py --execute --count 6000 --save --checkpoint-seconds 300
"""

from __future__ import annotations

import argparse
import random
import signal
import time
from typing import Optional

# 同じscriptsディレクトリ内の既存実装を再利用
from batch_llm_evaluate import BatchLLMEvaluator


class GracefulShutdown:
    """SIGINT/SIGTERMを受けたら、次の安全なタイミングで停止するためのフラグ。"""

    def __init__(self) -> None:
        self._requested = False

    def request(self, *_args) -> None:
        self._requested = True

    @property
    def requested(self) -> bool:
        return self._requested


def _sleep_with_shutdown(seconds: float, shutdown: GracefulShutdown) -> None:
    """長いsleepを細切れにして、停止要求が来たら早めに抜ける。"""

    end_time = time.monotonic() + max(0.0, seconds)
    while time.monotonic() < end_time:
        if shutdown.requested:
            return
        time.sleep(min(0.5, end_time - time.monotonic()))


def _evaluate_with_retry(
    evaluator: BatchLLMEvaluator,
    episode: dict,
    client,
    calibrate: bool,
    *,
    max_retries: int,
    retry_initial_seconds: float,
    retry_max_seconds: float,
    retry_jitter_seconds: float,
    shutdown: GracefulShutdown,
) -> Optional[dict]:
    """単一評価をリトライ付きで実行（既存のevaluate_singleを包む）。"""

    # max_retries=3 のとき「最大4回試す」
    max_attempts = max(1, max_retries + 1)

    for attempt in range(1, max_attempts + 1):
        if shutdown.requested:
            return None

        try:
            result = evaluator.evaluate_single(episode, client, calibrate=calibrate)
        except Exception as e:
            # 既存evaluate_singleも例外を握ってNoneを返す設計だが、念のため。
            person_name = episode.get("person_name", "不明")
            print(f"\n  ⚠️ 例外で評価失敗（{person_name}）: {e}")
            result = None

        if result:
            return result

        # 失敗したが、まだリトライ可能
        if attempt < max_attempts:
            backoff = min(retry_initial_seconds * (2 ** (attempt - 1)), retry_max_seconds)
            jitter = random.uniform(0.0, max(0.0, retry_jitter_seconds))
            wait_seconds = backoff + jitter
            print(f"\n  ↻ リトライ待機: {wait_seconds:.1f}秒（{attempt}/{max_attempts - 1}）")
            _sleep_with_shutdown(wait_seconds, shutdown)

    return None


def evaluate_batch_with_checkpoints(
    *,
    csv_path: Optional[str],
    count: int,
    delay: float,
    skip_evaluated: bool,
    person_type: Optional[str],
    calibrate: bool,
    dry_run: bool,
    execute: bool,
    save_to_csv: bool,
    checkpoint_seconds: int,
    max_retries: int,
    retry_initial_seconds: float,
    retry_max_seconds: float,
    retry_jitter_seconds: float,
) -> int:
    """チェックポイント保存付きでバッチ評価を実行。戻り値は終了コード。"""

    shutdown = GracefulShutdown()
    signal.signal(signal.SIGINT, shutdown.request)
    signal.signal(signal.SIGTERM, shutdown.request)

    evaluator = BatchLLMEvaluator(
        csv_path=csv_path,
        delay=delay,
        save_to_csv=save_to_csv,
    )

    # エピソード読み込み
    evaluator.load_episodes()

    # 評価対象を取得
    targets = evaluator.get_target_episodes(
        count=count,
        skip_evaluated=skip_evaluated,
        filter_person_type=person_type,
    )

    evaluator.stats["total"] = len(targets)

    # 評価済みの数をカウント（既存スクリプトに合わせる）
    if skip_evaluated:
        evaluated_count = sum(1 for ep in evaluator.episodes if evaluator.is_already_evaluated(ep))
        evaluator.stats["already_evaluated"] = evaluated_count
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

        return 0

    if not execute:
        print("⚠️ --execute を指定してください（このランナーは実行モード専用です）")
        return 2

    if not targets:
        print("⚠️ 評価対象がありません")
        return 0

    # Anthropicクライアント初期化（既存スクリプト同様）
    try:
        import anthropic

        client = anthropic.Anthropic()
    except Exception as e:
        print(f"❌ Anthropic APIクライアント作成失敗: {e}")
        return 1

    print(f"\n🚀 バッチ評価開始（{len(targets)}件）")
    start_time = time.monotonic()
    last_checkpoint_time = start_time
    last_saved_success = 0

    try:
        for i, episode in enumerate(targets):
            if shutdown.requested:
                print("\n\n⏹ 停止要求を検知しました。安全に終了処理へ移行します。")
                break

            person_name = episode.get("person_name", "不明")
            print(f"\r評価中: [{i + 1}/{len(targets)}] {person_name[:20]:<20}", end="", flush=True)

            result = _evaluate_with_retry(
                evaluator,
                episode,
                client,
                calibrate,
                max_retries=max_retries,
                retry_initial_seconds=retry_initial_seconds,
                retry_max_seconds=retry_max_seconds,
                retry_jitter_seconds=retry_jitter_seconds,
                shutdown=shutdown,
            )

            if result:
                evaluator.stats["success"] += 1
                evaluator.results.append(result)

                if save_to_csv:
                    evaluator.update_episode_with_scores(
                        result["episode_id"],
                        result["llm_scores"],
                    )
            else:
                evaluator.stats["error"] += 1

            # レート制限対策
            if i < len(targets) - 1:
                _sleep_with_shutdown(delay, shutdown)

            # チェックポイント保存（一定時間ごとにCSVへ反映）
            if save_to_csv and checkpoint_seconds > 0:
                now = time.monotonic()
                if (now - last_checkpoint_time) >= checkpoint_seconds and evaluator.stats["success"] > last_saved_success:
                    print("\n\n📝 チェックポイント保存を実行します…")
                    evaluator.save_episodes()
                    last_checkpoint_time = now
                    last_saved_success = evaluator.stats["success"]

    except KeyboardInterrupt:
        # SIGINTを受けた場合など
        print("\n\n⏹ 中断されました。可能な範囲で保存して終了します。")

    elapsed = time.monotonic() - start_time
    print(f"\n\n✅ 評価終了（{elapsed:.1f}秒）")

    # 最終保存（保存モードかつ成功がある場合）
    if save_to_csv and evaluator.stats["success"] > 0:
        print("📝 最終保存を実行します…")
        evaluator.save_episodes()

    # レポート生成（既存に合わせる）
    if evaluator.results:
        evaluator.generate_report()

    # 結果サマリー
    print("\n" + "=" * 70)
    print("結果サマリー")
    print("=" * 70)
    print(f"対象件数: {evaluator.stats['total']}")
    print(f"成功: {evaluator.stats['success']}")
    print(f"エラー: {evaluator.stats['error']}")
    if evaluator.stats.get("already_evaluated"):
        print(f"評価済み（スキップ対象）: {evaluator.stats['already_evaluated']}")

    return 0 if evaluator.stats["error"] == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="耐障害バッチLLM評価ランナー（5分チェックポイント保存）")
    parser.add_argument("--count", type=int, default=50, help="評価件数（デフォルト: 50）")
    parser.add_argument("--delay", type=float, default=1.0, help="API呼び出し間隔（秒、デフォルト: 1.0）")
    parser.add_argument(
        "--skip-evaluated",
        action="store_true",
        default=True,
        help="評価済みをスキップ（デフォルト: ON）",
    )
    parser.add_argument("--no-skip-evaluated", action="store_true", help="評価済みも再評価")
    parser.add_argument("--person-type", choices=["REAL", "FICTIONAL"], help="人物タイプでフィルタ")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（対象確認のみ）")
    parser.add_argument("--execute", action="store_true", help="実際に評価を実行")
    parser.add_argument("--save", action="store_true", help="結果をCSVに保存")
    parser.add_argument("--no-calibrate", action="store_true", help="キャリブレーションを無効化")
    parser.add_argument("--csv-path", help="CSVファイルのパス")

    # 追加: 耐障害化オプション
    parser.add_argument(
        "--checkpoint-seconds",
        type=int,
        default=300,
        help="チェックポイント保存間隔（秒、デフォルト: 300 = 5分）",
    )
    parser.add_argument("--max-retries", type=int, default=3, help="失敗時の最大リトライ回数（デフォルト: 3）")
    parser.add_argument(
        "--retry-initial-seconds",
        type=float,
        default=2.0,
        help="リトライ初期待機（秒、デフォルト: 2.0）",
    )
    parser.add_argument(
        "--retry-max-seconds",
        type=float,
        default=30.0,
        help="リトライ待機の上限（秒、デフォルト: 30.0）",
    )
    parser.add_argument(
        "--retry-jitter-seconds",
        type=float,
        default=1.0,
        help="待機時間に足す乱数（秒、デフォルト: 1.0）",
    )

    args = parser.parse_args()

    # 実行モードチェック（既存スクリプトに合わせる）
    if not args.dry_run and not args.execute:
        print("⚠️ --dry-run または --execute を指定してください")
        print("\n使用例:")
        print("  # ドライラン（対象確認）")
        print("  python scripts/batch_llm_evaluate_runner.py --dry-run --count 10")
        print("\n  # 実行（5分ごとにチェックポイント保存）")
        print(
            "  python scripts/batch_llm_evaluate_runner.py --execute --count 6000 --save --checkpoint-seconds 300"
        )
        return 2

    # 評価済みスキップの判定
    skip_evaluated = args.skip_evaluated and not args.no_skip_evaluated

    print("=" * 70)
    print("バッチLLM評価（耐障害ランナー）")
    print("=" * 70)
    print(f"評価件数: {args.count}")
    print(f"API間隔: {args.delay}秒")
    print(f"評価済みスキップ: {'ON' if skip_evaluated else 'OFF'}")
    print(f"CSV保存: {'ON' if args.save else 'OFF'}")
    print(f"チェックポイント間隔: {args.checkpoint_seconds}秒")
    if args.person_type:
        print(f"人物タイプ: {args.person_type}")

    return evaluate_batch_with_checkpoints(
        csv_path=args.csv_path,
        count=args.count,
        delay=args.delay,
        skip_evaluated=skip_evaluated,
        person_type=args.person_type,
        calibrate=not args.no_calibrate,
        dry_run=args.dry_run,
        execute=args.execute,
        save_to_csv=args.save,
        checkpoint_seconds=args.checkpoint_seconds,
        max_retries=args.max_retries,
        retry_initial_seconds=args.retry_initial_seconds,
        retry_max_seconds=args.retry_max_seconds,
        retry_jitter_seconds=args.retry_jitter_seconds,
    )


if __name__ == "__main__":
    raise SystemExit(main())

