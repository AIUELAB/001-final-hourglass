# Google検索API Phase 2 実装サマリー

**日時**: 2025-12-25
**ステータス**: 設計完了・承認待ち

---

## タスク完了状況

### A. 現状調査 ✅

**実施内容**:
1. Google検索の現行実装確認完了
2. キャッシュDB構造解析完了
3. 未検索件数レポート完了

**調査結果**:
- 総人物数: 7,361人
- Google検索済み: 93人（1.3%）
- **未検索: 7,268人（98.7%）**

### B. 設計提案 ✅

**成果物**: `/Users/admin/Documents/AIUELAB/001-final-hourglass/src/reports/google_search_phase2_design_20251225.md`

**設計ハイライト**:

#### 1. DBキャッシュスキーマ

**新規テーブル2つ**:
- `quota_tracker`: 日次クエリ数管理（100クエリ/日上限）
- `search_log`: 検索履歴トレーサビリティ

#### 2. 無料枠ガード設計

**停止条件**:
- 日次上限到達（total_queries >= 100）
- APIエラー429発生
- 手動停止フラグ

**再開条件**:
- 日付変更（自動的に新レコード作成）
- 残クエリ > 0
- status='active'

#### 3. 処理キュー設計

**優先順**:
- Fame Score v3降順（スコア高い人物から）
- 未検索のみ（google_hits IS NULL）
- バッチサイズ = 残クエリ数（動的調整）

#### 4. 完了予測

**無料枠運用**:
- 完了まで: **約73日**
- コスト: **$0**
- 開始予定: 2025-12-26
- 完了予定: 2026-03-09

**有料化した場合**:
- 完了まで: 1日
- コスト: 約$36
- 推奨: **無料枠運用**（コスト優先）

### C. 実装準備 ✅

**作成済みファイル**:
1. 設計書: `src/reports/google_search_phase2_design_20251225.md`
2. サマリー: `src/reports/google_search_phase2_summary_20251225.md`（本ファイル）

**承認待ち項目**:
1. 設計方針（キャッシュ優先・無料枠運用）
2. 完了期間（73日 vs 有料即日）
3. DB拡張（quota_tracker/search_log追加）
4. 自動実行（launchdで毎日3:00実行）

---

## 既存実装の分析

### キャッシュ機構（すでに実装済み）

**優れた点**:
- ✅ SQLiteベースのDBキャッシュ
- ✅ person_id単位の重複回避
- ✅ キャッシュヒット率の統計収集
- ✅ --force-refresh オプションあり

**コード例** (`scripts/fame_score_v3/google_search.py`):
```python
def get_google_search_hits(
    query: str,
    person_id: Optional[str] = None,
    force_refresh: bool = False,
):
    # キャッシュチェック（force_refreshでない場合）
    if person_id and not force_refresh:
        cached = get_cached_google_hits(person_id)
        if cached is not None:
            return cached  # キャッシュヒット

    # API呼び出し
    ...
```

### レート制限（すでに実装済み）

**現行設定**:
```python
REQUEST_INTERVAL = 1.0  # 1 req/sec
```

**改善案**:
- 日次上限管理を追加（quota_tracker）
- エラー429検知時の自動停止

### 統計収集（すでに実装済み）

**現行メトリクス**:
```python
_stats = {
    "cache_hits": 0,
    "api_calls": 0,
    "api_errors": 0,
}
```

**改善案**:
- 日次集計への拡張
- search_logテーブルで永続化

---

## 未検索人物の分析

### 上位未検索（Fame Score順）

| 順位 | 人物名 | Fame Score | 優先度 |
|------|--------|------------|--------|
| 21 | バッハ | 725.64 | 最高 |
| 22 | ジェーン・オースティン | 725.04 | 最高 |
| 23 | ゴルバチョフ | 724.72 | 最高 |
| 24 | フリーダ・カーロ | 724.30 | 最高 |
| 25 | トーマス・ジェファーソン | 724.15 | 最高 |
| 26 | シャルル・ド・ゴール | 723.89 | 最高 |
| 27 | 釈迦 | 723.11 | 最高 |
| 28 | チャールズ・ディケンズ | 723.08 | 最高 |
| 29 | トルストイ | 723.03 | 最高 |
| 30 | アリストテレス | 722.89 | 最高 |

