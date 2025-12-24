#!/usr/bin/env python3
"""
新規PERSON登録時の類似チェック（品質ゲート）。

使用方法:
    # 単一人物チェック
    python scripts/validate_new_person.py --name "スティーブ・ジョブズ"

    # CSVからバッチチェック
    python scripts/validate_new_person.py --csv new_persons.csv
"""

import argparse
import hashlib
import unicodedata
from pathlib import Path

import pandas as pd

# パス設定
MASTER_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

# 旧字体→新字体マッピング（主要なもの）
OLD_TO_NEW_KANJI = {
    "關": "関",
    "澤": "沢",
    "邊": "辺",
    "齋": "斎",
    "齊": "斉",
    "櫻": "桜",
    "國": "国",
    "學": "学",
    "會": "会",
    "黑": "黒",
    "眞": "真",
    "廣": "広",
    "惠": "恵",
    "彌": "弥",
    "壽": "寿",
    "譽": "誉",
    "盜": "盗",
    "默": "黙",
    "髙": "高",
    "﨑": "崎",
    "瀨": "瀬",
    "祿": "禄",
    "禮": "礼",
    "靈": "霊",
    "龍": "竜",
    "彅": "剪",  # 草彅剛対応
}


def normalize_name(name: str) -> str:
    """名前を正規化"""
    # Unicode正規化
    name = unicodedata.normalize("NFKC", name)

    # 旧字体→新字体
    for old, new in OLD_TO_NEW_KANJI.items():
        name = name.replace(old, new)

    # 記号統一
    name = name.replace("・", "")
    name = name.replace("＝", "")
    name = name.replace("．", "")
    name = name.replace(" ", "")
    name = name.replace("　", "")

    # 小文字統一
    name = name.lower()

    return name


def generate_person_id(name: str) -> str:
    """person_nameからperson_idを生成"""
    hash_obj = hashlib.md5(name.encode("utf-8"), usedforsecurity=False)
    return "P" + hash_obj.hexdigest()[:7].upper()


def find_similar_persons(name: str, df: pd.DataFrame, threshold: float = 0.7) -> list[dict]:
    """類似する既存人物を検索"""
    normalized_input = normalize_name(name)
    results = []

    # 既存人物を取得
    persons = df.groupby("person_id")["person_name"].first().to_dict()

    for pid, existing_name in persons.items():
        normalized_existing = normalize_name(existing_name)

        # 完全一致（正規化後）
        if normalized_input == normalized_existing:
            results.append(
                {
                    "person_id": pid,
                    "person_name": existing_name,
                    "match_type": "exact_normalized",
                    "similarity": 1.0,
                }
            )
            continue

        # 部分一致
        if normalized_input in normalized_existing or normalized_existing in normalized_input:
            # 長さの比率で類似度を計算
            len_ratio = min(len(normalized_input), len(normalized_existing)) / max(
                len(normalized_input), len(normalized_existing)
            )
            if len_ratio >= threshold:
                results.append(
                    {
                        "person_id": pid,
                        "person_name": existing_name,
                        "match_type": "substring",
                        "similarity": len_ratio,
                    }
                )

    return sorted(results, key=lambda x: x["similarity"], reverse=True)


def validate_person(name: str, df: pd.DataFrame) -> dict:
    """人物名を検証"""
    result = {
        "input_name": name,
        "generated_id": generate_person_id(name),
        "normalized_name": normalize_name(name),
        "status": "OK",
        "similar_persons": [],
        "recommendation": None,
    }

    # 完全一致チェック（生成IDが既存）
    if result["generated_id"] in df["person_id"].values:
        existing_name = df[df["person_id"] == result["generated_id"]]["person_name"].iloc[0]
        result["status"] = "EXISTS"
        result["recommendation"] = f"既存ID使用: {result['generated_id']} ({existing_name})"
        return result

    # 類似チェック
    similar = find_similar_persons(name, df)
    if similar:
        result["similar_persons"] = similar[:5]
        if similar[0]["match_type"] == "exact_normalized":
            result["status"] = "DUPLICATE_CANDIDATE"
            result["recommendation"] = f"既存IDへ統合を推奨: {similar[0]['person_id']} ({similar[0]['person_name']})"
        elif similar[0]["similarity"] >= 0.8:
            result["status"] = "WARNING"
            result["recommendation"] = (
                f"類似人物あり（要確認）: {similar[0]['person_id']} ({similar[0]['person_name']})"
            )

    return result


def main():
    parser = argparse.ArgumentParser(description="新規PERSON登録時の類似チェック")
    parser.add_argument("--name", type=str, help="チェックする人物名")
    parser.add_argument("--csv", type=str, help="チェックするCSVファイル")

    args = parser.parse_args()

    if not args.name and not args.csv:
        parser.print_help()
        return

    # マスターCSV読み込み
    df = pd.read_csv(MASTER_CSV, low_memory=False)
    print(f"マスターCSV: {df['person_id'].nunique()} 人物")
    print()

    if args.name:
        result = validate_person(args.name, df)
        print(f"入力名: {result['input_name']}")
        print(f"正規化: {result['normalized_name']}")
        print(f"生成ID: {result['generated_id']}")
        print(f"ステータス: {result['status']}")

        if result["recommendation"]:
            print(f"推奨: {result['recommendation']}")

        if result["similar_persons"]:
            print("\n類似人物:")
            for p in result["similar_persons"]:
                print(f"  - {p['person_name']} ({p['person_id']}) [{p['match_type']}: {p['similarity']:.2f}]")

    elif args.csv:
        input_df = pd.read_csv(args.csv)
        print(f"入力CSV: {len(input_df)} 件")

        results = []
        for _, row in input_df.iterrows():
            name = row.get("person_name") or row.get("name")
            if name:
                result = validate_person(name, df)
                results.append(result)

        # 結果サマリー
        ok_count = sum(1 for r in results if r["status"] == "OK")
        dup_count = sum(1 for r in results if r["status"] == "DUPLICATE_CANDIDATE")
        warn_count = sum(1 for r in results if r["status"] == "WARNING")

        print("\n=== 結果サマリー ===")
        print(f"OK: {ok_count}")
        print(f"重複候補: {dup_count}")
        print(f"警告: {warn_count}")

        if dup_count > 0 or warn_count > 0:
            print("\n=== 要確認 ===")
            for r in results:
                if r["status"] in ("DUPLICATE_CANDIDATE", "WARNING"):
                    print(f"  {r['input_name']}: {r['recommendation']}")


if __name__ == "__main__":
    main()
