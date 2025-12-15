---
description: EPUP - Episode Update Pipeline（エピソードDB品質の検出→分析→修正→予防→監視）
---

# EPUP Skill（Episode Update Pipeline）

## 目的
エピソードデータベースの品質を、**EPUP 7ステップ**（検出→分析→修正→類似検索→一括修正→予防→監視）で継続改善します。

## 参照（最小読み）
- **EPUP System 調査報告書（詳細）**: `/Users/admin/.claude/plans/typed-wishing-scone.md`
  - ※必要になったタイミングで“該当セクションだけ”参照し、全文貼り付けはしない

## 重要制約（必須）
- **推測で断言しない**：事実は「ファイルパス＋短い抜粋」で根拠を示す
- **機密を出さない**：APIキー等の値は表示・要求しない
- **低コンテキスト運用**：
  - 大きいファイル/ログの全文貼り付け禁止（**要約＋上位5件**まで）
  - まず `grep` で当たりを付けてから、必要なファイルだけ読む
- **自動修正は勝手にしない**：`--fix` / `--auto-fix` など“書き換える操作”は必ずユーザー承認後

## まず実行すること（最短ルート）
1. **エピソードDBの実体パスを確定**（存在するものを優先）
   - 候補: `preserved/data/MASTER_EPISODES_CURRENT.csv`, `preserved/MASTER_EPISODES_CURRENT.csv`, `MASTER_EPISODES_CURRENT.csv`, `data/MASTER_EPISODES_CURRENT.csv`
2. **軽量ヘルスチェック（ローカル・非LLM）**
   - `python scripts/check_single_master.py`
   - `python scripts/scheduled_epup_check.py --daily --csv <CSV_PATH>`
3. **必要時のみ成果評価（ローカル・非LLM）**
   - `python scripts/evaluate_epup_effectiveness.py --csv <CSV_PATH> --output reports/epup_evaluation_manual_YYYYMMDD_HHMMSS.json`
4. **結果に応じて「最小の次アクション」を提案**
   - 例：グループ名混入→該当修正スクリプト提案、架空キャラのメタ表現→`fix_fictional_meta_episodes.py`提案など

## 自動監視（エピソード更新でEPUPを発動）
エピソードの追加/編集/導入（インポート）などでCSVが更新されたら、自動で**軽量チェック**を回す。

- 推奨: `python scripts/epup_auto_watch.py --csv <CSV_PATH>`
- **コンテキスト節約**: `python scripts/epup_auto_watch.py --csv <CSV_PATH> --quiet`（レポートだけ残して出力を抑制）
- 期待挙動:
  - 変更検知 → `scheduled_epup_check.py --daily` を自動実行
  - アラートが出た時だけ、必要なら `evaluate_epup_effectiveness.py` を追加実行（※自動修正はしない）

## 問題タイプ別：次の一手（最小候補）
※ここに無い場合は、`typed-wishing-scone.md` の「関連スクリプト」節を必要最小で参照する。

- **単一マスター崩れ（CSVが散らばる）**: `python scripts/check_single_master.py`
- **KPI異常（軽量チェックでアラート）**: `python scripts/scheduled_epup_check.py --daily/--weekly`
- **全体スコア/21指標で現状把握**: `python scripts/evaluate_epup_effectiveness.py --csv <CSV_PATH> --output reports/...json`
- **評価の前後比較**: `python scripts/compare_epup_scores.py --baseline <A.json> --after <B.json> --output reports/...json`
- **架空キャラのメタ表現検出/修正**: `python scripts/fix_fictional_meta_episodes.py --detect-only`（修正は `--fix` を承認後）
- **年齢境界違反（死後/未到達年齢のエピソード）**: `python scripts/detect_problematic_phase8_episodes.py`（削除は `scripts/delete_problematic_phase8.py --execute` を承認後）
- **架空キャラ作品名欠落**: `python scripts/fix_fictional_work_title_format.py`（必要なら `--fix` を承認後）
- **グループ同期**: `python scripts/sync_group_from_master.py`（`--execute` は承認後）
- **別名・通称検出/修正**: `python scripts/normalize_person_names.py --dry-run`（修正実行は `--execute` を承認後）
  - 結果レポート: `reports/name_normalization_dryrun_*.json`
  - パターン例: 「山中教授」→「山中伸弥」、「ホリエモン」→「堀江貴文」
- **人物名バリデーション（生成前チェック）**:
  ```python
  from src.validators.person_name_validator import get_validator
  validator = get_validator()
  issues = validator.validate(person_name)
  for issue in issues:
      print(f"{issue.severity.value}: {issue.message}")
      if issue.auto_fixable:
          print(f"  → 修正案: {issue.fixed_value}")
  ```

## エピソード生成時の事前チェックリスト

新規エピソード生成前に以下を確認してください：

### 1. 人物名バリデーション

```python
from src.validators.person_name_validator import validate_before_episode_generation

is_valid, message, suggested_fix = validate_before_episode_generation(person_name)
if not is_valid:
    print(f"❌ {message}")
    if suggested_fix:
        print(f"✅ 修正案: {suggested_fix}")
        # 修正案を使用してエピソード生成
        person_name = suggested_fix["person_name"]
```

### 2. 検出される問題タイプ

- **別名使用**: 「山中教授」→「山中伸弥」を使用すべき
- **グループ名混入**: 「乃木坂46齋藤飛鳥」→「齋藤飛鳥」
- **組織名・肩書き混入**: 「日本人実業家の稲盛和夫」→「稲盛和夫」
- **連結名パターン**: 「ビートルズ・ジョン・レノン」→「ジョン・レノン」

### 3. 年齢境界チェック

- `birth_year` ~ `death_year`（または現在年）の範囲内か確認
- 範囲外の年齢は生成禁止（メタ表現誘発リスク）
- 参照: CLAUDE.md「年齢境界違反エピソード検出ルール」セクション

## 出力フォーマット（必ずこの順）

### 現状（事実＋根拠）

### 実行したチェック（コマンドと結果要約）

### 検出された問題（上位5件）

### 推奨アクション（最小差分・承認が必要な操作は明記）

### 次にユーザーへ確認したいこと（最大5つ）
