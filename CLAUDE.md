## 🌐 言語設定
**CRITICAL**: すべての応答は**日本語**で行ってください。

---

## 🚀 システム自動稼働 - 最重要

起動時に緑色バナー表示 = すべて正常稼働中。**システム状態の質問は不要です。**

稼働中システム: Serena MCP, Codex MCP, PDCAガーディアン, セッション記録, AI協調分析, KAIROS, RCA-Kaizen

詳細: `.session/STATUS.md`, `.session/AUTO_STARTUP_GUIDE.md`

---

## 🔴 品質優先原則（Quality-First）

### 絶対禁止
- ダミーデータでの処理継続
- プレースホルダーコードの本番使用
- 品質検証なしの出力

### 必須事項
- **Fail-Fast原則**: エラーは早期に顕在化
- **品質ゲート**: API応答率>95%, 削除率10-20%, ダミーデータ=0
- **トランザクション**: 全成功 or 全ロールバック

---

## 🎭 架空キャラクター保護ルール

**架空キャラクターは知名度があれば削除対象外**

| カテゴリ | 例 | 扱い |
|---------|-----|------|
| 国民的 | ドラえもん、サザエさん | **絶対保存** |
| 世界的 | ドラゴンボール、ポケモン | **絶対保存** |
| 社会現象 | 鬼滅の刃、進撃の巨人 | **保存** |

判定基準: `cultural_impact_score >= 6.0` or `google_trends_score >= 30`

---

## 🎭 架空キャラクターエピソード生成ルール（EPUP）

**エピソード本文に絶対書かないメタ的表現**:
- 「このキャラクターは架空です」
- 「実在しないためエピソードは存在しません」
- 「公式な描写は存在しません」
- 「申し訳ございませんが」
- 「フィクションとして」「設定上は」

**生成方針**:
| person_type | 生成方針 |
|-------------|---------|
| FICTIONAL | 作品世界内の視点でフィクション生成 |
| REAL | 事実ベースで慎重に生成 |

**チェックリスト（架空キャラ生成時）**:
- [ ] メタ的説明が含まれていないか
- [ ] 作品設定と矛盾していないか
- [ ] キャラクターの性格が一貫しているか
- [ ] 「あなたと同じ○歳のとき」形式で開始しているか

**検出・修正ツール**: `scripts/fix_fictional_meta_episodes.py`

---

## 🎯 スラッシュコマンド（Skills）

### 品質・分析系
- `/pdca` - 品質分析・改善提案
- `/codex-analyze` - AI協調分析
- `/kairos` - 機会検出
- `/rca` - 根本原因分析

### MCP管理系
- `/mcp-profile` - プロファイル切替（minimal/web/scraping/full）
- `/enable-web` - Web MCP一時有効化

### 開発系
`/fix-errors`, `/refactor`, `/test`, `/review`, `/optimize`

---

## 🔧 MCPサーバー

### 有効（常時）
- **ide** - IDE統合
- **context7** - ライブラリドキュメント

### 無効化済み（必要時に有効化）
- playwright, firecrawl, brave-search, fetch

プロファイル切替: `python scripts/switch_mcp_profile.py [minimal|web|scraping|full]`

---

## 🔀 Git/MCP運用フロー

### 日常の標準フロー（main直接push）

```bash
# 作業開始
git pull origin main

# 作業完了後
git status              # 変更確認
git add .               # ステージ
git commit -m "type: 説明"
git push origin main
```

### コミットメッセージ形式

| type | 用途 |
|------|------|
| `fix:` | バグ修正 |
| `feat:` | 新機能 |
| `docs:` | ドキュメント |
| `chore:` | 雑務・設定変更 |
| `style:` | フォーマット |

### MCP GitHub活用

| 操作 | MCPツール |
|------|----------|
| 履歴確認 | `mcp__github__list_commits` |
| Issue作成 | `mcp__github__create_issue` |
| Issue一覧 | `mcp__github__list_issues` |
| ファイル確認 | `mcp__github__get_file_contents` |

**重要**: MCP操作後は必ず `git pull origin main` でローカル同期

### トラブル対処

