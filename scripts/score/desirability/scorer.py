"""
desirability_score メインスコアラー

ユーザーにとっての「読みたさ」を定量化するスコア。
who（誰の話）× what（何が起きた）× when（いつの話）× quality（品質）を統合。

出力スケール: 0 〜 1,000,000

計算式:
    desirability_score = (
        who_factor × 0.35
      + what_factor × 0.40
      + when_factor × 0.15
      + quality_factor × 0.10
    ) × recency_boost × 1,000,000

使用方法:
    from scripts.score.desirability.scorer import calculate_desirability_score

    result = calculate_desirability_score(episode_row)
    print(f"スコア: {result['desirability_score']:,.0f}")
"""

import math
from dataclasses import dataclass
from typing import Optional

from .config import (
    RECENCY_BOOST,
    SUPERSTARS,
)
from .event_magnitude import calculate_event_magnitude, normalize_magnitude


# ============================================================
# 正規化パラメータ（super_total_norm_params_v1.2.0.jsonより）
# ============================================================
@dataclass
class NormalizationParams:
    """正規化パラメータ"""

    # celebrity_score_v2
    celebrity_median: float = 328.22
    celebrity_iqr: float = 452.75

    # episode_fame_v6
    fame_median: float = 53.03
    fame_iqr: float = 19.66

    # episode_importance_score
    importance_median: float = 51.31
    importance_iqr: float = 49.72


# デフォルトパラメータ
DEFAULT_PARAMS = NormalizationParams()

# 出力スケール
OUTPUT_SCALE = 1_000_000

# 重み配分
WEIGHTS = {
    "who": 0.35,  # 誰の話か
    "what": 0.40,  # 何が起きたか
    "when": 0.15,  # いつの話か
    "quality": 0.10,  # 品質担保
}

# multi_lang_pv正規化パラメータ（対数スケール）
PV_LOG_SCALE_FACTOR = 10.0  # log(1 + pv) / 10 で0-1程度にスケーリング


# ============================================================
# 共通ユーティリティ関数
# ============================================================


def robust_normalize(value: float, median: float, iqr: float) -> float:
    """
    シグモイド変換によるロバスト正規化

    外れ値に強い正規化:
    1. 中央値からの偏差をIQRで割ってzスコア化
    2. シグモイドで0-1にマッピング

    Args:
        value: 元の値
        median: 中央値
        iqr: 四分位範囲

    Returns:
        0-1の正規化値
    """
    if iqr == 0:
        return 0.5
    z = (value - median) / iqr
    # シグモイド: 極端な値でも0-1に収まる
    return 1 / (1 + math.exp(-z))


def safe_float(val, default: Optional[float] = None) -> Optional[float]:
    """
    安全な型変換

    Args:
        val: 変換対象の値
        default: 変換失敗時のデフォルト値

    Returns:
        floatまたはデフォルト値
    """
    if val is None or val == "":
        return default
    try:
        result = float(val)
        if math.isnan(result):
            return default
        return result
    except (ValueError, TypeError):
        return default


def get_float(val, default: float = 0.0) -> float:
    """
    確実にfloatを返す型安全なヘルパー

    Args:
        val: 変換対象の値
        default: 変換失敗時のデフォルト値

    Returns:
        float値（Noneは返さない）
    """
    result = safe_float(val, default)
    return result if result is not None else default


def safe_int(val, default: int = 0) -> int:
    """
    安全なint変換

    Args:
        val: 変換対象の値
        default: 変換失敗時のデフォルト値

    Returns:
        intまたはデフォルト値
    """
    if val is None or val == "":
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def log_normalize_pv(pv: int) -> float:
    """
    PV数を対数正規化

    大きな数値を0-1程度にスケーリング。
    log1p(pv) / PV_LOG_SCALE_FACTOR で計算。

    Args:
        pv: multi_lang_pv値

    Returns:
        0-1程度の正規化値
    """
    if pv <= 0:
        return 0.0
    return min(1.0, math.log1p(pv) / PV_LOG_SCALE_FACTOR)


# ============================================================
# who_factor（誰の話か）- 35%
# ============================================================


