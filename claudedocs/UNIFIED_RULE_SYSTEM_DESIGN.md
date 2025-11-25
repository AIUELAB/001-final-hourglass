# 統合ルール管理システム設計書

**作成日**: 2025年10月2日
**目的**: 散在したルールファイルを統合し、ルールが確実に適用されるシステムの構築

---

## 🎯 設計目標

### 主要目標
1. **Single Source of Truth**: すべてのルールを1つのシステムで管理
2. **確実な適用**: ルールが必ず適用される仕組み
3. **重複排除**: 同じルールの複数定義を完全排除
4. **後方互換性**: 既存システムとの互換性を保持

---

## 📊 現状分析

### 発見された問題

#### 1. ルールファイルの散在
```
rules_registry.json         : 171ルール (中央レジストリ)
pdca_rules.json            : 24ルール (重複多数)
pdca_guardian_rules.json   : 14ルール (RULE_081-097固有)
episode_guardian_config.json: 74ルール参照 (設定のみ)
```

#### 2. 重複ルール (23個)
- **RULE_160, 165-169**: 3ファイルに重複
- **RULE_077-080, 151-164**: 2ファイルに重複

#### 3. 不一致の内容
- `RULE_151`: registry「132-250文字」vs pdca「150-300文字」
- バージョン情報の不整合
- 更新日時の矛盾

#### 4. ファイル固有ルール
- `pdca_guardian_rules.json`: RULE_081-097 (registryに存在しない)
- `pdca_rules.json`: RATE_LIMIT_098
- `rules_registry.json`: 50個の固有ルール

#### 5. 実装の混乱
- `pdca_guardian.py`: ハードコードされた`ViolationType`
- 複数のPythonファイルが異なるJSONを参照
- ルールローディングロジックが不明確

---

## 🏗️ 統合システム設計

### アーキテクチャ概要

```
┌─────────────────────────────────────────────────┐
│   Unified Rule Registry (統合ルールレジストリ)   │
│   unified_rules.json (Single Source of Truth)   │
│   - 全192ルールを統合                             │
│   - 重複排除済み                                  │
│   - バージョン管理                                │
└─────────────────┬───────────────────────────────┘
                  │
      ┌───────────┴───────────┐
      │                       │
┌─────▼──────┐      ┌────────▼────────┐
│ Rule Loader │      │ Rule Validator  │
│ (読み込み)   │      │ (検証エンジン)   │
└─────┬──────┘      └────────┬────────┘
      │                       │
      │    ┌──────────────────┘
      │    │
┌─────▼────▼──────────────────────────────┐
│   Rule Application Layer (適用層)       │
│   - PDCAGuardian                        │
│   - EpisodeGuardian                     │
│   - FactChecker                         │
│   - その他の検証システム                 │
└─────────────────────────────────────────┘
```

---

## 📋 統合ルールスキーマ

### unified_rules.json 構造

```json
{
  "metadata": {
    "version": "1.0.0",
    "created_at": "2025-10-02T00:00:00",
    "last_updated": "2025-10-02T00:00:00",
    "total_rules": 192,
    "sources": [
      "rules_registry.json",
      "pdca_rules.json",
      "pdca_guardian_rules.json"
    ]
  },
  "rules": {
    "RULE_001": {
      "rule_id": "RULE_001",
      "name": "ルール名",
      "description": "詳細説明",
      "category": "data_quality|episode_format|episode_content|entity_type",
      "priority": "CRITICAL|HIGH|MEDIUM|LOW",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "status": "active|deprecated|superseded",
      "version": "v1.0.0",
      "created_at": "2025-XX-XX",
      "updated_at": "2025-XX-XX",
      "
": "pdca_guardian.py",
      "check_function": "check_function_name",
      "violation_type": "VIOLATION_TYPE_ENUM",
      "validation_logic": "検証ロジックの説明",
      "examples": {
        "valid": ["正しい例1", "正しい例2"],
        "invalid": ["誤った例1", "誤った例2"]
      },
      "related_rules": ["RULE_002", "RULE_003"],
      "supersedes": null,
      "superseded_by": null,
      "tags": ["tag1", "tag2"],
      "source_files": ["rules_registry.json", "pdca_rules.json"],
      "conflict_resolution": {
        "resolved_at": "2025-10-02",
        "resolution": "最新版を採用",
        "merged_from": ["pdca_rules.json v5.11", "rules_registry.json v1.0.0"]
      }
    }
  },
  "categories": {
    "data_quality": {
      "description": "データ品質関連ルール",
      "rule_count": 60,
      "rules": ["RULE_001", "RULE_002", ...]
    },
    "episode_format": {
      "description": "エピソード形式ルール",
      "rule_count": 20,
      "rules": ["RULE_101", "RULE_151", ...]
    },
    "episode_content": {
      "description": "エピソード内容ルール",
      "rule_count": 15,
      "rules": ["RULE_161", "RULE_166", ...]
    },
    "entity_type": {
      "description": "エンティティタイプルール",
      "rule_count": 5,
      "rules": ["ENTITY_TYPE_001", ...]
    }
  },
  "deprecated_rules": {
    "RULE_XXX": {
      "deprecated_at": "2025-XX-XX",
      "reason": "RULE_YYYに統合",
      "replacement": "RULE_YYY"
    }
  }
}
```

