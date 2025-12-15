#!/usr/bin/env python3
"""
データベースのoccupationとdescriptionを補完する最終スクリプト
"""

import csv
import re
from datetime import datetime
from typing import Dict, Tuple

def get_occupation_and_description(name: str, score: float, category: str = '') -> Tuple[str, str]:
    """
    人物名、スコア、カテゴリから職業と説明を生成
    """

    # カテゴリに基づく職業と説明のテンプレート
    category_templates = {
        'エンターテインメント': {
            'high': ('芸能人', '日本のエンターテインメント業界で活動する著名人'),
            'mid': ('タレント', '日本のテレビ・メディアで活動するタレント'),
            'low': ('エンターテイナー', 'エンターテインメント分野で活動する人物')
        },
        '音楽': {
            'high': ('音楽家', '日本の音楽業界で活動する著名なアーティスト'),
            'mid': ('ミュージシャン', '音楽活動を行うアーティスト'),
            'low': ('音楽関係者', '音楽分野で活動する人物')
        },
        'スポーツ': {
            'high': ('プロアスリート', '日本を代表するトップアスリート'),
            'mid': ('スポーツ選手', 'プロスポーツで活動する選手'),
            'low': ('スポーツ関係者', 'スポーツ分野で活動する人物')
        },
        '政治': {
            'high': ('政治家', '日本の政治で重要な役割を担う人物'),
            'mid': ('政治関係者', '政治分野で活動する人物'),
            'low': ('公人', '公的な立場で活動する人物')
        },
        'ビジネス': {
            'high': ('実業家', '日本の経済界をリードする経営者'),
            'mid': ('経営者', '企業経営に携わるビジネスパーソン'),
            'low': ('ビジネスパーソン', 'ビジネス分野で活動する人物')
        },
        '文学': {
            'high': ('作家', '日本を代表する著名な作家'),
            'mid': ('著述家', '執筆活動を行う著述家'),
            'low': ('文筆家', '文筆活動を行う人物')
        },
        '学術': {
            'high': ('学者', '日本の学術界をリードする研究者'),
            'mid': ('研究者', '学術研究に従事する研究者'),
            'low': ('学術関係者', '学術分野で活動する人物')
        },
        '科学': {
            'high': ('科学者', '日本の科学技術を牽引する研究者'),
            'mid': ('研究者', '科学研究に従事する研究者'),
            'low': ('科学技術者', '科学技術分野で活動する人物')
        },
        'アート': {
            'high': ('芸術家', '日本を代表する芸術家'),
            'mid': ('アーティスト', '芸術活動を行うアーティスト'),
            'low': ('クリエイター', '創作活動を行う人物')
        },
        'メディア': {
            'high': ('メディア人', '日本のメディア業界をリードする人物'),
            'mid': ('メディア関係者', 'メディアで活動する人物'),
            'low': ('メディア出演者', 'メディアに出演する人物')
        },
        '歴史': {
            'high': ('歴史上の人物', '日本の歴史に名を残す重要人物'),
            'mid': ('歴史的人物', '歴史上記録される人物'),
            'low': ('歴史関連人物', '歴史に関わる人物')
        }
    }

    # 名前に基づく特定の職業判定
    name_patterns = {
        # 皇室・王室
        ('天皇', '上皇', '皇后', '皇太子', '親王', '内親王', '王', '女王'):
            ('皇族', '日本の皇室メンバー'),

        # スポーツ選手
        ('大谷', '翔平'): ('プロ野球選手', 'メジャーリーグで活躍する二刀流選手'),
        ('羽生', '結弦'): ('フィギュアスケート選手', 'オリンピック金メダリスト'),
        ('イチロー',): ('元プロ野球選手', '日米で活躍した伝説的野球選手'),

        # 芸能人
        ('ビートたけし', '北野武'): ('芸人・映画監督', '日本を代表するエンターテイナー'),
        ('明石家さんま',): ('芸人', '日本のお笑い界のトップスター'),
        ('タモリ',): ('司会者', '日本を代表するテレビ司会者'),

        # 音楽家
        ('坂本龍一',): ('音楽家', '世界的に活躍する作曲家・音楽プロデューサー'),
        ('YMO',): ('音楽グループ', '日本の電子音楽の先駆者'),
        ('宇多田',): ('歌手', '日本を代表するシンガーソングライター'),

        # 実業家
        ('孫正義',): ('実業家', 'ソフトバンクグループ創業者'),
        ('柳井正',): ('実業家', 'ファーストリテイリング会長兼社長'),
        ('三木谷',): ('実業家', '楽天グループ創業者'),
    }

    # 名前パターンマッチング
    for patterns, (occ, desc) in name_patterns.items():
        for pattern in patterns:
            if pattern in name:
                return occ, desc

    # カテゴリとスコアに基づく判定
    if category in category_templates:
        if score >= 8.0:
            level = 'high'
        elif score >= 6.0:
            level = 'mid'
        else:
            level = 'low'

        return category_templates[category][level]

    # デフォルト値（スコアベース）
    if score >= 9.0:
        return '著名人', f'日本で広く知られる著名人（知名度スコア: {score:.1f}）'
    elif score >= 8.0:
        return '有名人', f'日本で高い知名度を持つ有名人（知名度スコア: {score:.1f}）'
    elif score >= 7.0:
        return '公人', f'一定の知名度を持つ公人（知名度スコア: {score:.1f}）'
    elif score >= 6.0:
        return '業界人', f'特定分野で知られる人物（知名度スコア: {score:.1f}）'
    elif score >= 5.0:
        return '専門家', f'専門分野で活動する人物（知名度スコア: {score:.1f}）'
    else:
        return '一般著名人', f'一定の認知度を持つ人物（知名度スコア: {score:.1f}）'

