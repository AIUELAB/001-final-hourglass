# iOS Release CLI ガイド

## 概要

iOS Release CLI は FinalHourglass アプリのリリースプロセスを自動化するコマンドラインツールです。

以下の8ステップのパイプラインを順次実行します:

1. **validate** - 環境・設定の検証
2. **version** - バージョン番号の更新
3. **archive** - Xcode アーカイブの作成
4. **export** - IPA ファイルのエクスポート
5. **upload** - TestFlight へのアップロード
6. **metadata** - App Store Connect メタデータ更新
7. **submit** - App Review への提出
8. **report** - リリースレポートの生成

### 動作モード

| モード | フラグ | 動作 |
|--------|--------|------|
| dry-run | (デフォルト) | 検証のみ。外部への副作用なし |
| execute | `--execute` | 実際のビルド・アップロード・提出を実行 |

---

## 前提条件

- **macOS** (Xcode 15 以上がインストール済み)
- **Python 3.11+**
- **App Store Connect API キー** (.p8 ファイル)
- **Apple Developer Program** のメンバーシップ

### 依存パッケージのインストール

```bash
cd ios-apps/final-hourglass
pip install -r requirements-cli.txt
```

依存パッケージ: click, rich, python-dotenv, PyJWT, cryptography, requests

---

## 設定

### 環境変数ファイルの準備

`.env.ios-release.example` をコピーして `.env.ios-release` を作成します。

```bash
cp .env.ios-release.example .env.ios-release
```

### 必須環境変数

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `APP_STORE_CONNECT_API_KEY_ID` | ASC API キー ID | `XXXXXXXXXX` |
| `APP_STORE_CONNECT_API_ISSUER_ID` | ASC API 発行者 ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `APP_STORE_CONNECT_API_KEY_PATH` | .p8 ファイルのパス | `~/.keys/AuthKey_XXXXX.p8` |
| `APPLE_TEAM_ID` | Apple Team ID | `N4UHXSGNLU` |
| `APPLE_BUNDLE_ID` | バンドル識別子 | `com.AIUELAB.FinalHourglass` |

---

## 使い方

### ローカル dry-run（検証のみ）

```bash
cd ios-apps/final-hourglass
python -m cli.ios_release --version 1.0.11
```

dry-run モードでは全ステップが検証のみで実行されます。ビルドは `CODE_SIGNING_ALLOWED=NO` で行われ、署名やアップロードは発生しません。

### ローカル実行（実際のリリース）

```bash
python -m cli.ios_release --execute --version 1.0.11 --whats-new "バグ修正とパフォーマンス改善"
```

`--execute` フラグにより、実際のアーカイブ・IPA 出力・TestFlight アップロード・審査提出が行われます。

### 特定ステップのみ実行

```bash
python -m cli.ios_release --step validate --step version --version 1.0.11
```

`--step` を複数回指定して、任意のステップのみ実行できます。

### CI モード（GitHub Actions 向け）

```bash
python -m cli.ios_release --ci --execute --version 1.0.11 \
  --build-number 42 \
  --export-options-plist /path/to/ExportOptions.plist
```

`--ci` フラグを付けると、GitHub Actions の `::set-output` 形式で結果を出力します。

### 主要オプション一覧

| オプション | 説明 |
|-----------|------|
| `--version` | リリースバージョン (例: `1.0.11`) |
| `--execute` | 実行モード (省略時は dry-run) |
| `--whats-new` | What's New テキスト |
| `--step` | 実行するステップ (複数指定可) |
| `--ci` | CI モード (GitHub Actions 出力形式) |
| `--build-number` | ビルド番号を明示指定 |
| `--export-options-plist` | ExportOptions.plist のパスを指定 |

---

## ステップ詳細

### 1. validate

環境とプロジェクト設定を検証します。

- バージョン文字列のフォーマットチェック (`X.Y.Z`)
- `FinalHourglass.xcworkspace` の存在確認
- コード署名 ID の検出 (`security find-identity`)
- 必須環境変数の存在チェック

### 2. version

pbxproj ファイル内のバージョン番号を更新します。

- `MARKETING_VERSION` を指定バージョンに設定
- `CURRENT_PROJECT_VERSION` をインクリメント（または `--build-number` で指定）

### 3. archive

