# Claude Code プロジェクト指示書（MCP対応版）🏆

## 🔴 品質優先原則（Quality-First Principles）- 最重要

### ⚠️ 絶対禁止事項（MUST NOT）

#### 1. **ダミーデータでの処理継続禁止**
```python
# ❌ 絶対禁止
if not api_available:
    return {'results': 0, 'data': []}  # ダミーデータで継続

# ✅ 正しい実装
if not api_available:
    raise SystemNotReadyError("API未設定のため処理を中止します")
```

#### 2. **プレースホルダーコードの本番使用禁止**
- TODO、FIXME、シミュレート、未実装のコードは本番環境に流さない
- `return 0` や `return []` などのダミー返り値の検出と排除
- 「後で実装」は技術的負債ではなく、品質欠陥として扱う

#### 3. **品質検証なしの出力禁止**
- データ品質検証前のCSV/JSON出力は絶対禁止
- 統計的異常（削除率45%超など）の自動検出必須
- 既知の有名人（HIKAKIN等）での妥当性検証なしの処理禁止

### ✅ 必須実装事項（MUST DO）

#### 1. **Fail-Fast原則の徹底**
- エラーは隠蔽せず、早期に顕在化させる
- 部分的成功での処理継続より、全体停止を選択
- 「動いているふり」より「正直な失敗」を優先

#### 2. **品質ゲートシステム**
```python
# 必須の品質ゲート
QUALITY_GATES = [
    "システム準備確認",      # API設定、依存関係チェック
    "データ品質検証",        # ダミーデータ検出、完全性確認
    "スコア妥当性確認",      # 範囲チェック、異常値検出
    "統計的整合性チェック",  # 削除率、分布の妥当性
    "サンプル検証"          # 既知データでの正確性確認
]
```

#### 3. **トランザクション処理**
- 全処理成功 or 全ロールバック（部分的成功を許さない）
- エラー時の完全な状態復元
- 監査ログによる全判定の追跡可能性確保

### 📊 品質メトリクスと基準値

| メトリクス | 基準値 | アクション |
|----------|--------|-----------|
| API応答実データ率 | >95% | 95%未満で処理停止 |
| 削除率 | 10-20% | 範囲外で再検証必須 |
| 有名人最低スコア | >7.0 | HIKAKIN等の検証必須 |
| ダミーデータ検出数 | 0 | 1件でも検出で即停止 |

### 🚨 品質問題発生時の対処

1. **即座に処理を停止**（エラーを隠さない）
2. **詳細な監査ログを出力**（原因追跡可能に）
3. **ロールバックを実行**（不完全なデータを残さない）
4. **人間への通知**（自動修復を試みない）

---

## 🎭 架空キャラクター・フィクション作品の保護ルール

### ⚠️ 重要原則
**架空キャラクターは知名度があれば削除対象ではない**

### 保護対象の架空キャラクター例
- **竈門炭治郎**（鬼滅の刃）- 社会現象作品の主人公
- **孫悟空**（ドラゴンボール）- 世界的有名作品のキャラクター
- **ドラえもん**（ドラえもん）- 国民的キャラクター
- **ピカチュウ**（ポケモン）- 世界的認知度
- **ルフィ**（ONE PIECE）- 長期連載人気作品
- **エヴァンゲリオン初号機**（エヴァンゲリオン）- 文化的影響大
- **セーラームーン**（美少女戦士セーラームーン）- ジャンルの代表

### 架空キャラクターの判定基準
1. **文化的影響度** - 作品の社会的影響力（社会現象、流行語など）
2. **認知度** - 一般的な知名度（子供から大人まで）
3. **商業的成功** - 興行収入、売上、グッズ展開
4. **国際的評価** - 海外での認知度、翻訳版の存在
5. **歴史的価値** - 作品の歴史、ジャンルへの影響

### 架空キャラクターの分類と扱い

