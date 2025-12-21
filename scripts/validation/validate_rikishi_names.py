#!/usr/bin/env python3
"""
力士名バリデーションスクリプト（四股名検証）

目的:
- 全力士の四股名 vs 本名混入を自動検証

使用方法:
    # 基本検証
    python scripts/validate_rikishi_names.py

    # レポート出力先を指定
    python scripts/validate_rikishi_names.py --output reports/rikishi_validation.json
"""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.data.normalize_person_names import RIKISHI_SHIKONA

CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORTS_DIR = PROJECT_ROOT / "reports"


def extract_rikishi_candidates(df: pd.DataFrame) -> pd.DataFrame:
    """
    力士候補を抽出

    Args:
        df: マスターCSVのDataFrame

    Returns:
        力士候補のDataFrame
    """
    # 力士関連キーワード
    rikishi_keywords = ["力士", "相撲", "大相撲", "sumo", "横綱", "大関", "関脇", "小結", "前頭"]

    # カテゴリ＋エピソード本文で検索
    rikishi_rows = df[
        df["category"].str.contains("スポーツ", na=False)
        & (df["episode_text"].str.contains("|".join(rikishi_keywords), case=False, na=False))
    ]

    # person_id/person_name でグループ化
    rikishi_candidates = rikishi_rows.groupby(["person_id", "person_name"]).size().reset_index(name="episode_count")

    return rikishi_candidates


def validate_rikishi_name(person_id: str, person_name: str) -> dict:
    """
    力士名をバリデーション

    Args:
        person_id: 人物ID
        person_name: 人物名

    Returns:
        バリデーション結果の辞書
    """
    # パターン1: RIKISHI_SHIKONAリスト完全一致
    if person_name in RIKISHI_SHIKONA:
        return {
            "person_id": person_id,
            "person_name": person_name,
            "status": "OK",
            "pattern": "EXACT_MATCH",
            "confidence": 1.0,
            "notes": "RIKISHI_SHIKONAリストに登録済み",
        }

    # パターン2: RIKISHI_SHIKONA部分一致（本名混入の疑い）
    for shikona in RIKISHI_SHIKONA:
        if person_name.startswith(shikona) and len(person_name) > len(shikona):
            suffix = person_name[len(shikona) :]
            # 末尾1-2文字の漢字
            if 1 <= len(suffix) <= 2 and all("\u4e00" <= char <= "\u9fff" for char in suffix):
                return {
                    "person_id": person_id,
                    "person_name": person_name,
                    "status": "NEEDS_FIX",
                    "suggested_name": shikona,
                    "pattern": "RIKISHI_SHIKONA_MATCH",
                    "confidence": 0.95,
                    "notes": f"四股名「{shikona}」から本名の名「{suffix}」を除去",
                }

    # パターン3: 汎用パターン（「の」+末尾1-2文字の漢字）
    if "の" in person_name:
        parts = person_name.split("の")
        if len(parts) >= 2:
            last_part = parts[-1]
            if len(last_part) >= 3:
                # 末尾1文字が漢字
                if "\u4e00" <= last_part[-1] <= "\u9fff":
                    shikona_candidate = person_name[:-1]
                    return {
                        "person_id": person_id,
                        "person_name": person_name,
                        "status": "REVIEW_REQUIRED",
                        "suggested_name": shikona_candidate,
                        "pattern": "RIKISHI_SHIKONA_GENERIC",
                        "confidence": 0.80,
                        "notes": f"「の」を含む力士名から末尾「{person_name[-1]}」を除去（要レビュー）",
                    }

    # 力士ではない、または問題なし
    return {
        "person_id": person_id,
        "person_name": person_name,
        "status": "OK",
        "pattern": "OTHER",
        "confidence": 0.5,
        "notes": "力士ではない可能性が高い、または問題なし",
    }


def main():
    parser = argparse.ArgumentParser(description="力士名バリデーションスクリプト（四股名検証）")
    parser.add_argument("--output", type=str, help="レポート出力先のパス")
    args = parser.parse_args()

    print("=" * 70)
    print("🔍 力士名バリデーション")
    print("=" * 70)

    # CSVを読み込み
    try:
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
        print(f"✅ CSV読み込み完了: {len(df)}レコード")
    except Exception as e:
        print(f"❌ CSV読み込みエラー: {e}")
        return 1

    # 力士候補を抽出
    rikishi_candidates = extract_rikishi_candidates(df)
    print(f"📊 力士候補: {len(rikishi_candidates)}名")

    # バリデーション実行
    results = []
    needs_fix_count = 0
    review_required_count = 0
    ok_count = 0

    print("\n" + "=" * 70)
    print("🔍 バリデーション結果")
    print("=" * 70)

    for _, row in rikishi_candidates.iterrows():
        person_id = row["person_id"]
        person_name = row["person_name"]

        result = validate_rikishi_name(person_id, person_name)
        result["episode_count"] = int(row["episode_count"])
        results.append(result)

        # 統計
        if result["status"] == "NEEDS_FIX":
            needs_fix_count += 1
            print(f"❌ {person_id}: {person_name} → {result['suggested_name']} (confidence={result['confidence']})")
        elif result["status"] == "REVIEW_REQUIRED":
            review_required_count += 1
            print(f"⚠️  {person_id}: {person_name} → {result['suggested_name']} (要レビュー)")
        else:
            ok_count += 1
            print(f"✅ {person_id}: {person_name}")

    # レポート作成
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_rikishi": len(rikishi_candidates),
        "needs_fix": needs_fix_count,
        "review_required": review_required_count,
        "ok": ok_count,
        "results": results,
    }

    # レポート保存
    if args.output:
        report_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = REPORTS_DIR / f"rikishi_validation_{timestamp}.json"

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"\n📄 レポート保存: {report_path}")

    print("\n" + "=" * 70)
    print("📊 サマリー")
    print("=" * 70)
    print(f"  力士候補: {len(rikishi_candidates)}名")
    print(f"  修正必要: {needs_fix_count}件")
    print(f"  要レビュー: {review_required_count}件")
    print(f"  問題なし: {ok_count}件")
    print("=" * 70)

    # 終了コード
    if needs_fix_count > 0:
        print("\n⚠️  修正が必要な力士名が検出されました")
        return 1
    elif review_required_count > 0:
        print("\n⚠️  レビューが必要な力士名が検出されました")
        return 0
    else:
        print("\n✅ すべての力士名が正しい形式です")
        return 0


if __name__ == "__main__":
    exit(main())
