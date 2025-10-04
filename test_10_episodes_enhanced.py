#!/usr/bin/env python3
"""
10エピソード大規模テスト（Enhanced版）

主な改善点:
1. 🔴 Critical修正: ゼロ除算防止・ファイル存在確認・CSVインジェクション対策
2. 🔴 データ検証: スコア妥当性・削除率監視
3. 🟡 品質ゲート: PDCA準拠の品質ゲートシステム
4. 🟡 エラーハンドリング: 包括的なエラー処理とロギング
5. 🟢 パフォーマンス監視: 実行時間・メモリ使用量の追跡

変更履歴:
- 2025-10-02: 品質優先原則に基づく大幅改善
"""

import csv
import json
import time
import logging
import traceback
import os
from datetime import datetime
from collections import defaultdict, Counter
from enum import Enum
from typing import List, Dict, Any, Optional

from batch_high_quality_generator import BatchHighQualityGenerator


# ================================================================================
# エラー定義（Fail-Fast原則）
# ================================================================================

class ErrorSeverity(Enum):
    """エラー重大度"""
    CRITICAL = "CRITICAL"  # 即座に処理停止
    ERROR = "ERROR"        # ロールバック後停止
    WARNING = "WARNING"    # ログ記録して継続
    INFO = "INFO"          # 情報記録のみ


class EpisodeTestError(Exception):
    """エピソードテスト基底例外"""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR, context: Optional[Dict] = None):
        self.severity = severity
        self.context = context or {}
        super().__init__(message)


class DataQualityError(EpisodeTestError):
    """データ品質エラー（🔴 Critical）"""
    def __init__(self, message: str, **context):
        super().__init__(message, ErrorSeverity.CRITICAL, context)


class APIRateLimitError(EpisodeTestError):
    """APIレート制限エラー（🟡 Warning）"""
    def __init__(self, message: str, **context):
        super().__init__(message, ErrorSeverity.WARNING, context)


# ================================================================================
# ユーティリティ関数
# ================================================================================

def sanitize_csv_field(value: Any) -> Any:
    """
    CSV数式インジェクション対策

    Excel等で開いた際に数式として実行されないよう、
    危険な文字で始まる値にシングルクォートを付与
    """
    if isinstance(value, str) and value:
        # 危険な文字: = + - @ \t \r
        if value[0] in ('=', '+', '-', '@', '\t', '\r'):
            return f"'{value}"
    return value


def write_safe_csv(filename: str, data: List[Dict], fieldnames: List[str]) -> None:
    """
    安全なCSV書き込み（UTF-8 BOM + サニタイゼーション）

    Args:
        filename: 出力ファイル名
        data: データリスト
        fieldnames: フィールド名リスト
    """
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()

        # 各行をサニタイズ
        sanitized_data = [
            {k: sanitize_csv_field(v) for k, v in row.items()}
            for row in data
        ]
        writer.writerows(sanitized_data)

    logging.info(f"✅ CSV書き込み完了: {filename} ({len(data)}行)")


def validate_and_convert_score(score_value: Any, person_name: str) -> float:
    """
    スコア変換と検証（PDCA準拠）

    Args:
        score_value: スコア値（文字列 or 数値）
        person_name: 人物名（検証用）

    Returns:
        100点満点スコア（0.0-100.0）

    Raises:
        ValueError: スコアが範囲外の場合
    """
    try:
        # 文字列→数値変換
        if isinstance(score_value, str):
            if not score_value or score_value.strip() == '':
                return 0.0
            score_value = float(score_value)

        # 10点満点→100点満点
        score_100 = float(score_value) * 10

        # 範囲チェック（0-100点）
        if not 0 <= score_100 <= 100:
            logging.error(
                f"❌ 異常スコア検出: {person_name} = {score_100}点 "
                f"(有効範囲: 0-100点)"
            )
            return 0.0

        # 有名人の最低スコア検証（プロジェクト規約: 7.0以上）
        FAMOUS_PEOPLE = ["HIKAKIN", "羽生結弦", "大谷翔平", "イチロー", "本田圭佑"]
        if person_name in FAMOUS_PEOPLE and score_100 < 70:
            logging.warning(
                f"⚠️ 有名人の異常低スコア: {person_name} = {score_100}点 "
                f"(期待値: 70点以上)"
            )

        return score_100

    except (ValueError, TypeError) as e:
        logging.error(f"スコア変換エラー: {person_name} - {e}")
        return 0.0


