#!/usr/bin/env python3
"""
エピソード関連性チェッカー（Episode Relevance Checker）
Web検索を使って「◯◯といえば」の定番度を測定

ユーザー要望:
「◯◯◯◯の有名なエピソードや偉業や事件といえば？でAIサーチして
より多く出てくるもの、優先的に出てくるものを取り上げてみては？」
"""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import time


@dataclass
class RelevanceScore:
    """関連性スコア"""
    person_name: str
    episode_description: str
    search_count: int  # 検索結果数
    top_rank: int  # 上位ランク（1位=最定番、10位=あまり定番でない）
    relevance_score: float  # 0-100点（100点=最も定番）
    is_iconic: bool  # 定番エピソードかどうか
    search_queries_used: List[str]  # 使用した検索クエリ


class EpisodeRelevanceChecker:
    """Web検索を使った定番度判定システム"""

    def __init__(self):
        self.min_iconic_score = 60.0  # 60点以上で「定番」と判定
        self.max_search_results = 10  # 最大10件の検索結果を分析

    def check_relevance(
        self,
        person_name: str,
        episode_keywords: List[str],
        mcp_search_function=None
    ) -> RelevanceScore:
        """
        エピソードの定番度をWeb検索で判定

        Args:
            person_name: 人物名
            episode_keywords: エピソードのキーワードリスト
                例: ['Amazon', '創業', 'ガレージ']
            mcp_search_function: Brave Search MCPの検索関数（テスト用にオプション）

        Returns:
            RelevanceScore: 関連性スコア
        """
        # 検索クエリの生成
        queries = self._generate_search_queries(person_name, episode_keywords)

        # 各クエリで検索
        search_results = []
        for query in queries:
            if mcp_search_function:
                # MCP検索を実行
                results = mcp_search_function(query, count=self.max_search_results)
                search_results.append((query, results))
            else:
                # テストモード: ダミーデータ
                search_results.append((query, []))

        # スコアリング
        relevance_score, top_rank, search_count = self._calculate_relevance_score(
            person_name, episode_keywords, search_results
        )

        episode_desc = self._format_episode_description(episode_keywords)
        is_iconic = relevance_score >= self.min_iconic_score

        return RelevanceScore(
            person_name=person_name,
            episode_description=episode_desc,
            search_count=search_count,
            top_rank=top_rank,
            relevance_score=relevance_score,
            is_iconic=is_iconic,
            search_queries_used=queries
        )

    def _generate_search_queries(
        self, person_name: str, episode_keywords: List[str]
    ) -> List[str]:
        """
        検索クエリを生成

        Args:
            person_name: 人物名
            episode_keywords: エピソードキーワード

        Returns:
            List[str]: 検索クエリリスト
        """
        queries = []

        # パターン1: 「◯◯といえば」
        queries.append(f"{person_name}といえば")

        # パターン2: 「◯◯の有名なエピソード」
        queries.append(f"{person_name} 有名なエピソード")

        # パターン3: 「◯◯の偉業」
        queries.append(f"{person_name} 偉業")

        # パターン4: 「◯◯ + キーワード」（最大3キーワード）
        for keyword in episode_keywords[:3]:
            queries.append(f"{person_name} {keyword}")

        return queries

    def _calculate_relevance_score(
        self,
        person_name: str,
        episode_keywords: List[str],
        search_results: List[Tuple[str, List[Dict]]]
    ) -> Tuple[float, int, int]:
        """
        検索結果から関連性スコアを計算

        Args:
            person_name: 人物名
            episode_keywords: エピソードキーワード
            search_results: 検索結果リスト

        Returns:
            Tuple[float, int, int]: (スコア, トップランク, 検索結果数)
        """
        total_score = 0.0
        keyword_matches = {kw: [] for kw in episode_keywords}
        total_results = 0

        # 各検索結果を分析
        for query, results in search_results:
            if not results:
                continue

            total_results += len(results)

            # 上位10件の結果を分析
            for rank, result in enumerate(results[:10], start=1):
                title = result.get('title', '')
                description = result.get('description', '')
                combined_text = f"{title} {description}"

                # キーワードマッチング
                for keyword in episode_keywords:
                    if keyword in combined_text:
                        # ランクに応じたスコア（1位=10点、10位=1点）
                        rank_score = (11 - rank)
                        keyword_matches[keyword].append((rank, rank_score))

        # スコア計算
        if not keyword_matches:
            return 0.0, 100, total_results

        # キーワードマッチ率
        matched_keywords = [kw for kw, matches in keyword_matches.items() if matches]
        match_rate = len(matched_keywords) / len(episode_keywords)

        # トップランク（最も高順位に出現したキーワードのランク）
        all_ranks = []
        for matches in keyword_matches.values():
            if matches:
                all_ranks.extend([rank for rank, _ in matches])

        top_rank = min(all_ranks) if all_ranks else 100

        # スコア計算式
        # - マッチ率: 0-50点
        # - トップランク: 0-30点（1位=30点、10位=3点）
        # - 検索結果数: 0-20点（10件以上=20点）
        score = (
            match_rate * 50.0 +
            ((11 - top_rank) * 3.0) if top_rank <= 10 else 0.0 +
            min(total_results / 10 * 20.0, 20.0)
        )

        return score, top_rank, total_results

    def _format_episode_description(self, keywords: List[str]) -> str:
        """エピソードの説明文を生成"""
        return ' + '.join(keywords)

    def compare_episodes(
        self,
        person_name: str,
        episode_candidates: List[Dict],
        mcp_search_function=None
    ) -> List[Tuple[Dict, RelevanceScore]]:
        """
        複数のエピソード候補を比較して定番度順にソート

        Args:
            person_name: 人物名
            episode_candidates: エピソード候補リスト
                [{'keywords': ['Amazon', '創業'], 'age': 30}, ...]
            mcp_search_function: Brave Search MCP関数

        Returns:
            List[Tuple[Dict, RelevanceScore]]: (エピソード, スコア)のリスト
                定番度の高い順にソート
        """
        scored_episodes = []

        for episode in episode_candidates:
            keywords = episode.get('keywords', [])
            score = self.check_relevance(person_name, keywords, mcp_search_function)
            scored_episodes.append((episode, score))

            # API rate limit対策
            time.sleep(0.5)

        # スコア順にソート（降順）
        scored_episodes.sort(key=lambda x: x[1].relevance_score, reverse=True)

        return scored_episodes

    def extract_keywords_from_episode(self, episode_text: str) -> List[str]:
        """
        エピソードテキストからキーワードを抽出

        Args:
            episode_text: エピソードテキスト

        Returns:
            List[str]: キーワードリスト
        """
        # 重要キーワードパターン
        important_patterns = [
            # 栄誉・賞
            r'ノーベル賞',
            r'芥川賞',
            r'直木賞',
            r'アカデミー賞',
            r'MVP',
            r'金メダル',
            # 事件
            r'逮捕',
            r'上場廃止',
            r'スキャンダル',
            # 創業・設立
            r'創業',
            r'設立',
            r'創設',
            # 場所・状況
            r'ガレージ',
            r'横断',
            # 作品・サービス名
            r'Amazon',
            r'Apple',
            r'ライブドア',
            r'慶應義塾',
            r'学問のすゝめ',
        ]

        keywords = []
        for pattern in important_patterns:
            matches = re.findall(pattern, episode_text)
            keywords.extend(matches)

        # 重複削除
        keywords = list(set(keywords))

        return keywords


