#!/usr/bin/env python3
"""
大量生産システム設定モジュール

設定クラスと定数を定義
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

# プロジェクトルート
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# データパス
MASTER_CSV_PATH = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
LOGS_DIR = PROJECT_ROOT / "src/reports/logs"


@dataclass
class QualityGateConfig:
    """品質ゲート設定"""

    min_factual_density: float = 6.5  # 事実密度閾値（7.0→6.5に緩和）
    min_generation_quality: float = 6.5  # 生成品質閾値（8.0→7.0→6.5に緩和）
    min_memorability: float = 5.5  # 記憶性閾値（6.0→5.5に緩和）
    min_year_count: int = 1  # 年号最低数
    min_number_count: int = 3  # 数値最低数
    min_proper_noun_count: int = 5  # 固有名詞最低数
    max_similarity_threshold: float = 0.7  # 重複判定閾値
    # Phase 3: 評価モデル設定
    use_haiku_for_evaluation: bool = True  # 評価にHaiku使用（コスト-92%）
    # Phase 4: 評価バッチサイズ
    evaluation_batch_size: int = 50  # 評価バッチサイズ（20→50で呼び出し-60%）


@dataclass
class GenerationConfig:
    """生成設定"""

    max_workers: int = 50  # 最大並列数
    candidates_per_input: int = 1  # 入力あたり候補数（3→1でトークン66%削減）
    max_retries: int = 3  # リトライ回数
    timeout_seconds: int = 60  # タイムアウト
    batch_size: int = 10  # バッチサイズ（評価用LLMトークン制限対応）
    # Phase 2: プロンプト圧縮オプション
    use_compact_prompt: bool = False  # 圧縮版プロンプト使用（-73%トークン）


@dataclass
class SelectionConfig:
    """候補選定設定"""

    target_count: int = 500  # 目標候補数
    uncovered_only: bool = True  # 純粋差分モード（既存DBにないものだけ生成）
    uncovered_ratio: float = 0.4  # 未カバー優先比率（uncovered_only=False時）
    low_quality_ratio: float = 0.3  # 低品質置換比率（uncovered_only=False時）
    diversity_ratio: float = 0.3  # 多様性向上比率（uncovered_only=False時）

    # カテゴリローテーション（曜日別）
    weekday_categories: Dict[int, List[str]] = field(
        default_factory=lambda: {
            0: ["科学・技術", "学術・研究"],  # 月
            1: ["芸術・文化", "音楽"],  # 火
            2: ["スポーツ"],  # 水
            3: ["文学", "映画・演劇"],  # 木
            4: ["ビジネス", "起業家"],  # 金
            5: ["政治・社会", "歴史"],  # 土
            6: ["エンターテイメント", "その他"],  # 日
        }
    )


@dataclass
class MassProductionConfig:
    """大量生産統合設定"""

    quality: QualityGateConfig = field(default_factory=QualityGateConfig)
    generation: GenerationConfig = field(default_factory=GenerationConfig)
    selection: SelectionConfig = field(default_factory=SelectionConfig)

    # パス設定
    master_csv_path: Path = MASTER_CSV_PATH
    logs_dir: Path = LOGS_DIR

    # 実行モード
    dry_run: bool = False
    verbose: bool = False


# デフォルト設定インスタンス
DEFAULT_CONFIG = MassProductionConfig()


# 品質スコア7軸の重み
QUALITY_SCORE_WEIGHTS = {
    "事実密度": 0.25,
    "生成品質スコア": 0.20,
    "記憶性スコア": 0.20,
    "意外性スコア": 0.10,
    "ストーリー品質": 0.10,
    "教育的価値": 0.10,
    "共感性スコア": 0.05,
}


# 禁止表現パターン
FORBIDDEN_PATTERNS = [
    "人生を振り返",
    "自らの歩みを振り返",
    "静かな日々を送",
    "晩年.*回顧",
    "回想しながら",
    "もし.*生きていたら",
]


# 必須キーワード（事実性担保）
REQUIRED_PATTERNS = {
    "year": r"\d{4}年",  # 年号
    "number": r"\d+",  # 数値
}
