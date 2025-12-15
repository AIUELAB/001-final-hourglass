#!/usr/bin/env python3
"""
Phase 4評価実行スクリプト
全100エピソードの定番度判定をBrave Search MCPで実行
"""

import csv
import time
from typing import List, Dict
from integrated_episode_evaluator import IntegratedEpisodeEvaluator


def brave_search_wrapper(query: str, count: int = 10) -> List[Dict]:
    """
    Brave Search MCPラッパー

    NOTE: このスクリプトをClaude Code環境で実行する際、
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


def main():
    """メイン処理"""

    print("=" * 80)
    print("Phase 4評価実行 - 全100エピソードの定番度判定")
    print("=" * 80)

    input_csv = "episodes_validated_100_20251001.csv"
    output_csv = "episodes_phase4_evaluation_20251001.csv"

    print(f"\n入力: {input_csv}")
    print(f"出力: {output_csv}")
    print()

    # 評価器を初期化（Phase 4有効）
    print("評価器を初期化中（Phase 4有効）...")
    try:
        evaluator = IntegratedEpisodeEvaluator(mcp_search_function=brave_search_wrapper)
        print("✅ 初期化完了\n")
    except Exception as e:
        print(f"❌ 初期化失敗: {e}\n")
        return

    # 全エピソード評価
    print("=" * 80)
    print("評価開始")
    print("=" * 80)
    print()
    print("⚠️ 注意: 100エピソード × 平均5クエリ = 約500リクエスト")
    print("⚠️ API Rate Limit対策で各エピソード間に0.5秒待機")
    print("⚠️ 推定所要時間: 約50秒 + 検索時間")
    print()

    try:
        results = evaluator.evaluate_all(input_csv)

        # サマリー表示
        print("\n" + "=" * 80)
        print("評価完了")
        print("=" * 80)
        print(evaluator.get_summary_report(results))

        # 結果を保存
        evaluator.save_results(results, output_csv)
        print(f"✅ 評価結果を保存: {output_csv}")

        # Phase 4不合格エピソードの詳細表示
        print("\n" + "=" * 80)
        print("Phase 4不合格エピソード詳細")
        print("=" * 80)

        phase4_failures = [r for r in results if r.compliance_passed and
                          r.distribution_passed and r.impact_passed and not r.relevance_passed]

        if phase4_failures:
            print(f"\n定番度不足: {len(phase4_failures)}件\n")

            for r in sorted(phase4_failures, key=lambda x: x.relevance_score):
                print(f"エピソードID: {r.episode_id}")
                print(f"  人物名: {r.person_name}")
                print(f"  年齢: {r.episode_age}歳")
                print(f"  定番度スコア: {r.relevance_score:.1f}/100点")
                print(f"  トップ順位: {r.top_rank}位")
                print(f"  エピソード: {r.episode_text[:80]}...")
                print(f"  推奨: {r.recommendation}")
                print()
        else:
            print("\n✅ すべてのエピソードがPhase 4基準を満たしています")

    except NotImplementedError as e:
        print(f"\n⚠️ {e}")
        print("\nこのスクリプトはClaude Code環境で実行してください")
        return
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 80)
    print("処理完了")
    print("=" * 80)


if __name__ == '__main__':
    main()
