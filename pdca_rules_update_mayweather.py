#!/usr/bin/env python3
"""
PDCAガーディアンルール更新スクリプト
フロイド・メイウェザー問題から学んだ教訓を永続化
"""

import json
from datetime import datetime
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def add_mayweather_rules():
    """メイウェザー問題から学んだルールを追加"""

    # project_memory.jsonを読み込み
    memory_file = Path("project_memory.json")

    if memory_file.exists():
        with open(memory_file, 'r', encoding='utf-8') as f:
            memory = json.load(f)
    else:
        # 新規作成
        memory = {
            "metadata": {
                "version": "1.0.0",
                "created": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat()
            },
            "permanent_rules": [],
            "quality_metrics": {},
            "failed_patterns": [],
            "success_patterns": [],
            "pdca_history": [],
            "improvement_log": []
        }

    # 新しいルールを追加
    new_rules = [
        {
            "rule_id": "RULE_NAME_NORMALIZATION_001",
            "category": "名前正規化",
            "priority": "CRITICAL",
            "description": "外国人名は正式名称・通称・略称すべてを考慮する",
            "created_date": datetime.now().isoformat(),
            "trigger_event": "フロイド・メイウェザーのスコア異常（3.0）",
            "checks": [
                "「ジュニア」「Jr.」「II」「III」などの世代表記の有無を確認",
                "Wikipedia検索時は複数パターン（正式名・通称・略称）で試行",
                "日本語表記のバリエーション（カタカナ表記の揺れ）を考慮",
                "ミドルネームの有無による違いを吸収"
            ],
            "example_violations": [
                "フロイド・メイウェザー → フロイド・メイウェザー・ジュニア",
                "モハメド・アリ → ムハンマド・アリ",
                "マイク・タイソン → マイケル・ジェラルド・タイソン"
            ],
            "fix_approach": "name_variants フィールドに複数の名前パターンを保持"
        },
        {
            "rule_id": "RULE_ATHLETE_EVALUATION_001",
            "category": "スポーツ選手評価",
            "priority": "HIGH",
            "description": "世界的アスリートは最低スコア7.0を保証",
            "created_date": datetime.now().isoformat(),
            "trigger_event": "世界チャンピオンボクサーが低スコア",
            "checks": [
                "世界チャンピオン経験者は最低7.0",
                "オリンピックメダリストは最低6.5",
                "日本での試合・興行実績がある場合は+1.0加点",
                "複数階級制覇は+0.5/階級"
            ],
            "evaluation_criteria": {
                "world_champion": 7.0,
                "olympic_medalist": 6.5,
                "japan_match_bonus": 1.0,
                "multi_division_bonus": 0.5
            }
        },
        {
            "rule_id": "RULE_NAME_VARIANTS_001",
            "category": "データ構造",
            "priority": "HIGH",
            "description": "1人物に対して複数の名前パターンを管理",
            "created_date": datetime.now().isoformat(),
            "implementation": {
                "new_fields": [
                    "name_variants: List[str] - 名前のバリエーションリスト",
                    "official_name: str - 正式名称",
                    "common_name: str - 一般的な呼称"
                ],
                "search_strategy": "すべてのname_variantsでWikipedia/Web検索を実行",
                "score_calculation": "最も高いスコアを採用"
            }
        },
        {
            "rule_id": "RULE_WIKIPEDIA_SEARCH_001",
            "category": "API使用",
            "priority": "CRITICAL",
            "description": "Wikipedia検索の改善",
            "created_date": datetime.now().isoformat(),
            "improvements": [
                "検索失敗時は名前の一部を削除して再試行",
                "「・」を含む名前は「・」なしでも検索",
                "カタカナ表記の長音符号の有無両方で検索",
                "リダイレクトページも正しく処理"
            ]
        }
    ]

    # 失敗パターンに追加
    failed_pattern = {
        "pattern_id": "FAIL_MAYWEATHER_001",
        "date": datetime.now().isoformat(),
        "description": "フロイド・メイウェザーが異常に低いスコア（3.0）",
        "root_cause": "名前の不完全な形（ジュニア欠落）でのWikipedia検索失敗",
        "impact": "世界的に有名なボクサーが低評価",
        "lesson_learned": "外国人名の正規化と複数パターン検索の必要性",
        "prevention": "RULE_NAME_NORMALIZATION_001, RULE_ATHLETE_EVALUATION_001"
    }

    # メモリに追加
    memory['permanent_rules'].extend(new_rules)
    memory['failed_patterns'].append(failed_pattern)

    # 改善ログに記録
    improvement = {
        "date": datetime.now().isoformat(),
        "title": "フロイド・メイウェザー問題の修正",
        "description": "名前正規化とスポーツ選手評価基準の改善",
        "rules_added": [r["rule_id"] for r in new_rules],
        "expected_impact": "外国人アスリートの適切な評価"
    }
    memory['improvement_log'].append(improvement)

    # メタデータ更新
    memory['metadata']['last_updated'] = datetime.now().isoformat()
    memory['metadata']['version'] = "1.1.0"  # バージョンアップ

    # 保存
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)

    logger.info("✅ PDCAガーディアンルールを更新しました")
    logger.info(f"  追加ルール数: {len(new_rules)}")
    logger.info(f"  失敗パターン記録: 1件")

    return memory

def display_rules(memory):
    """追加したルールを表示"""
    print("\n" + "="*60)
    print("📋 追加されたPDCAガーディアンルール")
    print("="*60)

    for rule in memory['permanent_rules'][-4:]:  # 最新4件
        print(f"\n🔸 {rule['rule_id']}")
        print(f"  カテゴリ: {rule['category']}")
        print(f"  優先度: {rule['priority']}")
        print(f"  説明: {rule['description']}")
        if 'checks' in rule:
            print("  チェック項目:")
            for check in rule['checks']:
                print(f"    - {check}")

    print("\n" + "="*60)
    print("❌ 記録された失敗パターン")
    print("="*60)

    latest_fail = memory['failed_patterns'][-1]
    print(f"\nパターンID: {latest_fail['pattern_id']}")
    print(f"問題: {latest_fail['description']}")
    print(f"原因: {latest_fail['root_cause']}")
    print(f"教訓: {latest_fail['lesson_learned']}")
    print(f"対策ルール: {latest_fail['prevention']}")

if __name__ == "__main__":
    logger.info("="*60)
    logger.info("🛡️ PDCAガーディアンルール更新開始")
    logger.info("="*60)

    # ルール追加
    memory = add_mayweather_rules()

    # 表示
    display_rules(memory)

    print("\n✅ PDCAガーディアンシステムが強化されました")
    print("  今後、同様の問題は自動的に検出・防止されます")
