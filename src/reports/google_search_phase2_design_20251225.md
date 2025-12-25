# Google検索API Phase 2 設計書

**作成日**: 2025-12-25
**目的**: Google検索ヒット数を追加してFame Score v3の精度向上
**方針**: キャッシュ優先・無料枠運用・コスト最小化

---

## 1. 現状分析

### 1.1 既存実装の確認

**実装済み機能**:
- Google Custom Search API統合 (`scripts/fame_score_v3/google_search.py`)
- SQLiteベースのDBキャッシュ (`data/cache/fame_score.db`)
- キャッシュ優先検索（同一person_idは再検索しない）
- Phase 2更新スクリプト (`scripts/update_fame_scores_phase2.py`)
- キャッシュ監視スクリプト (`scripts/monitor_search_cache.py`)

**設定ファイル**:
- APIキー: `/Users/admin/Documents/key/EP-Google-Count-API-Key.txt`
- CSE ID: `/Users/admin/Documents/key/EP_GOOGLE_COUNT_CSE_ID.txt`

**現在の状態**:
- 総人物数: **7,361人**
- Google検索済み: **93人** (1.3%)
- 未検索: **7,268人** (98.7%)

**無料枠制約**:
- Google Custom Search API: **100クエリ/日** (無料枠)
- 現在のレート制限: 1クエリ/秒

### 1.2 取得済み上位20人

| 順位 | 人物名 | Fame Score | Google Hits |
|------|--------|------------|-------------|
| 1 | ドナルド・トランプ | 789.06 | 4,360,000 |
| 2 | クリスティアーノ・ロナウド | 775.89 | 2,480,000 |
| 3 | マイケル・ジャクソン | 773.12 | 4,840,000 |
| 4 | エリザベス2世 | 763.74 | 2,740,000 |
| 5 | ケネディ | 758.79 | 3,760,000 |
| 6 | 習近平 | 758.75 | 32,700,000 |
| 7 | アインシュタイン | 758.52 | 3,290,000 |
| 8 | イーロン・マスク | 754.92 | 1,920,000 |
| 9 | ベニト・ムッソリーニ | 753.90 | 7,360,000 |
| 10 | ゴッホ | 753.04 | 9,870,000 |

### 1.3 未検索の上位50人（優先度高）

| 人物名 | Fame Score | 状態 |
|--------|------------|------|
| バッハ | 725.64 | 未検索 |
| ジェーン・オースティン | 725.04 | 未検索 |
| ゴルバチョフ | 724.72 | 未検索 |
| フリーダ・カーロ | 724.30 | 未検索 |
| トーマス・ジェファーソン | 724.15 | 未検索 |
| ... (他45人) | ... | 未検索 |

---

## 2. 設計方針

### 2.1 コア原則

1. **キャッシュファースト**: 既存のgoogle_hits値は絶対に再取得しない
2. **無料枠厳守**: 日次100クエリを超過しない（停止条件あり）
3. **スコア優先**: Fame Score降順で処理（効果の高い人物から）
4. **自動回復**: 日次上限到達時は翌日自動再開
5. **冪等性保証**: 何度実行しても同じ結果

### 2.2 処理フロー

```
1. DBから未検索リスト取得（fame_score_v3 DESC）
2. 日次クエリカウント確認（本日の消費量）
3. 残クエリ数を計算（100 - 本日の消費量）
4. 残クエリ分だけ処理
5. 上限到達 → 停止 & 翌日再開フラグ設定
```

---

## 3. データベーススキーマ設計

### 3.1 既存テーブル（変更なし）

**fame_cache** テーブル:
```sql
CREATE TABLE fame_cache (
    person_id TEXT PRIMARY KEY,
    person_name TEXT,
    wikidata_id TEXT,
    multi_lang_pv INTEGER,
    sitelinks INTEGER,
    inlinks INTEGER,
    pv_by_lang TEXT,
    fame_score_v3 REAL,
    fame_rank_v3 INTEGER,
    updated_at TEXT,
    google_hits INTEGER  -- 既に追加済み
);
```

### 3.2 新規テーブル: quota_tracker

**日次クエリカウントを管理**:

```sql
CREATE TABLE quota_tracker (
    date TEXT PRIMARY KEY,          -- YYYY-MM-DD
    total_queries INTEGER DEFAULT 0, -- 本日の総クエリ数
    quota_limit INTEGER DEFAULT 100, -- 日次上限
    last_updated TEXT,               -- ISO8601タイムスタンプ
    status TEXT DEFAULT 'active'     -- active | paused | completed
);
```

**運用ルール**:
- 日付が変わると自動的に新レコード作成（total_queries=0）
- `total_queries >= quota_limit` → status='paused'
- 全人物が取得完了 → status='completed'

### 3.3 新規テーブル: search_log

**個別検索履歴を記録**:

