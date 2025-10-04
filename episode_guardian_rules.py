#!/usr/bin/env python3
"""
EpisodeGuardianルール定義

すべてのエピソード検証ルールを一元管理

著者: Claude Code
日付: 2025-10-01
バージョン: 1.0.0
"""

from typing import Dict, Callable
from datetime import datetime

# ルールバージョン管理
RULE_VERSION = "1.2.0"
RULE_LAST_UPDATED = "2025-10-01"

# 変更履歴
RULE_CHANGELOG = {
    "1.2.0": {
        "date": "2025-10-01",
        "changes": [
            "CONTENT_005強化: 累積成果パターン追加（6パターン）",
            "検出パターン追加: 回数表現、本数表現、配信・再生数、紅白・映画等"
        ],
        "reason": "EP054累積成果混入問題（配信200万、紅白3回等）の検出強化",
        "author": "Claude Code",
        "affected_episodes": ["EP054"],
        "technical_details": "CONTENT_005のforbidden_patternsに6つの正規表現を追加し、累積成果を明示的な時間マーカーなしで記述するパターンに対応"
    },
    "1.1.0": {
        "date": "2025-10-01",
        "changes": [
            "CONTENT_004追加: 定番エピソード要件（WARNING）",
            "CONTENT_005追加: 年齢時点での事実のみ（CRITICAL）",
            "FORMAT_005追加: 相対的時間表現の検出（WARNING）"
        ],
        "reason": "EP025/EP028未来の成果混入問題の再発防止",
        "author": "Claude Code",
        "affected_episodes": ["EP025", "EP028"]
    },
    "1.0.0": {
        "date": "2025-10-01",
        "changes": [
            "Entity Typeルール追加（ENTITY_TYPE_001-003）",
            "グループ名ブラックリスト実装",
            "unified_validation_systemとの統合",
            "グループ特有表現検出ルール",
            "個人名パターンマッチングルール"
        ],
        "reason": "EP010グループ混入問題の再発防止",
        "author": "Claude Code"
    }
}


class RuleCategory:
    """ルールカテゴリ"""
    ENTITY_TYPE = "ENTITY_TYPE"  # エンティティタイプ関連
    FORMAT = "FORMAT"            # 形式ルール
    CONTENT = "CONTENT"          # 内容ルール
    PDCA = "PDCA"                # PDCAルール


class RuleSeverity:
    """ルール違反の重要度"""
    CRITICAL = "CRITICAL"  # 即座に失格
    WARNING = "WARNING"    # 警告、但し合格可能
    INFO = "INFO"          # 情報のみ


# ================================================
# Entity Typeルール（グループ混入防止）
# ================================================

ENTITY_TYPE_RULES = {
    "ENTITY_TYPE_001": {
        "name": "グループ名ブラックリスト",
        "category": RuleCategory.ENTITY_TYPE,
        "severity": RuleSeverity.CRITICAL,
        "description": "person_nameが既知のグループ名リストに含まれていないか確認",
        "rationale": "データベースは個人のみを扱う設計のため、グループは絶対に登録不可",
        "check_function": "is_not_in_known_groups",
        "error_message": "{person_name}はグループです。個人のみ登録可能です。",
        "suggestions": [
            "個人の名前のみ使用してください",
            "グループメンバーの個人名を使用することを検討してください"
        ],
        "examples": {
            "fail": ["サカナクション", "X JAPAN", "嵐"],
            "pass": ["羽生結弦", "YOSHIKI", "櫻井翔"]
        }
    },

    "ENTITY_TYPE_002": {
        "name": "グループ特有表現検出",
        "category": RuleCategory.ENTITY_TYPE,
        "severity": RuleSeverity.WARNING,
        "description": "エピソードテキストにグループ関連表現が複数含まれていないか確認",
        "rationale": "グループ関連表現が多い場合、グループ自体の話である可能性が高い",
        "keywords": ["結成", "メンバー", "バンド", "人組", "グループ", "デビュー", "コンビ", "ユニット", "チーム"],
        "threshold": 2,  # 2つ以上の表現で警告
        "exceptions": [
            "を結成",  # 個人がグループを結成した話
            "と結成"   # 個人が誰かとグループを作った話
        ],
        "error_message": "グループ関連表現を複数検出: {keywords}",
        "suggestions": [
            "個人の話であることを明確にしてください",
            "グループではなく個人の業績を記述してください"
        ]
    },

    "ENTITY_TYPE_003": {
        "name": "個人名パターンマッチング",
        "category": RuleCategory.ENTITY_TYPE,
        "severity": RuleSeverity.WARNING,
        "description": "person_nameが個人名パターンに一致するか確認",
        "rationale": "個人名の典型的なパターンに一致しない場合、グループ名の可能性",
        "patterns": {
            "japanese": "漢字2-5文字",
            "western": "スペース区切りの2単語（大文字開始）",
            "katakana": "カタカナのみ6文字以内"
        },
        "error_message": "{person_name}は個人名パターンに一致しません",
        "suggestions": [
            "日本人名または海外人名のパターンを確認してください",
            "グループ名ではないことを確認してください"
        ]
    }
}


