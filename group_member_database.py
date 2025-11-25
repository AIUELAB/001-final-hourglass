#!/usr/bin/env python3
"""
Group Member Database for Ultra Think
グループメンバーデータベース

This database contains comprehensive group membership information for
consistent parenthetical notation in person_name_display fields.
"""

# グループメンバーデータベース
# Format: 'Group Name': {'person_id': 'member_name', ...}
GROUP_MEMBERS_DATABASE = {
    'SEKAI NO OWARI': {
        'P000008': 'Fukase',
        'P000029': 'Saori',
        # NakajinとDJ LOVEのperson_idは未確認
    },

    'X JAPAN': {
        'P000039': 'YOSHIKI',
        'P000035': 'Toshl',
        'P000021': 'PATA',
        'P000012': 'HEATH',
        # hideのperson_idは未確認
    },

    "L'Arc~en~Ciel": {
        'P000041': 'hyde',
        'P000042': 'ken',
        'P000043': 'tetsuya',
        'P000044': 'yukihiro',
    },

    'BTS': {
        'P000023': 'RM',
        'P000759': 'Jin',
        'P000609': 'Suga',
        'P000017': 'J-Hope',
        'P000675': 'Jimin',
        'P000728': 'Jungkook',
        # Vのperson_idは未確認
    },

    'GLAY': {
        'P000031': 'TERU',
        'P000030': 'TAKURO',
        'P000014': 'HISASHI',
        'P000018': 'JIRO',
    },

    'LUNA SEA': {
        'P000024': 'RYUICHI',
        'P000028': 'SUGIZO',
        'P000016': 'INORAN',
        'P000019': 'J',
        'P004532': '真矢',
    },

    'YOASOBI': {
        'P000003': 'Ayase',
        'P003293': 'ikura',
    },

    'Mr.Children': {
        'P003857': '桜井和寿',
        'P004435': '田原健一',
        'P001631': '中川敬輔',
        'P005224': '鈴木英哉',
    },

    # YouTuberグループ
    '東海オンエア': {
        'P000090': 'Tetsuya',  # てつや
        'P000077': 'Jukiya',  # じゅきや
        # 他のメンバーのperson_idは未確認
    },

    'コムドット': {
        # メンバーのperson_idは要調査
    },

    'スカイピース': {
        # メンバーのperson_idは要調査
    },

    # お笑いコンビ・グループ
    'ナインティナイン': {
        'P003178': 'Okamura Takashi',  # 岡村隆史
        # 矢部浩之のperson_idは要確認
    },

    'かまいたち': {
        'P002957': 'Yamauchi Kenji',  # 山内健司
        'P004320': 'Hamaie Ryuichi',  # 濱家隆一
    },

    'ぼる塾': {
        # メンバーのperson_idは要調査
    },

    'ザ・ドリフターズ': {
        # いかりや長介のperson_idは要調査
    },

    # 韓国グループ（追加）
    'BLACKPINK': {
        'P000637': 'Jennie',
        'P000670': 'Jisoo',
        # RoséとLisaのperson_idは未確認
    },

    'SEVENTEEN': {
        # メンバーのperson_idは要調査
    },

    'TWICE': {
        'P000674': 'Jihyo',
        'P000731': 'Jeongyeon',
        # 他のメンバーのperson_idは未確認
    },

    'NCT': {
        'P000638': 'Jeno',
        'P000645': 'Jaemin',
        'P000672': 'Jisung',
        'P001519': 'Renjun',
        # 他のメンバーのperson_idは未確認
    },

    'ENHYPEN': {
        'P000625': 'Jake',
        'P000629': 'Jay',
        'P000727': 'Jungwon',
        # 他のメンバーのperson_idは未確認
    },

    # 日本のバンド（追加）
    'ONE OK ROCK': {
        # Taka, Toru, Ryota, Tomoyaのperson_idは要調査
        # 候補: P000034 (Toru), P000025 (Ryota), P000033 (Tomoya)
    },

    'EXILE': {
        # メンバーのperson_idは要調査
    },

    'Official髭男dism': {
        'P004907': 'Motoo Fujiwara',  # 藤原基央
        'P004919': 'Fujiwara Satoshi',  # 藤原聡
    },

    'RADWIMPS': {
        'P005163': 'Yojiro Noda',  # 野田洋次郎
    },

    'King Gnu': {
        'P001828': 'Satoru Iguchi',  # 井口理
    },
}

