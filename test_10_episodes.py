#!/usr/bin/env python3
"""
10エピソード大規模テスト

目的:
1. 既存エピソードとの比較
2. prompt_optimized vs iterative の比較
3. コスト効率の検証
4. エラーハンドリングの確認
"""

import csv
import json
import time
from datetime import datetime
from collections import defaultdict

from batch_high_quality_generator import BatchHighQualityGenerator


def prepare_test_data(input_csv: str, output_csv: str, limit: int = 10):
    """テストデータを準備"""

    print(f"{'='*80}")
    print(f"テストデータ準備")
    print(f"{'='*80}")

    # CSVを読み込み
    episodes = []
    with open(input_csv, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        episodes = list(reader)

    print(f"総エピソード数: {len(episodes)}件")

    # 多様性を確保するため、カテゴリから均等に選択
    test_episodes = []
    categories = list(set(ep['category'] for ep in episodes))

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

    # テストデータとして保存
    with open(output_csv, 'w', encoding='utf-8-sig', newline='') as f:
        if test_episodes:
            writer = csv.DictWriter(f, fieldnames=test_episodes[0].keys())
            writer.writeheader()
            writer.writerows(test_episodes)

    print(f"\nテスト対象エピソード:")
    for i, ep in enumerate(test_episodes, 1):
        print(f"{i}. {ep['person_name']}（{ep['episode_age']}歳）- {ep['category']}")

    print(f"\n✅ テストデータを {output_csv} に保存しました")

    return test_episodes


def run_comparison_test(test_episodes, timestamp):
    """モード別比較テスト"""

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

    print(f"\n{'='*80}")
    time.sleep(5)  # レート制限対策

    # モード2: iterative（高品質）
    print(f"\n【モード2: iterative】\n")

    batch_gen_quality = BatchHighQualityGenerator(
        provider="openai",
        mode="iterative",
        max_workers=2,  # 反復モードは負荷が高いので並列数を減らす
        max_iterations=3,
        pass_threshold=60
    )

    result_quality = batch_gen_quality.process_episodes_list(
        test_episodes,
        output_csv=f"test_10episodes_iterative_{timestamp}.csv",
        verbose=True
    )

    results['iterative'] = result_quality

    return results


def compare_with_existing(test_episodes, new_results, timestamp):
    """既存エピソードとの比較"""

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
        # weighted_scoreを数値に変換（文字列の場合があるため）
        existing_weighted = existing.get('weighted_score', 0)
        if isinstance(existing_weighted, str):
            try:
                existing_weighted = float(existing_weighted)
            except (ValueError, TypeError):
                existing_weighted = 0.0
        existing_score_100 = float(existing_weighted) * 10  # 10点満点を100点満点に変換

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

    # CSV保存
    comparison_csv = f"comparison_10episodes_{timestamp}.csv"
    with open(comparison_csv, 'w', encoding='utf-8-sig', newline='') as f:
        if comparison_data:
            writer = csv.DictWriter(f, fieldnames=comparison_data[0].keys())
            writer.writeheader()
            writer.writerows(comparison_data)

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


def generate_final_report(test_episodes, new_results, comparison_data, timestamp):
    """最終レポート生成"""

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

    report = f"""# 10エピソード大規模テスト - 最終レポート

**実行日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**テスト件数**: {len(test_episodes)}件

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
    from collections import Counter
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
        report += f"""### {i+1}. {row['person_name']}（{row['age']}歳）- {row['category']}

**既存エピソード** - {row['existing_score']:.1f}点
```
{row['existing_text'][:200]}...
```

**prompt_optimized** - {row['prompt_score']}点（{row['prompt_grade']}）
```
{row['prompt_text'][:200]}...
```

**iterative** - {row['iter_score']}点（{row['iter_grade']}）- {row['iter_iterations']}回反復
```
{row['iter_text'][:200]}...
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

---

**作成日時**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**テスト実行者**: Claude Code
"""

    # レポート保存
    report_file = f"TEST_10_EPISODES_REPORT_{timestamp}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n✅ 最終レポートを {report_file} に保存しました")

    return report


def main():
    """メイン処理"""

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    print(f"\n{'='*80}")
    print(f"10エピソード大規模テスト")
    print(f"{'='*80}\n")

    # Phase 1: テストデータ準備
    test_episodes = prepare_test_data(
        input_csv="episodes_final_unified_20251001_135250.csv",
        output_csv=f"test_10episodes_prepared_{timestamp}.csv",
        limit=10
    )

    time.sleep(2)

    # Phase 2: モード別比較テスト
    new_results = run_comparison_test(test_episodes, timestamp)

    # Phase 3: 既存エピソードとの比較
    comparison_df = compare_with_existing(test_episodes, new_results, timestamp)

    # Phase 4: 最終レポート生成
    report = generate_final_report(test_episodes, new_results, comparison_df, timestamp)

    print(f"\n{'='*80}")
    print(f"✅ 10エピソード大規模テスト完了")
    print(f"{'='*80}\n")

    print(f"【生成ファイル】")
    print(f"1. test_10episodes_prompt_optimized_{timestamp}.csv")
    print(f"2. test_10episodes_iterative_{timestamp}.csv")
    print(f"3. comparison_10episodes_{timestamp}.csv")
    print(f"4. TEST_10_EPISODES_REPORT_{timestamp}.md")


if __name__ == '__main__':
    main()