# ================================================
# 形式ルール（文字数、定型文等）
# ================================================

FORMAT_RULES = {
    "FORMAT_001": {
        "name": "文字数制限",
        "category": RuleCategory.FORMAT,
        "severity": RuleSeverity.CRITICAL,
        "description": "エピソードテキストが130-250文字の範囲内か確認",
        "min_length": 130,
        "max_length": 250,
        "error_message": "文字数が範囲外です（{count}文字）。130-250文字にしてください。",
        "suggestions": [
            "具体的な数値や固有名詞を追加してください",
            "冗長な表現を削除してください"
        ]
    },

    "FORMAT_002": {
        "name": "定型文禁止",
        "category": RuleCategory.FORMAT,
        "severity": RuleSeverity.CRITICAL,
        "description": "定型文や型にはまった表現が含まれていないか確認",
        "forbidden_patterns": [
            "あなたと同じ年齢で",
            "あなたと同年代の",
            "～という偉業を成し遂げた",
            "～という快挙を達成した"
        ],
        "error_message": "定型文が含まれています: {pattern}",
        "suggestions": [
            "具体的な表現に変更してください",
            "年齢は「あなたと同じ○歳のとき」を使用してください"
        ]
    },

    "FORMAT_003": {
        "name": "年号・日付禁止",
        "category": RuleCategory.FORMAT,
        "severity": RuleSeverity.CRITICAL,
        "description": "年号や日付が含まれていないか確認",
        "forbidden_patterns": [
            r"\d{4}年",  # 2014年
            r"令和\d+年",
            r"平成\d+年",
            r"\d+月\d+日"
        ],
        "error_message": "年号・日付が含まれています: {match}",
        "suggestions": [
            "年号を削除してください",
            "相対的な時間表現を使用してください"
        ]
    },

    "FORMAT_004": {
        "name": "主観表現禁止",
        "category": RuleCategory.FORMAT,
        "severity": RuleSeverity.CRITICAL,
        "description": "主観的な表現が含まれていないか確認",
        "forbidden_words": [
            "圧倒的", "素晴らしい", "驚異的", "劇的",
            "感動的", "伝説的", "奇跡的", "衝撃的"
        ],
        "error_message": "主観的表現が含まれています: {word}",
        "suggestions": [
            "客観的な事実のみを記述してください",
            "具体的な数値データに置き換えてください"
        ]
    },

    "FORMAT_005": {
        "name": "相対的時間表現の検出",
        "category": RuleCategory.FORMAT,
        "severity": RuleSeverity.WARNING,
        "description": "相対的時間表現（〇年後、〇年で）を検出",
        "rationale": "時点が明確でない表現は年齢時点の混乱を招く",
        "pattern": r'\d+[年ヶ月日](?:で|後|以内)',
        "error_message": "相対的時間表現を検出: {matches}",
        "suggestions": [
            "具体的な時点での事実を記述してください",
            "相対的時間表現は削除してください"
        ],
        "examples": {
            "fail": ["5年で2500万人に成長", "3年後には", "10年以内に"],
            "pass": ["初週で1.2万ドルの売上", "2ヶ月で週2万ドル達成"]
        }
    }
}


# ================================================
# 内容ルール（具体性、事実確認）
# ================================================

