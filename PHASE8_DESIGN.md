# Phase 8: 既存エピソード改善システム 設計書

**プロジェクト**: エピソード品質管理システム
**期間**: 2025-10-03
**目的**: Phase 7で構築したLLM改善システムを既存100エピソードに適用

---

## 🎯 Phase 8の目的

Phase 7で構築した**RULE_182（LLM改善エンジン）+ RULE_183（統合改善インターフェース）**を活用し、既存の100エピソードの品質を大幅に向上させる。

### 背景

**現在の状況** (PROJECT_STATUS.mdより):
- 評価対象: 100エピソード（episodes_validated_100_20251001.csv）
- 合格率: **4%（4/100件）** ← 極めて低い
- インパクト不足: 80件（30点未満）
- Phase 1改善（LLMプロンプトv2）成功率: **4.8%** ← 不十分

**Phase 7の成果**:
- RULE_182: +18.8点の改善実績
- RULE_183: 自動戦略選択（70%コスト削減）
- 処理速度: 3-5秒/エピソード
- コスト: $0.021/エピソード（OpenAI）

### Phase 8の目標

| 指標 | 現状 | Phase 8目標 | 改善率 |
|-----|------|-----------|--------|
| 合格率 | 4% | **30%以上** | +650% |
| 平均スコア | ~20点 | **50点以上** | +150% |
| インパクト不足（30点未満） | 80件 | **30件以下** | -62.5% |
| 総コスト | $0 | **$2.00以内** | 予算内 |

---

## 📊 Phase 8の全体構成

### Phase 8.1: 既存データ分析と改善対象選定

**目的**: 100エピソードを分析し、優先順位を決定

**タスク**:
1. 最新CSVファイルの特定と読み込み
2. 既存スコアデータの分析
   - スコア分布の確認
   - 問題パターンの分類
3. 改善優先度の決定
   - 低スコア（0-30点）: 最優先
   - 中スコア（30-60点）: 中優先
   - 高スコア（60点以上）: 改善不要
4. 予算配分計画

**成果物**:
- `episodes_analysis_phase8.json` - 分析結果
- `PHASE8_1_ANALYSIS_REPORT.md` - 詳細分析レポート

---

### Phase 8.2: バッチ改善システム実装

**目的**: 大量エピソードを効率的に改善するシステム構築

**設計方針**:
```python
class BatchEpisodeImprover:
    """100エピソード一括改善システム"""

    def __init__(self):
        self.interface = get_unified_interface(reset=True)
        self.cost_manager = CostManager(daily_limit_usd=2.50)  # Phase 8用予算
        self.stats = {
            "total": 0,
            "improved": 0,
            "failed": 0,
            "skipped": 0,
            "total_cost": 0.0
        }

    def process_batch(
        self,
        episodes: List[Dict],
        strategy: str = "auto",
        save_interval: int = 10
    ) -> Dict[str, Any]:
        """
        バッチ処理
        - 10件ごとに中間保存
        - エラー時の復旧機能
        - リアルタイム統計表示
        """
```

**主要機能**:

1. **優先度ベース処理**
   - 低スコアエピソード優先（ROI最大化）
   - スコア30点未満: Auto戦略（LLM優先）
   - スコア30-60点: Force_Pattern戦略（コスト削減）
   - スコア60点以上: スキップ

2. **チェックポイント機構**
   - 10件ごとに中間保存
   - エラー時の自動復旧
   - 進捗状況の可視化

3. **コスト管理**
   - リアルタイムコスト監視
   - 予算到達時の自動切り替え（LLM→Pattern）
   - 詳細なコスト内訳記録

4. **品質検証**
   - RULE_179統合評価パイプライン自動実行
   - 改善前後のスコア比較
   - 失敗ケースの詳細ログ

**成果物**:
- `batch_episode_improver.py` - バッチ改善システム
- `test_batch_improver.py` - テストスクリプト

---

### Phase 8.3: 実行とモニタリング

**目的**: 実際に100エピソードを改善

**実行計画**:

