#!/usr/bin/env python3
"""
Phase 7: LLM評価機能のテストスクリプト

Usage:
    python scripts/test_llm_evaluation.py [--samples N] [--no-calibrate]
"""

import argparse
import json
import os
import sys
from pathlib import Path

import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.utils.score_calculator import (
    LLM_EVALUATION_PROMPT,
    LLM_TARGET_STATS,
    batch_evaluate_with_llm,
    calculate_hybrid_rule_scores,
    calculate_hybrid_scores_with_llm,
    calibrate_llm_score,
    evaluate_with_llm,
    parse_llm_response,
)


def test_parse_llm_response():
    """parse_llm_response関数のテスト"""
    print("\n=== parse_llm_response テスト ===")

    # 正常ケース
    valid_json = (
        '{"記憶性": 8, "共感性": 6, "意外性": 7, "生成品質": 9, "教育的価値": 5, "ストーリー品質": 7, "事実密度": 8}'
    )
    result = parse_llm_response(valid_json)
    assert result is not None, "正常JSONのパース失敗"
    assert result["記憶性"] == 8, "記憶性スコアが不正"
    print(f"✅ 正常JSON: {result}")

    # 前後にテキストがあるケース
    with_text = 'Here is the evaluation:\n{"記憶性": 7, "共感性": 8, "意外性": 6, "生成品質": 7, "教育的価値": 6, "ストーリー品質": 8, "事実密度": 7}\nThank you!'
    result2 = parse_llm_response(with_text)
    assert result2 is not None, "テキスト付きJSONのパース失敗"
    print(f"✅ テキスト付きJSON: {result2}")

    # 不正ケース
    invalid_json = "This is not JSON"
    result3 = parse_llm_response(invalid_json)
    assert result3 is None, "不正JSONでNoneが返るべき"
    print("✅ 不正JSON: None返却確認")

    print("✅ parse_llm_response テスト完了")


def test_calibrate_llm_score():
    """calibrate_llm_score関数のテスト"""
    print("\n=== calibrate_llm_score テスト ===")

    # 各軸でキャリブレーションテスト
    test_cases = [
        ("記憶性", 7.0, 6.24),  # 平均付近は平均に近づく
        ("共感性", 9.0, 6.74),  # 高スコアは補正
        ("事実密度", 5.0, 7.47),  # 低スコアは補正
    ]

    for axis, raw_score, expected_approx in test_cases:
        calibrated = calibrate_llm_score(raw_score, axis)
        print(f"  {axis}: {raw_score} → {calibrated} (期待: ~{expected_approx})")
        assert 1 <= calibrated <= 10, f"キャリブレーション後のスコアが範囲外: {calibrated}"

    print("✅ calibrate_llm_score テスト完了")


def test_llm_evaluation_prompt():
    """プロンプトフォーマットのテスト"""
    print("\n=== LLM_EVALUATION_PROMPT テスト ===")

    test_episode = "山田太郎は1990年に東京大学を卒業後、起業家として成功を収めた。"
    prompt = LLM_EVALUATION_PROMPT.format(episode_text=test_episode)

    assert "{episode_text}" not in prompt, "プレースホルダーが残っている"
    assert test_episode in prompt, "エピソードテキストが含まれていない"
    assert "記憶性" in prompt, "評価軸が含まれていない"
    assert "JSON" in prompt, "出力形式指示が含まれていない"

    print(f"✅ プロンプト長: {len(prompt)} 文字")
    print("✅ LLM_EVALUATION_PROMPT テスト完了")


def test_evaluate_with_llm_real(episode_text: str, calibrate: bool = True):
    """実際のLLM API呼び出しテスト"""
    print("\n=== evaluate_with_llm 実テスト ===")
    print(f"エピソード: {episode_text[:100]}...")

    # API呼び出し
    scores = evaluate_with_llm(episode_text, calibrate=calibrate)

    if scores is None:
        print("❌ LLM評価失敗（API未設定の可能性）")
        return None

    print(f"✅ LLM評価結果 (calibrate={calibrate}):")
    for axis, score in scores.items():
        target = LLM_TARGET_STATS.get(axis, {})
        print(f"  {axis}: {score} (目標平均: {target.get('mean', 'N/A')})")

    return scores


def test_hybrid_scores(episode_data: dict, use_llm: bool = True):
    """ハイブリッドスコア計算テスト"""
    print("\n=== calculate_hybrid_scores_with_llm テスト ===")

    # ルールベースのみ
    rule_scores = calculate_hybrid_rule_scores(episode_data)
    print("ルールベーススコア:")
    for axis, score in rule_scores.items():
        print(f"  {axis}: {score}")

    if use_llm:
        # LLM連携
        hybrid_scores = calculate_hybrid_scores_with_llm(episode_data, use_llm=True)
        print("\nハイブリッドスコア (LLM連携):")
        for axis, score in hybrid_scores.items():
            print(f"  {axis}: {score}")
        return hybrid_scores

    return rule_scores


def load_sample_episodes(n: int = 5) -> list:
    """サンプルエピソードを読み込み"""
    csv_path = project_root / "preserved/data/MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return []

    df = pd.read_csv(csv_path, encoding="utf-8-sig", nrows=n * 10)

    # episode_textがあるものをフィルタ
    df = df[df["episode_text"].notna() & (df["episode_text"].str.len() > 100)]

    samples = df.head(n).to_dict("records")
    print(f"✅ {len(samples)}件のサンプルエピソードを読み込み")

    return samples


def main():
    parser = argparse.ArgumentParser(description="LLM評価機能のテスト")
    parser.add_argument("--samples", type=int, default=3, help="テストするサンプル数")
    parser.add_argument("--no-calibrate", action="store_true", help="キャリブレーションを無効化")
    parser.add_argument("--skip-api", action="store_true", help="API呼び出しをスキップ")
    args = parser.parse_args()

    print("=" * 60)
    print("Phase 7: LLM評価機能テスト")
    print("=" * 60)

    # 単体テスト
    test_parse_llm_response()
    test_calibrate_llm_score()
    test_llm_evaluation_prompt()

    if args.skip_api:
        print("\n⏭️ API呼び出しテストをスキップ")
        return

    # サンプルエピソードでテスト
    samples = load_sample_episodes(args.samples)

    if not samples:
        print("❌ サンプルエピソードがありません")
        return

    results = []
    for i, episode in enumerate(samples):
        print(f"\n--- サンプル {i + 1}/{len(samples)} ---")
        print(f"人物: {episode.get('person_name', 'N/A')}")

        # LLM評価テスト
        llm_scores = test_evaluate_with_llm_real(
            episode.get("episode_text", ""),
            calibrate=not args.no_calibrate,
        )

        if llm_scores:
            results.append(
                {
                    "person_name": episode.get("person_name"),
                    "llm_scores": llm_scores,
                }
            )

    # 結果サマリー
    if results:
        print("\n" + "=" * 60)
        print("テスト結果サマリー")
        print("=" * 60)

        # 分散計算
        import statistics

        for axis in LLM_TARGET_STATS.keys():
            scores = [r["llm_scores"].get(axis, 7) for r in results if r["llm_scores"]]
            if len(scores) >= 2:
                mean_score = statistics.mean(scores)
                std_score = statistics.stdev(scores)
                target_std = LLM_TARGET_STATS[axis]["std"]
                print(f"{axis}: 平均={mean_score:.2f}, σ={std_score:.2f} (目標σ={target_std})")

        # 結果をJSONで保存
        output_path = project_root / "reports/llm_evaluation_test_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 結果保存: {output_path}")


if __name__ == "__main__":
    main()
