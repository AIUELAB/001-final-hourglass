# SonarQube セットアップガイド

## セキュリティ設定

### 環境変数の設定

SonarQubeトークンを安全に管理するために、環境変数を使用してください：

```bash
# 環境変数を設定
export SONAR_TOKEN="your_sonarqube_token_here"

# または .env ファイルに追加
echo "SONAR_TOKEN=your_sonarqube_token_here" >> .env
```

### トークンの生成方法

1. SonarQube Web UI ([http://localhost:9000](http://localhost:9000)) にアクセス
2. ユーザー設定 → My Account → Security
3. "Generate Tokens" をクリック
4. トークン名を入力して生成
5. 生成されたトークンをコピーして環境変数に設定

## 使用方法

```bash
# 環境変数を設定してからスキャンを実行
export SONAR_TOKEN="your_token"
sonar-scanner

# または直接指定
sonar-scanner -Dsonar.token="your_token"
```

## セキュリティ注意事項

- **トークンをコードにハードコードしないでください**
- **トークンをGitにコミットしないでください**
- **定期的にトークンを更新してください**
- **不要になったトークンは必ず無効化してください**

## トラブルシューティング

### 認証エラーが発生する場合

1. 環境変数が正しく設定されているか確認
2. トークンが有効か確認
3. SonarQubeサーバーが起動しているか確認

### 権限エラーが発生する場合

1. ユーザーアカウントの権限を確認
2. プロジェクトへのアクセス権限を確認
3. 必要に応じて管理者に連絡
