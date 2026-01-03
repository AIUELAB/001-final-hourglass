# EP-3947C4DE（アインシュタイン 奇跡の年）順位修正レポート

**作成日時**: 2026-01-03
**対象エピソード**: EP-3947C4DE
**人物**: アルベルト・アインシュタイン (P93F1DB1)

---

## 1. 現状分析

### 修正前の状態
| 順位 | episode_id | 年齢 | fame_v6 | 内容 |
|------|------------|------|---------|------|
| 1 | EP-000003646 | 36歳 | 88.23 | 一般相対性理論 |
| 2 | EP-000002832 | 41歳 | 85.85 | 反ユダヤ主義への対応 |
| 3 | EP-000009225 | 1歳 | 83.90 | 幼少期 |
| 4 | EP-251214200921598 | 69歳 | 83.29 | 統一場理論研究 |
| **5** | **EP-3947C4DE** | **26歳** | **69.02** | **奇跡の年(1905年)** ← 最下位 |

### 問題点
EP-3947C4DE（奇跡の年）は物理学史上最重要の年であり、1位であるべきだが最下位だった。

---

## 2. 原因究明

### 根本原因
**person-level項目の不整合**

EP-3947C4DE は `scripts/add_einstein_1905.py` で追加時に、テンプレートとして別人物（尾崎豊）の行をコピーした結果、person-level項目が誤った値のままになっていた。

| 項目 | EP-3947C4DE (誤) | 他アインシュタインEP (正) |
|------|------------------|---------------------------|
| celebrity_score_v2 | 610.06 | 817.35 |
| sitelinks_count | 17 | 108 |
| multi_lang_pv | 16426958 | 65803252 |

### 影響
`celebrity_score_v2` が低いため、`person_fame` コンポーネント（30%寄与）のスコアが大幅に低下し、fame_v6 が 69.02 に抑えられた。

---

## 3. 修正内容

### 実施した修正
`scripts/fix_einstein_episode_data.py` を実行し、以下の11項目を参照エピソード（EP-000003646）からコピー:

```
celebrity_score_v2: 610.0649 → 817.3471
sitelinks_count: 17 → 108
multi_lang_pv: 16426958 → 65803252
fame_score_v2: 8.15 → 8.51
fame_score_v3: 1.80 → 6.94
fame_rank: 175 → 115
fame_rank_v3: 3124 → 55
celebrity_rank_v2: 220 → 7
google_hits: 2200000 → 1120000000
fame_score_japan: 50.0 → 95.0
wikipedia_pv: (empty) → 6116
```

### fame_v6 再計算
修正後に `scripts/recalculate_episode_fame_v6.py` を実行:
- fame_v6: 69.02 → **89.25**
- tier: 4 → **5**

---

## 4. 修正後の状態

### アインシュタイン内順位
| 順位 | episode_id | 年齢 | fame_v6 | 内容 |
|------|------------|------|---------|------|
| **1** | **EP-3947C4DE** | **26歳** | **89.25** | **奇跡の年(1905年)** ← 1位に浮上 |
| 2 | EP-000003646 | 36歳 | 88.23 | 一般相対性理論 |
| 3 | EP-000002832 | 41歳 | 85.85 | 反ユダヤ主義への対応 |
| 4 | EP-000009225 | 1歳 | 83.90 | 幼少期 |
| 5 | EP-251214200921598 | 69歳 | 83.29 | 統一場理論研究 |

### 検証
- ✅ EP-3947C4DE が1位になった
- ✅ 順位は重要度/有名度に沿っている（奇跡の年 > 一般相対性理論 > 反ユダヤ対応）
- ✅ 回帰テスト（TestEinsteinEpisodeRanking）がパス

---

## 5. 再発防止

### 追加したツール

| ツール | パス | 目的 |
|--------|------|------|
| 検出 | `scripts/validation/detect_person_level_mismatch.py` | person-level不整合を検出 |
| テスト | `tests/test_person_level_consistency.py` | 整合性の回帰テスト |

### 回帰テスト
```
TestEinsteinEpisodeRanking
├── test_einstein_miracle_year_is_top_ranked ✅
└── test_einstein_has_consistent_celebrity_score ✅
```

---

## 6. 残課題

### 他人物の不整合（承認待ち）
検出結果:
- 影響人物数: **580人**
- 不整合件数: **1,624件**

一括修正スクリプト:
```bash
python scripts/validation/detect_person_level_mismatch.py --fix
```

⚠️ 破壊的操作のため、明示承認が必要です。

---

## 変更ファイル一覧

| ファイル | 操作 |
|---------|------|
| `preserved/data/MASTER_EPISODES_CURRENT.csv` | 更新（EP-3947C4DE修正） |
| `scripts/fix_einstein_episode_data.py` | 新規 |
| `scripts/validation/detect_person_level_mismatch.py` | 新規 |
| `tests/test_person_level_consistency.py` | 新規 |