CONTENT_RULES = {
    "CONTENT_001": {
        "name": "数値データ必須",
        "category": RuleCategory.CONTENT,
        "severity": RuleSeverity.CRITICAL,
        "description": "エピソードテキストに具体的な数値が含まれているか確認",
        "min_numbers": 1,
        "error_message": "具体的な数値データがありません",
        "suggestions": [
            "年齢、金額、数量等の具体的な数値を追加してください",
            "記録や達成値を数値で表現してください"
        ]
    },

    "CONTENT_002": {
        "name": "固有名詞必須",
        "category": RuleCategory.CONTENT,
        "severity": RuleSeverity.CRITICAL,
        "description": "エピソードテキストに固有名詞が含まれているか確認",
        "min_proper_nouns": 1,
        "error_message": "固有名詞がありません",
        "suggestions": [
            "大会名、作品名、組織名等の固有名詞を追加してください",
            "具体的な場所や人物名を記述してください"
        ]
    },

    "CONTENT_003": {
        "name": "重複年齢禁止",
        "category": RuleCategory.CONTENT,
        "severity": RuleSeverity.CRITICAL,
        "description": "同じ年齢が複数回記載されていないか確認",
        "error_message": "年齢が重複しています: {age}歳",
        "suggestions": [
            "各年齢は1回のみ記載してください",
            "冒頭の「あなたと同じ○歳のとき」で年齢を示してください"
        ]
    },

    "CONTENT_004": {
        "name": "定番エピソード要件",
        "category": RuleCategory.CONTENT,
        "severity": RuleSeverity.WARNING,
        "description": "有名人の最も知られている定番エピソードを選択",
        "rationale": "ユーザーが共感しやすく、文化的インパクトが大きいエピソードが必須",
        "iconic_episodes": {
            "前澤友作": ["ZOZOTOWN", "開設", "売却"],
            "又吉直樹": ["火花", "芥川賞", "芥川龍之介賞"],
            "ジェフ・ベゾス": ["Amazon", "創業", "ガレージ"],
            "スティーブ・ジョブズ": ["Apple", "iPhone", "Macintosh"],
            "イーロン・マスク": ["Tesla", "SpaceX", "PayPal"],
            "星野源": ["逃げるは恥だが役に立つ", "逃げ恥", "恋"]
        },
        "error_message": "{person_name}の定番エピソードではありません。定番キーワード: {keywords}",
        "suggestions": [
            "最も有名なエピソードを選択してください",
            "文化的インパクトが大きい出来事を優先してください",
            "一般的な認知度が高いエピソードに変更してください"
        ],
        "examples": {
            "pass": [
                "前澤友作 → ZOZOTOWN開設",
                "又吉直樹 → 『火花』芥川賞受賞",
                "ジェフ・ベゾス → Amazon創業"
            ],
            "fail": [
                "前澤友作 → スタートトゥデイ設立（一般認知度低い）",
                "又吉直樹 → ピース結成（芥川賞ほど有名ではない）"
            ]
        }
    },

    "CONTENT_005": {
        "name": "年齢時点での事実のみ",
        "category": RuleCategory.CONTENT,
        "severity": RuleSeverity.CRITICAL,
        "description": "エピソード内に未来の成果や後日談が含まれていないか確認",
        "rationale": "ユーザーと有名人の『同じ年齢時』比較が目的。未来の成果はノイズ",
        "forbidden_patterns": [
            r'後に',
            r'その後',
            r'\d+年後',
            r'\d+年で',
            r'\d+ヶ月後',
            r'最終的に',
            r'やがて',
            r'続く',
            r'累計\d+',
            r'時価総額\d+',
            # EP054対策: 累積成果パターンの検出
            r'\d+回(?:出場|受賞|獲得|達成)',
            r'\d+本(?:出演|制作|公開)',
            r'(?:配信|ダウンロード)\s*\d+(?:万|億)',
            r'(?:YouTube|再生|視聴)\s*\d+億',
            r'紅白.*?\d+回',
            r'映画.*?\d+本'
        ],
        "error_message": "年齢時点外の未来の成果が含まれています: {matches}",
        "suggestions": [
            "その年齢で実際に起きた事実のみを記述してください",
            "未来の成果や後日談は削除してください",
            "年齢時点での具体的な数値に限定してください"
        ],
        "examples": {
            "fail": [
                "後にファッション通販ZOZOTOWNへと展開",
                "その後、『火花』で芥川賞を受賞し累計300万部",
                "5年で2500万人に成長",
                "時価総額1兆円企業に成長させ",
                "続く『劇場』も50万部のベストセラー",
                "配信200万ダウンロード、YouTube再生2億回",  # EP054
                "紅白歌合戦3回出場",  # EP054
                "俳優として映画20本出演"  # EP054
            ],
            "pass": [
                "初週で1.2万ドルの売上を達成",
                "2ヶ月後には週2万ドル達成（具体的期間内）",
                "M-1グランプリで準優勝し賞金500万円を獲得"
            ]
        }
    }
}


