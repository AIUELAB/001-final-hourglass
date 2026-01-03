#!/usr/bin/env python3
"""
EPUP: 同一人物エピソード間のスコア逆転検出

機能:
- 同一人物の複数エピソードで「社会的インパクトの大きいイベント」が
  低くスコアリングされている疑いを検出

使用方法:
    python scripts/validators/detect_score_reversals.py
    python scripts/validators/detect_score_reversals.py --person "村上春樹"
"""

import argparse
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

# 社会的インパクトが高いキーワード（発表/受賞/記録達成等）
HIGH_IMPACT_KEYWORDS = [
    # 作品発表
    "発表",
    "発売",
    "公開",
    "出版",
    "リリース",
    "デビュー",
    # 受賞
    "受賞",
    "ノーベル賞",
    "アカデミー賞",
    "グラミー賞",
    "金メダル",
    # 記録達成
    "世界初",
    "日本初",
    "史上初",
    "世界記録",
    "ギネス",
    "大ヒット",
    "ベストセラー",
    "ミリオン",
    "100万部",
    # 就任・創業
    "就任",
    "設立",
    "創業",
    "創設",
    "開発",
    # 歴史的
    "革命",
    "独立",
    "解放",
    "宣言",
]

# 内面/私的キーワード（スコアが低くなるべき）
LOW_IMPACT_KEYWORDS = [
    "重圧",
    "逃避",
    "苦悩",
    "悩み",
    "葛藤",
    "挫折",
    "病気",
    "入院",
    "療養",
    "休養",
    "家族",
    "結婚",
    "離婚",
    "恋愛",
    "日常",
    "趣味",
    "プライベート",
]


def load_episodes() -> list[dict]:
    """CSVからエピソードを読み込み"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def classify_episode(text: str) -> tuple[int, int]:
    """エピソードを分類（高インパクト/低インパクトキーワード数）"""
    high_count = sum(1 for kw in HIGH_IMPACT_KEYWORDS if kw in text)
    low_count = sum(1 for kw in LOW_IMPACT_KEYWORDS if kw in text)
    return high_count, low_count


def detect_reversals(episodes: list[dict], person_filter: str = None) -> list[dict]:
    """同一人物での逆転を検出"""
    # 人物ごとにグループ化
    person_episodes = {}
    for ep in episodes:
        pid = ep.get("person_id", "")
        pname = ep.get("person_name", "")
        if person_filter and person_filter not in pname:
            continue
        if pid:
            if pid not in person_episodes:
                person_episodes[pid] = []
            person_episodes[pid].append(ep)

    reversals = []

    for pid, eps in person_episodes.items():
        if len(eps) < 2:
            continue

        # エピソードをスコア順にソート
        sorted_eps = sorted(eps, key=lambda x: float(x.get("episode_fame_score", 0) or 0), reverse=True)

        for i, high_ep in enumerate(sorted_eps):
            for low_ep in sorted_eps[i + 1 :]:
                high_score = float(high_ep.get("episode_fame_score", 0) or 0)
                low_score = float(low_ep.get("episode_fame_score", 0) or 0)
                score_diff = high_score - low_score

                if score_diff < 0.5:  # 差が小さい場合はスキップ
                    continue

                high_text = high_ep.get("episode_text", "")
                low_text = low_ep.get("episode_text", "")

                high_hi, high_lo = classify_episode(high_text)
                low_hi, low_lo = classify_episode(low_text)

                # 逆転の疑い:
                # スコアが高いエピソードが「低インパクト」キーワード多い AND
                # スコアが低いエピソードが「高インパクト」キーワード多い
                if high_lo > high_hi and low_hi > low_lo:
                    reversals.append(
                        {
                            "person_id": pid,
                            "person_name": high_ep.get("person_name", ""),
                            "high_score_ep": high_ep["episode_id"],
                            "high_score": high_score,
                            "high_age": high_ep.get("age", ""),
                            "high_impact_kw": high_hi,
                            "high_private_kw": high_lo,
                            "low_score_ep": low_ep["episode_id"],
                            "low_score": low_score,
                            "low_age": low_ep.get("age", ""),
                            "low_impact_kw": low_hi,
                            "low_private_kw": low_lo,
                            "score_diff": score_diff,
                        }
                    )

    # スコア差でソート
    reversals.sort(key=lambda x: -x["score_diff"])
    return reversals


def main():
    parser = argparse.ArgumentParser(description="EPUP: スコア逆転検出")
    parser.add_argument("--person", type=str, help="特定の人物名でフィルタ")
    parser.add_argument("--limit", type=int, default=20, help="表示件数")
    args = parser.parse_args()

    print("=" * 60)
    print("【EPUP】同一人物エピソード スコア逆転検出")
    print("=" * 60)
    print()

    episodes = load_episodes()
    print(f"エピソード数: {len(episodes)}")
    print()

    reversals = detect_reversals(episodes, args.person)
    print(f"逆転候補: {len(reversals)}件")
    print()

    if not reversals:
        print("✅ 逆転候補は見つかりませんでした")
        return 0

    print("=== 逆転候補（上位）===")
    print()
    for i, r in enumerate(reversals[: args.limit], 1):
        print(f"{i:2d}. {r['person_name']}")
        print(f"    高スコア: {r['high_score_ep']} ({r['high_age']}歳) = {r['high_score']:.2f}")
        print(f"      → 高インパクトKW: {r['high_impact_kw']}, 私的KW: {r['high_private_kw']}")
        print(f"    低スコア: {r['low_score_ep']} ({r['low_age']}歳) = {r['low_score']:.2f}")
        print(f"      → 高インパクトKW: {r['low_impact_kw']}, 私的KW: {r['low_private_kw']}")
        print(f"    差: {r['score_diff']:.2f}")
        print()

    return 0


if __name__ == "__main__":
    exit(main())
