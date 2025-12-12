#!/usr/bin/env python3
"""
自動生成・品質チェック・修正ループ

エピソード生成→バリデーション→問題修正を自動で繰り返す。

使用方法:
    # 50件を目標に生成ループ実行
    python scripts/auto_generate_loop.py --target 50 --execute

    # 最大3ラウンドまで
    python scripts/auto_generate_loop.py --target 100 --max-rounds 3 --execute

    # ドライラン（実行確認のみ）
    python scripts/auto_generate_loop.py --target 20 --dry-run

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import anthropic

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.pipeline_layer1_generate import run_layer1
from scripts.pipeline_layer2_evaluate import run_layer2
from scripts.episode_validator import validate_episodes, load_episodes, ValidationIssue

# CSVパス
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
STAGING_CSV = PROJECT_ROOT / "generated" / "pipeline_staging.csv"
REPORT_DIR = PROJECT_ROOT / "reports"

# 環境変数チェック
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)

client = anthropic.Anthropic(api_key=API_KEY)


# =============================================================================
# 自動修正機能
# =============================================================================


def fix_placeholder_with_llm(episode: Dict, issue: ValidationIssue) -> Optional[str]:
    """LLMを使ってプレースホルダーを修正"""
    text = episode.get("episode_text", "")
    person_name = episode.get("person_name", "")
    age = episode.get("age", "")

    prompt = f"""以下のエピソードにプレースホルダー（...、○○、〇〇など）が含まれています。
具体的な内容に置き換えて、自然な文章にしてください。

【元のエピソード】
{text}

【修正ルール】
1. 「...」は適切な言葉や「……」に置き換え
2. 「○○」「〇〇」は具体的な単語に置き換え
3. 元の文章の意味や雰囲気を維持
4. 「あなたと同じ{age}歳のとき、{person_name}」の形式を維持

修正後のエピソード（本文のみ出力）:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"    ❌ LLM修正エラー: {e}")
        return None


