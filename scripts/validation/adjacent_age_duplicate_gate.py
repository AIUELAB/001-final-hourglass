#!/usr/bin/env python3
"""
近接年齢重複エピソード検出ゲート

同一人物（person_id）で年齢差が閾値以内（デフォルト3歳）のエピソードが
類似している場合に検出する。

例: マザー・テレサ 71-74歳で類似エピソードが複数存在

Usage:
    python scripts/validation/adjacent_age_duplicate_gate.py --csv PATH [--age-threshold N] [--dry-run]

Exit codes:
    0: OK（違反なし）
    1: CRITICAL（違反あり）
"""

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/adjacent_age_duplicate_gate_result.json"

# デフォルト閾値
DEFAULT_AGE_THRESHOLD = 3  # 年齢差3以内
DEFAULT_SIMILARITY_THRESHOLD = 0.5  # 50%以上類似で重複とみなす


@dataclass
class Episode:
    """エピソード情報"""

    episode_id: str
    person_id: str
    person_name: str
    age: float
    text: str
    episode_type: str = ""


@dataclass
class AdjacentDuplicateCluster:
    """近接年齢重複クラスター"""

    person_id: str
    person_name: str
    age_min: float
    age_max: float
    episode_count: int
    episodes: list = field(default_factory=list)
    avg_similarity: float = 0.0
    max_similarity: float = 0.0
    delete_candidates: list = field(default_factory=list)


def tokenize(text: str) -> set:
    """テキストを単語（トークン）に分解"""
    # 日本語・英語混在対応: 句読点・記号で分割し、空白も含める
    # 日本語は文字単位、英語は単語単位
    tokens = set()

    # 英語単語を抽出
    english_words = re.findall(r"[a-zA-Z]+", text.lower())
    tokens.update(english_words)

    # 日本語文字を抽出（ひらがな・カタカナ・漢字）
    # 2-gramで分割
    japanese_text = re.sub(r"[a-zA-Z0-9\s]", "", text)
    for i in range(len(japanese_text) - 1):
        tokens.add(japanese_text[i : i + 2])

    # 単一文字も追加（短いテキスト対応）
    for char in japanese_text:
        if char not in "、。「」『』（）・":
            tokens.add(char)

    return tokens


def jaccard_similarity(text1: str, text2: str) -> float:
    """ジャッカード係数による類似度計算（0-1）"""
    if not text1 or not text2:
        return 0.0

    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)

    if not tokens1 or not tokens2:
        return 0.0

    intersection = tokens1 & tokens2
    union = tokens1 | tokens2

    return len(intersection) / len(union) if union else 0.0


def cosine_similarity_simple(text1: str, text2: str) -> float:
    """簡易コサイン類似度（単語ベース）"""
    if not text1 or not text2:
        return 0.0

    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)

    if not tokens1 or not tokens2:
        return 0.0

    # 共通トークン数
    intersection = tokens1 & tokens2
    # コサイン類似度の簡易版: |A∩B| / sqrt(|A| * |B|)
    denominator = (len(tokens1) * len(tokens2)) ** 0.5

    return len(intersection) / denominator if denominator > 0 else 0.0


def calculate_episode_similarity(ep1: Episode, ep2: Episode, method: str = "jaccard") -> float:
    """
    エピソード間の類似度計算

    Args:
        ep1: エピソード1
        ep2: エピソード2
        method: 'jaccard' または 'cosine'

    Returns:
        類似度（0-1）
    """
    text1 = ep1.text
    text2 = ep2.text

    if method == "cosine":
        return cosine_similarity_simple(text1, text2)
    else:
        return jaccard_similarity(text1, text2)


