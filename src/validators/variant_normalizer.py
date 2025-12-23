#!/usr/bin/env python3
"""
異体字正規化モジュール

CJK互換漢字（異体字）を統一漢字に正規化し、
同一人物の重複PERSON ID発生を防止する。

使用例:
    from src.validators.variant_normalizer import normalize_person_name, detect_variant_duplicates

    # 正規化
    normalized = normalize_person_name("宮﨑駿")  # → "宮崎駿"

    # 重複検出
    duplicates = detect_variant_duplicates(df)
"""

import unicodedata
from typing import Dict, List, Optional, Set, Tuple

import pandas as pd

# CJK互換漢字 → 統一漢字のマッピング
# https://unicode.org/charts/PDF/UF900.pdf
VARIANT_CHAR_MAP: Dict[str, str] = {
    # 崎の異体字
    "\ufa11": "\u5d0e",  # 﨑 (U+FA11) → 崎 (U+5D0E)
    # 塚の異体字
    "\ufa10": "\u585a",  # 塚 (U+FA10) → 塚 (U+585A)
    # 晴の異体字
    "\ufa12": "\u6674",  # 晴 (U+FA12) → 晴 (U+6674)
    # 神の異体字
    "\ufa19": "\u795e",  # 神 (U+FA19) → 神 (U+795E)
    # 福の異体字
    "\ufa1a": "\u798f",  # 福 (U+FA1A) → 福 (U+798F)
    # 靖の異体字
    "\ufa1b": "\u9756",  # 靖 (U+FA1B) → 靖 (U+9756)
    # 精の異体字
    "\ufa1d": "\u7cbe",  # 精 (U+FA1D) → 精 (U+7CBE)
    # 羽の異体字
    "\ufa1e": "\u7fbd",  # 羽 (U+FA1E) → 羽 (U+7FBD)
    # 諸の異体字
    "\ufa22": "\u8af8",  # 諸 (U+FA22) → 諸 (U+8AF8)
    # 都の異体字
    "\ufa26": "\u90fd",  # 都 (U+FA26) → 都 (U+90FD)
    # 飯の異体字
    "\ufa2a": "\u98ef",  # 飯 (U+FA2A) → 飯 (U+98EF)
    # 館の異体字
    "\ufa2b": "\u9928",  # 館 (U+FA2B) → 館 (U+9928)
    # 鶴の異体字
    "\ufa2c": "\u9db4",  # 鶴 (U+FA2C) → 鶴 (U+9DB4)
    # 郎の異体字
    "\ufa2e": "\u90ce",  # 郎 (U+FA2E) → 郎 (U+90CE)
    # 隆の異体字
    "\ufa2f": "\u9686",  # 隆 (U+FA2F) → 隆 (U+9686)
}

# 逆マッピング（正規形 → 異体字セット）
CANONICAL_TO_VARIANTS: Dict[str, Set[str]] = {}
for variant, canonical in VARIANT_CHAR_MAP.items():
    if canonical not in CANONICAL_TO_VARIANTS:
        CANONICAL_TO_VARIANTS[canonical] = set()
    CANONICAL_TO_VARIANTS[canonical].add(variant)


def normalize_person_name(name: str) -> str:
    """
    人物名を正規化する

    処理:
    1. NFC正規化（合成形式への統一）
    2. CJK互換漢字の統一漢字への変換
    3. 全角空白の半角化

    Args:
        name: 正規化前の人物名

    Returns:
        正規化後の人物名
    """
    if pd.isna(name) or not name:
        return name

    result = str(name)

    # 1. Unicode NFC正規化
    result = unicodedata.normalize("NFC", result)

    # 2. CJK互換漢字を統一漢字に変換
    for variant, canonical in VARIANT_CHAR_MAP.items():
        result = result.replace(variant, canonical)

    # 3. 全角空白を半角に統一
    result = result.replace("\u3000", " ")

    return result


def has_variant_chars(name: str) -> bool:
    """
    人物名に異体字が含まれているかチェック

    Args:
        name: チェック対象の人物名

    Returns:
        異体字が含まれている場合True
    """
    if pd.isna(name) or not name:
        return False

    for variant in VARIANT_CHAR_MAP.keys():
        if variant in name:
            return True
    return False


def get_variant_info(name: str) -> List[Dict]:
    """
    人物名に含まれる異体字の情報を取得

    Args:
        name: チェック対象の人物名

    Returns:
        異体字情報のリスト
    """
    if pd.isna(name) or not name:
        return []

    info = []
    for variant, canonical in VARIANT_CHAR_MAP.items():
        if variant in name:
            info.append(
                {
                    "variant_char": variant,
                    "canonical_char": canonical,
                    "variant_code": f"U+{ord(variant):04X}",
                    "canonical_code": f"U+{ord(canonical):04X}",
                }
            )
    return info


def detect_variant_duplicates(
    df: pd.DataFrame,
) -> List[Dict]:
    """
    DataFrameから異体字による重複候補を検出

    Args:
        df: person_nameカラムを持つDataFrame

    Returns:
        重複候補のリスト
    """
    if "person_name" not in df.columns:
        return []

    # 正規化後の名前でグループ化
    normalized_to_original: Dict[str, Set[str]] = {}

    for name in df["person_name"].unique():
        if pd.isna(name):
            continue
        normalized = normalize_person_name(name)
        if normalized not in normalized_to_original:
            normalized_to_original[normalized] = set()
        normalized_to_original[normalized].add(name)

    # 複数の表記がある場合は重複候補
    duplicates = []
    for normalized, originals in normalized_to_original.items():
        if len(originals) > 1:
            # 各表記の詳細情報を収集
            variants = []
            for orig in originals:
                subset = df[df["person_name"] == orig]
                person_ids = subset["person_id"].unique().tolist()
                episode_count = len(subset)
                variants.append(
                    {
                        "name": orig,
                        "person_ids": person_ids,
                        "episode_count": episode_count,
                        "has_variant": has_variant_chars(orig),
                    }
                )

            duplicates.append(
                {
                    "normalized": normalized,
                    "variants": variants,
                    "total_episodes": sum(v["episode_count"] for v in variants),
                    "risk": "HIGH",
                }
            )

    return duplicates


def validate_new_person_name(new_name: str, existing_names: Set[str]) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    新規人物名の登録可否を検証

    Args:
        new_name: 新規登録しようとしている人物名
        existing_names: 既存の人物名セット

    Returns:
        (is_valid, conflict_name, message)
        - is_valid: 登録可能な場合True
        - conflict_name: 競合する既存名（あれば）
        - message: メッセージ
    """
    normalized_new = normalize_person_name(new_name)

    for existing in existing_names:
        normalized_existing = normalize_person_name(existing)
        if normalized_new == normalized_existing and new_name != existing:
            return (
                False,
                existing,
                f"異体字重複: '{new_name}' は既存の '{existing}' と同一人物です",
            )

    return (True, None, None)
