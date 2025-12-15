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

## 🔴 道具名・アイテム名誤登録防止ルール（EPUP）

**人物名として登録してはいけない名前パターン**

### 検出パターン

| パターン | 例 | 判定 |
|---------|-----|------|
| **道具接尾辞** | ○○ギプス、○○マシン、○○装置 | ❌ 道具名 |
| **物品接尾辞** | ○○アイテム、○○グッズ、○○ツール | ❌ 物品名 |
| **機械接尾辞** | ○○ロボット、○○メカ、○○システム | ❌ 機械名 |
| **作品由来** | 秘密道具、必殺技、魔法アイテム | ❌ 架空アイテム |

### 具体例（ブラックリスト）

| 誤登録名 | 正体 | 理由 |
|---------|------|------|
| 大リーグ養成ギプス | ドラえもんの秘密道具 | 道具名であり人物ではない |

### 検出ツール

**事前チェック**:
```bash
# 人物名バリデーション
python3 -c "
from src.validators.person_name_validator import validate_before_episode_generation
is_valid, message, fix = validate_before_episode_generation('大リーグ養成ギプス', 'REAL')
print(f'{message}')
"
```

**事後検出**:
```bash
# ブラックリスト照合
grep -f config/blacklist_names.txt preserved/data/MASTER_EPISODES_CURRENT.csv
```

### チェックリスト（エピソード生成時）

- [ ] 人物名に道具接尾辞（ギプス、マシン等）が含まれていないか
- [ ] 人物名が架空作品の固有名詞ではないか
- [ ] Wikipedia記事が実在するか（可能な場合）
- [ ] ブラックリストに該当しないか

---

## 🔢 年齢境界違反エピソード検出ルール（EPUP）

**エピソードは必ず birth_year ~ death_year（または現在年）の範囲内で生成する**

**禁止される年齢設定**:
- 人物の没年を超えた年齢（例：70歳で死去した人の71歳エピソード）
- 人物がまだ到達していない年齢（例：現在15歳の人の20歳エピソード）

**エピソード本文に絶対書かないメタ的表現**:
- 「すでにこの世を去って」「亡くなった後」「死去した後」
- 「未来のこと」「まだ到達していない」「まだ到来していない」
- 「代わりに〜歳のエピソード」「別の年齢で生成」
- 「年齢設定を変更」「申し訳ありませんが」「生成できません」

### メタデータベースの年齢境界違反検出

**CSVメタデータの矛盾がメタ表現を誘発する**

CSVのメタデータ（birth_year, death_year, award_year, age）に以下の矛盾がある場合、LLMがメタ表現を生成するリスクが高い：

| 検出条件 | 例 | リスク |
|---------|-----|-------|
| award_year > death_year | 伊能忠敬（死1818、業績1821） | 「すでにこの世を去って」生成 |
| age > (death_year - birth_year) | 享年73歳の人の75歳エピソード | 「亡くなった後」生成 |
| age > (current_year - birth_year) | 現在15歳の人の20歳エピソード | 「未来のこと」生成 |

**2段階防御アーキテクチャ：**
1. **予防（Prevention）:** `generate_senior_episodes.py` Lines 218-226 で生成時にブロック
2. **検出（Detection）:** `detect_age_boundary_violations.py` で事後検出

**処理方針：**
1. 検出された矛盾エピソードは削除（再生成しない）
2. テンプレートデータの修正（award_year を削除 or 正確な年に変更）
3. 生成時の予防コードを維持

**検出・修正ツール**:
- 本文パターン検出: `scripts/detect_problematic_phase8_episodes.py`
- メタデータ矛盾検出: `scripts/detect_age_boundary_violations.py` ⭐ NEW
- 削除: `scripts/delete_problematic_phase8.py`

**チェックリスト（エピソード生成時）**:
- [ ] birth_year/death_yearが利用可能か確認
- [ ] 選択年齢が有効範囲内か確認
- [ ] メタ的な年齢言及が含まれていないか確認

---

## 🔤 人物名表記ルール（名寄せ統合）

**正規表記（canonical name）を使用すること**

| 別名・通称 | 正規表記 | 理由 |
|-----------|---------|------|
| 山中教授 | 山中伸弥 | 個人名を明示 |
| マンデラ | ネルソン・マンデラ | フルネームで統一 |
| ホリエモン | 堀江貴文 | 本名を使用 |

**ルール**:
- エピソード生成時は**必ず正規表記**を使用
- 別名・通称は`ALIAS_KEYWORDS`に登録済み
- バリデーション: `PersonNameValidator`が自動検出
- 正規化: `normalize_person_names.py`が自動修正