---

## 🔧 統合ルールローダー

### unified_rule_loader.py

```python
#!/usr/bin/env python3
"""
統合ルールローダー - Single Source of Truthからルールをロード
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


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
    check_function: Optional[str] = None
    violation_type: Optional[str] = None
    validation_logic: Optional[str] = None
    examples: Optional[Dict] = None
    related_rules: Optional[List[str]] = None


class UnifiedRuleLoader:
    """統合ルールローダー"""

    UNIFIED_RULES_PATH = Path("unified_rules.json")

    def __init__(self):
        self.rules: Dict[str, Rule] = {}
        self.categories: Dict[str, List[str]] = {}
        self.metadata: Dict = {}

    def load_rules(self) -> bool:
        """統合ルールファイルをロード"""
        try:
            if not self.UNIFIED_RULES_PATH.exists():
                raise FileNotFoundError(
                    f"統合ルールファイルが見つかりません: {self.UNIFIED_RULES_PATH}"
                )

            with open(self.UNIFIED_RULES_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self.metadata = data.get('metadata', {})
            self.categories = data.get('categories', {})

            # ルールをロード
            for rule_id, rule_data in data.get('rules', {}).items():
                self.rules[rule_id] = Rule(**rule_data)

            print(f"✅ {len(self.rules)}個のルールをロードしました")
            return True

        except Exception as e:
            print(f"❌ ルールロードエラー: {e}")
            return False

    def get_rule(self, rule_id: str) -> Optional[Rule]:
        """指定したルールを取得"""
        return self.rules.get(rule_id)

    def get_rules_by_category(self, category: str) -> List[Rule]:
        """カテゴリ別にルールを取得"""
        rule_ids = self.categories.get(category, {}).get('rules', [])
        return [self.rules[rid] for rid in rule_ids if rid in self.rules]

    def get_active_rules(self) -> List[Rule]:
        """アクティブなルールのみ取得"""
        return [r for r in self.rules.values() if r.status == 'active']

    def get_critical_rules(self) -> List[Rule]:
        """CRITICAL優先度のルールを取得"""
        return [r for r in self.rules.values()
                if r.priority == 'CRITICAL' and r.status == 'active']
```

---

## 🔄 マイグレーション戦略

### Phase 1: 統合ルールファイル作成

```python
# scripts/create_unified_rules.py

def merge_rules():
    """3つのJSONファイルをマージ"""

    # 1. rules_registry.json をベースとする
    # 2. pdca_guardian_rules.json から RULE_081-097 を追加
    # 3. pdca_rules.json から重複を除外して追加
    # 4. 重複ルールの最新版を選択
    # 5. バージョン情報を統一

    pass
```

### Phase 2: ローダーの統合

```python
# pdca_guardian.py の修正

from unified_rule_loader import UnifiedRuleLoader

class PDCAGuardian:
    def __init__(self):
        self.rule_loader = UnifiedRuleLoader()
        self.rule_loader.load_rules()

        # 既存コードとの互換性を保持
        self._migrate_violation_types()
```

