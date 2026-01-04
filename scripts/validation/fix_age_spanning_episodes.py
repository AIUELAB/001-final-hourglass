#!/usr/bin/env python3
"""
年齢を跨ぐ寄せ集めエピソード修正スクリプト

修正対象:
- multiple_ages: 複数の年齢（10歳以上離れた）が詳述されている
- 主軸年齢以外のイベントが本文の大半を占める

修正方針:
- 主軸年齢のイベントに集中
- 他年齢の言及は「導入」「結果」程度に短縮
"""

import csv
import json
import re
import shutil
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_PATH = PROJECT_ROOT / "src" / "reports" / "age_spanning_fix_log.json"


def analyze_age_mentions(text: str, field_age: int) -> dict:
    """本文中の年齢言及を分析"""
    # 年齢パターン
    age_pattern = r"(\d+)歳"
    ages = [int(m) for m in re.findall(age_pattern, text)]

    # 主軸年齢と他年齢を分類
    other_ages = [a for a in ages if abs(a - field_age) > 5]

    return {"all_ages": ages, "other_ages": other_ages, "age_spread": max(ages) - min(ages) if ages else 0}


def extract_sentences_with_other_ages(text: str, field_age: int) -> list:
    """他年齢を含む文を抽出"""
    sentences = re.split(r"[。！？]", text)
    other_age_sentences = []

    for sentence in sentences:
        ages = [int(m) for m in re.findall(r"(\d+)歳", sentence)]
        for age in ages:
            if abs(age - field_age) > 10:  # 10歳以上離れた年齢
                other_age_sentences.append(
                    {"sentence": sentence.strip(), "other_age": age, "diff": abs(age - field_age)}
                )
                break

    return other_age_sentences


def suggest_fix(episode_id: str, person_name: str, field_age: int, text: str) -> dict | None:
    """修正提案を生成"""
    analysis = analyze_age_mentions(text, field_age)

    # 他年齢が2つ以上、かつ年齢差が20歳以上ある場合のみ修正対象
    if len(analysis["other_ages"]) < 1 or analysis["age_spread"] < 15:
        return None

    other_sentences = extract_sentences_with_other_ages(text, field_age)

    if not other_sentences:
        return None

    # 修正テキストの作成
    new_text = text
    removed_parts = []

    for item in other_sentences:
        sentence = item["sentence"]
        # 文が「〜年、」「〜歳のとき」で始まる長い記述を短縮
        if len(sentence) > 50 and (str(item["other_age"]) + "歳") in sentence:
            # 詳細な記述を短縮
            short = f"（後に{item['other_age']}歳で評価される）"
            if sentence in new_text:
                # 完全削除ではなく、短縮版に置換（または削除）
                new_text = new_text.replace(sentence + "。", "")
                removed_parts.append(sentence)

    if not removed_parts:
        return None

    return {
        "episode_id": episode_id,
        "person_name": person_name,
        "field_age": field_age,
        "original_length": len(text),
        "new_length": len(new_text),
        "removed_sentences": removed_parts,
        "analysis": analysis,
        "new_text": new_text.strip(),
    }


def main():
    """メイン処理"""
    print("=" * 60)
    print("年齢を跨ぐエピソード修正")
    print("=" * 60)

    # 既知の問題エピソードリスト（High判定のもの）
    target_episodes = [
        "EP-000002123",  # 益川敏英 65歳
        "EP-000001659",  # 森光子 47歳
        "EP-000001620",  # 益川敏英 68歳
        "EP-000001685",  # 鈴木大地 55歳
        "EP-000001562",  # 黒澤明 60歳
    ]

    # CSV読み込み
    with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    print(f"総エピソード数: {len(rows)}")

    # 修正候補を収集
    fixes = []
    for row in rows:
        episode_id = row.get("episode_id", "")

        # ターゲットリストにあるか、または独自分析
        if episode_id not in target_episodes:
            continue

        text = row.get("episode_text", "")
        age_str = row.get("age", "")
        person_name = row.get("person_name", "")

        try:
            field_age = int(float(age_str))
        except (ValueError, TypeError):
            continue

        fix = suggest_fix(episode_id, person_name, field_age, text)
        if fix:
            fixes.append(fix)

    print(f"\n修正候補: {len(fixes)}件")

    # 詳細表示
    for fix in fixes:
        print(f"\n{fix['episode_id']} ({fix['person_name']} {fix['field_age']}歳)")
        print(f"  年齢分析: {fix['analysis']}")
        print(f"  削除対象: {len(fix['removed_sentences'])}文")
        for s in fix["removed_sentences"][:2]:
            print(f"    - {s[:60]}...")

    # レポート保存
    report = {
        "timestamp": datetime.now().isoformat(),
        "target_count": len(target_episodes),
        "fix_count": len(fixes),
        "fixes": fixes,
    }

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\nレポート保存: {REPORT_PATH}")

    return fixes


if __name__ == "__main__":
    main()
