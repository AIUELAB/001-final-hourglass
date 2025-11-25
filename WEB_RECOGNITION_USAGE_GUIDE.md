# 📊 Web検索による知名度測定システム - 使用ガイド

## 🚀 システム概要

このシステムは、Ultra Thinkデータベース内の人物のWeb上での知名度を定量的に測定するために設計されています。複数の検索プロバイダーを統合し、コスト効率的な知名度スコア（0-100）を算出します。

## 🎯 特徴

- **複数検索プロバイダー対応**: Brave Search MCP、Google Custom Search API、Web Scraping
- **インテリジェントキャッシュ**: 1週間の結果キャッシュによるコスト削減
- **バッチ処理**: 大規模データの効率的な並行処理
- **レート制限対応**: API制限を考慮した自動調整
- **詳細な統計**: コスト、処理時間、エラー率の完全トラッキング

## 📋 前提条件

### Python環境
```bash
# 必要なライブラリ
pip install pandas requests beautifulsoup4 asyncio

# 既存プロジェクトの場合
source venv/bin/activate  # 仮想環境有効化
```

### APIキー設定（オプション）
```bash
# Google Custom Search API使用時
export GOOGLE_API_KEY="your_google_api_key"
export GOOGLE_SEARCH_ENGINE_ID="your_search_engine_id"

# Brave Search API使用時
export BRAVE_API_KEY="your_brave_api_key"
```

## 🚀 基本的な使用方法

### 1. Brave Search MCP使用（推奨）
```bash
# 基本的なバッチ処理（50件、Brave Search）
python web_recognition_system.py --mode brave --batch-size 50

# 開始位置指定
python web_recognition_system.py --mode brave --batch-size 100 --start-from 500

# レート制限調整（秒）
python web_recognition_system.py --mode brave --rate-limit 3.0 --max-concurrent 2
```

### 2. Google Custom Search API使用
```bash
# Google API（高精度、有料）
python web_recognition_system.py \
  --mode google \
  --google-api-key "YOUR_API_KEY" \
  --google-search-engine-id "YOUR_ENGINE_ID" \
  --batch-size 25  # 無料枠考慮
```

### 3. Web Scraping使用（無料、制限あり）
```bash
# Webスクレイピング（無料、リーガルリスク考慮）
python web_recognition_system.py --mode scraping --rate-limit 5.0
```

## 📊 コスト分析

### プロバイダー別コスト比較

| プロバイダー | コスト/1000クエリ | 無料枠 | 精度 | 推奨用途 |
|-------------|------------------|---------|------|----------|
| **Brave Search** | $不明 (APIキー要) | 不明 | ⭐⭐⭐⭐ | メイン運用 |
| **Google Custom** | $5.00 | 100クエリ/日 | ⭐⭐⭐⭐⭐ | 高精度検証 |
| **Web Scraping** | 無料 | サイト依存 | ⭐⭐ | 試験運用 |

### 大規模処理のコスト見積もり

```python
# Ultra Thinkデータベース全体（約17,000件）のコスト試算

# Google Custom Search使用時
total_records = 17000
cost_per_1000 = 5.00
estimated_cost = (total_records / 1000) * cost_per_1000
# 推定コスト: $85.00

# 無料枠活用戦略
free_quota_daily = 100
days_needed = total_records / free_quota_daily
# 無料処理期間: 170日（約6ヶ月）
```

## 🎛️ 詳細設定オプション

### バッチ処理パラメーター
```bash
python web_recognition_system.py \
  --csv-file "custom_database.csv" \      # 処理対象CSV
  --batch-size 100 \                      # 1回の処理件数
  --start-from 1000 \                     # 開始インデックス
  --rate-limit 2.5 \                      # クエリ間隔（秒）
  --max-concurrent 5                      # 最大並行処理数
```

### キャッシュ制御
```python
# システム内でキャッシュ期間変更
recognition_system = WebRecognitionSystem(cache_duration_hours=336)  # 2週間
```

## 📈 出力ファイル

### 1. 結果CSV
```
recognition_results_brave_20250831_143022.csv
```

| カラム | 説明 |
|---------|------|
| person_name | 人物名 |
| recognition_score | 知名度スコア（0-100） |
| search_results_count | 検索結果数 |
| relevance_score | 関連度スコア（0-1） |
| from_cache | キャッシュ使用フラグ |
| processed_at | 処理日時 |

### 2. 統計JSON
```json
{
  "provider": "brave",
  "total_records": 50,
  "processed": 48,
  "from_cache": 12,
  "new_queries": 36,
  "errors": 2,
  "total_cost": 0.18,
  "processing_time": 145.6
}
```

