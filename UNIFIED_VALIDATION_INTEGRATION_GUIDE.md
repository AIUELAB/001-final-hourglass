# 統合検証システム統合ガイド

**作成日**: 2025年10月01日
**バージョン**: 1.0.0

---

## 📋 概要

このガイドは、統合検証システム（Unified Validation System）を既存のエピソード生成パイプラインに統合する方法を説明します。

---

## 🎯 統合の目的

1. **品質保証の自動化**: 新規エピソード生成時に自動的に品質検証を実行
2. **統一基準の適用**: PDCAガーディアンとOptimizedValidationSystemの矛盾を解消した統一基準を適用
3. **自動修正**: 可能な違反を自動的に修正
4. **トレーサビリティ**: 全検証履歴を記録し、品質トレンドを追跡

---

## 📁 主要ファイル

### 1. 統合検証システム本体

| ファイル | 説明 |
|---------|------|
| `unified_validation_system.py` | コアの検証ロジック（6つのルール実装） |
| `unified_validation_system_with_persistence.py` | 永続化対応版（設定ファイル読み込み、履歴記録） |
| `unified_validation_config.json` | 検証ルールと動作設定 |

### 2. パイプライン統合

| ファイル | 説明 |
|---------|------|
| `episode_generator_with_unified_validation.py` | 統合検証システムを組み込んだエピソード生成器 |
| `episode_revalidation_system.py` | 既存エピソードのバッチ再検証 |
| `episode_auto_correction_system.py` | 自動修正システム |

---

## 🚀 統合手順

### Step 1: 設定ファイルの確認

`unified_validation_config.json` を確認し、プロジェクトの要件に合わせてカスタマイズ:

```json
{
  "validation_rules": {
    "character_count": {
      "enabled": true,
      "min_chars": 130,
      "max_chars": 250
    },
    "objective_emotional": {
      "enabled": true,
      "ban_subjective_keywords": true
    }
  },
  "integration": {
    "episode_generator": {
      "enabled": true,
      "validate_before_save": true,
      "auto_correct_violations": true,
      "reject_on_failure": true
    }
  }
}
```

### Step 2: 既存エピソード生成器の確認

既存のエピソード生成システムを特定:

```bash
# エピソード生成器のファイルを確認
ls -la *episode*generator*.py

# 例:
# - weekly_episode_generator.py
# - new_episodes_generator.py
# - episode_generator_200chars.py
```

### Step 3: 統合検証システムのインポート

既存のエピソード生成器に以下を追加:

```python
# 既存ファイルの先頭に追加
from unified_validation_system_with_persistence import create_validator

class ExistingEpisodeGenerator:
    def __init__(self):
        # 既存の初期化処理
        # ...

        # 統合検証システムを追加
        self.validator = create_validator("unified_validation_config.json")
```

### Step 4: エピソード生成メソッドに検証を追加

```python
def generate_episode(self, person_data):
    # 既存のエピソード生成ロジック
    episode = self._generate_episode_internal(person_data)

    # 統合検証システムで検証
    validation_result = self.validator.validate_episode(episode)

    # 検証結果を追加
    episode['validation_result'] = {
        'is_valid': validation_result.is_valid,
        'emotional_score': validation_result.emotional_impact_score,
        'specificity_score': validation_result.specificity_score,
        'violations': len(validation_result.violations)
    }

    # 検証失敗時の処理
    if not validation_result.is_valid:
        print(f"⚠️ 検証失敗: {person_data['person_name']}")
        for v in validation_result.violations:
            print(f"  - {v.message}")

        # 設定に応じて自動修正 or 拒否
        if self.validator.config.get("integration", {}).get("episode_generator", {}).get("auto_correct_violations", True):
            episode = self._auto_correct(episode, validation_result)
            # 再検証
            validation_result = self.validator.validate_episode(episode)

        if not validation_result.is_valid and self.validator.config.get("integration", {}).get("episode_generator", {}).get("reject_on_failure", True):
            return None  # エピソード生成を中止

    return episode
```

### Step 5: 自動修正ロジックの追加

```python
def _auto_correct(self, episode, validation_result):
    """自動修正を試行"""
    import re
    corrected_text = episode['episode_text']

    for violation in validation_result.violations:
        if violation.rule_name == "specificity":
            # 年号・日付の削除
            for pattern in [r'\d{4}年', r'令和\d+年', r'平成\d+年', r'\d+月\d+日']:
                corrected_text = re.sub(pattern, '', corrected_text)

        elif violation.rule_name == "objective_emotional":
            # 主観表現の削除
            subjective_words = ["素晴らしい", "すごい", "驚異的", "圧倒的", "感動的", "劇的"]
            for word in subjective_words:
                corrected_text = corrected_text.replace(word, '')

    episode['episode_text'] = corrected_text
    episode['corrections_applied'] = ['auto_correction']
    return episode
```

### Step 6: バッチ処理の統合

