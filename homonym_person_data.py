#!/usr/bin/env python3
"""
同姓同名人物のデータ定義
Wikipediaおよび検索結果から特定された実在の人物情報
"""

# 同姓同名人物の詳細データ
# 各人物には新しいperson_IDを割り当て、適切な情報を設定
HOMONYM_PERSONS = {
    # 田中太郎（データベースには無いが例として）
    'P004406': [  # 元の田中次郎
        {
            'new_id': 'P100001',
            'person_name': '田中太郎',
            'person_name_display': '田中太郎 (社会事業家)',
            'person_name_ja': '田中太郎',
            'category': '社会活動',
            'nationality': '日本',
            'occupation': '社会事業家',
            'description': '明治・大正期の社会事業家（1870-1932）',
            'recognition_score': 6.5
        },
        {
            'new_id': 'P100002',
            'person_name': '田中太郎',
            'person_name_display': '田中太郎 (実業家)',
            'person_name_ja': '田中太郎',
            'category': 'ビジネス',
            'nationality': '日本',
            'occupation': '実業家',
            'description': '元近鉄百貨店社長（1932-2020）',
            'recognition_score': 6.0
        },
        {
            'new_id': 'P100003',
            'person_name': '田中太郎',
            'person_name_display': '田中太郎 (声優)',
            'person_name_ja': '田中太郎',
            'category': 'エンタメ',
            'nationality': '日本',
            'occupation': '声優',
            'description': '男性声優（1985年生まれ）、2019年引退',
            'recognition_score': 5.0
        }
    ],
    
    # 佐藤直樹
    'P002051': [
        {
            'new_id': 'P100004',
            'person_name': '佐藤直樹',
            'person_name_display': '佐藤直樹 (野球)',
            'person_name_ja': '佐藤直樹',
            'category': 'スポーツ',
            'nationality': '日本',
            'occupation': 'プロ野球選手',
            'description': '福岡ソフトバンクホークス外野手（1998年生まれ）',
            'recognition_score': 7.0
        },
        {
            'new_id': 'P100005',
            'person_name': '佐藤直樹',
            'person_name_display': '佐藤直樹 (日活社長)',
            'person_name_ja': '佐藤直樹',
            'category': 'ビジネス',
            'nationality': '日本',
            'occupation': '実業家',
            'description': '日活株式会社社長、映画プロデューサー（1963年生まれ）',
            'recognition_score': 6.5
        },
        {
            'new_id': 'P100006',
            'person_name': '佐藤直樹',
            'person_name_display': '佐藤直樹 (法学者)',
            'person_name_ja': '佐藤直樹',
            'category': '学術',
            'nationality': '日本',
            'occupation': '法学者',
            'description': '九州工業大学名誉教授、刑事法学専攻（1951年生まれ）',
            'recognition_score': 6.0
        },
        {
            'new_id': 'P100007',
            'person_name': '佐藤直樹',
            'person_name_display': '佐藤直樹 (デザイナー)',
            'person_name_ja': '佐藤直樹',
            'category': '文化・芸術',
            'nationality': '日本',
            'occupation': 'グラフィックデザイナー',
            'description': '多摩美術大学教授、アートディレクター（1961年生まれ）',
            'recognition_score': 6.5
        }
    ],
    
    # 鈴木健太
    'P005185': [
        {
            'new_id': 'P100008',
            'person_name': '鈴木健太',
            'person_name_display': '鈴木健太 (秋田県知事)',
            'person_name_ja': '鈴木健太',
            'category': '政治',
            'nationality': '日本',
            'occupation': '政治家',
            'description': '第21代秋田県知事、元自衛官・司法書士（1975年生まれ）',
            'recognition_score': 8.5
        },
        {
            'new_id': 'P100009',
            'person_name': '鈴木健太',
            'person_name_display': '鈴木健太 (クリエイター)',
            'person_name_ja': '鈴木健太',
            'category': '文化・芸術',
            'nationality': '日本',
            'occupation': '映像作家',
            'description': 'クリエイティブディレクター、映像作家（1996年生まれ）',
            'recognition_score': 6.5
        },
        {
            'new_id': 'P100010',
            'person_name': '鈴木健太',
            'person_name_display': '鈴木健太 (サッカー)',
            'person_name_ja': '鈴木健太',
            'category': 'スポーツ',
            'nationality': '日本',
            'occupation': '元サッカー選手',
            'description': '元プロサッカー選手、MF（1985年生まれ）',
            'recognition_score': 5.5
        },
        {
            'new_id': 'P100011',
            'person_name': '鈴木健太',
            'person_name_display': '鈴木健太 (アナウンサー)',
            'person_name_ja': '鈴木健太',
            'category': 'エンタメ',
            'nationality': '日本',
            'occupation': 'アナウンサー',
            'description': 'MBS（毎日放送）元アナウンサー（1984年生まれ）',
            'recognition_score': 6.0
        }
    ],
    
    # 中村太郎
    'P001662': [
        {
            'new_id': 'P100012',
            'person_name': '中村太郎',
            'person_name_display': '中村太郎',
            'person_name_ja': '中村太郎',
            'category': 'その他',
            'nationality': '日本',
            'occupation': '一般人',
            'description': '特定の著名人物が見つからない一般的な名前',
            'recognition_score': 3.0
        }
    ],
    
    # 田中愛
    'P004401': [
        {
            'new_id': 'P100013',
            'person_name': '田中愛',
            'person_name_display': '田中愛',
            'person_name_ja': '田中愛',
            'category': 'エンタメ',
            'nationality': '日本',
            'occupation': 'タレント',
            'description': '女性タレント、モデル',
            'recognition_score': 5.0
        }
    ],
    
    # 山本健太
    'P003039': [
        {
            'new_id': 'P100014',
            'person_name': '山本健太',
            'person_name_display': '山本健太',
            'person_name_ja': '山本健太',
            'category': 'その他',
            'nationality': '日本',
            'occupation': '一般人',
            'description': '特定の著名人物が見つからない一般的な名前',
            'recognition_score': 3.0
        }
    ],
    
    # 高橋三郎
    'P005412': [
        {
            'new_id': 'P100015',
            'person_name': '高橋三郎',
            'person_name_display': '高橋三郎',
            'person_name_ja': '高橋三郎',
            'category': 'その他',
            'nationality': '日本',
            'occupation': '一般人',
            'description': '特定の著名人物が見つからない一般的な名前',
            'recognition_score': 3.0
        }
    ],
    
    # 渡辺直樹と渡邊直樹（同一人物の可能性もあるが別々に扱う）
    'P004264': [
        {
            'new_id': 'P100016',
            'person_name': '渡辺直樹',
            'person_name_display': '渡辺直樹',
            'person_name_ja': '渡辺直樹',
            'category': 'その他',
            'nationality': '日本',
            'occupation': '一般人',
            'description': '特定の著名人物が見つからない一般的な名前',
            'recognition_score': 3.0
        }
    ],
    
    'P004290': [
        {
            'new_id': 'P100017',
            'person_name': '渡邊直樹',
            'person_name_display': '渡邊直樹',
            'person_name_ja': '渡邊直樹',
            'category': 'その他',
            'nationality': '日本',
            'occupation': '一般人',
            'description': '特定の著名人物が見つからない一般的な名前',
            'recognition_score': 3.0
        }
    ],
    
    # 井上翔太
    'P001793': [
        {
            'new_id': 'P100018',
            'person_name': '井上翔太',
            'person_name_display': '井上翔太',
            'person_name_ja': '井上翔太',
            'category': 'その他',
            'nationality': '日本',
            'occupation': '一般人',
            'description': '特定の著名人物が見つからない一般的な名前',
            'recognition_score': 3.0
        }
    ],
    
    # 佐藤翔
    'P002057': [
        {
            'new_id': 'P100019',
            'person_name': '佐藤翔',
            'person_name_display': '佐藤翔',
            'person_name_ja': '佐藤翔',
            'category': 'スポーツ',
            'nationality': '日本',
            'occupation': 'サッカー選手',
            'description': 'プロサッカー選手',
            'recognition_score': 5.0
        }
    ],
    
    # 田中健太
    'P004382': [
        {
            'new_id': 'P100020',
            'person_name': '田中健太',
            'person_name_display': '田中健太',
            'person_name_ja': '田中健太',
            'category': 'その他',
            'nationality': '日本',
            'occupation': '一般人',
            'description': '特定の著名人物が見つからない一般的な名前',
            'recognition_score': 3.0
        }
    ]
}

def get_total_new_records():
    """新規作成されるレコード総数を取得"""
    total = 0
    for persons in HOMONYM_PERSONS.values():
        total += len(persons)
    return total

def get_homonym_stats():
    """同姓同名統計を取得"""
    stats = {
        'total_original_records': len(HOMONYM_PERSONS),
        'total_new_records': get_total_new_records(),
        'max_homonyms': max(len(persons) for persons in HOMONYM_PERSONS.values()),
        'avg_homonyms': get_total_new_records() / len(HOMONYM_PERSONS) if HOMONYM_PERSONS else 0
    }
    return stats

if __name__ == "__main__":
    stats = get_homonym_stats()
    print("同姓同名人物データ統計:")
    print(f"  元レコード数: {stats['total_original_records']}")
    print(f"  新レコード数: {stats['total_new_records']}")
    print(f"  最大同姓同名数: {stats['max_homonyms']}")
    print(f"  平均同姓同名数: {stats['avg_homonyms']:.1f}")