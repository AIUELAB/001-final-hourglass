#!/usr/bin/env python3
"""
EpisodeRelevanceCheckerのテスト
Brave Search MCPを使って実際の検索を実行
"""

from episode_relevance_checker import EpisodeRelevanceChecker, RelevanceScore


def mock_brave_search(query: str, count: int = 10):
    """
    Brave Search MCPのモック（実装時は実際のMCP関数に置き換える）

    実際の実装では以下のようになる:
    from mcp import brave_search
    return brave_search.search(query, count=count)
    """
    # テスト用のダミーデータ
    # 実際の使用時はClaude CodeのBrave Search MCPに置き換える

    results = []

    # シミュレート: ジェフ・ベゾスの検索結果
    if "ジェフ・ベゾス" in query:
        if "といえば" in query or "創業" in query or "Amazon" in query or "ガレージ" in query:
            # ガレージ創業は1位に頻出
            results.append({
                'title': 'ジェフ・ベゾス - Amazonをガレージで創業',
                'description': '1994年、30歳のジェフ・ベゾスはシアトルのガレージでAmazonを創業した。',
                'url': 'https://example.com/bezos-garage'
            })
            results.append({
                'title': 'ジェフ・ベゾスの起業ストーリー',
                'description': 'ヘッジファンドを辞めてガレージでオンライン書店を始めた伝説の起業家',
                'url': 'https://example.com/bezos-story'
            })

        if "Prime" in query or "Amazon Prime" in query:
            # Primeは3位程度
            results.append({
                'title': 'Amazon Primeの歴史',
                'description': '2005年にジェフ・ベゾスがAmazon Primeサービスを開始',
                'url': 'https://example.com/prime'
            })

    # シミュレート: 堀江貴文の検索結果
    if "堀江貴文" in query:
        if "といえば" in query or "事件" in query or "逮捕" in query or "ライブドア" in query:
            # ライブドア事件は1位に頻出
            results.append({
                'title': '堀江貴文 - ライブドア事件で逮捕',
                'description': '2006年、ライブドア事件で証券取引法違反容疑で逮捕された',
                'url': 'https://example.com/horie-arrest'
            })
            results.append({
                'title': 'ライブドア事件の真相',
                'description': '堀江貴文氏の逮捕と上場廃止までの経緯',
                'url': 'https://example.com/livedoor-case'
            })

        if "起業" in query or "設立" in query:
            # 起業は5位程度
            results.append({
                'title': '堀江貴文の起業',
                'description': '1996年、24歳で有限会社オン・ザ・エッヂを設立',
                'url': 'https://example.com/horie-startup'
            })

    # シミュレート: 大江健三郎の検索結果
    if "大江健三郎" in query:
        if "といえば" in query or "ノーベル賞" in query:
            # ノーベル賞は1位
            results.append({
                'title': '大江健三郎 - ノーベル文学賞受賞',
                'description': '1994年、ノーベル文学賞を受賞した日本人作家',
                'url': 'https://example.com/oe-nobel'
            })

        if "芥川賞" in query:
            # 芥川賞は2-3位
            results.append({
                'title': '大江健三郎の芥川賞受賞',
                'description': '1958年、23歳で「飼育」により芥川賞を受賞',
                'url': 'https://example.com/oe-akutagawa'
            })

    return results


def test_with_mock_search():
    """モック検索を使ったテスト"""
    checker = EpisodeRelevanceChecker()

    print("=" * 80)
    print("エピソード関連性チェッカー - Brave Search統合テスト")
    print("=" * 80)

    # テスト1: ジェフ・ベゾス - ガレージ創業 vs Prime開始
    print("\n" + "=" * 80)
    print("テスト1: ジェフ・ベゾス - どちらが定番エピソードか？")
    print("=" * 80)

    candidates = [
        {
            'keywords': ['Amazon', '創業', 'ガレージ', '30歳'],
            'age': 30,
            'description': 'ガレージでAmazon創業'
        },
        {
            'keywords': ['Amazon Prime', '開始', '35歳'],
            'age': 35,
            'description': 'Amazon Primeサービス開始'
        }
    ]

    results = checker.compare_episodes("ジェフ・ベゾス", candidates, mock_brave_search)

    print("\n定番度ランキング:")
    for i, (episode, score) in enumerate(results, start=1):
        print(f"\n{i}位: {episode['description']} ({episode['age']}歳)")
        print(f"  定番度スコア: {score.relevance_score:.1f}/100点")
        print(f"  判定: {'✅ 定番エピソード' if score.is_iconic else '❌ マイナーエピソード'}")
        print(f"  トップランク: {score.top_rank}位")
        print(f"  検索結果数: {score.search_count}件")

    # テスト2: 堀江貴文 - 起業 vs ライブドア事件
    print("\n" + "=" * 80)
    print("テスト2: 堀江貴文 - どちらが定番エピソードか？")
    print("=" * 80)

    candidates = [
        {
            'keywords': ['起業', '設立', 'オン・ザ・エッヂ', '24歳'],
            'age': 24,
            'description': '有限会社オン・ザ・エッヂ設立'
        },
        {
            'keywords': ['ライブドア', '事件', '逮捕', '上場廃止'],
            'age': 33,
            'description': 'ライブドア事件で逮捕'
        }
    ]

    results = checker.compare_episodes("堀江貴文", candidates, mock_brave_search)

    print("\n定番度ランキング:")
    for i, (episode, score) in enumerate(results, start=1):
        print(f"\n{i}位: {episode['description']} ({episode['age']}歳)")
        print(f"  定番度スコア: {score.relevance_score:.1f}/100点")
        print(f"  判定: {'✅ 定番エピソード' if score.is_iconic else '❌ マイナーエピソード'}")
        print(f"  トップランク: {score.top_rank}位")
        print(f"  検索結果数: {score.search_count}件")

    # テスト3: 大江健三郎 - 芥川賞 vs ノーベル賞
    print("\n" + "=" * 80)
    print("テスト3: 大江健三郎 - どちらが定番エピソードか？")
    print("=" * 80)

    candidates = [
        {
            'keywords': ['芥川賞', '飼育', '23歳'],
            'age': 23,
            'description': '芥川賞受賞'
        },
        {
            'keywords': ['ノーベル賞', 'ノーベル文学賞', '59歳'],
            'age': 59,
            'description': 'ノーベル文学賞受賞'
        }
    ]

    results = checker.compare_episodes("大江健三郎", candidates, mock_brave_search)

    print("\n定番度ランキング:")
    for i, (episode, score) in enumerate(results, start=1):
        print(f"\n{i}位: {episode['description']} ({episode['age']}歳)")
        print(f"  定番度スコア: {score.relevance_score:.1f}/100点")
        print(f"  判定: {'✅ 定番エピソード' if score.is_iconic else '❌ マイナーエピソード'}")
        print(f"  トップランク: {score.top_rank}位")
        print(f"  検索結果数: {score.search_count}件")

    print("\n" + "=" * 80)
    print("テスト完了")
    print("=" * 80)


if __name__ == '__main__':
    test_with_mock_search()
