# Fame Score v3 完了後ステッププラン

**作成日**: 2025-12-23
**対象**: Fame Score v3 処理完了後の作業計画
**現状**: 処理中（9.4%完了、695/7,383人）

---

## 背景と目的

### 解決すべき問題
- **問題**: 小泉八雲が1位（730点）、スティーブ・ジョブズが476位（612点）
- **原因**: 日本語Wikipedia PVのみに依存していたため、日本で有名な人物が過大評価

### Fame Score v3 の改善内容
| 項目 | v2（旧） | v3（新） |
|------|---------|---------|
| Wikipedia PV | 日本語のみ | 10言語（日/英/中/韓/独/仏/西/伊/葡/露） |
| Wikidata sitelinks | なし | 言語版リンク数 |
| Wikidata inlinks | なし | 被参照数 |
| 重み構成 | PV 100% | PV 50% + sitelinks 30% + inlinks 20% |

---

## Phase 1: データ検証（完了直後〜Day 1）

### 1.1 スコア分布の確認
```bash
python scripts/analyze_fame_score_distribution.py
```

確認項目:
- [ ] min / max / mean / median / std
- [ ] Tier別人数分布（Tier 1〜5）
- [ ] 上位100人のリスト出力

### 1.2 問題解決の検証

**必須チェックリスト**:
| 人物 | 旧順位 | 期待順位 | 実際の順位 | 判定 |
|------|--------|----------|------------|------|
| 小泉八雲 | 1位 | 500位以下 | ? | |
| スティーブ・ジョブズ | 476位 | 50位以内 | ? | |
| マイケル・ジョーダン | 771位 | 100位以内 | ? | |
| 大谷翔平 | 5950位 | 100位以内 | ? | |

### 1.3 異常値チェック
- [ ] スコアが0の人物
- [ ] スコアが異常に高い人物（>900）
- [ ] 架空キャラクターのスコア妥当性

### 1.4 同率問題の確認
```python
# 確認スクリプト
df = pd.read_csv('preserved/data/MASTER_EPISODES_CURRENT.csv')
fame_scores = df.groupby('person_name')['fame_score'].first()

print(f"1位の人数: {(fame_scores == fame_scores.max()).sum()}")
print(f"ユニーク率: {fame_scores.nunique() / len(fame_scores) * 100:.2f}%")
```

**成功基準**:
- 1位の人数: 1人
- 同率グループ最大サイズ: 2以下
- ユニーク率: 99.9%以上

---

## Phase 2: ダッシュボード反映（Day 1〜2）

### 2.1 CSV更新
```bash
# バックアップ作成
cp preserved/data/MASTER_EPISODES_CURRENT.csv \
   preserved/data/backup/MASTER_EPISODES_$(date +%Y%m%d).csv

# fame_score, fame_tier 更新
python scripts/apply_fame_score_v3.py --execute
```

### 2.2 ダッシュボード確認
- [ ] 「有名人度ランキング」タブの表示
- [ ] 「有名エピソードランキング」タブへの影響
- [ ] ソート・フィルター機能
- [ ] ページネーション（上部・下部）

### 2.3 キャッシュ更新
```bash
# heatmap_data.json 再生成（必要な場合）
python scripts/generate_heatmap_data.py --output preserved/heatmap_data.json
```

### 2.4 動作確認
```bash
# HTTPサーバー再起動
pkill -f "python.*http.server.*8080"
cd /Users/admin/Documents/AIUELAB/001-final-hourglass
python3 -m http.server 8080 &
open http://localhost:8080/preserved/episode_database_dashboard_v9.html
```

---

## Phase 3: 品質ゲート設定（Day 2〜3）

### 3.1 検証スクリプト作成
```python
# scripts/validate_fame_score.py
def validate_fame_score():
    checks = {
        '小泉八雲の順位': rank_of('小泉八雲') > 500,
        'ジョブズの順位': rank_of('スティーブ・ジョブズ') <= 50,
        '1位人数': count_rank_1() == 1,
        'ユニーク率': unique_ratio() >= 0.999,
    }
    return all(checks.values()), checks
```

### 3.2 EPUP統合
`docs/EPUP_RULES.md` に追記:
```markdown
## 10. Fame Score v3 品質基準

### ルール
- 世界的有名人（ジョブズ、ジョーダン等）は上位100位以内
- 日本ローカル有名人は過大評価しない
- 同率1位は発生させない

### 検証
python scripts/validate_fame_score.py
```

