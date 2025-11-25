#!/usr/bin/env python3
"""
フェーズ1: 緊急修正
Phase 1: Critical Fixes

目的:
1. RULE_151の文字数基準を132-250に統一
2. 説明なしルール6件のドキュメント化
"""

import logging
from unified_rule_management_system import UnifiedRuleRegistry
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


def main():
    """フェーズ1の修正を実行"""
    logger.info("=" * 60)
    logger.info("フェーズ1: 緊急修正開始")
    logger.info("=" * 60)

    registry = UnifiedRuleRegistry()

    # 1. RULE_151の文字数基準統一
    logger.info("\n1. RULE_151の文字数基準を132-250に統一...")

    rule_151_updates = {
        'name': '文字数制限チェック（132-250文字）',
        'description': '''文字数制限チェック

【標準範囲】
最小: 132文字
最大: 250文字

【更新履歴】
- 2025-09-22: 最小値を150から132に緩和
- 2025-10-02: FORMAT_001/RULE_160と完全統一''',
        'updated_at': datetime.now().isoformat()
    }

    success = registry.update_rule('RULE_151', rule_151_updates)
    if success:
        logger.info("✅ RULE_151の文字数基準を132-250に統一完了")
    else:
        logger.error("❌ RULE_151の更新に失敗")

    # 2. 説明なしルール6件のドキュメント化
    logger.info("\n2. 説明なしルール6件のドキュメント化...")

    # RULE_017: 品質妥協キーワード検出
    rule_017_updates = {
        'description': '''品質妥協キーワード検出

【目的】
提案文（proposal）に品質を妥協する可能性のあるキーワードが含まれていないかチェック。

【検出キーワード】
- ハイブリッド、部分的、一部のみ
- 簡易版、シンプル版、高速版
- quick、fast、simple
- 短縮、早く、速く

【違反時の対応】
- 品質妥協の可能性がある提案として警告
- 完全実装を推奨

【実装箇所】
pdca_guardian.py:check_proposal()''',
        'updated_at': datetime.now().isoformat()
    }

    if registry.update_rule('RULE_017', rule_017_updates):
        logger.info("✅ RULE_017: 品質妥協キーワード検出")

    # RULE_108: 歴史的重要性チェック
    rule_108_updates = {
        'description': '''歴史的重要性チェック

【目的】
エピソードに歴史的重要性を示す要素（「初」「史上」「記録」等）が含まれているか検証。

【チェック内容】
- historical_scoreがHISTORICAL_THRESHOLD以上であること
- 歴史的重要性を示すキーワードの存在確認

【歴史的キーワード例】
- 初、史上、記録、革命、歴史的
- 前代未聞、画期的、伝説的

【違反時の対応】
- ViolationType.EPISODE_MISSING_HISTORICAL_SIGNIFICANCE
- "歴史的重要性を示す要素が不足しています"

【実装箇所】
pdca_guardian.py:_check_historical_significance()''',
        'updated_at': datetime.now().isoformat()
    }

    if registry.update_rule('RULE_108', rule_108_updates):
        logger.info("✅ RULE_108: 歴史的重要性チェック")

    # RULE_113: 世界的偉業チェック
    rule_113_updates = {
        'description': '''世界的偉業チェック

【目的】
世界的に重要な人物（is_globally_significant=True）のエピソードに、グローバルな偉業が含まれているか確認。

【チェック基準】
- impact_result['details']['global'] >= 10
- 世界的に重要な人物の場合は必須

【グローバル偉業の例】
- オリンピック金メダル
- ノーベル賞受賞
- 世界記録樹立
- 国際的な賞の受賞

【違反時の対応】
- ViolationType.EPISODE_GLOBAL_ACHIEVEMENT_MISSING
- "世界的に重要な人物なのに、グローバルな偉業が含まれていません"

【実装箇所】
pdca_guardian.py:_check_global_achievement()''',
        'updated_at': datetime.now().isoformat()
    }

    if registry.update_rule('RULE_113', rule_113_updates):
        logger.info("✅ RULE_113: 世界的偉業チェック")

    # RULE_116: 具体性チェック
    rule_116_updates = {
        'description': '''具体性チェック

【目的】
エピソードテキストに具体的な要素（作品名、数値、固有名詞、イベント）が含まれているか検証。

【検出要素】
1. 作品名: 「」『』で囲まれた部分
   - 例: 「ドラゴンボール」『スラムダンク』

2. 数値: 数字+単位
   - 例: 1998年、100万人、3位、50億円

3. 固有名詞: 大文字始まり/カタカナ3文字以上
   - 例: Tokyo、オリンピック

4. イベントキーワード:
   - 優勝、受賞、発表、公演、開催、出演、登場

【違反基準】
- 具体的要素が2つ未満の場合

【実装箇所】
pdca_guardian.py:_check_concreteness()''',
        'updated_at': datetime.now().isoformat()
    }

    if registry.update_rule('RULE_116', rule_116_updates):
        logger.info("✅ RULE_116: 具体性チェック")

    # RULE_117: 感銘要素チェック
    rule_117_updates = {
        'description': '''感銘要素チェック

【目的】
エピソードに人々を感銘させる要素が含まれているか、6つのカテゴリから検証。

【6つの感銘カテゴリ】
1. achievement（実績）: 優勝、受賞、MVP、金メダル、世界一
2. challenge（挑戦）: 挑戦、困難、逆境、苦労、壁
3. emotion（感情）: 感動、涙、感謝、喜び、熱意
4. milestone（転機）: デビュー、転機、独立、結婚、引退
5. historical（歴史性）: 初、史上、革命、歴史的、伝説
6. relationship（人間関係）: 出会い、別れ、仲間、師匠、ライバル

【チェック基準】
- 最低2つのカテゴリから要素を含むこと
- 各カテゴリに複数のキーワードを定義

【違反時の対応】
- 感銘要素が不足している旨を警告
- 具体的にどのカテゴリが不足しているか提示

【実装箇所】
pdca_guardian.py:_check_impact_elements()''',
        'updated_at': datetime.now().isoformat()
    }

    if registry.update_rule('RULE_117', rule_117_updates):
        logger.info("✅ RULE_117: 感銘要素チェック")

    # RULE_169: バッチ処理個別検証
    rule_169_updates = {
        'description': '''バッチ処理個別検証

【目的】
バッチ処理時に各エピソードを個別検証し、品質保証を行う。

【検証項目】
1. 重複検出:
   - 各エピソードの先頭50文字をキーとして重複チェック
   - 重複が検出された場合はエラー

2. エピソード数検証:
   - 最低7件のエピソードが必要
   - 7件未満の場合はcritical違反

3. 個別品質チェック:
   - 各エピソードが他のルールに準拠しているか確認

【違反時の対応】
- 重複: duplicate_episode違反を記録
- 数不足: episode_count_insufficient（severity: critical）

【実装箇所】
pdca_guardian.py:check_batch_individual_verification()''',
        'updated_at': datetime.now().isoformat()
    }

    if registry.update_rule('RULE_169', rule_169_updates):
        logger.info("✅ RULE_169: バッチ処理個別検証")

    logger.info("\n" + "=" * 60)
    logger.info("✅ フェーズ1完了")
    logger.info("=" * 60)

    # 統計情報を表示
    logger.info("\n📊 最新統計:")
    logger.info(f"  総ルール数: {len(registry.rules)}")

    documented_rules = [r for r in registry.rules.values() if r.description != "（説明なし）"]
    doc_rate = len(documented_rules) / len(registry.rules) * 100
    logger.info(f"  ドキュメント率: {doc_rate:.1f}% ({len(documented_rules)}/{len(registry.rules)})")

    # 文字数範囲チェック
    length_rules = ['FORMAT_001', 'RULE_151', 'RULE_160']
    logger.info(f"\n  文字数範囲統一状況:")
    for rule_id in length_rules:
        if rule_id in registry.rules:
            rule = registry.rules[rule_id]
            logger.info(f"    {rule_id}: {rule.name}")


if __name__ == "__main__":
    main()