**処理戦略**:
- 初日: 上位100人（バッハ〜）
- 2日目: 101〜200人
- ...
- 73日目: 最後の68人

---

## 技術的考慮事項

### Google Custom Search API仕様

**無料枠制限**:
- クエリ数: 100/日
- レート制限: 公式ドキュメントに明記なし（保守的に1 req/sec推奨）
- タイムアウト: 10秒

**エラーコード**:
- 200: 成功
- 429: Too Many Requests（レート制限超過）
- 403: Forbidden（APIキー無効）

**返却データ**:
```json
{
  "searchInformation": {
    "totalResults": "4360000"  // ←この値を使用
  }
}
```

### DBトランザクション設計

**ACID保証**:
```python
# 疑似コード
conn = sqlite3.connect(CACHE_DB_PATH)
try:
    # 1. クエリカウント確認
    if not can_make_request():
        return  # 上限到達

    # 2. API呼び出し
    hits = call_google_api(query)

    # 3. トランザクション開始
    conn.execute("BEGIN")

    # 4. キャッシュ保存
    conn.execute("UPDATE fame_cache SET google_hits = ? WHERE person_id = ?", (hits, person_id))

    # 5. クォータ更新
    conn.execute("UPDATE quota_tracker SET total_queries = total_queries + 1 WHERE date = ?", (today,))

    # 6. ログ記録
    conn.execute("INSERT INTO search_log (...) VALUES (...)")

    # 7. コミット
    conn.commit()
except Exception as e:
    conn.rollback()
    raise
```

### エラーハンドリング階層

**Level 1: API呼び出し**
- Timeout → リトライ3回
- Network Error → リトライ3回
- 429 → 即座に停止

**Level 2: バッチ処理**
- 個別エラー → 次の人物へスキップ
- 連続エラー3回 → バッチ停止

**Level 3: スケジューラ**
- 日次上限到達 → 正常終了（翌日再開）
- 致命的エラー → exit 1（監視システム通知）

---

## 実装フェーズ

### Phase 1: DB拡張（0.5日）

**タスク**:
- [ ] `scripts/migrations/add_quota_tables.py` 作成
- [ ] quota_tracker テーブル作成
- [ ] search_log テーブル作成
- [ ] 既存データの整合性確認

**検証**:
```bash
sqlite3 data/cache/fame_score.db ".schema quota_tracker"
sqlite3 data/cache/fame_score.db ".schema search_log"
```

### Phase 2: クォータ管理（1日）

**タスク**:
- [ ] `scripts/fame_score_v3/quota_manager.py` 作成
- [ ] GoogleQuotaManager クラス実装
- [ ] ユニットテスト作成
- [ ] 統合テスト

**コード構造**:
```python
class GoogleQuotaManager:
    def get_remaining_quota(self, date: str) -> int
    def can_make_request(self, date: str) -> bool
    def increment_quota(self, date: str) -> None
    def get_status(self, date: str) -> str
```

### Phase 3: バッチ処理改善（1日）

**タスク**:
- [ ] `update_fame_scores_phase2.py` 改修
- [ ] quota_manager統合
- [ ] --auto フラグ追加
- [ ] 進捗レポート出力

**変更箇所**:
```python
# Before
def run_execute(max_queries: int = 0):
    persons = get_persons_without_google_hits(conn)
    if max_queries > 0:
        persons = persons[:max_queries]

# After
def run_execute(max_queries: int = 0, auto: bool = False):
    quota_mgr = GoogleQuotaManager(CACHE_DB_PATH)
    remaining = quota_mgr.get_remaining_quota(today)

    limit = min(remaining, max_queries) if max_queries > 0 else remaining
    persons = get_persons_without_google_hits(conn)[:limit]
```

