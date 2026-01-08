# SAGE Turbo 最適化完了 (2026-01-08)

## 目的
SAGE Turboの棄却を事前に予測・回避して採用率を向上し、コストを削減

## 改善結果

| 指標 | 基準値 | 最適化後 | 改善 |
|------|--------|---------|------|
| 採用率 | 68.6% | **85.0%** | **+16.4%** |
| 採用単価 | $0.0081 | **$0.0078** | **-3.7%** |
| 品質閾値 | 8.0固定 | 8.0固定 | 維持 |

## 実装内容

### Phase 1: 生成前フィルタ（turbo_engine.py）
- `_get_next_batch()`で`PreGenerationRules.check_all()`を実行
- same_age_duplicate/cooldown_activeを生成前に除外
- LLMコスト0で無駄な生成を回避

### Phase 2: 軽量後処理（orchestrator.py）
- `auto_fix_polite_form()`を生成後に適用
- 敬体/常体統一、句読点、文末の自動修正
- LLMコスト0で品質向上

### Phase 3: リトライロジック（orchestrator.py）
- `LOW_GENERATION_QUALITY`の場合1回だけリトライ
- 品質ゲート失敗→再生成→表層修正→再評価
- 採用率+10%以上の効果

## 修正ファイル
- `scripts/sage/turbo_engine.py`: _get_next_batch()に生成前フィルタ、_pre_filter_stats追加
- `scripts/sage/orchestrator.py`: auto_fix_polite_form追加、リトライロジック追加

## テスト結果

### dry-run ($0.1上限)
- 生成: 20件、採用: 18件、採用率: **90.0%**

### A/Bテスト ($1上限)
- 生成: 160件、採用: 136件、採用率: **85.0%**
- コスト: $1.07、単価: $0.0078

## 確定要件
- 品質閾値: `generation_quality >= 8.0` 固定
- リトライ回数: 最大1回
- same_age_duplicate: 除外のみ
- cooldown: 24時間維持