# ================================================
# すべてのルールを統合
# ================================================

ALL_RULES = {
    **ENTITY_TYPE_RULES,
    **FORMAT_RULES,
    **CONTENT_RULES
}


# ================================================
# ルール検索・管理関数
# ================================================

def get_rule(rule_id: str) -> Dict:
    """
    ルールIDからルール定義を取得

    Args:
        rule_id: ルールID（例: "ENTITY_TYPE_001"）

    Returns:
        ルール定義の辞書
    """
    return ALL_RULES.get(rule_id, {})


def get_rules_by_category(category: str) -> Dict[str, Dict]:
    """
    カテゴリ別にルールを取得

    Args:
        category: ルールカテゴリ（例: "ENTITY_TYPE"）

    Returns:
        カテゴリに属するルールの辞書
    """
    return {
        rule_id: rule
        for rule_id, rule in ALL_RULES.items()
        if rule.get("category") == category
    }


def get_rules_by_severity(severity: str) -> Dict[str, Dict]:
    """
    重要度別にルールを取得

    Args:
        severity: 重要度（例: "CRITICAL"）

    Returns:
        指定重要度のルールの辞書
    """
    return {
        rule_id: rule
        for rule_id, rule in ALL_RULES.items()
        if rule.get("severity") == severity
    }


def get_critical_rules() -> Dict[str, Dict]:
    """CRITICALルールのみを取得"""
    return get_rules_by_severity(RuleSeverity.CRITICAL)


def list_all_rule_ids() -> list:
    """すべてのルールIDをリスト化"""
    return list(ALL_RULES.keys())


def get_rule_count() -> Dict[str, int]:
    """ルール数の統計"""
    return {
        "total": len(ALL_RULES),
        "entity_type": len(get_rules_by_category(RuleCategory.ENTITY_TYPE)),
        "format": len(get_rules_by_category(RuleCategory.FORMAT)),
        "content": len(get_rules_by_category(RuleCategory.CONTENT)),
        "critical": len(get_critical_rules())
    }


# ================================================
# ルール追加時のチェックリスト
# ================================================

RULE_ADDITION_CHECKLIST = [
    "✓ ルールIDを採番した（CATEGORY_XXX形式）",
    "✓ nameを設定した（日本語の簡潔な名前）",
    "✓ categoryを設定した（ENTITY_TYPE/FORMAT/CONTENT/PDCA）",
    "✓ severityを設定した（CRITICAL/WARNING/INFO）",
    "✓ descriptionを記述した（ルールの説明）",
    "✓ rationaleを記述した（ルールの根拠・理由）",
    "✓ error_messageを設定した（エラーメッセージ）",
    "✓ suggestionsを設定した（改善提案）",
    "✓ examplesを追加した（合格例・不合格例）",
    "✓ CHANGELOGに追加した",
    "✓ テストケースを作成した"
]


if __name__ == "__main__":
    # デモ実行
    print("="*80)
    print("EpisodeGuardianルール定義")
    print("="*80 + "\n")

    print(f"ルールバージョン: {RULE_VERSION}")
    print(f"最終更新日: {RULE_LAST_UPDATED}\n")

    # ルール数の統計
    stats = get_rule_count()
    print("ルール数の統計:")
    print(f"  総数: {stats['total']}件")
    print(f"  Entity Type: {stats['entity_type']}件")
    print(f"  Format: {stats['format']}件")
    print(f"  Content: {stats['content']}件")
    print(f"  CRITICAL: {stats['critical']}件")
    print()

    # Entity Typeルールの詳細
    print("="*80)
    print("Entity Typeルール（グループ混入防止）")
    print("="*80 + "\n")

    for rule_id, rule in ENTITY_TYPE_RULES.items():
        print(f"{rule_id}: {rule['name']}")
        print(f"  重要度: {rule['severity']}")
        print(f"  説明: {rule['description']}")
        print(f"  根拠: {rule['rationale']}")
        print()

    # 変更履歴
    print("="*80)
    print("変更履歴")
    print("="*80 + "\n")

    for version, changelog in RULE_CHANGELOG.items():
        print(f"バージョン {version} ({changelog['date']})")
        print(f"  理由: {changelog['reason']}")
        print(f"  変更内容:")
        for change in changelog['changes']:
            print(f"    - {change}")
        print()
