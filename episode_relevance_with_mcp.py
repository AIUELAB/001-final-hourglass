#!/usr/bin/env python3
"""
EpisodeRelevanceChecker - 実際のBrave Search MCPを使用
Claude Codeで実行される実装
"""

from episode_relevance_checker import EpisodeRelevanceChecker
import csv
from typing import List, Dict


def brave_search_wrapper(query: str, count: int = 10):
    """
    Brave Search MCPラッパー

    Claude Codeで実行時、このコメントをClaude Codeに伝える：
    「このコードを実行する際、brave_search_wrapper関数内で
    mcp__brave-search__brave_web_search ツールを使ってください」

    実装例:
    from mcp import brave_search
    results = brave_search.web_search(query, count=count)
    return results
    """
    # NOTE: Claude Codeで実行時は上記のMCPツールを使用
    # ローカル実行時はこのエラーが出る
    raise NotImplementedError(
        "この関数はClaude Code環境で実行する必要があります。\n"
        "Claude Codeで実行時、mcp__brave-search__brave_web_search ツールを使用してください。"
    )


def load_problem_episodes(csv_path: str) -> List[Dict]:
    """
    問題のあるエピソードを読み込み

    Args:
        csv_path: CSVファイルパス

    Returns:
        問題エピソードのリスト
    """
    problem_episodes = []

    # ユーザーが指摘した6つの問題エピソード
    problem_ids = ['EP011', 'EP033', 'EP035', 'EP061', 'EP077', 'EP079']

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['episode_id'] in problem_ids:
                problem_episodes.append(row)

    return problem_episodes


def analyze_problem_episodes():
    """
    6つの問題エピソードの定番度を分析

    Claude Codeで実行すること
    """
    checker = EpisodeRelevanceChecker()

    print("=" * 80)
    print("問題エピソードの定番度分析 - Brave Search MCP使用")
    print("=" * 80)

    # EP011: ジェフ・ベゾス
    print("\n" + "=" * 80)
    print("EP011: ジェフ・ベゾス - 現在エピソード vs 推奨エピソード")
    print("=" * 80)

    candidates = [
        {
            'keywords': ['Amazon Prime', '開始', '35歳'],
            'age': 35,
            'description': '現在のエピソード: Amazon Primeサービス開始（35歳）'
        },
        {
            'keywords': ['Amazon', '創業', 'ガレージ', '30歳'],
            'age': 30,
            'description': '推奨エピソード: ガレージでAmazon創業（30歳）'
        }
    ]

    print("\n候補エピソード:")
    for i, candidate in enumerate(candidates, start=1):
        print(f"  {i}. {candidate['description']}")
        print(f"     キーワード: {', '.join(candidate['keywords'])}")

    print("\n検索実行中...")
    print("（NOTE: Claude Code環境で実行時、Brave Search MCPが使用されます）")

    try:
        results = checker.compare_episodes("ジェフ・ベゾス", candidates, brave_search_wrapper)

        print("\n✅ 定番度ランキング:")
        for i, (episode, score) in enumerate(results, start=1):
            print(f"\n{i}位: {episode['description']}")
            print(f"  定番度スコア: {score.relevance_score:.1f}/100点")
            print(f"  判定: {'✅ 定番エピソード' if score.is_iconic else '❌ マイナーエピソード'}")
            print(f"  トップランク: {score.top_rank}位")
            print(f"  検索結果数: {score.search_count}件")

    except NotImplementedError as e:
        print(f"\n⚠️ {e}")
        print("\nこのスクリプトはClaude Code環境で実行してください。")

    # EP033: 堀江貴文
    print("\n" + "=" * 80)
    print("EP033: 堀江貴文 - 現在エピソード vs 推奨エピソード")
    print("=" * 80)

    candidates = [
        {
            'keywords': ['起業', '設立', 'オン・ザ・エッヂ', '24歳'],
            'age': 24,
            'description': '現在のエピソード: 有限会社オン・ザ・エッヂ設立（24歳）'
        },
        {
            'keywords': ['ライブドア', '事件', '逮捕', '上場廃止'],
            'age': 33,
            'description': '推奨エピソード: ライブドア事件で逮捕（33歳）'
        }
    ]

    print("\n候補エピソード:")
    for i, candidate in enumerate(candidates, start=1):
        print(f"  {i}. {candidate['description']}")
        print(f"     キーワード: {', '.join(candidate['keywords'])}")

    # EP035: 大江健三郎
    print("\n" + "=" * 80)
    print("EP035: 大江健三郎 - 現在エピソード vs 推奨エピソード")
    print("=" * 80)

    candidates = [
        {
            'keywords': ['芥川賞', '飼育', '23歳'],
            'age': 23,
            'description': '現在のエピソード: 芥川賞受賞（23歳）'
        },
        {
            'keywords': ['ノーベル賞', 'ノーベル文学賞', '59歳'],
            'age': 59,
            'description': '推奨エピソード: ノーベル文学賞受賞（59歳）'
        }
    ]

    print("\n候補エピソード:")
    for i, candidate in enumerate(candidates, start=1):
        print(f"  {i}. {candidate['description']}")
        print(f"     キーワード: {', '.join(candidate['keywords'])}")

    # EP079: 福沢諭吉
    print("\n" + "=" * 80)
    print("EP079: 福沢諭吉 - 現在エピソード vs 推奨エピソード")
    print("=" * 80)

    candidates = [
        {
            'keywords': ['西洋事情', '出版', '35歳'],
            'age': 35,
            'description': '現在のエピソード: 西洋事情出版（35歳）'
        },
        {
            'keywords': ['慶應義塾', '創設', '26歳'],
            'age': 26,
            'description': '推奨エピソード1: 慶應義塾創設（26歳）'
        },
        {
            'keywords': ['学問のすゝめ', '出版', '37歳'],
            'age': 37,
            'description': '推奨エピソード2: 学問のすゝめ出版（37歳）'
        }
    ]

    print("\n候補エピソード:")
    for i, candidate in enumerate(candidates, start=1):
        print(f"  {i}. {candidate['description']}")
        print(f"     キーワード: {', '.join(candidate['keywords'])}")

    print("\n" + "=" * 80)
    print("分析完了")
    print("=" * 80)
    print("\n📝 次のステップ:")
    print("  1. Claude Code環境でこのスクリプトを実行")
    print("  2. Brave Search MCPで実際の定番度を測定")
    print("  3. 定番度が低いエピソードを特定")
    print("  4. 定番度の高いエピソードに差し替えを提案")


if __name__ == '__main__':
    analyze_problem_episodes()
