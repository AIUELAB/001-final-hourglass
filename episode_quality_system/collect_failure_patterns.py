#!/usr/bin/env python3
"""
失敗パターンを直接収集して分析
"""

import json
from pathlib import Path
from collections import defaultdict, Counter

def collect_failure_patterns():
    """失敗パターンの直接収集"""

    print("=" * 60)
    print("🔍 失敗パターン収集開始")
    print("=" * 60)

    # 既知の失敗パターン（テスト結果から）
    known_failures = [
        {
            'category': 'entertainment',
            'persons': ['松本人志', '新垣結衣', '米津玄師', '又吉直樹'],
            'common_issues': [
                '文字数不足: 128文字（最小132文字）',
                'テンプレート検出: ドラゴンボール作者',
                '作品名が必要（entertainment）'
            ]
        },
        {
            'category': 'literature',
            'persons': ['夏目漱石', '太宰治'],
            'common_issues': [
                '大手出版社などの一般的表現',
                'テンプレート検出: 近代日本文学の父'
            ]
        },
        {
            'category': 'business',
            'persons': ['稲盛和夫', '孫正義'],
            'common_issues': [
                '企業名・組織名が必要',
                'テンプレート検出: 京セラ創業'
            ]
        },
        {
            'category': 'science',
            'persons': ['山中伸弥', '湯川秀樹'],
            'common_issues': [
                '文字数不足: 68文字（最小132文字）',
                'テンプレート検出: 多くの.*?影響を与え'
            ]
        },
        {
            'category': 'sports',
            'persons': ['久保建英', '三浦知良'],
            'common_issues': [
                '大会名・リーグ名と具体的な記録が必要',
                '文字数不足: 124文字（最小132文字）',
                '繰り返し検出: プロ歴38年が重複'
            ]
        },
        {
            'category': 'history',
            'persons': ['坂本龍馬', '織田信長'],
            'common_issues': [
                '文字数不足: 67文字（最小132文字）',
                'テンプレート検出: この功績',
                'テンプレート検出: その後も.*?続け'
            ]
        }
    ]

    # パターン分析
    issue_patterns = defaultdict(Counter)
    category_issues = defaultdict(list)

    for failure in known_failures:
        category = failure['category']
        for issue in failure['common_issues']:
            # 問題タイプを分類
            if '文字数不足' in issue:
                issue_type = '文字数不足'
                # 文字数を抽出
                import re
                match = re.search(r'(\d+)文字', issue)
                if match:
                    char_count = int(match.group(1))
                    category_issues[category].append({
                        'type': issue_type,
                        'detail': f'平均{char_count}文字',
                        'severity': 'high'
                    })
            elif 'テンプレート検出' in issue:
                issue_type = 'テンプレート検出'
                template = issue.replace('テンプレート検出: ', '')
                category_issues[category].append({
                    'type': issue_type,
                    'detail': template,
                    'severity': 'medium'
                })
            elif '必要' in issue:
                issue_type = '固有名詞不足'
                category_issues[category].append({
                    'type': issue_type,
                    'detail': issue,
                    'severity': 'medium'
                })
            elif '繰り返し' in issue:
                issue_type = '繰り返し'
                category_issues[category].append({
                    'type': issue_type,
                    'detail': issue,
                    'severity': 'low'
                })
            else:
                issue_type = 'その他'
                category_issues[category].append({
                    'type': issue_type,
                    'detail': issue,
                    'severity': 'low'
                })

            issue_patterns[category][issue_type] += 1

    # 改善提案の生成
    print("\n【カテゴリ別問題分析】")
    print("=" * 60)

    improvements = {}

    for category, issues in issue_patterns.items():
        print(f"\n{category}カテゴリ:")
        improvements[category] = []

        for issue_type, count in issues.most_common():
            print(f"  {issue_type}: {count}件")

            if issue_type == '文字数不足':
                improvements[category].append({
                    'issue': '文字数不足',
                    'solution': 'テンプレートの拡張',
                    'actions': [
                        'impact部分を2文に拡張',
                        '実績を3つ以上含める',
                        '接続詞で自然につなぐ'
                    ]
                })
            elif issue_type == 'テンプレート検出':
                improvements[category].append({
                    'issue': 'テンプレート検出',
                    'solution': '検出ルールの調整',
                    'actions': [
                        f'{category}カテゴリ用の許可リスト作成',
                        '一般的すぎる表現を削除',
                        'カテゴリ固有の表現を許可'
                    ]
                })
            elif issue_type == '固有名詞不足':
                improvements[category].append({
                    'issue': '固有名詞不足',
                    'solution': '固有名詞パターン追加',
                    'actions': [
                        f'{category}用の必須キーワードリスト',
                        '事実データから自動抽出',
                        'カテゴリ別検証ルール'
                    ]
                })

    # 具体的な修正案
    print("\n" + "=" * 60)
    print("🔧 具体的な修正案")
    print("=" * 60)

    fixes = {
        'entertainment': {
            'template_expansions': [
                '「{work}」で{achievement}を達成し、{impact1}。さらに{fact1}、{fact2}の実績',
                '{age}歳で「{work}」を発表、{achievement}として評価。{numbers}の記録と{impact}の影響'
            ],
            'allowed_phrases': [
                '作品', '発表', '出演', '主演', '楽曲', '映画', 'ドラマ', '番組'
            ],
            'required_patterns': [
                '「.*?」',  # 作品名
                '\\d+.*?(本|枚|回|年)',  # 数値実績
            ]
        },
        'sports': {
            'template_expansions': [
                '{tournament}で{achievement}、{record}を記録。その後{fact1}、{fact2}という実績を重ねた',
                '{age}歳で{achievement}を達成、{tournament}での{record}。さらに{numbers}という成績'
            ],
            'allowed_phrases': [
                '大会', '優勝', 'メダル', '記録', '選手権', 'リーグ', '代表'
            ],
            'required_patterns': [
                '(オリンピック|世界選手権|W杯|ワールドカップ)',
                '\\d+.*?(勝|本|個|回|位)',
            ]
        },
        'science': {
            'template_expansions': [
                '{discovery}を発表し{award}を受賞、{impact1}。さらに{numbers}の研究成果と{impact2}への貢献',
                '{age}歳で{achievement}を達成、{field}分野で{discovery}。{publications}と{recognition}の評価'
            ],
            'allowed_phrases': [
                '研究', '発見', '理論', 'ノーベル賞', '論文', '発表', '開発'
            ],
            'required_patterns': [
                '(ノーベル|ラスカー|京都)賞',
                '\\d+.*?(編|件|年)',
            ]
        }
    }

    # 結果をJSON保存
    result = {
        'known_failures': known_failures,
        'issue_patterns': {k: dict(v) for k, v in issue_patterns.items()},
        'improvements': improvements,
        'fixes': fixes
    }

    output_file = "failure_patterns_analysis.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 分析結果保存: {output_file}")

    # サマリー表示
    print("\n" + "=" * 60)
    print("📊 分析サマリー")
    print("=" * 60)

    total_issues = sum(sum(issues.values()) for issues in issue_patterns.values())
    print(f"総問題数: {total_issues}件")

    print("\n問題タイプ別:")
    all_issues = Counter()
    for issues in issue_patterns.values():
        all_issues.update(issues)

    for issue_type, count in all_issues.most_common():
        percentage = count / total_issues * 100
        print(f"  {issue_type}: {count}件 ({percentage:.1f}%)")

    print("\n最優先改善事項:")
    print("  1. 文字数不足の解消（テンプレート拡張）")
    print("  2. テンプレート検出ルールの緩和")
    print("  3. カテゴリ別固有名詞パターンの追加")

    return result

if __name__ == "__main__":
    collect_failure_patterns()