**追加方法**:
新しい別名を発見した場合は以下に追加:
1. `scripts/normalize_person_names.py` - `ALIAS_KEYWORDS`辞書
2. `src/validators/person_name_validator.py` - `_check_alias_usage`メソッド（自動参照）

**検証コマンド**:
```bash
# 人物名バリデーション
python3 -c "
from src.validators.person_name_validator import get_validator
validator = get_validator()
issues = validator.validate('山中教授')
for issue in issues:
    print(f'{issue.severity.value}: {issue.message}')
"
```

### 実装パターン（normalize_person_names.py）

| パターン | 入力例 | 正規化後 | 信頼度 |
|---------|--------|---------|--------|
| **ALIAS** | 山中教授 | 山中伸弥 | 1.0 |
| **DESCRIPTION_PREFIX** | 日本人実業家の稲盛和夫 | 稲盛和夫 | 0.95 |
| **AFFILIATION_TITLE** | 楽天創業者三木谷浩史 | 三木谷浩史 | 0.95 |
| **ORG_PERSON** | 辻調 辻芳樹 | 辻芳樹 | 0.90 |
| **OCCUPATION_PREFIX** | 声優野沢雅子 | 野沢雅子 | 0.90 |
| **GROUP_MEMBER** | 乃木坂46齋藤飛鳥 | 齋藤飛鳥 | 0.95 |
| **GROUP_PREFIX** | AKB48指原莉乃 | 指原莉乃 | 0.95 |
| **RIKISHI_SHIKONA** | 千代の富士貢 | 千代の富士 | 0.90 |
| **ORDINAL_ARTIST** | 十四代酒井田柿右衛門 | 酒井田柿右衛門 | 0.85 |

### 使用方法

**検出のみ（ドライラン）**:
```bash
python scripts/normalize_person_names.py --dry-run
```

**自動修正実行**:
```bash
python scripts/normalize_person_names.py --execute --min-confidence 0.85
```

**特定パターンのみ検出**:
```bash
python scripts/normalize_person_names.py --dry-run --pattern ALIAS
```

**結果の確認**:
- レポート: `reports/name_normalization_dryrun_*.json`
- 自動修正: 信頼度 ≥ 0.85 かつ要レビューフラグなし
- 要確認: 信頼度 < 0.85 または複雑なパターン

**詳細**: `docs/PERSON_NAME_VALIDATION_WORKFLOW.md`（全9パターンの詳細説明）

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

**🔴 重要：バージョンアップはユーザーからの明示的な指示があった時のみ実行**

1. **ユーザーからの明示的な指示を待つ**
2. preserved/ に新バージョンを作成（例: v8.html）
3. 旧バージョンを archive/dashboards/ に移動
4. ファイル名・title・h1のバージョン番号を同期

### ダッシュボードアクセス方法

**✅ 正しい方法（HTTPサーバー経由）：**

```bash
# プロジェクトルートで実行
# プロジェクト定義のポート範囲: 8000-8082
python -m http.server 8082  # ダッシュボード用推奨ポート

# 起動メッセージで実際のポート番号を確認
# 例: Serving HTTP on 0.0.0.0 port 8082 (http://0.0.0.0:8082/) ...

# ブラウザでアクセス
http://localhost:8082/preserved/episode_database_dashboard_v8.html
```

**プロジェクト定義のポート範囲：**

| ポート | 用途 | 優先度 |
|--------|------|--------|
| **8082** | HTTPサーバー（ダッシュボード配信） | ✅ 推奨 |
| **8081** | HTTPサーバー代替 | ⭕ 推奨 |
| **8080** | HTTPサーバー代替 | ⭕ 推奨 |
| **8000** | FastAPI バックエンド | ⚠️ API用に予約 |

**注意：** 8000番はFastAPI用に予約されているため避ける。ダッシュボードは8082番を使用。

**詳細参照：** `docs/EPISODE_DB_STARTUP_GUIDE.md` - ポート番号の詳細仕様

**❌ 禁止方法（file://プロトコル）：**

```text
file:///Users/.../episode_database_dashboard_v8.html
→ CORS制限によりCSVファイル読み込み不可
```

### 整合性チェック（定期実行推奨）

```bash
python scripts/check_single_dashboard.py
```

チェック項目:
1. preserved/ に正規ダッシュボードが1つのみ存在
2. ルート直下にダッシュボードなし
3. archive/dashboards/ の存在確認

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
