#!/usr/bin/env python3
"""
PDCAガーディアンに客観性・具体性・教育的価値ルールを追加
RULE_161: 客観的事実主義
RULE_162: 具体的描写義務
RULE_163: 教育的価値確保
"""

import json
from datetime import datetime

# PDCAルールファイル読み込み
with open('pdca_rules.json', 'r', encoding='utf-8') as f:
    pdca_rules = json.load(f)

# RULE_161: 客観的事実主義
rule_161 = {
    "rule_id": "RULE_161",
    "name": "客観的事実主義",
    "description": "主観的感想・憶測・励ましを完全排除し、客観的事実のみでエピソードを構成",
    "category": "品質基準",
    "priority": "CRITICAL",
    "check_function": "check_objectivity",
    "violation_type": "SUBJECTIVITY_VIOLATION",
    "validation": "NGワードが含まれていないことを確認",
    "error_message": "主観的表現が検出されました",
    "prevention_measures": [
        "客観的事実のみで構成",
        "主観的感想の完全排除",
        "憶測・推測の禁止",
        "励まし文句の削除",
        "評価的形容詞の回避"
    ],
    "ng_words": [
        "素晴らしい", "感動", "勇気", "希望", "夢",
        "必ず", "きっと", "でしょう", "かもしれない",
        "与える", "与え続ける", "創造できます",
        "可能性が広がる", "未来を", "あなたも",
        "感銘", "称賛", "偉大", "輝かしい", "栄光"
    ],
    "historical_context": "2025年9月21日: ヘレン・ケラーエピソード比較により問題発覚",
    "examples": {
        "wrong": "この功績は多くの人々に勇気と感動を与え続けています",
        "correct": "この記録は現在も破られていない日本記録として残っている"
    },
    "implementation_notes": [
        "NGワードリストでの自動検出",
        "客観的事実の割合を95%以上に",
        "数値・日付・固有名詞を重視",
        "検証可能な情報のみ使用"
    ],
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.6"
}

# RULE_162: 具体的描写義務
rule_162 = {
    "rule_id": "RULE_162",
    "name": "具体的描写義務",
    "description": "場面が目に浮かぶレベルの詳細描写を義務化",
    "category": "品質基準",
    "priority": "CRITICAL",
    "check_function": "check_specificity",
    "violation_type": "SPECIFICITY_VIOLATION",
    "validation": "最低3つの具体的詳細が含まれることを確認",
    "error_message": "具体的描写が不足しています",
    "prevention_measures": [
        "5W1Hの明確な記載",
        "場所・時間・状況の具体化",
        "数値データの積極的活用",
        "固有名詞の使用",
        "感覚的描写の追加"
    ],
    "required_elements": {
        "minimum_details": 3,
        "should_include": ["いつ", "どこで", "誰が", "何を", "どのように"],
        "concrete_items": ["数値", "日付", "場所名", "人名", "作品名"]
    },
    "historical_context": "2025年9月21日: Water事件の詳細描写が模範例",
    "examples": {
        "wrong": "大学を卒業し、学士号を取得",
        "correct": "1904年6月、ラドクリフ大学の卒業式で、magna cum laude（優等）の成績で文学士号を授与され、聴衆2000人がスタンディングオベーション"
    },
    "implementation_notes": [
        "詳細情報データベースの拡充",
        "場面描写テンプレートの作成",
        "感覚的表現の追加",
        "時代背景の組み込み"
    ],
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.6"
}

# RULE_163: 教育的価値確保
rule_163 = {
    "rule_id": "RULE_163",
    "name": "教育的価値確保",
    "description": "歴史的意味・社会的影響を含む教育的価値の確保",
    "category": "品質基準",
    "priority": "CRITICAL",
    "check_function": "check_educational_value",
    "violation_type": "EDUCATIONAL_VALUE_VIOLATION",
    "validation": "なぜ重要かの客観的説明が含まれることを確認",
    "error_message": "教育的価値・歴史的意味の説明が不足",
    "prevention_measures": [
        "歴史的文脈の明示",
        "社会的影響の記載",
        "時代背景の説明",
        "普遍的原理の提示",
        "因果関係の明確化"
    ],
    "required_components": {
        "historical_context": "その時代における意味",
        "social_impact": "社会への影響",
        "universal_principle": "普遍的な教訓・原理",
        "causality": "原因と結果の関係"
    },
    "historical_context": "2025年9月21日: 学習原理の説明が模範例",
    "examples": {
        "wrong": "紅白歌合戦に出場した",
        "correct": "1951年の第2回紅白歌合戦出場は、戦後復興期の日本で女性歌手の社会的地位向上を象徴する出来事となり、後の女性アーティストの活躍の礎となった"
    },
    "implementation_notes": [
        "時代背景データベースの構築",
        "影響分析の自動化",
        "教育的観点の明示",
        "因果関係の論理的説明"
    ],
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.6"
}

