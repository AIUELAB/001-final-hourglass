# Fastlane スクリーンショット生成 エスコートガイド

このドキュメントでは、**SnapshotHelper / SnapshotUITests の Xcode ターゲット追加** と **`bundle exec fastlane screenshots` による自動スクリーンショット生成** の手順を、初心者でも分かりやすく詳しく説明します。

---

## 📌 やることの全体像

| ステップ | 内容 |
|----------|------|
| **1** | Xcode で `SnapshotHelper.swift` と `SnapshotUITests.swift` を FinalHourglassUITests ターゲットに追加 |
| **2** | `bundle exec fastlane screenshots` でスクリーンショットを自動生成 |

---

## ⚡ すでに実施済み（自動対応）

**SnapshotHelper.swift** と **SnapshotUITests.swift** は、**project.pbxproj に自動追加済み**です。  
Xcode でプロジェクトを開けば、これらのファイルは FinalHourglassUITests ターゲットに含まれています。

> 手動で追加する必要がある場合は、以下の「ステップ1」を参照してください。

---

## ステップ1: Xcode でファイルをターゲットに追加（手動が必要な場合）

### 1.1 前提条件

- Xcode がインストール済み
- プロジェクトパス: `ios-apps/final-hourglass/`
- 追加するファイル:
  - `FinalHourglassUITests/SnapshotHelper.swift`
  - `FinalHourglassUITests/SnapshotUITests.swift`

**※ 自動追加済み**: 上記「すでに実施済み」のとおり、project.pbxproj への追加は完了しています。手動追加が必要なのは、自動追加が何らかの理由で反映されていない場合のみです。

---

### 1.2 Xcode でプロジェクトを開く

```bash
cd /Users/admin/Documents/AIUELAB/001-final-hourglass/ios-apps/final-hourglass
open FinalHourglass.xcworkspace
```

> ⚠️ **注意**: `.xcworkspace` を開いてください。`.xcodeproj` ではなく `.xcworkspace` です。

---

### 1.3 ナビゲーターでファイルを確認

1. **左側のナビゲーター（プロジェクトツリー）** を開く
2. **FinalHourglass** プロジェクトをクリック
3. **FinalHourglassUITests** フォルダ（黄色のフォルダアイコン）を展開
4. 以下のファイルがあるか確認:
   - `SnapshotHelper.swift`
   - `SnapshotUITests.swift`

**ファイルが見つからない場合**:
- フォルダ内に物理的には存在するが、Xcode に表示されていない可能性があります
- その場合は **1.4** の「ファイルを追加」手順で追加します

---

### 1.4 ファイルをターゲットに追加する（2通りの方法）

#### 方法A: 既にナビゲーターに表示されている場合

1. **SnapshotHelper.swift** をクリックして選択
2. **右側のインスペクター** を開く（表示されていない場合は `Cmd + Option + 0`）
3. **File Inspector**（左から1番目のタブ）を選択
4. **Target Membership** セクションを探す
5. **FinalHourglassUITests** にチェックを入れる ✅

同じ手順を **SnapshotUITests.swift** にも行います。

---

#### 方法B: ファイルがナビゲーターに表示されていない場合

1. **FinalHourglassUITests** フォルダを右クリック
2. **「Add Files to "FinalHourglass"...」** を選択
3. ダイアログで `FinalHourglassUITests` フォルダに移動
4. **SnapshotHelper.swift** と **SnapshotUITests.swift** を **Shift キーを押しながら** 両方選択
5. 以下のオプションを確認:
   - ☑️ **Copy items if needed** → オフ（既にフォルダ内にあるため）
   - ☑️ **Add to targets** → **FinalHourglassUITests** にチェック
6. **Add** をクリック

---

### 1.5 追加の確認

1. **SnapshotHelper.swift** をクリック
2. 右側の **Target Membership** で **FinalHourglassUITests** にチェックが入っていることを確認
3. **SnapshotUITests.swift** も同様に確認

---

### 1.6 ビルドテスト（任意だが推奨）

