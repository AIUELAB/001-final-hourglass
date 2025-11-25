#!/usr/bin/env python3
"""
バリデーション失敗パターンを分析して改善点を特定
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from unified_episode_factory import UnifiedEpisodeFactory, EpisodeGenerationRequest

def analyze_validation_failures():
    """バリデーション失敗パターンの詳細分析"""

    print("=" * 60)
    print("🔍 バリデーション失敗分析開始")
    print("=" * 60)

    # ファクトリー初期化
    factory = UnifiedEpisodeFactory()

    # テスト対象（失敗しやすいパターンを重点的に）
    test_cases = [
        # entertainment（失敗率高）
        ("松本人志", 27, "entertainment"),
        ("新垣結衣", 28, "entertainment"),
        ("米津玄師", 27, "entertainment"),
        ("又吉直樹", 35, "entertainment"),
        ("Ado", 21, "entertainment"),

        # literature（テンプレート問題）
        ("夏目漱石", 40, "literature"),
        ("太宰治", 30, "literature"),

        # business（固有名詞問題）
        ("稲盛和夫", 27, "business"),
        ("孫正義", 33, "business"),

        # science（文字数不足）
        ("山中伸弥", 50, "science"),
        ("湯川秀樹", 28, "science"),

        # sports（繰り返し問題）
        ("久保建英", 18, "sports"),
        ("三浦知良", 30, "sports"),

        # history（文字数不足）
        ("坂本龍馬", 31, "history"),
        ("織田信長", 35, "history"),
    ]

    # 失敗パターン収集
    failure_patterns = defaultdict(list)
    stage_failures = Counter()
    validation_issues = defaultdict(list)

    for person_name, age, category in test_cases:
        print(f"\n分析: {person_name} ({category})")

        # 詳細モードでエピソード生成を試行
        request = EpisodeGenerationRequest(
            person_name=person_name,
            age=age,
            category=category,
            min_quality_score=70.0,
            max_attempts=1,  # 1回のみで失敗パターンを収集
            strict_mode=True
        )

        response = factory.generate(request)

        # パイプライン結果の分析
        if response.pipeline_result:
            for stage in response.pipeline_result.stages:
                if not stage.success:
                    stage_failures[stage.stage_name] += 1
                    failure_patterns[category].append({
                        'person': person_name,
                        'stage': stage.stage_name,
                        'issues': stage.issues
                    })

                    # 詳細な問題を記録
                    for issue in stage.issues:
                        validation_issues[stage.stage_name].append({
                            'category': category,
                            'person': person_name,
                            'issue': issue
                        })

        # バリデーション結果の分析
        if response.validation_result:
            for issue in response.validation_result.issues:
                print(f"  - {issue.validator}: {issue.message}")

    # 分析結果の集計
    print("\n" + "=" * 60)
    print("📊 失敗パターン分析結果")
    print("=" * 60)

    # ステージ別失敗率
    print("\n【ステージ別失敗回数】")
    for stage, count in stage_failures.most_common():
        print(f"  {stage}: {count}回")

    # カテゴリ別失敗パターン
    print("\n【カテゴリ別失敗パターン】")
    for category, failures in failure_patterns.items():
        print(f"\n{category} ({len(failures)}件):")

        # このカテゴリで最も多い失敗ステージ
        stage_counts = Counter(f['stage'] for f in failures)
        for stage, count in stage_counts.most_common(3):
            print(f"  - {stage}: {count}回")

    # 最も多い検証問題
    print("\n【検証問題Top10】")
    all_issues = []
    for stage_issues in validation_issues.values():
        all_issues.extend([issue['issue'] for issue in stage_issues])

    issue_counter = Counter(all_issues)
    for issue, count in issue_counter.most_common(10):
        print(f"  {count}回: {issue[:60]}...")

    # カテゴリ別の詳細分析
    print("\n【カテゴリ別詳細分析】")

    category_analysis = {}
    for category in ["entertainment", "literature", "business", "science", "sports", "history"]:
        category_issues = defaultdict(int)

        for stage_name, issues in validation_issues.items():
            for issue_data in issues:
                if issue_data['category'] == category:
                    # 問題のタイプを分類
                    issue_text = issue_data['issue']
                    if "文字数不足" in issue_text:
                        category_issues['文字数不足'] += 1
                    elif "テンプレート検出" in issue_text:
                        category_issues['テンプレート'] += 1
                    elif "固有名詞" in issue_text or "作品名" in issue_text:
                        category_issues['固有名詞不足'] += 1
                    elif "繰り返し" in issue_text:
                        category_issues['繰り返し'] += 1
                    elif "客観性" in issue_text:
                        category_issues['客観性'] += 1
                    else:
                        category_issues['その他'] += 1

        if category_issues:
            category_analysis[category] = dict(category_issues)
            print(f"\n{category}:")
            for issue_type, count in sorted(category_issues.items(), key=lambda x: x[1], reverse=True):
                print(f"  {issue_type}: {count}回")

    # 改善提案を生成
    print("\n" + "=" * 60)
    print("💡 改善提案")
    print("=" * 60)

    recommendations = []

    # カテゴリ別の提案
    for category, issues in category_analysis.items():
        if not issues:
            continue

        print(f"\n【{category}カテゴリ】")

        if issues.get('文字数不足', 0) > 0:
            print("  ⚠️ 文字数不足が頻発")
            print("    → テンプレートの拡張が必要")
            print("    → impact部分の詳細化")
            recommendations.append({
                'category': category,
                'issue': '文字数不足',
                'solution': 'テンプレート拡張'
            })

        if issues.get('テンプレート', 0) > 0:
            print("  ⚠️ テンプレート検出が過敏")
            print("    → 禁止フレーズリストの見直し")
            print("    → カテゴリ別の許容表現追加")
            recommendations.append({
                'category': category,
                'issue': 'テンプレート検出',
                'solution': '検出ルール緩和'
            })

        if issues.get('固有名詞不足', 0) > 0:
            print("  ⚠️ 固有名詞が不足")
            print("    → カテゴリ別の固有名詞パターン追加")
            print("    → 事実データからの自動抽出強化")
            recommendations.append({
                'category': category,
                'issue': '固有名詞不足',
                'solution': 'パターン追加'
            })

    # 結果を保存
    analysis_result = {
        'test_count': len(test_cases),
        'stage_failures': dict(stage_failures),
        'category_analysis': category_analysis,
        'recommendations': recommendations,
        'top_issues': [{'issue': issue, 'count': count} for issue, count in issue_counter.most_common(10)]
    }

    output_file = "validation_failure_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(analysis_result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 分析結果保存: {output_file}")

    return analysis_result

if __name__ == "__main__":
    analyze_validation_failures()
