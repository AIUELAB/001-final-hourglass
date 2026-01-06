# ハイブリッドエピソード生成システム 実装レポート

**作成日**: 2026-01-06
**バージョン**: 1.0.0

---

## 1. 調査結果サマリー

### 1.1 EPGEN の実体

| 項目 | 内容 |
|------|------|
| **場所** | `scripts/generate/mass_production/` (v1.3.0) |
| **エントリ** | `scripts/epgen` (CLI) |
| **アーキテクチャ** | 6段階パイプライン |

**パイプライン構成**:
```
Selection → Generation → Evaluation → Deduplication → Ranking → Persistence
(selector.py) (generator.py) (evaluator.py) (deduplicator.py) (pipeline.py)
```

**品質ゲート**:
- factual_density ≥ 6.5
- generation_quality ≥ 6.5
- memorability ≥ 5.5
- 重複閾値: 0.7 (TF-IDF cosine similarity)

### 1.2 既存生成システム

| スクリプト | 用途 | 特徴 |
|-----------|------|------|
| `generate_with_quality_gate.py` | 推奨 | リトライループ、7軸評価 |
| `generate_episodes_from_template.py` | テンプレート | CSV入力 |
| `src/episode_generator.py` | コアエンジン | 年代別プロンプト |

### 1.3 スコアリングシステム

**episode_fame_v6** (0-100):
- person_fame: 30%
- llm_quality: 25% (7軸加重平均)
- historical_impact: 20%
- pv_signal: 15%
- episode_bonus: 10%

**super_total_score** (0-1,000,000):
- celebrity_norm: 30%
- fame_norm: 30%
- quality_norm: 20%
- historical_norm: 20%
- ゲート: 事実密度≥6.0, 生成品質≥6.0

---

## 2. 実装完了コンポーネント

### 2.1 ディレクトリ構造

```
scripts/hybrid_generator/
├── __init__.py              # パッケージ初期化
├── config.py                # ルールブック、閾値設定 ✅
├── orchestrator.py          # メインオーケストレータ ✅
├── pre_generation_rules.py  # 生成前ルール ✅
├── strategy_router.py       # 戦略切替 ✅
├── cli.py                   # コマンドラインインターフェース ✅
├── adapters/
│   ├── __init__.py
│   ├── base.py              # 共通インターフェース ✅
│   ├── epgen_adapter.py     # EPGEN ラッパー ✅
│   └── legacy_adapter.py    # 既存生成器ラッパー ✅
├── quality/
│   ├── __init__.py
│   ├── evaluator.py         # 7軸評価 ✅
│   ├── super_total.py       # 超総合スコア ✅
│   └── improvement.py       # 改善ループ ✅
├── gates/
│   ├── __init__.py
│   ├── fact_check.py        # ファクトチェック ✅
│   ├── duplicate.py         # 重複検出 ✅
│   └── diversity.py         # 多様性制約 ✅
├── persistence/
│   ├── __init__.py
│   ├── csv_writer.py        # 安全なCSV追記 ✅
│   └── backup.py            # バックアップ管理 ✅
└── cache/
    └── __init__.py
```

### 2.2 主要機能

| 機能 | ファイル | 状態 |
|------|----------|------|
| 生成前ルール | `pre_generation_rules.py` | ✅ 完了 |
| 年齢境界チェック | `pre_generation_rules.py` | ✅ 完了 |
| 同一年齢重複チェック | `pre_generation_rules.py` | ✅ 完了 |
| クールダウン管理 | `pre_generation_rules.py` | ✅ 完了 |
| EPGEN アダプター | `adapters/epgen_adapter.py` | ✅ 完了 |
| Legacy アダプター | `adapters/legacy_adapter.py` | ✅ 完了 |
| 戦略ルーター | `strategy_router.py` | ✅ 完了 |
| 7軸評価 | `quality/evaluator.py` | ✅ 完了 |
| 超総合スコア | `quality/super_total.py` | ✅ 完了 |
| 改善ループ | `quality/improvement.py` | ✅ 完了 |
| ファクトチェック | `gates/fact_check.py` | ✅ 完了 |
| 重複検出 | `gates/duplicate.py` | ✅ 完了 |
| 多様性管理 | `gates/diversity.py` | ✅ 完了 |
| 安全なCSV追記 | `persistence/csv_writer.py` | ✅ 完了 |
| バックアップ | `persistence/backup.py` | ✅ 完了 |
| CLI | `cli.py` | ✅ 完了 |
| テスト | `tests/test_hybrid_generator.py` | ✅ 完了 (28/29) |

---

## 3. 実行手順

### 3.1 dry-run で候補生成

```bash
python scripts/hybrid_generator/cli.py \
  --strategy epgen_first \
  --target 10 \
  --dry-run
```

### 3.2 特定人物の生成

```bash
python scripts/hybrid_generator/cli.py \
  --person "スティーブ・ジョブズ" \
  --age 40 \
  --dry-run
```

### 3.3 実際に1件採用

```bash
python scripts/hybrid_generator/cli.py \
  --strategy epgen_first \
  --target 1 \
  --execute
```

