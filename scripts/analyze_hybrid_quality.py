#!/usr/bin/env python3
"""
品質分析レポート生成

既存EP vs 新規EP（ハイブリッド生成）の品質比較
"""

import csv
import json
import re
import statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path


PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src" / "reports"


def load_episodes() -> tuple[list[dict], list[dict]]:
    """既存EPと新規EPを分離してロード"""
    existing = []
    new_hybrid = []

    with open(MASTER_CSV, encoding="utf-8-sig") as f:  # BOM対応
        reader = csv.DictReader(f)
        for row in reader:
            episode_id = row.get("episode_id", "")

            # 新規EP判定: EP-26 で始まる (2026年生成)
            if episode_id.startswith("EP-26"):
                new_hybrid.append(row)
            else:
                existing.append(row)

    return existing, new_hybrid


def safe_float(value: str, default: float = 0.0) -> float:
    """安全にfloatに変換"""
    try:
        return float(value) if value else default
    except ValueError:
        return default


def analyze_scores(episodes: list[dict]) -> dict:
    """スコア分析"""
    super_totals = []
    axis_scores = defaultdict(list)

    axis_columns = [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
    ]

    for ep in episodes:
        # super_total_score
        st = safe_float(ep.get("super_total_score", ""))
        if st > 0:
            super_totals.append(st)

        # 7軸スコア
        for col in axis_columns:
            val = safe_float(ep.get(col, ""))
            if val > 0:
                axis_scores[col].append(val)

    result = {
        "super_total": {
            "count": len(super_totals),
            "mean": statistics.mean(super_totals) if super_totals else 0,
            "median": statistics.median(super_totals) if super_totals else 0,
            "std": statistics.stdev(super_totals) if len(super_totals) > 1 else 0,
            "min": min(super_totals) if super_totals else 0,
            "max": max(super_totals) if super_totals else 0,
        },
        "axis_scores": {},
    }

    for col, scores in axis_scores.items():
        if scores:
            result["axis_scores"][col] = {
                "mean": statistics.mean(scores),
                "median": statistics.median(scores),
            }

    return result


def analyze_quality_gates(episodes: list[dict]) -> dict:
    """品質ゲート通過率分析"""
    total = len(episodes)
    factual_pass = 0
    generation_pass = 0
    both_pass = 0

    for ep in episodes:
        fd = safe_float(ep.get("factual_density", ""))
        gq = safe_float(ep.get("generation_quality_score", ""))

        fd_ok = fd >= 6.0
        gq_ok = gq >= 6.0

        if fd_ok:
            factual_pass += 1
        if gq_ok:
            generation_pass += 1
        if fd_ok and gq_ok:
            both_pass += 1

    return {
        "total": total,
        "factual_density_pass": factual_pass,
        "factual_density_rate": factual_pass / total * 100 if total else 0,
        "generation_quality_pass": generation_pass,
        "generation_quality_rate": generation_pass / total * 100 if total else 0,
        "both_pass": both_pass,
        "both_rate": both_pass / total * 100 if total else 0,
    }


def analyze_content(episodes: list[dict]) -> dict:
    """コンテンツ分析"""
    char_counts = []
    year_count = 0
    proper_noun_counts = []

    year_pattern = re.compile(r"(1[789]\d{2}|20[0-2]\d)年")
    proper_noun_pattern = re.compile(r"「([^」]+)」")

    for ep in episodes:
        text = ep.get("episode_text", "")
        char_counts.append(len(text))

        # 年号含有
        if year_pattern.search(text):
            year_count += 1

        # 固有名詞（「」で囲まれた語）
        proper_nouns = proper_noun_pattern.findall(text)
        proper_noun_counts.append(len(proper_nouns))

    total = len(episodes)

    return {
        "total": total,
        "avg_char_count": statistics.mean(char_counts) if char_counts else 0,
        "median_char_count": statistics.median(char_counts) if char_counts else 0,
        "year_inclusion_count": year_count,
        "year_inclusion_rate": year_count / total * 100 if total else 0,
        "avg_proper_nouns": statistics.mean(proper_noun_counts) if proper_noun_counts else 0,
    }


