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

## コスト分析

| 項目 | 値 |
|------|-----|
| モデル | claude-sonnet-4-20250514 |
| 生成トークン | ~800 in / ~400 out |
| 評価トークン | ~700 in / ~250 out |
| 合計/件 | ~1,500 in / ~650 out |
| コスト/100件 | ~$1.60 (¥239) |

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

### v1.0 (2026-01-07)
- Hybrid Generator → SAGE へリブランド
- EPGEN-first 戦略の実装
- 7軸品質スコアリング
- 適応的フォールバック機構