```sql
CREATE TABLE search_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    person_id TEXT NOT NULL,
    query TEXT NOT NULL,
    google_hits INTEGER,
    status TEXT,                -- success | error | cached
    error_message TEXT,
    timestamp TEXT,             -- ISO8601
    processing_time_ms INTEGER,
    FOREIGN KEY (person_id) REFERENCES fame_cache(person_id)
);
```

**用途**:
- デバッグ用のトレーサビリティ
- エラー率の監視
- キャッシュヒット率の分析

---

## 4. 無料枠ガード設計

### 4.1 日次上限管理

**実装クラス**: `GoogleQuotaManager`

```python
class GoogleQuotaManager:
    def __init__(self, db_path: Path):
        self.db_path = db_path
        self.daily_limit = 100

    def get_remaining_quota(self, date: str) -> int:
        """残りクエリ数を取得"""
        used = self._get_used_quota(date)
        return max(0, self.daily_limit - used)

    def can_make_request(self, date: str) -> bool:
        """リクエスト可能か判定"""
        return self.get_remaining_quota(date) > 0

    def increment_quota(self, date: str) -> None:
        """クエリカウントをインクリメント"""
        # quota_trackerテーブルを更新

    def get_status(self, date: str) -> str:
        """状態を取得（active/paused/completed）"""
```

### 4.2 停止条件

以下の場合に処理を停止:

1. **日次上限到達**: `total_queries >= 100`
2. **APIエラー429発生**: Rate Limit Exceeded
3. **手動停止フラグ**: `status='paused'`（緊急停止用）

### 4.3 再開条件

以下の場合に自動再開:

1. **日付が変わった**: 新しい日のquota_trackerレコード作成
2. **remaining_quota > 0**: 残クエリあり
3. **status='active'**: アクティブ状態

### 4.4 エラーハンドリング

| エラー種別 | 対応 |
|-----------|------|
| 429 Too Many Requests | 即座に停止、翌日再開 |
| 403 Forbidden | APIキー無効、管理者通知 |
| Timeout | リトライ（最大3回） |
| Network Error | リトライ（最大3回） |
| その他 | ログ記録、次の人物へ |

---

## 5. 処理キュー設計

### 5.1 優先度スコア計算

**未検索人物の処理順**:

```python
def calculate_priority(person: dict) -> float:
    """
    優先度 = fame_score_v3（降順）

    高スコア人物から順に処理することで、
    限られたクエリ数で最大効果を得る。
    """
    return person['fame_score_v3']
```

### 5.2 バッチ処理戦略

**バッチサイズ**: 日次残クエリ数（動的）

```python
# 疑似コード
remaining = quota_manager.get_remaining_quota(today)
batch = get_unsearched_persons(limit=remaining)

for person in batch:
    if not quota_manager.can_make_request(today):
        break  # 日次上限到達

    hits = get_google_search_hits(person.name, person.id)
    quota_manager.increment_quota(today)

    # キャッシュに保存
    save_google_hits_to_cache(person.id, hits)
```

### 5.3 進捗レポート

**daily_progress_report.json** を出力:

```json
{
    "date": "2025-12-25",
    "total_persons": 7361,
    "searched_total": 150,
    "searched_today": 57,
    "remaining_unsearched": 7211,
    "quota_used": 57,
    "quota_remaining": 43,
    "status": "active",
    "estimated_days_to_complete": 127
}
```

---

## 6. スケジューラ設計

### 6.1 実行モード

**モードA: 手動実行**（開発・テスト用）

```bash
# ドライラン（実際のAPI呼び出しなし）
python scripts/update_fame_scores_phase2.py --dry-run

# 本番実行（日次上限まで）
python scripts/update_fame_scores_phase2.py --execute

# 最大10クエリに制限
python scripts/update_fame_scores_phase2.py --execute --max-queries 10
```

**モードB: 自動実行**（cron/launchd）

```bash
# 毎日3:00に自動実行（日次上限まで）
0 3 * * * cd /path/to/project && python scripts/update_fame_scores_phase2.py --execute --auto
```

### 6.2 自動実行フラグ

`--auto` フラグ時の動作:

1. 日次上限到達 → 警告なしで正常終了（exit 0）
2. 全完了済み → 正常終了、ログに記録
3. エラー発生 → ログ記録、exit 1（監視システム通知）

### 6.3 スケジューラスクリプト

**scripts/manage_phase2_scheduler.sh** を新規作成:

```bash
#!/bin/bash
# Phase 2 Google検索スケジューラ管理

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

case "$1" in
    start)
        # launchdで自動実行開始
        launchctl load ~/Library/LaunchAgents/com.aiuelab.hourglass.phase2.plist
        ;;
    stop)
        # 自動実行停止
        launchctl unload ~/Library/LaunchAgents/com.aiuelab.hourglass.phase2.plist
        ;;
    status)
        # 状態確認
        python "$PROJECT_ROOT/scripts/check_phase2_status.py"
        ;;
    run-once)
        # 手動実行（1回のみ）
        python "$PROJECT_ROOT/scripts/update_fame_scores_phase2.py" --execute
        ;;
esac
```

