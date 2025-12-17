#!/usr/bin/env python3
"""
PERSON成長パイプライン（MVP版）

目的:
  エピソードDBに未収録のPERSONを継続的に追加する運用システム

MVP版機能範囲:
  1. 候補収集（config/person_sources/*.csvから）
  2. 正規化/検証（PersonNameValidator, normalize_name）
  3. 未収録判定（既存DBとの重複検出）
  4. レポート生成（JSON形式）

使用方法:
    # 分析のみ（ドライラン）
    python scripts/person_growth_pipeline.py --analyze

    # 特定ソースのみ処理
    python scripts/person_growth_pipeline.py --analyze --sources manual_list

    # 件数制限
    python scripts/person_growth_pipeline.py --analyze --limit 10

詳細:
    docs/PERSON_GROWTH_DESIGN.md
"""

import argparse
import json
import re
import sys
import unicodedata
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.csv_path_resolver import (
    get_config_dir,
    get_master_csv_path,
    get_person_sources_dir,
    get_project_root,
    get_reports_dir,
)
from src.validators.person_name_validator import PersonNameValidator

# ========================================
# 定数（統一パス解決を使用）
# ========================================

MASTER_CSV = get_master_csv_path()
SOURCES_DIR = get_person_sources_dir()
REPORTS_DIR = get_reports_dir() / "person_growth"
CATEGORY_TAXONOMY = get_config_dir() / "category_taxonomy.json"

# 重複判定閾値
SIMILARITY_THRESHOLD = 0.85

# ========================================
# 正規化関数（merge_duplicate_persons.pyから再利用）
# ========================================


def normalize_name(name: str) -> str:
    """
    人物名を正規化

    処理:
    - NFKC正規化（全角→半角、etc）
    - 小文字化
    - 中点・スペース統一
    - 前後空白削除

    Args:
        name: 元の名前

    Returns:
        正規化された名前
    """
    if not name or pd.isna(name):
        return ""

    name = str(name)

    # NFKC正規化
    name = unicodedata.normalize("NFKC", name)

    # 小文字化
    name = name.lower()

    # 中点類の統一（・、·、・、‧ → ・）
    name = re.sub(r"[・·‧]", "・", name)

    # スペース統一
    name = re.sub(r"\s+", " ", name)

    # 前後空白削除
    name = name.strip()

    return name


def remove_honorifics(name: str) -> str:
    """
    敬称・接尾辞を除去

    Args:
        name: 名前

    Returns:
        敬称除去後の名前
    """
    # 日本語敬称
    honorifics = ["さん", "くん", "君", "ちゃん", "様", "氏", "先生", "博士"]
    for h in honorifics:
        if name.endswith(h):
            name = name[: -len(h)]

    return name.strip()


def calculate_similarity(name1: str, name2: str) -> float:
    """
    2つの名前の類似度を計算

    Args:
        name1: 名前1
        name2: 名前2

    Returns:
        類似度（0.0-1.0）
    """
    return SequenceMatcher(None, name1, name2).ratio()


def are_similar_names(name1: str, name2: str, threshold: float = SIMILARITY_THRESHOLD) -> bool:
    """
    2つの名前が類似しているか判定

    Args:
        name1: 名前1
        name2: 名前2
        threshold: 類似度閾値

    Returns:
        類似していればTrue
    """
    # 正規化
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)

    # 完全一致
    if n1 == n2:
        return True

    # 類似度計算
    return calculate_similarity(n1, n2) >= threshold


# ========================================
# カテゴリマッピング
# ========================================


def load_category_taxonomy() -> Dict[str, str]:
    """
    カテゴリ分類体系を読み込み

    Returns:
        sub_category → category のマッピング
    """
    if not CATEGORY_TAXONOMY.exists():
        print(f"⚠️  カテゴリ分類ファイルが見つかりません: {CATEGORY_TAXONOMY}")
        return {}

    with open(CATEGORY_TAXONOMY, "r", encoding="utf-8") as f:
        taxonomy = json.load(f)

    return taxonomy.get("mappings", {})


# ========================================
# 候補収集
# ========================================


