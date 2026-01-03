#!/usr/bin/env python3
"""
アインシュタインのエピソードスコア寄与分解
EP-3947C4DE問題の根本原因分析
"""

import csv
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.score.episode_fame_v6.scorer import EpisodeFameV6Scorer
from scripts.score.episode_fame_v6.config import WEIGHTS

CSV_PATH = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")
REPORT_PATH = Path("src/reports/einstein_score_analysis.json")


def main():
    # 全エピソード読み込み
    with open(CSV_PATH, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_episodes = list(reader)

    # アインシュタイン (P93F1DB1) のエピソードを抽出
    einstein_eps = [e for e in all_episodes if e.get("person_id") == "P93F1DB1"]

    print(f"アインシュタイン エピソード数: {len(einstein_eps)}")

    # v6スコアラー初期化
    scorer = EpisodeFameV6Scorer(all_episodes)

    # 各エピソードの寄与分解
    analysis = []
    for ep in einstein_eps:
        breakdown = scorer.score_episode(ep)

        # 加重スコア計算
        weighted = {
            "person_fame": breakdown.person_fame * WEIGHTS["person_fame"],
            "llm_quality": breakdown.llm_quality * WEIGHTS["llm_quality"],
            "historical_impact": breakdown.historical_impact * WEIGHTS["historical_impact"],
            "pv_signal": breakdown.pv_signal * WEIGHTS["pv_signal"],
            "episode_bonus": breakdown.episode_bonus * WEIGHTS["episode_bonus"],
        }

        result = {
            "episode_id": ep.get("episode_id"),
            "age": ep.get("age"),
            "episode_type": ep.get("episode_type"),
            "episode_text_head": ep.get("episode_text", "")[:100] + "...",
            "scores": {
                "episode_fame_score_col30": float(ep.get("episode_fame_score") or 0),
                "episode_fame_v5": float(ep.get("episode_fame_score_v5") or 0),
                "episode_fame_v6": float(ep.get("episode_fame_v6") or 0),
            },
            "v6_breakdown": {
                "person_fame_raw": round(breakdown.person_fame, 2),
                "person_fame_weighted": round(weighted["person_fame"], 2),
                "llm_quality_raw": round(breakdown.llm_quality, 2),
                "llm_quality_weighted": round(weighted["llm_quality"], 2),
                "historical_impact_raw": round(breakdown.historical_impact, 2),
                "historical_impact_weighted": round(weighted["historical_impact"], 2),
                "pv_signal_raw": round(breakdown.pv_signal, 2),
                "pv_signal_weighted": round(weighted["pv_signal"], 2),
                "episode_bonus_raw": round(breakdown.episode_bonus, 2),
                "episode_bonus_weighted": round(weighted["episode_bonus"], 2),
                "penalty": round(breakdown.penalty, 2),
                "total_v6_calculated": round(breakdown.total_score, 2),
            },
            "input_features": {
                "celebrity_score_v2": float(ep.get("celebrity_score_v2") or 0),
                "sitelinks_count": int(float(ep.get("sitelinks_count") or 0)),
                "multi_lang_pv": int(float(ep.get("multi_lang_pv") or 0)),
                "episode_count": int(float(ep.get("episode_count") or 1)),
                "記憶性スコア": float(ep.get("記憶性スコア") or 0),
                "共感性スコア": float(ep.get("共感性スコア") or 0),
                "意外性スコア": float(ep.get("意外性スコア") or 0),
                "生成品質スコア": float(ep.get("生成品質スコア") or 0),
                "教育的価値": float(ep.get("教育的価値") or 0),
                "ストーリー品質": float(ep.get("ストーリー品質") or 0),
                "事実密度": float(ep.get("事実密度") or 0),
            },
        }
        analysis.append(result)

    # v6スコア順にソート
    analysis.sort(key=lambda x: x["scores"]["episode_fame_v6"], reverse=True)

    # 問題分析
    target_ep = next((a for a in analysis if a["episode_id"] == "EP-3947C4DE"), None)

    report = {
        "timestamp": datetime.now().isoformat(),
        "target_episode": "EP-3947C4DE",
        "person": "アインシュタイン (P93F1DB1)",
        "problem_summary": {
            "col30_score": target_ep["scores"]["episode_fame_score_col30"] if target_ep else None,
            "v5_score": target_ep["scores"]["episode_fame_v5"] if target_ep else None,
            "v6_score": target_ep["scores"]["episode_fame_v6"] if target_ep else None,
            "v6_rank_in_person": next((i+1 for i, a in enumerate(analysis) if a["episode_id"] == "EP-3947C4DE"), None),
        },
        "root_cause": "ダッシュボードが episode_fame_score (col30) を使用しているが、v6スコアが反映されていない",
        "episodes_by_v6_rank": analysis,
    }

    # レポート保存
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 要約出力
    print(f"\n=== EP-3947C4DE (奇跡の年) 分析結果 ===")
    if target_ep:
        print(f"col30スコア: {target_ep['scores']['episode_fame_score_col30']}")
        print(f"v5スコア: {target_ep['scores']['episode_fame_v5']}")
        print(f"v6スコア: {target_ep['scores']['episode_fame_v6']}")
        print(f"v6順位: {report['problem_summary']['v6_rank_in_person']}/5")
        print(f"\n寄与分解 (v6):")
        bd = target_ep["v6_breakdown"]
        print(f"  person_fame:      {bd['person_fame_weighted']:.2f} (raw: {bd['person_fame_raw']:.2f})")
        print(f"  llm_quality:      {bd['llm_quality_weighted']:.2f} (raw: {bd['llm_quality_raw']:.2f})")
        print(f"  historical_impact:{bd['historical_impact_weighted']:.2f} (raw: {bd['historical_impact_raw']:.2f})")
        print(f"  pv_signal:        {bd['pv_signal_weighted']:.2f} (raw: {bd['pv_signal_raw']:.2f})")
        print(f"  episode_bonus:    {bd['episode_bonus_weighted']:.2f} (raw: {bd['episode_bonus_raw']:.2f})")
        print(f"  penalty:          -{bd['penalty']:.2f}")
        print(f"  合計:             {bd['total_v6_calculated']:.2f}")

    print(f"\nレポート保存: {REPORT_PATH}")


if __name__ == "__main__":
    main()
