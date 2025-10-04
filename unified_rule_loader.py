#!/usr/bin/env python3
"""
統合ルールローダー - Unified Rule Loader

Single Source of Truth (unified_rules.json) からルールをロードし、
すべてのシステムが同じルール定義を使用することを保証します。

使用例:
    loader = UnifiedRuleLoader()
    loader.load_rules()

    # 特定ルールの取得
    rule = loader.get_rule("RULE_001")

    # カテゴリ別取得
    data_quality_rules = loader.get_rules_by_category("data_quality")

    # アクティブなルールのみ
    active_rules = loader.get_active_rules()
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class RuleCategory(Enum):
    """ルールカテゴリ"""
    DATA_QUALITY = "data_quality"
    EPISODE_FORMAT = "episode_format"
    EPISODE_CONTENT = "episode_content"
    ENTITY_TYPE = "entity_type"


class RulePriority(Enum):
    """ルール優先度"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class RuleStatus(Enum):
    """ルールステータス"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


@dataclass
class Rule:
    """ルールデータクラス"""
    rule_id: str
    name: str
    description: str
    category: str
    priority: str
    severity: str
    status: str
    version: str
    created_at: str
    updated_at: str
    source_file: str
    check_function: Optional[str] = None
    violation_type: Optional[str] = None
    validation_logic: Optional[str] = None
    examples: Optional[Any] = None  # Dict or List
    related_rules: List[str] = field(default_factory=list)
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    source_files: List[str] = field(default_factory=list)
    conflict_resolution: Optional[Dict[str, Any]] = None
    implementation: Optional[Dict[str, Any]] = None  # pdca_guardian_rules用

    def is_active(self) -> bool:
        """アクティブなルールか判定"""
        return self.status == RuleStatus.ACTIVE.value

    def is_critical(self) -> bool:
        """クリティカルなルールか判定"""
        return self.priority == RulePriority.CRITICAL.value or self.severity == "CRITICAL"

    def is_high_priority(self) -> bool:
        """高優先度なルールか判定"""
        return self.priority in [RulePriority.CRITICAL.value, RulePriority.HIGH.value]


class UnifiedRuleLoader:
    """
    統合ルールローダー - Single Source of Truthからルールを読み込む

    すべてのシステムが同じルール定義を使用することを保証し、
    ルールの散在による適用漏れを防止します。
    """

    # unified_rules.jsonのパス（プロジェクトルート）
    UNIFIED_RULES_PATH = Path(__file__).parent / "unified_rules.json"

    def __init__(self, custom_path: Optional[Path] = None):
        """
        初期化

        Args:
            custom_path: カスタムのunified_rules.jsonパス（テスト用）
        """
        self.rules: Dict[str, Rule] = {}
        self.categories: Dict[str, Any] = {}
        self.metadata: Dict[str, Any] = {}
        self.deprecated_rules: Dict[str, Any] = {}
        self._rules_path = custom_path or self.UNIFIED_RULES_PATH
        self._loaded = False

    def load_rules(self, force_reload: bool = False) -> bool:
        """
        統合ルールファイルをロード

        Args:
            force_reload: 既にロード済みでも再読み込みするか

        Returns:
            ロード成功時True、失敗時False

        Raises:
            FileNotFoundError: unified_rules.jsonが存在しない
            json.JSONDecodeError: JSONパースエラー
        """
        if self._loaded and not force_reload:
            print(f"✅ ルールは既にロード済みです（{len(self.rules)}個）")
            return True

        try:
            if not self._rules_path.exists():
                raise FileNotFoundError(
                    f"統合ルールファイルが見つかりません: {self._rules_path}\n"
                    f"scripts/create_unified_rules.py を実行してください"
                )

            with open(self._rules_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # メタデータ読み込み
            self.metadata = data.get('metadata', {})
            self.categories = data.get('categories', {})
            self.deprecated_rules = data.get('deprecated_rules', {})

            # ルール読み込み
            rules_data = data.get('rules', {})
            for rule_id, rule_dict in rules_data.items():
                try:
                    # Ruleオブジェクトに変換
                    self.rules[rule_id] = Rule(**rule_dict)
                except TypeError as e:
                    print(f"⚠️ {rule_id}のロードに失敗（スキップ）: {e}")
                    continue

            self._loaded = True

            print(f"✅ {len(self.rules)}個のルールをロードしました")
            print(f"   バージョン: {self.metadata.get('version', 'unknown')}")
            print(f"   最終更新: {self.metadata.get('last_updated', 'unknown')}")
            print(f"   カテゴリ数: {len(self.categories)}")

            return True

        except FileNotFoundError as e:
            print(f"❌ ルールロードエラー: {e}")
            return False
        except json.JSONDecodeError as e:
            print(f"❌ JSONパースエラー: {e}")
            return False
        except Exception as e:
            print(f"❌ 予期しないエラー: {e}")
            import traceback
            traceback.print_exc()
            return False

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """
        指定したルールを取得

        Args:
            rule_id: ルールID（例: "RULE_001"）

        Returns:
            Ruleオブジェクト、存在しない場合None
        """
        if not self._loaded:
            print("⚠️ ルールが未ロードです。load_rules()を先に実行してください")
            return None

        return self.rules.get(rule_id)

    def get_rules_by_category(self, category: str) -> List[Rule]:
        """
        カテゴリ別にルールを取得

        Args:
            category: カテゴリ名（例: "data_quality"）

        Returns:
            Ruleオブジェクトのリスト
        """
        if not self._loaded:
            print("⚠️ ルールが未ロードです。load_rules()を先に実行してください")
            return []

        category_info = self.categories.get(category, {})
        rule_ids = category_info.get('rules', [])

        return [self.rules[rid] for rid in rule_ids if rid in self.rules]

    def get_active_rules(self) -> List[Rule]:
        """
        アクティブなルールのみ取得

        Returns:
            アクティブなRuleオブジェクトのリスト
        """
        if not self._loaded:
            print("⚠️ ルールが未ロードです。load_rules()を先に実行してください")
            return []

        return [rule for rule in self.rules.values() if rule.is_active()]

    def get_critical_rules(self) -> List[Rule]:
        """
        CRITICAL優先度のルールを取得

        Returns:
            CRITICALなRuleオブジェクトのリスト
        """
        if not self._loaded:
            print("⚠️ ルールが未ロードです。load_rules()を先に実行してください")
            return []

        return [rule for rule in self.rules.values()
                if rule.is_critical() and rule.is_active()]

    def get_rules_by_priority(self, priority: str) -> List[Rule]:
        """
        優先度別にルールを取得

        Args:
            priority: 優先度（CRITICAL, HIGH, MEDIUM, LOW）

        Returns:
            指定優先度のRuleオブジェクトのリスト
        """
        if not self._loaded:
            print("⚠️ ルールが未ロードです。load_rules()を先に実行してください")
            return []

        return [rule for rule in self.rules.values()
                if rule.priority == priority and rule.is_active()]

    def get_rules_by_tag(self, tag: str) -> List[Rule]:
        """
        タグ別にルールを取得

        Args:
            tag: タグ名

        Returns:
            指定タグを持つRuleオブジェクトのリスト
        """
        if not self._loaded:
            print("⚠️ ルールが未ロードです。load_rules()を先に実行してください")
            return []

        return [rule for rule in self.rules.values()
                if tag in rule.tags]

    def search_rules(self, keyword: str) -> List[Rule]:
        """
        ルールを検索（名前・説明に含まれるもの）

        Args:
            keyword: 検索キーワード

        Returns:
            マッチしたRuleオブジェクトのリスト
        """
        if not self._loaded:
            print("⚠️ ルールが未ロードです。load_rules()を先に実行してください")
            return []

        keyword_lower = keyword.lower()
        return [rule for rule in self.rules.values()
                if keyword_lower in rule.name.lower()
                or keyword_lower in rule.description.lower()]

    def get_statistics(self) -> Dict[str, Any]:
        """
        ルール統計情報を取得

        Returns:
            統計情報の辞書
        """
        if not self._loaded:
            return {"error": "ルールが未ロードです"}

        active_rules = self.get_active_rules()
        critical_rules = self.get_critical_rules()

        category_counts = {}
        for category_name, category_data in self.categories.items():
            category_counts[category_name] = category_data.get('rule_count', 0)

        return {
            "total_rules": len(self.rules),
            "active_rules": len(active_rules),
            "critical_rules": len(critical_rules),
            "deprecated_rules": len(self.deprecated_rules),
            "categories": category_counts,
            "version": self.metadata.get('version', 'unknown'),
            "last_updated": self.metadata.get('last_updated', 'unknown'),
        }

    def validate_rule_references(self) -> List[str]:
        """
        ルール参照の整合性をチェック

        Returns:
            エラーメッセージのリスト（問題がなければ空リスト）
        """
        if not self._loaded:
            return ["ルールが未ロードです"]

        errors = []

        for rule_id, rule in self.rules.items():
            # related_rulesの存在確認
            for related_id in rule.related_rules:
                if related_id not in self.rules:
                    errors.append(f"{rule_id}: 関連ルール {related_id} が存在しません")

            # supersedes/superseded_byの存在確認
            if rule.supersedes and rule.supersedes not in self.rules:
                errors.append(f"{rule_id}: 置換元ルール {rule.supersedes} が存在しません")

            if rule.superseded_by and rule.superseded_by not in self.rules:
                errors.append(f"{rule_id}: 置換先ルール {rule.superseded_by} が存在しません")

        return errors

    def print_summary(self):
        """統計情報をコンソールに表示"""
        if not self._loaded:
            print("⚠️ ルールが未ロードです。load_rules()を先に実行してください")
            return

        stats = self.get_statistics()

        print("\n" + "=" * 60)
        print("  統合ルールローダー - サマリー")
        print("=" * 60)
        print(f"📊 総ルール数: {stats['total_rules']}")
        print(f"✅ アクティブ: {stats['active_rules']}")
        print(f"🚨 クリティカル: {stats['critical_rules']}")
        print(f"📦 非推奨: {stats['deprecated_rules']}")
        print(f"\n📂 カテゴリ別:")
        for category, count in stats['categories'].items():
            print(f"   - {category}: {count}個")
        print(f"\n🔖 バージョン: {stats['version']}")
        print(f"📅 最終更新: {stats['last_updated']}")
        print("=" * 60 + "\n")


def main():
    """テスト実行用のメイン関数"""
    print("=" * 60)
    print("  統合ルールローダー - テスト実行")
    print("=" * 60)
    print()

    # ローダー初期化
    loader = UnifiedRuleLoader()

    # ルールロード
    if not loader.load_rules():
        print("❌ ルールのロードに失敗しました")
        return

    # サマリー表示
    loader.print_summary()

    # 整合性チェック
    print("🔍 ルール参照の整合性チェック...")
    errors = loader.validate_rule_references()
    if errors:
        print(f"⚠️ {len(errors)}件の問題を検出:")
        for error in errors[:5]:  # 最初の5件のみ表示
            print(f"   - {error}")
        if len(errors) > 5:
            print(f"   ... 他 {len(errors) - 5} 件")
    else:
        print("✅ 整合性チェック完了（問題なし）")

    # サンプル検索
    print("\n🔍 サンプル検索: 'Wikipedia'")
    results = loader.search_rules("Wikipedia")
    print(f"   検索結果: {len(results)}件")
    for rule in results[:3]:
        print(f"   - {rule.rule_id}: {rule.name}")

    print("\n" + "=" * 60)
    print("  ✅ テスト完了")
    print("=" * 60)


if __name__ == '__main__':
    main()