### Phase 4: スケジューラ構築（0.5日）

**タスク**:
- [ ] `scripts/manage_phase2_scheduler.sh` 作成
- [ ] `scripts/check_phase2_status.py` 作成
- [ ] launchd設定ファイル作成
- [ ] 動作確認

**launchdパス**:
```
~/Library/LaunchAgents/com.aiuelab.hourglass.phase2.plist
```

### Phase 5: 監視強化（0.5日）

**タスク**:
- [ ] `monitor_search_cache.py` 改修
- [ ] quota_tracker情報追加
- [ ] 日次レポート自動生成

**出力例**:
```
=== Google検索キャッシュ監視 ===

キャッシュカバレッジ: 193/7361 (2.6%)
未取得: 7168人

今日のクォータ:
  使用: 57/100 (57%)
  残り: 43
  ステータス: active

未取得トップ5: ...
```

### Phase 6: テスト（1日）

**テストケース**:
1. ユニットテスト（quota_manager）
2. ドライラン（--dry-run）
3. 少量テスト（--max-queries 5）
4. 日次上限テスト（--max-queries 100）
5. 自動再開テスト（日付またぎ）

---

## リスク管理

### 技術リスク

| リスク | 確率 | 影響度 | 対策 |
|--------|------|--------|------|
| API仕様変更 | 低 | 高 | 定期的な公式ドキュメント確認 |
| 無料枠廃止 | 低 | 中 | Bing APIフォールバック実装済み |
| クォータ計算誤差 | 中 | 低 | search_logで実績確認 |
| DB破損 | 低 | 高 | 日次バックアップ推奨 |

### 運用リスク

| リスク | 確率 | 影響度 | 対策 |
|--------|------|--------|------|
| 73日間の保守負荷 | 中 | 低 | 完全自動化・監視システム |
| マシン停止 | 中 | 低 | launchdで自動再開 |
| APIキー漏洩 | 低 | 高 | 環境変数・ファイル権限厳格化 |

---

## 次のアクション

### 承認依頼事項

**設計承認**: 以下の4点について承認をお願いします

1. **設計方針**: キャッシュ優先・無料枠運用でOK？
2. **完了期間**: 73日で無料完了 vs 有料で即日完了（どちらを選択？）
3. **DB拡張**: quota_tracker/search_logテーブル追加OK？
4. **自動実行**: launchdで毎日3:00に自動実行OK？

### 承認後のステップ

**実装フロー**:
```
1. DB拡張（0.5日）
   ↓
2. quota_manager実装（1日）
   ↓
3. バッチ処理改善（1日）
   ↓
4. スケジューラ構築（0.5日）
   ↓
5. 監視強化（0.5日）
   ↓
6. テスト（1日）
   ↓
7. 本番稼働開始
```

**合計工数**: 約4.5日

---

## 参考情報

### 関連ファイルパス

**実装済み**:
- `/Users/admin/Documents/AIUELAB/001-final-hourglass/scripts/fame_score_v3/google_search.py`
- `/Users/admin/Documents/AIUELAB/001-final-hourglass/scripts/update_fame_scores_phase2.py`
- `/Users/admin/Documents/AIUELAB/001-final-hourglass/scripts/monitor_search_cache.py`
- `/Users/admin/Documents/AIUELAB/001-final-hourglass/data/cache/fame_score.db`

**新規作成予定**:
- `scripts/fame_score_v3/quota_manager.py`
- `scripts/migrations/add_quota_tables.py`
- `scripts/check_phase2_status.py`
- `scripts/manage_phase2_scheduler.sh`

**設定ファイル**:
- APIキー: `/Users/admin/Documents/key/EP-Google-Count-API-Key.txt`
- CSE ID: `/Users/admin/Documents/key/EP_GOOGLE_COUNT_CSE_ID.txt`

### 外部リンク

**Google Custom Search API**:
- 公式ドキュメント: https://developers.google.com/custom-search/v1/overview
- 無料枠: https://developers.google.com/custom-search/v1/overview#Pricing

---

**END OF SUMMARY**