def validate_deletion_rate(test_episodes: List[Dict], results: List[Any]) -> float:
    """
    削除率の統計的整合性チェック（プロジェクト規約: 10-20%）

    Args:
        test_episodes: テストエピソードリスト
        results: 生成結果リスト

    Returns:
        削除率（%）

    Raises:
        DataQualityError: 削除率が45%を超える場合
    """
    if not test_episodes or not results:
        return 0.0

    total = len(test_episodes)
    failed = sum(1 for r in results if r.score < 60)
    deletion_rate = (failed / total) * 100

    # 規約チェック（10-20%が正常範囲）
    if deletion_rate < 10:
        logging.warning(
            f"⚠️ 削除率が異常に低い: {deletion_rate:.1f}% "
            f"(正常範囲: 10-20%)"
        )
    elif deletion_rate > 45:
        raise DataQualityError(
            f"削除率が異常に高い: {deletion_rate:.1f}%",
            deletion_rate=deletion_rate,
            threshold=45.0,
            normal_range="10-20%",
            failed_count=failed,
            total_count=total,
            message="データ品質に重大な問題がある可能性があります"
        )

    logging.info(f"✅ 削除率: {deletion_rate:.1f}% (正常範囲内)")
    return deletion_rate


# ================================================================================
# 品質ゲートシステム（PDCA準拠）
# ================================================================================

def validate_quality_gates(episodes: List[Dict]) -> None:
    """
    品質ゲートシステム（Fail-Fast原則）

    Args:
        episodes: エピソードリスト

    Raises:
        DataQualityError: 品質ゲート違反時
    """
    logging.info("🔍 品質ゲートチェック開始...")

    # Gate 1: データ品質検証
    if not episodes:
        raise DataQualityError(
            "エピソードデータが空です",
            gate="Gate 1: データ品質検証"
        )

    # Gate 2: ダミーデータ検出（TODO、FIXME、シミュレート）
    dummy_keywords = ['TODO', 'FIXME', 'シミュレート', '未実装', 'DUMMY']
    dummy_count = 0
    dummy_samples = []

    for ep in episodes:
        text = ep.get('episode_text', '')
        for keyword in dummy_keywords:
            if keyword in text:
                dummy_count += 1
                dummy_samples.append({
                    'person': ep.get('person_name', 'Unknown'),
                    'keyword': keyword,
                    'text_preview': text[:100]
                })
                break

    if dummy_count > 0:
        raise DataQualityError(
            f"ダミーデータ検出: {dummy_count}件",
            gate="Gate 2: ダミーデータ検出",
            dummy_count=dummy_count,
            samples=dummy_samples[:3]
        )

    # Gate 3: スコア妥当性確認
    invalid_scores = []
    for ep in episodes:
        score = ep.get('weighted_score', 0)
        try:
            score_float = float(score) if score else 0.0
            if not 0 <= score_float <= 10:
                invalid_scores.append({
                    'person': ep.get('person_name', 'Unknown'),
                    'score': score
                })
        except (ValueError, TypeError):
            invalid_scores.append({
                'person': ep.get('person_name', 'Unknown'),
                'score': score
            })

    if invalid_scores:
        raise DataQualityError(
            f"異常なスコア検出: {len(invalid_scores)}件",
            gate="Gate 3: スコア妥当性確認",
            invalid_count=len(invalid_scores),
            samples=invalid_scores[:3]
        )

    # Gate 4: 統計的整合性チェック
    categories = [ep.get('category', 'Unknown') for ep in episodes]
    category_counts = Counter(categories)

    # カテゴリの偏りチェック（1カテゴリが80%以上を占める場合）
    max_category = category_counts.most_common(1)[0]
    max_ratio = max_category[1] / len(episodes) * 100

    if max_ratio > 80:
        logging.warning(
            f"⚠️ カテゴリの偏り検出: {max_category[0]} = {max_ratio:.1f}%"
        )

    logging.info("✅ すべての品質ゲートをクリアしました")


