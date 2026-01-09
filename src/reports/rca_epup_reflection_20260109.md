# 原因究明レポート: EPUP反映パイプライン不具合

## 調査日時
2026-01-09 09:40

## 対象エピソード
| episode_id | person_name | age | 問題 |
|------------|-------------|-----|------|
| EP-20260108155755653AA603 | セリーナ・ウィリアムズ | 36 | category欠損 |
| EP-202601081557559D8BF273 | クリストファー・コロンブス | 41 | category欠損 |
| EP-20260108155755782D0FE7 | ベートーヴェン | 53 | category欠損 |
| EP-2026010815575574DE9C75 | パブロ・ピカソ | 23 | category欠損 |
| EP-20260108155755FD58A845 | ゴッホ | 37 | category欠損 |
| EP-20260108155755FF58D531 | 本田宗一郎 | 42 | category欠損 |
| EP-20260108155755B209D4E2 | ベートーヴェン | 38 | category欠損 |
| EP-260105225818578736 | 有島武郎 | 80 | **年齢境界違反** (死亡45歳) |
| EP-260105225818578739 | 武者小路実篤 | 80 | OK |
| EP-260105225818578740 | 堀辰雄 | 80 | **年齢境界違反** (死亡48歳) |

## 発見した問題

### 問題1: category欠損（7件）
- **原因**: `process_batch_results.py` でBatch API結果をマスターCSVに書き込む際、iconic_achievements_master.jsonからcategoryを取得できなかった
- **影響範囲**: 2026-01-08 15:57:55に生成されたBatch APIエピソード7件
- **再現手順**:
  1. batch_iconic_submit.pyでBatch APIにリクエスト送信
  2. process_batch_results.pyで結果取得
  3. iconic_achievements_master.jsonにcategoryが定義されていない人物の場合、categoryがnullになる

### 問題2: 年齢境界違反（2件）
- **原因**: EP-260105225818578736（有島武郎80歳）、EP-260105225818578740（堀辰雄80歳）は、死亡年齢を超えた架空のエピソード
- **影響範囲**: 明らかに虚偽の内容（有島武郎が2003年に活動、堀辰雄が1984年に文化勲章受章など）
- **再現手順**:
  1. 生成時に年齢境界チェックが実行されていない
  2. 死亡年齢（有島45歳、堀48歳）を超える80歳のエピソードが生成された

## 根本原因

### 1. Batch API反映時のcategory取得ロジック不備
- `process_batch_results.py:140` で `category = request_meta["category"]` を取得
- iconic_achievements_master.jsonにcategoryが定義されていない場合、nullになる
- **修正方針**: person_idから既存エピソードのcategoryを取得するフォールバック追加

### 2. 年齢境界チェックの欠如
- 生成時に `detect_age_boundary_violations.py` が実行されていない
- SAGE orchestratorのゲートに年齢境界チェックが含まれていない
- **修正方針**: DB反映前ゲートに年齢境界チェックを追加

## 修正計画

### Phase 1: 即時修正（対象エピソード）
1. category欠損7件: person_idから正しいcategoryを復元
2. 年齢境界違反2件: DBから削除

### Phase 2: 再発防止（パイプライン改善）
1. `db_reflection_gate.py` に以下のチェックを追加:
   - 定型フォーマット検証
   - category必須チェック
   - 年齢境界チェック
   - 必須スコア欠損チェック
2. `process_batch_results.py` にcategoryフォールバック追加

### Phase 3: 全件検証
- 全エピソードに対して上記チェックを実行
- 不備があるエピソードをリストアップ

## 8軸スコア体系（確定）

| 軸 | カラム名 | 説明 |
|----|---------|------|
| 1 | llm_memorability_score | 記憶性 |
| 2 | llm_empathy_score | 共感性 |
| 3 | llm_surprise_score | 意外性 |
| 4 | llm_generation_quality_score | 生成品質 |
| 5 | llm_educational_value | 教育的価値 |
| 6 | llm_storytelling_quality | ストーリー品質 |
| 7 | llm_factual_density | 事実密度 |
| 8 | 象徴性スコア | 象徴性（Phase 4追加） |

## 必須カラム一覧（ダッシュボード表示）
- episode_id, person_id, person_name, age, episode_text
- category, fame_tier, episode_fame_tier_v6
- composite_score, super_total_score, episode_fame_v6
- celebrity_score_v2, fame_score_v3
