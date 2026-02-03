#!/usr/bin/env python3
"""
Top20 多様性ゲート

上位20件のエピソードにおいて、同一人物（person_id）のエピソードが
制限数を超えていないかチェックする。

これにより、ダッシュボードのTop20が特定の有名人で埋め尽くされることを防ぐ。

Usage:
    python scripts/validation/top20_diversity_gate.py
    python scripts/validation/top20_diversity_gate.py --dry-run
    python scripts/validation/top20_diversity_gate.py --max-per-person 3

Exit codes:
    0: 合格（全person_idが制限以下）
    1: 違反検出
"""

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/top20_diversity_gate_result.json"

# デフォルト制限
MAX_EPISODES_PER_PERSON = 2


@dataclass
class PersonViolation:
    """人物単位の違反情報"""

    person_id: str
    person_name: str
    count: int
    limit: int
    episodes: list  # [{"episode_id", "age", "score"}]


@dataclass
class GateResult:
    """ゲート結果"""

    check_date: str
    score_type: str  # "super_total_score" or "desirability_score"
    passed: bool
    total_violations: int
    violations: list  # [PersonViolation]
    top20_episodes: list  # Top20のエピソード一覧


def load_episodes() -> list[dict]:
    """マスターCSVからエピソードを読み込む"""
    episodes = []
    with open(MASTER_CSV, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)
    return episodes


def get_top20_by_score(episodes: list[dict], score_field: str) -> list[dict]:
    """指定スコアでソートしてTop20を取得"""
    # スコアが有効なエピソードのみ抽出
    valid_episodes = []
    for ep in episodes:
        score_str = ep.get(score_field, "")
        if score_str:
            try:
                score = float(score_str)
                ep["_sort_score"] = score
                valid_episodes.append(ep)
            except (ValueError, TypeError):
                pass

    # スコア降順でソート
    valid_episodes.sort(key=lambda x: x["_sort_score"], reverse=True)

    return valid_episodes[:20]


def check_diversity(top20: list[dict], score_field: str, max_per_person: int) -> GateResult:
    """Top20の多様性をチェック"""
    # person_id別にグループ化
    person_episodes = defaultdict(list)

    for ep in top20:
        person_id = ep.get("person_id", "")
        person_name = ep.get("person_name", "Unknown")
        episode_id = ep.get("episode_id", "")
        age = ep.get("age", "?")
        score = ep.get("_sort_score", 0)

        if person_id:
            person_episodes[person_id].append(
                {
                    "episode_id": episode_id,
                    "person_name": person_name,
                    "age": age,
                    "score": score,
                }
            )

    # 違反検出
    violations = []
    for person_id, eps in person_episodes.items():
        if len(eps) > max_per_person:
            violations.append(
                PersonViolation(
                    person_id=person_id,
                    person_name=eps[0]["person_name"],
                    count=len(eps),
                    limit=max_per_person,
                    episodes=eps,
                )
            )

    # 違反数でソート（多い順）
    violations.sort(key=lambda x: x.count, reverse=True)

    # Top20エピソード一覧を作成
    top20_list = [
        {
            "rank": i + 1,
            "episode_id": ep.get("episode_id", ""),
            "person_name": ep.get("person_name", ""),
            "age": ep.get("age", ""),
            "score": ep.get("_sort_score", 0),
        }
        for i, ep in enumerate(top20)
    ]

    return GateResult(
        check_date=datetime.now().isoformat(),
        score_type=score_field,
        passed=len(violations) == 0,
        total_violations=len(violations),
        violations=[asdict(v) for v in violations],
        top20_episodes=top20_list,
    )


def print_result(result: GateResult, dry_run: bool = False):
    """結果を出力"""
    print("\n" + "━" * 50)
    print(" Top20 多様性ゲート")
    print("━" * 50)
    print(f"📊 チェック対象: {result.score_type} Top20")

    if result.passed:
        print(f"✅ 合格: 全person_idが{MAX_EPISODES_PER_PERSON}件以下")
    else:
        print(f"❌ 違反検出: {result.total_violations}人")
        for v in result.violations:
            print(f"\n  - {v['person_name']}: {v['count']}件（制限: {v['limit']}件）")
            for ep in v["episodes"]:
                print(f"    - {ep['episode_id']} ({ep['age']}歳): {ep['score']:,.0f}")

    if dry_run:
        print("\n--- Top20 一覧 ---")
        for ep in result.top20_episodes:
            print(f"  {ep['rank']:2d}. {ep['person_name']} ({ep['age']}歳): {ep['score']:,.0f}")

    print("━" * 50)


def main():
    parser = argparse.ArgumentParser(description="Top20 多様性ゲート - 同一人物の偏りをチェック")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="詳細出力（Top20一覧を表示）",
    )
    parser.add_argument(
        "--max-per-person",
        type=int,
        default=MAX_EPISODES_PER_PERSON,
        help=f"同一人物の最大許容件数（デフォルト: {MAX_EPISODES_PER_PERSON}）",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=str(MASTER_CSV),
        help="チェック対象のCSVファイル",
    )
    args = parser.parse_args()

    # CSVパス更新
    csv_path = Path(args.csv)
    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return 1

    # エピソード読み込み
    print(f"📂 Loading: {csv_path}")
    episodes = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)
    print(f"   Total episodes: {len(episodes)}")

    # チェック対象スコア
    score_fields = ["super_total_score", "desirability_score"]
    all_results = []
    has_violation = False

    for score_field in score_fields:
        # Top20取得
        top20 = get_top20_by_score(episodes, score_field)
        if len(top20) < 20:
            print(f"⚠️ {score_field}: 有効なエピソードが20件未満（{len(top20)}件）")

        # 多様性チェック
        result = check_diversity(top20, score_field, args.max_per_person)
        all_results.append(asdict(result))

        # 結果出力
        print_result(result, args.dry_run)

        if not result.passed:
            has_violation = True

    # レポート出力
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "gate_name": "top20_diversity_gate",
        "check_date": datetime.now().isoformat(),
        "max_per_person": args.max_per_person,
        "overall_passed": not has_violation,
        "results": all_results,
    }
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📝 レポート保存: {REPORT_PATH}")

    # 終了コード
    if has_violation:
        print("\n❌ ゲート失敗: 違反が検出されました")
        return 1
    else:
        print("\n✅ ゲート通過: 全チェック合格")
        return 0


if __name__ == "__main__":
    sys.exit(main())