def generate_report(existing_stats: dict, new_stats: dict) -> str:
    """レポートMarkdown生成"""

    report = f"""# 品質分析レポート: 既存EP vs 新規EP（ハイブリッド生成）

生成日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## 1. 概要

| 区分 | エピソード数 |
|------|-------------|
| 既存EP | {existing_stats["score"]["super_total"]["count"]:,} |
| 新規EP（ハイブリッド生成） | {new_stats["score"]["super_total"]["count"]:,} |

---

## 2. super_total_score 分布

| 指標 | 既存EP | 新規EP | 差分 |
|------|--------|--------|------|
| 平均 | {existing_stats["score"]["super_total"]["mean"]:,.0f} | {new_stats["score"]["super_total"]["mean"]:,.0f} | {new_stats["score"]["super_total"]["mean"] - existing_stats["score"]["super_total"]["mean"]:+,.0f} |
| 中央値 | {existing_stats["score"]["super_total"]["median"]:,.0f} | {new_stats["score"]["super_total"]["median"]:,.0f} | {new_stats["score"]["super_total"]["median"] - existing_stats["score"]["super_total"]["median"]:+,.0f} |
| 標準偏差 | {existing_stats["score"]["super_total"]["std"]:,.0f} | {new_stats["score"]["super_total"]["std"]:,.0f} | - |
| 最小値 | {existing_stats["score"]["super_total"]["min"]:,.0f} | {new_stats["score"]["super_total"]["min"]:,.0f} | - |
| 最大値 | {existing_stats["score"]["super_total"]["max"]:,.0f} | {new_stats["score"]["super_total"]["max"]:,.0f} | - |

---

## 3. 7軸スコア平均比較

| 軸 | 既存EP | 新規EP | 差分 |
|-----|--------|--------|------|
"""

    axis_order = [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
    ]

    for axis in axis_order:
        e_val = existing_stats["score"]["axis_scores"].get(axis, {}).get("mean", 0)
        n_val = new_stats["score"]["axis_scores"].get(axis, {}).get("mean", 0)
        diff = n_val - e_val
        report += f"| {axis} | {e_val:.2f} | {n_val:.2f} | {diff:+.2f} |\n"

    report += f"""
---

## 4. 品質ゲート通過率

| 指標 | 既存EP | 新規EP |
|------|--------|--------|
| factual_density ≥ 6.0 | {existing_stats["gate"]["factual_density_rate"]:.1f}% ({existing_stats["gate"]["factual_density_pass"]:,}/{existing_stats["gate"]["total"]:,}) | {new_stats["gate"]["factual_density_rate"]:.1f}% ({new_stats["gate"]["factual_density_pass"]:,}/{new_stats["gate"]["total"]:,}) |
| 生成品質 ≥ 6.0 | {existing_stats["gate"]["generation_quality_rate"]:.1f}% ({existing_stats["gate"]["generation_quality_pass"]:,}/{existing_stats["gate"]["total"]:,}) | {new_stats["gate"]["generation_quality_rate"]:.1f}% ({new_stats["gate"]["generation_quality_pass"]:,}/{new_stats["gate"]["total"]:,}) |
| 両方クリア | {existing_stats["gate"]["both_rate"]:.1f}% ({existing_stats["gate"]["both_pass"]:,}/{existing_stats["gate"]["total"]:,}) | {new_stats["gate"]["both_rate"]:.1f}% ({new_stats["gate"]["both_pass"]:,}/{new_stats["gate"]["total"]:,}) |

---

## 5. コンテンツ分析

| 指標 | 既存EP | 新規EP |
|------|--------|--------|
| 平均文字数 | {existing_stats["content"]["avg_char_count"]:.0f}文字 | {new_stats["content"]["avg_char_count"]:.0f}文字 |
| 年号含有率 | {existing_stats["content"]["year_inclusion_rate"]:.1f}% | {new_stats["content"]["year_inclusion_rate"]:.1f}% |
| 平均固有名詞数 | {existing_stats["content"]["avg_proper_nouns"]:.1f}個 | {new_stats["content"]["avg_proper_nouns"]:.1f}個 |

---

## 6. 結論

"""

    # 自動評価
    score_diff = new_stats["score"]["super_total"]["mean"] - existing_stats["score"]["super_total"]["mean"]
    if score_diff > 50000:
        report += "- super_total_score: 新規EPが大幅に優位\n"
    elif score_diff > 0:
        report += "- super_total_score: 新規EPがやや優位\n"
    else:
        report += f"- super_total_score: 既存EPが優位（差: {abs(score_diff):,.0f}）\n"

    gate_diff = new_stats["gate"]["both_rate"] - existing_stats["gate"]["both_rate"]
    if gate_diff > 5:
        report += "- 品質ゲート通過率: 新規EPが優位\n"
    elif gate_diff > -5:
        report += "- 品質ゲート通過率: ほぼ同等\n"
    else:
        report += "- 品質ゲート通過率: 既存EPが優位\n"

    return report


def main():
    print("Loading episodes...")
    existing, new_hybrid = load_episodes()
    print(f"  既存EP: {len(existing):,}")
    print(f"  新規EP: {len(new_hybrid):,}")

    print("Analyzing existing episodes...")
    existing_stats = {
        "score": analyze_scores(existing),
        "gate": analyze_quality_gates(existing),
        "content": analyze_content(existing),
    }

    print("Analyzing new episodes...")
    new_stats = {
        "score": analyze_scores(new_hybrid),
        "gate": analyze_quality_gates(new_hybrid),
        "content": analyze_content(new_hybrid),
    }

    print("Generating report...")
    report_md = generate_report(existing_stats, new_stats)

    # レポート保存
    report_path = REPORT_DIR / "quality_comparison_report.md"
    report_path.write_text(report_md, encoding="utf-8")
    print(f"Saved: {report_path}")

    # JSONデータ保存
    json_path = REPORT_DIR / "quality_comparison_data.json"
    json_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now().isoformat(),
                "existing": existing_stats,
                "new_hybrid": new_stats,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Saved: {json_path}")

    # サマリー表示
    print("\n=== Summary ===")
    print("super_total_score 平均:")
    print(f"  既存: {existing_stats['score']['super_total']['mean']:,.0f}")
    print(f"  新規: {new_stats['score']['super_total']['mean']:,.0f}")
    print("品質ゲート両方クリア率:")
    print(f"  既存: {existing_stats['gate']['both_rate']:.1f}%")
    print(f"  新規: {new_stats['gate']['both_rate']:.1f}%")


if __name__ == "__main__":
    main()
