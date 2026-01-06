#!/usr/bin/env python3
"""
超総合スコア（Super Total Score）算出モジュール

目的:
    複数の既存スコアを統合し「ユーザーが最も読みたい真のエピソード」を順位付け

出力スケール: 0 〜 1,000,000

使用方法:
    from scripts.score.super_total_scorer import SuperTotalScorer

    scorer = SuperTotalScorer(all_episodes)
    result = scorer.calculate(episode_row)
    print(f"スコア: {result.score:,.0f}")
    print(f"内訳: {result.breakdown}")
"""

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class SuperTotalConfig:
    """超総合スコア設定

    Attributes:
        version: 設定バージョン
        min_factual_density: 事実密度の足切り閾値
        min_generation_quality: 生成品質の足切り閾値
        weight_celebrity: 人物有名度の重み
        weight_episode_fame: エピソード有名度の重み
        weight_quality: 品質スコアの重み
        weight_historical: 歴史的インパクトの重み
        achievement_boost_multiplier: 偉業ブースト乗数（v2.0.0追加）
        output_scale: 出力スケール（デフォルト: 1,000,000）
    """

    version: str = "v1.2.0"
    # ゲート閾値
    min_factual_density: float = 6.0
    min_generation_quality: float = 6.0
    # 重み（合計 = 1.0）v1.1.0調整: historical重み増加
    weight_celebrity: float = 0.30  # v1.0.0: 0.35 → v1.1.0: 0.30
    weight_episode_fame: float = 0.30
    weight_quality: float = 0.20  # v1.0.0: 0.25 → v1.1.0: 0.20
    weight_historical: float = 0.20  # v1.0.0: 0.10 → v1.1.0: 0.20
    # 偉業ブースト乗数（v2.0.0: 0.5で半減、v1.x: 1.0でフル）
    achievement_boost_multiplier: float = 1.0
    # 出力スケール
    output_scale: int = 1_000_000

    @classmethod
    def from_json(cls, config_path: Path) -> "SuperTotalConfig":
        """JSONファイルから設定を読み込む

        Args:
            config_path: 設定ファイルパス

        Returns:
            SuperTotalConfig インスタンス
        """
        with open(config_path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(
            version=data.get("version", "v2.0.0"),
            weight_celebrity=data["weights"]["celebrity"],
            weight_episode_fame=data["weights"]["episode_fame"],
            weight_quality=data["weights"]["quality"],
            weight_historical=data["weights"]["historical"],
            min_factual_density=data["gates"]["min_factual_density"],
            min_generation_quality=data["gates"]["min_generation_quality"],
            achievement_boost_multiplier=data.get("achievement_boost_multiplier", 1.0),
            output_scale=data.get("output_scale", 1_000_000),
        )


# v1.3.0: 偉業キーワードダイレクトブースト（ネガティブ文脈除外対応）
ACHIEVEMENT_BOOST = {
    # 最高レベル（+12%）
    "ノーベル賞": 0.12,
    "ノーベル物理学賞": 0.12,
    "ノーベル化学賞": 0.12,
    "ノーベル文学賞": 0.12,
    "ノーベル平和賞": 0.12,
    "ノーベル医学賞": 0.12,
    "E=mc²": 0.12,  # v1.2.0追加: 世界で最も有名な方程式
    "特殊相対性理論": 0.12,  # v1.2.0追加: 科学史上最重要理論
    "一般相対性理論": 0.12,  # v1.2.0追加
    "ワールドシリーズ制覇": 0.12,  # v1.3.0追加: MLB最高栄誉
    "ワールドシリーズ優勝": 0.12,  # v1.3.0追加
    # 高レベル（+10%）
    "世界初": 0.10,
    "史上初": 0.10,
    "オリンピック金メダル": 0.10,
    "アカデミー賞": 0.10,
    "グラミー賞": 0.10,
    "相対性理論": 0.10,  # v1.2.0追加
    "奇跡の年": 0.10,  # v1.2.0追加: アインシュタイン1905年
    "量子力学": 0.10,  # v1.2.0追加
    "万有引力": 0.10,  # v1.2.0追加: ニュートン
    "進化論": 0.10,  # v1.2.0追加: ダーウィン
    "本塁打王": 0.10,  # v1.3.0追加
    "三冠王": 0.10,  # v1.3.0追加
    # 中レベル（+8%）
    "50本塁打": 0.08,
    "51本塁打": 0.08,  # v1.3.0追加
    "52本塁打": 0.08,  # v1.3.0追加
    "53本塁打": 0.08,  # v1.3.0追加
    "54本塁打": 0.08,  # v1.3.0追加
    "55本塁打": 0.08,  # v1.3.0追加
    "50盗塁": 0.08,
    "二刀流達成": 0.08,  # v1.3.0修正: 「二刀流」→「二刀流達成」に変更（ネガティブ文脈回避）
    "投打二刀流": 0.08,  # v1.3.0追加
    "MVP": 0.08,
    "世界記録": 0.08,
    "日本初": 0.08,
    "画期的": 0.08,  # v1.2.0追加
    "革命的": 0.08,  # v1.2.0追加
    "リーグ優勝": 0.08,  # v1.3.0追加
    # 低レベル（+5%）
    "金メダル": 0.05,
    "優勝": 0.05,
    "記録更新": 0.05,
    "シーズン優勝": 0.05,  # v1.3.0追加
}

# v1.3.0: ネガティブ文脈キーワード（これらが近くにある場合はブースト無効化）
NEGATIVE_CONTEXT_KEYWORDS = [
    "失敗",
    "挫折",
    "断念",
    "できなかった",
    "できず",
    "逃した",
    "惜しくも",
    "届かず",
    "及ばず",
    "敗れ",
]

# v1.2.0: ターニングポイントブースト
TURNING_POINT_BOOST = 0.08  # TURNING_POINT_MANUALタグ持ちに+8%


@dataclass
class NormalizationParams:
    """正規化パラメータ（永続化用）"""

    version: str
    computed_at: str
    celebrity_median: float
    celebrity_iqr: float
    fame_median: float
    fame_iqr: float
    importance_median: float = 50.0  # v1.1.0追加
    importance_iqr: float = 30.0  # v1.1.0追加


@dataclass
class ScoreResult:
    """スコア算出結果

    Attributes:
        score: 超総合スコア（0-1,000,000）
        passed_gate: ゲートを通過したか
        gate_reason: ゲート不通過の理由
        breakdown: スコア内訳
        penalties: 適用されたペナルティ
    """

    score: float
    passed_gate: bool
    gate_reason: Optional[str]
    breakdown: dict
    penalties: list

    def to_dict(self) -> dict:
        """辞書に変換"""
        return asdict(self)


class SuperTotalScorer:
    """超総合スコア算出器

    設計方針:
    1. ゲートファースト: 品質基準を満たさないものは事前に足切り
    2. 正規化統一: 全スコアを0-1に正規化してから統合
    3. 二重計上回避: 7軸を使用し、5軸は使用しない
    """

    # 7軸重み（質の観点で重要度順）
    QUALITY_WEIGHTS = {
        "記憶性スコア": 0.25,  # 最重要: 記憶に残るか
        "意外性スコア": 0.18,  # 興味を引くか
        "ストーリー品質": 0.15,  # 読みやすさ
        "教育的価値": 0.15,  # 学びがあるか
        "事実密度": 0.12,  # 具体性（ゲート済み）
        "共感性スコア": 0.10,  # 感情的響き
        "生成品質スコア": 0.05,  # 文章品質（ゲート済み）
    }

    # 回顧・抽象パターン
    RETROSPECTIVE_PATTERNS = [
        "人生を振り返",
        "自らの歩みを振り返",
        "静かな日々を送",
        "晩年.*回顧",
        "回想しながら",
        "もし.*生きていたら",
    ]

    def __init__(
        self,
        all_episodes: list,
        config: Optional[SuperTotalConfig] = None,
        normalization_params: Optional[NormalizationParams] = None,
    ):
        """
        Args:
            all_episodes: 全エピソードデータ（正規化パラメータ計算用）
            config: 設定（省略時はデフォルト）
            normalization_params: 事前計算済み正規化パラメータ（省略時は計算）
        """
        self.config = config or SuperTotalConfig()

        if normalization_params:
            self.norm_params = normalization_params
        else:
            self.norm_params = self._compute_normalization(all_episodes)

    def _compute_normalization(self, episodes: list) -> NormalizationParams:
        """正規化パラメータを計算（ロバストスケーリング用）"""

        def robust_stats(values: list) -> tuple:
            """中央値とIQRを計算"""
            arr = np.array([v for v in values if v is not None and not np.isnan(v)], dtype=float)
            if len(arr) == 0:
                return 0.0, 1.0
            median = float(np.median(arr))
            q1 = float(np.percentile(arr, 25))
            q3 = float(np.percentile(arr, 75))
            iqr = q3 - q1
            if iqr == 0:
                iqr = 1.0  # ゼロ除算防止
            return median, iqr

        celeb_values = [self._safe_float(e.get("celebrity_score_v2")) for e in episodes]
        fame_values = [self._safe_float(e.get("episode_fame_v6")) for e in episodes]
        importance_values = [self._safe_float(e.get("episode_importance_score")) for e in episodes]

        celeb_median, celeb_iqr = robust_stats(celeb_values)
        fame_median, fame_iqr = robust_stats(fame_values)
        importance_median, importance_iqr = robust_stats(importance_values)

        return NormalizationParams(
            version=self.config.version,
            computed_at=datetime.now().isoformat(),
            celebrity_median=celeb_median,
            celebrity_iqr=celeb_iqr,
            fame_median=fame_median,
            fame_iqr=fame_iqr,
            importance_median=importance_median,
            importance_iqr=importance_iqr,
        )

    def save_normalization_params(self, path: Path) -> None:
        """正規化パラメータを保存"""
        with open(path, "w", encoding="utf-8") as f:
            json.dump(asdict(self.norm_params), f, ensure_ascii=False, indent=2)

    @classmethod
    def load_normalization_params(cls, path: Path) -> NormalizationParams:
        """正規化パラメータを読み込み"""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return NormalizationParams(**data)

    def _safe_float(self, val, default: Optional[float] = None) -> Optional[float]:
        """安全な型変換"""
        if val is None or val == "":
            return default
        try:
            result = float(val)
            if np.isnan(result):
                return default
            return result
        except (ValueError, TypeError):
            return default

    def _robust_normalize(self, value: float, median: float, iqr: float) -> float:
        """
        ロバスト正規化（シグモイド変換）

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
        if iqr == 0 or value is None:
            return 0.5
        z = (value - median) / iqr
        # シグモイド: 極端な値でも0-1に収まる
        return 1 / (1 + math.exp(-z))

    def _check_gate(self, row: dict) -> tuple:
        """
        ハードゲート（足切り）チェック

        以下の条件で除外:
        - 事実密度 < 6.0
        - 生成品質 < 6.0
        - verification_status = "rejected"

        Returns:
            (passed: bool, reason: Optional[str])
        """
        fact = self._safe_float(row.get("事実密度"), 0)
        gen = self._safe_float(row.get("生成品質スコア"), 0)

        if fact < self.config.min_factual_density:
            return False, f"事実密度 {fact:.1f} < {self.config.min_factual_density}"

        if gen < self.config.min_generation_quality:
            return False, f"生成品質 {gen:.1f} < {self.config.min_generation_quality}"

        status = row.get("verification_status", "")
        if status == "rejected":
            return False, "verification_status = rejected"

        return True, None

    def _calc_quality_score(self, row: dict) -> float:
        """
        7軸加重平均による品質スコア

        Returns:
            0-1の品質スコア
        """
        total_weight = 0.0
        weighted_sum = 0.0

        for field, weight in self.QUALITY_WEIGHTS.items():
            val = self._safe_float(row.get(field))
            if val is not None:
                weighted_sum += val * weight
                total_weight += weight

        if total_weight == 0:
            return 0.5

        # 0-10スケールを0-1に正規化
        return (weighted_sum / total_weight) / 10

    def _calc_penalty(self, row: dict) -> tuple:
        """
        ソフトペナルティを計算

        適用されるペナルティ:
        - 事実密度 6.0-7.0 → 乗数 0.85
        - 生成品質 6.0-7.0 → 乗数 0.85
        - 回顧パターン → 乗数 0.80

        Returns:
            (multiplier: float, penalties: list[str])
        """
        penalties = []
        multiplier = 1.0

        # 事実密度ソフトペナルティ
        fact = self._safe_float(row.get("事実密度"), 10)
        if 6.0 <= fact < 7.0:
            multiplier *= 0.85
            penalties.append(f"事実密度ソフトペナルティ ({fact:.1f})")

        # 生成品質ソフトペナルティ
        gen = self._safe_float(row.get("生成品質スコア"), 10)
        if 6.0 <= gen < 7.0:
            multiplier *= 0.85
            penalties.append(f"生成品質ソフトペナルティ ({gen:.1f})")

        # 回顧パターン
        text = row.get("episode_text", "")
        for pattern in self.RETROSPECTIVE_PATTERNS:
            if pattern in text:
                multiplier *= 0.80
                penalties.append(f"回顧パターン: {pattern}")
                break  # 1回のみ適用

        return multiplier, penalties

    def _calc_achievement_boost(self, row: dict) -> tuple:
        """
        偉業キーワードブーストを計算（v1.3.0: ネガティブ文脈除外対応）

        エピソードテキストに偉業キーワードが含まれる場合、
        スコアに乗数ブーストを適用する。
        v1.3.0: キーワード周辺にネガティブ文脈がある場合はブースト無効化
        TURNING_POINT_MANUALタグがある場合も追加ブースト。
        v2.0.0: achievement_boost_multiplierでブースト全体を調整可能

        Returns:
            (boost: float, keywords: list[str])
        """
        text = row.get("episode_text", "")
        boost = 0.0
        keywords = []

        for keyword, boost_value in ACHIEVEMENT_BOOST.items():
            if keyword in text:
                # v1.3.0: ネガティブ文脈チェック
                # キーワードの前後30文字にネガティブワードがあればスキップ
                idx = text.find(keyword)
                context_start = max(0, idx - 30)
                context_end = min(len(text), idx + len(keyword) + 30)
                context = text[context_start:context_end]

                is_negative = False
                for neg_word in NEGATIVE_CONTEXT_KEYWORDS:
                    if neg_word in context:
                        is_negative = True
                        break

                if is_negative:
                    continue  # ネガティブ文脈ではブーストしない

                # 最大ブーストを採用（複数キーワードがあっても最大値）
                if boost_value > boost:
                    boost = boost_value
                keywords.append(keyword)

        # v1.2.0: TURNING_POINT_MANUALタグブースト（累積）
        source = row.get("source", "")
        if source == "TURNING_POINT_MANUAL":
            boost += TURNING_POINT_BOOST
            keywords.append("TURNING_POINT")

        # v2.0.0: achievement_boost_multiplierで全体調整
        boost = boost * self.config.achievement_boost_multiplier

        return boost, keywords

    def calculate(self, row: dict) -> ScoreResult:
        """
        超総合スコアを計算

        Args:
            row: エピソードデータ（CSVの1行に相当するdict）

        Returns:
            ScoreResult: スコアと説明
        """
        # Step 1: ゲートチェック
        passed, reason = self._check_gate(row)
        if not passed:
            return ScoreResult(
                score=0,
                passed_gate=False,
                gate_reason=reason,
                breakdown={},
                penalties=[],
            )

        # Step 2: 各コンポーネントの正規化
        celebrity_norm = self._robust_normalize(
            self._safe_float(row.get("celebrity_score_v2"), 0),
            self.norm_params.celebrity_median,
            self.norm_params.celebrity_iqr,
        )

        fame_norm = self._robust_normalize(
            self._safe_float(row.get("episode_fame_v6"), 0),
            self.norm_params.fame_median,
            self.norm_params.fame_iqr,
        )

        quality_norm = self._calc_quality_score(row)

        # 歴史的インパクト（episode_importance_scoreをロバスト正規化：v1.1.0修正）
        historical_norm = self._robust_normalize(
            self._safe_float(row.get("episode_importance_score"), 0),
            self.norm_params.importance_median,
            self.norm_params.importance_iqr,
        )

        # Step 3: 重み付き統合
        raw = (
            self.config.weight_celebrity * celebrity_norm
            + self.config.weight_episode_fame * fame_norm
            + self.config.weight_quality * quality_norm
            + self.config.weight_historical * historical_norm
        )

        # Step 3.5: 偉業キーワードブースト（v1.1.0）
        achievement_boost, boost_keywords = self._calc_achievement_boost(row)
        raw = raw * (1 + achievement_boost)

        # Step 4: ペナルティ適用
        penalty_mult, penalties = self._calc_penalty(row)

        # Step 5: 最終スコア計算
        final = raw * penalty_mult * self.config.output_scale

        return ScoreResult(
            score=round(final, 0),
            passed_gate=True,
            gate_reason=None,
            breakdown={
                "celebrity_norm": round(celebrity_norm, 4),
                "fame_norm": round(fame_norm, 4),
                "quality_norm": round(quality_norm, 4),
                "historical_norm": round(historical_norm, 4),
                "achievement_boost": round(achievement_boost, 2),
                "boost_keywords": boost_keywords,
                "raw_score": round(raw, 4),
                "penalty_multiplier": round(penalty_mult, 2),
            },
            penalties=penalties,
        )


def main():
    """デモ実行"""
    import pandas as pd

    CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

    print("=" * 60)
    print("超総合スコア算出デモ")
    print("=" * 60)

    # データ読み込み
    print("\n1. データ読み込み中...")
    df = pd.read_csv(CSV_PATH, dtype=str)
    episodes = df.to_dict("records")
    print(f"   読み込み完了: {len(episodes):,}件")

    # スコアラー初期化
    print("\n2. スコアラー初期化中...")
    scorer = SuperTotalScorer(episodes)
    print("   正規化パラメータ:")
    print(
        f"     celebrity_score_v2: median={scorer.norm_params.celebrity_median:.1f}, iqr={scorer.norm_params.celebrity_iqr:.1f}"
    )
    print(f"     episode_fame_v6: median={scorer.norm_params.fame_median:.1f}, iqr={scorer.norm_params.fame_iqr:.1f}")
    print(
        f"     episode_importance: median={scorer.norm_params.importance_median:.1f}, iqr={scorer.norm_params.importance_iqr:.1f}"
    )

    # サンプル計算
    print("\n3. サンプル計算...")

    # 大谷翔平を探す
    ohtani_eps = [e for e in episodes if e.get("person_name") == "大谷翔平"]
    if ohtani_eps:
        ep = ohtani_eps[0]
        result = scorer.calculate(ep)
        print("\n   大谷翔平エピソード:")
        print(f"     スコア: {result.score:,.0f}")
        print(f"     ゲート: {'PASS' if result.passed_gate else 'FAIL'}")
        print(f"     内訳: {result.breakdown}")

    # 上位10件を計算
    print("\n4. 上位10件計算中...")
    scores = []
    for ep in episodes[:1000]:  # サンプリング
        result = scorer.calculate(ep)
        if result.passed_gate:
            scores.append((ep.get("episode_id"), ep.get("person_name"), result.score))

    scores.sort(key=lambda x: x[2], reverse=True)
    print("\n   Top 10:")
    for i, (ep_id, name, score) in enumerate(scores[:10], 1):
        print(f"     {i}. {name}: {score:,.0f} ({ep_id})")

    print("\n" + "=" * 60)
    print("デモ完了")


if __name__ == "__main__":
    main()
