#!/usr/bin/env python3
"""
episodes_final_complete_20250923_142019.csv 修正スクリプト

実行内容:
1. 年号の削除（21件のエピソード修正）
2. B列（user_age）の削除
3. 定型文の削除または別表現への置き換え
4. カテゴリ名の日本語統一
5. カラム構成の統合検証システム準拠への再設計
"""

import csv
import re
from datetime import datetime
from typing import Dict, List, Tuple
from unified_validation_system_with_persistence import create_validator


# 定型文パターン
TEMPLATE_PATTERNS = [
    "日本中が歓喜に包まれ、次世代アスリートたちに夢と希望を与えた瞬間だった。",
    "この瞬間から始まった物語は、今も多くの人々に夢を与えている。",
    "数多くの名作を世に送り出した。作品は世代を超えて愛され、日本文学の宝となっている。",
    "この作品は時代を超えて読み継がれ、多くの読者の心に深い感動を与え続けている。",
    "この楽曲は時代の象徴となり、多くのリスナーの心に深く刻まれた。",
    "この技術革新は未来への扉を開き、次世代のイノベーターたちに大きなインスピレーションを与えた。",
    "この受賞は日本のエンターテインメント界の実力を世界に示す快挙となった。",
    "このスタートアップは後に業界を変革し、新たなビジネスモデルの先駆けとなった。",
    "この挑戦が現代のビジネスシーンを形作っている。",
]

# カテゴリ名の日本語統一マップ
CATEGORY_MAP = {
    "sports": "スポーツ",
    "entertainment": "エンターテインメント",
    "music": "音楽",
    "business": "ビジネス",
    "literature": "文学",
    "technology": "テクノロジー",
    "science": "科学",
    "政治・社会": "政治",
    "科学・研究": "科学",
    "医学・健康": "医学",
    "文化・芸術": "文化",
    "アニメーション": "アニメ",
    "映画": "映画",
    "漫画": "漫画",
    "将棋": "将棋",
    "芸術": "芸術",
    "建築": "建築",
    "教育": "教育",
    "伝統芸能": "伝統芸能",
    "政治": "政治",
}


def remove_years(text: str) -> str:
    """年号・日付を削除"""
    # 西暦年（例: 2007年、1995年）
    text = re.sub(r'\d{4}年(?:\d{1,2}月)?(?:\d{1,2}日)?', '', text)

    # 和暦年（例: 令和元年、平成30年）
    text = re.sub(r'(?:明治|大正|昭和|平成|令和)\d{1,2}年', '', text)

    # 年代表記（例: 2020年代）
    text = re.sub(r'\d{4}年代', '', text)

    # 連続する空白を1つに
    text = re.sub(r'\s+', '', text)

    return text


def remove_templates(text: str) -> str:
    """定型文を削除"""
    for pattern in TEMPLATE_PATTERNS:
        text = text.replace(pattern, '')

    # 連続する空白を1つに
    text = re.sub(r'\s+', '', text)

    return text


def normalize_category(category: str) -> str:
    """カテゴリ名を日本語に統一"""
    return CATEGORY_MAP.get(category, category)