def fix_format_with_llm(episode: Dict) -> Optional[str]:
    """フォーマット違反をLLMで修正"""
    text = episode.get("episode_text", "")
    person_name = episode.get("person_name", "")
    age = episode.get("age", "")

    prompt = f"""以下のエピソードが「あなたと同じN歳のとき、[人物名]は」の形式で始まっていません。
正しい形式に修正してください。

【元のエピソード】
{text}

【修正ルール】
1. 必ず「あなたと同じ{age}歳のとき、{person_name}は」で始める
2. 元の内容・エピソードの本質は維持
3. 200-350文字程度

修正後のエピソード（本文のみ出力）:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"    ❌ LLM修正エラー: {e}")
        return None


def fix_simple_issues(text: str) -> str:
    """シンプルな問題を正規表現で修正"""
    # ... → ……
    text = re.sub(r"\.{3,}", "……", text)
    # 。。。 → ……
    text = re.sub(r"。{2,}", "……", text)
    return text


def auto_fix_issues(episodes: List[Dict], issues: List[ValidationIssue], use_llm: bool = True) -> Tuple[int, int]:
    """
    検出された問題を自動修正

    Returns: (fixed_count, failed_count)
    """
    # エピソードIDでインデックス
    ep_map = {ep.get("episode_id", ""): ep for ep in episodes}

    fixed = 0
    failed = 0

    # 問題をエピソードIDでグループ化
    issues_by_ep = {}
    for issue in issues:
        if issue.episode_id not in issues_by_ep:
            issues_by_ep[issue.episode_id] = []
        issues_by_ep[issue.episode_id].append(issue)

    for ep_id, ep_issues in issues_by_ep.items():
        if ep_id not in ep_map:
            continue

        ep = ep_map[ep_id]
        text = ep.get("episode_text", "")
        original_text = text
        person_name = ep.get("person_name", "")

        print(f"  [{ep_id}] {person_name}")

        for issue in ep_issues:
            print(f"    修正中: {issue.issue_type}")

            if issue.issue_type == "placeholder":
                # まずシンプル修正を試行
                text = fix_simple_issues(text)

                # まだプレースホルダーが残っている場合はLLM修正
                if use_llm and ("○○" in text or "〇〇" in text or "××" in text):
                    ep["episode_text"] = text
                    fixed_text = fix_placeholder_with_llm(ep, issue)
                    if fixed_text:
                        text = fixed_text
                    time.sleep(0.5)

            elif issue.issue_type == "format_violation" and use_llm:
                fixed_text = fix_format_with_llm(ep)
                if fixed_text:
                    text = fixed_text
                time.sleep(0.5)

            elif issue.issue_type == "meta_expression" and use_llm:
                # メタ表現は再生成が必要
                print("    ⚠️ メタ表現は手動対応が必要")
                failed += 1
                continue

        if text != original_text:
            ep["episode_text"] = text
            fixed += 1
            print("    ✅ 修正完了")
        else:
            if any(i.severity == "CRITICAL" for i in ep_issues):
                failed += 1

    return fixed, failed


def save_staging_csv(episodes: List[Dict]):
    """ステージングCSVを保存"""
    if not episodes:
        return

    fieldnames = list(episodes[0].keys())

    with open(STAGING_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(episodes)


def count_master_episodes() -> int:
    """マスターCSVのエピソード数をカウント"""
    if not MASTER_CSV.exists():
        return 0

    with open(MASTER_CSV, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        return sum(1 for _ in reader)


def run_auto_loop(
    target_count: int,
    max_rounds: int = 5,
    batch_size: int = 20,
    execute: bool = False,
) -> Dict:
    """
    自動生成・品質チェック・修正ループを実行

    Args:
        target_count: 目標エピソード数
        max_rounds: 最大ラウンド数
        batch_size: 1回あたりの生成数
        execute: 本番実行フラグ

    Returns:
        実行結果サマリ
    """
    start_time = datetime.now()
    initial_master_count = count_master_episodes()

    print("=" * 70)
    print("🔄 自動生成・品質チェック・修正ループ")
    print("=" * 70)
    print(f"  目標件数: {target_count}")
    print(f"  最大ラウンド: {max_rounds}")
    print(f"  バッチサイズ: {batch_size}")
    print(f"  実行モード: {'本番' if execute else 'ドライラン'}")
    print(f"  現在のマスター件数: {initial_master_count}")
    print("=" * 70)

    results = {
        "target_count": target_count,
        "initial_master_count": initial_master_count,
        "rounds": [],
        "total_generated": 0,
        "total_accepted": 0,
        "total_fixed": 0,
        "total_failed": 0,
    }

    total_accepted = 0
    round_num = 0

    while total_accepted < target_count and round_num < max_rounds:
        round_num += 1
        remaining = target_count - total_accepted
        current_batch = min(batch_size, remaining + 5)  # 少し余裕を持って

        print(f"\n{'=' * 70}")
        print(f"🔄 ラウンド {round_num}/{max_rounds}")
        print(f"{'=' * 70}")
        print(f"  残り目標: {remaining}件")
        print(f"  今回生成: {current_batch}件")

        round_result = {
            "round": round_num,
            "target": current_batch,
            "generated": 0,
            "accepted": 0,
            "fixed": 0,
            "validation_issues": 0,
        }

        # ========================================
        # Step 1: 生成
        # ========================================
        print("\n📍 Step 1: エピソード生成")
        layer1_result = run_layer1(current_batch, None, execute)
        round_result["generated"] = layer1_result.get("generated", 0)
        results["total_generated"] += round_result["generated"]

        if not round_result["generated"]:
            print("  ⚠️ 生成されたエピソードがありません")
            results["rounds"].append(round_result)
            continue

        # ========================================
        # Step 2: 評価
        # ========================================
        print("\n📍 Step 2: 品質評価")
        layer2_result = run_layer2(None, execute)
        round_result["accepted"] = layer2_result.get("auto_accepted", 0)
        total_accepted += round_result["accepted"]
        results["total_accepted"] += round_result["accepted"]

        # ========================================
        # Step 3: バリデーション
        # ========================================
        print("\n📍 Step 3: バリデーション")
        episodes = load_episodes("pipeline_staging")
        validation_result = validate_episodes(episodes)
        summary = validation_result.summary()

        print(f"  チェック件数: {summary['total_checked']}")
        print(f"  CRITICAL: {summary['critical_count']}")
        print(f"  WARNING: {summary['warning_count']}")

        round_result["validation_issues"] = summary["total_issues"]

        # ========================================
        # Step 4: 自動修正
        # ========================================
        if summary["total_issues"] > 0 and execute:
            print("\n📍 Step 4: 自動修正")
            fixed, failed = auto_fix_issues(episodes, validation_result.issues, use_llm=True)
            round_result["fixed"] = fixed
            results["total_fixed"] += fixed
            results["total_failed"] += failed

            # 修正を保存
            save_staging_csv(episodes)
            print(f"  修正完了: {fixed}件")

            # 再バリデーション
            print("\n📍 Step 4b: 再バリデーション")
            episodes = load_episodes("pipeline_staging")
            validation_result = validate_episodes(episodes)
            summary = validation_result.summary()
            print(f"  残り問題: CRITICAL={summary['critical_count']}, WARNING={summary['warning_count']}")

        results["rounds"].append(round_result)

        print(f"\n📊 ラウンド{round_num}結果:")
        print(f"  生成: {round_result['generated']}件")
        print(f"  採用: {round_result['accepted']}件")
        print(f"  修正: {round_result['fixed']}件")
        print(f"  累計採用: {total_accepted}/{target_count}")

    # ========================================
    # 最終結果
    # ========================================
    end_time = datetime.now()
    elapsed = (end_time - start_time).total_seconds()
    final_master_count = count_master_episodes()

    results["final_master_count"] = final_master_count
    results["net_added"] = final_master_count - initial_master_count
    results["elapsed_seconds"] = round(elapsed, 1)
    results["episodes_per_minute"] = round(results["total_accepted"] / max(1, elapsed / 60), 1)

    print("\n" + "=" * 70)
    print("🎉 ループ完了")
    print("=" * 70)
    print("\n📊 最終結果:")
    print(f"  ラウンド数: {round_num}")
    print(f"  総生成数: {results['total_generated']}")
    print(f"  総採用数: {results['total_accepted']}")
    print(f"  総修正数: {results['total_fixed']}")
    print(f"  マスター増加: {initial_master_count} → {final_master_count} (+{results['net_added']})")
    print(f"  所要時間: {elapsed:.1f}秒")
    print(f"  効率: {results['episodes_per_minute']}件/分")

    if total_accepted >= target_count:
        print(f"\n✅ 目標達成！ ({total_accepted}/{target_count})")
    else:
        print(f"\n⚠️ 目標未達: {total_accepted}/{target_count} ({target_count - total_accepted}件不足)")

    # レポート保存
    if execute:
        REPORT_DIR.mkdir(exist_ok=True)
        report_path = REPORT_DIR / f"auto_loop_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        print(f"\n📝 レポート保存: {report_path}")

    return results


def main():
    parser = argparse.ArgumentParser(description="自動生成・品質チェック・修正ループ")
    parser.add_argument("--target", type=int, default=20, help="目標エピソード数")
    parser.add_argument("--max-rounds", type=int, default=5, help="最大ラウンド数")
    parser.add_argument("--batch-size", type=int, default=20, help="1回あたりの生成数")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    args = parser.parse_args()

    execute = args.execute and not args.dry_run

    run_auto_loop(
        target_count=args.target,
        max_rounds=args.max_rounds,
        batch_size=args.batch_size,
        execute=execute,
    )


if __name__ == "__main__":
    main()