def calculate_who_factor(
    celebrity_score_v2: float,
    multi_lang_pv: int,
    person_name: str,
    params: NormalizationParams = DEFAULT_PARAMS,
) -> float:
    """
    人物の知名度因子を計算

    構成:
    - celebrity_score_v2を0-1に正規化（ロバスト正規化）: 60%
    - multi_lang_pvを対数正規化: 30%
    - スーパースターボーナス: +10%

    Args:
        celebrity_score_v2: 人物の知名度スコア
        multi_lang_pv: 多言語Wikipedia PV数
        person_name: 人物名
        params: 正規化パラメータ

    Returns:
        0-1のwho_factor値
    """
    # celebrity_score_v2 正規化（60%）
    celeb_norm = robust_normalize(
        celebrity_score_v2 or 0,
        params.celebrity_median,
        params.celebrity_iqr,
    )

    # multi_lang_pv 対数正規化（30%）
    pv_norm = log_normalize_pv(multi_lang_pv or 0)

    # 基本スコア
    base_score = celeb_norm * 0.6 + pv_norm * 0.3

    # スーパースターボーナス（+10%）
    superstar_bonus = 0.0
    if person_name:
        for star in SUPERSTARS:
            if star in person_name:
                superstar_bonus = 0.1
                break

    return min(1.0, base_score + superstar_bonus)


# ============================================================
# what_factor（何が起きたか）- 40%
# ============================================================


def calculate_what_factor(
    episode_text: str,
    episode_importance_score: float,
    params: NormalizationParams = DEFAULT_PARAMS,
) -> tuple[float, float, str, list]:
    """
    イベント重要度因子を計算

    構成:
    - event_magnitude（Tierキーワード使用）: 60%
    - episode_importance_score正規化: 40%

    Args:
        episode_text: エピソードテキスト
        episode_importance_score: エピソード重要度スコア
        params: 正規化パラメータ

    Returns:
        tuple: (what_factor, event_magnitude, highest_tier, matched_keywords)
        - what_factor: 0-1のwhat_factor値
        - event_magnitude: 計算されたmagnitude値
        - highest_tier: マッチした最高Tier
        - matched_keywords: マッチしたキーワードリスト
    """
    # event_magnitude計算（60%）
    magnitude, highest_tier, matched_keywords = calculate_event_magnitude(episode_text or "")
    magnitude_norm = normalize_magnitude(magnitude)

    # episode_importance_score正規化（40%）
    importance_norm = robust_normalize(
        episode_importance_score or 0,
        params.importance_median,
        params.importance_iqr,
    )

    what_factor = magnitude_norm * 0.6 + importance_norm * 0.4

    return what_factor, magnitude, highest_tier, matched_keywords


# ============================================================
# when_factor（いつの話か）- 15%
# ============================================================


def calculate_when_factor(
    episode_year: Optional[int],
) -> float:
    """
    時期因子を計算

    最近のエピソードほど高スコア。
    年代ごとに異なるスコアを適用:
    - 2020年代: 1.0（最高）
    - 2010年代: 0.9
    - 2000年代: 0.8
    - 1990年代: 0.7
    - それ以前: 年代に応じて減衰

    Args:
        episode_year: エピソードの年（Noneの場合はデフォルト値）

    Returns:
        0-1のwhen_factor値
    """
    if episode_year is None or episode_year <= 0:
        return 0.5  # 不明な場合は中間値

    # 年代判定
    if episode_year >= 2020:
        return 1.0
    elif episode_year >= 2010:
        return 0.9
    elif episode_year >= 2000:
        return 0.8
    elif episode_year >= 1990:
        return 0.7
    elif episode_year >= 1980:
        return 0.6
    elif episode_year >= 1970:
        return 0.5
    elif episode_year >= 1950:
        return 0.4
    elif episode_year >= 1900:
        return 0.3
    else:
        # 1900年以前は最低値
        return 0.2


def estimate_episode_year(
    birth_year: Optional[int],
    age: Optional[int],
) -> Optional[int]:
    """
    birth_yearとageからepisode_yearを推定

    Args:
        birth_year: 生年
        age: エピソード時の年齢

    Returns:
        推定されたepisode_year（推定不可の場合はNone）
    """
    if birth_year is None or age is None:
        return None
    if birth_year <= 0 or age < 0:
        return None
    return birth_year + age


# ============================================================
# quality_factor（品質担保）- 10%
# ============================================================


