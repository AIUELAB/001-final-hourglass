#!/usr/bin/env python3
"""
統合ルール管理システム (Unified Rule Management System)
Unified Rule Management System

目的:
1. 散在するルールファイルの一元管理
2. ルールの重複・競合の検出と解決
3. PDCAガーディアンとの完全統合
4. ルールバージョン管理とロールバック機能

設計原則:
- Single Source of Truth: rules_registry.json が唯一の真実
- Immutable History: すべてのルール変更を記録
- Fail-Fast: ルール競合は即座に検出
- Backward Compatible: 既存システムとの互換性維持

Created: 2025-10-02
Version: 1.0.0
"""

import json
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from enum import Enum

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


class RulePriority(Enum):
    """ルール優先度"""
    CRITICAL = 1    # 違反したら即座に停止
    HIGH = 2        # 重要な警告
    MEDIUM = 3      # 通常の警告
    LOW = 4         # 情報レベル


class RuleStatus(Enum):
    """ルールステータス"""
    ACTIVE = "active"           # アクティブ
    DEPRECATED = "deprecated"   # 非推奨（警告のみ）
    DISABLED = "disabled"       # 無効化
    REPLACED = "replaced"       # 別ルールで置換済み


class RuleCategory(Enum):
    """ルールカテゴリ"""
    # PDCAガーディアン由来（RULE_001-169）
    DATA_QUALITY = "data_quality"           # データ品質
    API_USAGE = "api_usage"                 # API使用
    EPISODE_FORMAT = "episode_format"       # エピソード形式
    EPISODE_CONTENT = "episode_content"     # エピソード内容
    ENTITY_TYPE = "entity_type"             # エンティティタイプ
    DISPLAY_NAME = "display_name"           # 表示名
    DATABASE_SCHEMA = "database_schema"     # データベーススキーマ

    # EpisodeGuardian由来
    VALIDATION = "validation"               # バリデーション
    GROUP_DETECTION = "group_detection"     # グループ検出

    # システム全体
    INTEGRATION = "integration"             # システム統合
    SECURITY = "security"                   # セキュリティ


@dataclass
class Rule:
    """統一ルールオブジェクト"""
    rule_id: str                    # RULE_001, ENTITY_TYPE_001, etc.
    name: str                       # 人間可読な名前
    description: str                # 詳細説明
    category: RuleCategory          # カテゴリ
    priority: RulePriority          # 優先度
    status: RuleStatus              # ステータス

    # 実装情報
    source_file: str                # 実装ファイル
    function_name: Optional[str]    # 検証関数名

    # バージョン管理
    created_at: str                 # 作成日時
    updated_at: str                 # 更新日時
    version: str                    # バージョン (v1.0.0)

    # 関連情報
    related_rules: List[str]        # 関連ルール
    replaces: Optional[str]         # 置換対象ルール
    replaced_by: Optional[str]      # 置換先ルール

    # メタデータ
    tags: List[str]                 # タグ
    examples: List[str]             # 違反例

    def to_dict(self) -> Dict:
        """辞書に変換"""
        d = asdict(self)
        d['category'] = self.category.value
        d['priority'] = self.priority.value
        d['status'] = self.status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict) -> 'Rule':
        """辞書から復元"""
        data['category'] = RuleCategory(data['category'])
        data['priority'] = RulePriority(data['priority'])
        data['status'] = RuleStatus(data['status'])
        return cls(**data)