def process_csv(input_path: str, output_path: str) -> Dict:
    """CSVファイルを処理"""
    validator = create_validator()

    # 統計情報
    stats = {
        "total": 0,
        "year_removed": 0,
        "template_removed": 0,
        "category_normalized": 0,
        "too_short": 0,
        "validation_failed": 0,
        "validation_passed": 0,
    }

    # 入力CSVを読み込み
    with open(input_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    stats["total"] = len(rows)

    # 各行を処理
    processed_rows = []

    for row in rows:
        person_name = row['person_name']
        episode_age = int(row['episode_age'])
        episode_text = row['episode_text']
        category = row['category']

        # 元のテキストを保存
        original_text = episode_text

        # 1. 年号削除
        episode_text_no_year = remove_years(episode_text)
        if episode_text_no_year != episode_text:
            stats["year_removed"] += 1

        # 2. 定型文削除
        episode_text_clean = remove_templates(episode_text_no_year)
        if episode_text_clean != episode_text_no_year:
            stats["template_removed"] += 1

        # 3. カテゴリ正規化
        normalized_category = normalize_category(category)
        if normalized_category != category:
            stats["category_normalized"] += 1

        # 文字数チェック
        char_count = len(episode_text_clean)

        if char_count < 130:
            # 文字数不足の場合は元のテキストから年号のみ削除
            episode_text_clean = episode_text_no_year
            char_count = len(episode_text_clean)
            stats["too_short"] += 1

            # それでも130文字未満なら元のテキストを使用
            if char_count < 130:
                episode_text_clean = original_text
                char_count = len(episode_text_clean)

        # 統合検証システムで検証
        episode_dict = {
            "episode_id": f"E{stats['total']:03d}",
            "person_id": f"P{stats['total']:03d}",
            "person_name": person_name,
            "display_name": person_name,
            "episode_text": episode_text_clean,
            "episode_age": episode_age,
            "user_age": episode_age,  # 同じ値
            "occupation": "不明",
            "category": normalized_category
        }

        validation_result = validator.validate_episode(episode_dict)

        if validation_result.is_valid:
            stats["validation_passed"] += 1
        else:
            stats["validation_failed"] += 1

        # 新しいカラム構成で出力
        processed_row = {
            "person_name": person_name,
            "episode_age": episode_age,
            "episode_text": episode_text_clean,
            "episode_type": "iconic",  # 既存データは定番エピソードとして扱う
            "character_count": char_count,
            "category": normalized_category,
            "is_valid": validation_result.is_valid,
            "violation_count": len(validation_result.violations),
            "emotional_impact_score": validation_result.emotional_impact_score,
            "specificity_score": validation_result.specificity_score,
            "has_numerical_data": has_numerical_data(episode_text_clean),
            "has_proper_nouns": has_proper_nouns(episode_text_clean),
            "fact_check_status": row.get('fact_check_status', 'pending'),
            "created_date": datetime.now().strftime("%Y%m%d_%H%M%S")
        }

        processed_rows.append(processed_row)

    # 出力CSVに書き込み
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = [
            "person_name",
            "episode_age",
            "episode_text",
            "episode_type",
            "character_count",
            "category",
            "is_valid",
            "violation_count",
            "emotional_impact_score",
            "specificity_score",
            "has_numerical_data",
            "has_proper_nouns",
            "fact_check_status",
            "created_date"
        ]

        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(processed_rows)

    return stats


def has_numerical_data(text: str) -> bool:
    """数値データの有無を判定"""
    numerical_patterns = [
        r'\d+[歳億万千百十回連覇勝本枚冊人件個]',
        r'\d+年間',
        r'\d+シーズン',
        r'\d+位',
        r'\d+円',
        r'\d+ドル',
        r'\d+%',
    ]
    return any(re.search(pattern, text) for pattern in numerical_patterns)


def has_proper_nouns(text: str) -> bool:
    """固有名詞の有無を判定（簡易版）"""
    # カタカナ連続3文字以上、漢字3文字以上の大会名・作品名等
    patterns = [
        r'[ァ-ヶー]{3,}',  # カタカナ3文字以上
        r'『[^』]+』',  # 作品名
        r'「[^」]+」',  # 大会名・団体名
    ]
    return any(re.search(pattern, text) for pattern in patterns)


def main():
    """メイン処理"""
    input_path = "episodes_final_complete_20250923_142019.csv"
    output_path = f"episodes_fixed_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

    print("=" * 80)
    print("CSV修正スクリプト - 実行開始")
    print("=" * 80)
    print(f"\n入力: {input_path}")
    print(f"出力: {output_path}\n")

    # 処理実行
    stats = process_csv(input_path, output_path)

    # 結果表示
    print("\n" + "=" * 80)
    print("処理完了")
    print("=" * 80)
    print(f"\n総レコード数: {stats['total']}件")
    print(f"\n【修正統計】")
    print(f"  年号削除: {stats['year_removed']}件")
    print(f"  定型文削除: {stats['template_removed']}件")
    print(f"  カテゴリ正規化: {stats['category_normalized']}件")
    print(f"  文字数不足: {stats['too_short']}件")
    print(f"\n【検証結果】")
    print(f"  合格: {stats['validation_passed']}件 ({stats['validation_passed']/stats['total']*100:.1f}%)")
    print(f"  不合格: {stats['validation_failed']}件 ({stats['validation_failed']/stats['total']*100:.1f}%)")
    print(f"\n出力ファイル: {output_path}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