def calculate_quality_factor(
    episode_fame_v6: float,
    quality_7axis_avg: Optional[float] = None,
) -> float:
    """
    品質因子を計算

    構成:
    - episode_fame_v6 / 100: 70%
    - quality_7axis_avg / 10: 30%

    Args:
        episode_fame_v6: エピソード有名度スコア (0-100)
        quality_7axis_avg: 7軸品質スコア平均 (0-10)（省略可）

    Returns:
        0-1のquality_factor値
    """
    # episode_fame_v6正規化（70%）
    fame_norm = (episode_fame_v6 or 0) / 100.0
    fame_norm = min(1.0, max(0.0, fame_norm))

    # quality_7axis_avg正規化（30%）
    if quality_7axis_avg is not None:
        quality_norm = quality_7axis_avg / 10.0
        quality_norm = min(1.0, max(0.0, quality_norm))
    else:
        quality_norm = 0.5  # デフォルト中間値

    return fame_norm * 0.7 + quality_norm * 0.3


def calculate_quality_7axis_avg(row: dict) -> Optional[float]:
    """
    7軸品質スコアの平均を計算

    Args:
        row: CSVの1行分のデータ

    Returns:
        7軸スコアの平均（0-10）、計算不可の場合はNone
    """
    axis_fields = [
        "memorability_score",
        "empathy_score",
        "surprise_score",
        "generation_quality_score",
        "educational_value",
        "story_quality",
        "factual_density",
    ]

    values = []
    for field in axis_fields:
        val = safe_float(row.get(field))
        if val is not None:
            values.append(val)

    if not values:
        return None

    return sum(values) / len(values)


# ============================================================
# recency_boost（時代性ブースト）
# ============================================================


def calculate_recency_boost(episode_year: Optional[int]) -> float:
    """
    時代性ブーストを計算

    最近のエピソードに乗数ブーストを適用。
    config.pyのRECENCY_BOOSTを使用。

    Args:
        episode_year: エピソードの年

    Returns:
        recency_boost乗数（0.9〜1.2）
    """
    if episode_year is None or episode_year <= 0:
        return 1.0  # 不明な場合はベースライン

    if episode_year >= 2020:
        return RECENCY_BOOST["2020s"]
    elif episode_year >= 2010:
        return RECENCY_BOOST["2010s"]
    elif episode_year >= 2000:
        return RECENCY_BOOST["2000s"]
    elif episode_year >= 1990:
        return RECENCY_BOOST["1990s"]
    else:
        return RECENCY_BOOST["older"]


# ============================================================
# メイン関数
# ============================================================


def calculate_desirability_score(
    row: dict,
    params: NormalizationParams = DEFAULT_PARAMS,
) -> dict:
    """
    エピソードのdesirability_scoreを計算

    計算式:
        desirability_score = (
            who_factor × 0.35
          + what_factor × 0.40
          + when_factor × 0.15
          + quality_factor × 0.10
        ) × recency_boost × 1,000,000

    Args:
        row: CSVの1行分のデータ（dict形式）
        params: 正規化パラメータ
        current_year: 現在の年（デフォルト: 2026）

    Returns:
        dict: {
            "desirability_score": float,  # 最終スコア（0-1,000,000）
            "event_magnitude": float,     # イベント重要度（0-50）
            "recency_boost": float,       # 時代性ブースト乗数
            "who_factor": float,          # 誰の話か（0-1）
            "what_factor": float,         # 何が起きたか（0-1）
            "when_factor": float,         # いつの話か（0-1）
            "quality_factor": float,      # 品質担保（0-1）
            "highest_tier": str,          # マッチした最高Tier
            "matched_keywords": list,     # マッチしたキーワード
        }
    """
    # 必要な値を取得
    celebrity_score_v2 = get_float(row.get("celebrity_score_v2"), 0.0)
    multi_lang_pv = safe_int(row.get("multi_lang_pv"), 0)
    person_name = row.get("person_name", "")
    episode_text = row.get("episode_text", "")
    episode_importance_score = get_float(row.get("episode_importance_score"), 0.0)
    episode_fame_v6 = get_float(row.get("episode_fame_v6"), 0.0)

    # episode_yearの取得または推定
    episode_year_raw = safe_int(row.get("episode_year"), 0)
    episode_year: Optional[int] = episode_year_raw if episode_year_raw > 0 else None
    if episode_year is None:
        birth_year = safe_int(row.get("birth_year"), 0)
        age = safe_int(row.get("age"), 0)
        episode_year = estimate_episode_year(birth_year, age)

    # 7軸品質平均の計算
    quality_7axis_avg = calculate_quality_7axis_avg(row)

    # 各因子の計算
    who_factor = calculate_who_factor(
        celebrity_score_v2,
        multi_lang_pv,
        person_name,
        params,
    )

    what_factor, event_magnitude, highest_tier, matched_keywords = calculate_what_factor(
        episode_text,
        episode_importance_score,
        params,
    )

    when_factor = calculate_when_factor(episode_year)

    quality_factor = calculate_quality_factor(episode_fame_v6, quality_7axis_avg)

    # recency_boost
    recency_boost = calculate_recency_boost(episode_year)

    # 最終スコア計算
    weighted_sum = (
        who_factor * WEIGHTS["who"]
        + what_factor * WEIGHTS["what"]
        + when_factor * WEIGHTS["when"]
        + quality_factor * WEIGHTS["quality"]
    )

    desirability_score = weighted_sum * recency_boost * OUTPUT_SCALE

    return {
        "desirability_score": round(desirability_score, 0),
        "event_magnitude": event_magnitude,
        "recency_boost": round(recency_boost, 2),
        "who_factor": round(who_factor, 4),
        "what_factor": round(what_factor, 4),
        "when_factor": round(when_factor, 4),
        "quality_factor": round(quality_factor, 4),
        "highest_tier": highest_tier,
        "matched_keywords": matched_keywords,
    }


