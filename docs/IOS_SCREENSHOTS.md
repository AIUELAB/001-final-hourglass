# iOS スクリーンショット撮影ガイド

本ドキュメントでは、App Store提出に必要なスクリーンショットの撮影手順を説明します。

---

## 📋 必要なスクリーンショット

### サイズ要件

| デバイス | 解像度 | 必須 |
|----------|--------|------|
| 6.7インチ（iPhone 15 Pro Max） | 1290 x 2796 px | ✅ 必須 |
| 6.1インチ（iPhone 15 Pro） | 1179 x 2556 px | 推奨 |

### 必要枚数

- **最低**: 各サイズ 1枚
- **推奨**: 各サイズ 5枚
- **最大**: 各サイズ 10枚

### 推奨する画面（5枚）

| # | 画面 | 内容 |
|---|------|------|
| 1 | 砂時計メイン画面 | アプリのメインビジュアル、残り時間表示 |
| 2 | エピソード一覧 | 著名人のエピソードカード一覧 |
| 3 | エピソード詳細 | エピソードの詳細表示 |
| 4 | プロフィール画面 | ユーザー情報と健康スコア |
| 5 | 健康入力画面 | 生活習慣の入力フォーム |

---

## 🛠️ 撮影環境の準備

### Step 1: シミュレーターの起動

```bash
# 利用可能なシミュレーター一覧を表示
xcrun simctl list devices available

# iPhone 15 Pro Max シミュレーターを起動
xcrun simctl boot "iPhone 15 Pro Max"

# シミュレーターアプリを開く
open -a Simulator
```

### Step 2: アプリのインストール

```bash
# プロジェクトディレクトリに移動
cd ios-apps/final-hourglass

# シミュレーター向けにビルド
xcodebuild -workspace FinalHourglass.xcworkspace \
  -scheme FinalHourglass \
  -configuration Debug \
  -destination 'platform=iOS Simulator,name=iPhone 15 Pro Max' \
  build

# または Xcode から直接実行
# 1. FinalHourglass.xcworkspace を開く
# 2. ターゲットデバイスで "iPhone 15 Pro Max" を選択
# 3. Cmd + R で実行
```

---

## 📸 スクリーンショットの撮影

### 方法1: コマンドラインで撮影

```bash
# スクリーンショット保存用ディレクトリを作成
mkdir -p ~/Desktop/AppStoreScreenshots

# スクリーンショットを撮影
xcrun simctl io booted screenshot ~/Desktop/AppStoreScreenshots/01_hourglass_main.png
```

### 方法2: シミュレーターで撮影

1. シミュレーターで目的の画面を表示
2. **Cmd + S** でスクリーンショットを保存
3. デスクトップにPNGファイルが保存される

### 方法3: Xcodeで撮影

1. Xcodeでアプリを実行
2. **Debug** → **Capture Screenshot** を選択

---

## 📱 各画面の撮影手順

### 1. 砂時計メイン画面

1. アプリを起動
2. オンボーディングを完了（または既存データで起動）
3. 砂時計タブを表示
4. **Cmd + S** で撮影

```bash
xcrun simctl io booted screenshot ~/Desktop/AppStoreScreenshots/01_hourglass_main.png
```

### 2. エピソード一覧

1. エピソードタブをタップ
2. エピソードカードが複数表示された状態で撮影

```bash
xcrun simctl io booted screenshot ~/Desktop/AppStoreScreenshots/02_episodes_list.png
```

### 3. エピソード詳細

1. エピソード一覧から任意のエピソードをタップ
2. 詳細画面が表示されたら撮影

```bash
xcrun simctl io booted screenshot ~/Desktop/AppStoreScreenshots/03_episode_detail.png
```

### 4. プロフィール画面

1. プロフィールタブをタップ
2. ユーザー情報と健康スコアが表示された状態で撮影

```bash
xcrun simctl io booted screenshot ~/Desktop/AppStoreScreenshots/04_profile.png
```

### 5. 健康入力画面

1. プロフィールタブから健康情報編集ボタンをタップ
2. 入力フォームが表示されたら撮影

```bash
xcrun simctl io booted screenshot ~/Desktop/AppStoreScreenshots/05_health_input.png
```

---

## 🎨 撮影のベストプラクティス

### ✅ Do（推奨）

- **リアルなデータ**を使用（ダミーデータは避ける）
- **明るく見やすい画面**で撮影
- **ステータスバー**を確認（時刻は9:41が一般的）
- **通知やポップアップ**がない状態で撮影
- **バッテリー残量**を満充電で表示

### ❌ Don't（避ける）

- 開発用のデバッグ表示が残っている
- 個人情報が含まれている
- 画面が暗すぎる・見づらい
- エラー画面やローディング中

---

## 🔄 複数デバイスでの撮影

### iPhone 15 Pro Max（6.7インチ）

```bash
# シミュレーターを切り替え
xcrun simctl shutdown all
xcrun simctl boot "iPhone 15 Pro Max"

# 撮影
xcrun simctl io booted screenshot ~/Desktop/AppStoreScreenshots/6.7inch/01_hourglass_main.png
```

### iPhone 15 Pro（6.1インチ）

```bash
# シミュレーターを切り替え
xcrun simctl shutdown all
xcrun simctl boot "iPhone 15 Pro"

# 撮影
xcrun simctl io booted screenshot ~/Desktop/AppStoreScreenshots/6.1inch/01_hourglass_main.png
```

---

## 📁 ファイル整理

推奨するディレクトリ構造:

```
~/Desktop/AppStoreScreenshots/
├── 6.7inch/
│   ├── 01_hourglass_main.png
│   ├── 02_episodes_list.png
│   ├── 03_episode_detail.png
│   ├── 04_profile.png
│   └── 05_health_input.png
└── 6.1inch/
    ├── 01_hourglass_main.png
    ├── 02_episodes_list.png
    ├── 03_episode_detail.png
    ├── 04_profile.png
    └── 05_health_input.png
```

---

## ✅ 撮影チェックリスト

撮影後、以下を確認してください:

- [ ] 6.7インチ用スクリーンショット 5枚撮影済み
- [ ] 6.1インチ用スクリーンショット 5枚撮影済み（任意）
- [ ] 全画像がPNG形式
- [ ] 画像サイズが正しい（1290x2796 / 1179x2556）
- [ ] 個人情報が含まれていない
- [ ] デバッグ表示がない
- [ ] 画面が明るく見やすい

### サイズ確認コマンド

```bash
# 画像サイズを確認
sips -g pixelWidth -g pixelHeight ~/Desktop/AppStoreScreenshots/6.7inch/*.png

# 期待値:
# pixelWidth: 1290
# pixelHeight: 2796
```

---

## 📚 関連ドキュメント

- [App Store メタデータ](./appstore-metadata.md)
- [iOS署名証明書設定ガイド](./IOS_SIGNING_SETUP.md)
- [App Store提出チェックリスト](./APPSTORE_SUBMISSION_CHECKLIST.md)

---

## 🔧 トラブルシューティング

### シミュレーターが見つからない

```bash
# 最新のシミュレーターランタイムをインストール
xcodebuild -downloadPlatform iOS
```

### スクリーンショットが保存されない

```bash
# シミュレーターの状態を確認
xcrun simctl list devices booted

# 起動していない場合は起動
xcrun simctl boot "iPhone 15 Pro Max"
```

### 画像サイズが違う

シミュレーターの設定で「Physical Size」になっていることを確認:
- **Window** → **Physical Size** を選択
