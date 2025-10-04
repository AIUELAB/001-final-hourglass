#!/usr/bin/env python3
"""
RULE_171追加スクリプト - 括弧内ワード重複防止
Add RULE_171: Prevent Bracket Word Duplication in Episode Text

括弧内に表示されるグループ名・作品名がエピソード本文に
重複して出現しないようにするルールを追加します。

Created: 2025-10-02
"""

import json
from datetime import datetime
from pathlib import Path


def add_rule_171():
    """RULE_171を追加"""

    rules_file = Path("rules_registry.json")

    # 既存ルールをロード
    with open(rules_file, 'r', encoding='utf-8') as f:
        rules = json.load(f)

    # RULE_171の定義
    rule_171 = {
        "rule_id": "RULE_171",
        "name": "括弧内ワード重複防止",
        "description": """名前の横に括弧が付いた場合、その括弧内ワードはエピソード本文に使用されないこと。

【目的】
- グループメンバーや架空キャラクターの名前表示時に、括弧内のグループ名/作品名がエピソード本文に重複出現することを防ぐ
- 視覚的な冗長性を排除し、読みやすさを向上させる

【適用対象】
1. **グループメンバー**
   - 例: `あなたと同じ30歳のとき、髙比良くるま(令和ロマン)は`
   - エピソード本文に「令和ロマン」という文字列を含んではいけない

2. **架空キャラクター**
   - 例: `あなたと同じ19歳のとき、モンキー・D・ルフィ（ONE PIECE）は`
   - エピソード本文に「ONE PIECE」という文字列を含んではいけない

【チェックロジック】
```python
def check_bracket_word_duplication(person_name, group_or_work_name, episode_text):
    # 括弧内ワードがエピソード本文に存在するか
    if group_or_work_name and group_or_work_name in episode_text:
        return {
            'valid': False,
            'violation': 'RULE_171',
            'message': f'括弧内ワード「{group_or_work_name}」がエピソード本文に重複'
        }
    return {'valid': True}
```

【違反例】
❌ **違反**: `YOSHIKI(X JAPAN)` の場合
```
あなたと同じ23歳のとき、YOSHIKI(X JAPAN)は
XJAPANとして「BLUEBLOOD」でメジャーデビューを果たした。
                ^^^^^^ 違反！括弧内「X JAPAN」と重複
```

✅ **正解**:
```
あなたと同じ23歳のとき、YOSHIKI(X JAPAN)は
「BLUEBLOOD」でメジャーデビューを果たした。
ビジュアル系ロックという新ジャンルを確立...
```

【適用タイミング】
- エピソード生成時の最終検証
- 既存エピソードの修正時
- Episode Guardian による自動チェック

【関連ルール】
- ENTITY_TYPE_001: グループ名の個人誤登録防止
- FORMAT_001: エピソード形式統一
""",
        "category": "episode_content",
        "priority": 1,
        "status": "active",
        "tags": [
            "episode_format",
            "group_name",
            "work_title",
            "duplication_prevention",
            "readability"
        ],
        "source_file": "episode_guardian.py",
        "function_name": "check_bracket_word_duplication",
        "version": "v1.0.0",
        "related_rules": [
            "ENTITY_TYPE_001",
            "FORMAT_001"
        ],
        "replaces": None,
        "replaced_by": None,
        "examples": [
            {
                "type": "violation",
                "person_name": "YOSHIKI",
                "group_name": "X JAPAN",
                "episode_text": "YOSHIKIはXJAPANとして「BLUEBLOOD」でメジャーデビュー...",
                "reason": "括弧内「X JAPAN」がエピソード本文に「XJAPAN」として重複"
            },
            {
                "type": "violation",
                "person_name": "モンキー・D・ルフィ",
                "work_title": "ONE PIECE",
                "episode_text": "ルフィはONE PIECEの主人公として冒険を始めた...",
                "reason": "括弧内「ONE PIECE」がエピソード本文に重複"
            },
            {
                "type": "valid",
                "person_name": "YOSHIKI",
                "group_name": "X JAPAN",
                "episode_text": "「BLUEBLOOD」でメジャーデビューを果たした。ビジュアル系ロックという新ジャンルを確立...",
                "reason": "括弧内「X JAPAN」はエピソード本文に出現していない"
            }
        ],
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }

    # ルールを追加
    rules["RULE_171"] = rule_171

    # ファイルに保存
    with open(rules_file, 'w', encoding='utf-8') as f:
        json.dump(rules, f, ensure_ascii=False, indent=2)

    print("✅ RULE_171を追加しました")
    print(f"   ルールID: {rule_171['rule_id']}")
    print(f"   名前: {rule_171['name']}")
    print(f"   カテゴリ: {rule_171['category']}")
    print(f"   優先度: {rule_171['priority']}")
    print(f"   タグ: {', '.join(rule_171['tags'])}")

    # 統計更新
    total_rules = len(rules)
    active_rules = sum(1 for r in rules.values() if r.get('status') == 'active')

    print(f"\n📊 ルール統計:")
    print(f"   総ルール数: {total_rules}")
    print(f"   アクティブ: {active_rules}")

    return rule_171


def update_episode_guardian_config():
    """episode_guardian_config.jsonを更新"""

    config_file = Path("episode_guardian_config.json")

    with open(config_file, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # RULE_171をepisode_contentカテゴリに追加
    if "RULE_171" not in config["unified_rules"]["categories"]["episode_content"]:
        config["unified_rules"]["categories"]["episode_content"].append("RULE_171")
        config["unified_rules"]["total_rules"] += 1

    with open(config_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("\n✅ episode_guardian_config.jsonを更新しました")


def main():
    """メイン実行"""
    print("="*70)
    print("📝 RULE_171追加: 括弧内ワード重複防止")
    print("="*70)

    # RULE_171を追加
    rule_171 = add_rule_171()

    # Episode Guardian設定を更新
    update_episode_guardian_config()

    print("\n" + "="*70)
    print("✅ RULE_171の追加が完了しました")
    print("="*70)

    print("\n次のステップ:")
    print("1. episode_guardian.pyにcheck_bracket_word_duplication()関数を実装")
    print("2. 既存エピソードをRULE_171でチェック")
    print("3. 違反エピソードを修正")


if __name__ == "__main__":
    main()