`xcodebuild archive` で xcarchive を作成します。

- dry-run 時: `CODE_SIGNING_ALLOWED=NO` で署名なしビルド
- execute 時: 署名付きアーカイブを生成

### 4. export

xcarchive から IPA ファイルをエクスポートします。

- TN3110 対策として `ApplicationProperties` を xcarchive の Info.plist に自動注入
- distribution method: `app-store-connect`（Xcode 16.4+ 対応）
- `--export-options-plist` で外部 plist 指定も可能

### 5. upload

IPA ファイルを TestFlight にアップロードします。

- `xcrun altool --upload-app` を使用
- ASC API キーで認証

### 6. metadata

App Store Connect API 経由でメタデータを更新します。

- What's New テキストの設定（`--whats-new` で指定）
- JWT トークンによる認証

### 7. submit

App Store Connect API 経由で App Review に提出します。

- バージョンのレビュー提出リクエスト送信
- 提出状態の確認

### 8. report

リリースレポート（Markdown 形式）を生成します。

- 実行結果のサマリー
- 各ステップの成否一覧
- ビルド情報（バージョン、ビルド番号、パス）

---

## CI/CD 統合（GitHub Actions）

### ワークフローファイル

`.github/workflows/ios-release-v2.yml`

### トリガー

`workflow_dispatch` で手動実行し、バージョン番号を入力として受け取ります。

### ワークフロー概要

```
workflow_dispatch (version入力)
  └─ build-and-release ジョブ (macOS runner)
       ├─ Checkout
       ├─ Python セットアップ
       ├─ 依存インストール (requirements-cli.txt)
       ├─ 証明書・プロファイル復元
       └─ CLI 実行 (--ci --execute --version $VERSION)
```

### 主要出力

| 出力名 | 説明 |
|--------|------|
| `new_version` | リリースバージョン |
| `new_build` | ビルド番号 |
| `archive_path` | xcarchive のパス |
| `ipa_path` | IPA ファイルのパス |

build + archive + upload を1ジョブに統合しており、IPA の artifact 往復が不要なため 3-5 分の短縮を実現しています。

---

## トラブルシューティング

### TN3110 "Generic Xcode Archive"

**症状**: `expected one {} but found app-store-connect`

**原因**: xcarchive の Info.plist に `ApplicationProperties` が欠落している。

**対応**: CLI は export ステップで自動的に `ApplicationProperties` を注入します。手動対応は不要です。

### xcrun altool の非推奨警告

Xcode 14 以降で非推奨になっていますが、現時点では動作します。将来的には ASC API 直接アップロードへの移行を検討してください。

### 署名 ID が見つからない

```bash
security find-identity -v -p codesigning
```

有効な署名証明書がキーチェーンにインストールされているか確認してください。

### ExportOptions.plist のパースエラー

```bash
plutil -lint ExportOptions.plist
```

`<?xml` 宣言の前に空白がないことを確認してください（xcodebuild はパースに失敗します）。

### プロビジョニングプロファイルの問題

プロファイルは NAME よりも UUID で指定する方が確実です。`steps.profile.outputs.uuid` を使用してください。

---

## アーキテクチャ

```
cli/
├── ios_release.py          # メイン CLI エントリポイント (Click)
├── config.py               # 設定ローダー (.env.ios-release)
├── steps/                  # パイプラインステップ
│   ├── validate.py         #   環境検証
│   ├── version.py          #   バージョン更新
│   ├── archive.py          #   xcodebuild archive
│   ├── export_ipa.py       #   IPA エクスポート
│   ├── upload.py           #   TestFlight アップロード
│   ├── metadata.py         #   ASC メタデータ更新
│   ├── submit.py           #   App Review 提出
│   └── report.py           #   リリースレポート生成
└── utils/                  # 共有ユーティリティ
    ├── xcodebuild.py       #   xcodebuild コマンドラッパー
    ├── plistbuddy.py       #   PlistBuddy ヘルパー
    ├── asc_api.py          #   App Store Connect API クライアント
    └── ci.py               #   GitHub Actions 出力ヘルパー
```

各ステップは独立したモジュールとして実装されており、`ios_release.py` がオーケストレーターとして順次呼び出します。dry-run / execute の分岐は各ステップ内で処理されます。
