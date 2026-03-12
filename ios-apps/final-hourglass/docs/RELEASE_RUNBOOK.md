# iOS リリース手順書 (Release Runbook)

> **対象アプリ**: FinalHourglass (`com.AIUELAB.FinalHourglass`)
> **ワークフロー**: `.github/workflows/ios-release-v2.yml`
> **CLI**: `python -m cli.ios_release`

---

## 目次

1. [リリース前チェックリスト](#1-リリース前チェックリスト)
2. [リリース実行手順](#2-リリース実行手順)
3. [リリース後確認事項](#3-リリース後確認事項)
4. [トラブルシューティング](#4-トラブルシューティング)
5. [ロールバック手順](#5-ロールバック手順)
6. [バージョニングポリシー](#6-バージョニングポリシー)
7. [Secrets・環境変数一覧](#7-secrets環境変数一覧)

---

## 1. リリース前チェックリスト

リリース実行前に、以下の項目をすべて確認してください。

### コード品質

- [ ] テストが全パスしている
  ```bash
  cd ios-apps/final-hourglass && pytest tests/
  ```
- [ ] main ブランチに最新の変更がマージ済み
- [ ] SwiftLint の警告がないことを確認

### リリース準備

- [ ] バージョン番号を決定（[バージョニングポリシー](#6-バージョニングポリシー)を参照）
- [ ] What's New テキストを準備（App Store に表示されるリリースノート）
- [ ] スクリーンショットに更新が必要か確認
- [ ] Privacy Manifest (`PrivacyInfo.xcprivacy`) が最新か確認

### インフラ確認

- [ ] GitHub Secrets がすべて設定済み（[Secrets 一覧](#7-secrets環境変数一覧)を参照）
- [ ] Apple Developer 証明書が有効期限内
- [ ] Provisioning Profile が有効期限内
- [ ] App Store Connect API キーが有効

### 事前検証（推奨）

```bash
# dry-run で事前に問題がないか確認
gh workflow run ios-release-v2.yml --ref main -f version="X.Y.Z" -f dry_run=true
```

---

## 2. リリース実行手順

3つの方法でリリースを実行できます。**GitHub Actions 経由を推奨**します。

### A. GitHub Actions 経由（推奨）

最も安全で推奨される方法です。署名・アップロード・リリース作成まで自動化されています。

#### Step 1: dry-run で事前検証

```bash
gh workflow run ios-release-v2.yml --ref main -f version="1.0.12" -f dry_run=true
```

dry-run では以下がスキップされます:
- コード署名（証明書・プロファイルのインストール）
- App Store Connect へのアップロード
- Git タグの作成
- GitHub Release の作成

#### Step 2: 本番実行

```bash
gh workflow run ios-release-v2.yml --ref main -f version="1.0.12"
```

#### Step 3: 進捗確認

```bash
# 最新のワークフロー実行を表示
gh run list --workflow=ios-release-v2.yml --limit 1

# リアルタイムでログを追跡
gh run watch <run_id>

# 完了後、結果を確認
gh run view <run_id>
```

#### ワークフローの3段階

| ジョブ | ランナー | タイムアウト | 内容 |
|--------|----------|-------------|------|
| `validate` | ubuntu-latest | 5分 | バージョン形式検証、重複タグチェック、main ブランチ強制、Secrets 確認、Privacy Manifest チェック |
| `build-upload` | macos-15 | 45分 | 証明書・プロファイル設定、CLI によるビルド・アーカイブ・エクスポート・アップロード |
| `create-release` | ubuntu-latest | 10分 | Changelog 生成、Git タグ作成、GitHub Release 作成（IPA・dSYM 添付） |

### B. ローカル CLI 実行

ローカルの macOS 環境で直接 CLI を実行する方法です。
事前に[環境変数](#ローカル実行時の環境変数)の設定が必要です。

```bash
cd ios-apps/final-hourglass

# 環境変数を設定（.env.ios-release に記載するか、直接 export）
export APP_STORE_CONNECT_API_KEY_ID="YOUR_KEY_ID"
export APP_STORE_CONNECT_API_ISSUER_ID="YOUR_ISSUER_ID"
export APP_STORE_CONNECT_API_KEY_PATH="/path/to/AuthKey_XXXX.p8"
export APPLE_TEAM_ID="N4UHXSGNLU"
export APPLE_BUNDLE_ID="com.AIUELAB.FinalHourglass"

# 全ステップ実行
python -m cli.ios_release \
  --execute \
  --version 1.0.12 \
  --whats-new "バグ修正とパフォーマンス改善"

# 特定のステップのみ実行
python -m cli.ios_release \
  --execute \
  --version 1.0.12 \
  --step validate --step version --step archive
```

#### CLI オプション一覧

| オプション | 必須 | 説明 |
|-----------|------|------|
| `--version X.Y.Z` | 必須 | リリースバージョン |
| `--execute` | - | 本番モード（省略時は dry-run） |
| `--whats-new "テキスト"` | - | App Store のリリースノート |
| `--step STEP` | - | 実行するステップを指定（複数指定可） |
| `--build-number N` | - | ビルド番号を手動指定 |
| `--export-options-plist PATH` | - | ExportOptions.plist のパスを指定 |
| `--ci` | - | GitHub Actions 出力形式（`::set-output` 等） |

#### 利用可能なステップ

`--step` で以下を指定できます:

| ステップ | 内容 |
|---------|------|
| `validate` | 環境・設定の検証 |
| `version` | Info.plist のバージョン更新 |
| `archive` | Xcode アーカイブ（xcarchive 生成） |
| `export` | IPA エクスポート |
| `upload` | App Store Connect へアップロード |
| `metadata` | メタデータ更新 |
| `submit` | 審査提出 |
| `report` | 実行結果レポート出力 |

### C. タグプッシュ経由

Git タグをプッシュすることで自動的にワークフローがトリガーされます。

```bash
# タグを作成してプッシュ
git tag ios-v1.0.12
git push origin ios-v1.0.12
```

> **注意**: タグプッシュ経由の場合、`dry_run` オプションは使用できません。常に本番モードで実行されます。

---

## 3. リリース後確認事項

### 必須確認

- [ ] **TestFlight ビルド反映確認**
  - [App Store Connect](https://appstoreconnect.apple.com/) にログイン
  - 「TestFlight」タブでビルドが表示されていることを確認
  - ビルドのステータスが「処理中」→「テスト準備完了」に変わるまで待機（通常10〜30分）

- [ ] **GitHub Release 確認**
  ```bash
  gh release view ios-v1.0.12
  ```
  - IPA と dSYM が添付されていることを確認
  - Changelog が正しいことを確認

### 推奨確認

- [ ] **内部テスターへの通知**
  - TestFlight の自動通知が送信されていることを確認
  - 必要に応じてテスターグループを更新

- [ ] **dSYM アーティファクトのダウンロード**
  ```bash
  # GitHub Actions のアーティファクトからダウンロード
  gh run download <run_id> --name dSYMs-1.0.12
  ```
  - クラッシュレポートのシンボリケーション用に保管

- [ ] **ビルドの動作確認**
  - TestFlight で実機インストール・基本動作を確認

---

## 4. トラブルシューティング

### 署名エラー

**症状**: `Code Signing Error` / `No signing certificate found`

**対処法**:
1. Apple Developer ポータルで証明書の有効期限を確認
2. Provisioning Profile が証明書と紐付いているか確認
3. GitHub Secrets を再設定（Base64 エンコードの再生成）
   ```bash
   # 証明書を Base64 エンコード
   base64 -i Certificates.p12 | pbcopy
   ```
4. Keychain のロック解除に失敗している場合は `KEYCHAIN_PASSWORD` を再設定

### アップロード失敗

**症状**: `altool` がタイムアウト / エラーコードを返す

**対処法**:
- 再実行で解消することが多い（Apple サーバー側の一時的な問題）
- App Store Connect API キーの有効期限を確認
- ネットワーク接続の安定性を確認
- `xcrun altool` は Xcode 14 以降で非推奨警告が出るが、動作には影響なし

### TN3110 Generic Xcode Archive

**症状**: `expected one {} but found app-store-connect`

**対処法**:
- CLI が自動で ApplicationProperties を xcarchive の Info.plist に注入するため、通常は発生しない
- 発生した場合は、xcarchive の `Info.plist` に `ApplicationProperties` キーが存在するか確認
- `SKIP_INSTALL=NO` をコマンドラインで全体指定していないか確認（アプリターゲットのみに設定すべき）

### ExportOptions.plist パースエラー

**症状**: `The data couldn't be read because it isn't in the correct format`

**対処法**:
1. `<?xml` 宣言の前に空白・BOM がないか確認
2. plist の構文を検証
   ```bash
   plutil -lint ExportOptions.plist
   ```
3. GitHub Actions では PlistBuddy でプログラム的に生成するため、通常は発生しない

### ビルド失敗

**症状**: `xcodebuild` がエラーで終了

**対処法**:
- Xcode バージョンの確認（macOS 15 ランナーの Xcode バージョン）
- SPM キャッシュのクリア
  ```bash
  rm -rf ~/Library/Developer/Xcode/DerivedData
  swift package purge-cache
  ```
- `xcodebuild -resolvePackageDependencies` で依存関係を事前解決

### 重複タグエラー

**症状**: `Tag ios-vX.Y.Z already exists`

**対処法**:
- 既に同じバージョンでリリースされている可能性あり
- バージョン番号を変更するか、既存タグを削除してから再実行
  ```bash
  git tag -d ios-v1.0.12
  git push origin :refs/tags/ios-v1.0.12
  ```

---

## 5. ロールバック手順

リリース後に問題が発覚した場合の対処手順です。

### TestFlight ビルドの無効化

1. [App Store Connect](https://appstoreconnect.apple.com/) にログイン
2. 「TestFlight」→ 対象ビルドを選択
3. 「テスターに対するビルドの提供を停止」を実行

### App Store 提出の取り消し

1. App Store Connect で「App Store」タブを開く
2. 審査待ちの場合は「提出を取り消し」を選択
3. 既に審査通過済みの場合は「バージョンをリリースから削除」

### GitHub Release の削除

```bash
# Release を削除
gh release delete ios-v1.0.12 --yes

# Git タグを削除（ローカル + リモート）
git tag -d ios-v1.0.12
git push origin :refs/tags/ios-v1.0.12
```

### 修正版のリリース

1. 問題を修正して main にマージ
2. パッチバージョンを上げて再リリース（例: `1.0.12` → `1.0.13`）

---

## 6. バージョニングポリシー

### セマンティックバージョニング (X.Y.Z)

| 要素 | 意味 | 変更タイミング |
|------|------|---------------|
| **X** (メジャー) | 破壊的変更 | UI の大幅刷新、機能の互換性がなくなる変更 |
| **Y** (マイナー) | 新機能追加 | 後方互換性のある機能追加 |
| **Z** (パッチ) | バグ修正 | バグ修正、パフォーマンス改善 |

### ビルド番号の計算

ビルド番号は以下の式で自動計算されます:

```
ビルド番号 = PATCH + GitHub Actions run_number
```

例: バージョン `1.0.12` で `run_number` が `50` の場合、ビルド番号は `62`

### タグ命名規則

```
ios-v{MAJOR}.{MINOR}.{PATCH}
```

例: `ios-v1.0.12`, `ios-v2.1.0`

---

## 7. Secrets・環境変数一覧

### GitHub Secrets（必須）

| Secret 名 | 説明 |
|-----------|------|
| `DISTRIBUTION_CERTIFICATE_BASE64` | Apple Distribution 証明書（.p12）の Base64 |
| `DISTRIBUTION_CERTIFICATE_PASSWORD` | 証明書のパスワード |
| `KEYCHAIN_PASSWORD` | CI 用キーチェーンのパスワード（任意の文字列） |
| `PROVISIONING_PROFILE_BASE64` | App Store 配布用プロビジョニングプロファイルの Base64 |
| `APP_STORE_CONNECT_API_KEY_BASE64` | ASC API キー（.p8）の Base64 |
| `APP_STORE_CONNECT_API_KEY_ID` | ASC API キー ID |
| `APP_STORE_CONNECT_API_ISSUER_ID` | ASC API 発行者 ID |
| `IOS_REPO_TOKEN` | iOS サブモジュールアクセス用 GitHub トークン |

### ローカル実行時の環境変数

| 環境変数 | 値 |
|---------|-----|
| `APP_STORE_CONNECT_API_KEY_ID` | ASC API キー ID |
| `APP_STORE_CONNECT_API_ISSUER_ID` | ASC API 発行者 ID |
| `APP_STORE_CONNECT_API_KEY_PATH` | AuthKey_XXXX.p8 のファイルパス |
| `APPLE_TEAM_ID` | `N4UHXSGNLU` |
| `APPLE_BUNDLE_ID` | `com.AIUELAB.FinalHourglass` |

> `.env.ios-release` ファイルに記載することも可能です（GitHub Actions では自動生成されます）。

---

## 参考リンク

- [CLI リリースガイド](./CLI_RELEASE_GUIDE.md)
- [ワークフロー定義](../../../.github/workflows/ios-release-v2.yml)
- [Apple - App Store Connect API](https://developer.apple.com/documentation/appstoreconnectapi)
- [Apple - TN3110: Resolving Generic Xcode Archive issue](https://developer.apple.com/documentation/technotes/tn3110)
