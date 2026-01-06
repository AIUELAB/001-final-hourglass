# スコア整合性管理ワークフロー

## 概要

新しいスコアを追加/更新したときに、全エピソードの欠損スコアを埋め、
v10ダッシュボードに正しく表示される状態を保証するための標準運用フロー。

---

## スコア列一覧とスケール

| 列名 | スケール | 種別 | 必須 |
|------|---------|------|------|
| 記憶性スコア | 0-10 | 7軸 | ✓ |
| 共感性スコア | 0-10 | 7軸 | ✓ |
| 意外性スコア | 0-10 | 7軸 | ✓ |
| 生成品質スコア | 0-10 | 7軸 | ✓ |
| 教育的価値 | 0-10 | 7軸 | ✓ |
| ストーリー品質 | 0-10 | 7軸 | ✓ |
| 事実密度 | 0-10 | 7軸 | ✓ |
| composite_score | 0-70 | 派生 | ✓ |
| composite_score_5axis | 0-50 | 派生 | |
| episode_fame_v6 | 0-200 | Fame | ✓ |
| episode_fame_tier_v6 | 1-5 | Tier | ✓ |
| fame_score_v3 | 0-900 | Fame | ✓ |
| fame_score_japan | 0-1000 | Fame | |
| celebrity_score_v2 | 0-1000 | Celebrity | ✓ |
| celebrity_rank_v2 | 1-N | Rank | ✓ |
| super_total_score | 0-1000000 | Super | ✓ |

---

## 標準運用フロー

### 1. 新スコア追加時

```bash
# Step 1: 欠損検出 (dry-run)
python scripts/score/score_integrity_manager.py --detect

# Step 2: 欠損埋め (dry-run)
python scripts/score/score_integrity_manager.py --dry-run

# Step 3: 実行
python scripts/score/score_integrity_manager.py --execute

# Step 4: ダッシュボード更新
python scripts/update_dashboard_v10.py

# Step 5: 確認
open http://localhost:8088/episode_database_dashboard_v10.html
```

### 2. 日次バッチ

```bash
# 完全パイプライン
python scripts/score/score_integrity_manager.py --execute
python scripts/update_dashboard_v10.py
```

### 3. 個別スコア再計算

```bash
# 7軸スコア
python scripts/score/fill_missing_seven_axis.py

# Episode Fame v6
python scripts/calculate_episode_fame_v6.py --execute

# Celebrity Score v2
python scripts/update_celebrity_score_v2.py --execute

# Super Total Score
python scripts/recalculate_super_total_v1.2.py

# Fame Score v3 (Wikidata API使用)
python scripts/update_fame_scores_v3.py --execute
```

---

## 欠損理由と対処法

| 列 | 理由 | 対処法 |
|----|------|--------|
| fame_score_japan | 日本以外の人物 | 正常 (0のまま) |
| super_total_score | 品質ゲート未達 | 事実密度/生成品質 < 6.0 → 0 |
| quality_score | レガシー列 | 無視可 |

### 品質ゲート

super_total_score は以下を満たさないと0になる:
- 事実密度 ≥ 6.0
- 生成品質スコア ≥ 6.0

---

## 検証コマンド

```bash
# 欠損検出のみ
python scripts/score/score_integrity_manager.py --detect

# 検証のみ
python scripts/score/score_integrity_manager.py --validate

# テスト実行
python -m pytest tests/test_score_integrity.py -v
```

---

## レポート出力

実行ごとに `src/reports/logs/score_integrity_YYYYMMDD_HHMMSS.json` に出力:

```json
{
  "timestamp": "2026-01-06T15:51:13",
  "dry_run": false,
  "detection": {
    "記憶性スコア": {"missing": 0, "filled": 10518, "rate": 100.0, "status": "ok"},
    ...
  },
  "fill": {
    "7axis": 0,
    "composite": 587,
    "fame_tier": 286,
    ...
  },
  "validation": {
    "range_violations": {},
    "nan_inf_count": 0
  },
  "errors": []
}
```

---

## EPUP再発防止チェックリスト

- [ ] 品質ゲート（事実密度/生成品質 ≥ 6.0）を維持
- [ ] 欠損を「適当なデフォルト値」で埋めない
- [ ] ヒューリスティック計算は暫定値であり、LLM再評価が推奨
- [ ] 範囲外値が発生した場合は調査

---

## ファイル構成

```
scripts/score/
├── score_integrity_manager.py  # メインスクリプト
├── fill_all_missing_scores.py  # 7軸埋め (既存)
├── fill_missing_seven_axis.py  # 7軸専用 (既存)
├── recalculate_all_scores.py   # 全再計算 (既存)
└── ...

tests/
└── test_score_integrity.py     # 自動テスト

src/reports/logs/
└── score_integrity_*.json      # レポート出力
```

---

## 関連ドキュメント

- [CLAUDE.md](../CLAUDE.md) - 全体ガイド
- [docs/EPISODE_DB_STARTUP_GUIDE.md](EPISODE_DB_STARTUP_GUIDE.md) - ダッシュボードガイド
