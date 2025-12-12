#!/usr/bin/env python3
"""
問題のあるエピソードを検出するスクリプト

検出対象:
1. 未来エピソード（2024年以降の年齢に基づく）
2. 高スコア（fame>=95）だが内容が曖昧なエピソード
3. ACHIEVEMENTだが具体的達成がないエピソード
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime

import pandas as pd

# 有名人の生年データ（主要な人物のみ）
BIRTH_YEARS = {
    "堺雅人": 1973,
    "トニー・ベネット": 1926,
    "ヘンリー・キッシンジャー": 1923,
    "ハルク・ホーガン": 1953,
    "マイルス・デイヴィス": 1926,
    "パット・メセニー": 1954,
    "ジミー・ペイジ": 1944,
    "ジェフ・ベック": 1944,
    "ブライアン・イーノ": 1948,
    "ボビー・マクファーリン": 1950,
}

# 曖昧な表現のパターン
VAGUE_PATTERNS = [
    r"続けていました",
    r"挑戦し続けて",
    r"円熟期を迎え",
    r"変わらず.*活動",
    r"精力的に",
    r"さらなる",
    r"より一層",
    r"ますます",
    r"深めて",
    r"広げて",
]

# 具体的な達成を示すパターン
ACHIEVEMENT_PATTERNS = [
    r"\d{4}年.*(?:受賞|獲得|達成|記録|突破|発表|出版|リリース)",
    r"(?:グラミー|アカデミー|ノーベル|オリンピック|世界選手権)",
    r"(?:金メダル|銀メダル|銅メダル|優勝|準優勝)",
    r"(?:売上|視聴率|動員).*(?:\d+|記録)",
    r"(?:初|史上最|世界初|日本初)",
]


def load_master_data(filepath: str) -> pd.DataFrame:
    """マスターデータを読み込む"""
    return pd.read_csv(filepath)


def estimate_birth_year_from_wiki(person_name: str) -> int | None:
    """Wikipediaなどから生年を推定（将来的にAPI連携予定）"""
    return BIRTH_YEARS.get(person_name)


def is_future_episode(row: pd.Series, current_year: int = 2024) -> bool:
    """未来のエピソードかどうかを判定"""
    if row.get("person_type") != "REAL":
        return False

    birth_year = estimate_birth_year_from_wiki(row.get("person_name", ""))
    if birth_year:
        episode_year = birth_year + int(row.get("age", 0))
        return episode_year > current_year

    return False


def has_vague_content(text: str) -> list[str]:
    """曖昧な表現が含まれているかチェック"""
    if not isinstance(text, str):
        return []
    matches = []
    for pattern in VAGUE_PATTERNS:
        if re.search(pattern, text):
            matches.append(pattern)
    return matches


def has_concrete_achievement(text: str) -> bool:
    """具体的な達成が記載されているかチェック"""
    if not isinstance(text, str):
        return False
    for pattern in ACHIEVEMENT_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def analyze_episode(row: pd.Series) -> dict:
    """エピソードを分析して問題点を返す"""
    issues = []
    severity = 0  # 0: OK, 1: 軽度, 2: 中度, 3: 重度

    episode_text = str(row.get("episode_text", ""))
    episode_type = row.get("episode_type", "")
    fame_score = row.get("episode_fame_score", 0)

    # 未来エピソードチェック
    if is_future_episode(row):
        issues.append("未来のエピソード（2024年以降）")
        severity = max(severity, 3)

    # 高スコアだが曖昧な内容
    vague_matches = has_vague_content(episode_text)
    if fame_score >= 95 and vague_matches:
        issues.append(f"高スコアだが曖昧な表現: {', '.join(vague_matches[:3])}")
        severity = max(severity, 2)

    # ACHIEVEMENTなのに具体的達成なし
    if episode_type == "ACHIEVEMENT" and not has_concrete_achievement(episode_text):
        issues.append("ACHIEVEMENTだが具体的達成の記載なし")
        severity = max(severity, 2)

    # 100.0スコアの妥当性
    if fame_score == 100.0:
        # 世界的偉業のキーワードがあるかチェック
        world_class = any(
            kw in episode_text for kw in ["グラミー", "アカデミー", "ノーベル", "オリンピック", "世界記録", "史上初"]
        )
        if not world_class:
            issues.append("fame=100.0だが世界的偉業の根拠が薄い")
            severity = max(severity, 1)

    return {
        "episode_id": row.get("episode_id"),
        "person_name": row.get("person_name"),
        "age": row.get("age"),
        "episode_type": episode_type,
        "episode_fame_score": fame_score,
        "issues": issues,
        "severity": severity,
        "needs_review": severity >= 2,
        "needs_deletion": severity >= 3,
    }


def main():
    parser = argparse.ArgumentParser(description="問題のあるエピソードを検出")
    parser.add_argument(
        "--input",
        default="preserved/data/MASTER_EPISODES_CURRENT.csv",
        help="入力CSVファイル",
    )
    parser.add_argument("--min-fame", type=float, default=95.0, help="最低fameスコア")
    parser.add_argument("--output", default=None, help="出力JSONファイル")
    parser.add_argument("--verbose", action="store_true", help="詳細表示")
    args = parser.parse_args()

    # データ読み込み
    df = load_master_data(args.input)
    print(f"総エピソード数: {len(df)}")

    # 高スコアのエピソードをフィルタ
    high_score = df[df["episode_fame_score"] >= args.min_fame]
    print(f"fame >= {args.min_fame}: {len(high_score)}件")

    # 分析実行
    results = []
    for _, row in high_score.iterrows():
        analysis = analyze_episode(row)
        if analysis["issues"]:
            results.append(analysis)

    # 重大度でソート
    results.sort(key=lambda x: (-x["severity"], -x["episode_fame_score"]))

    # 結果表示
    print(f"\n問題のあるエピソード: {len(results)}件")
    print(f"  - 削除推奨（重度）: {sum(1 for r in results if r['needs_deletion'])}件")
    print(f"  - 要レビュー（中度）: {sum(1 for r in results if r['needs_review'] and not r['needs_deletion'])}件")
    print(f"  - 軽微な問題: {sum(1 for r in results if not r['needs_review'])}件")

    if args.verbose:
        print("\n=== 問題のあるエピソード詳細 ===")
        for r in results[:20]:
            severity_mark = "🚨" if r["needs_deletion"] else "⚠️" if r["needs_review"] else "ℹ️"
            print(f"\n{severity_mark} {r['episode_id']} | {r['person_name']} {r['age']}歳")
            print(f"   Type: {r['episode_type']} | Fame: {r['episode_fame_score']}")
            for issue in r["issues"]:
                print(f"   - {issue}")

    # 出力
    if args.output:
        output_data = {
            "timestamp": datetime.now().isoformat(),
            "total_analyzed": len(high_score),
            "problems_found": len(results),
            "summary": {
                "needs_deletion": sum(1 for r in results if r["needs_deletion"]),
                "needs_review": sum(1 for r in results if r["needs_review"]),
            },
            "episodes": results,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n結果を {args.output} に保存しました")

    return results


if __name__ == "__main__":
    main()
