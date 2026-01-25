"""
LLM InspirationScore パイロットテスト

キーワードマッチングとLLM直接評価を比較検証
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.score.episode_fame_v2.inspiration_scorer import calculate_inspiration_score
from scripts.score.episode_fame_v2.inspiration_scorer_llm import InspirationScorerLLM


def load_sample_episodes(csv_path: str, sample_size: int = 10, include_anchors: bool = True) -> list:
    """
    サンプルエピソードをロード

    Args:
        csv_path: マスターCSVパス
        sample_size: サンプル数
        include_anchors: アンカー人物を含めるか

    Returns:
        エピソードリスト
    """
    # アンカー人物（参考ランキング上位）
    anchor_persons = [
        "ネルソン・マンデラ",
        "ダライ・ラマ14世",
        "マハトマ・ガンディー",
        "キング牧師",
        "マララ・ユスフザイ",
        "ヘレン・ケラー",
        "スティーブン・ホーキング",
        "マリー・キュリー",
        "ベートーヴェン",
        "アンネ・フランク",
    ]

    episodes = []
    anchor_found = []
    general = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            ep = {
                "episode_id": row.get("episode_id", ""),
                "person_id": row.get("person_id", ""),
                "person_name": row.get("person_name", ""),
                "text": row.get("episode_text", ""),
                "category": row.get("category", ""),
            }

            # 空テキストはスキップ
            if not ep["text"] or len(ep["text"]) < 50:
                continue

            # アンカー人物かチェック
            is_anchor = any(anchor in ep["person_name"] for anchor in anchor_persons)

            if include_anchors and is_anchor:
                anchor_found.append(ep)
            else:
                general.append(ep)

    # サンプル構成: アンカー優先 + 一般からランダム
    if include_anchors:
        episodes.extend(anchor_found[: min(len(anchor_found), sample_size // 2)])
        remaining = sample_size - len(episodes)
        # 一般から均等にサンプリング
        step = max(1, len(general) // remaining) if remaining > 0 else 1
        for i in range(0, len(general), step):
            if len(episodes) >= sample_size:
                break
            episodes.append(general[i])
    else:
        step = max(1, len(general) // sample_size)
        for i in range(0, len(general), step):
            if len(episodes) >= sample_size:
                break
            episodes.append(general[i])

    return episodes[:sample_size]


def run_pilot(
    sample_size: int = 10,
    api_key: str = None,
    output_dir: str = "src/reports",
) -> dict:
    """
    パイロットテスト実行

    Args:
        sample_size: サンプル数
        api_key: Anthropic APIキー
        output_dir: 出力ディレクトリ

    Returns:
        テスト結果
    """
    csv_path = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

    print("=== LLM InspirationScore パイロットテスト ===")
    print(f"サンプル数: {sample_size}")
    print()

    # サンプルロード
    print("サンプルエピソードをロード中...")
    episodes = load_sample_episodes(str(csv_path), sample_size)
    print(f"ロード完了: {len(episodes)}件")
    print()

    # LLMスコアラー初期化
    print("LLMスコアラーを初期化中...")
    llm_scorer = InspirationScorerLLM(api_key=api_key)
    print(f"モデル: {llm_scorer.model}")
    print()

    results = []

    for i, ep in enumerate(episodes):
        print(f"[{i + 1}/{len(episodes)}] {ep['person_name'][:20]}...")

        # キーワードベース評価
        keyword_result = calculate_inspiration_score(
            text=ep["text"],
            person_name=ep["person_name"],
            category=ep["category"],
        )

        # LLM評価
        llm_result = llm_scorer.evaluate(
            text=ep["text"],
            person_name=ep["person_name"],
        )

        result = {
            "episode_id": ep["episode_id"],
            "person_name": ep["person_name"],
            "text_preview": ep["text"][:100] + "..." if len(ep["text"]) > 100 else ep["text"],
            "keyword": {
                "total": keyword_result["total"],
                "axes": keyword_result.get("axes", {}),
            },
            "llm": {
                "total": llm_result["total"],
                "axes": {
                    "difficulty": llm_result.get("difficulty", 0),
                    "effort": llm_result.get("effort", 0),
                    "decision": llm_result.get("decision", 0),
                    "achievement": llm_result.get("achievement", 0),
                    "social_impact": llm_result.get("social_impact", 0),
                },
                "narrative_pattern": llm_result.get("narrative_pattern", ""),
                "narrative_depth": llm_result.get("narrative_depth", 0),
                "reasoning": llm_result.get("reasoning", ""),
                "cached": llm_result.get("cached", False),
            },
            "diff": round(llm_result["total"] - keyword_result["total"], 2),
        }
        results.append(result)

        # 結果表示
        print(
            f"  Keyword: {keyword_result['total']:.1f} | LLM: {llm_result['total']:.1f} | Diff: {result['diff']:+.1f}"
        )
        if llm_result.get("reasoning"):
            print(f"  理由: {llm_result['reasoning'][:50]}...")
        print()

    # 統計計算
    keyword_scores = [r["keyword"]["total"] for r in results]
    llm_scores = [r["llm"]["total"] for r in results]
    diffs = [r["diff"] for r in results]

    stats = {
        "sample_count": len(results),
        "keyword": {
            "mean": round(sum(keyword_scores) / len(keyword_scores), 2),
            "min": round(min(keyword_scores), 2),
            "max": round(max(keyword_scores), 2),
        },
        "llm": {
            "mean": round(sum(llm_scores) / len(llm_scores), 2),
            "min": round(min(llm_scores), 2),
            "max": round(max(llm_scores), 2),
        },
        "diff": {
            "mean": round(sum(diffs) / len(diffs), 2),
            "min": round(min(diffs), 2),
            "max": round(max(diffs), 2),
        },
        "cache_stats": llm_scorer.get_cache_stats(),
    }

    # サマリー表示
    print("=" * 50)
    print("統計サマリー")
    print("=" * 50)
    print(
        f"キーワード平均: {stats['keyword']['mean']:.1f} (範囲: {stats['keyword']['min']:.1f}-{stats['keyword']['max']:.1f})"
    )
    print(f"LLM平均: {stats['llm']['mean']:.1f} (範囲: {stats['llm']['min']:.1f}-{stats['llm']['max']:.1f})")
    print(f"差分平均: {stats['diff']['mean']:+.1f} (範囲: {stats['diff']['min']:+.1f} to {stats['diff']['max']:+.1f})")
    print(f"キャッシュ済み: {stats['cache_stats']['cached_count']}件")
    print()

    # 結果保存
    output = {
        "timestamp": datetime.now().isoformat(),
        "sample_size": sample_size,
        "model": llm_scorer.model,
        "stats": stats,
        "results": results,
    }

    output_path = Path(output_dir) / f"llm_pilot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"結果保存: {output_path}")

    return output


def main():
    import argparse

    parser = argparse.ArgumentParser(description="LLM InspirationScore パイロットテスト")
    parser.add_argument("--sample", type=int, default=10, help="サンプル数（デフォルト: 10）")
    parser.add_argument("--api-key", type=str, default=None, help="Anthropic APIキー")

    args = parser.parse_args()

    # APIキー確認
    api_key = args.api_key or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("エラー: ANTHROPIC_API_KEYが設定されていません")
        print("環境変数またはスクリプトで指定してください")
        sys.exit(1)

    run_pilot(
        sample_size=args.sample,
        api_key=api_key,
    )


if __name__ == "__main__":
    main()
