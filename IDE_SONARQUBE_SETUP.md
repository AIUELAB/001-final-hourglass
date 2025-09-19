# IDE SonarQube接続設定ガイド

## 🔧 問題と解決策

### 問題

IDEが「Connection 'http-localhost-9000' is not working」エラーを表示

### 原因

- IDEの接続URLが`localhost`を使用している
- SonarQubeはDockerコンテナで実行中
- ホスト名の解決に問題がある可能性

## ✅ 解決方法

### 1. VS Code / Cursor の設定

`.vscode/settings.json`に以下を設定済み:

```json
{
  "sonarlint.connectedMode.connections.sonarqube": [
    {
      "serverUrl": "http://127.0.0.1:9000",  // localhostではなく127.0.0.1を使用
      "token": "YOUR_SONARQUBE_TOKEN_HERE"
    }
  ],
  "sonarlint.connectedMode.project": {
    "projectKey": "YOUR_PROJECT_KEY_HERE"
  }
}
```

### 2. IntelliJ IDEA / JetBrains IDEの設定

1. **Settings/Preferences** → **Tools** → **SonarLint**
2. **Connection** タブで新しい接続を追加:
   - **Connection name**: SonarQube Local
   - **Server URL**: `http://127.0.0.1:9000` (localhostではなく)
   - **Authentication**: Token
   - **Token**: `YOUR_SONARQUBE_TOKEN_HERE`
3. **Test Connection** をクリック

### 3. 代替URL設定

以下のURLも試してください:

- `http://127.0.0.1:9000` ✅ 推奨
- `http://host.docker.internal:9000` (Docker Desktop使用時)
- `http://0.0.0.0:9000`

## 🔍 確認済み情報

### SonarQube サーバー状態

- **実行環境**: Docker コンテナ
- **コンテナ名**: sonarqube
- **イメージ**: sonarqube:latest
- **ポート**: 0.0.0.0:9000 -> 9000/tcp
- **状態**: UP (稼働中)
- **バージョン**: 25.8.0.112029

### トークン情報

- **名前**: Sonar-Qube
- **タイプ**: GLOBAL_ANALYSIS_TOKEN
- **有効期限**: 2026-08-25
- **最終接続**: 正常

### プロジェクト

- **プロジェクトキー**: `YOUR_PROJECT_KEY_HERE`
- **プロジェクト名**: sonar-project.properties

## 📋 トラブルシューティング

### IDE再起動

設定変更後は必ずIDEを再起動してください。

### ファイアウォール確認

```bash
# ポート9000が開いているか確認
netstat -an | grep 9000
```

### 接続テスト

```bash
# ブラウザで確認
open http://127.0.0.1:9000

# curlで確認
curl http://127.0.0.1:9000/api/system/status
```

### Docker確認

```bash
# コンテナ状態確認
docker ps | grep sonarqube

# ログ確認
docker logs sonarqube --tail 50
```

## 🚀 次のステップ

1. IDEを再起動
2. SonarLintプラグインの設定で`http://127.0.0.1:9000`を使用
3. トークンを設定
4. Test Connectionで接続確認
5. プロジェクトをバインド

## 📝 注意事項

- `localhost`ではなく`127.0.0.1`を使用することが重要
- Dockerコンテナとの通信では、ホスト名解決の問題を避けるためIPアドレスを推奨
- **セキュリティ**: トークンは環境変数として管理することを強く推奨
- **重要**: 実際のトークンをコードにハードコードしないでください

## 🔒 セキュリティ設定

### 環境変数での管理（推奨）

```bash
# .envファイルを作成
export SONARQUBE_TOKEN="your_actual_token_here"
export SONARQUBE_PROJECT_KEY="your_project_key_here"

# または、.env.localファイル（gitignoreに追加）
echo "SONARQUBE_TOKEN=your_actual_token_here" > .env.local
echo "SONARQUBE_PROJECT_KEY=your_project_key_here" >> .env.local
```

### 設定ファイルでの使用

```json
{
  "sonarlint.connectedMode.connections.sonarqube": [
    {
      "serverUrl": "http://127.0.0.1:9000",
      "token": "${env:SONARQUBE_TOKEN}"
    }
  ],
  "sonarlint.connectedMode.project": {
    "projectKey": "${env:SONARQUBE_PROJECT_KEY}"
  }
}
```
