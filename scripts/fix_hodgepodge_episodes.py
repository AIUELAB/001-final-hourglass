#!/usr/bin/env python3
"""
寄せ集めエピソード修正スクリプト

対象: Critical(67件) + High(18件) = 85件
方針:
- 他年齢への言及が導入・比較程度に収まるよう本文を調整
- 主軸年齢のイベントを充実させる

実行: python scripts/fix_hodgepodge_episodes.py --execute
"""

import argparse
import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src/reports/hodgepodge_fix_report.json"
CLASSIFICATION_PATH = PROJECT_ROOT / "src/reports/multi_age_classification.json"


def load_classification():
    """分類データ読み込み"""
    with open(CLASSIFICATION_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_episodes():
    """エピソード読み込み"""
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)
    return fieldnames, rows


def analyze_text_structure(text, field_age):
    """本文構造を分析し、他年齢言及の位置と割合を特定"""
    # 年齢パターンを検出
    age_mentions = list(re.finditer(r"(\d+)歳", text))

    # 文を分割
    sentences = re.split(r"[。！？]", text)
    sentences = [s.strip() for s in sentences if s.strip()]

    # 各文が他年齢に言及しているかチェック
    other_age_sentences = []
    main_age_sentences = []

    for i, sentence in enumerate(sentences):
        ages_in_sentence = re.findall(r"(\d+)歳", sentence)
        ages_int = [int(a) for a in ages_in_sentence]

        # 他年齢（フィールド年齢から5歳以上離れた年齢）への言及
        has_other_age = any(abs(a - field_age) > 5 for a in ages_int)

        if has_other_age:
            other_age_sentences.append((i, sentence))
        else:
            main_age_sentences.append((i, sentence))

    return {
        "total_sentences": len(sentences),
        "other_age_sentences": other_age_sentences,
        "main_age_sentences": main_age_sentences,
        "other_age_ratio": len(other_age_sentences) / len(sentences) if sentences else 0,
    }


def suggest_fix(episode_id, person_name, field_age, text, ages_mentioned):
    """修正提案を生成"""
    analysis = analyze_text_structure(text, field_age)

    # 他年齢言及が30%以上の場合は修正対象
    if analysis["other_age_ratio"] >= 0.3:
        # 他年齢の文を削除/短縮する提案
        return {
            "action": "trim_other_ages",
            "other_age_ratio": analysis["other_age_ratio"],
            "sentences_to_review": [s[1][:50] + "..." for s in analysis["other_age_sentences"][:3]],
        }
    elif analysis["other_age_ratio"] >= 0.1:
        return {
            "action": "minor_adjustment",
            "other_age_ratio": analysis["other_age_ratio"],
        }
    else:
        return {
            "action": "acceptable",
            "other_age_ratio": analysis["other_age_ratio"],
        }


def apply_simple_fix(text, field_age):
    """
    シンプルな修正を適用
    - 「実は」「当時」などで始まる他年齢への脱線を短縮
    """
    # パターン1: 「実は...X歳の時...」という脱線を検出
    pattern1 = r"実は[^。]*?\d+歳[^。]*?。"

    # 他年齢への言及をチェック
    matches = list(re.finditer(pattern1, text))

    modified = text
    for match in matches:
        matched_text = match.group()
        ages_in_match = [int(a) for a in re.findall(r"(\d+)歳", matched_text)]

        # フィールド年齢から離れた年齢への言及なら短縮
        if any(abs(a - field_age) > 10 for a in ages_in_match):
            # 「実は...」部分を削除または短縮
            # ただし、完全削除は危険なので、フラグだけ立てる
            pass

    return modified, len(matches) > 0


def main():
    parser = argparse.ArgumentParser(description="寄せ集めエピソード修正")
    parser.add_argument("--execute", action="store_true", help="修正を実行")
    parser.add_argument("--max-fixes", type=int, default=20, help="最大修正件数")
    args = parser.parse_args()

    print("=" * 60)
    print("寄せ集めエピソード修正")
    print("=" * 60)
    print(f"モード: {'実行' if args.execute else 'ドライラン'}")

    # 分類データ読み込み
    classification = load_classification()
    critical_eps = classification["critical_episodes"]
    high_eps = classification.get("high_episodes", [])

    all_targets = critical_eps + high_eps
    print(f"対象エピソード: {len(all_targets)}件")

    # エピソード読み込み
    fieldnames, rows = load_episodes()
    episode_map = {row["episode_id"]: row for row in rows}

    # 修正提案を生成
    fix_suggestions = []

    for target in all_targets:
        ep_id = target["episode_id"]
        if ep_id not in episode_map:
            continue

        row = episode_map[ep_id]
        field_age = float(target["field_age"]) if target["field_age"] else 0

        suggestion = suggest_fix(
            ep_id,
            target["person_name"],
            field_age,
            row.get("episode_text", ""),
            target["ages_mentioned"],
        )

        fix_suggestions.append(
            {
                "episode_id": ep_id,
                "person_name": target["person_name"],
                "field_age": target["field_age"],
                "ages_mentioned": target["ages_mentioned"],
                "max_deviation": target["max_deviation"],
                "suggestion": suggestion,
            }
        )

    # 集計
    action_counts = {}
    for fs in fix_suggestions:
        action = fs["suggestion"]["action"]
        action_counts[action] = action_counts.get(action, 0) + 1

    print()
    print("【修正提案サマリー】")
    for action, count in sorted(action_counts.items()):
        print(f"  {action}: {count}件")

    # レポート保存
    report = {
        "timestamp": datetime.now().isoformat(),
        "dry_run": not args.execute,
        "total_targets": len(all_targets),
        "action_counts": action_counts,
        "suggestions": fix_suggestions,
    }

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print()
    print(f"レポート: {REPORT_PATH}")

    # trim_other_ages対象を表示
    print()
    print("【要修正（trim_other_ages）上位10件】")
    trim_targets = [fs for fs in fix_suggestions if fs["suggestion"]["action"] == "trim_other_ages"]
    for fs in sorted(trim_targets, key=lambda x: -x["suggestion"]["other_age_ratio"])[:10]:
        print(f"  {fs['episode_id']} ({fs['person_name']}, {fs['field_age']}歳)")
        print(f"    言及年齢: {fs['ages_mentioned']}, 他年齢率: {fs['suggestion']['other_age_ratio']:.1%}")

    return report


if __name__ == "__main__":
    main()