# ルール追加
pdca_rules['rules'].extend([rule_161, rule_162, rule_163])

# メタデータ更新
pdca_rules['metadata']['objectivity_rules'] = {
    "added_date": datetime.now().strftime("%Y-%m-%d"),
    "version": "v5.6",
    "description": "客観性・具体性・教育的価値の3本柱",
    "rules": ["RULE_161", "RULE_162", "RULE_163"],
    "trigger": "ヘレン・ケラーエピソード比較問題"
}

# バージョン更新
pdca_rules['version'] = "5.6"
pdca_rules['last_updated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 更新履歴
pdca_rules['update_history'].append({
    "version": "5.6",
    "date": datetime.now().strftime("%Y-%m-%d"),
    "changes": [
        "RULE_161: 客観的事実主義ルール追加",
        "RULE_162: 具体的描写義務ルール追加",
        "RULE_163: 教育的価値確保ルール追加",
        "主観的表現の完全排除",
        "エピソード品質の抜本的改善"
    ]
})

# 保存
with open('pdca_rules.json', 'w', encoding='utf-8') as f:
    json.dump(pdca_rules, f, ensure_ascii=False, indent=2)

print("✅ PDCA Guardian ルール追加完了:")
print(f"   - RULE_161: 客観的事実主義")
print(f"   - RULE_162: 具体的描写義務")
print(f"   - RULE_163: 教育的価値確保")
print(f"   バージョン: {pdca_rules['version']}")

# ViolationType列挙型追加用
violation_types = """
    # RULE_161-163: 品質基準違反 (v5.6)
    SUBJECTIVITY_VIOLATION = "主観的表現違反"
    SPECIFICITY_VIOLATION = "具体性不足違反"
    EDUCATIONAL_VALUE_VIOLATION = "教育的価値不足違反"
"""

print("\n📝 ViolationType列挙型に以下を追加:")
print(violation_types)

# チェックメソッド例
check_methods = '''
def check_objectivity(self, episode_text: str) -> List[Dict]:
    """客観性チェック（RULE_161）"""
    violations = []
    ng_words = [
        "素晴らしい", "感動", "勇気", "希望", "夢",
        "必ず", "きっと", "でしょう", "かもしれない",
        "与える", "与え続ける", "創造できます",
        "可能性が広がる", "未来を", "あなたも"
    ]

    for word in ng_words:
        if word in episode_text:
            violations.append({
                'rule_id': 'RULE_161',
                'type': ViolationType.SUBJECTIVITY_VIOLATION.value,
                'message': f'主観的表現「{word}」が検出されました',
                'severity': 'critical'
            })
    return violations

def check_specificity(self, episode_text: str) -> List[Dict]:
    """具体性チェック（RULE_162）"""
    violations = []

    # 数値、日付、固有名詞の数をカウント
    import re
    numbers = len(re.findall(r'\d+', episode_text))
    dates = len(re.findall(r'\d{4}年', episode_text))

    if numbers + dates < 3:
        violations.append({
            'rule_id': 'RULE_162',
            'type': ViolationType.SPECIFICITY_VIOLATION.value,
            'message': f'具体的詳細が不足（数値:{numbers}個、日付:{dates}個）',
            'severity': 'critical'
        })
    return violations

def check_educational_value(self, episode_text: str) -> List[Dict]:
    """教育的価値チェック（RULE_163）"""
    violations = []

    # 因果関係や影響を示すキーワードをチェック
    educational_keywords = [
        "この結果", "これにより", "影響", "意味", "背景",
        "当時", "史上", "初めて", "転換点", "きっかけ"
    ]

    if not any(keyword in episode_text for keyword in educational_keywords):
        violations.append({
            'rule_id': 'RULE_163',
            'type': ViolationType.EDUCATIONAL_VALUE_VIOLATION.value,
            'message': '歴史的意味・社会的影響の説明が不足',
            'severity': 'warning'
        })
    return violations
'''

print("\n📝 チェックメソッド実装例:")
print(check_methods)

print("\n🎯 実装ガイドライン:")
print("1. 全ての主観的フレーズを削除")
print("2. encouragementsリストを廃止")
print("3. category_phrasesを客観的記述に変更")
print("4. データベースに詳細情報を追加")
print("5. 5W1Hを明確に記載")
print("6. 歴史的文脈・社会的影響を含める")