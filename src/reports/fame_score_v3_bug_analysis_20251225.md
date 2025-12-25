# 有名人度スコア異常値 原因分析レポート

**作成日時**: 2025-12-25
**対象**: PERSON ID `PF632FA6` / 名前 `ken` (L'Arc~en~Ciel) / 報告値 `7133.400000000001`

---

## 1. ドライラン結果要約

### 1.1 PF632FA6の生データ（CSV）
| フィールド | 値 |
|-----------|-----|
| person_id | PF632FA6 |
| person_name | ken |
| fame_score (旧) | 6.0 |
| fame_score_v2 | 54.33 |
| **fame_score_v3** | **713.34** |
| multi_lang_pv | 600,170 |
| sitelinks_count | 331 |

### 1.2 スコア分布（fame_score_v3）
- 件数: 11,237件
- 最大: 789.27
- 最小: 0.01
- 中央値: 378.13
- 1000超過: 0件（正常）

### 1.3 異常の定義
- fame_score_v3は**0-1000スケール**で設計
- ken(713.34)は上位11%程度で**正常範囲内**
- 報告値 7133.4 は**10倍**されている

---

## 2. 根本原因（証拠付き）

### 原因: ダッシュボードでの**誤った10倍変換**

**問題箇所**: `preserved/episode_database_dashboard_v10.html`

#### 箇所1: 3279行目
```javascript
const score = (person.fame_score || 0) * 10;  // 0-100 → 0-1000スケールに変換
```

#### 箇所2: 4049行目
```javascript
const fame1000 = (fameScoreValue || 0) * 10;  // 0-100 → 0-1000
```

### 問題のメカニズム
1. データ読み込み（3961-3972行目）で `fame_score_v3` を優先使用
2. `fame_score_v3` は**既に0-1000スケール**
3. しかし表示時に「0-100 → 0-1000変換」として**さらに10倍**
4. 結果: 713.34 × 10 = **7133.400000000001**

### 証拠
```python
fame_score_v3 (713.34) * 10 = 7133.400000000001  # ← ユーザー報告値と完全一致
```

### 仮説検証
| 仮説 | 結果 | 根拠 |
|------|------|------|
| スケール/正規化ミス | **確定** | ダッシュボード3279行, 4049行 |
| 重複カウント | 否定 | エピソード2件のみ、スコアは人物単位 |
| パース崩れ | 否定 | CSV値は正常(713.34) |
| 浮動小数誤差 | 否定 | 10倍は意図的な乗算 |
| 別人混入 | 否定 | PF632FA6はken唯一 |
| 例外経路 | 否定 | 正常パスで発生 |

---

## 3. CSVデータの状態

**CSVデータは正常です。修正不要。**

- `fame_score_v3`: 713.34（0-1000スケール、正常範囲）
- 問題はダッシュボードの**表示ロジックのみ**

---

## 4. 修正案

### 案A: 10倍変換の削除（推奨）
```javascript
// 修正前
const score = (person.fame_score || 0) * 10;

// 修正後
const score = person.fame_score || 0;
```

**影響**: 表示値が正しい0-1000スケールに修正される

### 案B: fame_score_v3使用時のみ変換スキップ
```javascript
// fame_score_v3は既に0-1000スケールなので変換不要
const score = person.fame_score || 0;
// 旧スコア(0-100)を使う場合のみ10倍
```

**影響**: 後方互換性を維持

### 推奨: 案A（シンプル）
- 現在CSVは全て fame_score_v3 を使用
- 旧スコア(0-100)との混在はない
- コード簡素化

---

## 5. 影響範囲

- 修正対象: `preserved/episode_database_dashboard_v10.html`
- 修正行: 3279行目, 4049行目（計2箇所）
- CSVデータ: **変更不要**

---

## 6. 修正結果（承認後）

### 修正内容
| 行番号 | 修正前 | 修正後 |
|--------|--------|--------|
| 3241 | `(p.fame_score \|\| 0) * 10` | `p.fame_score \|\| 0` |
| 3279 | `(person.fame_score \|\| 0) * 10` | `person.fame_score \|\| 0` |
| 3643 | `ep.episode_fame_score * 10` | `ep.episode_fame_score \|\| 0` |
| 3683 | `ep.episode_fame_score * 10` | `ep.episode_fame_score \|\| 0` |
| 4049 | `(fameScoreValue \|\| 0) * 10` | `fameScoreValue \|\| 0` |
| 4050 | `(episodeFameScoreValue \|\| 0) * 10` | `episodeFameScoreValue \|\| 0` |
| 4445-4446 | `ep.fame_score * 10` | `ep.fame_score` |
| 4451-4452 | `ep.episode_fame_score * 10` | `ep.episode_fame_score` |

### 修正後の検証結果
```
📋 検証対象: preserved/data/MASTER_EPISODES_CURRENT.csv

=== 統計 ===
  総行数: 11240
  fame_score_v3: 11240件
    最大: 789.27
    最小: 0.00
  episode_fame_score: 11237件
    最大: 433.30

✅ 検証OK: 異常値なし
```

### 修正確認
- `fame_score * 10` の残存: **0件**
- PF632FA6 (ken): **713.34**（正常範囲、10倍バグ解消）

---

## 7. 再発防止策

### 7.1 品質ゲート（新規追加）
- **スクリプト**: `scripts/validate_fame_score.py`
- 機能:
  - スコアが0-1000範囲内か検証
  - NaN/inf/負数を検出
  - 上限超過を検出・報告

### 7.2 テスト（新規追加）
- **ファイル**: `tests/test_fame_score_validation.py`
- テストケース:
  - `test_all_scores_within_range`: 全スコアが範囲内
  - `test_no_nan_or_inf`: NaN/infなし
  - `test_no_negative_scores`: 負数なし
  - `test_specific_person_ken`: PF632FA6の回帰テスト
  - `test_fame_score_v3_is_already_1000_scale`: 10倍バグ防止

### 7.3 監視
- 定期実行: `python scripts/validate_fame_score.py`
- CI統合推奨: テスト自動実行

### 7.4 ロールバック手順
```bash
# ダッシュボードをGitから復元
git checkout HEAD~1 -- preserved/episode_database_dashboard_v10.html
```

---

## 8. 追加修正（包括監査）

### 8.1 発見した追加の不整合

| 箇所 | 問題 | 修正内容 |
|------|------|----------|
| 4049行 | `super_total_score`計算でスケール混在 | `composite * 100`で0-1000に統一 |
| 4457行 | `composite_score`閾値が0-1000用 | 閾値を0-10用（7.5/6.5）に修正 |
| 4467行 | `/1000`表示（composite_scoreは0-10） | `/10`に修正 |
| 3687行 | `episode_fame_score`閾値が0-1000用 | 閾値を0-500用（350/250）に修正 |
| 4452行 | `episode_fame_score`バッジ閾値 | 同上 |

### 8.2 スコアフィールド定義（確定版）

| スケール | フィールド |
|----------|-----------|
| 0-5 (Tier) | fame_tier, episode_fame_tier |
| 0-10 | composite_score, llm_*, 記憶性, 共感性, 意外性, 生成品質, etc. |
| 0-100 | fame_score (旧), fame_score_v2, impressiveness_score |
| 0-500 | episode_fame_score |
| 0-1000 | fame_score_v3, quality_score, priority_score |

---

## 9. 再発防止システム（包括版）

### 9.1 検証スクリプト
- `scripts/validate_fame_score.py` - 有名人度スコア専用
- `scripts/validate_all_scores.py` - **全スコアフィールド包括検証**

### 9.2 テストスイート（10テスト）
- `TestFameScoreValidation` - 有名人度スコア検証（6テスト）
- `TestAllScoresValidation` - 全スコア検証（3テスト）
- `TestDashboardScaleConsistency` - ダッシュボード整合性（1テスト）

### 9.3 定期実行コマンド
```bash
# 全スコア検証
python scripts/validate_all_scores.py

# テスト実行
pytest tests/test_fame_score_validation.py -v
```

---

## 10. 完了サマリー

| 項目 | 結果 |
|------|------|
| 根本原因 | ダッシュボードの誤った10倍変換 + スケール混在 |
| 修正箇所 | **13箇所**（8箇所→追加5箇所） |
| CSVデータ | 変更不要（全て正常範囲） |
| 検証 | ✅ 全10テスト合格 |
| 再発防止 | 包括検証スクリプト + テストスイート
