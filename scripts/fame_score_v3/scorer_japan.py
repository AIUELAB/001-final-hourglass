#!/usr/bin/env python3
"""
日本向け有名人度スコア計算モジュール。

グローバルスコア（fame_score_v3）に対して日本人上乗せを適用し、
日本ユーザー向けにチューニングされたスコアを算出する。

採用案: 案2+3ハイブリッド
- 日本人フラグ + カテゴリ重み + 日本語PV比率ボーナス
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class JapanBoostConfig:
    """日本向け上乗せ設定"""

    enabled: bool = True
    base_alpha: float = 0.10
    category_weights: dict = None
    pv_ratio_max_bonus: float = 0.15
    pv_ratio_scale: float = 0.50

    def __post_init__(self):
        if self.category_weights is None:
            self.category_weights = {"default": 0.05}


def load_config(config_path: Optional[Path] = None) -> JapanBoostConfig:
    """設定ファイルを読み込み"""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "fame_score_japan.yaml"

    if not config_path.exists():
        return JapanBoostConfig()

    with open(config_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    japan_boost = data.get("japan_boost", {})
    pv_ratio = japan_boost.get("pv_ratio_bonus", {})

    return JapanBoostConfig(
        enabled=japan_boost.get("enabled", True),
        base_alpha=japan_boost.get("base_alpha", 0.10),
        category_weights=japan_boost.get("category_weights", {"default": 0.05}),
        pv_ratio_max_bonus=pv_ratio.get("max_bonus", 0.15),
        pv_ratio_scale=pv_ratio.get("scale", 0.50),
    )


def calculate_japan_score(
    global_score: float,
    is_japanese: bool,
    category: str,
    wikipedia_pv_ja: float = 0,
    multi_lang_pv: float = 0,
    config: Optional[JapanBoostConfig] = None,
) -> float:
    """
    日本向け有名人度スコアを計算。

    Args:
        global_score: グローバルスコア（fame_score_v3）
        is_japanese: 日本人フラグ
        category: カテゴリ（スポーツ、音楽等）
        wikipedia_pv_ja: 日本語Wikipedia PV
        multi_lang_pv: 多言語合計PV
        config: 設定（Noneの場合はデフォルト読み込み）

    Returns:
        日本向けスコア（fame_score_japan）
    """
    if config is None:
        config = load_config()

    if not config.enabled:
        return global_score

    if not is_japanese:
        return global_score

    # 基本上乗せ
    boost = config.base_alpha

    # カテゴリ重み
    cat_weight = config.category_weights.get(category, config.category_weights.get("default", 0.05))
    boost += cat_weight

    # 日本語PV比率ボーナス
    if multi_lang_pv > 0 and wikipedia_pv_ja > 0:
        ja_pv_ratio = wikipedia_pv_ja / multi_lang_pv
        pv_bonus = min(ja_pv_ratio * config.pv_ratio_scale, config.pv_ratio_max_bonus)
        boost += pv_bonus

    # 最終スコア
    japan_score = global_score * (1 + boost)
    return round(japan_score, 2)


def calculate_boost_breakdown(
    is_japanese: bool,
    category: str,
    wikipedia_pv_ja: float = 0,
    multi_lang_pv: float = 0,
    config: Optional[JapanBoostConfig] = None,
) -> dict:
    """
    上乗せの内訳を計算（デバッグ/レポート用）。

    Returns:
        {
            "is_japanese": bool,
            "base_alpha": float,
            "category_weight": float,
            "pv_ratio_bonus": float,
            "total_boost": float,
            "multiplier": float,
        }
    """
    if config is None:
        config = load_config()

    result = {
        "is_japanese": is_japanese,
        "base_alpha": 0.0,
        "category_weight": 0.0,
        "pv_ratio_bonus": 0.0,
        "total_boost": 0.0,
        "multiplier": 1.0,
    }

    if not is_japanese:
        return result

    result["base_alpha"] = config.base_alpha

    cat_weight = config.category_weights.get(category, config.category_weights.get("default", 0.05))
    result["category_weight"] = cat_weight

    if multi_lang_pv > 0 and wikipedia_pv_ja > 0:
        ja_pv_ratio = wikipedia_pv_ja / multi_lang_pv
        pv_bonus = min(ja_pv_ratio * config.pv_ratio_scale, config.pv_ratio_max_bonus)
        result["pv_ratio_bonus"] = round(pv_bonus, 4)

    total = result["base_alpha"] + result["category_weight"] + result["pv_ratio_bonus"]
    result["total_boost"] = round(total, 4)
    result["multiplier"] = round(1 + total, 4)

    return result


if __name__ == "__main__":
    # テスト実行
    print("=== 日本向けスコア計算テスト ===\n")

    config = load_config()
    print(f"設定読み込み: enabled={config.enabled}")
    print(f"  base_alpha: {config.base_alpha}")
    print(f"  category_weights: {config.category_weights}")
    print()

    test_cases = [
        # (name, global_score, is_japanese, category, ja_pv, multi_pv)
        ("大谷翔平", 536.85, True, "スポーツ", 261588, 5452838),
        ("安倍晋三", 676.14, True, "政治・社会", 100067, 1156270),
        ("イチロー", 500.00, True, "スポーツ", 150000, 2000000),
        ("トランプ", 789.06, False, "政治・社会", 50000, 10000000),
    ]

    for name, score, is_jp, cat, ja_pv, multi_pv in test_cases:
        japan_score = calculate_japan_score(score, is_jp, cat, ja_pv, multi_pv, config)
        breakdown = calculate_boost_breakdown(is_jp, cat, ja_pv, multi_pv, config)

        print(f"{name}:")
        print(f"  global: {score:.2f} → japan: {japan_score:.2f}")
        print(f"  multiplier: ×{breakdown['multiplier']:.2f}")
        if is_jp:
            print(
                f"  内訳: base={breakdown['base_alpha']:.0%} + cat={breakdown['category_weight']:.0%} + pv={breakdown['pv_ratio_bonus']:.1%}"
            )
        print()
