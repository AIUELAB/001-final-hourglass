"""
8軸スコアカラム名の一元管理

Phase 28: CSVフィールド英語化
- CSVカラム名を英語に統一
- ダッシュボード表示は日本語維持
"""

# CSV出力用（英語）- 内部キー → CSVカラム名
AXIS_COLUMNS = {
    "memorability": "memorability_score",
    "empathy": "empathy_score",
    "surprise": "surprise_score",
    "generation_quality": "generation_quality_score",
    "educational_value": "educational_value",
    "story_quality": "story_quality",
    "factual_density": "factual_density",
    "iconic": "iconic_score",
}

# 日本語表示用（ダッシュボード等）- 英語カラム名 → 日本語ラベル
AXIS_LABELS_JA = {
    "memorability_score": "記憶性スコア",
    "empathy_score": "共感性スコア",
    "surprise_score": "意外性スコア",
    "generation_quality_score": "生成品質スコア",
    "educational_value": "教育的価値",
    "story_quality": "ストーリー品質",
    "factual_density": "事実密度",
    "iconic_score": "象徴性スコア",
}

# 後方互換（旧日本語→新英語）
LEGACY_COLUMN_MAP = {
    "記憶性スコア": "memorability_score",
    "共感性スコア": "empathy_score",
    "意外性スコア": "surprise_score",
    "生成品質スコア": "generation_quality_score",
    "教育的価値": "educational_value",
    "ストーリー品質": "story_quality",
    "事実密度": "factual_density",
    "象徴性スコア": "iconic_score",
}

# 英語カラム名リスト（順序付き）
AXIS_SCORE_COLUMNS = [
    "memorability_score",
    "empathy_score",
    "surprise_score",
    "generation_quality_score",
    "educational_value",
    "story_quality",
    "factual_density",
    "iconic_score",
]

# ダッシュボード用短縮キーマッピング
DASHBOARD_SHORT_KEYS = {
    "memorability_score": "mem",
    "empathy_score": "emp",
    "surprise_score": "sur",
    "generation_quality_score": "gen",
    "educational_value": "edu",
    "story_quality": "story",
    "factual_density": "fact",
    "iconic_score": "icon",
}
