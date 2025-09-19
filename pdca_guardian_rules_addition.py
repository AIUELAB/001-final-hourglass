#!/usr/bin/env python3
"""
PDCAガーディアンルール追加スクリプト
連続IDパターンによる誤削除を防止するルール（RULE_077-080）を追加
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


def add_batch_data_protection_rules():
    """バッチデータ保護ルールの追加"""
    
    new_rules = [
        {
            "rule_id": "RULE_077",
            "name": "連続IDによるプレースホルダー誤判定防止",
            "description": "連続IDパターンだけでプレースホルダーと判定することを禁止。同一職業の連続IDはバッチ追加の証拠",
            "priority": "CRITICAL",
            "category": "データ品質",
            "check_function": "check_consecutive_id_logic",
            "violation_type": "CONSECUTIVE_ID_FALSE_POSITIVE",
            "prevention_measures": [
                "連続IDパターンの検出時、必ず職業フィールドを確認",
                "同一職業の連続IDはバッチ追加として保護",
                "original_batch_idフィールドの確認を必須化",
                "3件以上の同一職業連続は自動的に保護対象"
            ],
            "historical_context": "2025年9月11日: 女子プロレスラー24名を含む618件が誤削除された事件",
            "examples": {
                "wrong": "if consecutive_ids >= 5: mark_as_placeholder()",
                "correct": "if consecutive_ids >= 5 and len(unique_occupations) > 3: review_required()"
            }
        },
        {
            "rule_id": "RULE_078",
            "name": "職業別バッチデータ自動保護",
            "description": "スポーツ選手など特定職業カテゴリの連続データは自動的に保護対象とする",
            "priority": "HIGH",
            "category": "データ保護",
            "check_function": "check_occupation_batch_protection",
            "violation_type": "OCCUPATION_BATCH_UNPROTECTED",
            "protected_occupations": [
                "女子プロレスラー", "サッカー選手", "野球選手", "バスケットボール選手",
                "テニス選手", "水泳選手", "陸上選手", "バレーボール選手", "体操選手",
                "フィギュアスケート選手", "卓球選手", "バドミントン選手", "レスリング選手",
                "ラグビー選手", "柔道選手", "ボクシング選手", "ゴルフ選手", "女子格闘家"
            ],
            "batch_detection_criteria": {
                "min_consecutive_count": 3,
                "occupation_consistency": 0.8,
                "score_uniformity": 0.9
            }
        },
        {
            "rule_id": "RULE_079",
            "name": "Wikipedia存在確認優先原則",
            "description": "プレースホルダー判定前に必ずWikipedia存在確認を実施。存在する人物は削除対象外",
            "priority": "CRITICAL",
            "category": "検証プロセス",
            "check_function": "check_wikipedia_validation_priority",
            "violation_type": "WIKIPEDIA_CHECK_SKIPPED",
            "implementation_requirements": [
                "プレースホルダー判定の前にWikipedia検証を実施",
                "Wikipedia存在確認済みデータには保護フラグを設定",
                "検証履歴をextraフィールドに記録",
                "バッチ処理時も個別にWikipedia確認"
            ],
            "validation_order": [
                "1. Wikipedia存在確認",
                "2. 既知有名人リストとの照合",
                "3. バッチ追加パターンの確認",
                "4. プレースホルダーパターン検出",
                "5. 最終判定（保護優先）"
            ]
        },
        {
            "rule_id": "RULE_080",
            "name": "削除前の多段階検証必須化",
            "description": "データ削除前に必ず複数の検証ステップを実施し、誤削除を防止",
            "priority": "CRITICAL",
            "category": "品質保証",
            "check_function": "check_multi_stage_validation",
            "violation_type": "VALIDATION_STEPS_INSUFFICIENT",
            "required_validation_steps": [
                {
                    "step": 1,
                    "name": "職業パターン分析",
                    "description": "同一職業の連続性を確認",
                    "fail_action": "PROTECT"
                },
                {
                    "step": 2,
                    "name": "バッチID確認",
                    "description": "original_batch_idの存在確認",
                    "fail_action": "PROTECT"
                },
                {
                    "step": 3,
                    "name": "Wikipedia検証",
                    "description": "Wikipedia存在確認",
                    "fail_action": "PROTECT"
                },
                {
                    "step": 4,
                    "name": "既知パターン照合",
                    "description": "過去の誤削除パターンとの照合",
                    "fail_action": "REVIEW_REQUIRED"
                },
                {
                    "step": 5,
                    "name": "統計的異常検出",
                    "description": "削除率が20%を超える場合は再検証",
                    "fail_action": "HALT_PROCESS"
                }
            ],
            "deletion_safeguards": {
                "max_deletion_rate": 0.2,
                "min_validation_confidence": 0.95,
                "require_human_review_above": 100,
                "auto_rollback_on_error": True
            }
        }
    ]
    
    # 既存のPDCAルールファイルを読み込み
    pdca_rules_file = Path("pdca_rules.json")
    
    if pdca_rules_file.exists():
        with open(pdca_rules_file, 'r', encoding='utf-8') as f:
            existing_rules = json.load(f)
    else:
        existing_rules = {"rules": [], "version": "1.0.0", "last_updated": None}
    
    # 新しいルールを追加
    existing_rules["rules"].extend(new_rules)
    existing_rules["last_updated"] = datetime.now().isoformat()
    existing_rules["version"] = "1.1.0"
    
    # 更新内容を記録
    update_log = {
        "timestamp": datetime.now().isoformat(),
        "action": "ADD_RULES",
        "rules_added": [rule["rule_id"] for rule in new_rules],
        "reason": "女子プロレスラー等618件の誤削除事件を受けた恒久的対策",
        "implemented_by": "PDCAGuardianSystem",
        "validation_status": "ACTIVE"
    }
    
    if "update_history" not in existing_rules:
        existing_rules["update_history"] = []
    existing_rules["update_history"].append(update_log)
    
    # ファイルに保存
    with open(pdca_rules_file, 'w', encoding='utf-8') as f:
        json.dump(existing_rules, f, ensure_ascii=False, indent=2)
    
    logger.info("=" * 60)
    logger.info("✅ PDCAガーディアンルール追加完了")
    logger.info("=" * 60)
    
    for rule in new_rules:
        logger.info(f"  {rule['rule_id']}: {rule['name']}")
        logger.info(f"    優先度: {rule['priority']}")
        logger.info(f"    カテゴリ: {rule['category']}")
    
    return new_rules


def create_validation_checklist():
    """検証チェックリスト生成"""
    
    checklist = {
        "title": "プレースホルダー検出前チェックリスト",
        "version": "2.0.0",
        "created": datetime.now().isoformat(),
        "mandatory_checks": [
            {
                "id": "CHECK_001",
                "name": "職業一致率確認",
                "description": "連続IDグループ内の職業一致率を確認",
                "threshold": 0.8,
                "action_if_pass": "PROTECT",
                "action_if_fail": "CONTINUE"
            },
            {
                "id": "CHECK_002",
                "name": "バッチIDフィールド確認",
                "description": "extraフィールド内のoriginal_batch_id確認",
                "required": False,
                "action_if_found": "PROTECT",
                "action_if_not_found": "CONTINUE"
            },
            {
                "id": "CHECK_003",
                "name": "Wikipedia存在確認",
                "description": "Wikipedia APIでの存在確認",
                "required": True,
                "action_if_exists": "PROTECT",
                "action_if_not_exists": "CONTINUE"
            },
            {
                "id": "CHECK_004",
                "name": "既知有名人照合",
                "description": "保護リスト内の人物との照合",
                "required": True,
                "action_if_match": "PROTECT",
                "action_if_no_match": "CONTINUE"
            },
            {
                "id": "CHECK_005",
                "name": "削除率チェック",
                "description": "全体の削除率が閾値以内か確認",
                "threshold": 0.2,
                "action_if_exceed": "HALT",
                "action_if_normal": "CONTINUE"
            }
        ],
        "final_decision_logic": """
        if any(check.result == 'PROTECT'):
            return 'DO_NOT_DELETE'
        elif any(check.result == 'HALT'):
            return 'STOP_PROCESS'
        elif validation_confidence < 0.95:
            return 'HUMAN_REVIEW_REQUIRED'
        else:
            return 'CAN_DELETE'
        """
    }
    
    checklist_file = Path("placeholder_detection_checklist.json")
    with open(checklist_file, 'w', encoding='utf-8') as f:
        json.dump(checklist, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n📋 チェックリスト作成: {checklist_file}")
    
    return checklist


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 PDCAガーディアンルール追加処理開始")
    logger.info("=" * 60)
    
    # ルール追加
    new_rules = add_batch_data_protection_rules()
    
    # チェックリスト作成
    checklist = create_validation_checklist()
    
    # サマリー出力
    logger.info("\n" + "=" * 60)
    logger.info("📊 追加完了サマリー")
    logger.info("=" * 60)
    logger.info(f"  追加ルール数: {len(new_rules)}")
    logger.info(f"  チェックリスト項目: {len(checklist['mandatory_checks'])}")
    logger.info("\n💡 今後の処理:")
    logger.info("  1. すべてのプレースホルダー検出処理にこれらのルールを適用")
    logger.info("  2. 削除前に必ずチェックリストを実行")
    logger.info("  3. Wikipedia検証を最優先で実施")
    logger.info("  4. 削除率20%超過時は自動停止")
    
    # 教訓の記録
    lesson_learned = {
        "incident_date": "2025-09-11",
        "incident_summary": "連続IDパターンによる誤判定で女子プロレスラー24名を含む618件が誤削除",
        "root_cause": "連続IDパターンのみでプレースホルダーと判定する単純なロジック",
        "impact": "正当なバッチ追加データの大量誤削除",
        "corrective_actions": [
            "RULE_077: 連続ID誤判定防止",
            "RULE_078: 職業別バッチ保護",
            "RULE_079: Wikipedia確認優先",
            "RULE_080: 多段階検証必須化"
        ],
        "preventive_measures": [
            "プレースホルダー検出ロジックの完全改修",
            "削除前チェックリストの義務化",
            "Wikipedia検証の最優先実施",
            "削除率監視による自動停止機能"
        ]
    }
    
    lesson_file = Path("lessons_learned_20250911.json")
    with open(lesson_file, 'w', encoding='utf-8') as f:
        json.dump(lesson_learned, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n📚 教訓記録: {lesson_file}")
    logger.info("\n✅ PDCAガーディアンルール追加完了")
    logger.info("⚠️ 二度と同じ過ちを繰り返さないよう、これらのルールは永続的に適用されます")


if __name__ == "__main__":
    main()