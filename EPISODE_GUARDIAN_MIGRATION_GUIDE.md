# EpisodeGuardian移行ガイド

**日付**: 2025年10月1日
**対象**: 既存の検証・修正スクリプトをEpisodeGuardianに統合

---

## 📋 移行対象スクリプト

### 高優先度（即座に移行）

| スクリプト | 機能 | EpisodeGuardian統合版 | ステータス |
|----------|------|---------------------|----------|
| `fact_check_all_100_episodes.py` | 100件包括チェック | `validate_episode_with_guardian.py --csv` | ✅ 完了 |
| `fix_5_problematic_episodes.py` | 問題エピソード修正 | `validate_episode_with_guardian.py` | ✅ 統合済み |
| `fix_remaining_2_episodes.py` | 残り2件修正 | `validate_episode_with_guardian.py` | ✅ 統合済み |
| `generate_ep010_replacement.py` | EP010代替生成 | EpisodeGuardianで検証 | ✅ 完了 |
| `final_verification_with_episode_guardian.py` | 最終検証 | 既に実装 | ✅ 完了 |

### 中優先度（段階的移行）

| スクリプト | 機能 | 移行方法 | ステータス |
|----------|------|---------|----------|
| `comprehensive_fact_check.py` | 包括的ファクトチェック | `validate_episode_with_guardian.py` | ⏳ 保留 |
| `fix_critical_episodes.py` | 重大エピソード修正 | EpisodeGuardian検証後修正 | ⏳ 保留 |
| `fix_duplicate_episodes.py` | 重複エピソード修正 | 手動確認後EpisodeGuardian検証 | ⏳ 保留 |

### 低優先度（オプション）

| スクリプト | 機能 | 移行判断 | ステータス |
|----------|------|---------|----------|
| `add_entity_type_column.py` | entity_type追加 | 不要（DB仕様は個人のみ） | ❌ 移行不要 |
| `check_and_fix_persons.py` | 人物データ確認 | EpisodeGuardianで代替可能 | ⏳ 保留 |
| `fact_checker.py` | ファクトチェッカー | EpisodeGuardianと統合検討 | ⏳ 保留 |

---

## 🔧 移行方法

### パターン1: 単純な検証スクリプト

**移行前**:
```python
# fact_check_all_100_episodes.py
validator = create_validator()
for episode in episodes:
    result = validator.validate_episode(episode)
    if not result.is_valid:
        print(f"失格: {episode['person_name']}")
```

**移行後**:
```bash
python3 validate_episode_with_guardian.py --csv episodes.csv --verbose
```

### パターン2: エピソード修正スクリプト

**移行前**:
```python
# fix_5_problematic_episodes.py
episodes = load_episodes()
fixed_episodes = []
for episode in episodes:
    fixed = fix_episode(episode)
    fixed_episodes.append(fixed)
save_episodes(fixed_episodes)
```

**移行後**:
```python
from episode_guardian import create_episode_guardian

guardian = create_episode_guardian()

# 1. 検証
result = guardian.validate_episode(episode)
if not result.is_valid:
    print(f"失格: {result.message}")
    print(f"改善提案: {result.suggestions}")

# 2. 修正
fixed_episode = apply_fixes(episode, result.suggestions)

# 3. 再検証
final_result = guardian.validate_episode(fixed_episode)
if final_result.is_valid:
    print("✅ 修正成功")
```

### パターン3: エピソード生成スクリプト

**移行前**:
```python
# generate_ep010_replacement.py
episode = generate_episode(person_name, age, text)
validator = create_validator()
result = validator.validate_episode(episode)
```

**移行後**:
```python
from episode_guardian import create_episode_guardian

guardian = create_episode_guardian()

# 生成
episode = generate_episode(person_name, age, text)

# EpisodeGuardianで検証（Entity Type含む）
result = guardian.validate_episode(episode)

if result.is_valid:
    save_episode(episode)
else:
    # Entity Type失敗の場合は別の人物を選択
    if 'ENTITY_TYPE_001' in result.failed_rules:
        print(f"❌ {person_name}はグループです")
        # 代替人物を選択
```

---

## 📊 統合検証スクリプトの使用方法

### validate_episode_with_guardian.py

#### 単一エピソード検証
```bash
python3 validate_episode_with_guardian.py \
  --name "羽生結弦" \
  --age 19 \
  --text "あなたと同じ19歳のとき、羽生結弦はソチ五輪で金メダルを獲得した。..." \
  --category "スポーツ" \
  --verbose
```

**出力例**:
```
🛡️ EpisodeGuardian v1.0.0
   既知のグループ: 36件

✅ 合格: 羽生結弦

検証結果サマリー
総エピソード数: 1件
合格: 1件 (100.0%)
失格: 0件 (0.0%)
```

#### CSVファイル検証
```bash
python3 validate_episode_with_guardian.py \
  --csv episodes_complete_100_20251001.csv \
  --verbose
```

**出力例**:
```
📄 CSVファイル読み込み: episodes_complete_100_20251001.csv
   総エピソード数: 100件

✅ 合格: Ado
✅ 合格: HIKAKIN
...
✅ 合格: 黒澤明

検証結果サマリー
総エピソード数: 100件
合格: 100件 (100.0%)
失格: 0件 (0.0%)

EpisodeGuardianメトリクス
総検証数: 100
Entity Type失敗: 0
グループ検出数: 0
```

