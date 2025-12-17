# Stage 3: curate-episodes - エピソード生成（LLM統合）

## 📋 概要

Stage 3は、検証済みのソース（verified_sources.csv）をEPUP形式のエピソードに変換するステージです。Claude APIを使用して、事実情報を「あなたと同じ{age}歳のとき、...」形式の自然なエピソードに変換します。

## 🔄 パイプラインフロー

```
verified_sources.csv
    ↓
[Stage 3: curate-episodes]
    ├─ 年齢抽出（contextフィールドから）
    ├─ LLMでEPUP形式に変換
    ├─ CuratedEpisodeモデル作成
    └─ バリデーション（基本チェックのみ）
    ↓
curated_episodes.csv
```

## 📥 入力データ

### verified_sources.csv

| カラム | 説明 | 例 |
|--------|------|-----|
| source_id | ソースID（MD5ハッシュ） | SRC-3a765f0b433a1083 |
| person_name | 人物名 | イチロー |
| person_id | 人物ID | P001 |
| person_type | 人物タイプ | REAL/FICTIONAL |
| raw_text | 元テキスト | 2004年シーズン262安打記録を達成 |
| context | コンテキスト | 年齢31歳時の業績 |
| evidence_quality | 根拠品質 | A/B |
| source_url | ソースURL | https://... |
| category | カテゴリ | スポーツ |

**重要**: `context`フィールドに年齢情報が必須です（例: "年齢31歳時の業績"、"40歳のときの発見"）

## 📤 出力データ

### curated_episodes.csv

| カラム | 説明 | 例 |
|--------|------|-----|
| episode_id | エピソードID | （空：Stage 4でマージ時に採番） |
| person_id | 人物ID | P001 |
| person_name | 人物名 | イチロー |
| age | 年齢 | 31 |
| episode_text | エピソード本文 | あなたと同じ31歳のとき、... |
| source_id | ソースID | SRC-3a765f0b433a1083 |
| source_url | ソースURL | https://... |
| evidence_quality | 根拠品質 | B |
| validation_status | バリデーション状態 | pending |
| validation_issues | 検出された問題 | （空） |
| generated_at | 生成日時 | 2025-12-17T22:04:54.229698 |
| person_type | 人物タイプ | REAL |
| category | カテゴリ | スポーツ |

## 🚀 使用方法

### 基本実行（ドライラン）

```bash
# 環境変数から自動読み込み（.envファイル）
source .env
python scripts/pipeline_curate_episodes.py --dry-run
```

### 本番実行（ファイル書き込み）

```bash
source .env
python scripts/pipeline_curate_episodes.py --execute
```

### オプション

```bash
python scripts/pipeline_curate_episodes.py \
  --input generated/verified_sources.csv \
  --output generated/curated_episodes.csv \
  --api-key YOUR_API_KEY \
  --execute \
  --max-sources 10  # 最大処理件数を制限（テスト用）
```

## 🔑 API Key設定

### 方法1: 環境変数（推奨）

```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
```

または`.env`ファイルに記載：

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### 方法2: コマンドライン引数

```bash
python scripts/pipeline_curate_episodes.py --api-key sk-ant-api03-... --execute
```

## 📊 処理ロジック

### 1. 年齢抽出

`extract_age_from_context()`関数が以下のパターンで年齢を抽出：

| パターン | 例 | 抽出結果 |
|---------|-----|---------|
| 年齢XX歳時 | 年齢31歳時の業績 | 31 |
| XX歳のとき | 40歳のときの発見 | 40 |
| XX歳時 | 23歳時の業績 | 23 |

年齢が抽出できない場合、そのソースはスキップされます。

### 2. EPUP形式変換

`convert_to_epup_format()`関数がClaude APIを使用してEPUP形式に変換：

#### プロンプト構造

**システムプロンプト**:
```
あなたはエピソードライターです。
与えられた情報を「あなたと同じ{age}歳のとき、{person_name}は...」形式に変換してください。

重要なルール：
1. 必ず「あなたと同じ」で始める
2. 事実を正確に保つ
3. 簡潔に（2-3文で完結）
4. メタ的表現を避ける
5. 架空キャラクターの場合も作品世界内の視点で書く
6. 敬称は基本的に省略
7. 読者に語りかける自然な文体
```

