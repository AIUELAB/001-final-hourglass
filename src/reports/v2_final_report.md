# Celebrity Score v2 - 最終レポート

**作成日時**: 2025-12-26 01:12
**ステータス**: 完了

---

## 1. 現状調査結果（v1の根拠、経路、課題）

### v1（fame_score_v3）の構成
- **計算式**: `0.50*PV + 0.30*sitelinks + 0.20*inlinks` × 1000
- **保存先**: CSV (`fame_score_v3`, `fame_rank_v3`) + SQLite (`fame_cache`)
- **表示**: ダッシュボード、API

### 課題
| 課題 | 詳細 | v2での対策 |
|------|------|-----------|
| 長期バイアス | Wikidataは長期評価に偏る | エピソード数・LLM品質を追加 |
| 政治家過剰評価 | 報道露出で上位独占 | カテゴリ上限700 |
| 同名曖昧性 | 短名で誤マッチ | 確信度<0.8で半減 |

---

## 2. v2設計（採用案）

### 計算式（案A改: トレンド+品質重視型）

```
v2 = (
    0.30 * log_normalize(multi_lang_pv) +
    0.18 * linear_normalize(sitelinks) +
    0.12 * log_normalize(inlinks) +
    0.18 * log_normalize(google_hits) +
    0.10 * sqrt_normalize(episode_count) +
    0.12 * linear_normalize(llm_quality)
) × 1000
```

### カテゴリ上限
- 政治・社会: 700
- アニメ・漫画・ゲーム: 700

### 同名曖昧性
- 確信度 < 0.8: スコア半減

---

## 3. 実装結果

### 変更点
| ファイル | 変更内容 |
|---------|---------|
| `scripts/fame_score_v3/scorer_v2.py` | v2計算ロジック |
| `scripts/update_celebrity_score_v2.py` | 算出パイプライン |
| `scripts/validate_celebrity_score_v2.py` | 品質検証 |
| `tests/test_celebrity_score_v2.py` | 回帰テスト（11件） |

### 保存先
- CSV: `celebrity_score_v2`, `celebrity_rank_v2`
- DB: `fame_cache`テーブルに4カラム追加

### 実行手順
```bash
# ドライラン
python scripts/update_celebrity_score_v2.py --dry-run

# 本番実行
python scripts/update_celebrity_score_v2.py --execute

# 品質検証
python scripts/validate_celebrity_score_v2.py

# テスト
pytest tests/test_celebrity_score_v2.py
```

### ロールバック
```bash
# DBからv2カラムを削除
sqlite3 data/cache/fame_score.db "
  UPDATE fame_cache SET celebrity_score_v2 = NULL, celebrity_rank_v2 = NULL;
"

# CSVは git checkout で復元
git checkout preserved/data/MASTER_EPISODES_CURRENT.csv
```

---

## 4. 品質ゲート・監視・テスト（EPUP）

### 品質ゲート
| ゲート | 条件 | 対応 |
|--------|------|------|
| スコア範囲 | 0-1000 | 自動クリップ |
| カテゴリ上限 | 政治家≤700 | 上限適用 |
| 同名曖昧性 | 確信度<0.8 | スコア半減 |

### 監視
- `scripts/validate_celebrity_score_v2.py` を定期実行
- レポート: `src/reports/v2_validation_*.json`

### 回帰テスト（11件）
| カテゴリ | テスト数 | 内容 |
|---------|---------|------|
| スコア範囲 | 3 | 0-1000制約 |
| カテゴリ上限 | 3 | 政治家700、アニメ700 |
| 曖昧性ペナルティ | 2 | 0.8境界値 |
| 決定性 | 1 | 同入力同出力 |
| 順位計算 | 2 | 降順、同点同順位 |

---

## 5. Top10結果

| 順位 | 人物 | スコア | カテゴリ |
|------|------|--------|----------|
| 1 | アインシュタイン | 836.8 | 科学・技術 |
| 2 | パブロ・ピカソ | 825.7 | 芸術・文化 |
| 3 | マイケル・ジャクソン | 820.0 | 音楽 |
| 4 | エルヴィス・プレスリー | 817.0 | 音楽 |
| 5 | クリスティアーノ・ロナウド | 811.5 | スポーツ |
| 6 | 黒澤明 | 811.2 | 映画・演劇 |
| 7 | イーロン・マスク | 805.1 | 科学・技術 |
| 8 | スティーブ・ジョブズ | 800.5 | 科学・技術 |
| 9 | バッハ | 797.0 | 音楽 |
| 10 | エリザベス2世 | 796.9 | 歴史 |

**政治家占有率**: 0%（目標20%以下を達成）

---

## 6. 統計

- **計算人物数**: 7,154人
- **最高スコア**: 836.79
- **平均スコア**: 435.73
- **最低スコア**: 21.9

---

## 7. 結論

v1（fame_score_v3）を温存しつつ、v2（celebrity_score_v2）を新設しました。

- ✓ v1に影響なし
- ✓ 全PERSONに対してv2算出・保存
- ✓ 体感ランキング（トレンド・品質重視）
- ✓ カテゴリ上限・曖昧性ペナルティで品質ゲート
- ✓ 回帰テスト11件でEPUP定着
