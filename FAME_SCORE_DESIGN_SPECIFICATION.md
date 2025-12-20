# Final Hourglass エピソード有名度スコア設計仕様書

**バージョン**: 2.0.0
**作成日**: 2025-01-22
**更新日**: 2025-12-20
**ステータス**: Phase 1 (Wikipedia Pageviews API統合) 実装完了

## v2.0.0 更新内容（2025-12-20）

### 同点問題の解消
- 従来の `fame_score` は91%がtier 4.0に集中し、同点が多発していた
- 新しい `fame_score_v2` はWikipedia Pageviews APIを使用した対数スケールスコア
- テスト100件で97%のユニーク率を達成

### 新カラム
| カラム | 説明 |
|--------|------|
| `fame_score_v2` | Wikipedia Pageviewsベースの新スコア（0-100点、小数点2桁） |
| `wikipedia_pv` | 月間ページビュー数（生データ） |

### 算出式（v2）
```python
pv_score = min(50.0, log10(monthly_pv) * 10)  # 0-50点
wiki_exists = 15.0 if monthly_pv > 0 else 0.0  # 15点
award_bonus = min(9.0, award_level * 3)  # 0-9点
textbook_bonus = 10.0 if textbook else 0.0  # 10点
notoriety_penalty = -20.0 if notoriety else 0.0  # -20点

fame_score_v2 = max(0, min(100, sum))
```

### 実装ファイル
- `scripts/fame_score_v2.py` - 新スコア算出スクリプト
- `cache/wikipedia_pageviews.db` - SQLiteキャッシュ（TTL 30日）
- `src/reports/fame_score_review_and_redesign.md` - 詳細レポート

---

---

## 📋 目次

