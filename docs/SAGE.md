# SAGE - Smart Adaptive Generation Engine

高品質エピソード生成システム

## 概要

SAGE (Smart Adaptive Generation Engine) は、Claude Sonnet 4 を活用した知的エピソード生成システムです。7軸品質スコアリングと適応的フォールバック戦略により、高い採用率（~90%）を実現します。

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────┐
│                      SAGE Pipeline                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐ │
│  │Candidate │ → │Pre-Gen   │ → │Generator │ → │Quality   │ │
│  │Selection │   │Rules     │   │(Claude)  │   │Gates     │ │
│  └──────────┘   └──────────┘   └──────────┘   └──────────┘ │
│       │              │              │              │        │
│       ↓              ↓              ↓              ↓        │
│  Priority Score  Age Boundary   EPGEN/Legacy   7-Axis      │
│  Diversity       Cooldown       Fallback       Scoring     │
│  Fame Balance    Daily Limit                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 使用方法

### CLI

```bash
# 10件生成（dry-run）
python scripts/sage/cli.py --target 10 --dry-run

# 100件生成（実行）
python scripts/sage/cli.py --target 100 --execute

# 推奨候補を表示
python scripts/sage/cli.py --recommend 10

# 特定人物を指定
python scripts/sage/cli.py --person "大谷翔平" --age 30 --execute
```

### スケジューラ

```bash
# 自動実行開始（毎日4:00）
./scripts/manage_sage_scheduler.sh start

# 状態確認
./scripts/manage_sage_scheduler.sh status

# 手動実行
./scripts/manage_sage_scheduler.sh run 50
```

## 品質スコアリング

### 7軸評価

| 軸 | 説明 | 重み |
|----|------|------|
| factual_density | 事実密度（年号・数値・固有名詞） | 1.5 |
| generation_quality | 生成品質（文章の自然さ） | 1.4 |
| memorability | 記憶性（印象に残るか） | 1.2 |
| surprise | 意外性（知らなかった事実） | 1.1 |
| story_quality | ストーリー品質 | 1.0 |
| educational_value | 教育的価値 | 1.0 |
| emotional_impact | 感情インパクト | 1.0 |

### 品質ゲート

```yaml
min_thresholds:
  factual_density: 6.0
  generation_quality: 6.0

composite_score:
  min: 400
  target: 500
  retry_threshold: 470

super_total:
  min: 300,000
  target: 500,000
```

## 生成戦略

### EPGEN-First（デフォルト）

1. EPGEN（新生成エンジン）で生成を試行
2. 失敗時はLegacy（従来エンジン）にフォールバック
3. 両方失敗した場合のみ棄却

```
EPGEN成功率: ~91%
Legacy成功率: ~100%（フォールバック時）
総合採用率: ~90%
```

## コスト最適化（Phase 1-3）

### 最適化サマリー

| Phase | 対象 | 削減率 | デフォルト |
|-------|------|--------|-----------|
| Phase 1 | コスト計測 | 可視化100% | 有効 |
| Phase 2 | プロンプト圧縮 | **-73%** | 無効（要設定） |
| Phase 3 | 評価Haiku化 | **-92%** | 有効 |

### Phase 1: コスト計測基盤

トークン使用量とコストをログに自動記録。

```python
# ログ出力例（src/reports/logs/run_*.json）
{
  "cost_metrics": {
    "total_input_tokens": 15000,
    "total_output_tokens": 5000,
    "estimated_cost_usd": 0.1200,
    "avg_tokens_per_episode": 2000,
    "avg_cost_per_episode_usd": 0.012
  }
}
```

### Phase 2: プロンプト圧縮

生成プロンプトを73%圧縮（558文字 → 149文字）。

```python
from scripts.generate.mass_production.config import GenerationConfig

# 圧縮版プロンプト有効化
config = GenerationConfig(use_compact_prompt=True)
```

**圧縮版プロンプト例:**
```
EP生成|大谷翔平|25歳|スポーツ|生1994

開始文:「あなたと同じ25歳のとき、」
必須:年号≥1/数値≥3/固有名詞≥5/「」作品名≥2
禁止:人生を振り返/自らの歩みを振り返/静かな日々を送/晩年.*回顧
焦点:青年期:キャリア形成/転機/決断

300-400字,EPテキストのみ出力
```