### Phase 3: 段階的移行

1. **Week 1**: 統合ルールファイル作成・検証
2. **Week 2**: ローダー実装・単体テスト
3. **Week 3**: PDCAGuardian統合・互換性確認
4. **Week 4**: EpisodeGuardian統合
5. **Week 5**: 全体テスト・本番適用

---

## ✅ 重複解決ルール

### ルールマージの優先順位

1. **最新版優先**: 更新日時が最新のものを採用
2. **詳細度優先**: 説明が詳細な方を採用
3. **registry優先**: 同条件なら`rules_registry.json`を採用

### 具体例: RULE_160

```json
// pdca_rules.json: 150-300文字 (2025-09-21)
// rules_registry.json: 132-250文字 (2025-10-02)
// → registry優先 (最新 + 詳細)

{
  "rule_id": "RULE_160",
  "name": "エピソード文字数150-250文字制限",
  "description": "エピソードの文字数を150文字以上250文字以下に厳格に制限",
  "character_limits": {
    "min": 150,
    "max": 250
  },
  "conflict_resolution": {
    "resolved_at": "2025-10-02",
    "resolution": "registry版を採用（最新かつ実績値ベース）",
    "merged_from": [
      "pdca_rules.json v5.5 (150-300)",
      "rules_registry.json v1.0.0 (150-250)"
    ]
  }
}
```

---

## 🧪 テスト戦略

### 単体テスト

```python
# tests/test_unified_rule_loader.py

def test_load_all_rules():
    """全ルールが正しくロードされるか"""
    loader = UnifiedRuleLoader()
    assert loader.load_rules() == True
    assert len(loader.rules) == 192

def test_no_duplicates():
    """重複ルールがないか"""
    loader = UnifiedRuleLoader()
    loader.load_rules()
    rule_ids = list(loader.rules.keys())
    assert len(rule_ids) == len(set(rule_ids))

def test_all_active_rules_have_check_function():
    """アクティブルールすべてにcheck_functionがあるか"""
    loader = UnifiedRuleLoader()
    loader.load_rules()
    active = loader.get_active_rules()
    for rule in active:
        assert rule.check_function is not None
```

### 統合テスト

```python
# tests/test_pdca_guardian_integration.py

def test_pdca_loads_unified_rules():
    """PDCAGuardianが統合ルールを正しくロードするか"""
    guardian = PDCAGuardian()
    assert len(guardian.rules) > 0

def test_backward_compatibility():
    """既存のViolationTypeとの互換性"""
    guardian = PDCAGuardian()
    # 既存の違反検出が動作するか確認
```

---

## 📝 移行チェックリスト

### 準備フェーズ
- [x] 散在ルールファイルの調査完了
- [x] 重複ルールの特定完了
- [x] 統合システム設計完了
- [ ] 統合ルールスキーマ確定
- [ ] マイグレーションスクリプト作成

### 実装フェーズ
- [ ] `unified_rules.json` 生成
- [ ] `UnifiedRuleLoader` 実装
- [ ] 単体テスト作成・実行
- [ ] PDCAGuardian統合
- [ ] EpisodeGuardian統合

### 検証フェーズ
- [ ] 全ルールのロード確認
- [ ] 重複排除の確認
- [ ] 既存機能の動作確認
- [ ] パフォーマンステスト

### 本番適用フェーズ
- [ ] 段階的ロールアウト
- [ ] モニタリング
- [ ] 旧ファイルのアーカイブ

---

## 🎯 成功基準

1. **ルール統合率**: 100% (192/192ルール)
2. **重複排除率**: 100% (0重複)
3. **既存機能互換性**: 100% (全機能動作)
4. **パフォーマンス**: ルールロード時間 < 1秒
5. **保守性**: Single Source of Truth確立

---

## 📚 参考資料

- `rules_registry.json`: 中央レジストリ (171ルール)
- `pdca_rules.json`: PDCAルール (24ルール)
- `pdca_guardian_rules.json`: Wikipediaルール (14ルール)
- `pdca_guardian.py`: 実装ロジック
- `episode_guardian.py`: エピソード検証

---

**次のステップ**: 統合ルールファイル `unified_rules.json` の生成スクリプト作成
