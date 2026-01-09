#!/usr/bin/env python3
"""
episode_fame_score 再計算スクリプト

バッチ生成時期によるスケール不整合を解消し、
全エピソードを1-10スケールで統一する

評価基準: 歴史的重要性ベース
"""

import csv
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import shutil

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backup"
OUTPUT_DIR = PROJECT_ROOT / "reports"


# エピソードタイプによる基本重要性ボーナス
# 注意: ACHIEVEMENT等はfactual_densityに応じて1.0-1.3倍に調整される
TYPE_BONUS_BASE = {
    "ACHIEVEMENT": 1.3,  # 偉業達成（条件付きで最大効果）
    "TURNING_POINT": 1.0,  # 転機
    "FOUNDING": 1.3,  # 創業・設立（条件付きで最大効果）
    "INNOVATION": 1.3,  # 革新（条件付きで最大効果）
    "CHALLENGE": 0.5,  # 挑戦
    "DEBUT": 0.8,  # デビュー
    "RECORD": 1.2,  # 記録達成
    "AWARD": 1.0,  # 受賞
    "DISCOVERY": 1.3,  # 発見（条件付きで最大効果）
    "CREATION": 1.0,  # 創作
}

# factual_densityによる倍率補正が適用されるタイプ
FACT_DENSITY_DEPENDENT_TYPES = {"ACHIEVEMENT", "FOUNDING", "INNOVATION", "DISCOVERY"}

# 歴史的重要キーワード（+0.5 each, max 2.0）
HISTORICAL_KEYWORDS = [
    # 史上初系
    "日本初",
    "世界初",
    "史上初",
    "初めて",
    "最初の",
    # 受賞系
    "ノーベル賞",
    "オリンピック",
    "金メダル",
    "銀メダル",
    "銅メダル",
    "アカデミー賞",
    "グラミー賞",
    "世界記録",
    "日本記録",
    # 歴史的出来事
    "改革",
    "革命",
    "維新",
    "建国",
    "独立",
    "発見",
    "発明",
    "創設",
    "設立",
    "創業",
    # 社会的影響
    "国民的",
    "歴史的",
    "画期的",
    "記念碑的",
    # 文化的重要性
    "代表作",
    "傑作",
    "名作",
    "金字塔",
]

# 個人的エピソードキーワード（ペナルティ）
PERSONAL_KEYWORDS = [
    "家族",
    "私生活",
    "病気",
    "入院",
    "療養",
    "結婚",
    "離婚",
    "恋愛",
    "交際",
    "子供の頃",
    "幼少期",
    "学生時代",
]

# 低重要度キーワード（ペナルティ）
LOW_IMPORTANCE_KEYWORDS = [
    "日常",
    "普通の",
    "平凡な",
    "一般的な",
    "趣味",
    "プライベート",
]


