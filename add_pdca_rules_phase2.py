#!/usr/bin/env python3
"""
PDCAガーディアンシステムに新しいルールを追加（フェーズ2）
P003218とダニエル問題を防ぐための永続的ルール
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


def add_data_quality_rules():
    """データ品質に関する新ルールを追加"""
    
    logger.info("=" * 60)
    logger.info("📝 PDCAガーディアンルール追加（フェーズ2）")
    logger.info("=" * 60)
    
    # project_memory.jsonを読み込み
    memory_file = Path("project_memory.json")
    with open(memory_file, 'r', encoding='utf-8') as f:
        memory = json.load(f)
    
    # 新しいルールを追加
    new_rules = [
        {
            "id": "RULE_059",
            "date": "2025-09-10",
            "source": "ユーザー指摘（P003218・ダニエル問題）",
            "rule": "Wikipedia掲載必須：知名度データベースには原則Wikipediaに記載がある人物のみ収録",
            "priority": "CRITICAL",
            "category": "データ品質",
            "context": "「いつからWikipediaに載っていない人物が有名人・知名人のデータに入れるようになったの？」",
            "violations": [],
            "enforcement": "Wikipedia APIまたはWeb検索で存在確認必須",
            "description": "プレースホルダーやテストデータの混入を防ぐ最重要ルール"
        },
        {
            "id": "RULE_060",
            "date": "2025-09-10",
            "source": "ユーザー指摘（P003218問題）",
            "rule": "グループエンティティのperson_name検証：entity_type='group'の場合、person_nameはグループ名のみ",
            "priority": "CRITICAL",
            "category": "データ整合性",
            "context": "「鈴木嵐」のような存在しない個人名がグループに設定される問題",
            "violations": [],
            "enforcement": "グループの場合はperson_name == person_name_displayを必須とする",
            "description": "グループを個人として扱うデータ不整合を防ぐ"
        },
        {
            "id": "RULE_061",
            "date": "2025-09-10",
            "source": "ユーザー指摘（ダニエル問題）",
            "rule": "プレースホルダーパターン検出：外国人名+日本人名の組み合わせは要レビュー",
            "priority": "HIGH",
            "category": "データ品質",
            "context": "「ダニエル三郎」「ダニエル健太」などの明らかなテストデータ",
            "violations": [],
            "enforcement": "パターンマッチング: (カタカナ外国人名) + (漢字/ひらがな日本人名)",
            "description": "テストデータやプレースホルダーの自動検出"
        },
        {
            "id": "RULE_062",
            "date": "2025-09-10",
            "source": "システム分析",
            "rule": "同一スコアクラスター警告：同じスコアが10件以上ある場合は警告",
            "priority": "MEDIUM",
            "category": "データ品質",
            "context": "74件のテニス選手が全員50.0点という異常パターン",
            "violations": [],
            "enforcement": "スコア分布の統計的チェック、異常なクラスターの検出",
            "description": "機械的生成データの検出"
        },
        {
            "id": "RULE_063",
            "date": "2025-09-10",
            "source": "システム分析",
            "rule": "テストデータパターン検出：同一職業・同一スコア・連番IDは要確認",
            "priority": "HIGH",
            "category": "データ品質",
            "context": "テンプレート生成によるテストデータの混入防止",
            "violations": [],
            "enforcement": "occupation + score + sequential_id のパターン検出",
            "description": "バッチ生成されたテストデータの検出"
        },
        {
            "id": "RULE_064",
            "date": "2025-09-10",
            "source": "システム分析",
            "rule": "連番ID異常検出：10件以上の連番IDブロックは要レビュー",
            "priority": "MEDIUM",
            "category": "データ品質",
            "context": "P001451-P001460のような機械的生成パターン",
            "violations": [],
            "enforcement": "person_idの連続性チェック、10件以上の連番で警告",
            "description": "一括生成データの検出と品質確認"
        }
    ]
    
    # 既存のルールに追加
    if 'pdca_guardian_rules' not in memory:
        memory['pdca_guardian_rules'] = []
    
    # 重複チェック
    existing_ids = {rule['id'] for rule in memory['pdca_guardian_rules']}
    added_count = 0
    
    for rule in new_rules:
        if rule['id'] not in existing_ids:
            memory['pdca_guardian_rules'].append(rule)
            logger.info(f"✅ 追加: {rule['id']} - {rule['rule'][:50]}...")
            added_count += 1
        else:
            logger.info(f"⏭️ スキップ（既存）: {rule['id']}")
    
    # 保存
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n📊 ルール追加完了: {added_count}個")
    logger.info(f"📊 総ルール数: {len(memory['pdca_guardian_rules'])}個")
    
    return added_count


def update_failure_patterns():
    """失敗パターンも更新"""
    
    logger.info("\n" + "=" * 60)
    logger.info("📝 失敗パターンの追加")
    logger.info("=" * 60)
    
    memory_file = Path("project_memory.json")
    with open(memory_file, 'r', encoding='utf-8') as f:
        memory = json.load(f)
    
    new_failures = [
        {
            "id": "FAIL_P003218",
            "date": "2025-09-10",
            "pattern": "グループ名への個人名付与",
            "description": "「嵐」に「鈴木」を付けて「鈴木嵐」とする誤り",
            "consequence": "存在しない人物が生成され、データ品質が低下",
            "prevention": "RULE_060: グループのperson_name検証を徹底"
        },
        {
            "id": "FAIL_DANIEL",
            "date": "2025-09-10",
            "pattern": "プレースホルダーデータの本番混入",
            "description": "「ダニエル三郎」などのテストデータが本番DBに混入",
            "consequence": "架空の人物がデータベースを汚染",
            "prevention": "RULE_059: Wikipedia掲載確認、RULE_061: プレースホルダーパターン検出"
        }
    ]
    
    if 'failure_patterns' not in memory:
        memory['failure_patterns'] = []
    
    existing_ids = {f.get('id', '') for f in memory['failure_patterns']}
    added_count = 0
    
    for failure in new_failures:
        if failure['id'] not in existing_ids:
            memory['failure_patterns'].append(failure)
            logger.info(f"✅ 追加: {failure['id']} - {failure['pattern']}")
            added_count += 1
    
    # 保存
    with open(memory_file, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n📊 失敗パターン追加: {added_count}個")
    
    return added_count


def generate_rule_report():
    """ルール追加レポートの生成"""
    
    memory_file = Path("project_memory.json")
    with open(memory_file, 'r', encoding='utf-8') as f:
        memory = json.load(f)
    
    rules = memory.get('pdca_guardian_rules', [])
    
    # カテゴリ別集計
    categories = {}
    for rule in rules:
        cat = rule.get('category', 'その他')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(rule)
    
    # 優先度別集計
    priorities = {'CRITICAL': 0, 'HIGH': 0, 'MEDIUM': 0, 'LOW': 0}
    for rule in rules:
        priority = rule.get('priority', 'MEDIUM')
        if priority in priorities:
            priorities[priority] += 1
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'total_rules': len(rules),
        'categories': {cat: len(rules) for cat, rules in categories.items()},
        'priorities': priorities,
        'latest_rules': [r['id'] for r in rules[-6:]],  # 最新6個
        'phase2_rules': ['RULE_059', 'RULE_060', 'RULE_061', 'RULE_062', 'RULE_063', 'RULE_064']
    }
    
    report_file = f"pdca_rules_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n📝 レポート保存: {report_file}")
    
    # サマリー表示
    logger.info("\n" + "=" * 60)
    logger.info("📊 PDCAガーディアンルール サマリー")
    logger.info("=" * 60)
    logger.info(f"総ルール数: {report['total_rules']}個")
    logger.info("\nカテゴリ別:")
    for cat, count in report['categories'].items():
        logger.info(f"  {cat}: {count}個")
    logger.info("\n優先度別:")
    for priority, count in report['priorities'].items():
        logger.info(f"  {priority}: {count}個")
    
    return report


def main():
    """メイン処理"""
    logger.info("🚀 PDCAガーディアンルール追加（フェーズ2）開始")
    
    # 1. データ品質ルールの追加
    rules_added = add_data_quality_rules()
    
    # 2. 失敗パターンの追加
    failures_added = update_failure_patterns()
    
    # 3. レポート生成
    report = generate_rule_report()
    
    # 最終サマリー
    logger.info("\n" + "=" * 60)
    logger.info("✅ 完了サマリー")
    logger.info("=" * 60)
    logger.info(f"新規ルール追加: {rules_added}個")
    logger.info(f"失敗パターン追加: {failures_added}個")
    logger.info(f"総ルール数: {report['total_rules']}個")
    
    logger.info("\n🎯 今回追加した重要ルール:")
    logger.info("  RULE_059: Wikipedia掲載必須")
    logger.info("  RULE_060: グループ名検証")
    logger.info("  RULE_061: プレースホルダー検出")
    logger.info("  RULE_062: 同一スコアクラスター警告")
    logger.info("  RULE_063: テストデータパターン検出")
    logger.info("  RULE_064: 連番ID異常検出")
    
    logger.info("\n✅ PDCAガーディアンルールの追加が完了しました！")
    logger.info("これらのルールにより、今後同様の問題が発生することを防ぎます。")


if __name__ == "__main__":
    main()