**ユーザープロンプト（実在人物）**:
```
人物名: イチロー（実在人物）
年齢: 31歳
情報: 2004年シーズン262安打記録を達成。メジャーリーグ記録更新。
コンテキスト: 年齢31歳時の業績

この情報を「あなたと同じ31歳のとき、イチローは...」形式のエピソードに変換してください。
事実に基づいた正確な記述を心がけてください。
```

**ユーザープロンプト（架空キャラクター）**:
```
人物名: ドラえもん（架空キャラクター）
年齢: 10歳
情報: 22世紀からやってきた猫型ロボット
コンテキスト: 作品設定

この情報を「あなたと同じ10歳のとき、ドラえもんは...」形式のエピソードに変換してください。
架空キャラクターですが、作品世界内の視点で自然なエピソードとして記述してください。
メタ的な説明（「架空のキャラクターです」等）は絶対に含めないでください。
```

#### API設定

- **Model**: `claude-sonnet-4-5-20250929`
- **Temperature**: `0.3`（低温度で事実性を重視）
- **Max Tokens**: `500`

### 3. CuratedEpisode作成

変換されたエピソードテキストを使ってCuratedEpisodeインスタンスを作成：

```python
curated = CuratedEpisode(
    person_id=person_id,
    person_name=person_name,
    age=age,
    episode_text=episode_text,  # LLMで生成
    source_id=source_id,
    source_url=source_url,
    evidence_quality=evidence_quality,
    person_type=person_type,
    category=category,
    validation_status="pending",  # Stage 4でバリデーション
)
```

### 4. バリデーション（基本チェックのみ）

CuratedEpisodeモデルの`validate()`メソッドで基本チェック：

- 必須フィールド存在確認
- age範囲検証（0-150）
- evidence_quality値検証（A/B/C）
- person_type値検証（REAL/FICTIONAL）
- episode_text基本フォーマット検証（「あなたと同じ」で始まるか）

**注意**: 詳細なバリデーション（テンプレート検出、事実性チェック等）はStage 4で実施します。

## 📈 出力統計

スクリプト実行後に表示される統計：

```
📊 統計:
  総ソース数: 5
  成功: 3
  失敗: 2
    - 年齢抽出失敗: 2
    - LLM変換失敗: 0
```

### レポートファイル

`reports/episode_curation_YYYYMMDD_HHMMSS.json`に詳細レポートが保存されます：

```json
{
  "timestamp": "2025-12-17T22:05:04.839842",
  "input_csv": ".../verified_sources.csv",
  "output_csv": ".../curated_episodes.csv",
  "statistics": {
    "total_sources": 5,
    "successful": 3,
    "failed": 2,
    "age_extraction_failed": 2,
    "llm_conversion_failed": 0
  }
}
```

## ✅ 成功例

### 実在人物（イチロー）

**入力（verified_sources.csv）**:
```csv
source_id,person_name,age,raw_text,context,evidence_quality
SRC-...,イチロー,31,2004年シーズン262安打記録を達成,年齢31歳時の業績,B
```

**出力（curated_episodes.csv）**:
```csv
episode_id,person_name,age,episode_text,evidence_quality
,イチロー,31,"あなたと同じ31歳のとき、イチローはメジャーリーグのシーズン最多安打記録を84年ぶりに更新しました。2004年シーズン、262安打という驚異的な数字を叩き出し、ジョージ・シスラーが1920年に作った257安打の記録を破ったのです。この偉業は、日本人選手として、そしてメジャーリーグ史に永遠に刻まれる記録となりました。",B
```

### 架空キャラクター（適切な年齢情報があれば）

**入力**:
```csv
source_id,person_name,person_type,raw_text,context,evidence_quality
SRC-...,孫悟空,FICTIONAL,スーパーサイヤ人に覚醒,年齢24歳時の戦闘,A
```

**出力**:
```csv
episode_text
"あなたと同じ24歳のとき、孫悟空は初めてスーパーサイヤ人に覚醒しました。仲間であるクリリンがフリーザに殺され、激しい怒りに包まれた瞬間、金色の髪と青い瞳を持つ伝説の戦士へと変身を遂げたのです。"
```

