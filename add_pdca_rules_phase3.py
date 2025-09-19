#!/usr/bin/env python3
"""
PDCAガーディアンルール追加 - フェーズ3
グループ/団体登録禁止とWikipedia確認ルール
"""

import json
from datetime import datetime
from pathlib import Path
import logging

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_project_memory():
    """プロジェクトメモリの読み込み"""
    memory_file = Path("project_memory.json")
    
    if memory_file.exists():
        with open(memory_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return {
            "pdca_guardian_rules": [],
            "quality_gates": [],
            "validation_history": []
        }


def add_new_rules(memory):
    """新しいPDCAルールを追加"""
    
    new_rules = [
        {
            "id": "RULE_065",
            "rule": "団体・グループ・バンド・コンビ名の登録禁止：個人データベースのため集合体は収録しない",
            "category": "data_integrity",
            "priority": "CRITICAL",
            "created_at": datetime.now().isoformat(),
            "enforcement": "automatic",
            "validation": "entity_type != 'group'",
            "error_message": "グループ/団体は登録できません。メンバー個人として登録してください。"
        },
        {
            "id": "RULE_066",
            "rule": "entity_type='group'の使用禁止：グループエンティティタイプは廃止",
            "category": "data_structure",
            "priority": "CRITICAL",
            "created_at": datetime.now().isoformat(),
            "enforcement": "automatic",
            "validation": "entity_type in ['person', 'fictional_character']",
            "error_message": "entity_typeは'person'または'fictional_character'のみ使用可能です。"
        },
        {
            "id": "RULE_067",
            "rule": "個人のみ登録可（芸名/活動名OK）：実在個人または架空キャラクターのみ",
            "category": "data_quality",
            "priority": "HIGH",
            "created_at": datetime.now().isoformat(),
            "enforcement": "automatic",
            "validation": "is_individual_entity",
            "error_message": "個人またはキャラクターのみ登録可能です。"
        },
        {
            "id": "RULE_068",
            "rule": "グループメンバーは個人として登録、括弧付き団体名表記：例 'YOSHIKI (X JAPAN)'",
            "category": "naming_convention",
            "priority": "HIGH",
            "created_at": datetime.now().isoformat(),
            "enforcement": "manual",
            "validation": "check_band_member_format",
            "example": "person_name: 'YOSHIKI', person_name_display: 'YOSHIKI (X JAPAN)'",
            "error_message": "バンドメンバーはperson_name_displayに括弧付きでグループ名を記載してください。"
        },
        {
            "id": "RULE_069",
            "rule": "Wikipedia未掲載かつ実在確認不可の人物はスコア0：存在しない人物の排除",
            "category": "data_validation",
            "priority": "CRITICAL",
            "created_at": datetime.now().isoformat(),
            "enforcement": "automatic",
            "validation": "wikipedia_exists OR other_proof_exists OR set_score_zero",
            "error_message": "Wikipedia未掲載かつ実在確認不可の人物はname_recognition=0に設定されます。"
        },
        {
            "id": "RULE_070",
            "rule": "定期的なWikipedia存在確認の実施：データ品質の継続的検証",
            "category": "quality_assurance",
            "priority": "MEDIUM",
            "created_at": datetime.now().isoformat(),
            "enforcement": "scheduled",
            "frequency": "monthly",
            "validation": "run_wikipedia_validation",
            "error_message": "定期的なWikipedia存在確認が必要です。"
        }
    ]
    
    # 既存のルールに追加
    existing_ids = {rule['id'] for rule in memory.get('pdca_guardian_rules', [])}
    
    for rule in new_rules:
        if rule['id'] not in existing_ids:
            memory['pdca_guardian_rules'].append(rule)
            logger.info(f"✅ ルール追加: {rule['id']} - {rule['rule'][:50]}...")
        else:
            logger.info(f"⏭️ スキップ（既存）: {rule['id']}")
    
    return memory


def add_quality_gates(memory):
    """品質ゲートの追加・更新"""
    
    new_gates = [
        {
            "id": "GATE_008",
            "name": "グループエンティティ検出",
            "check": "entity_type != 'group'",
            "severity": "CRITICAL",
            "action": "reject",
            "message": "グループエンティティは許可されません"
        },
        {
            "id": "GATE_009",
            "name": "Wikipedia存在確認",
            "check": "wikipedia_validation_passed",
            "severity": "WARNING",
            "action": "review",
            "message": "Wikipedia未掲載の人物は要レビュー"
        },
        {
            "id": "GATE_010",
            "name": "バンドメンバー表記確認",
            "check": "band_member_format_correct",
            "severity": "LOW",
            "action": "warn",
            "message": "バンドメンバーの表記形式を確認してください"
        }
    ]
    
    if 'quality_gates' not in memory:
        memory['quality_gates'] = []
    
    existing_gate_ids = {gate['id'] for gate in memory['quality_gates']}
    
    for gate in new_gates:
        if gate['id'] not in existing_gate_ids:
            memory['quality_gates'].append(gate)
            logger.info(f"✅ 品質ゲート追加: {gate['id']} - {gate['name']}")
    
    return memory


def save_project_memory(memory):
    """プロジェクトメモリの保存"""
    memory_file = Path("project_memory.json")
    
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
    
    logger.info(f"💾 プロジェクトメモリ保存: {memory_file}")


def create_validation_record(memory):
    """検証記録の作成"""
    validation = {
        "timestamp": datetime.now().isoformat(),
        "phase": "phase3_group_wikipedia_validation",
        "actions": [
            "グループエンティティ8件削除",
            "バンドメンバー表記17件修正",
            "Wikipedia存在確認実施",
            "PDCAルール6件追加（RULE_065-070）"
        ],
        "results": {
            "groups_removed": 8,
            "band_members_fixed": 17,
            "wikipedia_checked": 50,
            "rules_added": 6
        }
    }
    
    if 'validation_history' not in memory:
        memory['validation_history'] = []
    
    memory['validation_history'].append(validation)
    logger.info("📝 検証記録追加")
    
    return memory


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 PDCAガーディアンルール追加 - フェーズ3")
    logger.info("=" * 60)
    
    # プロジェクトメモリ読み込み
    memory = load_project_memory()
    logger.info("📂 プロジェクトメモリ読み込み完了")
    
    # 新ルール追加
    memory = add_new_rules(memory)
    
    # 品質ゲート追加
    memory = add_quality_gates(memory)
    
    # 検証記録作成
    memory = create_validation_record(memory)
    
    # 保存
    save_project_memory(memory)
    
    # サマリー
    logger.info("=" * 60)
    logger.info("📊 追加完了サマリー")
    logger.info("=" * 60)
    logger.info(f"  PDCAルール総数: {len(memory['pdca_guardian_rules'])}個")
    logger.info(f"  品質ゲート総数: {len(memory.get('quality_gates', []))}個")
    logger.info(f"  検証履歴: {len(memory.get('validation_history', []))}件")
    
    # 追加されたルールの表示
    logger.info("\n📋 追加されたルール:")
    for rule_id in ["RULE_065", "RULE_066", "RULE_067", "RULE_068", "RULE_069", "RULE_070"]:
        rule = next((r for r in memory['pdca_guardian_rules'] if r['id'] == rule_id), None)
        if rule:
            logger.info(f"  {rule['id']}: {rule['rule'][:60]}...")
    
    return memory


if __name__ == "__main__":
    memory = main()
    print("\n✅ PDCAガーディアンルール追加完了")
    print(f"📊 総ルール数: {len(memory['pdca_guardian_rules'])}個")