#### ステップ1: テスト実行（5エピソード）
```bash
# 低スコア5件でテスト
python batch_episode_improver.py \
  --input episodes_validated_100_20251001.csv \
  --output episodes_phase8_test_5.csv \
  --max-episodes 5 \
  --strategy auto
```

**検証項目**:
- ✅ スコア向上確認（期待: +10点以上）
- ✅ コスト予測確認（期待: $0.10以内）
- ✅ エラーハンドリング動作確認
- ✅ 中間保存機能確認

#### ステップ2: 優先度バッチ1（低スコア 30件）
```bash
# 0-30点の30件を改善
python batch_episode_improver.py \
  --input episodes_validated_100_20251001.csv \
  --output episodes_phase8_batch1_low.csv \
  --score-range 0 30 \
  --strategy auto \
  --budget 0.80
```

**期待結果**:
- 改善率: 70%以上（21/30件）
- 平均スコア向上: +15点
- コスト: $0.60-0.80
- 所要時間: 2-3分

#### ステップ3: 優先度バッチ2（中スコア 50件）
```bash
# 30-60点の50件を改善
python batch_episode_improver.py \
  --input episodes_validated_100_20251001.csv \
  --output episodes_phase8_batch2_mid.csv \
  --score-range 30 60 \
  --strategy force_pattern \
  --budget 1.20
```

**期待結果**:
- 改善率: 50%以上（25/50件）
- 平均スコア向上: +10点
- コスト: $0.00（パターンのみ）
- 所要時間: <1分

#### ステップ4: 統合と最終検証
```bash
# 全エピソードを統合
python merge_improved_episodes.py \
  --inputs episodes_phase8_batch1_low.csv episodes_phase8_batch2_mid.csv \
  --output episodes_phase8_complete_100.csv
```

**モニタリング項目**:
- リアルタイムコスト追跡
- スコア向上のグラフ化
- 失敗ケースの即座分析
- メモリ使用量監視

**成果物**:
- `episodes_phase8_complete_100.csv` - 改善後100エピソード
- `phase8_execution_log.json` - 実行ログ
- `phase8_monitoring_stats.json` - 統計データ

---

### Phase 8.4: 結果分析と最終レポート

**目的**: Phase 8の成果を定量評価

**分析項目**:

1. **スコア改善分析**
   - 改善前後の分布比較
   - カテゴリ別改善効果
   - 年齢別改善効果

2. **コスト分析**
   - 総コスト vs ROI
   - 戦略別コスト効率
   - エピソード1件あたりコスト

3. **品質分析**
   - 合格率の変化（4% → ?%）
   - インパクトスコア分布
   - ルール違反率

4. **失敗分析**
   - 改善失敗の原因分類
   - 問題パターンの抽出
   - 今後の改善提案

**成果物**:
- `PHASE8_COMPLETION_REPORT.md` - 包括的完了レポート
- `PHASE8_STATISTICS.md` - 統計分析レポート
- `PHASE8_LESSONS_LEARNED.md` - 教訓と次のステップ

---

## 💰 予算計画

### 総予算: $2.50

**内訳**:

| バッチ | 対象件数 | 戦略 | 予想コスト |
|-------|---------|------|----------|
| テスト | 5件 | Auto | $0.10 |
| バッチ1（低スコア） | 30件 | Auto（LLM優先） | $0.60-0.80 |
| バッチ2（中スコア） | 50件 | Force_Pattern | $0.00 |
| 予備 | - | - | $1.60 |

**コスト削減戦略**:
- スコア60点以上: 改善スキップ
- 中スコア帯: Force_Pattern（無料）
- 予算残少時: 自動的にForce_Pattern切替
- Anthropic検討（$0.004/件、80%削減）

---

## 🎯 成功基準

### 必達目標

| 指標 | 目標値 | 測定方法 |
|-----|--------|---------|
| 合格率 | 30%以上 | RULE_179評価でpassed=True |
| 平均スコア | 50点以上 | total_scoreの平均 |
| インパクト不足削減 | 50件以下 | social_impact < 30点の件数 |
| コスト遵守 | $2.50以内 | CostManager統計 |

