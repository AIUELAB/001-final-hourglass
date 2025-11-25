#!/usr/bin/env python3
"""
ルール矛盾検出・分析システム
Rule Contradiction Detection and Analysis System

目的:
1. ルール同士の論理的矛盾を検出
2. 相反する要求の特定
3. 優先度の競合検出
4. 実装レベルでの矛盾検出

Created: 2025-10-02
"""

import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Set
from dataclasses import dataclass
from unified_rule_management_system import UnifiedRuleRegistry

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class Contradiction:
    """矛盾情報"""
    rule1_id: str
    rule2_id: str
    contradiction_type: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    evidence: List[str]


class RuleContradictionAnalyzer:
    """ルール矛盾分析器"""

    def __init__(self):
        self.registry = UnifiedRuleRegistry()
        self.pdca_source = self._load_pdca_source()
        self.contradictions: List[Contradiction] = []

    def _load_pdca_source(self) -> str:
        """pdca_guardian.pyのソースコードをロード"""
        pdca_path = Path("pdca_guardian.py")
        if pdca_path.exists():
            with open(pdca_path, 'r', encoding='utf-8') as f:
                return f.read()
        return ""

    def analyze_all_contradictions(self) -> List[Contradiction]:
        """すべての矛盾を分析"""
        logger.info("🔍 ルール矛盾分析開始...\n")

        # 1. 論理的矛盾
        self._detect_logical_contradictions()

        # 2. 優先度の矛盾
        self._detect_priority_contradictions()

        # 3. 実装レベルの矛盾
        self._detect_implementation_contradictions()

        # 4. カテゴリの矛盾
        self._detect_category_contradictions()

        # 5. 説明文の矛盾
        self._detect_description_contradictions()

        self._generate_report()

        return self.contradictions

    def _detect_logical_contradictions(self):
        """論理的矛盾の検出"""
        logger.info("=" * 60)
        logger.info("1. 論理的矛盾の検出")
        logger.info("=" * 60)

        # pdca_guardian.pyから具体的なルール実装を抽出
        contradictions_found = []

        # 例: RULE_001 (calibrated_score禁止) vs 他のルールでcalibrated_scoreを使用
        if "calibrated_score" in self.pdca_source:
            # calibrated_scoreの使用箇所を検索
            usage_pattern = r'(RULE_\d+).*calibrated_score'
            matches = re.finditer(usage_pattern, self.pdca_source)

            for match in matches:
                rule_id = match.group(1)
                if rule_id != "RULE_001":
                    contradictions_found.append({
                        'rule1': 'RULE_001',
                        'rule2': rule_id,
                        'type': 'calibrated_score使用禁止違反'
                    })

        # エピソード長さの矛盾を検出
        length_rules = self._find_rules_about_length()
        if len(length_rules) > 1:
            for i, (rule1_id, rule1_desc) in enumerate(length_rules):
                for rule2_id, rule2_desc in length_rules[i+1:]:
                    # 長さ要求が矛盾していないかチェック
                    if self._check_length_contradiction(rule1_desc, rule2_desc):
                        self.contradictions.append(Contradiction(
                            rule1_id=rule1_id,
                            rule2_id=rule2_id,
                            contradiction_type="文字数範囲の矛盾",
                            severity="HIGH",
                            description=f"{rule1_id}と{rule2_id}で文字数範囲が矛盾",
                            evidence=[rule1_desc, rule2_desc]
                        ))

        logger.info(f"検出された論理的矛盾: {len(contradictions_found)}件\n")

    def _find_rules_about_length(self) -> List[Tuple[str, str]]:
        """文字数に関するルールを検索"""
        length_rules = []

        for rule_id, rule in self.registry.rules.items():
            if any(kw in rule.description.lower() for kw in ['文字', '長さ', 'length', '180', '250']):
                length_rules.append((rule_id, rule.description))

        return length_rules

    def _check_length_contradiction(self, desc1: str, desc2: str) -> bool:
        """文字数範囲の矛盾チェック"""
        # 数値範囲を抽出
        numbers1 = re.findall(r'\d+', desc1)
        numbers2 = re.findall(r'\d+', desc2)

        if not numbers1 or not numbers2:
            return False

        # 範囲が異なる場合は矛盾の可能性
        return numbers1 != numbers2

    def _detect_priority_contradictions(self):
        """優先度の矛盾検出"""
        logger.info("=" * 60)
        logger.info("2. 優先度の矛盾検出")
        logger.info("=" * 60)

        # 同じ内容なのに優先度が異なるルールを検出
        similar_rules = {}

        for rule_id, rule in self.registry.rules.items():
            # キーワードで分類
            keywords = self._extract_keywords(rule.description)
            key = tuple(sorted(keywords))

            similar_rules.setdefault(key, []).append((rule_id, rule))

        contradictions_found = 0

        for key, rules in similar_rules.items():
            if len(rules) > 1:
                priorities = {rule.priority.value for _, rule in rules}
                if len(priorities) > 1:
                    # 優先度が異なる
                    self.contradictions.append(Contradiction(
                        rule1_id=rules[0][0],
                        rule2_id=rules[1][0],
                        contradiction_type="優先度の不一致",
                        severity="MEDIUM",
                        description=f"類似内容だが優先度が異なる: {priorities}",
                        evidence=[f"{r[0]}: {r[1].description}" for r in rules]
                    ))
                    contradictions_found += 1

        logger.info(f"検出された優先度矛盾: {contradictions_found}件\n")

    def _extract_keywords(self, text: str) -> Set[str]:
        """キーワード抽出"""
        # 日本語の重要単語を抽出（簡易版）
        keywords = set()

        important_words = [
            'エピソード', '文字', '数値', 'API', 'ダミー', 'データ',
            '品質', 'スコア', '具体', '感銘', 'グループ', '個人',
            '表示名', '括弧', 'カラム', 'スキーマ'
        ]

        for word in important_words:
            if word in text:
                keywords.add(word)

        return keywords

    def _detect_implementation_contradictions(self):
        """実装レベルの矛盾検出"""
        logger.info("=" * 60)
        logger.info("3. 実装レベルの矛盾検出")
        logger.info("=" * 60)

        # pdca_guardian.pyから実装を抽出
        contradictions_found = 0

        # 例: ルールAが「Xを禁止」、ルールBが「Xを推奨」
        forbidden_patterns = self._extract_forbidden_patterns()
        required_patterns = self._extract_required_patterns()

        # 禁止と必須の衝突を検出
        for forbidden_rule, forbidden_item in forbidden_patterns:
            for required_rule, required_item in required_patterns:
                if self._items_conflict(forbidden_item, required_item):
                    self.contradictions.append(Contradiction(
                        rule1_id=forbidden_rule,
                        rule2_id=required_rule,
                        contradiction_type="禁止と必須の衝突",
                        severity="CRITICAL",
                        description=f"{forbidden_rule}が禁止、{required_rule}が必須",
                        evidence=[forbidden_item, required_item]
                    ))
                    contradictions_found += 1

        logger.info(f"検出された実装矛盾: {contradictions_found}件\n")

    def _extract_forbidden_patterns(self) -> List[Tuple[str, str]]:
        """禁止パターンを抽出"""
        patterns = []

        # RULE_XXX.*禁止 のパターンを検索
        pattern = r'(RULE_\d+)[^\n]*禁止[^\n]*([^\n]+)'
        matches = re.finditer(pattern, self.pdca_source)

        for match in matches:
            rule_id = match.group(1)
            forbidden_item = match.group(2).strip()
            patterns.append((rule_id, forbidden_item))

        return patterns

    def _extract_required_patterns(self) -> List[Tuple[str, str]]:
        """必須パターンを抽出"""
        patterns = []

        # RULE_XXX.*必須 のパターンを検索
        pattern = r'(RULE_\d+)[^\n]*必須[^\n]*([^\n]+)'
        matches = re.finditer(pattern, self.pdca_source)

        for match in matches:
            rule_id = match.group(1)
            required_item = match.group(2).strip()
            patterns.append((rule_id, required_item))

        return patterns

    def _items_conflict(self, item1: str, item2: str) -> bool:
        """アイテムが衝突するかチェック"""
        # 同じキーワードが含まれていれば衝突の可能性
        keywords1 = set(item1.split())
        keywords2 = set(item2.split())

        return len(keywords1 & keywords2) > 0

    def _detect_category_contradictions(self):
        """カテゴリの矛盾検出"""
        logger.info("=" * 60)
        logger.info("4. カテゴリの矛盾検出")
        logger.info("=" * 60)

        # 同じルールIDが異なるカテゴリに分類されている
        contradictions_found = 0

        # episode_guardian_config.jsonと比較
        config_path = Path("episode_guardian_config.json")
        if config_path.exists():
            with open(config_path, 'r') as f:
                config = json.load(f)

            unified_rules = config.get('unified_rules', {})
            categories_in_config = unified_rules.get('categories', {})

            for category, rule_ids in categories_in_config.items():
                for rule_id in rule_ids:
                    if rule_id in self.registry.rules:
                        registry_category = self.registry.rules[rule_id].category.value

                        if registry_category != category:
                            self.contradictions.append(Contradiction(
                                rule1_id=rule_id,
                                rule2_id=rule_id,
                                contradiction_type="カテゴリ不一致",
                                severity="LOW",
                                description=f"レジストリ: {registry_category}, 設定: {category}",
                                evidence=[f"Registry: {registry_category}", f"Config: {category}"]
                            ))
                            contradictions_found += 1

        logger.info(f"検出されたカテゴリ矛盾: {contradictions_found}件\n")

    def _detect_description_contradictions(self):
        """説明文の矛盾検出"""
        logger.info("=" * 60)
        logger.info("5. 説明文の矛盾検出")
        logger.info("=" * 60)

        contradictions_found = 0

        # 「説明なし」のルールが多数存在
        no_description = [
            rule_id for rule_id, rule in self.registry.rules.items()
            if rule.description == "（説明なし）"
        ]

        if no_description:
            logger.warning(f"⚠️ 説明なしのルール: {len(no_description)}件")
            logger.warning(f"  対象: {', '.join(no_description[:10])}...")

            self.contradictions.append(Contradiction(
                rule1_id="SYSTEM",
                rule2_id="MULTIPLE",
                contradiction_type="説明文の欠如",
                severity="HIGH",
                description=f"{len(no_description)}件のルールに説明がない",
                evidence=no_description[:20]
            ))
            contradictions_found += 1

        logger.info(f"検出された説明文問題: {contradictions_found}件\n")

    def _generate_report(self):
        """矛盾レポート生成"""
        logger.info("=" * 60)
        logger.info("📊 矛盾分析結果サマリー")
        logger.info("=" * 60)

        total = len(self.contradictions)
        logger.info(f"総矛盾数: {total}件\n")

        # 深刻度別
        by_severity = {}
        for c in self.contradictions:
            by_severity.setdefault(c.severity, []).append(c)

        for severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']:
            count = len(by_severity.get(severity, []))
            if count > 0:
                logger.info(f"  {severity}: {count}件")

        # タイプ別
        logger.info("\n矛盾タイプ別:")
        by_type = {}
        for c in self.contradictions:
            by_type.setdefault(c.contradiction_type, []).append(c)

        for ctype, contradictions in by_type.items():
            logger.info(f"  {ctype}: {len(contradictions)}件")

        # 詳細出力
        if self.contradictions:
            logger.info("\n" + "=" * 60)
            logger.info("詳細な矛盾リスト")
            logger.info("=" * 60)

            for i, c in enumerate(self.contradictions[:10], 1):
                logger.info(f"\n{i}. [{c.severity}] {c.contradiction_type}")
                logger.info(f"   ルール: {c.rule1_id} ⚔️ {c.rule2_id}")
                logger.info(f"   説明: {c.description}")
                if c.evidence:
                    logger.info(f"   証拠: {c.evidence[:2]}")

            if len(self.contradictions) > 10:
                logger.info(f"\n... 他 {len(self.contradictions) - 10}件")

        # JSON出力
        report = {
            'total_contradictions': total,
            'by_severity': {k: len(v) for k, v in by_severity.items()},
            'by_type': {k: len(v) for k, v in by_type.items()},
            'contradictions': [
                {
                    'rule1_id': c.rule1_id,
                    'rule2_id': c.rule2_id,
                    'type': c.contradiction_type,
                    'severity': c.severity,
                    'description': c.description,
                    'evidence': c.evidence[:5]  # 最初の5件のみ
                }
                for c in self.contradictions
            ]
        }

        with open("rule_contradictions_report.json", 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"\n📄 詳細レポート: rule_contradictions_report.json")


def main():
    """メイン処理"""
    analyzer = RuleContradictionAnalyzer()
    contradictions = analyzer.analyze_all_contradictions()

    logger.info("\n" + "=" * 60)
    if contradictions:
        logger.warning(f"⚠️ {len(contradictions)}件の矛盾が検出されました")
        logger.info("詳細は rule_contradictions_report.json を参照してください")
    else:
        logger.info("✅ ルール間の矛盾は検出されませんでした")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
