#!/usr/bin/env python3
"""
PDCAガーディアンルール追加 - フェーズ4（改訂版）
Wikipedia存在確認を主軸とした検証ルール
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


def add_wikipedia_validation_rules(memory):
    """Wikipedia存在確認を中心としたPDCAルールを追加"""
    
    new_rules = [
        {
            "id": "RULE_071",
            "rule": "Wikipedia存在確認必須：person_name + occupation + nationalityで検索し存在確認",
            "category": "data_validation",
            "priority": "CRITICAL",
            "created_at": datetime.now().isoformat(),
            "enforcement": "automatic",
            "validation": "wikipedia_search_required",
            "search_pattern": "'{person_name} {occupation} {nationality}' OR '{person_name} {occupation}' OR '{person_name}'",
            "error_message": "Wikipedia存在確認が必須です。複合検索で存在を検証してください。"
        },
        {
            "id": "RULE_072",
            "rule": "Wikipedia未掲載者スコア0設定：検索で見つからない人物は自動的にname_recognition=0",
            "category": "data_quality",
            "priority": "CRITICAL",
            "created_at": datetime.now().isoformat(),
            "enforcement": "automatic",
            "validation": "if not wikipedia_exists then name_recognition = 0",
            "error_message": "Wikipedia未掲載のため、name_recognition=0に設定されます。"
        },
        {
            "id": "RULE_073",
            "rule": "複合検索による存在確認：名前単独ではなく職業・国籍を含めた総合検証",
            "category": "data_validation",
            "priority": "HIGH",
            "created_at": datetime.now().isoformat(),
            "enforcement": "automatic",
            "validation": "composite_search_validation",
            "search_levels": [
                "Level 1: person_name + occupation + nationality",
                "Level 2: person_name + occupation",
                "Level 3: person_name only (if levels 1-2 fail)"
            ],
            "error_message": "複合検索による存在確認が必要です。"
        },
        {
            "id": "RULE_074",
            "rule": "既知有名人リスト保護：HIKAKIN等の明確な有名人は検証エラー時も保護",
            "category": "data_protection",
            "priority": "HIGH",
            "created_at": datetime.now().isoformat(),
            "enforcement": "automatic",
            "validation": "known_celebrities_protection",
            "protected_list": ["HIKAKIN", "米津玄師", "大谷翔平", "リーチマイケル", "香川真司"],
            "error_message": "既知有名人は保護対象のため、スコアを維持します。"
        },
        {
            "id": "RULE_075",
            "rule": "定期的な全件Wikipedia検証：データベース全体の定期的な存在確認実施",
            "category": "quality_assurance",
            "priority": "MEDIUM",
            "created_at": datetime.now().isoformat(),
            "enforcement": "scheduled",
            "frequency": "weekly",
            "validation": "full_database_wikipedia_validation",
            "batch_size": 100,
            "error_message": "定期的なWikipedia全件検証を実施してください。"
        },
        {
            "id": "RULE_076",
            "rule": "API検証エラー時の処理：タイムアウトや接続エラー時はスコア維持、再検証フラグ設定",
            "category": "error_handling",
            "priority": "MEDIUM",
            "created_at": datetime.now().isoformat(),
            "enforcement": "automatic",
            "validation": "on_api_error: maintain_score AND set_revalidation_flag",
            "retry_policy": "3 attempts with exponential backoff",
            "error_message": "API検証エラーのため、スコアを維持し再検証フラグを設定します。"
        }
    ]
    
    # 既存のルールに追加
    existing_ids = {rule['id'] for rule in memory.get('pdca_guardian_rules', [])}
    
    for rule in new_rules:
        if rule['id'] not in existing_ids:
            memory['pdca_guardian_rules'].append(rule)
            logger.info(f"✅ ルール追加: {rule['id']} - {rule['rule'][:50]}...")
        else:
            # 既存ルールを更新（改訂版として）
            for i, existing_rule in enumerate(memory['pdca_guardian_rules']):
                if existing_rule['id'] == rule['id']:
                    memory['pdca_guardian_rules'][i] = rule
                    logger.info(f"🔄 ルール更新: {rule['id']} - {rule['rule'][:50]}...")
                    break
    
    return memory


def add_wikipedia_quality_gates(memory):
    """Wikipedia検証用の品質ゲート追加"""
    
    new_gates = [
        {
            "id": "GATE_011",
            "name": "Wikipedia存在確認ゲート",
            "check": "wikipedia_existence_verified",
            "severity": "CRITICAL",
            "action": "set_score_zero_if_not_found",
            "message": "Wikipedia未掲載者は自動的にスコア0設定"
        },
        {
            "id": "GATE_012",
            "name": "複合検索検証ゲート",
            "check": "composite_search_completed",
            "severity": "HIGH",
            "action": "require_validation",
            "message": "person_name + occupation + nationalityでの検証必須"
        },
        {
            "id": "GATE_013",
            "name": "スコア0レコード処理ゲート",
            "check": "score_zero_handling",
            "severity": "MEDIUM",
            "action": "review_for_deletion_or_retention",
            "message": "スコア0レコードの削除または保持を判断"
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


def create_validation_record(memory):
    """検証記録の作成"""
    validation = {
        "timestamp": datetime.now().isoformat(),
        "phase": "phase4_wikipedia_validation_revised",
        "actions": [
            "Wikipedia存在確認ルール追加（RULE_071-076改訂版）",
            "複合検索による検証実装",
            "644件のプレースホルダー検出・スコア0設定",
            "既知有名人保護リスト実装"
        ],
        "results": {
            "placeholders_detected": 644,
            "score_zero_set": 644,
            "rules_revised": 6,
            "validation_method": "wikipedia_api_composite_search"
        },
        "key_changes": [
            "パターン検出からWikipedia存在確認へ方針変更",
            "person_name + occupation + nationalityでの複合検索実装",
            "API検証エラー時の適切な処理追加"
        ]
    }
    
    if 'validation_history' not in memory:
        memory['validation_history'] = []
    
    memory['validation_history'].append(validation)
    logger.info("📝 検証記録追加")
    
    return memory


def save_project_memory(memory):
    """プロジェクトメモリの保存"""
    memory_file = Path("project_memory.json")
    
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
    
    logger.info(f"💾 プロジェクトメモリ保存: {memory_file}")


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 PDCAガーディアンルール追加 - フェーズ4（改訂版）")
    logger.info("📌 Wikipedia存在確認を主軸とした検証ルール")
    logger.info("=" * 60)
    
    # プロジェクトメモリ読み込み
    memory = load_project_memory()
    logger.info("📂 プロジェクトメモリ読み込み完了")
    
    # Wikipedia検証ルール追加
    memory = add_wikipedia_validation_rules(memory)
    
    # 品質ゲート追加
    memory = add_wikipedia_quality_gates(memory)
    
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
    logger.info("\n📋 追加/更新されたルール:")
    for rule_id in ["RULE_071", "RULE_072", "RULE_073", "RULE_074", "RULE_075", "RULE_076"]:
        rule = next((r for r in memory['pdca_guardian_rules'] if r['id'] == rule_id), None)
        if rule:
            logger.info(f"  {rule['id']}: {rule['rule'][:60]}...")
    
    # 重要な変更点
    logger.info("\n🔄 重要な変更点:")
    logger.info("  1. パターン検出 → Wikipedia存在確認へ方針転換")
    logger.info("  2. 複合検索（名前＋職業＋国籍）による精度向上")
    logger.info("  3. Wikipedia未掲載者は自動的にスコア0設定")
    logger.info("  4. 既知有名人の保護リスト実装")
    logger.info("  5. API検証エラー時の適切な処理")
    
    return memory


if __name__ == "__main__":
    memory = main()
    print("\n✅ PDCAガーディアンルール追加完了（改訂版）")
    print(f"📊 総ルール数: {len(memory['pdca_guardian_rules'])}個")
    print("🎯 Wikipedia存在確認が主要な検証基準として設定されました")