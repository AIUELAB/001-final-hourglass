# Google Sheets リアルタイム同期システム 📊

## 概要
Ultra Think データベース（人物データ）をGoogle Sheetsとリアルタイムで同期するシステムです。
ブラウザ上で簡単に閲覧・編集でき、変更は自動的にローカルCSVファイルに反映されます。

## 🚀 クイックスタート

### 1. 必要なパッケージのインストール
```bash
pip install -r requirements_sheets.txt
```

### 2. Google Cloud Platform設定

#### サービスアカウントの作成
1. [Google Cloud Console](https://console.cloud.google.com)にアクセス
2. 新しいプロジェクトを作成または既存のプロジェクトを選択
3. 左メニューから「APIとサービス」→「ライブラリ」を選択
4. 以下のAPIを有効化：
   - Google Sheets API
   - Google Drive API

#### 認証情報の作成
1. 「APIとサービス」→「認証情報」を選択
2. 「認証情報を作成」→「サービスアカウント」を選択
3. サービスアカウントの詳細を入力して作成
4. 作成したサービスアカウントをクリック
5. 「キー」タブ→「鍵を追加」→「新しい鍵を作成」→「JSON」
6. ダウンロードしたJSONファイルを`credentials.json`として保存

### 3. 初回セットアップと実行
```bash
# 初回セットアップ（認証とスプレッドシート作成）
python google_sheets_sync.py --setup

# CSVをGoogle Sheetsにアップロード
python google_sheets_sync.py --upload
```

## 📋 使用方法

### 基本コマンド

#### データのアップロード
```bash
python google_sheets_sync.py --upload
```
ローカルのCSVファイルをGoogle Sheetsにアップロードします。

#### データのダウンロード
```bash
python google_sheets_sync.py --download
```
Google Sheetsの内容をローカルCSVファイルにダウンロードします。

#### 双方向同期
```bash
python google_sheets_sync.py --sync
```
アップロードとダウンロードを両方実行します。

#### リアルタイム監視モード
```bash
python google_sheets_sync.py --watch
```
ファイルの変更を監視し、自動的に同期を行います。
- ローカルCSVの変更 → 自動的にSheetsへアップロード
- Google Sheetsの変更 → 30秒ごとにチェックしてダウンロード

#### ステータス確認
```bash
python google_sheets_sync.py --status
```
現在の同期状態を確認します。

## 🎯 Google Sheetsでの編集

### アクセス方法
1. プログラム実行後に表示されるURLをクリック
2. または、Googleドライブから「Ultra Think Database」を開く

### 便利な機能

#### フィルタリング
- データ → フィルタを作成
- 条件を設定して必要なデータのみ表示

#### ソート
- 列のヘッダーをクリック → データ → 列をソート

#### 条件付き書式
- フォーマット → 条件付き書式
- 例：accuracy_score < 70 の行を赤色でハイライト

#### データ検証
- データ → データの検証
- ドロップダウンリストや数値範囲を設定

#### コメント機能
- セルを右クリック → コメントを挿入
- 修正内容や確認事項をメモ

## 📁 ファイル構成

```
001-final-hourglass/
├── google_sheets_sync.py      # メインプログラム
├── sheets_config.json         # 設定ファイル
├── requirements_sheets.txt    # 必要なパッケージ
├── credentials.json           # Google認証ファイル（要作成）
└── ultra_think_NO_FAKE_RESEARCHERS_20250827_143418.csv  # データベース
```

## ⚙️ 設定ファイル (sheets_config.json)

```json
{
  "csv_file": "CSVファイル名",
  "sheet_name": "スプレッドシート名",
  "spreadsheet_id": "自動生成されるID",
  "auto_sync_interval": 30,      # 自動同期間隔（秒）
  "backup_enabled": true,         # バックアップ有効/無効
  "batch_size": 1000             # バッチアップロードサイズ
}
```

## 🔍 データ品質チェック機能

### 自動検出される問題
- 重複データ
- 空白フィールド
- 数値範囲外の値
- 日本語名の欠落

### 修正方法
1. Google Sheetsで問題のあるセルを直接編集
2. 変更は自動的にローカルCSVに反映
3. バックアップが自動作成されるので安心

## 🚨 トラブルシューティング

### 認証エラーが発生する場合
- `credentials.json`が正しい場所にあるか確認
- Google Cloud ConsoleでAPIが有効になっているか確認

### アップロードが遅い場合
- `sheets_config.json`の`batch_size`を調整
- ネットワーク接続を確認

### 同期が反映されない場合
- `--watch`モードを再起動
- Google Sheetsをリロード

## 💡 活用例

### デバッグワークフロー
1. `python google_sheets_sync.py --upload`でデータをアップロード
2. Google Sheetsで問題のあるデータを確認
3. フィルタで問題のある行のみ表示
4. 直接編集して修正
5. `python google_sheets_sync.py --download`で修正済みデータを取得

### チーム作業
1. スプレッドシートURLをチームメンバーと共有
2. 複数人で同時に異なる部分を編集
3. リアルタイム同期で全員の変更を統合

## 📝 注意事項

- 大量のデータ（10万行以上）の場合は処理時間がかかります
- 同時編集時は競合を避けるため、異なる行を編集してください
- バックアップファイルは定期的に削除してください

## 🆘 サポート

問題が発生した場合は、以下を確認してください：
1. エラーメッセージの内容
2. `sheets_config.json`の設定
3. Google Cloud Consoleの設定
4. ネットワーク接続状態

---
Created by Ultra Think Database Manager v1.0