def detect_adjacent_duplicates(
    csv_path: Path,
    age_threshold: int = DEFAULT_AGE_THRESHOLD,
    similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> dict:
    """
    近接年齢重複を検出

    Args:
        csv_path: CSVファイルパス
        age_threshold: 年齢差の閾値（デフォルト3）
        similarity_threshold: 類似度の閾値（デフォルト0.5）

    Returns:
        検出結果辞書
    """
    # 人物ごとにエピソードをグループ化
    person_episodes: dict[str, list[Episode]] = defaultdict(list)

    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            person_id = row.get("person_id", "")
            person_name = row.get("person_name", "")
            episode_id = row.get("episode_id", "")
            age_str = row.get("age", "")
            text = row.get("episode_text", "") or row.get("episode_summary", "")
            episode_type = row.get("episode_type", "")

            if not (person_id and text and age_str):
                continue

            try:
                age = float(age_str)
            except (ValueError, TypeError):
                continue

            episode = Episode(
                episode_id=episode_id,
                person_id=person_id,
                person_name=person_name,
                age=age,
                text=text,
                episode_type=episode_type,
            )
            person_episodes[person_id].append(episode)

    # クラスター検出
    clusters: list[AdjacentDuplicateCluster] = []

    for person_id, episodes in person_episodes.items():
        if len(episodes) < 2:
            continue

        # 年齢順にソート
        episodes.sort(key=lambda x: x.age)

        # 近接年齢ペアを検出
        processed_pairs: set[tuple[str, str]] = set()

        for i, ep1 in enumerate(episodes):
            for j, ep2 in enumerate(episodes):
                if i >= j:
                    continue

                # 年齢差チェック
                age_diff = abs(ep1.age - ep2.age)
                if age_diff > age_threshold:
                    continue

                # 重複ペアスキップ
                pair_key: tuple[str, str] = (min(ep1.episode_id, ep2.episode_id), max(ep1.episode_id, ep2.episode_id))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)

                # 類似度計算
                similarity = calculate_episode_similarity(ep1, ep2)

                if similarity >= similarity_threshold:
                    # クラスターに追加または新規作成
                    added = False
                    for cluster in clusters:
                        if cluster.person_id == person_id:
                            # 既存クラスターに年齢が近接しているかチェック
                            if (
                                abs(ep1.age - cluster.age_min) <= age_threshold
                                or abs(ep1.age - cluster.age_max) <= age_threshold
                                or abs(ep2.age - cluster.age_min) <= age_threshold
                                or abs(ep2.age - cluster.age_max) <= age_threshold
                            ):
                                # クラスターにエピソード追加
                                existing_ids = {e["episode_id"] for e in cluster.episodes}
                                if ep1.episode_id not in existing_ids:
                                    cluster.episodes.append(
                                        {
                                            "episode_id": ep1.episode_id,
                                            "age": ep1.age,
                                            "text_snippet": ep1.text[:100],
                                        }
                                    )
                                if ep2.episode_id not in existing_ids:
                                    cluster.episodes.append(
                                        {
                                            "episode_id": ep2.episode_id,
                                            "age": ep2.age,
                                            "text_snippet": ep2.text[:100],
                                        }
                                    )
                                cluster.age_min = min(cluster.age_min, ep1.age, ep2.age)
                                cluster.age_max = max(cluster.age_max, ep1.age, ep2.age)
                                cluster.episode_count = len(cluster.episodes)
                                cluster.max_similarity = max(cluster.max_similarity, similarity)
                                added = True
                                break

                    if not added:
                        # 新規クラスター作成
                        cluster = AdjacentDuplicateCluster(
                            person_id=person_id,
                            person_name=ep1.person_name,
                            age_min=min(ep1.age, ep2.age),
                            age_max=max(ep1.age, ep2.age),
                            episode_count=2,
                            episodes=[
                                {
                                    "episode_id": ep1.episode_id,
                                    "age": ep1.age,
                                    "text_snippet": ep1.text[:100],
                                },
                                {
                                    "episode_id": ep2.episode_id,
                                    "age": ep2.age,
                                    "text_snippet": ep2.text[:100],
                                },
                            ],
                            max_similarity=similarity,
                        )
                        clusters.append(cluster)

    # クラスターごとに平均類似度と削除候補を計算
    for cluster in clusters:
        if len(cluster.episodes) >= 2:
            # 最も古い年齢のエピソードを残し、それ以外を削除候補に
            sorted_eps = sorted(cluster.episodes, key=lambda x: x["age"])
            cluster.delete_candidates = [e["episode_id"] for e in sorted_eps[1:]]

            # 平均類似度は最大類似度で代用（簡略化）
            cluster.avg_similarity = cluster.max_similarity

    # 類似度順にソート
    clusters.sort(key=lambda x: (-x.max_similarity, -x.episode_count))

    return {
        "scan_date": datetime.now().isoformat(),
        "parameters": {
            "age_threshold": age_threshold,
            "similarity_threshold": similarity_threshold,
            "csv_path": str(csv_path),
        },
        "total_clusters": len(clusters),
        "total_duplicate_episodes": sum(c.episode_count for c in clusters),
        "clusters": [asdict(c) for c in clusters],
    }