# 名前ベースのグループ検索用辞書
NAME_TO_GROUP = {}
for group, members in GROUP_MEMBERS_DATABASE.items():
    for person_id, name in members.items():
        # 複数の名前表記に対応
        names = [name]

        # 日本語名も含む場合の処理
        if person_id == 'P000008':
            names.extend(['Fukase', 'ふかせ', '深瀬'])
        elif person_id == 'P000039':
            names.extend(['YOSHIKI', 'ヨシキ'])
        elif person_id == 'P000035':
            names.extend(['Toshl', 'トシ', 'Toshi'])
        elif person_id == 'P000041':
            names.extend(['hyde', 'HYDE', 'ハイド'])
        elif person_id == 'P000023':
            names.extend(['RM', 'Rap Monster', 'アールエム'])
        elif person_id == 'P000759':
            names.extend(['Jin', 'ジン'])
        elif person_id == 'P000609':
            names.extend(['Suga', 'SUGA', 'シュガ'])
        elif person_id == 'P000017':
            names.extend(['J-Hope', 'j-hope', 'ジェイホープ'])
        elif person_id == 'P000675':
            names.extend(['Jimin', 'JIMIN', 'ジミン'])
        elif person_id == 'P000728':
            names.extend(['Jungkook', 'Jung Kook', 'ジョングク'])

        for n in names:
            NAME_TO_GROUP[n.lower()] = (group, person_id)

def get_group_for_person(person_id: str) -> str:
    """
    指定されたperson_idのグループ名を取得

    Args:
        person_id: 人物のID

    Returns:
        グループ名（見つからない場合はNone）
    """
    for group, members in GROUP_MEMBERS_DATABASE.items():
        if person_id in members:
            return group
    return None

def get_group_by_name(person_name: str) -> tuple:
    """
    人物名からグループ情報を取得

    Args:
        person_name: 人物名

    Returns:
        (グループ名, person_id) のタプル（見つからない場合は(None, None)）
    """
    name_lower = person_name.lower()
    if name_lower in NAME_TO_GROUP:
        return NAME_TO_GROUP[name_lower]

    # 部分一致検索
    for key in NAME_TO_GROUP:
        if key in name_lower or name_lower in key:
            return NAME_TO_GROUP[key]

    return (None, None)

def should_have_group_notation(person_id: str) -> bool:
    """
    指定されたperson_idがグループ名の括弧表記を持つべきか判定

    Args:
        person_id: 人物のID

    Returns:
        グループ名の括弧表記が必要な場合True
    """
    return get_group_for_person(person_id) is not None

def get_correct_display_name(person_id: str, current_display: str) -> str:
    """
    正しいdisplay_name（グループ名付き）を生成

    Args:
        person_id: 人物のID
        current_display: 現在のdisplay_name

    Returns:
        グループ名付きの正しいdisplay_name
    """
    group = get_group_for_person(person_id)
    if not group:
        return current_display

    # すでに括弧表記がある場合はそのまま返す
    if f'({group})' in current_display or f'（{group}）' in current_display:
        return current_display

    # グループ名を追加
    return f"{current_display} ({group})"

# 統計情報
def get_statistics():
    """データベースの統計情報を取得"""
    total_groups = len(GROUP_MEMBERS_DATABASE)
    total_members = sum(len(members) for members in GROUP_MEMBERS_DATABASE.values())

    stats = {
        'total_groups': total_groups,
        'total_members': total_members,
        'groups_by_category': {
            'music_bands': ['SEKAI NO OWARI', 'X JAPAN', "L'Arc~en~Ciel", 'GLAY', 'LUNA SEA',
                           'YOASOBI', 'Mr.Children', 'ONE OK ROCK', 'EXILE', 'Official髭男dism',
                           'RADWIMPS', 'King Gnu'],
            'kpop_groups': ['BTS', 'BLACKPINK', 'SEVENTEEN', 'TWICE', 'NCT', 'ENHYPEN'],
            'youtubers': ['東海オンエア', 'コムドット', 'スカイピース'],
            'comedians': ['ナインティナイン', 'かまいたち', 'ぼる塾', 'ザ・ドリフターズ'],
        }
    }

    return stats

if __name__ == "__main__":
    # データベースの統計を表示
    stats = get_statistics()
    print(f"=== グループメンバーデータベース統計 ===")
    print(f"総グループ数: {stats['total_groups']}")
    print(f"総メンバー数: {stats['total_members']}")
    print(f"\nカテゴリー別:")
    for category, groups in stats['groups_by_category'].items():
        print(f"  {category}: {len(groups)}グループ")

    # テストケース
    print(f"\n=== テストケース ===")
    test_cases = [
        ('P000008', 'Fukase'),
        ('P000039', 'YOSHIKI'),
        ('P000023', 'RM'),
    ]

    for person_id, name in test_cases:
        group = get_group_for_person(person_id)
        correct_display = get_correct_display_name(person_id, name)
        print(f"{person_id} ({name}): {group} → {correct_display}")