| エラー | 対処 |
|--------|------|
| non-fast-forward | `git pull --rebase origin main` |
| コンフリクト | 手動解決 → `git add` → `git rebase --continue` |

詳細: `docs/GIT_MCP_WORKFLOW.md`

---

## 📊 CSVファイル規約

- **UTF-8 BOM必須**: `encoding='utf-8-sig'`
- Excel対応必須

---

## 📁 マスターCSV運用ルール（単一マスター原則）

### 正規マスター（唯一の実ファイル）

```
preserved/data/MASTER_EPISODES_CURRENT.csv  ← 正規マスター（実ファイル）
```

### シンボリックリンク構造

```
data/MASTER_EPISODES_CURRENT.csv
    ↓ シンボリックリンク
preserved/data/MASTER_EPISODES_CURRENT.csv
```

### 運用ルール

| 操作 | 使用パス |
|------|----------|
| **編集（Claude/スクリプト）** | `preserved/data/MASTER_EPISODES_CURRENT.csv` |
| **読み込み（ダッシュボード）** | `data/MASTER_EPISODES_CURRENT.csv`（リンク経由） |
| **整合性チェック** | `python scripts/check_single_master.py` |

### 絶対禁止

- ❌ `data/MASTER_EPISODES_CURRENT.csv` に実ファイルを作成
- ❌ シンボリックリンクを削除して実ファイルに置換
- ❌ `preserved/data/` 以外の場所にマスターCSVを複製

### 整合性チェック（定期実行推奨）

```bash
python scripts/check_single_master.py
```

チェック項目:
1. 正規マスターの存在確認
2. シンボリックリンクの正常性
3. 二重マスター（実ファイル重複）の検出

---

## 📊 ダッシュボード運用ルール（単一正規版原則）

### 正規ダッシュボード（唯一の最新版）

```
preserved/episode_database_dashboard_v7.html  ← 正規版
```

### 運用ルール

| 操作 | 使用パス |
|------|----------|
| **編集・閲覧** | `preserved/episode_database_dashboard_v*.html` |
| **バージョンアップ** | preserved/ に新バージョンを作成 |
| **旧バージョン** | `archive/dashboards/` に保存 |

### 絶対禁止

- ❌ ルート直下にダッシュボードHTMLを作成
- ❌ preserved/ 以外の場所でダッシュボードを編集
- ❌ 同一バージョンの複数コピーを保持

### バージョンアップ手順

1. preserved/ に新バージョンを作成（例: v8.html）
2. 旧バージョンを archive/dashboards/ に移動
3. ファイル名・title・h1のバージョン番号を同期

---

## 🔢 バージョン同期ルール（EPUP）

**ファイル名のバージョンとUI表示は必ず同期させる**

| 変更対象 | 同時更新必須 |
|----------|-------------|
| ファイル名 `*_v6.html` | `<title>`, `<h1>` のバージョン表記 |
| ダッシュボード新規作成 | ファイル名・title・h1すべて同一バージョン |

```html
<!-- ファイル: episode_database_dashboard_v6.html -->
<title>エピソードメインデータベース v6</title>
<h1>📊 エピソードメインデータベース v6</h1>
```

**チェックリスト（バージョンアップ時）:**
- [ ] ファイル名のバージョン番号
- [ ] `<title>`タグのバージョン番号
- [ ] `<h1>`タグのバージョン番号
- [ ] 関連ドキュメントの参照更新

---

## 🔄 セッション復元

Cursor再起動後: `前回のセッションを復元してください`

記録ファイル: `.session/current_session.json`, `.session/STATUS.md`

---

## 開発コマンド

```bash
ruff format src tests      # フォーマット
ruff check src tests --fix # リント
pytest tests --cov=src     # テスト
mypy src                   # 型チェック
```

---

## 注意事項

- コミット前にテスト実行
- 環境変数は`.env`, `.env.mcp`で管理
- センシティブ情報はコミット禁止

## リソース

- 詳細セットアップ: `docs/SETUP.md`
- MCP詳細: `docs/MCP_SERVERS.md`
- [MCP Documentation](https://modelcontextprotocol.io/)
