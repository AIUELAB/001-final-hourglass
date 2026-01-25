#!/usr/bin/env python3
"""
FICTIONAL文頭フォーマット品質ゲート

FICTIONALエピソードの文頭が必ず以下の形式であることを保証する：
「あなたと同じ{age}歳のとき、{name}『{work_title}』は」

Usage:
    python scripts/validation/fictional_lead_gate.py --verify   # 違反件数を確認
    python scripts/validation/fictional_lead_gate.py --details  # 違反詳細を表示
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

# 必須パターン: 「あなたと同じ{age}歳のとき、{name}『{work_title}』は」
FICTIONAL_LEAD_PATTERN = re.compile(r"^あなたと同じ\d+歳のとき、[^『]+『[^』]+』は")

# NG work_title（カテゴリ名・スタジオ名等）
INVALID_WORK_TITLES = frozenset(
    [
        # ジャンル
        "少年漫画",
        "少女漫画",
        "青年漫画",
        "女性漫画",
        "少年ジャンプ",
        "週刊少年マガジン",
        "週刊少年サンデー",
        # スタジオ
        "ディズニー",
        "ピクサー",
        "ピクサー・アニメーション・スタジオ",
        "スタジオジブリ",
        "ジブリ",
        "東映アニメーション",
        "サンライズ",
        "京都アニメーション",
        "Production I.G",
        "MAPPA",
        "ufotable",
        "Wit Studio",
        # メディア種別
        "アニメ",
        "ゲーム",
        "映画",
        "ドラマ",
        "小説",
        "漫画",
        "テレビアニメ",
        "オリジナルアニメ",
        "ライトノベル",
        "OVA",
        "劇場版",
        # その他
        "オリジナル",
        "不明",
        "なし",
        "",
    ]
)


def check_fictional_lead(
    episode_text: str,
    person_type: str,
    work_title: Optional[str] = None,
    person_name: Optional[str] = None,
) -> tuple[bool, str]:
    """
    FICTIONAL文頭フォーマットをチェック

    Args:
        episode_text: エピソードテキスト
        person_type: 人物タイプ（REAL/FICTIONAL）
        work_title: 作品名
        person_name: 人物名（詳細エラー用）

    Returns:
        (準拠しているか, メッセージ)
    """
    # REALはスキップ
    ptype = str(person_type).upper() if person_type else "REAL"
    if "FICTIONAL" not in ptype:
        return True, "REAL: スキップ"

    # テキストが空
    if not episode_text:
        return False, "episode_textが空"

    # 1. 文頭に『作品名』があるか
    if not FICTIONAL_LEAD_PATTERN.match(episode_text):
        return False, f"文頭に『作品名』がありません: {episode_text[:50]}..."

    # 2. work_titleがカテゴリ名でないか
    if work_title and str(work_title) in INVALID_WORK_TITLES:
        return False, f"work_titleがカテゴリ名: {work_title}"

    return True, "OK"


def check_fictional_lead_row(row: dict) -> tuple[bool, str]:
    """
    行データからFICTIONAL文頭チェック（SafeCSVWriter統合用）

    Args:
        row: CSV行データ

    Returns:
        (準拠しているか, メッセージ)
    """
    return check_fictional_lead(
        episode_text=row.get("episode_text", ""),
        person_type=row.get("person_type", ""),
        work_title=row.get("work_title"),
        person_name=row.get("person_name"),
    )


def verify_all_fictional_episodes(df: pd.DataFrame, show_details: bool = False) -> tuple[int, int, list[dict]]:
    """
    全FICTIONALエピソードを検証

    Args:
        df: マスターCSV DataFrame
        show_details: 違反詳細を収集するか

    Returns:
        (合格件数, 違反件数, 違反リスト)
    """
    fictional = df[df["person_type"] == "FICTIONAL"]
    passed = 0
    failed = 0
    violations = []

    for _, row in fictional.iterrows():
        is_valid, msg = check_fictional_lead(
            episode_text=row.get("episode_text", ""),
            person_type=row.get("person_type", ""),
            work_title=row.get("work_title"),
            person_name=row.get("person_name"),
        )

        if is_valid:
            passed += 1
        else:
            failed += 1
            if show_details:
                violations.append(
                    {
                        "episode_id": row.get("episode_id"),
                        "person_name": row.get("person_name"),
                        "work_title": row.get("work_title"),
                        "message": msg,
                        "text_start": str(row.get("episode_text", ""))[:80],
                    }
                )

    return passed, failed, violations


def main():
    parser = argparse.ArgumentParser(description="FICTIONAL文頭フォーマット検証")
    parser.add_argument("--verify", action="store_true", help="違反件数を確認")
    parser.add_argument("--details", action="store_true", help="違反詳細を表示")
    parser.add_argument("--limit", type=int, default=20, help="詳細表示の上限")

    args = parser.parse_args()

    if not args.verify and not args.details:
        args.verify = True

    print(f"📂 マスターCSV: {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV, low_memory=False)
    print(f"📊 総エピソード数: {len(df):,}件")

    fictional_count = len(df[df["person_type"] == "FICTIONAL"])
    print(f"🎭 FICTIONALエピソード数: {fictional_count:,}件")

    passed, failed, violations = verify_all_fictional_episodes(df, args.details)

    print("\n" + "=" * 60)
    print("FICTIONAL文頭フォーマット検証結果")
    print("=" * 60)
    print(f"✅ 合格: {passed:,}件 ({passed / fictional_count * 100:.1f}%)")
    print(f"❌ 違反: {failed:,}件 ({failed / fictional_count * 100:.1f}%)")

    if failed == 0:
        print("\n🎉 全FICTIONALエピソードが文頭フォーマットに準拠しています")
        sys.exit(0)
    else:
        print(f"\n⚠️ {failed}件の違反があります")

        if args.details and violations:
            print("\n" + "-" * 60)
            print(f"違反詳細（最大{args.limit}件）")
            print("-" * 60)
            for v in violations[: args.limit]:
                print(f"\n[{v['episode_id']}] {v['person_name']} ({v['work_title']})")
                print(f"  {v['message']}")
                print(f"  文頭: {v['text_start']}...")

        sys.exit(1)


if __name__ == "__main__":
    main()