### Phase 3: 評価Haiku化

評価APIをSonnet→Haikuに変更（コスト-92%）。

```python
from scripts.sage.strategy_router import create_router

# Haiku評価（デフォルト）
router = create_router(use_haiku_evaluation=True)

# Sonnet評価（高精度モード）
router = create_router(use_haiku_evaluation=False)
```

**モデル料金比較:**

| モデル | Input/1M | Output/1M | 削減率 |
|--------|----------|-----------|--------|
| Sonnet | $3.00 | $15.00 | - |
| Haiku | $0.25 | $1.25 | -92% |

### 全最適化有効時の使用方法

```python
from scripts.sage.strategy_router import create_router
from scripts.sage.orchestrator import SAGEOrchestrator
from scripts.sage.config import SAGEConfig

# 設定
config = SAGEConfig()

# ルーター作成（Phase 3: Haiku評価デフォルト有効）
router = create_router(
    strategy="epgen_first",
    use_haiku_evaluation=True,  # Phase 3
)

# オーケストレーター
orchestrator = SAGEOrchestrator(config=config)

# 生成実行
results = orchestrator.generate(target=100)
```

**CLI使用時:**
```bash
# Phase 3（Haiku評価）はデフォルト有効
python scripts/sage/cli.py --target 100 --execute
```

## コスト分析

### 最適化前

| 項目 | 値 |
|------|-----|
| 生成モデル | claude-sonnet-4-20250514 |
| 評価モデル | claude-sonnet-4-20250514 |
| 生成トークン | ~800 in / ~400 out |
| 評価トークン | ~700 in / ~250 out |
| 合計/件 | ~1,500 in / ~650 out |
| コスト/100件 | ~$1.60 (¥239) |

### 最適化後（Phase 1-3適用）

| 項目 | 値 |
|------|-----|
| 生成モデル | claude-sonnet-4-20250514 |
| 評価モデル | claude-3-5-haiku-20241022 |
| 生成トークン | ~215 in / ~400 out（圧縮時） |
| 評価トークン | ~700 in / ~250 out |
| コスト/100件 | ~$0.50-0.70 (¥75-105) |
| 削減率 | **約60-70%** |

## ディレクトリ構造

```
scripts/sage/
├── cli.py              # メインCLI
├── config.py           # 設定・閾値
├── orchestrator.py     # オーケストレーター
├── strategy_router.py  # 戦略ルーター
├── pre_generation_rules.py  # 生成前ルール
├── adapters/
│   ├── epgen_adapter.py    # EPGEN接続
│   ├── legacy_adapter.py   # Legacy接続
│   └── base.py             # 基底クラス
├── gates/
│   ├── candidate_prioritizer.py  # 候補優先度
│   ├── duplicate.py              # 重複検出
│   ├── fact_check.py             # ファクトチェック
│   └── diversity.py              # 多様性
├── quality/
│   ├── evaluator.py       # 品質評価
│   ├── super_total.py     # 超総合スコア
│   └── improvement.py     # 品質改善
└── persistence/
    └── csv_writer.py      # CSV書き込み
```

## 関連ファイル

- `preserved/sage_dashboard.html` - ダッシュボード
- `scripts/update_sage_dashboard.py` - ダッシュボード更新
- `scripts/manage_sage_scheduler.sh` - スケジューラ管理
- `tests/test_sage.py` - テストスイート
- `src/reports/logs/run_*.json` - 実行ログ

## バージョン履歴

### v1.1 (2026-01-07)
- **Phase 1**: コスト計測基盤（TokenUsage, cost_metrics）
- **Phase 2**: プロンプト圧縮（-73%トークン削減）
- **Phase 3**: 評価Haiku化（-92%コスト削減）
- 総合コスト削減: 約60-70%

### v1.0 (2026-01-07)
- Hybrid Generator → SAGE へリブランド
- EPGEN-first 戦略の実装
- 7軸品質スコアリング
- 適応的フォールバック機構