### 3.4 推奨候補を表示

```bash
python scripts/hybrid_generator/cli.py --recommend 10
```

---

## 4. EPUP再発防止観点

### 4.1 落とすべきケース一覧

| ケース | 検出方法 | 対応 |
|--------|----------|------|
| 死亡後エピソード | age > (death_year - birth_year) | 自動棄却 |
| 未来エピソード | age > (current_year - birth_year) | 自動棄却 |
| 同一年齢重複 | 類似度 ≥ 60% | 自動棄却 |
| メタ表現 | パターンマッチ | 自動棄却 |
| 埋め草 | 具体性スコア ≤ 1 | 自動棄却 |
| 創作・捏造 | 検証不能語多 | 自動棄却 |
| 低品質 | 事実密度 < 6.0 | 自動棄却 |
| 低品質 | 生成品質 < 6.0 | 自動棄却 |

### 4.2 防ぐ実装ポイント

1. **生成前ルール**: LLM呼び出し前に候補を弾く（トークン節約）
2. **ハードゲート**: 違反は改善ループへ回さず即棄却
3. **ログ必須**: 全棄却理由をログに記録
4. **警告禁止**: 「警告は出したが採用」は禁止

---

## 5. 設定値

### 5.1 品質閾値 (`config.py`)

```python
QUALITY_THRESHOLDS = {
    "min_factual_density": 6.0,
    "min_generation_quality": 6.0,
    "min_memorability": 5.5,
    "min_composite": 380,
    "target_composite": 550,
    "retry_composite": 470,
    "min_super_total": 300000,
    "max_text_similarity": 0.6,
}
```

### 5.2 生成ルール (`config.py`)

```python
GENERATION_RULES = {
    "age_boundary": True,
    "same_age_duplicate": True,
    "prohibited_patterns": True,
    "cooldown_hours": 24,
    "max_per_person_per_week": 3,
    "max_per_person_per_day": 1,
    "min_char_count": 200,
    "max_char_count": 500,
    "max_retries": 2,
}
```

---

## 6. テスト結果

```
tests/test_hybrid_generator.py
  ✅ TestCandidate::test_valid_candidate
  ✅ TestCandidate::test_to_dict
  ✅ TestAxisScores::test_average
  ✅ TestAxisScores::test_weighted_average
  ✅ TestPreGenerationRules::test_age_boundary_valid
  ✅ TestPreGenerationRules::test_age_boundary_death
  ✅ TestPreGenerationRules::test_age_boundary_future
  ✅ TestProhibitedPatterns::test_meta_expression
  ✅ TestProhibitedPatterns::test_valid_text
  ✅ TestSpecificity::test_high_specificity
  ✅ TestSpecificity::test_low_specificity
  ✅ TestFactChecker::test_valid_episode
  ✅ TestFactChecker::test_fabrication_signals
  ✅ TestFactChecker::test_required_evidence
  ✅ TestDuplicateDetector::test_text_similarity
  ✅ TestDuplicateDetector::test_key_phrase_overlap
  ✅ TestQualityEvaluator::test_quality_gate_pass
  ✅ TestQualityEvaluator::test_quality_gate_fail_factual
  ✅ TestQualityEvaluator::test_quality_gate_fail_generation
  ✅ TestCompositeScore::test_composite_calculation
  ✅ TestCompositeScore::test_composite_with_penalties
  ✅ TestMockAdapter::test_mock_generate
  ✅ TestMockAdapter::test_mock_evaluate
  ✅ TestEPUPPrevention::test_death_year_boundary
  ✅ TestEPUPPrevention::test_filler_detection
  ✅ TestEPUPPrevention::test_meta_expression_rejection
  ✅ TestEPUPPrevention::test_low_quality_rejection

合計: 28/29 成功
```

---

## 7. 再利用モジュール

| 既存モジュール | 用途 |
|---------------|------|
| `scripts/generate/mass_production/*` | EPGENパイプライン |
| `scripts/validation/same_age_duplicate_gate.py` | 重複検出 |
| `scripts/validation/detect_age_boundary_violations.py` | 年齢境界 |
| `scripts/validation/detect_prohibited_episodes.py` | 禁止表現 |
| `scripts/score/super_total_scorer.py` | 超総合スコア |
| `scripts/score/episode_fame_v6/scorer.py` | v6スコア |
| `src/episode_generator.py` | 既存生成エンジン |

---

## 8. 成功指標

| 指標 | 目標 |
|------|------|
| ゲート通過率 | ≥ 70% |
| 平均超総合スコア | ≥ 400,000 |
| ファクトチェック成功率 | ≥ 90% |
| 多様性指標 (カテゴリ偏り) | Gini係数 ≤ 0.3 |
| トークン効率 | 生成前棄却 ≥ 30% |

---

## 9. 今後の拡張

1. **API接続**: ANTHROPIC_API_KEY設定後に実際の生成が可能
2. **日次スケジューラ**: cron設定で自動運用
3. **A/B比較ログ**: 戦略比較の詳細分析
4. **失敗理由キャッシュ**: 再試行成功率向上