---

## 7. 監視・アラート設計

### 7.1 監視対象メトリクス

| メトリクス | 閾値 | アクション |
|-----------|------|-----------|
| エラー率 | >10% | 警告ログ出力 |
| API応答時間 | >5秒 | 警告ログ出力 |
| 日次消費率 | 100% | 停止、翌日再開 |
| 連続エラー | 3回 | 該当人物スキップ |

### 7.2 監視コマンド

**既存スクリプト**: `scripts/monitor_search_cache.py`

実行例:
```bash
python scripts/monitor_search_cache.py
```

出力:
```
キャッシュカバレッジ: 150/7361 (2.0%)
未取得: 7211人

未取得トップ5:
  1. バッハ (スコア: 725.64)
  2. ジェーン・オースティン (スコア: 725.04)
  ...

セッション統計:
  キャッシュヒット: 45
  API呼び出し: 55
  APIエラー: 2

レポート保存: src/reports/logs/cache_monitor_20251225_120000.json
```

### 7.3 アラートルール

**critical**: API無効化、認証エラー
**warning**: エラー率10%超過、連続エラー3回
**info**: 日次上限到達（正常動作）

---

## 8. 実装タスク

### 8.1 Phase A: DB拡張（承認後実施）

- [ ] `quota_tracker` テーブル作成
- [ ] `search_log` テーブル作成
- [ ] マイグレーションスクリプト作成

### 8.2 Phase B: クォータ管理実装

- [ ] `GoogleQuotaManager` クラス実装
- [ ] 日次上限チェック機能
- [ ] 停止・再開ロジック

### 8.3 Phase C: バッチ処理改善

- [ ] `update_fame_scores_phase2.py` にクォータ管理統合
- [ ] `--auto` フラグ追加
- [ ] 進捗レポート出力

### 8.4 Phase D: スケジューラ構築

- [ ] `manage_phase2_scheduler.sh` 作成
- [ ] launchd設定ファイル作成
- [ ] `check_phase2_status.py` 作成

### 8.5 Phase E: 監視強化

- [ ] `monitor_search_cache.py` にクォータ情報追加
- [ ] 日次レポート自動生成
- [ ] エラー通知機能

### 8.6 Phase F: テスト

- [ ] ユニットテスト（quota_manager）
- [ ] 統合テスト（dry-run）
- [ ] 本番テスト（max-queries=10）

---

## 9. 見積もり

### 9.1 完了予測

**現状**:
- 未検索: 7,268人
- 日次処理可能: 100人（無料枠上限）

**予測**:
- **完了まで約73日** (7,268 / 100)
- 開始日: 2025-12-26（承認後）
- 完了予定: 2026-03-09

### 9.2 コスト分析

**無料枠運用**:
- Google Custom Search API: $0/月（100クエリ/日以内）

**有料化した場合**:
- 追加クエリ: $5/1000クエリ
- 全7,268人を1日で完了: $36.34

**推奨**: 無料枠運用（コスト$0、73日で完了）

### 9.3 リスク評価

| リスク | 確率 | 影響 | 対策 |
|--------|------|------|------|
| API仕様変更 | 低 | 高 | 公式ドキュメント定期確認 |
| 無料枠廃止 | 低 | 中 | Bing APIフォールバック実装済み |
| レート制限誤検知 | 中 | 低 | quota_tracker精度向上 |
| 長期実行の保守負荷 | 中 | 低 | 自動化・監視で対応 |

---

## 10. 承認事項

### 10.1 実装前確認

以下を確認してから実装開始してください:

1. **設計方針の承認**: キャッシュ優先・無料枠運用でOK？
2. **完了期間の承認**: 73日かけて無料で完了 vs 有料で即日完了
3. **DB拡張の承認**: quota_tracker/search_logテーブル追加OK？
4. **自動実行の承認**: launchdで毎日自動実行OK？

### 10.2 次のステップ

**承認後**:
1. Phase A（DB拡張）から順次実装
2. テスト実行（--dry-run → --max-queries 10）
3. 本番実行開始（--execute --auto）
4. 日次監視レポート確認

---

## 11. 参考資料

**関連ファイル**:
- `/Users/admin/Documents/AIUELAB/001-final-hourglass/scripts/fame_score_v3/google_search.py`
- `/Users/admin/Documents/AIUELAB/001-final-hourglass/scripts/update_fame_scores_phase2.py`
- `/Users/admin/Documents/AIUELAB/001-final-hourglass/scripts/monitor_search_cache.py`
- `/Users/admin/Documents/AIUELAB/001-final-hourglass/data/cache/fame_score.db`

**APIドキュメント**:
- Google Custom Search JSON API: https://developers.google.com/custom-search/v1/overview
- 無料枠: 100クエリ/日

---

**END OF DESIGN DOCUMENT**