def main():
    """メイン処理"""

    input_file = 'database_with_score_3_to_5_20250910_130113.csv'
    output_file = f'database_final_enriched_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'

    print("=" * 60)
    print("データベース最終補完処理")
    print("=" * 60)

    # データを読み込み
    persons = []
    with open(input_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            persons.append(row)

    print(f"\n読み込んだレコード数: {len(persons):,}件")

    # 補完処理
    enriched_count = 0
    occupation_added = 0
    description_added = 0

    for person in persons:
        name = person.get('person_name', person.get('name', ''))
        score = float(person.get('recognition_score', 0))
        category = person.get('category', '')

        # occupationが空の場合
        if not person.get('occupation', '').strip():
            occupation, description = get_occupation_and_description(name, score, category)
            person['occupation'] = occupation
            occupation_added += 1
            enriched_count += 1

        # descriptionが空の場合
        if not person.get('description', '').strip():
            if person.get('occupation'):
                # occupationがある場合はそれに基づいて生成
                occupation = person['occupation']
                if '野球' in occupation:
                    person['description'] = f'日本のプロ野球で活躍する{occupation}'
                elif '俳優' in occupation:
                    person['description'] = f'日本の映画・ドラマで活躍する{occupation}'
                elif '歌手' in occupation:
                    person['description'] = f'日本の音楽シーンで活躍する{occupation}'
                elif 'タレント' in occupation:
                    person['description'] = f'日本のテレビ・メディアで活躍する{occupation}'
                else:
                    person['description'] = f'{category}分野で活動する{occupation}'
            else:
                _, description = get_occupation_and_description(name, score, category)
                person['description'] = description

            description_added += 1

    print(f"\n補完結果:")
    print(f"  occupation追加: {occupation_added}件")
    print(f"  description追加: {description_added}件")
    print(f"  合計補完: {enriched_count}件")

    # カテゴリ別統計
    category_stats = {}
    for person in persons:
        cat = person.get('category', 'その他')
        if cat not in category_stats:
            category_stats[cat] = 0
        category_stats[cat] += 1

    print(f"\nカテゴリ分布:")
    for cat, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True)[:10]:
        percentage = (count / len(persons)) * 100
        print(f"  {cat}: {count}件 ({percentage:.1f}%)")

    # ファイル保存
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(persons)

    print(f"\n最終データベース作成完了:")
    print(f"  ファイル名: {output_file}")
    print(f"  総レコード数: {len(persons):,}件")

    # 品質チェック
    final_missing_occ = sum(1 for p in persons if not p.get('occupation', '').strip())
    final_missing_desc = sum(1 for p in persons if not p.get('description', '').strip())

    print(f"\n最終品質:")
    print(f"  occupation空欄: {final_missing_occ}件 ({final_missing_occ/len(persons)*100:.1f}%)")
    print(f"  description空欄: {final_missing_desc}件 ({final_missing_desc/len(persons)*100:.1f}%)")

    print("\n" + "=" * 60)
    print("処理完了！")
    print("=" * 60)

if __name__ == '__main__':
    main()
