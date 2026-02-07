# iOS署名証明書設定ガイド

本ドキュメントでは、GitHub ActionsでiOSアプリをApp Store/TestFlightに配信するための署名証明書設定手順を説明します。

---

## 📋 概要

GitHub ActionsのCI/CDパイプラインでiOSアプリを署名・配信するには、以下の8つのSecretsを設定する必要があります。

| Secret名 | 用途 |
|----------|------|
| `DISTRIBUTION_CERTIFICATE_BASE64` | 配布用証明書（.p12）のBase64エンコード |
| `DISTRIBUTION_CERTIFICATE_PASSWORD` | .p12ファイルのパスワード |
| `KEYCHAIN_PASSWORD` | CI用一時キーチェーンのパスワード |
| `PROVISIONING_PROFILE_BASE64` | Provisioning ProfileのBase64エンコード |
| `APP_STORE_CONNECT_API_KEY_BASE64` | App Store Connect API Key（.p8）のBase64エンコード |
| `APP_STORE_CONNECT_API_KEY_ID` | API KeyのKey ID |
| `APP_STORE_CONNECT_API_ISSUER_ID` | API KeyのIssuer ID |
| `IOS_REPO_TOKEN` | iOSサブモジュールアクセス用のPAT |

---

## 🔐 Step 1: Distribution Certificate（配布用証明書）の作成

### 1.1 Apple Developer Consoleで証明書を作成

