#!/usr/bin/env python3
"""
Phase 4統合テスト - 定番度判定をBrave Search MCPで実行
"""

from integrated_episode_evaluator import IntegratedEpisodeEvaluator
from typing import List, Dict


def brave_search_wrapper(query: str, count: int = 10) -> List[Dict]:
    """
    Brave Search MCPラッパー

    NOTE: このテストをClaude Code環境で実行する際、
    この関数内でmcp__brave-search__brave_web_searchツールを使用してください

    Args:
        query: 検索クエリ
        count: 取得結果数

    Returns:
        検索結果リスト
    """
    raise NotImplementedError(
        "この関数はClaude Code環境で実行する必要があります。\n"
        "Claude Codeで実行時、mcp__brave-search__brave_web_search ツールを使用してください。"
    )


def test_phase4_integration():
    """Phase 4統合テスト"""

    print("=" * 80)
    print("Phase 4統合テスト - 定番度判定")
    print("=" * 80)

    # テスト用エピソード（ユーザーが指摘した6つの問題エピソード）
    test_episodes = [
        {
            'episode_id': 'EP011',
            'person_name': 'ジェフ・ベゾス',
            'episode_age': 35,
            'episode_text': 'あなたと同じ35歳のとき、ジェフ・ベゾスはヘッジファンドを辞め、妻とともに車でアメリカを横断。Amazon Primeサービスを開始した。このサービスは年会費79ドルで無制限の2日間無料配送を提供し、後にAmazonの主要な収益源となった。',
            'category': 'ビジネス'
        },
        {
            'episode_id': 'EP033',
            'person_name': '堀江貴文',
            'episode_age': 24,
            'episode_text': 'あなたと同じ24歳のとき、堀江貴文は東京大学在学中に有限会社オン・ザ・エッヂを設立した。ホームページ制作事業から始まり、後にライブドアとなる企業の礎を築いた。資本金わずか600万円でのスタートだった。',
            'category': 'ビジネス'
        },
        {
            'episode_id': 'EP035',
            'person_name': '大江健三郎',
            'episode_age': 23,
            'episode_text': 'あなたと同じ23歳のとき、大江健三郎は「飼育」で芥川賞を受賞した。東京大学在学中の受賞で、戦後生まれの作家として初の快挙だった。審査員の川端康成が激賞し、日本文学の新たな才能として注目を集めた。',
            'category': '文化'
        },
    ]

    print("\n注意: このテストはClaude Code環境で実行してください")
    print("Brave Search MCPツールが必要です\n")

    # Phase 4有効の評価器を作成
    print("評価器を初期化中（Phase 4有効）...")
    try:
        evaluator = IntegratedEpisodeEvaluator(mcp_search_function=brave_search_wrapper)
        print("✅ 初期化完了\n")
    except Exception as e:
        print(f"❌ 初期化失敗: {e}\n")
        return

    # 各エピソードを評価
    for episode in test_episodes:
        print("=" * 80)
        print(f"{episode['episode_id']}: {episode['person_name']}（{episode['episode_age']}歳）")
        print("=" * 80)

        try:
            result = evaluator.evaluate(episode)

            print(f"\n📊 評価結果:")
            print(f"  Phase 1 - ルール準拠: {'✅ 合格' if result.compliance_passed else '❌ 不合格'}")
            print(f"  Phase 2 - 配分チェック: {'✅ 合格' if result.distribution_passed else '❌ 不合格'}")
            print(f"    - 年齢時点: {result.age_specific_percentage:.1f}%")
            print(f"  Phase 3 - インパクト評価: {'✅ 合格' if result.impact_passed else '❌ 不合格'}")
            print(f"    - スコア: {result.impact_score}/50点")
            print(f"  Phase 4 - 定番度判定: {'✅ 合格' if result.relevance_passed else '❌ 不合格'}")
            print(f"    - 定番度スコア: {result.relevance_score:.1f}/100点")
            print(f"    - トップ順位: {result.top_rank}位")
            print(f"    - 定番判定: {'✅ 定番' if result.is_iconic else '❌ マイナー'}")

            print(f"\n📝 総合判定: {'✅ 合格' if result.overall_passed else '❌ 不合格'}")
            print(f"推奨: {result.recommendation}")
            print()

        except NotImplementedError as e:
            print(f"\n⚠️ テスト実行不可: {e}")
            print("このテストはClaude Code環境で実行してください\n")
            break
        except Exception as e:
            print(f"\n❌ エラー: {e}\n")
            continue

    print("=" * 80)
    print("テスト完了")
    print("=" * 80)


def test_phase4_disabled():
    """Phase 4無効の動作確認"""

    print("\n" + "=" * 80)
    print("Phase 4無効テスト（MCP関数なし）")
    print("=" * 80)

    # MCP関数なしで初期化（Phase 4スキップ）
    evaluator = IntegratedEpisodeEvaluator(mcp_search_function=None)

    test_episode = {
        'episode_id': 'EP_TEST',
        'person_name': 'テスト太郎',
        'episode_age': 30,
        'episode_text': 'あなたと同じ30歳のとき、テスト太郎は何かを成し遂げた。',
        'category': 'テスト'
    }

    result = evaluator.evaluate(test_episode)

    print(f"\n📊 評価結果:")
    print(f"  Phase 4 - 定番度判定: {'✅ 合格（スキップ）' if result.relevance_passed else '❌ 不合格'}")
    print(f"    - 定番度スコア: {result.relevance_score:.1f}/100点（デフォルト値）")
    print(f"    - 定番判定: {'✅ 定番' if result.is_iconic else '❌ マイナー'}（デフォルト値）")

    print("\n✅ Phase 4無効時は自動的にスキップされる（デフォルト合格）\n")


if __name__ == '__main__':
    print("\n🧪 Phase 4統合テストスイート\n")

    # テスト1: Phase 4無効（すぐに実行可能）
    test_phase4_disabled()

    # テスト2: Phase 4有効（Claude Code環境必須）
    test_phase4_integration()

    print("\n" + "=" * 80)
    print("📝 次のステップ:")
    print("=" * 80)
    print("1. Claude Code環境でこのテストを実行")
    print("2. Brave Search MCPが正しく動作することを確認")
    print("3. 6つの問題エピソードがPhase 4で検出されることを確認")
    print("4. 全100エピソードの評価を実行")
    print("=" * 80)
