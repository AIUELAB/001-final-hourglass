# エピソード生成システム改善提案書

## 🔴 問題の詳細分析

### 1. 根本原因

#### 1.1 LLMの本質的問題
- **ハルシネーション傾向**: LLMは学習データの混在により、異なる人物の情報を混同
- **創造性と正確性のトレードオフ**: 面白いエピソードを作ろうとすると事実が歪む
- **時系列の混乱**: 年代情報が正確に処理されない

#### 1.2 システム設計の問題
- **検証プロセスの欠如**: 生成後の事実確認が行われていない
- **データソースの信頼性**: Wikipedia APIだけでは不十分
- **プロンプトの曖昧さ**: 「具体的」を求めると「創作」してしまう

### 2. 発見された誤情報パターン

| 人物 | 誤情報 | 正しい情報 | 原因分析 |
|------|--------|------------|----------|
| Ado | ヨルシカとコラボで「うっせぇわ」| syudouが作詞作曲 | 複数アーティストの混同 |
| Ado | デビューアルバム「Ado」| 1stアルバム「狂言」| 存在しない作品名の創作 |
| Ado | 21歳でデビュー | 18歳でデビュー | 年齢計算の誤り |
| Fukase | 「アイアムアヒーロー」500万DL | 存在しない曲 | 完全な創作 |
| Fukase | オリコン賞2年連続 | 受賞歴なし | 他アーティストとの混同 |

## 🛡️ 改善提案

### 1. 三層防御システムの実装

```python
class ThreeLayerDefenseSystem:
    """三層防御システム"""

    def __init__(self):
        self.pre_validator = PreGenerationValidator()    # 事前検証
        self.generator = SafeEpisodeGenerator()          # 安全生成
        self.post_validator = PostGenerationValidator()  # 事後検証

    def generate_episode(self, person_data):
        # 第1層: 事前検証
        verified_facts = self.pre_validator.verify_facts(person_data)

        # 第2層: 制約付き生成
        episode = self.generator.generate_with_facts(verified_facts)

        # 第3層: 事後検証
        validated_episode = self.post_validator.validate_and_correct(episode)

        return validated_episode
```

### 2. 事実データベースの構築

#### 2.1 信頼できるデータソース
- **Wikipedia日本語版**: 基本情報
- **公式サイト**: アーティストの正確な作品情報
- **ニュースアーカイブ**: 日付と事実の確認
- **手動検証済みDB**: よく使われる人物の正確な情報

#### 2.2 データ構造
```python
VERIFIED_FACTS_DB = {
    'person_id': {
        'basic_info': {...},
        'timeline': [...],         # 年表形式の事実
        'achievements': [...],      # 検証済み実績
        'works': [...],            # 作品リスト
        'common_mistakes': [...],   # よくある間違い
        'reliable_sources': [...]   # 信頼できる情報源
    }
}
```

### 3. プロンプトエンジニアリングの改善

#### 3.1 事実優先プロンプト
```python
FACT_FIRST_PROMPT = """
以下の検証済み事実のみを使用してエピソードを作成：

【使用可能な事実】
{verified_facts}

【絶対禁止事項】
- 上記以外の情報の追加
- 数値の変更や誇張
- 推測や創作

【必須フォーマット】
「あなたと同じ{age}歳のとき、{name}は」で始め、
上記の事実から1-2個を選んで150-230文字で記述。
"""
```

#### 3.2 温度パラメータの調整
- `temperature=0.1`: 事実重視（創造性最小）
- `top_p=0.9`: 確率の高い選択肢のみ使用
- `max_tokens=300`: 長すぎる生成を防ぐ

### 4. 品質保証プロセス

#### 4.1 自動検証
```python
class QualityAssurance:
    def validate_episode(self, episode, facts):
        checks = {
            'fact_accuracy': self.check_facts(episode, facts),
            'no_hallucination': self.detect_hallucination(episode),
            'year_consistency': self.check_years(episode),
            'name_accuracy': self.check_names(episode),
            'number_validity': self.check_numbers(episode)
        }

        return all(checks.values()), checks
```

#### 4.2 人間によるスポットチェック
- 有名人（HIKAKIN、Ado等）での定期的な検証
- ランダムサンプリングでの品質確認
- ユーザーフィードバックの収集

### 5. 実装ロードマップ

| フェーズ | 内容 | 期間 | 優先度 |
|---------|------|------|--------|
| Phase 1 | 事実DBの構築（上位100人） | 1週間 | 🔴 高 |
| Phase 2 | 三層防御システム実装 | 3日 | 🔴 高 |
| Phase 3 | プロンプト最適化 | 2日 | 🟡 中 |
| Phase 4 | 自動検証システム | 1週間 | 🟡 中 |
| Phase 5 | 継続的改善プロセス | 継続 | 🟢 低 |

## 📊 期待される改善効果

### 定量的目標
- **事実正確性**: 60% → 95%以上
- **ハルシネーション率**: 40% → 5%以下
- **ユーザー満足度**: 向上見込み
- **処理コスト**: 若干増加（検証プロセス追加）

### 定性的効果
- ブランド信頼性の向上
- クレーム・修正要求の削減
- サービス品質の安定化
- 将来的な拡張性の確保

## 🚀 次のアクション

1. **即座に実施**
   - 既知の誤情報パターンのハードコード修正
   - temperatureパラメータを0.1に下げる
   - 生成後の基本的なファクトチェック追加

2. **今週中に実施**
   - 上位20人の検証済みデータ作成
   - 改善版プロンプトのA/Bテスト
   - エラーログの詳細分析

3. **今月中に実施**
   - 完全な三層防御システムの実装
   - 100人分の検証済みDBの構築
   - 品質モニタリングダッシュボード作成

## まとめ

現在のシステムの最大の問題は、**LLMの創造性に依存しすぎて事実確認を怠っていること**です。

提案する改善策の核心は：
1. **事実を先に用意する**（生成ではなく選択）
2. **制約を強くする**（創造性より正確性）
3. **多層的に検証する**（信頼性の確保）

これにより、「面白いが間違っている」から「正確で価値がある」エピソードへの転換を実現します。
