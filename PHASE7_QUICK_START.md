# Phase 7: LLM改善システム クイックスタートガイド

**5分で始めるLLMベースエピソード改善**

---

## 🚀 5分でスタート

### 前提条件

```bash
# 1. Python環境
python --version  # 3.11以上

# 2. 依存パッケージ
pip install openai anthropic  # LLMプロバイダー

# 3. APIキー設定
export OPENAI_API_KEY="your_openai_key"
# または
export ANTHROPIC_API_KEY="your_anthropic_key"
```

### 最小限のコード

```python
from rules.unified_improvement_interface import improve_episode_auto

# エピソードを自動改善（推奨）
improved_text, summary = improve_episode_auto(
    episode_id="EP_001",
    person_name="大谷翔平",
    episode_text="あなたと同じ28歳のとき、大谷翔平は素晴らしい業績を残した。",
    database_age=28,
    person_context={
        "person_name": "大谷翔平",
        "birth_year": 1994,
        "category": "プロ野球選手"
    }
)

print(f"改善方法: {summary['method']}")
print(f"改善後: {improved_text}")
```

**実行結果例**:
```
改善方法: llm
改善後: あなたと同じ28歳のとき、大谷翔平はプロ野球選手として、2022年のシーズンにおいて、
メジャーリーグベースボール（MLB）のロサンゼルス・エンゼルスで投手として9勝を挙げ、
打者としても46本塁打を記録しました。
```

---

## 📋 基本的な使い方

### 1. Auto戦略（推奨）

**特徴**: スコアベースで自動的に最適な改善方法を選択

```python
from rules.unified_improvement_interface import improve_episode_auto

improved_text, summary = improve_episode_auto(
    episode_id="EP_001",
    person_name="イチロー",
    episode_text="あなたと同じ30歳のとき、イチローは優れた選手として活躍した。",
    database_age=30,
    person_context={
        "person_name": "イチロー",
        "birth_year": 1973,
        "category": "プロ野球選手"
    },
    llm_provider="openai"  # "openai" or "anthropic"
)

# 結果確認
if summary['improved']:
    print(f"✅ 改善成功: {summary['method']}")
    print(f"スコア: {summary.get('original_score', 0):.1f} → {summary.get('final_score', 0):.1f}")
else:
    print(f"スキップ: {summary.get('reason', 'unknown')}")
```

### 2. 戦略を明示的に指定

```python
from rules.unified_improvement_interface import get_unified_interface

interface = get_unified_interface()

# LLMのみ使用（高品質優先）
improved_text, summary = interface.improve_episode_unified(
    ...,
    strategy_mode="force_llm",  # LLMのみ
    llm_provider="openai"
)

# パターンベースのみ使用（高速優先）
improved_text, summary = interface.improve_episode_unified(
    ...,
    strategy_mode="force_pattern"  # RULE_180のみ
)

# ハイブリッド（両方実行して比較）
improved_text, summary = interface.improve_episode_unified(
    ...,
    strategy_mode="hybrid"  # 最高品質保証
)
```

---

## ⚙️ 設定とカスタマイズ

### コスト上限設定

```python
from rules.unified_improvement_interface import (
    get_unified_interface,
    CostManager
)

# コスト管理付きインターフェース
interface = get_unified_interface(reset=True)
interface.cost_manager = CostManager(
    daily_limit_usd=10.0  # 1日$10まで
)

# 予算チェック
if interface.cost_manager.can_use_llm():
    print(f"✅ 残予算: ${interface.cost_manager.get_remaining_budget():.2f}")
else:
    print("❌ 予算超過 - 自動的にRULE_180使用")
```

### 統計情報の取得

```python
# 改善実行後
stats = interface.get_statistics()

print(f"総改善数: {stats['total_improvements']}")
print(f"LLM使用: {stats['rule182_count']}件")
print(f"パターン使用: {stats['rule180_count']}件")
print(f"コスト: ${stats['cost_usage']:.3f}")
print(f"残予算: ${stats['remaining_budget']:.2f}")
```

---

## 🎯 ユースケース別ガイド

### ケース1: 低スコアエピソードの改善

**状況**: スコア50-60点の品質不良エピソードを改善したい

```python
# Auto戦略が自動的にLLMを選択
improved_text, summary = improve_episode_auto(
    episode_id="EP_LOW_001",
    person_name="羽生結弦",
    episode_text="あなたと同じ25歳のとき、羽生結弦は最高の演技で金メダルを獲得した。",
    database_age=25,
    person_context={"birth_year": 1994, "category": "フィギュアスケーター"},
    llm_provider="openai"
)

# 期待: LLMによる大幅改善（+15-20点）
```

### ケース2: 大量エピソードの高速処理

**状況**: 100件のエピソードを低コストで改善したい