def load_candidates(sources_filter: Optional[List[str]] = None, limit: Optional[int] = None) -> pd.DataFrame:
    """
    config/person_sources/*.csvから候補人物を収集

    Args:
        sources_filter: 処理対象ソース名のリスト（None=全て）
        limit: 最大収集件数（None=無制限）

    Returns:
        候補人物のDataFrame

    必須列:
        - person_name: 人物名
        - category: カテゴリ
        - person_type: REAL/FICTIONAL
    """
    if not SOURCES_DIR.exists():
        print(f"❌ ソースディレクトリが存在しません: {SOURCES_DIR}")
        sys.exit(1)

    csv_files = list(SOURCES_DIR.glob("*.csv"))
    if not csv_files:
        print(f"⚠️  ソースCSVが見つかりません: {SOURCES_DIR}")
        return pd.DataFrame()

    # ソースフィルタ適用
    if sources_filter:
        csv_files = [f for f in csv_files if f.stem in sources_filter]
        if not csv_files:
            print(f"⚠️  指定されたソースが見つかりません: {sources_filter}")
            return pd.DataFrame()

    # 全CSVを読み込み
    dfs = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, encoding="utf-8-sig")
            df["source_file"] = csv_file.stem
            dfs.append(df)
            print(f"✅ 読み込み: {csv_file.name} ({len(df)}件)")
        except Exception as e:
            print(f"⚠️  読み込みエラー: {csv_file.name} - {e}")

    if not dfs:
        print("❌ 有効なソースCSVがありませんでした")
        return pd.DataFrame()

    # 統合
    candidates = pd.concat(dfs, ignore_index=True)

    # 必須列チェック
    required_cols = ["person_name", "category", "person_type"]
    missing_cols = [col for col in required_cols if col not in candidates.columns]
    if missing_cols:
        print(f"❌ 必須列が不足しています: {missing_cols}")
        sys.exit(1)

    # 件数制限
    if limit and len(candidates) > limit:
        candidates = candidates.head(limit)
        print(f"⚠️  件数制限により {limit} 件に絞り込みました")

    return candidates


# ========================================
# 正規化/検証
# ========================================


def normalize_and_validate(candidates: pd.DataFrame) -> Tuple[pd.DataFrame, List[Dict]]:
    """
    候補人物の正規化と検証

    Args:
        candidates: 候補人物のDataFrame

    Returns:
        (正規化済みDataFrame, 検証エラーリスト)
    """
    validator = PersonNameValidator()
    errors = []

    # 正規化
    candidates["person_name_normalized"] = candidates["person_name"].apply(
        lambda x: remove_honorifics(normalize_name(x))
    )

    # 検証
    for idx, row in candidates.iterrows():
        person_name = row["person_name"]

        # PersonNameValidator（person_typeは不要）
        issues = validator.validate(person_name)
        if issues:
            for issue in issues:
                errors.append(
                    {
                        "person_name": person_name,
                        "source_file": row.get("source_file", "unknown"),
                        "severity": issue.severity.value,
                        "message": issue.message,
                        "issue_type": issue.issue_type.value,
                    }
                )

    return candidates, errors


# ========================================
# 未収録判定
# ========================================