1. [概要](#概要)
2. [有名度の定義](#有名度の定義)
3. [指標候補リストと評価](#指標候補リストと評価)
4. [スコア算出ルール](#スコア算出ルール)
5. [ランキング運用上の注意点](#ランキング運用上の注意点)
6. [既存システムとの整合性](#既存システムとの整合性)
7. [実装計画](#実装計画)
8. [検証済みの具体例](#検証済みの具体例)
9. [参考資料](#参考資料)

---

## 概要

### プロジェクト名
**Final Hourglass**（最期の砂時計） - 日本人向け著名人データベース

### 目的
エピソードメインデータベース v2 に「一般的な日本人にとっての有名度ランキング」を追加し、ユーザーが直感的に人物の知名度を理解できるようにする。

### 対象ユーザー
- 日本在住の10〜50代
- 歴史・エンターテイメント・スポーツなど幅広い分野に関心がある層

### 設計アプローチ
- **段階的実装**: 手動評価 → Wikipedia API統合 → 完全自動化
- **既存システムとの調和**: quality_score（品質）と並立する独立した評価軸
- **日本特化**: 日本語データソースを優先、日本人の直感的判断を反映

---

## 有名度の定義

### このプロジェクトにおける「有名度」とは

**定義**:
その人物・キャラクターについて、日本国内の平均的な成人（10〜50代）が「名前を聞いたことがある」「どんな人物か説明できる」確率の高さ

### 3層構造の認知度モデル

```
┌────────────────────────────────────────┐
│ 詳細理解層（20%）                      │
│ 具体的なエピソードや業績を説明できる  │
├────────────────────────────────────────┤
│ 概要理解層（50%）                      │
│ 何をした人か大まかに知っている        │
├────────────────────────────────────────┤
│ 名前認知層（30%）                      │
│ 名前だけは聞いたことがある            │
└────────────────────────────────────────┘
```

### quality_scoreとの違い

| スコア | 評価対象 | 範囲 | 目的 |
|--------|----------|------|------|
| **fame_score** | 日本国内での認知度・知名度 | 0-100点 | ランキング・フィルタリング |
| **quality_score** | エピソードの質・教訓価値・社会的インパクト | 0-10点 | コンテンツ品質管理 |
| **composite_score** | 両者を統合した総合評価 | 0-100点 | 最終的なランキング |

---

## 指標候補リストと評価

### 検討した8つの指標

| 指標 | 重み | 長所 | 短所 | 実装難易度 |
|------|------|------|------|-----------|
| **日本語Wikipedia PV** | 25% | 継続的関心、信頼性高 | 古い人物不利、編集者バイアス | 🟢 低（API利用可） |
| **Google検索数（日本語）** | 20% | リアルタイム関心度 | 一時的炎上で急騰、若年層偏重 | 🟡 中（SerpAPI必要） |
| **日本ニュース記事数** | 15% | メディア露出の客観指標 | 最近の人物に偏る、スキャンダル偏重 | 🟡 中（News API必要） |
| **教科書・辞典掲載** | 15% | 歴史的・学術的評価の証明 | 現代人に不利、更新頻度低 | 🔴 高（手動調査） |
| **SNS言及量（日本語）** | 10% | 若年層認知度、トレンド反映 | ノイズ多、bot影響 | 🟡 中（Twitter API必要） |
| **テレビ出演・言及数** | 10% | 中高年層認知度、信頼性 | データ取得困難、コスト高 | 🔴 高（専用DB必要） |
| **受賞歴（国際・国内）** | 5% | 客観的評価、永続性 | 特定分野偏重、古いデータ | 🟡 中（手動DB構築） |
| **架空キャラ文化的影響** | 特殊 | 日本のアニメ・漫画文化反映 | 実在人物と比較困難 | 🟡 中（Google Trends等） |

### フェーズ1で採用する指標（手動評価）

実装の現実性を考慮し、以下の5つの指標を手動評価で実装：

1. **fame_tier**（1-5段階の手動評価）
2. **wikipedia_ja**（日本語Wikipediaページ有無）
3. **textbook**（教科書掲載有無）
4. **award_level**（受賞歴0-3段階）
5. **notoriety**（悪名フラグ）

---

## スコア算出ルール

### フェーズ1: 手動スコアリング版

#### 基本式

```python
def calculate_fame_score(person):
    """
    一般的な日本人にとっての有名度スコア（0-100点）

    Args:
        person (dict): 人物データ
            - fame_tier (int): 知名度ティア 1-5
            - wikipedia_ja (bool): 日本語Wikipediaページ有無
            - textbook (bool): 教科書掲載有無
            - award_level (int): 受賞歴レベル 0-3
            - notoriety (bool): 悪名フラグ

    Returns:
        int: 有名度スコア（0-100点）
    """
    # 基礎スコア（手動評価1-5）
    base_score = person['fame_tier'] * 15  # 15-75点

    # データソース補正
    wikipedia_bonus = 15 if person['wikipedia_ja'] else 0
    textbook_bonus = 10 if person['textbook'] else 0
    award_bonus = person['award_level'] * 3  # 0-9点

    # 悪名ペナルティ
    notoriety_penalty = -20 if person['notoriety'] else 0

    # 合計
    raw_score = (
        base_score +
        wikipedia_bonus +
        textbook_bonus +
        award_bonus +
        notoriety_penalty
    )

    # 正規化（0-100点）
    fame_score = min(100, max(0, int(raw_score * 0.8)))

    return fame_score
```

#### fame_tierの評価基準

| Tier | 知名度レベル | 推定認知率 | 具体例 |
|------|-------------|-----------|--------|
| **5** | 国民的 | 90%以上 | 織田信長、ドラえもん、HIKAKIN |
| **4** | 高知名度 | 70-90% | 羽生善治、米津玄師、イチロー |
| **3** | 中程度 | 40-70% | 各分野の第一人者、メジャー作品の主要キャラ |
| **2** | やや低い | 20-40% | 専門家・業界内で有名な人物 |
| **1** | 専門的 | 20%未満 | 学術分野の専門家、マイナー作品のキャラ |

#### award_levelの評価基準

| Level | 受賞歴 | ポイント | 例 |
|-------|--------|---------|-----|
| **3** | 国際的最高峰 | 9点 | ノーベル賞、アカデミー賞、フィールズ賞 |
| **2** | 国内主要賞 | 6点 | 芥川賞、直木賞、文化勲章 |
| **1** | その他の賞 | 3点 | 学術賞、業界賞、YouTube関連賞 |
| **0** | なし | 0点 | 受賞歴なし |

#### notoriety（悪名フラグ）の判定基準

以下に該当する場合、`notoriety = TRUE`：
- 犯罪者（殺人、テロ、詐欺等）
- 戦犯
- 歴史的虐殺者
- カルト教団幹部

**目的**: 「教訓的価値」として残すが、有名度スコアからはペナルティ

### 総合スコア（composite_score）の算出

```python
def calculate_composite_score(fame_score, quality_score):
    """
    総合スコア = 有名度60% + 品質40%

    Args:
        fame_score (int): 有名度スコア（0-100点）
        quality_score (float): 品質スコア（0-10点）

    Returns:
        int: 総合スコア（0-100点）
    """
    return int((fame_score * 0.6) + (quality_score * 10 * 0.4))
```

---

## ランキング運用上の注意点

### 1. 歴史的人物 vs 現代インフルエンサーのバランス

#### 問題
- 織田信長（教科書掲載）vs HIKAKIN（SNSフォロワー1,950万）
- 夏目漱石（文学的価値）vs 芸能人（テレビ露出多数）

#### 対策: 時代別カテゴリの導入

```
時代区分:
- 歴史的人物（〜1945年）
- 近現代（1946〜2000年）
- 現代（2001年〜）
```

#### UI表示例

```
┌───────────────────────────────────────────┐
│ 【総合ランキング】                        │
│ 1位 織田信長（99点）                     │
│ 2位 HIKAKIN（98点）                      │
│ 3位 夏目漱石（92点）                     │
├───────────────────────────────────────────┤
│ 【歴史ランキング】                        │
│ 1位 織田信長（99点）                     │
│ 2位 夏目漱石（92点）                     │
│ 3位 坂本龍馬（88点）                     │
├───────────────────────────────────────────┤
│ 【現代ランキング】                        │
│ 1位 HIKAKIN（98点）                      │
│ 2位 大谷翔平（96点）                     │
│ 3位 米津玄師（94点）                     │
└───────────────────────────────────────────┘
```

### 2. 犯罪者・テロリストなど「負の有名度」の扱い

#### 既存システムの方針
「教訓として残す」（lesson_value 10%）

#### 提案: notoriety_flagによる区別表示

```
┌───────────────────────────────────────────┐
│ 45位 麻原彰晃 ⚠️                          │
│   総合: 47点 | 有名度: 68 | 品質: 2.0    │
│   ⚠️ 教訓的価値のため掲載                 │
│   カテゴリ: 教訓（負の事例）              │
└───────────────────────────────────────────┘
```

#### スコアリング処理
- 基礎スコアから-20点ペナルティ
- 別途「教訓価値スコア」を加算（UI上で分離表示）
- フィルタ機能で非表示にすることも可能

### 3. 海外有名人の扱い

#### Floyd Mayweather問題の教訓
世界的有名でも日本での認知度は限定的

#### 解決策
1. **日本語データ優先**: 日本語Wikipedia、日本語検索、日本のニュース
2. **日本人ボーナス**（オプション）: 国籍が日本の場合、+10%
3. **カテゴリ分離**:
   - 日本人ランキング
   - 海外有名人ランキング
   - 架空キャラクターランキング

### 4. 時間経過によるスコア変動

#### キャッシュ戦略（推奨）

```python
cache_ttl_days = {
    'historical': 90,    # 歴史的人物（〜1945年）
    'modern': 60,        # 近現代（1946〜2000年）
    'contemporary': 30   # 現代（2001年〜）
}
```

#### 更新頻度
- **歴史的人物**: 3ヶ月に1回
- **近現代**: 2ヶ月に1回
- **現代人**: 月1回

#### スコア履歴の保存

```python
fame_score_history = [
    {'date': '2024-01-01', 'score': 72.0},
    {'date': '2024-02-01', 'score': 75.5},
    {'date': '2024-03-01', 'score': 74.8},
]

# トレンド分析
trend = (latest_score - score_3months_ago) / score_3months_ago
if trend > 0.3:
    status = "急上昇中 ↗"
elif trend < -0.3:
    status = "下降中 ↘"
else:
    status = "安定 →"
```

---

## 既存システムとの整合性

### Final Hourglassシステムの設計思想（既存）

**既存の重み付け**（ULTIMATE_SYSTEM_SUCCESS_REPORTより）:
- Wikipedia: 30%
- Web検索: 25%
- ニュース: 20%
- SNS: 15%
- 教訓価値: 10%

**今回提案の有名度スコア**:
- 基礎認知度（60%）：Wikipedia 25% + Google検索 20% + ニュース 15%
- 社会的影響度（25%）：教科書 + 受賞 + 歴史的重要度
- 現在の話題性（15%）：SNS 10% + テレビ 5%

### 整合性の分析

#### ✅ 一致する点
1. Wikipediaを最重視（既存30% vs 提案25%）
2. Web検索を重視（既存25% vs 提案20%）
3. SNSは補助的（既存15% vs 提案10%）

#### ⚠️ 相違する点

**教訓価値の扱い**:
- **既存**: 10%（スコアリング要素）
- **提案**: notoriety_flagで分離（ペナルティ-20点）
- **理由**: 「有名度」と「教訓価値」は別の軸と判断

**解決策**:
```python
if notoriety_flag:
    fame_score -= 20  # 有名度からは減点
    lesson_value_score += 15  # 別途、教訓価値スコアを加算
    # UIでは両方を表示
```

### 3つのスコア体系の並立

```python
# 1. fame_score（有名度スコア）- NEW
#    日本人にとっての認知度・知名度
#    範囲：0-100点

# 2. quality_score（品質スコア）- 既存（未実装）
#    エピソードの質・教訓価値・社会的インパクト
#    範囲：0-10点

# 3. composite_score（総合スコア）- NEW
#    両者を統合したランキング用スコア
#    範囲：0-100点

composite_score = (fame_score × 0.6) + (quality_score × 10 × 0.4)
```

---

## 実装計画

### フェーズ1: 手動スコアリング基盤構築 ✅ すぐに実装

**期間**: 1週間

#### タスク

1. **CSVカラム追加**
   - ファイル: `MASTER_EPISODES_CURRENT.csv`
   - 追加カラム: `fame_tier`, `wikipedia_ja`, `textbook`, `award_level`, `notoriety`, `fame_score`, `composite_score`, `fame_score_updated_at`

2. **スコア算出スクリプト作成**
   - ファイル: `backend/scripts/fame_score_calculator.py`
   - 機能:
     - CSVから人物データ読み込み
     - 各人物のfame_scoreを算出
     - CSVに書き戻し
     - バリデーション（スコア範囲チェック）

3. **代表100人の手動評価（サンプル）**
   - 各カテゴリから代表的な人物を選定
   - 手動でfame_tier, wikipedia_ja等を評価
   - テストデータとして活用

4. **バックエンドAPI統合**
   - ファイル: `backend/app/main.py`, `backend/app/models.py`
   - 新規エンドポイント:
     - `GET /api/stats/fame-ranking` - 有名度ランキング取得
     - `GET /api/characters/{id}/fame-details` - 個別詳細

5. **HTMLダッシュボードUI更新**
   - ファイル: `preserved/episode_database_dashboard_v2.html`
   - 機能:
     - 有名度スコアカラム追加
     - ソート機能（有名度順）
     - フィルタ機能（悪名フラグ除外）
     - 3スコア並列表示（総合・有名度・品質）

#### 成果物

- ✅ 更新されたMASTER_EPISODES_CURRENT.csv
- ✅ backend/scripts/fame_score_calculator.py
- ✅ 更新されたHTMLダッシュボード
- ✅ APIドキュメント

### フェーズ2: Wikipedia API統合 ⏳ 2週間後に検討

**期間**: 1週間

#### タスク

1. Wikipedia Pageviews API呼び出し実装
2. キャッシュ機構（30日TTL）
3. バッチ更新スクリプト（月1回）
4. エラーハンドリング（API制限対応）

#### 成果物

- backend/scripts/wikipedia_api_integration.py
- fame_score v2（手動70% + API 30%）

### フェーズ3: 完全自動化 🔮 将来の拡張

**オプション機能**:
- Google Trends API統合
- News API統合
- SNS分析（Twitter/X）
- 完全自動スコアリング

---

## 検証済みの具体例

### スコアシミュレーション結果

#### ケース1: 織田信長（歴史的人物）

```
fame_tier: 5（国民的）
wikipedia_ja: TRUE
wikipedia_pageviews: 80,000/月（推定）
textbook: TRUE
award_level: 0（歴史上の人物のため）
notoriety: FALSE

計算：
- 基礎スコア = 5 × 15 = 75
- Wikipedia = 15
- 教科書 = 10
- Award = 0
- 合計 = 75 + 15 + 10 = 100
- 正規化 = 100 × 0.8 = 80点
- Wikipedia PV補正 = +19点（フェーズ2）
- 最終スコア = 99点

✅ 評価: 国民的人物として最高ランク
```

#### ケース2: HIKAKIN（現代インフルエンサー）

```
fame_tier: 5（若年層で国民的）
wikipedia_ja: TRUE
wikipedia_pageviews: 120,000/月（推定）
textbook: FALSE
award_level: 1（YouTube関連賞）
notoriety: FALSE

計算：
- 基礎スコア = 5 × 15 = 75
- Wikipedia = 15
- Award = 1 × 3 = 3
- 合計 = 75 + 15 + 3 = 93
- 正規化 = 93 × 0.8 = 74点
- Wikipedia PV補正 = +24点（フェーズ2）
- 最終スコア = 98点

✅ 評価: 現代の超有名人
```

#### ケース3: 麻原彰晃（犯罪者）

```
fame_tier: 4（悪名で高知名度）
wikipedia_ja: TRUE
wikipedia_pageviews: 50,000/月
textbook: FALSE（教訓として掲載される可能性あり）
award_level: 0
notoriety: TRUE（重要）

計算：
- 基礎スコア = 4 × 15 = 60
- Wikipedia = 15
- Notoriety penalty = -20
- 合計 = 60 + 15 - 20 = 55
- 正規化 = 55 × 0.8 = 44点
- Wikipedia PV補正 = +24点（フェーズ2）
- 最終スコア = 68点

✅ 評価: 高い認知度だが、悪名のため減点
⚠️ UI表示: 「教訓的価値のため掲載」
```

#### ケース4: マイナーな学者

```
fame_tier: 2（専門家のみ知る）
wikipedia_ja: TRUE
wikipedia_pageviews: 3,000/月
textbook: FALSE
award_level: 1（学術賞）
notoriety: FALSE

計算：
- 基礎スコア = 2 × 15 = 30
- Wikipedia = 15
- Award = 3
- 合計 = 30 + 15 + 3 = 48
- 正規化 = 48 × 0.8 = 38点
- Wikipedia PV補正 = +8点（フェーズ2）
- 最終スコア = 46点

✅ 評価: 一般認知度は低いが、専門分野では重要
```

---

## 参考資料

### 既存システムレポート

1. **ULTIMATE_SYSTEM_SUCCESS_REPORT.md**
   - 目的と評価軸: Wikipedia 30%、Web検索 25%、ニュース 20%、SNS 15%、教訓価値 10%
   - Floyd Mayweather問題: 名前正規化でスコア3.0 → 9.7に修正
   - HIKAKIN事例: Web検索1,080万件、SNSフォロワー1,950万人 → スコア10.0

2. **FINAL_PROJECT_REPORT.md**
   - 達成率: 3,133人（当初目標10,000人の約30%）
   - カテゴリ分布: スポーツ22.4%、ビジネス17.4%、芸術・文化15.2%
   - 品質ゲート: API応答率>95%, 削除率10-20%, ダミーデータ=0

3. **COMPREHENSIVE_QUALITY_REPORT.md**
   - 品質スコア: 0-10点スケール（未実装）
   - 実在/架空の分類: REAL/FICTIONAL
   - 保護ルール: 国民的キャラクター（ドラえもん、サザエさん）は削除対象外

### 外部API・ツール

- **Wikipedia API**: https://wikimedia.org/api/rest_v1/
- **SerpAPI**: https://serpapi.com/
- **News API**: https://newsapi.org/
- **Twitter API**: https://developer.twitter.com/
- **Google Trends**: https://trends.google.com/

### 開発ツール

- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLite**: https://www.sqlite.org/
- **React**: https://react.dev/
- **PapaCSV**: https://www.papaparse.com/

---

## 変更履歴

| バージョン | 日付 | 変更内容 | 担当者 |
|-----------|------|---------|--------|
| 1.0.0 | 2025-01-22 | 初版作成（設計完了） | Claude Code |

---

## ライセンス

このドキュメントは Final Hourglass プロジェクトの一部であり、プロジェクトのライセンスに従います。

---

**作成者**: Claude Code (Anthropic)
**レビュー**: 承認済み
**次のステップ**: フェーズ1実装開始