def get_clusters(result: dict) -> list[dict]:
    """
    重複クラスターをリスト化

    Args:
        result: detect_adjacent_duplicates()の結果

    Returns:
        クラスターのリスト
    """
    return result.get("clusters", [])


def print_report(result: dict, verbose: bool = False) -> None:
    """結果を表示"""
    print("=" * 70)
    print("近接年齢重複エピソード検出ゲート")
    print("=" * 70)

    params = result.get("parameters", {})
    print(f"\n設定:")
    print(f"  年齢差閾値: {params.get('age_threshold', DEFAULT_AGE_THRESHOLD)}歳以内")
    print(f"  類似度閾値: {params.get('similarity_threshold', DEFAULT_SIMILARITY_THRESHOLD) * 100:.0f}%以上")

    print(f"\n結果サマリー:")
    print(f"  総クラスター数: {result['total_clusters']}")
    print(f"  総重複件数: {result['total_duplicate_episodes']}")

    clusters = result.get("clusters", [])
    if clusters:
        print("\n--- 検出されたクラスター ---")
        display_count = 20 if verbose else 10
        for i, cluster in enumerate(clusters[:display_count], 1):
            age_range = f"{int(cluster['age_min'])}-{int(cluster['age_max'])}歳"
            print(f"\n  [{i}] {cluster['person_name']} ({age_range})")
            print(f"      件数: {cluster['episode_count']}件")
            print(f"      最大類似度: {cluster['max_similarity'] * 100:.1f}%")
            print(f"      削除候補: {cluster['delete_candidates']}")

            if verbose:
                print("      エピソード詳細:")
                for ep in cluster["episodes"]:
                    print(f"        - [{ep['episode_id']}] {ep['age']}歳: {ep['text_snippet'][:50]}...")

        if len(clusters) > display_count:
            print(f"\n  ... 他 {len(clusters) - display_count} クラスター")


def main():
    parser = argparse.ArgumentParser(
        description="近接年齢重複エピソード検出ゲート",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
例:
    # デフォルト設定で実行
    python scripts/validation/adjacent_age_duplicate_gate.py

    # カスタム閾値で実行
    python scripts/validation/adjacent_age_duplicate_gate.py --age-threshold 5 --similarity-threshold 0.6

    # dry-runモード（ゲートを落とさない）
    python scripts/validation/adjacent_age_duplicate_gate.py --dry-run
        """,
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=DEFAULT_MASTER_CSV,
        help=f"CSVファイルパス (デフォルト: {DEFAULT_MASTER_CSV})",
    )
    parser.add_argument(
        "--age-threshold",
        type=int,
        default=DEFAULT_AGE_THRESHOLD,
        help=f"年齢差の閾値 (デフォルト: {DEFAULT_AGE_THRESHOLD})",
    )
    parser.add_argument(
        "--similarity-threshold",
        type=float,
        default=DEFAULT_SIMILARITY_THRESHOLD,
        help=f"類似度の閾値 (デフォルト: {DEFAULT_SIMILARITY_THRESHOLD})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="ゲートを落とさず情報のみ表示",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細表示",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=REPORT_PATH,
        help=f"出力JSONファイルパス (デフォルト: {REPORT_PATH})",
    )

    args = parser.parse_args()

    # CSVファイル存在確認
    if not args.csv.exists():
        print(f"Error: CSVファイルが見つかりません: {args.csv}")
        return 1

    # 検出実行
    result = detect_adjacent_duplicates(
        csv_path=args.csv,
        age_threshold=args.age_threshold,
        similarity_threshold=args.similarity_threshold,
    )

    # レポート出力
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    # 結果表示
    print_report(result, verbose=args.verbose)

    print(f"\nレポート出力: {args.output}")

    # ゲート判定
    if result["total_clusters"] > 0:
        print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}CRITICAL: {result['total_clusters']}クラスター検出")
        if not args.dry_run:
            return 1

    print("\nOK: 近接年齢重複なし")
    return 0


if __name__ == "__main__":
    sys.exit(main())