## 🎯 知名度スコア解釈

### スコア段階
- **0-20**: 一般的でない/地域限定的
- **21-40**: 業界内で認知
- **41-60**: 国内で知名度あり
- **61-80**: 高い知名度/メディア露出
- **81-100**: 非常に有名/国際的認知

### スコア計算ロジック
```python
# 基本スコア（検索結果数のログスケール）
base_score = min(math.log10(max(result_count, 1)) * 25, 80)

# 関連度ボーナス（検索結果の人物名との関連性）
relevance_bonus = relevance_score * 20

# 最終スコア
final_score = min(int(base_score + relevance_bonus), 100)
```

## 🔧 カスタマイズ方法

### 1. 新しい検索プロバイダー追加
```python
class CustomSearchProvider:
    async def search_person(self, person_name: str, **kwargs) -> Dict:
        # カスタム検索ロジック
        return {
            'person_name': person_name,
            'search_provider': 'custom',
            'recognition_score': calculated_score
        }
```

### 2. スコア計算アルゴリズム変更
```python
def custom_scoring_algorithm(search_results: Dict) -> int:
    # カスタムスコリングロジック
    weighted_score = (
        search_results['result_count'] * 0.6 +
        search_results['relevance_score'] * 100 * 0.4
    )
    return min(int(weighted_score / 10), 100)
```

## ⚠️ 注意事項・制限事項

### APIレート制限
- **Google Custom Search**: 100クエリ/日（無料）、その後$5/1000クエリ
- **Brave Search**: プロバイダー依存（APIキー要）
- **Web Scraping**: サイトごとのrobot.txt準拠、法的リスク考慮

### データ品質
- 同名異人の識別制限
- 国際的な知名度と地域的知名度の区別困難
- 時期による知名度変動への対応制限

### 技術制限
- 非同期処理によるメモリ使用量増加
- 大規模バッチ処理時のタイムアウトリスク
- キャッシュデータベースのディスク容量考慮

## 🔍 トラブルシューティング

### よくある問題

#### 1. APIキーエラー
```bash
# エラー: Google API Error: Invalid API key
# 解決: APIキーの再確認と環境変数設定
export GOOGLE_API_KEY="correct_api_key"
```

#### 2. レート制限エラー
```bash
# エラー: Too Many Requests (429)
# 解決: レート制限の緩和
python web_recognition_system.py --rate-limit 5.0 --max-concurrent 1
```

#### 3. メモリ不足
```bash
# 大規模バッチ処理時のメモリ不足
# 解決: バッチサイズの縮小
python web_recognition_system.py --batch-size 10 --max-concurrent 2
```

### ログ確認
```bash
# 詳細ログ有効化
export PYTHONPATH=.
python -u web_recognition_system.py --mode brave 2>&1 | tee processing.log
```

## 📚 実装例

### Ultra Thinkデータベース全体処理
```bash
#!/bin/bash
# 分割バッチ処理スクリプト

CSV_FILE="ultra_think_YOUTUBER_GROUPS_FIXED_20250828_201154.csv"
BATCH_SIZE=50
TOTAL_RECORDS=17000

for start in $(seq 0 $BATCH_SIZE $TOTAL_RECORDS); do
  echo "Processing batch: $start - $((start + BATCH_SIZE))"

  python web_recognition_system.py \
    --csv-file "$CSV_FILE" \
    --mode brave \
    --batch-size $BATCH_SIZE \
    --start-from $start \
    --rate-limit 2.0

  # バッチ間休憩
  sleep 60
done
```

### 結果統合スクリプト
```python
import pandas as pd
import glob

# 全結果ファイルを統合
result_files = glob.glob("recognition_results_*.csv")
combined_df = pd.concat([pd.read_csv(f) for f in result_files])

# 重複除去
combined_df = combined_df.drop_duplicates(subset=['person_name'])

# 統合結果保存
combined_df.to_csv("all_recognition_results.csv", index=False)
print(f"統合完了: {len(combined_df)} 件の結果")
```

## 🚀 今後の拡張予定

1. **リアルタイム知名度監視**: 定期的な知名度変動追跡
2. **多言語対応**: 英語・中国語などでの国際的知名度測定
3. **ソーシャルメディア統合**: Twitter/Instagram等のフォロワー数連携
4. **機械学習強化**: より精密なスコアリングアルゴリズム

---

## 📞 サポート

質問やバグ報告は、プロジェクトのGitHubリポジトリまたは開発チームまでご連絡ください。