### 3.3 自動監視
```bash
# CSVファイル変更時に自動検証
fswatch -o preserved/data/MASTER_EPISODES_CURRENT.csv | \
  xargs -n1 python scripts/validate_fame_score.py
```

---

## Phase 4: 問題発生時の対応

### シナリオA: スコアが改善されていない
```
原因調査:
1. APIレスポンス確認（キャッシュDB）
2. 計算ロジック確認（scripts/fame_score_v3/scorer.py）
3. 重み付け調整

対応:
- config/fame_score_config.yaml で重み変更
- 必要ならSerpAPIデータ（¥7,500投資済み）を追加活用
```

### シナリオB: 同率問題が残る
```
対応:
1. タイブレーク導入
   - エピソード数
   - Wikipedia記事長
   - person_id のハッシュ（最終手段）

2. rank/score 分離
   - fame_rank: 一意な整数（1〜N）
   - fame_score: 表示用連続値
```

### シナリオC: 特定人物のスコアが異常
```
対応:
1. config/wikipedia_overrides.json で記事名マッピング修正
2. config/fame_overrides.json で個別スコア上書き
```

### シナリオD: API制限で完了しない
```
対応:
1. 部分的適用（完了分のみ先に反映）
2. キャッシュ活用（data/cache/fame_score.db）
3. 翌日に再開
```

---

## Phase 5: Episode Fame Score 改善（Week 1〜2）

### 5.1 計算式の見直し
```python
# 現在
episode_fame_score = person_fame_score * 0.7 + episode_quality * 0.3

# 改善案
episode_fame_score = (
    person_fame_score * 0.5 +
    episode_quality * 0.3 +
    episode_specificity * 0.2  # そのエピソードがどれだけ有名か
)
```

### 5.2 エピソードランキング検証
- [ ] 有名な人の有名なエピソードが上位に来ているか
- [ ] 無名な人のエピソードが上位に来ていないか

### 5.3 表示形式の統一
- 人物ランキングとエピソードランキングで同じTier色・バッジを使用

---

## Phase 6: 長期的改善（Month 1〜）

### 6.1 データソース拡充
| ソース | 現状 | 計画 | コスト |
|--------|------|------|--------|
| Wikipedia PV | 10言語 | 20言語 | 無料 |
| Wikidata | 使用中 | 継続 | 無料 |
| Google検索 | キャッシュあり | 再活用 | ¥7,500投資済み |
| SNS | なし | 検討 | 要調査 |

### 6.2 自動更新の仕組み
```bash
# 月次更新（cron）
0 3 1 * * python scripts/update_fame_scores_v3.py --execute >> logs/fame_update.log
```

### 6.3 時系列トラッキング
- fame_score_history テーブルの作成
- 月次変動レポートの自動生成

---

## 成功指標（KPI）

### 必須達成項目
| 指標 | 現状 | 目標 |
|------|------|------|
| 小泉八雲の順位 | 1位 | 500位以下 |
| ジョブズの順位 | 476位 | 50位以内 |
| 大谷翔平の順位 | 5950位 | 100位以内 |
| 1位の人数 | 79人 | 1人 |
| ユニーク率 | 不明 | 99.9%以上 |

### 推奨達成項目
- Tier 1（世界的有名人）: 上位1%
- Tier 2（国民的有名人）: 上位5%
- 架空キャラクター: 適切な範囲（Tier 3〜4）

---

## マイルストーン

```
Day 0   : Fame Score v3 処理完了
Day 1   : データ検証完了、問題があれば修正開始
Day 2   : ダッシュボード反映完了
Day 3   : 品質ゲート設定完了
Week 1  : 安定運用開始
Week 2  : Episode Fame Score 改善
Month 1 : 自動更新の仕組み構築
Month 3 : データソース拡充検討
```

---

## 関連ファイル

| ファイル | 用途 |
|----------|------|
| `scripts/update_fame_scores_v3.py` | スコア更新スクリプト |
| `scripts/fame_score_v3/scorer.py` | スコア計算ロジック |
| `scripts/fame_score_v3/wikipedia_pv.py` | Wikipedia PV取得 |
| `scripts/fame_score_v3/wikidata.py` | Wikidata指標取得 |
| `config/fame_score_config.yaml` | 設定ファイル |
| `data/cache/fame_score.db` | キャッシュDB |
| `preserved/data/MASTER_EPISODES_CURRENT.csv` | マスターCSV |
| `preserved/episode_database_dashboard_v9.html` | ダッシュボード |

---

## 履歴

| 日付 | 変更内容 |
|------|----------|
| 2025-12-23 | 初版作成 |

---

**作成者**: Claude Code
**レビュー**: 未実施