| カテゴリ | 例 | 扱い | 基準 |
|---------|-----|------|------|
| 国民的キャラクター | ドラえもん、サザエさん、アンパンマン | **絶対保存** | 3世代以上に認知 |
| 世界的有名作品 | ドラゴンボール、ポケモン、ナルト | **絶対保存** | 海外展開成功 |
| 社会現象作品 | 鬼滅の刃、進撃の巨人、呪術廻戦 | **保存** | メディア露出大 |
| 有名ゲームキャラ | マリオ、リンク、クラウド | **保存** | ゲーム売上1000万本以上 |
| 歴史的作品 | 鉄腕アトム、ガンダム、ウルトラマン | **保存** | 20年以上の歴史 |
| マイナー作品 | 認知度低い作品のキャラクター | **要レビュー** | 上記基準未満 |

### データベースでの実装ルール
```python
# 架空キャラクター判定
if entity_type == "fictional_character":
    if cultural_impact_score >= 6.0:
        return "KEEP"  # 文化的影響度が高い
    elif google_trends_score >= 30:
        return "KEEP"  # 検索トレンドが高い
    elif has_wikipedia and wikipedia_languages >= 3:
        return "KEEP"  # 複数言語のWikipedia記事
    else:
        return "REVIEW_REQUIRED"
```

---

## 🚀 Ultra Think モード - サブエージェント自動活用

### 並行処理の原則

Claude Codeは以下の条件で**自動的にサブエージェント（Taskツール）を使用**します：

- **3つ以上の独立タスク**: 必ずTask toolで並行実行
- **ファイル検索・データ処理・分析**: 可能な限り並行化
- **I/O待機時間**: 最小化のため積極的に並列処理
- **大量データ処理**: 自動的に分割して並列実行

### タスク分割基準

- **ファイル処理**: 100件以上 → 10並列実行
- **データ変換**: 1000行以上 → バッチ分割処理
- **API呼び出し**: 5件以上 → バッチ処理で並列化
- **検索タスク**: 複数条件 → 並行検索

### 🎯 効率化の自動判断

Claude Codeは以下を**能動的に判断**して並列化します：

1. タスクの独立性を分析
2. 処理時間を推定
3. 最適な並列数を決定
4. サブエージェントに自動振り分け

## 🎯 Serena MCP Server 自動起動（永久設定済み - 2025年8月30日）

### 🚀 Claude Code起動時にSerenaが自動起動

**このプロジェクトでClaude Codeを起動すると、Serena MCPサーバーが自動的に起動します。**

#### 自動起動される内容