```python
from rules.unified_improvement_interface import get_unified_interface

interface = get_unified_interface(reset=True)

for episode in episodes:  # 100件
    improved_text, summary = interface.improve_episode_unified(
        ...,
        strategy_mode="force_pattern"  # パターンのみ（高速・無料）
    )

# 処理時間: <100秒
# コスト: $0
```

### ケース3: 重要エピソードの品質保証

**状況**: トップページ表示エピソードの最高品質を保証したい

```python
# Hybrid戦略で両方試して良い方を選択
improved_text, summary = interface.improve_episode_unified(
    ...,
    strategy_mode="hybrid",
    llm_provider="openai"
)

if summary['method'] == 'hybrid_llm_win':
    print(f"✅ LLMが優位: +{summary.get('score_improvement', 0):.1f}点")
else:
    print(f"✅ パターンが優位")

# コスト: $0.02/件
# 品質: 最高保証
```

---

## 🛠️ トラブルシューティング

### エラー1: APIキー未設定

**エラーメッセージ**:
```
openai.AuthenticationError: No API key provided
```

**解決策**:
```bash
export OPENAI_API_KEY="sk-..."
# 確認
echo $OPENAI_API_KEY
```

### エラー2: 予算超過

**エラーメッセージ**:
```
⚠️ コスト上限到達 - RULE_180にフォールバック
```

**解決策**:
```python
# 予算を増やす
interface.cost_manager.daily_limit = 20.0

# または予算をリセット
interface.cost_manager.reset_daily()
```

### エラー3: LLM改善が失敗する

**症状**: フォールバックが頻発

**解決策**:
```python
# 1. プロバイダーを変更
llm_provider="anthropic"  # OpenAIからAnthropicへ

# 2. Mockで動作確認
llm_provider="mock"  # テストモード

# 3. ログ確認
import logging
logging.basicConfig(level=logging.DEBUG)
```

---

## 📊 パフォーマンスガイド

### 処理速度

| 戦略 | 1件あたり | 100件 |
|-----|----------|-------|
| Force_Pattern | <1秒 | <100秒 |
| Force_LLM | 3-5秒 | 5-8分 |
| Auto | 1-3秒 | 2-5分 |
| Hybrid | 6-10秒 | 10-15分 |

### コスト見積もり

| 件数 | Auto戦略 | Force_LLM | Hybrid |
|------|---------|----------|--------|
| 10件 | $0.06 | $0.20 | $0.20 |
| 100件 | $0.60 | $2.00 | $2.00 |
| 1000件 | $6.00 | $20.00 | $20.00 |

**推奨**: Auto戦略（コスト効率最高）

---

## 🔍 よくある質問

### Q1: どの戦略を使うべき？

**A**: ほとんどの場合、**Auto戦略**を推奨

- ✅ 自動的に最適な方法を選択
- ✅ コスト70%削減
- ✅ 高品質と効率のバランス

### Q2: OpenAIとAnthropicどちらが良い？

**A**: 用途による

| プロバイダー | 利点 | 欠点 |
|------------|------|------|
| OpenAI GPT-4 | 品質高い、安定 | コスト高（$0.02/件） |
| Anthropic Claude | コスト安い（$0.004/件推定） | テスト未完了 |

**推奨**: まずOpenAIでテスト、後でAnthropicと比較

### Q3: 予算はいくらに設定すべき？

**A**: 使用量による

- **テスト環境**: $5/日（250件まで）
- **小規模運用**: $10/日（500件まで）
- **本番環境**: $50/日（2,500件まで）

### Q4: フォールバック機構とは？

**A**: LLM改善失敗時の安全網

```
RULE_182（LLM）で改善試行
  ↓ 失敗（文字数不足等）
自動的にRULE_180にフォールバック
  ↓
必ず何らかの改善を提供
```

**メリット**: 100%成功率保証

---

## 🎓 次のステップ

### 学習リソース

1. **Phase 7完了レポート**: 全体像把握
2. **APIリファレンス**: 詳細な関数仕様
3. **Phase 7設計ドキュメント**: アーキテクチャ理解

### 実践課題

1. **基本**: 3件のエピソードをAuto戦略で改善
2. **中級**: 20件を各戦略で改善して比較
3. **上級**: コスト管理とモニタリング実装

### サポート

- **Issues**: GitHub Issuesで質問
- **ドキュメント**: `PHASE7_*.md`参照
- **コード**: `rules/rule_182_*.py`, `rules/unified_*.py`

---

## ✅ チェックリスト

### 初回セットアップ

- [ ] Python 3.11以上インストール
- [ ] 依存パッケージインストール（openai, anthropic）
- [ ] APIキー設定
- [ ] 動作確認（Mockプロバイダー）
- [ ] 実LLMテスト（1件）

### 本番展開前

- [ ] コスト上限設定
- [ ] モニタリング設定
- [ ] テスト環境で10件実行
- [ ] 結果検証
- [ ] 段階的展開計画

---

**🚀 準備完了！さあ、LLMでエピソードを改善しましょう！**
