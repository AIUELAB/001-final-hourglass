# RCA: メタ要素汚染 防止強化 (2026-01-28)

## 概要
架空キャラクターエピソードにおけるメタ要素（販売本数、興行収入、製作プロセス等）の混入を完全防止するための多層防御を構築。

## 背景
- **発見日**: 2026-01-23 (RCA-20260123)
- **対象**: セフィロス（EP-260113031851994）、ガンダルフ（EP-260111220937181）等
- **混入例**: 「980万本を売上」「2001年の『ホビット』撮影準備」「魔力92%」

## 根本原因分析

### 一次原因: Orchestrator のゲート条件不備
- **箇所**: `scripts/sage/orchestrator.py` L498, L844
- **問題**: `person_type` のみで架空キャラを判定
  ```python
  # 修正前（脆弱）
  if candidate.person_type and "FICTIONAL" in str(candidate.person_type).upper():
  ```
- **結果**: `person_type="REAL"` に誤分類された架空キャラ（孫悟飯、マリオ等）が FictionalQualityGate を完全バイパス

### 二次原因: 防御層の不足
- Pre-commit hook にメタ検出なし → CSVコミット時にチェックされない
- CI にメタ検出なし → マージ前に検出されない

### 汚染経路
```
LLM生成 → Orchestrator(person_type判定のみ) → SafeCSVWriter(二重チェックあり) → CSV
                  ↑ ここでバイパス
```
SafeCSVWriter は二重チェック（person_type + person_name）を持つが、Orchestrator 段階で既にメタ要素が含まれたテキストが通過していた。

## 対策

### 即時対策（2026-01-23 実施済み）
- `detect_meta_element_violations.py --dry-run` で554件検出
- 全違反エピソードを削除（commit: 90fed43c）

### 恒久対策（2026-01-28 実施）

| 層 | 対策 | ファイル |
|----|------|---------|
| 生成直後 | Orchestrator に person_name 判定追加（OR条件） | `scripts/sage/orchestrator.py` |
| 書込前 | SafeCSVWriter 二重チェック（既存） | `scripts/sage/persistence/csv_writer.py` |
| コミット前 | Pre-commit hook でメタ検出 | `.pre-commit-config.yaml` |
| マージ前 | CI でメタ検出（`--strict`モード） | `.github/workflows/epup-daily-check.yml` |

### 多層防御フロー
```
LLM生成
  ↓
[層1] Orchestrator: person_type OR person_name で FictionalQualityGate 適用
  ↓
[層2] SafeCSVWriter: person_type + person_name 二重チェック
  ↓
[層3a] Pre-commit: detect_meta_element_violations.py --strict
  ↓
[層3b] CI: detect_meta_element_violations.py --strict
  ↓
CSV書込完了
```

## 検証手順
```bash
# メタ汚染0件確認
python scripts/validation/detect_meta_element_violations.py --dry-run

# strictモード動作確認
python scripts/validation/detect_meta_element_violations.py --dry-run --strict; echo "exit: $?"

# pre-commit動作確認
pre-commit run check-meta-violations --all-files
```

## 運用手順
1. 新規エピソード生成時: Orchestrator が自動で3層チェック実行
2. CSV更新コミット時: pre-commit が自動検出
3. PR作成時: CI が自動検出
4. 違反発見時: `detect_meta_element_violations.py --fix` で修正、または `--delete-only` で削除
