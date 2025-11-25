# 統一エピソードファクトリ API ドキュメント

## 概要
統一エピソードファクトリv2は、高品質なエピソード生成を保証する統合システムです。

## クイックスタート

```python
from unified_episode_factory_v2 import UnifiedEpisodeFactory, EpisodeGenerationRequest

# ファクトリの初期化
factory = UnifiedEpisodeFactory(use_optimized=True)

# リクエスト作成
request = EpisodeGenerationRequest(
    person_name="大谷翔平",
    age=29,
    category="sports",
    min_quality_score=70.0,
    use_optimized=True
)

# エピソード生成
response = factory.generate(request)

if response.success:
    print(f"エピソード: {response.episode}")
    print(f"品質スコア: {response.quality_score}")
```

## API リファレンス

### UnifiedEpisodeFactory

統一エピソードファクトリのメインクラス

#### コンストラクタ

```python
UnifiedEpisodeFactory(use_optimized: bool = True)
```

**パラメータ:**
- `use_optimized` (bool): 最適化バリデーションシステムを使用するか（デフォルト: True）

#### メソッド

##### generate()

```python
generate(request: EpisodeGenerationRequest) -> EpisodeGenerationResponse
```

エピソードを生成する唯一の公開メソッド

**パラメータ:**
- `request` (EpisodeGenerationRequest): 生成リクエスト

**戻り値:**
- `EpisodeGenerationResponse`: 生成結果

### EpisodeGenerationRequest

エピソード生成リクエストのデータクラス

```python
@dataclass
class EpisodeGenerationRequest:
    person_name: str              # 人物名（必須）
    age: int                      # 年齢（必須）
    category: Optional[str]       # カテゴリ（任意）
    focus_area: Optional[str]     # フォーカス分野（任意）
    min_quality_score: float      # 最小品質スコア（デフォルト: 70.0）
    max_attempts: int             # 最大試行回数（デフォルト: 5）
    strict_mode: bool             # 厳格モード（デフォルト: False）
    use_optimized: bool           # 最適化使用（デフォルト: True）
```

### EpisodeGenerationResponse

エピソード生成レスポンスのデータクラス

```python
@dataclass
class EpisodeGenerationResponse:
    success: bool                           # 成功フラグ
    episode: Optional[str]                  # 生成されたエピソード
    quality_score: float                    # 品質スコア（0-100）
    validation_result: Optional[ValidationResult]  # バリデーション結果
    pipeline_result: Optional[PipelineResult]      # パイプライン結果
    attempts: int                           # 試行回数
    generation_time_ms: float               # 生成時間（ミリ秒）
    error_message: Optional[str]            # エラーメッセージ
    improvement_history: List[Dict]         # 改善履歴
```

## カテゴリ

サポートされているカテゴリ：

- `sports` - スポーツ選手
- `entertainment` - 芸能人、アーティスト
- `science` - 科学者、研究者
- `business` - 実業家、経営者
- `literature` - 作家、文学者
- `history` - 歴史的人物
- `default` - その他

## バリデーションシステム

### OptimizedValidationSystem（推奨）

最適化されたバリデーションシステム（成功率100%）

**特徴:**
- 文字数基準: 130-250文字
- カテゴリ別許可フレーズ
- 緩和されたテンプレート検出
- 高速処理（平均6.73ms）

### UnifiedValidationSystem

標準バリデーションシステム（厳格モード）

**特徴:**
- 文字数基準: 132-250文字
- 厳格なテンプレート検出
- 完全な固有名詞要件

## 使用例

### 基本的な使用

```python
# シンプルな生成
factory = UnifiedEpisodeFactory()
request = EpisodeGenerationRequest(
    person_name="新垣結衣",
    age=28
)
response = factory.generate(request)
```

### カテゴリ指定

```python
# スポーツカテゴリで生成
request = EpisodeGenerationRequest(
    person_name="羽生結弦",
    age=23,
    category="sports"
)
response = factory.generate(request)
```

### 品質基準カスタマイズ

```python
# 高品質基準で生成
request = EpisodeGenerationRequest(
    person_name="村上春樹",
    age=40,
    category="literature",
    min_quality_score=90.0,  # 90点以上を要求
    max_attempts=10          # 最大10回試行
)
response = factory.generate(request)
```

### バッチ処理

```python
# 複数人物の一括処理
people = [
    ("大谷翔平", 29, "sports"),
    ("新垣結衣", 28, "entertainment"),
    ("山中伸弥", 50, "science")
]

results = []
for name, age, category in people:
    request = EpisodeGenerationRequest(
        person_name=name,
        age=age,
        category=category
    )
    response = factory.generate(request)
    if response.success:
        results.append(response.episode)
```

## パフォーマンス

### ベンチマーク結果

| 指標 | 値 |
|------|-----|
| 平均レスポンスタイム | 6.73ms |
| 成功率 | 100% |
| 平均品質スコア | 99.1/100 |
| スループット | 404 req/s |

### 推奨設定

**高速処理優先:**
```python
factory = UnifiedEpisodeFactory(use_optimized=True)
request.min_quality_score = 70.0
request.max_attempts = 3
```

**高品質優先:**
```python
factory = UnifiedEpisodeFactory(use_optimized=False)
request.min_quality_score = 90.0
request.max_attempts = 10
request.strict_mode = True
```

## エラーハンドリング

```python
response = factory.generate(request)

if not response.success:
    print(f"エラー: {response.error_message}")

    # 改善履歴を確認
    for history in response.improvement_history:
        print(f"試行{history['attempt']}: スコア{history['score']}")
        for issue in history['issues']:
            print(f"  - {issue}")
```

## データベース

### 人物データ構造

```json
{
  "persons": {
    "大谷翔平": {
      "facts": {
        "achievements": ["WBC優勝", "MVP獲得"],
        "numbers": ["44本塁打", "10勝5敗"],
        "works": []
      }
    }
  }
}
```

### サポート人物数

- 総数: 135人
- カテゴリ別:
  - sports: 45人
  - entertainment: 35人
  - science: 20人
  - business: 15人
  - literature: 10人
  - history: 10人

## トラブルシューティング

### よくある問題

**Q: "警告: 不正な呼び出し元" が表示される**
A: 許可リストに呼び出し元ファイルを追加してください。

**Q: 文字数が足りない**
A: `use_optimized=True` を設定し、拡張テンプレートを使用してください。

**Q: 品質スコアが低い**
A: カテゴリを正しく指定し、人物がデータベースに存在することを確認してください。

## ライセンスと制限

- 商用利用: 要相談
- 最大同時接続: 400 req/s
- データベース更新: 月1回

## サポート

- GitHub Issues: [プロジェクトリポジトリ]
- メール: support@example.com

---

最終更新: 2025年1月
バージョン: 2.0.0