def test_relevance_checker():
    """関連性チェッカーのテスト"""
    checker = EpisodeRelevanceChecker()

    print("=" * 80)
    print("エピソード関連性チェッカー - テスト")
    print("=" * 80)

    # テストケース1: ジェフ・ベゾス
    print("\nテストケース1: ジェフ・ベゾス")
    print("-" * 80)

    # 候補1: 30歳のガレージ創業
    keywords1 = ['Amazon', '創業', 'ガレージ', '30歳']
    score1 = checker.check_relevance("ジェフ・ベゾス", keywords1)

    print(f"\n候補1: {score1.episode_description}")
    print(f"  定番度スコア: {score1.relevance_score:.1f}/100点")
    print(f"  判定: {'✅ 定番' if score1.is_iconic else '❌ マイナー'}")
    print(f"  トップランク: {score1.top_rank}位")
    print(f"  検索結果数: {score1.search_count}件")

    # 候補2: 35歳のPrime開始
    keywords2 = ['Amazon Prime', '開始', '35歳']
    score2 = checker.check_relevance("ジェフ・ベゾス", keywords2)

    print(f"\n候補2: {score2.episode_description}")
    print(f"  定番度スコア: {score2.relevance_score:.1f}/100点")
    print(f"  判定: {'✅ 定番' if score2.is_iconic else '❌ マイナー'}")
    print(f"  トップランク: {score2.top_rank}位")
    print(f"  検索結果数: {score2.search_count}件")

    print("\n" + "=" * 80)
    print("比較結果:")
    print("=" * 80)
    if score1.relevance_score > score2.relevance_score:
        print("✅ 候補1（ガレージ創業）の方が定番度が高い")
    else:
        print("✅ 候補2（Prime開始）の方が定番度が高い")

    # テストケース2: キーワード抽出
    print("\n" + "=" * 80)
    print("テストケース2: キーワード抽出")
    print("=" * 80)

    episode_text = "あなたと同じ30歳のとき、ジェフ・ベゾスはヘッジファンドを辞め、妻とともに車でアメリカを横断。ガレージでAmazonを創業した。"
    keywords = checker.extract_keywords_from_episode(episode_text)

    print(f"\nエピソード: {episode_text[:50]}...")
    print(f"抽出キーワード: {keywords}")


if __name__ == '__main__':
    test_relevance_checker()
