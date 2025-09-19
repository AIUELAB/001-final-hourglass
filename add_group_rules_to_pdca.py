#!/usr/bin/env python3
"""
PDCAガーディアンにグループ関連ルールを追加
"""

import json
from datetime import datetime
from pathlib import Path

def add_group_rules():
    """グループ関連ルールの追加"""
    print("="*60)
    print("🛡️ PDCAガーディアンへのグループルール追加")
    print("="*60)
    
    # project_memory.json読み込み
    memory_file = Path("project_memory.json")
    if not memory_file.exists():
        print("❌ project_memory.jsonが見つかりません")
        return False
    
    with open(memory_file, 'r', encoding='utf-8') as f:
        memory = json.load(f)
    
    # 新しいルールを追加
    new_rules = [
        {
            "id": "RULE_050",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "P003218「嵐」の問題から学習",
            "rule": "グループ名と個人名を正しく区別すること",
            "priority": "CRITICAL",
            "context": "「嵐」「SMAP」「TOKIO」などのグループ名を個人として扱わない",
            "violations": [],
            "enforcement": "entity_typeフィールドでperson/group/fictional_characterを正確に分類",
            "group_detection": {
                "known_groups": [
                    "嵐", "SMAP", "TOKIO", "関ジャニ∞", "King & Prince", 
                    "SixTONES", "Snow Man", "NEWS", "KAT-TUN", "Hey! Say! JUMP",
                    "Kis-My-Ft2", "A.B.C-Z", "ジャニーズWEST", "なにわ男子",
                    "AKB48", "乃木坂46", "櫻坂46", "日向坂46", "NMB48", "SKE48",
                    "DREAMS COME TRUE", "Mr.Children", "サザンオールスターズ",
                    "EXILE", "三代目 J SOUL BROTHERS", "GENERATIONS",
                    "BTS", "BLACKPINK", "TWICE", "Stray Kids", "SEVENTEEN"
                ]
            }
        },
        {
            "id": "RULE_051",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "グループメンバー管理の必要性",
            "rule": "グループメンバーは独立した個人として管理",
            "priority": "HIGH",
            "context": "グループのメンバーは個別のIDを持ち、group_idで親グループと関連付ける",
            "violations": [],
            "enforcement": "メンバーはperson_id_suffix形式（例：P003218_001）で管理",
            "member_management": {
                "id_format": "{group_id}_{member_number}",
                "required_fields": ["group_id", "group_name", "member_name"],
                "link_to_parent": True
            }
        },
        {
            "id": "RULE_052",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "source": "知名度評価の精度向上",
            "rule": "グループと個人メンバーで異なる評価基準を適用",
            "priority": "HIGH",
            "context": "グループ全体の知名度と個人メンバーの知名度は異なる",
            "violations": [],
            "enforcement": "グループは集団としての知名度、メンバーは個人としての知名度を評価",
            "evaluation_rules": {
                "group_minimum_score": 7.0,
                "member_base_score": 6.0,
                "famous_group_bonus": 2.0
            }
        }
    ]
    
    # 既存のルールに追加
    for rule in new_rules:
        # 既に同じIDのルールが存在するかチェック
        existing_ids = [r.get('id') for r in memory.get('permanent_rules', [])]
        if rule['id'] not in existing_ids:
            memory['permanent_rules'].append(rule)
            print(f"✅ {rule['id']}: {rule['rule']}")
        else:
            print(f"⚠️ {rule['id']}は既に存在します")
    
    # failed_patternsに追加
    new_failure = {
        "id": "FAIL_GROUP_001",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "pattern": "グループを個人として扱う",
        "description": "「嵐」のようなグループ名を個人名として処理",
        "consequence": "グループメンバーの情報が失われ、データ構造が不整合",
        "prevention": "entity_typeフィールドの適切な使用とグループ検出ロジックの実装"
    }
    
    if 'failed_patterns' not in memory:
        memory['failed_patterns'] = []
    
    failure_ids = [f.get('id') for f in memory['failed_patterns']]
    if new_failure['id'] not in failure_ids:
        memory['failed_patterns'].append(new_failure)
        print(f"✅ 失敗パターン追加: {new_failure['id']}")
    
    # improvement_logに追加
    improvement = {
        "date": datetime.now().isoformat(),
        "type": "ルール追加",
        "description": "グループ/個人判定ルール（RULE_050-052）を追加",
        "priority": "CRITICAL",
        "reason": "P003218「嵐」がグループではなく個人として誤分類される問題を発見",
        "impact": "今後グループと個人を正確に区別し、適切なデータ構造を維持"
    }
    
    if 'improvement_log' not in memory:
        memory['improvement_log'] = []
    
    memory['improvement_log'].append(improvement)
    print(f"✅ 改善ログ追加")
    
    # メタデータ更新
    memory['metadata']['last_updated'] = datetime.now().isoformat()
    
    # 保存
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
    
    print("\n💾 project_memory.json更新完了")
    print(f"📚 総ルール数: {len(memory['permanent_rules'])}")
    print(f"❌ 失敗パターン数: {len(memory['failed_patterns'])}")
    
    return True

if __name__ == "__main__":
    success = add_group_rules()
    if success:
        print("\n✅ グループルールの追加完了")
    else:
        print("\n❌ グループルール追加失敗")