#### JSONファイル検証
```bash
python3 validate_episode_with_guardian.py \
  --json episode.json \
  --verbose
```

#### カスタム設定ファイル
```bash
python3 validate_episode_with_guardian.py \
  --csv episodes.csv \
  --config custom_episode_guardian_config.json
```

---

## 🔄 段階的移行プロセス

### フェーズ1: 並行運用（1週間）

1. **既存スクリプトを維持**
   - 現行の検証スクリプトは引き続き使用
   - EpisodeGuardianを並行実行

2. **比較検証**
   ```bash
   # 既存システム
   python3 fact_check_all_100_episodes.py

   # EpisodeGuardian
   python3 validate_episode_with_guardian.py --csv episodes.csv

   # 結果を比較
   diff old_results.txt new_results.txt
   ```

3. **問題の特定と修正**
   - 検証結果の差異を分析
   - EpisodeGuardianの調整

### フェーズ2: 段階的切り替え（2週間）

1. **高優先度スクリプトの切り替え**
   - `fact_check_all_100_episodes.py` → `validate_episode_with_guardian.py`
   - `final_verification_*` → `final_verification_with_episode_guardian.py`

2. **CI/CD統合**
   ```yaml
   # .github/workflows/validate.yml
   - name: Validate episodes
     run: python3 validate_episode_with_guardian.py --csv episodes.csv
   ```

3. **ドキュメント更新**
   - README.mdにEpisodeGuardianの使用方法を追加
   - 既存スクリプトを非推奨マーク

### フェーズ3: 完全移行（1ヶ月）

1. **既存スクリプトの削除またはアーカイブ**
   ```bash
   mkdir -p deprecated/
   mv fact_check_*.py deprecated/
   mv fix_*.py deprecated/
   ```

2. **EpisodeGuardianのみを使用**
   - すべての検証・修正フローでEpisodeGuardianを使用
   - 既存スクリプトは参照のみ

3. **最終検証**
   ```bash
   # 全エピソード検証
   python3 validate_episode_with_guardian.py --csv all_episodes.csv --verbose

   # リグレッションテスト
   python3 tests/test_episode_guardian.py --regression-only
   ```

---

## 🎯 移行チェックリスト

### 移行前の準備
- [ ] EpisodeGuardian本体のテスト実行（14テストすべて合格）
- [ ] 既存スクリプトの棚卸し（機能と使用頻度の確認）
- [ ] バックアップの作成（既存スクリプトとデータ）

### 移行中の確認
- [ ] 並行運用期間の設定（1週間以上）
- [ ] 検証結果の比較と差異分析
- [ ] 問題発生時のロールバック手順の準備

### 移行後の検証
- [ ] EpisodeGuardianのみでの検証実行
- [ ] リグレッションテストの合格
- [ ] CI/CD統合の確認
- [ ] ドキュメントの更新

---

## 📚 参考資料

### EpisodeGuardianドキュメント
- `episode_guardian.py` - メインシステム
- `episode_guardian_rules.py` - ルール定義
- `episode_guardian_config.json` - 設定ファイル
- `tests/test_episode_guardian.py` - テストスイート
- `EPISODE_GUARDIAN_IMPLEMENTATION_REPORT_20251001.md` - 実装レポート

### 既存システムドキュメント
- `unified_validation_system_with_persistence.py` - 既存検証システム
- `pdca_guardian.py` - PDCAルール（将来統合予定）
- `group_member_database.py` - グループデータベース

---

## 🚨 トラブルシューティング

### 問題1: 既存システムとの検証結果の差異

**原因**: Entity Type検証が追加されたため

**解決策**:
1. 差異のあるエピソードを特定
2. person_nameがグループでないか確認
3. グループの場合は個人への置き換え

### 問題2: 既知グループリストの不足

**原因**: 新しいグループが追加された

**解決策**:
1. `episode_guardian.py`の`_load_known_groups()`にグループ名を追加
2. または`group_member_database.py`に追加

```python
groups.update([
    '新しいグループ名',
    'Another Group'
])
```

### 問題3: パフォーマンスの低下

**原因**: 大量データの検証

**解決策**:
1. バッチ処理の最適化
2. 並列処理の導入
3. キャッシュの活用

---

## 🎉 移行完了の基準

以下のすべてが満たされた場合、移行完了とみなす：

✅ **機能面**
- EpisodeGuardianですべての検証が実行可能
- 既存システムと同等以上の検証精度
- Entity Type検証が正常に動作

✅ **品質面**
- 14のユニットテストすべてが合格
- EP010リグレッションテストが合格
- 100件のエピソード検証が100%合格

✅ **運用面**
- CI/CD統合が完了
- ドキュメントが更新済み
- チーム全員がEpisodeGuardianを使用可能

✅ **廃止判断**
- 既存スクリプトが1ヶ月間未使用
- すべての機能がEpisodeGuardianで代替可能
- アーカイブ済み

---

**作成者**: Claude Code
**最終更新**: 2025年10月1日
**ステータス**: ✅ 完了
