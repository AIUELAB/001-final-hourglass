#!/usr/bin/env python3
"""
メタ表現違反検出・修正スクリプト

対象パターン:
1. 声優/キャスト言及 (81件予想)
2. 物語言及 (19件予想)
3. 原作言及 (2件予想)
"""

import pandas as pd
import re
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent

# メタ表現パターン
META_EXPRESSION_PATTERNS = {
    "声優/キャスト言及": [
        r"声優",
        r"キャスト",
        r"演じ[たてるられ]",
        r"が演じる",
        r"を演じ",
    ],
    "物語言及": [
        r"物語(の中)?で",
        r"物語の",
        r"ストーリー(の中)?で",
    ],
    "原作言及": [
        r"原作(では|において|の中で|で)",
        r"原作版",
    ],
}


def detect_meta_expression_violations(csv_path: str) -> dict:
    """
    メタ表現違反を検出

    Returns:
        カテゴリ別の違反エピソードリスト
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    violations = defaultdict(list)
    all_violations = []

    for idx, row in df.iterrows():
        person_type = str(row.get("person_type", "")).upper()
        episode_text = str(row.get("episode_text", ""))

        # FICTIONALのエピソードのみチェック
        if "FICTIONAL" not in person_type:
            continue

        detected = []
        for category, patterns in META_EXPRESSION_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, episode_text):
                    detected.append((category, pattern))
                    break  # 同カテゴリ内で最初のマッチのみ

        if detected:
            violation_info = {
                "index": idx,
                "episode_id": row.get("episode_id", ""),
                "person_id": row.get("person_id", ""),
                "person_name": row.get("person_name", ""),
                "age": row.get("age", ""),
                "work_title": row.get("work_title", ""),
                "episode_text": episode_text,
                "detected_patterns": detected,
                "categories": list(set(c for c, p in detected)),
            }
            all_violations.append(violation_info)

            for category, pattern in detected:
                violations[category].append(violation_info)

    return {
        "by_category": dict(violations),
        "all": all_violations,
        "summary": {category: len(items) for category, items in violations.items()},
    }


def generate_report(violations: dict) -> str:
    """検出結果レポート生成"""
    lines = []
    lines.append("=" * 70)
    lines.append("メタ表現違反検出レポート")
    lines.append(f"検出日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)
    lines.append("")

    # サマリー
    lines.append("【サマリー】")
    total = len(violations["all"])
    lines.append(f"  総違反件数: {total}件")
    for category, count in violations["summary"].items():
        lines.append(f"  - {category}: {count}件")
    lines.append("")

    # カテゴリ別詳細
    for category, items in violations["by_category"].items():
        lines.append("-" * 70)
        lines.append(f"【{category}】({len(items)}件)")
        lines.append("-" * 70)

        for i, ep in enumerate(items[:10], 1):  # 各カテゴリ最大10件表示
            lines.append(f"\n  [{i}] {ep['person_name']} ({ep['age']}歳) - {ep['work_title']}")
            lines.append(f"      episode_id: {ep['episode_id']}")
            # 検出パターンを含む箇所を抽出
            text = ep["episode_text"]
            for cat, pattern in ep["detected_patterns"]:
                match = re.search(pattern, text)
                if match:
                    start = max(0, match.start() - 20)
                    end = min(len(text), match.end() + 20)
                    context = text[start:end]
                    lines.append(f"      検出: ...{context}...")

        if len(items) > 10:
            lines.append(f"\n  ...他 {len(items) - 10}件")

    return "\n".join(lines)


def main():
    """メイン処理"""
    csv_path = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return

    print("🔍 メタ表現違反を検出中...")
    violations = detect_meta_expression_violations(str(csv_path))

    # レポート出力
    report = generate_report(violations)
    print(report)

    # レポート保存
    report_dir = PROJECT_ROOT / "src" / "reports" / "logs"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"meta_expression_violations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"\n📄 レポート保存: {report_path}")

    # 違反episode_idリスト出力
    if violations["all"]:
        print("\n【違反episode_idリスト】")
        for ep in violations["all"]:
            print(ep["episode_id"])

    return violations


if __name__ == "__main__":
    main()