def calculate_episode_fame_v3(row: dict) -> tuple[float, int, str]:
    """
    歴史的重要性ベースのエピソード有名度計算

    Returns:
        tuple: (score, tier, reason)
        - score: 1.0-100.0 のスコア（10倍スケール）
        - tier: 1-5 のティア
        - reason: スコア計算の理由
    """
    base = 50.0  # 10倍スケール
    reasons = []

    episode_type = row.get("episode_type", "").strip().upper()
    episode_text = row.get("episode_text", "")

    # factual_densityを取得（タイプボーナス条件に使用）
    fact_density = 0.0
    try:
        fact_density = float(row.get("factual_density", 0) or 0)
    except (ValueError, TypeError):
        fact_density = 0.0

    # 1. エピソードタイプによる重要性 (+0〜13)
    # factual_density依存タイプはfactual_densityに応じて1.0-1.3倍に調整
    base_type_bonus = TYPE_BONUS_BASE.get(episode_type, 0)

    if episode_type in FACT_DENSITY_DEPENDENT_TYPES:
        # factual_density≥5.0で最大効果、<5.0で1.0倍に減衰
        if fact_density >= 5.0:
            type_multiplier = 1.0
        else:
            type_multiplier = max(0.77, fact_density / 5.0)  # 最低でも1.0/1.3≈0.77倍
        type_bonus = base_type_bonus * type_multiplier * 10
        if type_bonus > 0:
            reasons.append(f"type:{episode_type}+{type_bonus:.1f}(fd={fact_density:.1f})")
    else:
        type_bonus = base_type_bonus * 10  # 10倍
        if type_bonus > 0:
            reasons.append(f"type:{episode_type}+{type_bonus}")

    # 2. 歴史的重要キーワード (+5 each, max 20)
    history_count = 0
    matched_historical = []
    for kw in HISTORICAL_KEYWORDS:
        if kw in episode_text:
            history_count += 1
            matched_historical.append(kw)
    history_bonus = min(history_count * 5, 20)  # 10倍
    if history_bonus > 0:
        reasons.append(f"hist:{','.join(matched_historical[:3])}+{history_bonus}")

    # 3. 個人的エピソードペナルティ (-5 each, max 20)
    personal_count = 0
    matched_personal = []
    for kw in PERSONAL_KEYWORDS:
        if kw in episode_text:
            personal_count += 1
            matched_personal.append(kw)
    personal_penalty = min(personal_count * 5, 20)  # 10倍
    if personal_penalty > 0:
        reasons.append(f"personal:{','.join(matched_personal[:2])}-{personal_penalty}")

    # 4. 低重要度ペナルティ (-3 each, max 10)
    low_count = 0
    for kw in LOW_IMPORTANCE_KEYWORDS:
        if kw in episode_text:
            low_count += 1
    low_penalty = min(low_count * 3, 10)  # 10倍
    if low_penalty > 0:
        reasons.append(f"low:-{low_penalty}")

    # 5. 人物の知名度による調整（person_fame_scoreがあれば）
    person_fame = row.get("person_fame_score", "")
    person_bonus = 0
    if person_fame:
        try:
            pf = float(person_fame)
            if pf >= 9.0:
                person_bonus = 5  # 10倍
            elif pf >= 8.0:
                person_bonus = 3  # 10倍
            elif pf <= 3.0:
                person_bonus = -3  # 10倍
            if person_bonus != 0:
                reasons.append(f"person_fame:{pf}→{person_bonus:+d}")
        except ValueError:
            pass

    # 最終スコア計算 (1-100スケール)
    score = base + type_bonus + history_bonus - personal_penalty - low_penalty + person_bonus
    score = max(1.0, min(100.0, round(score, 0)))  # 1-100

    # ティア計算 (10倍スケール)
    if score >= 90:
        tier = 5
    elif score >= 75:
        tier = 4
    elif score >= 60:
        tier = 3
    elif score >= 45:
        tier = 2
    else:
        tier = 1

    reason_str = "; ".join(reasons) if reasons else "base:50"

    return score, tier, reason_str