def find_missing_persons(candidates: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    既存DBとの照合により未収録人物を特定

    Args:
        candidates: 候補人物のDataFrame

    Returns:
        (未収録人物のDataFrame, 既収録人物のDataFrame)
    """
    if not MASTER_CSV.exists():
        print(f"⚠️  マスターCSVが見つかりません: {MASTER_CSV}")
        return candidates, pd.DataFrame()

    # 既存DB読み込み
    master_df = pd.read_csv(MASTER_CSV, encoding="utf-8-sig")
    existing_names = master_df["person_name"].dropna().unique()
    existing_names_normalized = {normalize_name(name) for name in existing_names}

    print(f"📊 既存DB: {len(existing_names)} 人収録")

    # 重複判定
    missing = []
    found = []

    for idx, row in candidates.iterrows():
        candidate_name = row["person_name"]
        candidate_normalized = normalize_name(candidate_name)

        # 1. 完全一致チェック
        if candidate_name in existing_names:
            found.append({**row.to_dict(), "match_type": "exact", "match_confidence": 1.0})
            continue

        # 2. 正規化一致チェック
        if candidate_normalized in existing_names_normalized:
            found.append({**row.to_dict(), "match_type": "normalized", "match_confidence": 0.95})
            continue

        # 3. 類似度チェック（コストが高いので最後）
        is_similar = False
        best_match = None
        best_score = 0.0

        for existing_name in existing_names:
            if are_similar_names(candidate_name, existing_name, threshold=SIMILARITY_THRESHOLD):
                is_similar = True
                score = calculate_similarity(candidate_normalized, normalize_name(existing_name))
                if score > best_score:
                    best_score = score
                    best_match = existing_name

        if is_similar:
            found.append(
                {
                    **row.to_dict(),
                    "match_type": "similar",
                    "match_confidence": best_score,
                    "matched_to": best_match,
                }
            )
        else:
            missing.append(row.to_dict())

    missing_df = pd.DataFrame(missing) if missing else pd.DataFrame()
    found_df = pd.DataFrame(found) if found else pd.DataFrame()

    return missing_df, found_df


# ========================================
# レポート生成
# ========================================


def generate_report(
    candidates: pd.DataFrame,
    validation_errors: List[Dict],
    missing: pd.DataFrame,
    found: pd.DataFrame,
    output_path: Optional[Path] = None,
) -> Dict:
    """
    分析結果のレポート生成

    Args:
        candidates: 候補人物
        validation_errors: 検証エラーリスト
        missing: 未収録人物
        found: 既収録人物
        output_path: レポート出力先（None=自動生成）

    Returns:
        レポート辞書
    """
    # レポート作成
    report = {
        "timestamp": datetime.now().isoformat(),
        "summary": {
            "total_candidates": len(candidates),
            "validation_errors": len(validation_errors),
            "missing_persons": len(missing),
            "found_persons": len(found),
            "missing_percentage": (round(len(missing) / len(candidates) * 100, 2) if len(candidates) > 0 else 0.0),
        },
        "missing_persons": (
            missing[["person_name", "category", "person_type", "source_file"]].to_dict("records")
            if not missing.empty
            else []
        ),
        "found_persons": (
            found[["person_name", "category", "match_type", "match_confidence"]].to_dict("records")
            if not found.empty
            else []
        ),
        "validation_errors": validation_errors,
        "category_breakdown": (missing["category"].value_counts().to_dict() if not missing.empty else {}),
    }

    # ファイル出力
    if output_path is None:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = REPORTS_DIR / f"person_growth_analysis_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 レポート出力: {output_path}")

    return report


# ========================================
# CLI
# ========================================


def print_summary(report: Dict):
    """サマリーを標準出力"""
    summary = report["summary"]

    print("\n" + "=" * 60)
    print("📊 PERSON成長パイプライン分析結果（MVP版）")
    print("=" * 60)
    print(f"📌 候補人物数: {summary['total_candidates']} 人")
    print(f"✅ 既収録: {summary['found_persons']} 人")
    print(f"🆕 未収録: {summary['missing_persons']} 人 ({summary['missing_percentage']}%)")
    print(f"⚠️  検証エラー: {summary['validation_errors']} 件")

    # カテゴリ内訳
    if report["category_breakdown"]:
        print("\n📂 未収録人物のカテゴリ内訳:")
        for category, count in sorted(report["category_breakdown"].items(), key=lambda x: x[1], reverse=True):
            print(f"  - {category}: {count}人")

    # 検証エラー詳細
    if report["validation_errors"]:
        print("\n⚠️  検証エラー詳細（上位10件）:")
        for error in report["validation_errors"][:10]:
            print(f"  - {error['person_name']}: {error['message']}")

    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="PERSON成長パイプライン（MVP版）",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        help="分析モード（候補収集→検証→未収録判定→レポート）",
    )

    parser.add_argument(
        "--sources",
        type=str,
        help="処理対象ソース名（カンマ区切り、例: manual_list,nhk_asadora）",
    )

    parser.add_argument(
        "--limit",
        type=int,
        help="候補収集の最大件数",
    )

    parser.add_argument(
        "--output",
        type=Path,
        help="レポート出力先（デフォルト: reports/person_growth/person_growth_analysis_YYYYMMDD_HHMMSS.json）",
    )

    args = parser.parse_args()

    # --analyzeが未指定の場合はヘルプ表示
    if not args.analyze:
        parser.print_help()
        print("\n💡 まずは --analyze で分析を実行してください")
        sys.exit(0)

    print("🚀 PERSON成長パイプライン（MVP版）開始")
    print(f"📂 ソースディレクトリ: {SOURCES_DIR}")
    print(f"📄 マスターCSV: {MASTER_CSV}")

    # ソースフィルタ
    sources_filter = args.sources.split(",") if args.sources else None

    # 1. 候補収集
    print("\n【ステップ1】候補収集")
    candidates = load_candidates(sources_filter=sources_filter, limit=args.limit)
    if candidates.empty:
        print("❌ 候補人物が見つかりませんでした")
        sys.exit(1)

    # 2. 正規化/検証
    print("\n【ステップ2】正規化/検証")
    candidates, validation_errors = normalize_and_validate(candidates)
    print(f"✅ 正規化完了: {len(candidates)} 人")
    print(f"⚠️  検証エラー: {len(validation_errors)} 件")

    # 3. 未収録判定
    print("\n【ステップ3】未収録判定")
    missing, found = find_missing_persons(candidates)
    print(f"🆕 未収録: {len(missing)} 人")
    print(f"✅ 既収録: {len(found)} 人")

    # 4. レポート生成
    print("\n【ステップ4】レポート生成")
    report = generate_report(
        candidates=candidates,
        validation_errors=validation_errors,
        missing=missing,
        found=found,
        output_path=args.output,
    )

    # サマリー表示
    print_summary(report)

    print("\n✅ 分析完了")


if __name__ == "__main__":
    main()