1. [Apple Developer Console](https://developer.apple.com/account) にログイン
2. **Certificates, Identifiers & Profiles** → **Certificates** に移動
3. **+** ボタンをクリック
4. **Apple Distribution** を選択して **Continue**
5. **Certificate Signing Request (CSR)** をアップロード

### 1.2 CSRの作成方法（Mac）

```bash
# キーチェーンアクセスでCSRを作成
# 1. キーチェーンアクセスを開く
# 2. メニュー: キーチェーンアクセス → 証明書アシスタント → 認証局に証明書を要求
# 3. メールアドレスを入力、「ディスクに保存」を選択
```

### 1.3 証明書をダウンロード・エクスポート

1. 作成した証明書（.cer）をダウンロード
2. ダブルクリックしてキーチェーンにインストール
3. キーチェーンアクセスで証明書を右クリック → **「〜を書き出す...」**
4. **.p12形式**で保存
5. パスワードを設定（これが`DISTRIBUTION_CERTIFICATE_PASSWORD`になる）

### 1.4 Base64エンコード

```bash
# .p12ファイルをBase64エンコードしてクリップボードにコピー
base64 -i Distribution.p12 | pbcopy

# 確認（先頭部分のみ表示）
base64 -i Distribution.p12 | head -c 100
```

---

## 📱 Step 2: Provisioning Profileの作成

### 2.1 App IDの確認

1. [Apple Developer Console](https://developer.apple.com/account) → **Identifiers**
2. Bundle ID `com.aiuelab.FinalHourglass` が登録されていることを確認
3. なければ **+** で新規作成

### 2.2 Provisioning Profileの作成

1. **Profiles** → **+** ボタンをクリック
2. **App Store Connect** を選択して **Continue**
3. App ID: `com.aiuelab.FinalHourglass` を選択
4. Certificate: Step 1で作成した配布用証明書を選択
5. Profile Name: `FinalHourglass AppStore` と入力
6. **Generate** → ダウンロード

### 2.3 Base64エンコード

```bash
# Provisioning ProfileをBase64エンコード
base64 -i FinalHourglass_AppStore.mobileprovision | pbcopy

# 確認
base64 -i FinalHourglass_AppStore.mobileprovision | head -c 100
```

---

## 🔑 Step 3: App Store Connect API Keyの作成

### 3.1 API Keyの作成

1. [App Store Connect](https://appstoreconnect.apple.com) にログイン
2. **ユーザとアクセス** → **インテグレーション** → **キー** タブ
3. **App Store Connect API** セクションで **+** をクリック
4. 名前: `GitHub Actions` など任意
5. アクセス: **App Manager** を選択
6. **生成** をクリック
7. **APIキーをダウンロード**（.p8ファイル）

> ⚠️ **重要**: .p8ファイルは一度しかダウンロードできません！安全な場所に保管してください。

### 3.2 Key IDとIssuer IDの確認

作成後の画面で以下を確認・メモ:
- **Key ID**: `XXXXXXXXXX`（10文字）
- **Issuer ID**: `XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`（UUID形式）

### 3.3 Base64エンコード

```bash
# API Key (.p8) をBase64エンコード
base64 -i AuthKey_XXXXXXXXXX.p8 | pbcopy

# 確認
base64 -i AuthKey_XXXXXXXXXX.p8 | head -c 100
```

---

## 🔒 Step 4: GitHub Secretsの設定

### 4.1 Secrets設定ページへ移動

1. GitHubリポジトリを開く
2. **Settings** → **Secrets and variables** → **Actions**
3. **New repository secret** をクリック

### 4.2 各Secretの設定

| Secret名 | 値の取得元 |
|----------|-----------|
| `DISTRIBUTION_CERTIFICATE_BASE64` | Step 1.4で取得したBase64文字列 |
| `DISTRIBUTION_CERTIFICATE_PASSWORD` | Step 1.3で設定した.p12のパスワード |
| `KEYCHAIN_PASSWORD` | 任意の安全なパスワード（例: `CI-keychain-2024!`） |
| `PROVISIONING_PROFILE_BASE64` | Step 2.3で取得したBase64文字列 |
| `APP_STORE_CONNECT_API_KEY_BASE64` | Step 3.3で取得したBase64文字列 |
| `APP_STORE_CONNECT_API_KEY_ID` | Step 3.2でメモしたKey ID |
| `APP_STORE_CONNECT_API_ISSUER_ID` | Step 3.2でメモしたIssuer ID |
| `IOS_REPO_TOKEN` | Step 5で作成するPAT |

---

## 🔗 Step 5: IOS_REPO_TOKEN（Personal Access Token）の作成

iOSサブモジュールにアクセスするためのPATを作成します。

### 5.1 PATの作成

1. GitHub右上のアイコン → **Settings** → **Developer settings**
2. **Personal access tokens** → **Fine-grained tokens** → **Generate new token**
3. 設定:
   - Token name: `ios-repo-access`
   - Expiration: 90日など適切な期間
   - Repository access: **Only select repositories** → iOSリポジトリを選択
   - Permissions: **Contents** → **Read-only**
4. **Generate token** → トークンをコピー

### 5.2 Secretに追加

- Secret名: `IOS_REPO_TOKEN`
- 値: 生成したPAT

---

## ✅ Step 6: 検証

### 6.1 設定確認

GitHub Secretsページで8つ全てが設定されていることを確認:

```
✅ DISTRIBUTION_CERTIFICATE_BASE64
✅ DISTRIBUTION_CERTIFICATE_PASSWORD
✅ KEYCHAIN_PASSWORD
✅ PROVISIONING_PROFILE_BASE64
✅ APP_STORE_CONNECT_API_KEY_BASE64
✅ APP_STORE_CONNECT_API_KEY_ID
✅ APP_STORE_CONNECT_API_ISSUER_ID
✅ IOS_REPO_TOKEN
```

### 6.2 テストリリース

```bash
# テスト用タグを作成
git tag ios-v1.0.2
git push origin ios-v1.0.2
```

GitHub Actionsで以下を確認:
1. ✅ Validate Release ジョブが成功
2. ✅ Build & Archive ジョブが署名付きで成功
3. ✅ Export IPA が成功（dry-runではなく実際のIPA）
4. ✅ Upload to TestFlight が成功
5. ✅ Create GitHub Release が成功

### 6.3 TestFlightで確認

App Store Connect → TestFlight でビルドが表示されることを確認。

---

## 🔧 トラブルシューティング

### エラー: "No signing certificate found"

- 証明書が期限切れではないか確認
- Base64エンコードが正しいか確認（改行が含まれていないか）

### エラー: "Provisioning profile doesn't match"

- Provisioning ProfileのBundle IDが`com.aiuelab.FinalHourglass`か確認
- 証明書とProvisioning Profileの組み合わせが正しいか確認

### エラー: "Unable to authenticate with App Store Connect"

- API Key IDとIssuer IDが正しいか確認
- API Keyの権限が**App Manager**以上か確認
- .p8ファイルが正しくBase64エンコードされているか確認

### エラー: "Submodule checkout failed"

- `IOS_REPO_TOKEN`が正しく設定されているか確認
- PATの権限にContents読み取りが含まれているか確認
- PATが期限切れではないか確認

---

## 📚 関連ドキュメント

- [App Store メタデータ](./appstore-metadata.md)
- [スクリーンショット撮影ガイド](./IOS_SCREENSHOTS.md)
- [App Store提出チェックリスト](./APPSTORE_SUBMISSION_CHECKLIST.md)

---

## 📝 補足: ExportOptions.plist

現在の`ios-apps/final-hourglass/ExportOptions.plist`の設定:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<plist version="1.0">
<dict>
    <key>method</key>
    <string>app-store</string>
    <key>teamID</key>
    <string>V24V6U5Q5R</string>
    <key>uploadBitcode</key>
    <false/>
    <key>uploadSymbols</key>
    <true/>
    <key>signingStyle</key>
    <string>manual</string>
    <key>provisioningProfiles</key>
    <dict>
        <key>com.aiuelab.FinalHourglass</key>
        <string>FinalHourglass AppStore</string>
    </dict>
</dict>
</plist>
```

Provisioning Profile名は`FinalHourglass AppStore`と一致させてください。
