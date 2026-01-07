"""
Hybrid Generator Configuration

ハイブリッドエピソード生成システムの設定ファイル。
ルールブック、品質閾値、多様性目標を一元管理。
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

# ==============================================================================
# パス設定
# ==============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
BACKUP_DIR = PROJECT_ROOT / "preserved" / "backups"
LOGS_DIR = PROJECT_ROOT / "src" / "reports" / "logs"
CACHE_DIR = PROJECT_ROOT / "src" / "cache" / "hybrid_generator"


# ==============================================================================
# 生成戦略
# ==============================================================================


class Strategy(Enum):
    """生成戦略の種類"""

    EPGEN_FIRST = "epgen_first"  # EPGEN優先、失敗時は既存へフォールバック
    LEGACY_FIRST = "legacy_first"  # 既存優先、品質不足時にEPGENで補強
    AB_COMPARE = "ab_compare"  # A/B比較モード（両方生成して比較）


# ==============================================================================
# 生成前ルール（トークン節約）
# ==============================================================================

GENERATION_RULES = {
    # 基本制約
    "age_boundary": True,  # birth-death範囲内のみ
    "same_age_duplicate": True,  # 同一人物・同一年齢の重複禁止
    "prohibited_patterns": True,  # メタ表現・禁止パターン
    # 多様性制約
    "cooldown_hours": 4,  # 同一人物の再生成までの待機時間（24→4に短縮）
    "max_per_person_per_week": 3,  # 週あたり同一人物の生成上限
    "max_per_person_per_day": 1,  # 日あたり同一人物の生成上限
    # 品質制約
    "min_char_count": 200,  # 最小文字数
    "max_char_count": 500,  # 最大文字数
    # リトライ制約
    "max_retries": 2,  # 最大リトライ回数
    "retry_delay_seconds": 1,  # リトライ間隔
}

# ==============================================================================
# 品質閾値（EPUP再発防止）
# ==============================================================================

QUALITY_THRESHOLDS = {
    # 7軸スコア閾値（0-10）- ハードゲート
    # Phase 2: 上位レベル必須化（事実密度>=7, 生成品質>=8）
    "min_factual_density": 7.0,  # 事実密度（最重要）← Phase2: 6.0→7.0
    "min_generation_quality": 8.0,  # 生成品質（最重要）← Phase2: 6.0→8.0
    "min_memorability": 5.5,  # 記憶性
    "min_empathy": 4.0,  # 共感性（Phase4調整: 5.0→4.0、架空キャラ対応）
    "min_surprise": 4.0,  # 意外性（Phase4調整: 5.0→4.0、架空キャラ対応）
    "min_educational_value": 4.0,  # 教育的価値（Phase4調整: 5.0→4.0、架空キャラ対応）
    "min_story_quality": 5.0,  # ストーリー品質
    # 統合スコア閾値
    "min_composite": 380,  # 即棄却ライン
    "target_composite": 550,  # 即採用ライン
    "retry_composite": 470,  # リトライ後採用ライン
    # 超総合スコア閾値（0-1,000,000）
    "min_super_total": 300000,  # 最低採用ライン
    "target_super_total": 500000,  # 目標ライン
    # 重複検出閾値
    "max_tfidf_similarity": 0.7,  # TF-IDF類似度
    "max_text_similarity": 0.6,  # テキスト類似度（同一年齢）
    # 具体性閾値
    "min_specificity": 2,  # 最低具体性スコア（埋め草検出）
}

# ==============================================================================
# 多様性目標
# ==============================================================================

DIVERSITY_TARGETS = {
    # カテゴリ分布目標（Gini係数）
    "max_category_gini": 0.3,
    # 年代分布目標
    "era_distribution": {
        "古代-中世": 0.10,  # ~1500
        "近世": 0.15,  # 1500-1800
        "近代": 0.25,  # 1800-1950
        "現代前期": 0.25,  # 1950-2000
        "現代後期": 0.25,  # 2000~
    },
    # カテゴリ分布目標
    "category_distribution": {
        "政治": 0.12,
        "ビジネス": 0.15,
        "科学": 0.12,
        "芸術": 0.15,
        "スポーツ": 0.15,
        "エンターテインメント": 0.12,
        "文学": 0.08,
        "音楽": 0.08,
        "その他": 0.03,
    },
    # 人物タイプ分布
    "person_type_distribution": {
        "REAL": 0.85,
        "FICTIONAL": 0.10,
        "MYTHOLOGICAL": 0.05,
    },
}

# ==============================================================================
# 創作検知シグナル
# ==============================================================================

FABRICATION_SIGNALS = [
    "具体的年号なし",
    "固有名詞1個以下",
    "「と言われている」多用",
    "「かもしれない」多用",
    "「らしい」多用",
    "検証可能な記録参照なし",
    "抽象的表現過多",
    "回顧的表現過多",
]

# ==============================================================================
# 生成時必須根拠
# ==============================================================================

REQUIRED_EVIDENCE = [
    "年号 (YYYY年)",
    "固有名詞 (作品名/イベント名/組織名)",
    "数値データ (記録/統計)",
]

# ==============================================================================
# 禁止パターン（メタ表現等）
# ==============================================================================

PROHIBITED_PATTERNS = [
    # メタ表現
    r"このエピソード",
    r"この物語",
    r"この話",
    r"読者",
    r"視聴者",
    # 未来予測
    r"になるでしょう",
    r"になるだろう",
    r"と予想される",
    # 曖昧表現
    r"ある日",
    r"ある時",
    r"いつか",
    # 過度な推測
    r"と思われる",
    r"ではないか",
    r"だったかもしれない",
]

# ==============================================================================
# 棄却理由コード
# ==============================================================================


class RejectionReason(Enum):
    """棄却理由の種類"""

    # 生成前チェック
    AGE_BOUNDARY_VIOLATION = "age_boundary"  # 年齢境界違反
    SAME_AGE_DUPLICATE = "same_age_duplicate"  # 同一年齢重複
    COOLDOWN_ACTIVE = "cooldown_active"  # クールダウン中
    WEEKLY_LIMIT_EXCEEDED = "weekly_limit"  # 週間上限超過
    # 生成後チェック
    LOW_FACTUAL_DENSITY = "low_factual_density"  # 事実密度不足
    LOW_GENERATION_QUALITY = "low_generation_quality"  # 生成品質不足
    LOW_COMPOSITE_SCORE = "low_composite"  # 統合スコア不足
    LOW_SUPER_TOTAL = "low_super_total"  # 超総合スコア不足
    HIGH_SIMILARITY = "high_similarity"  # 高類似度
    # ファクトチェック
    FACT_CHECK_FAILED = "fact_check_failed"  # ファクトチェック失敗
    FABRICATION_DETECTED = "fabrication_detected"  # 創作検知
    NO_EVIDENCE = "no_evidence"  # 根拠なし
    # パターンチェック
    PROHIBITED_PATTERN = "prohibited_pattern"  # 禁止パターン
    FILLER_DETECTED = "filler_detected"  # 埋め草検出（即棄却: score < 1）
    LOW_SPECIFICITY = "low_specificity"  # 具体性不足（リトライ可: score 1-2）
    # その他
    GENERATION_ERROR = "generation_error"  # 生成エラー
    MAX_RETRIES_EXCEEDED = "max_retries"  # リトライ上限


# ==============================================================================
# 設定データクラス
# ==============================================================================


@dataclass
class HybridConfig:
    """ハイブリッド生成システム設定"""

    # 戦略
    strategy: Strategy = Strategy.EPGEN_FIRST

    # パス
    master_csv: Path = field(default_factory=lambda: MASTER_CSV)
    backup_dir: Path = field(default_factory=lambda: BACKUP_DIR)
    logs_dir: Path = field(default_factory=lambda: LOGS_DIR)
    cache_dir: Path = field(default_factory=lambda: CACHE_DIR)

    # 生成設定
    target_count: int = 10
    dry_run: bool = True
    use_mock: bool = False  # True: モックアダプター使用（API不要）
    verbose: bool = False

    # ルール・閾値
    generation_rules: dict[str, Any] = field(default_factory=lambda: GENERATION_RULES.copy())
    quality_thresholds: dict[str, float] = field(default_factory=lambda: QUALITY_THRESHOLDS.copy())
    diversity_targets: dict[str, Any] = field(default_factory=lambda: DIVERSITY_TARGETS.copy())

    def __post_init__(self) -> None:
        """初期化後処理：ディレクトリ作成"""
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HybridConfig":
        """辞書から設定を生成"""
        if "strategy" in data and isinstance(data["strategy"], str):
            data["strategy"] = Strategy(data["strategy"])
        return cls(**data)