1. **Serena MCPサーバー**: SSEトランスポート、ポート8000で起動
2. **Webダッシュボード**: [http://127.0.0.1:24282/dashboard/index.html](http://127.0.0.1:24282/dashboard/index.html)
3. **API エンドポイント**: [http://localhost:8000](http://localhost:8000)
4. **プロジェクト自動アクティベート**: 001-final-hourglass

#### 手動制御コマンド

```bash
# Serenaの状態確認
ps aux | grep serena-mcp-server

# Serenaを手動で停止
pkill -f serena-mcp-server

# Serenaを手動で起動
python3 scripts/start_serena_server.py

# ログ確認
tail -f serena_startup.log
```

#### 永続設定ファイル

- `startup_config.json` - `serena_settings`セクションで自動起動を制御
- `scripts/claude-startup-hook.sh` - 起動フックスクリプト（Serena起動を含む）
- `scripts/start_serena_server.py` - Serena起動スクリプト

## 📊 Ultra Think 自動同期システム（2025年8月永久設定）

### 🚀 起動時自動同期＆ブラウザ表示（永久設定済み）

**Claude Code起動時に以下が自動実行されます：**

1. **データベース自動同期**: 最新のultra_think_*.csvをGoogle Sheetsと同期
2. **ブラウザ自動表示**: 同期完了後、Google Sheetsを自動でブラウザに表示
3. **音声通知**: 同期完了時に通知音を再生（オプション）
4. **バックグラウンド監視**: ファイル変更を継続的に監視

### ⚡ 起動時自動実行（デフォルトで有効）

```bash
# Claude Code起動時に自動実行される永久設定
# 手動実行も可能:
python3 auto_startup_sync.py

# 起動フックの手動実行
./scripts/claude-startup-hook.sh
```

### 📋 永久設定ファイル

#### `startup_config.json` - 起動設定（永久保存）

```json
{
  "startup_settings": {
    "auto_sync_on_startup": true,      // 起動時自動同期
    "auto_open_browser": true,         // ブラウザ自動オープン
    "browser_focus": true,             // ブラウザにフォーカス
    "show_notification": true          // デスクトップ通知
  }
}
```

#### `sheets_config.json` - 同期設定

- `auto_sync_enabled`: データ自動同期の有効/無効
- `auto_rename_sheet`: スプレッドシート名自動更新の有効/無効
- `spreadsheet_id`: Google SheetsのID

### 📌 スプレッドシート名同期ルール（永久設定）

**重要**: CSVファイル名とGoogle Sheetsのスプレッドシート名は常に同期させる

#### 命名規則

- **CSVファイル名**: `ultra_think_XXXX_YYYYMMDD_HHMMSS.csv`
- **スプレッドシート名**: `Ultra Think XXXX YYYYMMDD HHMMSS`
- アンダースコア(_)はスペースに変換
- 最初の`ultra_think`は`Ultra Think`に変換（大文字化）
- 日付・時刻部分（YYYYMMDD_HHMMSS）はそのまま保持

#### 自動同期タイミング

1. **force_sync.py実行時**: 必ずスプレッドシート名も更新
2. **auto_startup_sync.py実行時**: 起動時に自動同期
3. **CSVファイル名変更時**: watchdogで監視して自動更新
4. **手動同期時**: すべての同期操作でスプレッドシート名も更新

#### 設定確認

```json
{
  "auto_rename_sheet": true,  // 必ずtrueに設定（永久有効）
  "sheet_name_sync_rule": "auto"  // 自動同期ルール
}
```

### 🎯 自動実行される処理

1. **環境チェック**: Python環境、必要ファイルの確認
2. **最新CSV検出**: ultra_think_*.csvの最新版を自動検出
3. **Google Sheets同期**: データを完全同期
4. **ブラウザ起動**: デフォルトブラウザでスプレッドシートを表示
5. **ログ記録**: sync_log.jsonに実行履歴を記録

### 📱 通知システム

- **音声通知**: 同期完了時に成功音を再生
- **デスクトップ通知**: macOS通知センターに表示
- **ログ出力**: コンソールに詳細情報を表示

### ⚙️ カスタマイズ

起動時の動作は`startup_config.json`で詳細にカスタマイズ可能：

- ブラウザの選択（Chrome, Safari, Firefox等）
- 音声通知のON/OFF
- 同期タイミングの調整
- メモリ制限の設定

### 📝 ログ

- `sync_log.json`: 同期履歴（最新10件を保持）
- `sheet_sync.log`: バックグラウンド監視のログ
- `logs/startup_sync_*.log`: 起動時同期の詳細ログ

## プロジェクト概要

このプロジェクトは**2025年最新ベストプラクティス**に対応したMCP（Model Context Protocol）サーバーが完全統合されたClaude Codeテンプレートです。

## 🆕 最新アップデート (2025年8月)

- **Ollama統合** - 完全無料のローカルLLM対応
- **MkDocs自動ドキュメント生成** - コードから直接APIドキュメント作成
- **Ruff統一** - Black/isort/flake8を一つのツールに統合
- **最適化された依存関係** - 不要なパッケージを削除し高速化

## 🎯 2025年最新機能

### スラッシュコマンド

`.claude/commands/`ディレクトリにカスタムコマンドが定義されています：

- `/fix-errors` - エラー修正
- `/refactor` - リファクタリング
- `/test` - テスト作成
- `/review` - コードレビュー
- `/optimize` - パフォーマンス最適化

### MCPプロファイル

パフォーマンスに応じて選択可能：

- `minimal` - Serenaのみ（最高速）
- `standard` - 基本開発セット
- `remote` - リモートサーバーのみ（クラウドネイティブ）
- `hybrid` - ローカル＋リモートの併用
- `full` - 全機能有効

### リモートMCPサーバー（2025年8月追加）

クラウドホスト型MCPサーバーをローカル設定なしで利用可能：

- **SSE/HTTPトランスポート** - リアルタイム通信対応
- **OAuth 2.0認証** - セキュアな認証フロー
- **自動更新** - ベンダー管理による常に最新の状態
- 詳細は`REMOTE_MCP_SERVERS.md`参照

### Headlessモード

CI/CDでの自動実行に対応：

```bash
./scripts/claude-headless.sh -t test
```

## 🎯 利用可能なMCPサーバー

### 🌟 Serena - 高度なコード操作サーバー（推奨）

- **セマンティックコード検索** - LSPを使用した高度なコード理解
- **多言語対応** - Python, TypeScript, Go, Rust, Java, C#, PHP等
- **コード実行** - シェルコマンドの実行とログ読み取り
- **プロジェクト管理** - 自動インデックス作成と高速検索
- **filesystemの上位互換** - より高度なファイル操作が可能

### 🔧 Smithery - MCPサーバー管理ツール

- **サーバー管理** - MCPサーバーのインストール/アンインストール/更新
- **サーバー検索** - SmitheryレジストリからMCPサーバーを探す
- **サーバー検査** - インストール済みサーバーの詳細情報
- **開発ツール** - MCPサーバー開発用のホットリロード、ビルド、プレイグラウンド

### 基本MCPサーバー

- **filesystem** - ファイルシステム操作（Serena使用時は無効推奨）
- **github** - GitHub統合（Issue、PR、コード検索）
- **fetch** - Web取得とスクレイピング
- **context7** - ライブラリドキュメント取得
- **brave-search** - Web、画像、ニュース、動画検索
- **playwright** - ブラウザ自動化とテスト
- **ide** - IDE統合（診断、コード実行）
- **firecrawl** - 高度なWebスクレイピング

### 追加MCPサーバー

- **memory** - 長期記憶管理
- **sequential-thinking** - 順次思考処理
- **puppeteer** - ブラウザ自動化（代替）
- **smithery-stdout** - stdoutログのキャプチャと管理
- **postgres/slack/gitlab** - 各種サービス統合
- **aws/gcp/azure** - クラウドサービス統合
- **docker/kubernetes** - コンテナ管理

### 🌐 リモートMCPサーバー（クラウドホスト型）

- **Linear** - 課題管理とプロジェクト追跡（SSE）
- **Notion** - ナレッジベースとワークスペース（HTTP + OAuth）
- **Sentry** - エラー追跡とパフォーマンス監視（SSE）
- **Apidog** - API ドキュメントとテスト（HTTP）
- **SimpleScraper** - Webスクレイピングサービス（SSE）

## 開発環境

- Python 3.11+
- Node.js 18+
- 仮想環境: `venv`
- パッケージ管理: pip, npm

## 重要なコマンド

### MCPセットアップ

```bash
# ローカルMCPサーバーのインストール
cd mcp-config
bash setup-mcp.sh

# リモートMCPサーバーの設定
./scripts/setup-remote-mcp.sh

# 環境変数の設定
cp .env.mcp.example .env.mcp
# .env.mcpファイルを編集してAPIキーを設定

# リモートサーバー管理
./scripts/mcp-remote-manager.sh list    # サーバー一覧
./scripts/mcp-remote-manager.sh test    # 接続テスト
./scripts/mcp-remote-manager.sh profile hybrid  # ハイブリッドプロファイル適用
```

### 環境セットアップ

#### オプション1: Python仮想環境（開発推奨）

```bash
# 仮想環境の作成と有効化
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate  # Windows

# 本番用依存関係（Ollama無し）
pip install -r requirements.txt

# 開発用依存関係（Ollama含む）
pip install -r requirements-dev.txt

# NPMパッケージ
npm install  # package.jsonがある場合
```

#### オプション2: Docker（本番環境推奨）✅ 完全解決済み

```bash
# Dockerイメージのビルド
docker build -t claude-code-mcp:latest .

# コンテナの実行
docker run -it --rm \
  -v $(pwd):/app \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e ANTHROPIC_API_KEY=$ANTHROPIC_API_KEY \
  claude-code-mcp:latest

# VS Code Dev Containerとして使用
# .devcontainer/devcontainer.jsonが設定済み
# VS Code/Cursorで「Reopen in Container」を選択
```

#### 依存関係の管理

```bash
# 本番用: requirements.txt (Ollama無し、Docker対応)
# 開発用: requirements-dev.txt (Ollama含む、ローカル開発用)

# pyproject.tomlから再生成する場合
pip-compile pyproject.toml -o requirements.txt
# または uvを使用
uv pip compile pyproject.toml -o requirements.txt
```

### 開発コマンド

```bash
# コードフォーマット（Ruff統一）
ruff format src/ tests/

# リント（Ruff統一）
ruff check src/ tests/

# テスト実行
pytest tests/

# 型チェック
mypy src/
```

## MCPサーバーの活用例

### Serenaでの高度なコード操作

```python
# セマンティック検索
# "Serenaで calculate_sum 関数の定義を探して"
# "Serenaで TODO コメントがあるすべての場所を表示"

# コードリファクタリング
# "Serenaですべての print 文を logger.info に置換"
# "Serenaで変数名 foo を bar にリネーム"

# コード実行
# "Serenaで pytest を実行して結果を確認"
# "Serenaで npm run build を実行"
```

### ファイル操作

```python
# MCPのfilesystemサーバーを使って、ファイルを読み書き
# /mcp コマンドでMCPツールを確認
```

### GitHub統合

```python
# GitHubのIssueやPRを直接操作
# コード検索や自動レビューも可能
```

### Web検索とスクレイピング

```python
# Brave SearchやFirecrawlを使った情報収集
# Playwrightでブラウザ自動化
```

## プロジェクト構造

```text
.
├── mcp-config/         # MCP設定とスクリプト
│   ├── claude_desktop_config.json
│   └── setup-mcp.sh
├── src/                # ソースコード
├── tests/              # テストコード
├── scripts/            # ユーティリティスクリプト
└── venv/               # Python仮想環境
```

## 📊 CSVファイル作成規約

### Excel対応必須ルール

**重要**: すべてのCSVファイルは必ずExcelで開くことを想定して作成すること

#### UTF-8 BOM必須
- **すべてのCSVファイル出力時にBOM（Byte Order Mark）を付与**
- BOM: `0xEF 0xBB 0xBF` を先頭に追加
- Pythonでの実装: `encoding='utf-8-sig'`を使用

#### 日本語文字化け防止
- 日本語データが正しく読み取れることを確認
- Excelで開いても文字化けしないことを検証
- 作成後は必ずExcelでの表示確認を行う

#### 実装例
```python
# CSVファイル作成時（pandas使用）
with open('output.csv', 'w', encoding='utf-8-sig') as f:
    df.to_csv(f, index=False)

# 通常のCSV作成
import csv
with open('output.csv', 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.writer(f)
    writer.writerows(data)
```

#### チェックリスト
- [ ] UTF-8 BOMが付与されている
- [ ] 日本語が含まれるデータで動作確認済み
- [ ] Excelで開いて文字化けがないことを確認
- [ ] 数値・日付フォーマットが正しく認識される

## コーディング規約

- PEP 8に準拠
- Ruffでフォーマット・リント（Black/isort/flake8互換）
- 型ヒントを積極的に使用
- docstringは必須（Google Style）
- MCPサーバーを活用した効率的な開発

## 注意事項

- コミット前に必ずテストを実行
- 環境変数は`.env`と`.env.mcp`ファイルで管理
- センシティブな情報はコミットしない
- MCPサーバーのAPIキーは適切に管理

## よくある作業

### 新機能の追加

1. `src/`に新しいモジュールを作成
2. 対応するテストを`tests/`に作成
3. MCPサーバーを活用して外部サービスと連携
4. テストを実行して確認
5. コードをフォーマット・リント

### MCPサーバーの活用

```python
# GitHubから情報取得
# mcp__github__get_issue でIssue情報を取得

# Webから情報収集
# mcp__brave-search__brave_web_search で検索

# ファイル操作
# mcp__filesystem__read_file でファイル読み込み
```

### デバッグ

```python
import pdb; pdb.set_trace()  # ブレークポイント
```

## トラブルシューティング

### MCPサーバー関連

- MCPサーバーが動作しない場合は`npm install -g @modelcontextprotocol/server-*`を実行
- APIキーが設定されているか`.env.mcp`を確認
- Claudeアプリケーションを再起動

### Python環境

- 仮想環境が有効でない場合は`source venv/bin/activate`を実行
- パッケージが見つからない場合は`pip install -r requirements.txt`を再実行

## Smitheryの使い方

### MCPサーバーの管理

```bash
# Smitheryを使って新しいMCPサーバーをインストール
"Smitheryで obsidian MCPサーバーをインストールして"

# インストール済みサーバーの確認
"Smitheryでインストール済みのMCPサーバーを一覧表示"

# サーバーの詳細情報
"Smitheryで github MCPサーバーの詳細を表示"
```

### 開発ツール

```bash
# MCPサーバーの開発
"Smitheryで開発サーバーを起動（ホットリロード付き）"
"Smitheryでサーバーをビルド"
"Smitheryでプレイグラウンドを開く"
```

## Serenaの詳細な使い方

### プロジェクトのアクティベート

```bash
# 特定のプロジェクトをアクティベート
# "Serenaで /path/to/project をアクティベート"
```

### LSP機能の活用

- **定義にジャンプ**: 関数やクラスの定義元を探す
- **参照検索**: 特定の関数が使われている場所をすべて探す
- **シンボル検索**: プロジェクト全体からシンボルを検索
- **エラー診断**: コードのエラーをリアルタイムで検出

### Serena vs filesystem

- Serena使用時はfilesystemサーバーを無効にすることを推奨
- Serenaはより高度なコード理解と操作が可能
- シンプルなファイル読み書きのみの場合はfilesystemでも十分

## MCPサーバー使用時のベストプラクティス

1. **適切なサーバーの選択**
   - コード操作: Serena（推奨）
   - ファイル操作: filesystem
   - GitHub操作: github
   - Web検索: brave-search
   - スクレイピング: firecrawl/playwright

2. **エラーハンドリング**
   - MCPサーバーのレスポンスを適切に処理
   - APIレート制限に注意

3. **セキュリティ**
   - APIキーは環境変数で管理
   - 認証情報をハードコードしない

## リソース

- [MCP Documentation](https://modelcontextprotocol.io/)
- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [GitHub MCP Server](https://github.com/modelcontextprotocol/servers)

## 開発コマンド（最適化版）

```bash
# コードフォーマット（Ruff統一）
ruff format src tests

# リント（Ruff統一）
ruff check src tests --fix

# 型チェック
mypy src

# テスト実行（カバレッジ）
pytest tests --cov=src

# すべてのチェック
pre-commit run --all-files

# Ollama統合
./scripts/setup-ollama.sh  # セットアップ
python src/ollama_integration.py  # テスト実行

# ドキュメント生成
mkdocs serve  # ローカルプレビュー
mkdocs build  # ビルド
```

## 依存関係の更新（uv推奨）

```bash
uv pip compile requirements.in -o requirements.txt
uv pip sync requirements.txt
```

## GitHub MCP Integration（ネイティブ版）

```bash
# ネイティブバイナリのインストール（Docker不要）
./setup_github_mcp.sh

# 環境変数（.env もしくは .env.mcp）
# どちらの変数名でも可：GITHUB_TOKEN / GITHUB_PAT
GITHUB_TOKEN=your_github_token
# LLMプロバイダ
OPENAI_API_KEY=your_openai_key  # または ANTHROPIC_API_KEY

# 動作確認
python test_github_mcp.py
python src/github_mcp_integration.py
```

## Docker トラブルシューティング ✅ 解決済み

### 問題: Failed to reopen folder in container

**原因**: 依存関係の競合（httpxバージョン、Ollamaパッケージ）

**解決策**:

1. Ollamaパッケージを`optional-dependencies`に移動
2. `requirements.txt` - 本番用（Ollama無し）
3. `requirements-dev.txt` - 開発用（Ollama含む）
4. httpxを0.27.0に統一

### Docker使用状況

```bash
# イメージ確認
docker images | grep claude-code-mcp
# claude-code-mcp   latest    2a4e584ffcfb   238MB ✅

# コンテナ動作確認
docker run --rm claude-code-mcp:latest python --version
# Python 3.11.13 ✅

# 完全なクリーンビルド
docker build --no-cache -t claude-code-mcp:latest .
```

### VS Code/Cursor Dev Container

```json
// .devcontainer/devcontainer.json設定済み
// "Reopen in Container"で自動的にDocker環境で開発可能
```