## ⚠️ エラーケース

### 1. 年齢抽出失敗

**原因**: contextフィールドに年齢情報がない

```csv
context
"作品設定"  # 年齢が含まれていない
"自伝より"  # 年齢が含まれていない
```

**対処**:
- Stage 1のデータ収集時にcontextに年齢を含める
- または、manual_sources.csvで明示的に年齢を指定

### 2. LLM API エラー

**エラーメッセージ**:
```
❌ LLM conversion failed for イチロー: API Error
```

**原因**:
- API keyが無効
- レート制限超過
- ネットワークエラー

**対処**:
```bash
# API key確認
echo $ANTHROPIC_API_KEY

# .envファイル確認
cat .env | grep ANTHROPIC_API_KEY

# レート制限の場合は--max-sourcesで件数を制限
python scripts/pipeline_curate_episodes.py --execute --max-sources 3
```

### 3. バリデーションエラー

**エラーメッセージ**:
```
ValueError: Invalid age: 200. Must be 0-150
```

**原因**: 年齢範囲が不正

**対処**: contextフィールドの年齢データを修正

## 🔧 トラブルシューティング

### Q1: ドライランと本番実行の違いは？

**A**:
- `--dry-run`: ファイル書き込みを行わず、処理結果のみ表示
- `--execute`: curated_episodes.csvに実際に書き込み

### Q2: 全ソースが年齢抽出失敗する

**A**: verified_sources.csvのcontextカラムを確認してください：

```python
# 確認スクリプト
import pandas as pd
df = pd.read_csv("generated/verified_sources.csv", encoding="utf-8-sig")
print(df[["person_name", "context"]])
```

contextに年齢情報（「年齢XX歳時」等）が含まれているか確認。

### Q3: LLMが「あなたと同じ」で始まらない

**A**: スクリプトは自動修正を試みますが、失敗する場合は：

```python
# 手動修正
episode_text = f"あなたと同じ{age}歳のとき、{original_text}"
```

または、プロンプトを調整してLLM出力を改善。

### Q4: APIコストを抑えたい

**A**:
- `--max-sources`で処理件数を制限
- テストは`--dry-run`で実行（API呼び出しなし）
- `temperature=0.3`に設定済み（低コスト）

### Q5: カスタムプロンプトを使いたい

**A**: `scripts/pipeline_curate_episodes.py`の`convert_to_epup_format()`関数内の`system_prompt`と`user_prompt`を編集してください。

## 📝 次のステージ

Stage 3完了後は、Stage 4: validate-and-mergeに進みます：

```bash
# Stage 4（今後実装予定）
python scripts/pipeline_validate_and_merge.py --execute
```

Stage 4では：
- 詳細なバリデーション（テンプレート検出、事実性チェック等）
- 品質ゲート通過判定
- MASTER_EPISODES_CURRENT.csvへのマージ
- review_queue.csv生成（レビュー必要なエピソード）

## 🧪 テスト

### テスト実行

```bash
# 全テスト実行
pytest tests/test_pipeline_curate_episodes.py -v

# カバレッジ付き
pytest tests/test_pipeline_curate_episodes.py --cov=src.models.curated_episode --cov=scripts.pipeline_curate_episodes
```

### テストカバレッジ

- 年齢抽出ロジック: 6テスト
- EPUP変換（モック使用）: 3テスト
- CuratedEpisodeモデル: 6テスト
- 統合テスト: 2テスト

合計: **17テスト**、全てパス

## 📚 関連ドキュメント

- [Stage 1: collect-sources](./PIPELINE_COLLECT_SOURCES.md)
- [Stage 2: verify-sources](./PIPELINE_VERIFY_SOURCES.md)
- [Data Models](./DATA_MODELS.md)
- [EPUP (Episode Quality Protocol)](../CLAUDE.md#epup)

## 🎯 まとめ

Stage 3では：

✅ verified_sources.csvから年齢を自動抽出
✅ Claude APIでEPUP形式に変換
✅ 事実を正確に保ちながら自然な文章生成
✅ 架空キャラクターにも対応
✅ 基本バリデーションを実施
✅ curated_episodes.csvに保存

次のStage 4で詳細なバリデーションとマージを実施します。