def analyze_current_distribution(rows: list) -> dict:
    """現在のスコア分布を分析"""
    stats = {
        "total": len(rows),
        "by_batch": defaultdict(lambda: {"count": 0, "scores": [], "min": float("inf"), "max": 0}),
        "by_tier": defaultdict(int),
        "score_distribution": defaultdict(int),
    }

    for row in rows:
        ep_id = row.get("episode_id", "")
        score_str = row.get("episode_fame_score", "")
        tier_str = row.get("episode_fame_tier", "")

        # バッチ判定
        if ep_id.startswith("EP-00"):
            batch = "EP-00XXXX (元データ)"
        elif ep_id.startswith("EP-251130"):
            batch = "EP-251130XXX (11/30)"
        elif ep_id.startswith("EP-251201"):
            batch = "EP-251201XXX (12/1)"
        elif ep_id.startswith("EP-251205"):
            batch = "EP-251205XXX (12/5)"
        elif ep_id.startswith("EP-251206"):
            batch = "EP-251206XXX (12/6)"
        elif ep_id.startswith("EP-251207"):
            batch = "EP-251207XXX (12/7)"
        else:
            batch = "その他"

        stats["by_batch"][batch]["count"] += 1

        if score_str:
            try:
                score = float(score_str)
                stats["by_batch"][batch]["scores"].append(score)
                stats["by_batch"][batch]["min"] = min(stats["by_batch"][batch]["min"], score)
                stats["by_batch"][batch]["max"] = max(stats["by_batch"][batch]["max"], score)

                # スコア分布（10刻み）
                bucket = int(score // 10) * 10
                stats["score_distribution"][bucket] += 1
            except ValueError:
                pass

        if tier_str:
            try:
                tier = int(tier_str)
                stats["by_tier"][tier] += 1
            except ValueError:
                pass

    # 平均計算
    for batch, data in stats["by_batch"].items():
        if data["scores"]:
            data["avg"] = sum(data["scores"]) / len(data["scores"])
        else:
            data["avg"] = 0
            data["min"] = 0
            data["max"] = 0

    return stats


def recalculate_all(csv_path: Path, execute: bool = False) -> dict:
    """全エピソードのepisode_fame_scoreを再計算"""

    # CSV読み込み
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    # 現在の分布を分析
    print("=== 現在のスコア分布 ===")
    current_stats = analyze_current_distribution(rows)

    for batch, data in sorted(current_stats["by_batch"].items()):
        print(f"{batch}: {data['count']}件, 平均={data['avg']:.2f}, 範囲={data['min']:.1f}-{data['max']:.1f}")

    print("\n現在のティア分布:")
    for tier in sorted(current_stats["by_tier"].keys()):
        print(f"  Tier {tier}: {current_stats['by_tier'][tier]}件")

    # 再計算
    print("\n=== 再計算中 ===")
    updated_rows = []
    new_stats = {
        "by_tier": defaultdict(int),
        "score_distribution": defaultdict(int),
        "samples": {
            "high": [],  # score >= 8
            "mid": [],  # 5 <= score < 8
            "low": [],  # score < 5
        },
    }

    for row in rows:
        new_score, new_tier, reason = calculate_episode_fame_v3(row)

        # 更新
        row["episode_fame_score"] = str(new_score)
        row["episode_fame_tier"] = str(new_tier)
        updated_rows.append(row)

        # 統計
        new_stats["by_tier"][new_tier] += 1
        bucket = int(new_score)
        new_stats["score_distribution"][bucket] += 1

        # サンプル収集
        sample = {
            "episode_id": row.get("episode_id", ""),
            "person_name": row.get("person_name", ""),
            "episode_type": row.get("episode_type", ""),
            "score": new_score,
            "tier": new_tier,
            "reason": reason,
            "text_preview": row.get("episode_text", "")[:80],
        }

        if new_score >= 8 and len(new_stats["samples"]["high"]) < 10:
            new_stats["samples"]["high"].append(sample)
        elif 5 <= new_score < 8 and len(new_stats["samples"]["mid"]) < 10:
            new_stats["samples"]["mid"].append(sample)
        elif new_score < 5 and len(new_stats["samples"]["low"]) < 10:
            new_stats["samples"]["low"].append(sample)

    # 新しい分布表示
    print("\n=== 新しいスコア分布 ===")
    print("ティア分布:")
    for tier in sorted(new_stats["by_tier"].keys()):
        print(f"  Tier {tier}: {new_stats['by_tier'][tier]}件")

    print("\nスコア分布:")
    for score in sorted(new_stats["score_distribution"].keys()):
        count = new_stats["score_distribution"][score]
        bar = "█" * (count // 50)
        print(f"  {score}.0-{score}.9: {count:4d}件 {bar}")

    # サンプル表示
    print("\n=== 高スコアサンプル (>= 8.0) ===")
    for s in new_stats["samples"]["high"][:5]:
        print(f"  {s['episode_id']} | {s['person_name']} | {s['score']} | {s['reason']}")

    print("\n=== 中スコアサンプル (5.0-7.9) ===")
    for s in new_stats["samples"]["mid"][:5]:
        print(f"  {s['episode_id']} | {s['person_name']} | {s['score']} | {s['reason']}")

    print("\n=== 低スコアサンプル (< 5.0) ===")
    for s in new_stats["samples"]["low"][:5]:
        print(f"  {s['episode_id']} | {s['person_name']} | {s['score']} | {s['reason']}")

    if not execute:
        print("\n--execute オプションなし: ドライラン終了")
        return new_stats

    # バックアップ作成
    BACKUP_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"MASTER_before_fame_fix_{timestamp}.csv"
    shutil.copy(csv_path, backup_path)
    print(f"\nバックアップ: {backup_path}")

    # CSV書き出し
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    print(f"\n更新完了: {len(updated_rows)}件")

    # レポート出力
    OUTPUT_DIR.mkdir(exist_ok=True)
    report_path = OUTPUT_DIR / f"episode_fame_recalc_{timestamp}.json"
    import json

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "timestamp": timestamp,
                "total_updated": len(updated_rows),
                "tier_distribution": dict(new_stats["by_tier"]),
                "score_distribution": dict(new_stats["score_distribution"]),
                "samples": {
                    "high": new_stats["samples"]["high"],
                    "mid": new_stats["samples"]["mid"],
                    "low": new_stats["samples"]["low"],
                },
            },
            f,
            ensure_ascii=False,
            indent=2,
        )
    print(f"レポート: {report_path}")

    return new_stats


def main():
    import argparse

    parser = argparse.ArgumentParser(description="episode_fame_score 再計算")
    parser.add_argument("--execute", action="store_true", help="実際に更新を実行")
    args = parser.parse_args()

    print("=" * 60)
    print("episode_fame_score 再計算 (歴史的重要性ベース)")
    print("=" * 60)

    if not MASTER_CSV.exists():
        print(f"エラー: {MASTER_CSV} が見つかりません")
        sys.exit(1)

    print(f"\n入力: {MASTER_CSV}")

    recalculate_all(MASTER_CSV, execute=args.execute)


if __name__ == "__main__":
    main()