# ============================================================
# バッチ処理用ユーティリティ
# ============================================================


def score_all_episodes(
    episodes: list[dict],
    params: Optional[NormalizationParams] = None,
) -> list[dict]:
    """
    全エピソードにdesirability_scoreを付与

    Args:
        episodes: エピソードリスト
        params: 正規化パラメータ（省略時はデフォルト）

    Returns:
        スコア付きエピソードリスト
    """
    if params is None:
        params = DEFAULT_PARAMS

    scored = []
    for ep in episodes:
        result = calculate_desirability_score(ep, params)
        ep_copy = ep.copy()
        ep_copy.update(result)
        scored.append(ep_copy)

    return scored


def get_top_episodes(
    scored_episodes: list[dict],
    n: int = 100,
    sort_key: str = "desirability_score",
) -> list[dict]:
    """
    上位N件のエピソードを取得

    Args:
        scored_episodes: スコア付きエピソードリスト
        n: 取得件数
        sort_key: ソートキー

    Returns:
        上位N件のエピソードリスト
    """
    sorted_eps = sorted(
        scored_episodes,
        key=lambda x: x.get(sort_key, 0),
        reverse=True,
    )
    return sorted_eps[:n]


# ============================================================
# デモ実行
# ============================================================


def main():
    """デモ実行"""
    import pandas as pd
    from pathlib import Path

    PROJECT_ROOT = Path(__file__).resolve().parents[3]
    CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

    print("=" * 60)
    print("desirability_score算出デモ")
    print("=" * 60)

    # データ読み込み
    print("\n1. データ読み込み中...")
    df = pd.read_csv(CSV_PATH, dtype=str)
    episodes = df.to_dict("records")
    print(f"   読み込み完了: {len(episodes):,}件")

    # サンプル計算
    print("\n2. サンプル計算...")

    # 大谷翔平を探す
    ohtani_eps = [e for e in episodes if e.get("person_name") == "大谷翔平"]
    if ohtani_eps:
        ep = ohtani_eps[0]
        result = calculate_desirability_score(ep)
        print("\n   大谷翔平エピソード:")
        print(f"     desirability_score: {result['desirability_score']:,.0f}")
        print(f"     who_factor: {result['who_factor']:.4f}")
        print(f"     what_factor: {result['what_factor']:.4f}")
        print(f"     when_factor: {result['when_factor']:.4f}")
        print(f"     quality_factor: {result['quality_factor']:.4f}")
        print(f"     event_magnitude: {result['event_magnitude']}")
        print(f"     recency_boost: {result['recency_boost']}")
        print(f"     highest_tier: {result['highest_tier']}")
        print(f"     matched_keywords: {result['matched_keywords'][:5]}...")

    # 上位10件を計算
    print("\n3. 上位10件計算中...")
    scores = []
    for ep in episodes[:1000]:  # サンプリング
        result = calculate_desirability_score(ep)
        scores.append(
            {
                "episode_id": ep.get("episode_id"),
                "person_name": ep.get("person_name"),
                "desirability_score": result["desirability_score"],
                "highest_tier": result["highest_tier"],
            }
        )

    scores.sort(key=lambda x: x["desirability_score"], reverse=True)
    print("\n   Top 10:")
    for i, s in enumerate(scores[:10], 1):
        print(f"     {i}. {s['person_name']}: {s['desirability_score']:,.0f} (Tier {s['highest_tier']})")

    print("\n" + "=" * 60)
    print("デモ完了")


if __name__ == "__main__":
    main()
