# 本番環境展開チェックリスト

## 展開前確認事項

### 1. コードベース
- [ ] すべてのテストがパス
- [ ] 型チェック完了
- [ ] リントチェック完了
- [ ] セキュリティスキャン完了

### 2. 設定ファイル
- [ ] 環境変数の確認
- [ ] データベースパスの確認
- [ ] ログ設定の確認
- [ ] エラーハンドリング設定

### 3. 依存関係
- [ ] requirements.txt更新
- [ ] バージョン固定
- [ ] セキュリティ脆弱性チェック

### 4. データベース
- [ ] complete_person_facts.json（135人）の整合性
- [ ] バックアップ作成
- [ ] インデックス最適化

### 5. パフォーマンス
- [ ] 負荷テスト実施
- [ ] メモリ使用量測定
- [ ] レスポンスタイム測定
- [ ] 同時接続数テスト

## 展開手順

### Step 1: バックアップ
```bash
# 現在の本番環境をバックアップ
mkdir -p backups/$(date +%Y%m%d)
cp -r episode_quality_system/ backups/$(date +%Y%m%d)/
```

### Step 2: 依存関係の更新
```bash
# 仮想環境の作成
python3 -m venv venv_production
source venv_production/bin/activate

# 依存関係のインストール
pip install -r requirements.txt
```

### Step 3: 設定の更新
```python
# production_config.py
VALIDATION_MODE = "optimized"  # 最適化モード使用
MIN_QUALITY_SCORE = 70.0       # 最小品質スコア
MAX_ATTEMPTS = 5                # 最大試行回数
USE_CACHE = True                # キャッシュ有効化
```

### Step 4: データベースの配置
```bash
# データベースファイルの配置
cp complete_person_facts.json /path/to/production/data/
chmod 644 /path/to/production/data/complete_person_facts.json
```

### Step 5: システムファイルの配置
```bash
# コアファイルの配置
cp unified_episode_factory_v2.py /path/to/production/
cp optimized_validation_system.py /path/to/production/
cp expanded_episode_templates.py /path/to/production/
cp mandatory_pipeline.py /path/to/production/
```

## 監視設定

### ログ監視
```python
# logging_config.py
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('episode_generation.log'),
        logging.StreamHandler()
    ]
)
```

### メトリクス収集
- 生成成功率
- 平均レスポンスタイム
- エラー率
- リソース使用率

## ロールバック計画

### 自動ロールバック条件
- エラー率 > 5%
- レスポンスタイム > 1秒
- 成功率 < 90%

### ロールバック手順
```bash
# 前バージョンに戻す
cp -r backups/$(date +%Y%m%d)/* /path/to/production/
# サービス再起動
systemctl restart episode-service
```

## 展開後確認

### ヘルスチェック
```python
# health_check.py
def check_system_health():
    checks = {
        "database": check_database_connection(),
        "validation": check_validation_system(),
        "generation": check_episode_generation(),
        "performance": check_performance_metrics()
    }
    return all(checks.values())
```

### スモークテスト
```python
# smoke_test.py
test_cases = [
    ("大谷翔平", 29, "sports"),
    ("新垣結衣", 28, "entertainment"),
    ("山中伸弥", 50, "science")
]

for person, age, category in test_cases:
    assert generate_episode(person, age, category).success
```

## 連絡先

### 問題発生時
- 主担当: システム管理者
- 副担当: 開発チーム
- エスカレーション: プロジェクトマネージャー

## 承認

- [ ] 開発チーム承認
- [ ] QAチーム承認
- [ ] セキュリティチーム承認
- [ ] プロジェクトマネージャー承認

---

最終更新: 2025年1月
次回レビュー: 2025年2月