class UnifiedRuleRegistry:
    """統合ルールレジストリ"""

    def __init__(self, registry_path: str = "rules_registry.json"):
        self.registry_path = Path(registry_path)
        self.rules: Dict[str, Rule] = {}
        self.history: List[Dict] = []
        self.checksum: Optional[str] = None

        self._load_registry()

    def _load_registry(self):
        """レジストリをロード"""
        if self.registry_path.exists():
            with open(self.registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # ルールを復元（2つの形式に対応）
                # 形式1: {"rules": {...}, "history": [...]}
                # 形式2: {"RULE_001": {...}, "RULE_002": {...}}（ルートレベル）

                if 'rules' in data:
                    # 形式1（履歴情報あり）
                    rules_data = data['rules']
                    self.history = data.get('history', [])
                    self.checksum = data.get('checksum')
                else:
                    # 形式2（ルートレベルにルールのみ）
                    rules_data = data
                    self.history = []
                    self.checksum = None

                for rule_id, rule_data in rules_data.items():
                    try:
                        self.rules[rule_id] = Rule.from_dict(rule_data)
                    except Exception as e:
                        logger.warning(f"⚠️ ルール{rule_id}の読み込みに失敗: {e}")
                        continue

                logger.info(f"✅ レジストリロード完了: {len(self.rules)}ルール")
        else:
            logger.warning("⚠️ レジストリファイルが存在しません。新規作成します。")
            self._create_initial_registry()

    def _save_registry(self):
        """レジストリを保存"""
        data = {
            'rules': {rule_id: rule.to_dict() for rule_id, rule in self.rules.items()},
            'history': self.history,
            'checksum': self._calculate_checksum(),
            'last_updated': datetime.now().isoformat(),
            'version': '1.0.0'
        }

        with open(self.registry_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        self.checksum = data['checksum']
        logger.info(f"💾 レジストリ保存完了: {len(self.rules)}ルール")

    def _calculate_checksum(self) -> str:
        """チェックサム計算"""
        content = json.dumps(
            {rule_id: rule.to_dict() for rule_id, rule in sorted(self.rules.items())},
            sort_keys=True
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def _create_initial_registry(self):
        """初期レジストリ作成（既存ルールのマイグレーション）"""
        logger.info("🔄 既存ルールのマイグレーション開始...")

        # pdca_guardian.pyから既存ルールを抽出
        self._migrate_pdca_rules()

        # episode_guardian_config.jsonからルールを抽出
        self._migrate_episode_guardian_rules()

        self._save_registry()
        logger.info("✅ 初期レジストリ作成完了")

    def _migrate_pdca_rules(self):
        """PDCAガーディアンルールのマイグレーション"""
        # RULE_001-169の例（実際は全ルールを網羅）
        sample_pdca_rules = [
            {
                'rule_id': 'RULE_001',
                'name': 'calibrated_score使用禁止',
                'description': 'calibrated_scoreの使用は禁止。必ず実際のAPIで算出したスコアを使用すること。',
                'category': RuleCategory.DATA_QUALITY,
                'priority': RulePriority.CRITICAL,
                'source_file': 'pdca_guardian.py',
                'tags': ['api', 'scoring', 'data_quality']
            },
            {
                'rule_id': 'RULE_100',
                'name': 'クレジット管理の永久化',
                'description': 'すべてのエピソードとCSV出力に開発クレジットを付与すること。',
                'category': RuleCategory.EPISODE_CONTENT,
                'priority': RulePriority.HIGH,
                'source_file': 'pdca_guardian.py',
                'tags': ['credit', 'metadata']
            }
        ]

        for rule_data in sample_pdca_rules:
            rule = Rule(
                rule_id=rule_data['rule_id'],
                name=rule_data['name'],
                description=rule_data['description'],
                category=rule_data['category'],
                priority=rule_data['priority'],
                status=RuleStatus.ACTIVE,
                source_file=rule_data['source_file'],
                function_name=None,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                version='v1.0.0',
                related_rules=[],
                replaces=None,
                replaced_by=None,
                tags=rule_data['tags'],
                examples=[]
            )
            self.rules[rule.rule_id] = rule

        logger.info(f"✅ PDCAルール {len(sample_pdca_rules)}件をマイグレーション")

    def _migrate_episode_guardian_rules(self):
        """EpisodeGuardianルールのマイグレーション"""
        episode_guardian_rules = [
            {
                'rule_id': 'ENTITY_TYPE_001',
                'name': 'グループ名の個人誤登録防止',
                'description': 'グループ名が個人として登録されていないかチェック',
                'category': RuleCategory.ENTITY_TYPE,
                'priority': RulePriority.CRITICAL,
                'source_file': 'episode_guardian.py'
            },
            {
                'rule_id': 'FORMAT_001',
                'name': 'エピソード文字数範囲チェック',
                'description': 'エピソードは180-250文字の範囲内であること',
                'category': RuleCategory.EPISODE_FORMAT,
                'priority': RulePriority.HIGH,
                'source_file': 'episode_guardian.py'
            }
        ]

        for rule_data in episode_guardian_rules:
            rule = Rule(
                rule_id=rule_data['rule_id'],
                name=rule_data['name'],
                description=rule_data['description'],
                category=rule_data['category'],
                priority=rule_data['priority'],
                status=RuleStatus.ACTIVE,
                source_file=rule_data['source_file'],
                function_name=None,
                created_at=datetime.now().isoformat(),
                updated_at=datetime.now().isoformat(),
                version='v1.0.0',
                related_rules=[],
                replaces=None,
                replaced_by=None,
                tags=[],
                examples=[]
            )
            self.rules[rule.rule_id] = rule

        logger.info(f"✅ EpisodeGuardianルール {len(episode_guardian_rules)}件をマイグレーション")

    def add_rule(self, rule: Rule) -> bool:
        """ルール追加"""
        if rule.rule_id in self.rules:
            logger.error(f"❌ ルールID重複: {rule.rule_id}")
            return False

        self.rules[rule.rule_id] = rule

        # 履歴記録
        self.history.append({
            'action': 'add',
            'rule_id': rule.rule_id,
            'timestamp': datetime.now().isoformat()
        })

        self._save_registry()
        logger.info(f"✅ ルール追加: {rule.rule_id}")
        return True

    def update_rule(self, rule_id: str, updates: Dict) -> bool:
        """ルール更新"""
        if rule_id not in self.rules:
            logger.error(f"❌ ルールが存在しません: {rule_id}")
            return False

        rule = self.rules[rule_id]

        # 更新適用
        for key, value in updates.items():
            if hasattr(rule, key):
                setattr(rule, key, value)

        rule.updated_at = datetime.now().isoformat()

        # Enum型を文字列に変換してから履歴記録
        serializable_updates = {}
        for key, value in updates.items():
            if isinstance(value, (RuleCategory, RulePriority, RuleStatus)):
                serializable_updates[key] = value.value
            else:
                serializable_updates[key] = value

        # 履歴記録
        self.history.append({
            'action': 'update',
            'rule_id': rule_id,
            'updates': serializable_updates,
            'timestamp': datetime.now().isoformat()
        })

        self._save_registry()
        logger.info(f"✅ ルール更新: {rule_id}")
        return True

    def deprecate_rule(self, rule_id: str, replacement_id: Optional[str] = None) -> bool:
        """ルールを非推奨化"""
        if rule_id not in self.rules:
            logger.error(f"❌ ルールが存在しません: {rule_id}")
            return False

        self.rules[rule_id].status = RuleStatus.DEPRECATED

        if replacement_id:
            self.rules[rule_id].replaced_by = replacement_id
            if replacement_id in self.rules:
                self.rules[replacement_id].replaces = rule_id

        # 履歴記録
        self.history.append({
            'action': 'deprecate',
            'rule_id': rule_id,
            'replacement_id': replacement_id,
            'timestamp': datetime.now().isoformat()
        })

        self._save_registry()
        logger.info(f"⚠️ ルール非推奨化: {rule_id}")
        return True

    def detect_conflicts(self) -> List[Tuple[str, str, str]]:
        """ルール競合検出"""
        conflicts = []

        # 同じカテゴリ・優先度で似た内容のルールを検出
        rules_by_category = {}
        for rule_id, rule in self.rules.items():
            if rule.status == RuleStatus.ACTIVE:
                key = (rule.category, rule.priority)
                rules_by_category.setdefault(key, []).append(rule)

        for (category, priority), rules in rules_by_category.items():
            for i, rule1 in enumerate(rules):
                for rule2 in rules[i+1:]:
                    # 説明文の類似度チェック（簡易版）
                    if self._similar_descriptions(rule1.description, rule2.description):
                        conflicts.append((
                            rule1.rule_id,
                            rule2.rule_id,
                            f"Similar rules in {category.value}"
                        ))

        return conflicts

    def _similar_descriptions(self, desc1: str, desc2: str, threshold: float = 0.5) -> bool:
        """説明文の類似度判定（簡易版）"""
        words1 = set(desc1.split())
        words2 = set(desc2.split())

        if not words1 or not words2:
            return False

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return (intersection / union) > threshold

    def get_active_rules(self, category: Optional[RuleCategory] = None) -> List[Rule]:
        """アクティブなルールを取得"""
        active = [r for r in self.rules.values() if r.status == RuleStatus.ACTIVE]

        if category:
            active = [r for r in active if r.category == category]

        return sorted(active, key=lambda r: (r.priority.value, r.rule_id))

    def export_to_markdown(self, output_path: str = "RULES_DOCUMENTATION.md"):
        """ルールをMarkdownドキュメントとして出力"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# 統合ルール管理システム - ルール一覧\n\n")
            f.write(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"総ルール数: {len(self.rules)}\n")
            f.write(f"アクティブ: {sum(1 for r in self.rules.values() if r.status == RuleStatus.ACTIVE)}\n")
            f.write(f"非推奨: {sum(1 for r in self.rules.values() if r.status == RuleStatus.DEPRECATED)}\n\n")

            # カテゴリ別に出力
            for category in RuleCategory:
                rules = [r for r in self.rules.values() if r.category == category]
                if not rules:
                    continue

                f.write(f"## {category.value.upper()}\n\n")

                for rule in sorted(rules, key=lambda r: r.rule_id):
                    f.write(f"### {rule.rule_id}: {rule.name}\n\n")
                    f.write(f"**優先度**: {rule.priority.name}\n\n")
                    f.write(f"**ステータス**: {rule.status.value}\n\n")
                    f.write(f"**説明**: {rule.description}\n\n")
                    f.write(f"**実装**: `{rule.source_file}`")
                    if rule.function_name:
                        f.write(f" - `{rule.function_name}()`")
                    f.write("\n\n")

                    if rule.tags:
                        f.write(f"**タグ**: {', '.join(rule.tags)}\n\n")

                    if rule.replaced_by:
                        f.write(f"⚠️ このルールは `{rule.replaced_by}` に置き換えられました\n\n")

                    f.write("---\n\n")

        logger.info(f"📄 ルールドキュメント生成: {output_path}")


def main():
    """テスト実行"""
    logger.info("🚀 統合ルール管理システム - 初期化")

    # レジストリ作成
    registry = UnifiedRuleRegistry()

    # アクティブルール一覧
    logger.info(f"\n📋 アクティブルール: {len(registry.get_active_rules())}件")

    # カテゴリ別統計
    for category in RuleCategory:
        count = len([r for r in registry.rules.values()
                    if r.category == category and r.status == RuleStatus.ACTIVE])
        if count > 0:
            logger.info(f"  {category.value}: {count}件")

    # 競合検出
    conflicts = registry.detect_conflicts()
    if conflicts:
        logger.warning(f"\n⚠️ ルール競合検出: {len(conflicts)}件")
        for rule1_id, rule2_id, reason in conflicts:
            logger.warning(f"  {rule1_id} ⚔️ {rule2_id}: {reason}")
    else:
        logger.info("\n✅ ルール競合なし")

    # Markdownドキュメント生成
    registry.export_to_markdown()

    logger.info("\n✅ 統合ルール管理システム初期化完了")


if __name__ == "__main__":
    main()
