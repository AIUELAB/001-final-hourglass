#!/usr/bin/env python3
"""
Phase 4.1: RULE_172 MCP統合テスト

brave-search MCPサーバーを使用した実データ取得のテスト
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from rules.rule_172_social_impact import SocialImpactAnalyzer

def test_mcp_integration():
    """MCP統合テスト"""
    print("=" * 80)
    print("Phase 4.1: RULE_172 MCP統合テスト")
    print("=" * 80)
    print()

    # テストケース
    test_cases = [
        {
            "person": "大谷翔平",
            "text": "あなたと同じ28歳のとき、大谷翔平はMLBでア・リーグMVPを受賞し、投手と打者の二刀流で歴史を変えた。2021年シーズン、投球では9勝、156奪三振、打撃では46本塁打、100打点を記録。ベーブ・ルース以来100年ぶりの快挙として世界中のメディアが報じ、野球の常識を覆した。"
        },
        {
            "person": "山中伸弥",
            "text": "あなたと同じ45歳のとき、山中伸弥はiPS細胞の作製でノーベル生理学・医学賞を受賞した。2006年にマウス皮膚細胞から万能細胞を作る方法を発見し、わずか6年でノーベル賞。再生医療に革命をもたらし、世界中の難病患者に希望を与えた。"
        },
        {
            "person": "HIKAKIN",
            "text": "あなたと同じ23歳のとき、HIKAKINはYouTube登録者数100万人を突破し、日本のYouTuber文化の礎を築いた。2012年、ボイスパーカッションの動画が海外で1000万再生を記録し一夜にして有名に。その後、子供向けコンテンツで健全なYouTubeエンターテイメントを確立した。"
        }
    ]

    print("🔧 テストモード1: MCP統合モード（実データ取得）")
    print("-" * 80)
    analyzer_mcp = SocialImpactAnalyzer(use_mcp=True)
    print()

    for i, test in enumerate(test_cases, 1):
        print(f"テストケース {i}: {test['person']}")
        print(f"  テキスト: {test['text'][:60]}...")
        print()

        try:
            result = analyzer_mcp.evaluate(test["person"], test["text"])

            status = "✅ 合格" if result["passed"] else "❌ 不合格"
            print(f"  {status}")
            print(f"  📊 総合スコア: {result['total_score']:.1f}点")
            print(f"  📈 インパクトレベル: {result['impact_level']}")
            print(f"  📋 メトリクス:")
            for key, value in result["metrics"].items():
                print(f"     - {key}: {value}")
            print(f"  📝 エビデンス:")
            for evidence in result["evidence"][:3]:
                print(f"     {evidence}")
        except Exception as e:
            print(f"  ⚠️ エラー: {e}")
            import traceback
            traceback.print_exc()

        print()

    print("=" * 80)
    print()

    print("🔧 テストモード2: 推定モード（フォールバック）")
    print("-" * 80)
    analyzer_estimate = SocialImpactAnalyzer(use_mcp=False)
    print()

    # 1件だけテスト（比較用）
    test = test_cases[0]
    print(f"比較テスト: {test['person']}")
    result = analyzer_estimate.evaluate(test["person"], test["text"])
    print(f"  総合スコア: {result['total_score']:.1f}点")
    print(f"  データソース: {result['evidence'][0]}")
    print()

    print("=" * 80)
    print("✅ Phase 4.1 MCP統合テスト完了")
    print("=" * 80)
    print()
    print("次のステップ:")
    print("1. ✅ RULE_172 MCP統合完了")
    print("2. 🔄 Phase 4.2: RULE_173年齢柔軟性エンジン実装")
    print("3. 🔄 Phase 4.3: RULE_174-178実装")
    print("=" * 80)


if __name__ == "__main__":
    test_mcp_integration()