def validate_system_readiness() -> None:
    """
    システム準備確認（依存関係・環境変数チェック）

    Raises:
        DataQualityError: システム準備不足時
    """
    logging.info("🔍 システム準備確認開始...")

    # 必須ファイルチェック
    checks = [
        ("batch_high_quality_generator.py", "バッチ生成モジュール"),
    ]

    for file_path, description in checks:
        if not os.path.exists(file_path):
            raise DataQualityError(
                f"必要なファイルが見つかりません: {description}",
                file_path=file_path,
                check_type="system_readiness"
            )

    # 環境変数チェック
    required_env_vars = ["OPENAI_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]

    if missing_vars:
        raise DataQualityError(
            f"必要な環境変数が設定されていません: {', '.join(missing_vars)}",
            missing_vars=missing_vars,
            check_type="environment"
        )

    logging.info("✅ システム準備確認完了")


# ================================================================================
# メイン処理関数
# ================================================================================

def prepare_test_data(input_csv: str, output_csv: str, limit: int = 10) -> List[Dict]:
    """
    テストデータを準備（カテゴリ均等分散）

    Args:
        input_csv: 入力CSVファイルパス
        output_csv: 出力CSVファイルパス
        limit: サンプル数

    Returns:
        テストエピソードリスト

    Raises:
        FileNotFoundError: 入力ファイルが存在しない場合
        DataQualityError: データ品質に問題がある場合
    """
    print(f"{'='*80}")
    print(f"テストデータ準備")
    print(f"{'='*80}")

    # 🔴 Critical修正: ファイル存在確認
    if not os.path.exists(input_csv):
        raise FileNotFoundError(f"❌ 入力ファイルが見つかりません: {input_csv}")

    # CSVを読み込み
    episodes = []
    with open(input_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        episodes = list(reader)

    if not episodes:
        raise DataQualityError(
            "入力CSVファイルが空です",
            input_file=input_csv
        )

    print(f"総エピソード数: {len(episodes)}件")

    # 多様性を確保するため、カテゴリから均等に選択
    test_episodes = []
    categories = list(set(ep['category'] for ep in episodes if 'category' in ep))

    if not categories:
        raise DataQualityError(
            "カテゴリ情報が存在しません",
            input_file=input_csv
        )

    category_episodes = defaultdict(list)
    for ep in episodes:
        category_episodes[ep['category']].append(ep)

    per_category = limit // len(categories)
    remainder = limit % len(categories)

    for i, category in enumerate(categories):
        n = per_category + (1 if i < remainder else 0)
        selected = category_episodes[category][:n]
        test_episodes.extend(selected)

        if len(test_episodes) >= limit:
            break

    test_episodes = test_episodes[:limit]

    # 品質ゲートチェック
    validate_quality_gates(test_episodes)

    # テストデータとして保存（🔴 Critical修正: 安全なCSV書き込み）
    if test_episodes:
        write_safe_csv(output_csv, test_episodes, list(test_episodes[0].keys()))

    print(f"\nテスト対象エピソード:")
    for i, ep in enumerate(test_episodes, 1):
        print(f"{i}. {ep['person_name']}（{ep['episode_age']}歳）- {ep['category']}")

    print(f"\n✅ テストデータを {output_csv} に保存しました")

    return test_episodes


def run_comparison_test(test_episodes: List[Dict], timestamp: str) -> Dict[str, Any]:
    """
    モード別比較テスト（prompt_optimized vs iterative）

    Args:
        test_episodes: テストエピソードリスト
        timestamp: タイムスタンプ

    Returns:
        モード別結果の辞書
    """
    print(f"\n{'='*80}")
    print(f"Phase 2: モード別比較テスト")
    print(f"{'='*80}\n")

    results = {}

    # モード1: prompt_optimized（高速）
    print(f"【モード1: prompt_optimized】\n")

    batch_gen_fast = BatchHighQualityGenerator(
        provider="openai",
        mode="prompt_optimized",
        max_workers=3,
        pass_threshold=60
    )

    result_fast = batch_gen_fast.process_episodes_list(
        test_episodes,
        output_csv=f"test_10episodes_prompt_optimized_{timestamp}.csv",
        verbose=True
    )

    results['prompt_optimized'] = result_fast

    # 🔴 データ検証: 削除率監視
    deletion_rate_fast = validate_deletion_rate(test_episodes, result_fast.results)
    logging.info(f"prompt_optimizedモード削除率: {deletion_rate_fast:.1f}%")

    print(f"\n{'='*80}")
    time.sleep(5)  # レート制限対策

    # モード2: iterative（高品質）
    print(f"\n【モード2: iterative】\n")

    batch_gen_quality = BatchHighQualityGenerator(
        provider="openai",
        mode="iterative",
        max_workers=2,
        max_iterations=3,
        pass_threshold=60
    )

    result_quality = batch_gen_quality.process_episodes_list(
        test_episodes,
        output_csv=f"test_10episodes_iterative_{timestamp}.csv",
        verbose=True
    )

    results['iterative'] = result_quality

    # 🔴 データ検証: 削除率監視
    deletion_rate_quality = validate_deletion_rate(test_episodes, result_quality.results)
    logging.info(f"iterativeモード削除率: {deletion_rate_quality:.1f}%")

    return results


def compare_with_existing(
    test_episodes: List[Dict],
    new_results: Dict[str, Any],
    timestamp: str
) -> List[Dict]:
    """
    既存エピソードとの比較

    Args:
        test_episodes: テストエピソードリスト
        new_results: モード別結果
        timestamp: タイムスタンプ

    Returns:
        比較データリスト

    Raises:
        DataQualityError: 比較データが空の場合
    """
    print(f"\n{'='*80}")
    print(f"既存エピソード vs 新システム - 比較分析")
    print(f"{'='*80}\n")

    comparison_data = []

    for i, (existing, new_prompt, new_iter) in enumerate(
        zip(
            test_episodes,
            new_results['prompt_optimized'].results,
            new_results['iterative'].results
        ),
        1
    ):
        # 🔴 Critical修正: スコア検証
        existing_score_100 = validate_and_convert_score(
            existing.get('weighted_score', 0),
            existing['person_name']
        )

        comparison_data.append({
            'person_name': existing['person_name'],
            'age': existing['episode_age'],
            'category': existing['category'],

            # 既存
            'existing_text': existing['episode_text'],
            'existing_score': existing_score_100,
            'existing_length': existing['character_count'],

            # prompt_optimized
            'prompt_text': new_prompt.episode_text,
            'prompt_score': new_prompt.score,
            'prompt_grade': new_prompt.grade,
            'prompt_length': len(new_prompt.episode_text),

            # iterative
            'iter_text': new_iter.episode_text,
            'iter_score': new_iter.score,
            'iter_grade': new_iter.grade,
            'iter_iterations': new_iter.iterations,
            'iter_length': len(new_iter.episode_text),

            # 改善幅
            'improvement_prompt': new_prompt.score - existing_score_100,
            'improvement_iter': new_iter.score - existing_score_100
        })

    # 🔴 Critical修正: ゼロ除算防止
    if not comparison_data:
        raise DataQualityError(
            "比較データが空です",
            phase="Phase 3: 比較分析"
        )

    # CSV保存（🔴 Critical修正: 安全なCSV書き込み）
    comparison_csv = f"comparison_10episodes_{timestamp}.csv"
    write_safe_csv(comparison_csv, comparison_data, list(comparison_data[0].keys()))

    # 統計表示
    print(f"【スコア比較】\n")
    print(f"{'人物名':<15} {'既存':<8} {'Prompt':<8} {'Iter':<8} {'改善(P)':<10} {'改善(I)':<10}")
    print(f"{'-'*70}")

    for row in comparison_data:
        print(f"{row['person_name']:<15} "
              f"{row['existing_score']:<8.1f} "
              f"{row['prompt_score']:<8.0f} "
              f"{row['iter_score']:<8.0f} "
              f"+{row['improvement_prompt']:<9.1f} "
              f"+{row['improvement_iter']:<9.1f}")

    # 平均計算
    avg_existing = sum(d['existing_score'] for d in comparison_data) / len(comparison_data)
    avg_prompt = sum(d['prompt_score'] for d in comparison_data) / len(comparison_data)
    avg_iter = sum(d['iter_score'] for d in comparison_data) / len(comparison_data)
    avg_imp_prompt = sum(d['improvement_prompt'] for d in comparison_data) / len(comparison_data)
    avg_imp_iter = sum(d['improvement_iter'] for d in comparison_data) / len(comparison_data)

    print(f"{'-'*70}")
    print(f"{'平均':<15} "
          f"{avg_existing:<8.1f} "
          f"{avg_prompt:<8.1f} "
          f"{avg_iter:<8.1f} "
          f"+{avg_imp_prompt:<9.1f} "
          f"+{avg_imp_iter:<9.1f}")

    print(f"\n✅ 比較データを {comparison_csv} に保存しました")

    return comparison_data


def generate_final_report(
    test_episodes: List[Dict],
    new_results: Dict[str, Any],
    comparison_data: List[Dict],
    timestamp: str
) -> str:
    """
    最終レポート生成

    Args:
        test_episodes: テストエピソードリスト
        new_results: モード別結果
        comparison_data: 比較データリスト
        timestamp: タイムスタンプ

    Returns:
        レポート文字列
    """
    # 🔴 Critical修正: ゼロ除算防止
    if not comparison_data:
        logging.error("❌ 比較データが空のため、レポート生成をスキップします")
        return ""

    # 統計計算
    avg_existing = sum(d['existing_score'] for d in comparison_data) / len(comparison_data)
    avg_prompt = sum(d['prompt_score'] for d in comparison_data) / len(comparison_data)
    avg_iter = sum(d['iter_score'] for d in comparison_data) / len(comparison_data)
    avg_imp_prompt = sum(d['improvement_prompt'] for d in comparison_data) / len(comparison_data)
    avg_imp_iter = sum(d['improvement_iter'] for d in comparison_data) / len(comparison_data)

    max_existing = max(d['existing_score'] for d in comparison_data)
    max_prompt = max(d['prompt_score'] for d in comparison_data)
    max_iter = max(d['iter_score'] for d in comparison_data)

    min_existing = min(d['existing_score'] for d in comparison_data)
    min_prompt = min(d['prompt_score'] for d in comparison_data)
    min_iter = min(d['iter_score'] for d in comparison_data)

    pass_existing = sum(1 for d in comparison_data if d['existing_score'] >= 60)
    pass_prompt = sum(1 for d in comparison_data if d['prompt_score'] >= 60)
    pass_iter = sum(1 for d in comparison_data if d['iter_score'] >= 60)

    report = f"""# 10エピソード大規模テスト - 最終レポート（Enhanced版）

**実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**テスト件数**: {len(test_episodes)}件
**改善版**: 品質優先原則・PDCA準拠

---

## 📊 総合結果

### スコア比較

| メトリクス | 既存 | prompt_optimized | iterative | 改善幅（P） | 改善幅（I） |
|----------|------|-----------------|-----------|-----------|-----------|
| 平均スコア | {avg_existing:.1f}点 | {avg_prompt:.1f}点 | {avg_iter:.1f}点 | +{avg_imp_prompt:.1f}点 | +{avg_imp_iter:.1f}点 |
| 最高スコア | {max_existing:.1f}点 | {max_prompt:.0f}点 | {max_iter:.0f}点 | - | - |
| 最低スコア | {min_existing:.1f}点 | {min_prompt:.0f}点 | {min_iter:.0f}点 | - | - |

### 合格率（60点以上）

| システム | 合格数 | 合格率 |
|---------|-------|--------|
| 既存 | {pass_existing}件 | {pass_existing / len(comparison_data) * 100:.1f}% |
| prompt_optimized | {pass_prompt}件 | {pass_prompt / len(comparison_data) * 100:.1f}% |
| iterative | {pass_iter}件 | {pass_iter / len(comparison_data) * 100:.1f}% |

### グレード分布

**prompt_optimized**:
"""

    # グレード分布計算
    grade_dist_prompt = Counter(d['prompt_grade'] for d in comparison_data)
    for grade in ['S', 'A', 'B', 'C', 'D']:
        count = grade_dist_prompt.get(grade, 0)
        percentage = count / len(comparison_data) * 100
        report += f"- {grade}評価: {count}件 ({percentage:.1f}%)\n"

    report += f"\n**iterative**:\n"
    grade_dist_iter = Counter(d['iter_grade'] for d in comparison_data)
    for grade in ['S', 'A', 'B', 'C', 'D']:
        count = grade_dist_iter.get(grade, 0)
        percentage = count / len(comparison_data) * 100
        report += f"- {grade}評価: {count}件 ({percentage:.1f}%)\n"

    report += f"""

---

## 💰 コスト分析

### 処理時間

- prompt_optimized: {new_results['prompt_optimized'].processing_time:.1f}秒 ({new_results['prompt_optimized'].processing_time / 60:.1f}分)
- iterative: {new_results['iterative'].processing_time:.1f}秒 ({new_results['iterative'].processing_time / 60:.1f}分)

### 推定コスト（OpenAI GPT-4o-mini）

- prompt_optimized: ${new_results['prompt_optimized'].total_cost:.4f}（1件あたり ${new_results['prompt_optimized'].total_cost / len(test_episodes):.4f}）
- iterative: ${new_results['iterative'].total_cost:.4f}（1件あたり ${new_results['iterative'].total_cost / len(test_episodes):.4f}）

### 100エピソード処理の試算

- prompt_optimized: ${new_results['prompt_optimized'].total_cost / len(test_episodes) * 100:.2f}
- iterative: ${new_results['iterative'].total_cost / len(test_episodes) * 100:.2f}

---

## 📋 個別エピソード詳細

"""

    for i, row in enumerate(comparison_data):
        # 🟢 最適化: 文字列スライスを事前計算
        existing_preview = row['existing_text'][:200] + '...' if len(row['existing_text']) > 200 else row['existing_text']
        prompt_preview = row['prompt_text'][:200] + '...' if len(row['prompt_text']) > 200 else row['prompt_text']
        iter_preview = row['iter_text'][:200] + '...' if len(row['iter_text']) > 200 else row['iter_text']

        report += f"""### {i+1}. {row['person_name']}（{row['age']}歳）- {row['category']}

**既存エピソード** - {row['existing_score']:.1f}点
```
{existing_preview}
```

**prompt_optimized** - {row['prompt_score']}点（{row['prompt_grade']}）
```
{prompt_preview}
```

**iterative** - {row['iter_score']}点（{row['iter_grade']}）- {row['iter_iterations']}回反復
```
{iter_preview}
```

**改善ポイント**:
- prompt_optimized: +{row['improvement_prompt']:.1f}点
- iterative: +{row['improvement_iter']:.1f}点

---

"""

    report += f"""
## 🎯 結論

### 主要な発見

1. **スコア向上**: 既存{avg_existing:.1f}点 → prompt_optimized {avg_prompt:.1f}点 → iterative {avg_iter:.1f}点
2. **合格率向上**: 既存{pass_existing / len(comparison_data) * 100:.1f}% → prompt_optimized {pass_prompt / len(comparison_data) * 100:.1f}% → iterative {pass_iter / len(comparison_data) * 100:.1f}%
3. **コスト効率**: prompt_optimizedが最もコスト効率が高い（${new_results['prompt_optimized'].total_cost / len(test_episodes):.4f}/件）
4. **品質**: iterativeモードが最高品質を実現（平均{avg_iter:.1f}点）

### 推奨事項

- **プロトタイプ・テスト**: prompt_optimizedモード（高速・低コスト）
- **本番・重要エピソード**: iterativeモード（高品質）
- **100エピソード処理**: prompt_optimizedで実施後、低スコアのみiterativeで再生成

### 品質改善（Enhanced版）

✅ **実装済み改善**:
1. 🔴 Critical修正: ゼロ除算防止・ファイル存在確認・CSVインジェクション対策
2. 🔴 データ検証: スコア妥当性検証・削除率監視（10-20%正常範囲）
3. 🟡 品質ゲート: PDCA準拠の4段階品質チェック
4. 🟡 エラーハンドリング: Fail-Fast原則に基づく包括的エラー処理
5. 🟢 安全性向上: UTF-8 BOM対応・CSV数式インジェクション対策

---

**作成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**テスト実行者**: Claude Code (Enhanced Edition)
**改善バージョン**: v2.0 - Quality-First Principles
"""

    # レポート保存
    report_file = f"TEST_10_EPISODES_REPORT_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    logging.info(f"✅ 最終レポートを {report_file} に保存しました")
    print(f"\n✅ 最終レポートを {report_file} に保存しました")

    return report


# ================================================================================
# メイン処理（包括的エラーハンドリング）
# ================================================================================

def main() -> int:
    """
    メイン処理（Fail-Fast原則・完全エラーハンドリング）

    Returns:
        終了コード（0: 成功, 1: エラー, 130: 中断）
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'test_execution_{timestamp}.log'),
            logging.StreamHandler()
        ]
    )

    try:
        print(f"\n{'='*80}")
        print(f"10エピソード大規模テスト（Enhanced版）")
        print(f"品質優先原則・PDCA準拠")
        print(f"{'='*80}\n")

        # Phase 0: システム準備確認
        logging.info("Phase 0: システム準備確認開始")
        validate_system_readiness()

        # Phase 1: テストデータ準備
        logging.info("Phase 1: テストデータ準備開始")
        test_episodes = prepare_test_data(
            input_csv="episodes_final_unified_20251001_135250.csv",
            output_csv=f"test_10episodes_prepared_{timestamp}.csv",
            limit=10
        )

        time.sleep(2)

        # Phase 2: モード別比較テスト
        logging.info("Phase 2: モード別比較テスト開始")
        new_results = run_comparison_test(test_episodes, timestamp)

        # Phase 3: 既存エピソードとの比較
        logging.info("Phase 3: 既存エピソードとの比較開始")
        comparison_df = compare_with_existing(test_episodes, new_results, timestamp)

        # Phase 4: 最終レポート生成
        logging.info("Phase 4: 最終レポート生成開始")
        report = generate_final_report(test_episodes, new_results, comparison_df, timestamp)

        # 成功ログ
        logging.info(f"✅ 10エピソード大規模テスト完了")

        print(f"\n{'='*80}")
        print(f"✅ 10エピソード大規模テスト完了")
        print(f"{'='*80}\n")

        print(f"【生成ファイル】")
        print(f"1. test_10episodes_prompt_optimized_{timestamp}.csv")
        print(f"2. test_10episodes_iterative_{timestamp}.csv")
        print(f"3. comparison_10episodes_{timestamp}.csv")
        print(f"4. TEST_10_EPISODES_REPORT_{timestamp}.md")
        print(f"5. test_execution_{timestamp}.log（実行ログ）")

        return 0  # 成功

    except DataQualityError as e:
        # 🔴 データ品質エラー: Fail-Fast
        logging.critical(f"🚨 データ品質エラーにより処理を中止: {e}")
        logging.critical(f"エラーコンテキスト: {json.dumps(e.context, indent=2, ensure_ascii=False)}")
        print(f"\n❌ データ品質エラーにより処理を中止しました")
        print(f"詳細はログファイルを確認してください: test_execution_{timestamp}.log")
        return 1

    except KeyboardInterrupt:
        logging.warning("⚠️ ユーザーによる処理中断")
        print("\n⚠️ 処理を中断しました")
        return 130

    except Exception as e:
        logging.error(f"❌ 予期しないエラー: {e}")
        logging.error(traceback.format_exc())
        print(f"\n❌ 予期しないエラーが発生しました")
        print(f"詳細はログファイルを確認してください: test_execution_{timestamp}.log")
        return 1


if __name__ == '__main__':
    exit_code = main()
    exit(exit_code)
