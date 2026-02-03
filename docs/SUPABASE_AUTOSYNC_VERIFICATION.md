# CSV→Supabase自動同期機能 検証レポート

## 結論: ✅ 正常稼働

実装は本番環境対応水準で、説明通りに正しく機能しています。

---

## 検証結果サマリー

| コンポーネント | ファイル | 状態 |
|--------------|---------|------|
| 自動同期コア | `backend/app/services/supabase_autosync.py` | ✅ 完備 |
| ファイル監視 | `backend/app/services/file_watcher.py` | ✅ 完備 |
| CSVローダー | `backend/app/utils/csv_loader.py` | ✅ 完備 |
| 移行スクリプト | `scripts/supabase/migrate_csv_to_supabase.py` | ✅ 完備 |
| 統合 | `backend/app/main.py` | ✅ 完備 |

---

## 詳細検証

### 1. 自動同期コア (`supabase_autosync.py`)

| 機能 | 実装 | 詳細 |
|------|------|------|
| 環境変数制御 | ✅ | `ENABLE_SUPABASE_CSV_AUTOSYNC=1` で有効化 |
| 必須変数チェック | ✅ | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` 未設定時は警告でスキップ |
| スロットリング | ✅ | デフォルト60秒間隔（`SUPABASE_AUTOSYNC_THROTTLE_SECONDS`） |
| 多重実行防止 | ✅ | `_sync_in_progress` + `threading.Lock()` |
| ファイル安定化待機 | ✅ | 10秒間監視、1秒安定で完了判定 |
| 変更検出 | ✅ | SHA256ハッシュ比較で重複同期防止 |
| ログ出力 | ✅ | 「Supabase自動同期: 開始」「Supabase自動同期: 完了」 |
| エラーハンドリング | ✅ | 包括的（環境変数、パッケージ、実行、例外） |
| セキュリティ | ✅ | 秘密情報をログに出力しない |

### 2. ファイル監視 (`file_watcher.py`)

| 機能 | 実装 | 詳細 |
|------|------|------|
| on_modified | ✅ | 通常のファイル編集検出 |
| on_created | ✅ | VSCode等の原子的保存対応 |
| on_moved | ✅ | Excel等の置換保存対応 |
| デバウンス | ✅ | 1秒間隔でchatteringフィルタ |
| シングルトン | ✅ | 重複起動防止 |

### 3. CSVローダー (`csv_loader.py`)

| 機能 | 実装 | 詳細 |
|------|------|------|
| 優先パス | ✅ | `preserved/data/MASTER_EPISODES_CURRENT.csv` |
| フォールバック | ✅ | ルート直下のCSVにも対応 |
| エンコーディング | ✅ | UTF-8-SIG（BOM対応） |

### 4. 移行スクリプト (`migrate_csv_to_supabase.py`)

| 機能 | 実装 | 詳細 |
|------|------|------|
| --csv オプション | ✅ | 任意のCSVパスを指定可能 |
| --batch-size | ✅ | デフォルト500件 |
| upsert | ✅ | `episode_id` 競合解決 |
| リトライ | ✅ | 3回、指数バックオフ（2-10秒） |
| エラーログ | ✅ | `src/reports/logs/migration_errors_*.json` |
| dry-run | ✅ | 実行確認モード |

### 5. main.py統合

| 機能 | 実装 | 詳細 |
|------|------|------|
| startup時 | ✅ | ファイル監視開始、コールバック登録 |
| CSV更新時 | ✅ | `maybe_schedule_supabase_autosync()` 呼び出し |
| shutdown時 | ✅ | ファイル監視停止 |

---

## 処理フロー図

```
CSV保存 (Excelなど)
    ↓
file_watcher (on_modified/on_created/on_moved)
    ↓ デバウンス1秒
on_csv_updated() [main.py]
    ↓
maybe_schedule_supabase_autosync()
    ├─ ENABLE_SUPABASE_CSV_AUTOSYNC チェック → 無効ならreturn
    ├─ 必須環境変数チェック → 未設定なら警告してreturn
    ├─ 多重実行チェック → 実行中なら pending フラグ設定
    └─ スロットリング → 60秒以内なら待機
         ↓ 別スレッド起動
    _run_supabase_autosync_worker()
         ├─ ファイル安定化待機 (max 10秒)
         ├─ SHA256チェック → 変更なしならreturn
         └─ migrate_csv_to_supabase.py 実行
              ├─ バッチ処理 (500件ずつ)
              └─ Supabase upsert (episode_id競合解決)
                   ↓
              ログ: 「Supabase自動同期: 完了」
```

---

## 設定値一覧

| 環境変数 | デフォルト | 説明 |
|---------|----------|------|
| `ENABLE_SUPABASE_CSV_AUTOSYNC` | false | 有効化フラグ |
| `SUPABASE_URL` | (必須) | Supabase URL |
| `SUPABASE_SERVICE_ROLE_KEY` | (必須) | サービスロールキー |
| `SUPABASE_AUTOSYNC_BATCH_SIZE` | 500 | バッチサイズ |
| `SUPABASE_AUTOSYNC_THROTTLE_SECONDS` | 60 | スロットリング間隔 |
| `SUPABASE_AUTOSYNC_STABLE_WAIT_SECONDS` | 10 | 安定化待機時間 |
| `SUPABASE_AUTOSYNC_STABLE_WINDOW_SECONDS` | 1 | 安定判定ウィンドウ |

---

## 注意事項

1. **upsertのみ**: CSVから行を削除してもSupabase側は削除されない
2. **文字コード**: UTF-8（BOM付き推奨）で保存必須
3. **環境変数**: `ENABLE_SUPABASE_CSV_AUTOSYNC=1` で明示的にONにする必要あり

---

## 動作確認方法

```bash
# 1. 環境変数設定（.envファイル）
ENABLE_SUPABASE_CSV_AUTOSYNC=1
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...

# 2. バックエンド起動
cd backend && python3 -m uvicorn app.main:app --reload --port 8000

# 3. CSV保存 → ログ確認
# 「Supabase自動同期: 開始」「Supabase自動同期: 完了」が出力されればOK
```

---

## 検証日時

- **検証日**: 2026-02-04
- **検証者**: Claude Code (Opus 4.5)
- **ステータス**: ✅ 本番環境使用可能
