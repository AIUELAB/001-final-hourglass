# SAGE最適化セッション - 2026-01-07

## セッション概要

**目的**: 品質を落とさずに採用率改善とコスト最適化を両立
**結果**: 採用率 68% → 89-91% (+21-23pt) 改善達成

---

## 完了タスク

### Phase 1: 架空キャラ除外フィルタ ✅
- `scripts/sage/config.py`: `fictional_enabled: bool = False` 追加
- `scripts/sage/orchestrator.py:515-518`: person_type フィルタ追加

```python
# Phase 8: 架空キャラ除外フィルタ
person_type = str(row.get("person_type", "REAL"))
if not self.config.fictional_enabled and person_type != "REAL":
    continue
```

### Phase 2: AsyncOrchestrator CLI統合 ✅
- `scripts/sage/cli.py`: 以下のフラグ追加
  - `--async`: 非同期並列処理有効化
  - `--fictional`: 架空キャラを含める
  - `--max-concurrent`: 同時実行数

### Phase 3: Batch API統合 ✅ (完了)
- `scripts/sage/cli.py`: `--execute --batch`フラグ統合
- EPGENの本格的なプロンプトビルダーを使用
- 50%コスト削減可能
- 24時間遅延（結果は後で取得）

**使用方法:**
```bash
# バッチモードで生成（50%コスト削減）
python scripts/sage/cli.py --target 100 --execute --batch

# ステータス確認
python scripts/sage/cli.py --batch-status BATCH_ID

# 結果取得
python scripts/sage/cli.py --batch-results BATCH_ID
```

---

## テスト結果

| Run | 生成数 | 採用数 | 採用率 |
|-----|--------|--------|--------|
| ベースライン | 100 | 68 | 68% |
| dry-run | 20 | 17 | 85% |
| 本番1回目 | 100 | 91 | 91% |
| 本番2回目 | 100 | 89 | 89% |

---

## 主要ファイル変更

| ファイル | 変更内容 | 行数 |
|---------|---------|------|
| `scripts/sage/config.py` | fictional_enabled, batch_api_enabled, async_enabled, max_concurrent | +4行 |
| `scripts/sage/orchestrator.py` | person_type == "REAL" フィルタ | +5行 |
| `scripts/sage/cli.py` | --async, --fictional, --max-concurrent フラグ | +25行 |

---

## 実行ログパス

- 最新: `src/reports/logs/run_20260107_181712.json`
- プランファイル: `/Users/admin/.claude/plans/rosy-toasting-llama.md`

---

## ユーザー決定事項

| 項目 | 決定 |
|------|------|
| 品質閾値 | REAL: 8.0維持 |
| 架空キャラ | **除外** |
| Batch API | 遅延許容 |
| 優先年齢 | 均等生成 |

---

## 完了したTODO

1. [x] Phase 8 コミット完了 (57269ec) - 架空キャラ除外フィルタ
2. [x] Phase 9 実装完了 (f7b9b86) - 評価Haiku + Batch API
3. [x] Phase 10 実装完了 (fee2b9a) - プロンプト圧縮 (-60%トークン)
4. [x] Phase 11 確認完了 - 失敗理由別テンプレート（Phase 5で実装済み）
5. [x] Phase 12 実装完了 (cb63fe5) - 候補スコア閾値厳格化 (-15%生成)
6. [x] Phase 13 実装完了 (3429336) - カテゴリ別閾値（dry-run 95%, 本番 80%）
7. [x] H4 実装完了 (9cb02c2) - プロンプトキャッシュ (-90%入力トークン)
8. [x] Batch API統合完了 (7d6944c) - 50%コスト削減モード
9. [x] Phase 14 実装完了 (0d63060) - 候補選定改善（デフォルト年齢拡張）
10. [x] Phase 15 実装完了 (b32f156) - 年齢在庫優先度スコアリング
    - CandidatePrioritizerに_calculate_inventory_age_priority_score()追加
    - ウェイト: EP 0.4, Category 0.25, Age 0.15, Inventory 0.2
    - 中心年齢（40歳）からの距離ペナルティ
    - GENERATEモード年齢優先（REPLACEは低スコア10.0）

## 最新実績 (2026-01-07 23:00時点)
- 総ラン数: 79回 (dry-run: 40 / execute: 39)
- 生成: 2,601件
- 採用: 2,265件 (採用率87.1%)
- EPGEN成功率: 95.5%
- フォールバック: 115件
- リジェクト: 334件

## 新規ツール
- `scripts/sage/analyze_age_priority.py`: 年齢別優先度分析
- `scripts/sage/monitor_batch_jobs.py`: Batch APIジョブ監視