```python
def batch_generate_episodes(self, person_list):
    """バッチでエピソードを生成"""
    validated_episodes = []

    for person_data in person_list:
        episode = self.generate_episode(person_data)
        if episode:
            validated_episodes.append(episode)

    # 統計情報
    stats = self.validator.get_statistics()
    print(f"\n=== バッチ生成結果 ===")
    print(f"処理件数: {len(person_list)}")
    print(f"成功: {len(validated_episodes)}")
    print(f"準拠率: {stats['compliance_rate']:.1f}%")

    # 検証履歴を保存
    self.validator.save_validation_history()

    return validated_episodes
```

---

## 🔧 設定のカスタマイズ

### ルールの有効/無効切り替え

`unified_validation_config.json` で各ルールを制御:

```json
{
  "validation_rules": {
    "character_count": {"enabled": true},
    "historical_moment": {"enabled": true},
    "objective_emotional": {"enabled": true},
    "achievement": {"enabled": true},
    "duplicate_age": {"enabled": true},
    "specificity": {"enabled": true}
  }
}
```

### 自動修正の制御

```json
{
  "auto_correction": {
    "enabled": true,
    "max_attempts": 3,
    "corrections": {
      "remove_temporal_noise": true,
      "remove_subjective_expressions": true,
      "fix_age_duplicates": true
    }
  }
}
```

### 品質ゲートの設定

```json
{
  "quality_gates": {
    "enabled": true,
    "fail_on_critical": true,
    "warn_on_important": true,
    "min_compliance_rate": 95.0
  }
}
```

---

## 📊 モニタリングと分析

### 検証履歴の確認

```python
# 統計情報の取得
stats = validator.get_statistics()

print(f"総検証数: {stats['total_validations']}")
print(f"準拠率: {stats['compliance_rate']:.1f}%")
print(f"平均感銘スコア: {stats['avg_emotional_score']:.2f}")
print(f"平均具体性スコア: {stats['avg_specificity_score']:.2f}")
```

### 検証履歴ファイル

`validation_history.json` に全ての検証履歴が記録されます:

```json
[
  {
    "timestamp": "2025-10-01T14:30:00",
    "episode_name": "イチロー",
    "is_valid": true,
    "violation_count": 0,
    "emotional_score": 0.75,
    "specificity_score": 0.85
  }
]
```

---

## 🎯 具体的な統合例

### 例1: weekly_episode_generator.py への統合

```python
# weekly_episode_generator.py
from unified_validation_system_with_persistence import create_validator

class WeeklyEpisodeGenerator:
    def __init__(self):
        self.validator = create_validator()
        # ... 既存の初期化

    def generate_weekly_batch(self):
        # ... 既存の生成ロジック

        # 生成後に検証
        validated_episodes = []
        for episode in generated_episodes:
            result = self.validator.validate_episode(episode)
            if result.is_valid:
                validated_episodes.append(episode)

        return validated_episodes
```

### 例2: 新規エピソード生成パイプライン

```python
from episode_generator_with_unified_validation import ValidatedEpisodeGenerator

# 統合検証システム対応ジェネレータを使用
generator = ValidatedEpisodeGenerator("unified_validation_config.json")

# エピソード生成（自動検証付き）
episode = generator.generate_episode({
    "person_name": "羽生善治",
    "episode_text": "...",
    "user_age": 30,
    "episode_age": 30
})

# 検証成功時のみエピソードが返される
if episode:
    print("✅ 検証済みエピソード生成成功")
```

---

## ✅ チェックリスト

統合完了時に確認:

- [ ] `unified_validation_config.json` がプロジェクトルートに存在
- [ ] 既存エピソード生成器が統合検証システムをインポート
- [ ] エピソード生成メソッドで検証を実行
- [ ] 検証失敗時の処理（自動修正 or 拒否）を実装
- [ ] バッチ処理で検証履歴を保存
- [ ] 統計情報を定期的に確認するロジックを実装
- [ ] Google Sheetsへの同期が既存の `force_sync.py` で動作

---

## 🚨 トラブルシューティング

### 問題: 検証が実行されない

**原因**: 設定ファイルで無効化されている

**解決策**:
```json
{
  "integration": {
    "episode_generator": {
      "enabled": true  // ← これを確認
    }
  }
}
```

### 問題: 自動修正が動作しない

**原因**: 修正可能なルール違反ではない

**解決策**: 手動修正が必要な違反を確認し、`manual_episode_corrections.py` を参考に修正

### 問題: 準拠率が低すぎる

**原因**: ルールが厳しすぎる、または既存データに問題

**解決策**:
1. `episode_revalidation_system.py` で全エピソードを再検証
2. 違反パターンを分析
3. 必要に応じて `unified_validation_config.json` でルールを調整

---

## 📚 関連ドキュメント

- `UNIFIED_VALIDATION_COMPLETION_REPORT.md` - 統合検証システム完成レポート
- `unified_validation_system.py` - コアシステムのソースコード
- `episodes_final_unified_20251001_135250.csv` - 100%準拠達成データ

---

**最終更新**: 2025年10月01日
**次のステップ**: 新規エピソード生成パイプラインへの統合テスト