1. 上部のスキームで **FinalHourglassUITests** を選択
2. デバイスで **Any iOS Simulator** または **iPhone 15 Pro Max** を選択
3. **Cmd + B** でビルド
4. エラーが出なければ OK

---

## ステップ2: Fastlane でスクリーンショットを生成

### 2.1 作業ディレクトリに移動

```bash
cd /Users/admin/Documents/AIUELAB/001-final-hourglass/ios-apps/final-hourglass
```

---

### 2.2 Bundler で依存関係をインストール

Fastlane は Gemfile で管理されているため、まず依存関係をインストールします。

```bash
bundle install
```

初回または Gemfile 更新後は必ず実行してください。

---

### 2.3 スクリーンショット生成を実行

```bash
  bundle exec fastlane screenshots
```

---

### 2.4 スキームの確認（重要）

Fastlane の `capture_screenshots` は **scheme: "FinalHourglassUITests"** を指定しています。  
ワークスペースにこのスキームが無い場合は、以下で作成してください。

1. Xcode で `FinalHourglass.xcworkspace` を開く
2. メニュー **Product** → **Scheme** → **Manage Schemes...**
3. **+** をクリック
4. **Target** で **FinalHourglassUITests** を選択
5. **Scheme name** を `FinalHourglassUITests` に設定
6. **Shared** にチェックを入れる（CI で使用する場合）
7. **Close** をクリック

### 2.5 実行中の流れ

1. **シミュレーターが起動**（iPhone 15 Pro Max 等）
2. **アプリがビルド・起動**
3. **SnapshotUITests** のテストが実行され、各画面でスクリーンショットを撮影
4. 完了後、**`fastlane/screenshots/`** に画像が保存されます

---

### 2.6 出力先

```
ios-apps/final-hourglass/fastlane/screenshots/
├── iPhone-15-Pro-Max/
│   ├── 01_砂時計メイン画面.png
│   ├── 02_エピソード一覧.png
│   └── ...
└── （他のデバイスサイズ）
```

---

## トラブルシューティング

### エラー: `SnapshotHelper` が見つからない

- **原因**: SnapshotHelper.swift がターゲットに追加されていない
- **対策**: ステップ1を再度確認し、Target Membership に FinalHourglassUITests を設定

---

### エラー: `No such file or directory - SnapshotHelper`

- **原因**: 同上。ファイルがターゲットのソースに含まれていない
- **対策**: ステップ1.4 の方法Bで、ファイルを追加し直す

---

### エラー: `bundle: command not found`

- **原因**: Bundler がインストールされていない
- **対策**:
  ```bash
  gem install bundler
  bundle install
  ```

---

### エラー: シミュレーターが見つからない

```bash
# 利用可能なシミュレーター一覧
xcrun simctl list devices available

# iPhone 15 Pro Max を起動
xcrun simctl boot "iPhone 15 Pro Max"
open -a Simulator
```

---

### スクリーンショットが空・日本語が文字化け

- **原因**: SnapshotUITests.swift 内の `snapshot()` 呼び出しや、画面遷移のタイミング
- **対策**: SnapshotUITests.swift の各テストメソッドを確認し、適切な `wait` や `sleep` を追加

---

## クイックリファレンス

```bash
# 1. Xcode でプロジェクトを開く
cd ios-apps/final-hourglass
open FinalHourglass.xcworkspace

# 2. Xcode GUI で SnapshotHelper.swift と SnapshotUITests.swift を
#    FinalHourglassUITests ターゲットに追加（Target Membership にチェック）

# 3. 依存関係インストール
bundle install

# 4. スクリーンショット生成
bundle exec fastlane screenshots
```

---

## 関連ドキュメント

- [iOS スクリーンショット撮影ガイド](./IOS_SCREENSHOTS.md)（手動撮影の方法）
- [App Store 提出チェックリスト](./APPSTORE_SUBMISSION_CHECKLIST.md)
- [App Store メタデータ](./appstore-metadata.md)