### 努力目標

| 指標 | 目標値 |
|-----|--------|
| 合格率 | 40%以上 |
| 平均スコア | 60点以上 |
| インパクト不足 | 30件以下 |
| コスト | $2.00以内 |

---

## 🔧 技術仕様

### システム構成

```
Phase 8 Batch Improvement System
├── Data Analysis Layer
│   ├── episodes_validated_100_20251001.csv（入力）
│   ├── Score Distribution Analyzer
│   └── Priority Sorter
│
├── Improvement Engine Layer (Phase 7)
│   ├── RULE_182: LLMImprovementEngine
│   ├── RULE_183: UnifiedImprovementInterface
│   ├── CostManager
│   └── Strategy Selector
│
├── Batch Processing Layer
│   ├── BatchEpisodeImprover
│   ├── Checkpoint Manager
│   ├── Progress Monitor
│   └── Error Recovery
│
├── Validation Layer
│   ├── RULE_179: Integrated Evaluation Pipeline
│   ├── Score Comparison
│   └── Quality Gate
│
└── Reporting Layer
    ├── Statistics Collector
    ├── Visualization Generator
    └── Report Builder
```

### データフロー

```
Input: episodes_validated_100_20251001.csv
  ↓
[Phase 8.1] 分析 → 優先度決定
  ↓
[Phase 8.2] バッチ改善システム
  ├─ RULE_183（Auto戦略）
  │   ├─ スコア < 60 → RULE_182（LLM）
  │   └─ スコア >= 60 → RULE_180（Pattern）
  ↓
[RULE_179] 再評価
  ↓
[Phase 8.3] 10件ごとにチェックポイント保存
  ↓
[Phase 8.4] 統計分析・レポート生成
  ↓
Output: episodes_phase8_complete_100.csv
```

---

## 📋 実装計画

### Day 1: Phase 8.1 + 8.2実装

**午前**:
- ✅ 既存データ分析スクリプト作成
- ✅ 優先度ソート実装
- ✅ Phase 8.1レポート作成

**午後**:
- ✅ BatchEpisodeImprover実装
- ✅ チェックポイント機構
- ✅ テストケース作成・実行

### Day 2: Phase 8.3実行

**午前**:
- ✅ テスト実行（5件）
- ✅ バッチ1実行（低スコア30件）

**午後**:
- ✅ バッチ2実行（中スコア50件）
- ✅ 統合・検証

### Day 3: Phase 8.4分析

**全日**:
- ✅ 統計分析
- ✅ レポート作成
- ✅ 教訓まとめ

---

## 🚨 リスクと対策

### リスク1: 予算超過

**リスク**: LLM使用で$2.50を超過
**対策**:
- CostManagerで厳密な制限
- 予算80%到達でアラート
- 自動的にForce_Patternに切り替え

### リスク2: 改善効果不足

**リスク**: スコア向上が期待未満
**対策**:
- テスト実行で早期検証
- プロンプト再調整オプション
- Hybrid戦略の活用

### リスク3: 処理時間超過

**リスク**: 100件処理に時間がかかりすぎる
**対策**:
- 並列処理の検討
- 優先度の高い件のみ実行
- バッチサイズの調整

### リスク4: システムエラー

**リスク**: API障害、メモリ不足等
**対策**:
- チェックポイント機構で復旧
- エラーログの詳細記録
- フォールバック機構

---

## 📚 参照ドキュメント

- `PHASE7_COMPLETION_REPORT.md` - Phase 7の成果
- `PHASE7_API_REFERENCE.md` - API仕様
- `PHASE7_QUICK_START.md` - 使用方法
- `PROJECT_STATUS.md` - プロジェクト全体状況

---

## ✅ Phase 8完了条件

1. ✅ 100エピソード改善完了
2. ✅ 合格率30%以上達成
3. ✅ 予算$2.50以内
4. ✅ 包括的レポート作成
5. ✅ 次フェーズへの提案

---

**Phase 8設計書 v1.0 - 2025-10-03**
