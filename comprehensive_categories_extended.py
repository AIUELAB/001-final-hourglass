#!/usr/bin/env python3
"""
拡張版包括的カテゴリ定義
歴史的教訓、日本サブカル、架空人物を含む完全版
"""

EXTENDED_CATEGORIES = {
    
    # ============ 歴史的教訓カテゴリ（負の歴史から学ぶ） ============
    'historical_lessons': {
        'description': '歴史の暗部から学ぶべき教訓を持つ人物',
        'warning': '美化せず、教訓として捉えることが重要',
        'categories': {
            '独裁者・暴君': {
                'keywords': ['dictator', 'tyrant', '独裁者', '暴君'],
                'examples': 'ヒトラー、スターリン、毛沢東、ポル・ポト',
                'lessons': '権力の危険性、全体主義の恐怖',
                'key_ages': '権力掌握時の年齢、失脚時の年齢'
            },
            '戦争犯罪者': {
                'keywords': ['war criminal', 'war crime', '戦犯'],
                'examples': '東條英機、アイヒマン',
                'lessons': '戦争の悲惨さ、個人の責任',
                'key_ages': '戦争指導時の年齢、裁判時の年齢'
            },
            'テロリスト': {
                'keywords': ['terrorist', 'extremist', 'テロリスト'],
                'examples': 'オサマ・ビンラディン、オウム真理教幹部',
                'lessons': '過激思想の危険性、洗脳の恐怖',
                'key_ages': '過激化した年齢、事件時の年齢'
            },
            '経済犯罪者': {
                'keywords': ['fraud', 'scammer', '詐欺師', '経済犯'],
                'examples': 'バーニー・マドフ、エンロン経営陣、ホリエモン（逮捕時）',
                'lessons': '倫理観の重要性、規制の必要性',
                'key_ages': '犯罪開始年齢、逮捕時の年齢'
            },
            '連続殺人犯': {
                'keywords': ['serial killer', 'murderer', '殺人犯'],
                'examples': 'ジャック・ザ・リッパー、テッド・バンディ',
                'lessons': '社会の闇、心理学的考察',
                'key_ages': '最初の犯行年齢、逮捕時の年齢'
            },
            'カルト教祖': {
                'keywords': ['cult leader', 'false prophet', 'カルト'],
                'examples': 'ジム・ジョーンズ、麻原彰晃、チャールズ・マンソン',
                'lessons': 'マインドコントロールの危険性',
                'key_ages': '教団設立年齢、事件時の年齢'
            },
            '裏切り者・スパイ': {
                'keywords': ['traitor', 'spy', 'double agent', 'スパイ'],
                'examples': 'ユダ、ベネディクト・アーノルド、ゾルゲ',
                'lessons': '忠誠と背信、国際諜報の現実',
                'key_ages': '裏切り時の年齢'
            },
            '汚職政治家': {
                'keywords': ['corrupt', 'bribery', '汚職', '収賄'],
                'examples': 'ニクソン（ウォーターゲート）、田中角栄（ロッキード）',
                'lessons': '権力腐敗、透明性の重要性',
                'key_ages': '汚職発覚時の年齢'
            },
        }
    },
    
    # ============ 日本のサブカルチャー・エンターテインメント ============
    'japanese_subculture': {
        'description': '日本のサブカルチャー・エンターテインメント界の人物',
        'categories': {
            'お笑い芸人': {
                'keywords': ['comedian', 'owarai', 'お笑い', '芸人'],
                'subcategories': {
                    'レジェンド芸人': ['ビートたけし', '明石家さんま', '志村けん', 'ダウンタウン'],
                    'M-1王者': ['霜降り明星', 'サンドウィッチマン', 'ミルクボーイ'],
                    'ブレイク芸人': ['千鳥', 'かまいたち', '東京03', 'バナナマン'],
                    'YouTuber芸人': ['江頭2:50', 'カジサック', 'オリラジ中田'],
                    '女性芸人': ['渡辺直美', 'ゆりやんレトリィバァ', '友近'],
                    'ピン芸人': ['有吉弘行', '劇団ひとり', '小島よしお'],
                }
            },
            '日本のYouTuber': {
                'keywords': ['youtuber', 'ユーチューバー', '動画投稿者'],
                'subcategories': {
                    'トップYouTuber': ['HIKAKIN', 'はじめしゃちょー', 'Fischer\'s'],
                    'ゲーム実況者': ['キヨ', '牛沢', 'もこう', '加藤純一'],
                    'VTuber': ['キズナアイ', 'ホロライブ', 'にじさんじ', 'ぺこら'],
                    '教育系': ['中田敦彦', 'QuizKnock', 'ヨビノリ'],
                    '料理系': ['きまぐれクック', 'リュウジ', 'だれウマ'],
                    'ビジネス系': ['マコなり社長', '竹花貴騎', 'マナブ'],
                }
            },
            'アイドル': {
                'keywords': ['idol', 'アイドル', 'ジャニーズ', 'AKB'],
                'subcategories': {
                    'ジャニーズ': ['SMAP', '嵐', 'King & Prince', 'Snow Man'],
                    '女性アイドル': ['AKB48', '乃木坂46', '日向坂46', 'NiziU'],
                    '地下アイドル': ['でんぱ組.inc', 'BiSH', 'ベイビーレイズJAPAN'],
                    'K-POP': ['BTS', 'TWICE', 'SEVENTEEN', 'Stray Kids'],
                    '昭和アイドル': ['山口百恵', '松田聖子', 'おニャン子クラブ'],
                }
            },
            '声優': {
                'keywords': ['voice actor', 'seiyuu', '声優'],
                'subcategories': {
                    'レジェンド声優': ['野沢雅子', '山寺宏一', '林原めぐみ'],
                    '人気男性声優': ['梶裕貴', '花江夏樹', '松岡禎丞'],
                    '人気女性声優': ['花澤香菜', '悠木碧', '早見沙織'],
                    '歌手活動': ['水樹奈々', 'LiSA', '宮野真守'],
                    'VTuber声優': ['ホロライブ声優', 'にじさんじ声優'],
                }
            },
            '俳優・女優': {
                'keywords': ['actor', 'actress', '俳優', '女優'],
                'subcategories': {
                    '大物俳優': ['渡辺謙', '真田広之', '役所広司', '西田敏行'],
                    '若手俳優': ['菅田将暉', '山﨑賢人', '吉沢亮', '横浜流星'],
                    '大物女優': ['吉永小百合', '樹木希林', '岸恵子'],
                    '若手女優': ['橋本環奈', '浜辺美波', '今田美桜', '広瀬すず'],
                    '舞台俳優': ['市村正親', '堀内敬子', '古田新太'],
                    '2.5次元俳優': ['佐藤流司', '鈴木拡樹', '崎山つばさ'],
                }
            },
            'アニメ監督': {
                'keywords': ['anime director', 'animation', 'アニメ監督'],
                'subcategories': {
                    '巨匠': ['宮崎駿', '押井守', '富野由悠季', '庵野秀明'],
                    '新世代': ['新海誠', '細田守', '湯浅政明', '山田尚子'],
                    'アニメーター': ['今石洋之', '吉成曜', '井上俊之'],
                }
            },
            '漫画家': {
                'keywords': ['manga artist', 'mangaka', '漫画家'],
                'subcategories': {
                    'ジャンプ系': ['尾田栄一郎', '鳥山明', '岸本斉史', '吾峠呼世晴'],
                    '少女漫画': ['矢沢あい', 'CLAMP', '種村有菜'],
                    '青年漫画': ['浦沢直樹', '井上雄彦', '板垣恵介'],
                    'Web漫画': ['ONE', '春輝', 'やしろあずき'],
                }
            },
            'ゲームクリエイター': {
                'keywords': ['game creator', 'game designer', 'ゲーム'],
                'subcategories': {
                    'レジェンド': ['宮本茂', '堀井雄二', '坂口博信', '小島秀夫'],
                    'インディー': ['ZUN', 'トビー・フォックス', 'カイロソフト'],
                    'ソシャゲ': ['サイゲームス', 'Yostar', 'miHoYo'],
                }
            },
            'ミュージシャン': {
                'keywords': ['musician', 'artist', 'ミュージシャン'],
                'subcategories': {
                    'J-POP': ['米津玄師', 'あいみょん', 'Official髭男dism', 'King Gnu'],
                    'ロック': ['B\'z', 'ONE OK ROCK', 'RADWIMPS', 'BUMP OF CHICKEN'],
                    'ヒップホップ': ['KOHH', 'BAD HOP', 'JP THE WAVY', 'Creepy Nuts'],
                    'アニソン': ['LiSA', 'Aimer', 'YOASOBI', 'Ado'],
                    'ボカロP': ['ハチ', 'DECO*27', 'syudou', 'ピノキオピー'],
                }
            },
            'インフルエンサー': {
                'keywords': ['influencer', 'インフルエンサー', 'TikToker'],
                'subcategories': {
                    'Instagram': ['渡辺直美', 'ローラ', 'kemio', 'ゆうこす'],
                    'TikTok': ['景井ひな', 'なえなの', 'ひなた', 'コムドット'],
                    'Twitter': ['けんすう', 'イケハヤ', 'はあちゅう'],
                    'ファッション': ['げんじ', 'ゆうた', 'よしあき'],
                }
            },
        }
    },
    
    # ============ 架空の人物（フィクション） ============
    'fictional_characters': {
        'description': '映画・漫画・アニメ・ゲームの架空人物',
        'note': '設定上の年齢と重要イベントが明確な場合に適用',
        'categories': {
            '少年漫画主人公': {
                'keywords': ['shonen protagonist', '少年漫画', '主人公'],
                'characters': {
                    'モンキー・D・ルフィ': {'age_events': [(17, '海賊王を目指し旅立つ'), (19, '新世界へ')]},
                    '孫悟空': {'age_events': [(12, '亀仙人に弟子入り'), (23, 'ピッコロ大魔王を倒す')]},
                    'うずまきナルト': {'age_events': [(12, '忍者学校卒業'), (16, 'ペイン戦'), (19, '第四次忍界大戦')]},
                    '竈門炭治郎': {'age_events': [(13, '家族を失い鬼殺隊へ'), (15, '無限城決戦')]},
                    'エレン・イェーガー': {'age_events': [(10, '母を巨人に殺される'), (15, '調査兵団入団'), (19, '地鳴らし')]},
                }
            },
            '少女漫画ヒロイン': {
                'keywords': ['shojo heroine', '少女漫画', 'ヒロイン'],
                'characters': {
                    '月野うさぎ': {'age_events': [(14, 'セーラームーン覚醒'), (16, 'セーラースターズ')]},
                    '牧野つくし': {'age_events': [(16, '英徳学園入学'), (18, '道明寺と結ばれる')]},
                    '本田透': {'age_events': [(16, '草摩家に居候'), (18, '呪い解放')]},
                }
            },
            'ゲームキャラクター': {
                'keywords': ['game character', 'video game', 'ゲームキャラ'],
                'characters': {
                    'クラウド・ストライフ': {'age_events': [(21, 'ソルジャー偽装'), (23, 'セフィロスとの決戦')]},
                    'リンク': {'age_events': [(17, 'ハイラル救済の旅')]},
                    'ソリッド・スネーク': {'age_events': [(23, 'ビッグボス暗殺任務'), (42, 'リキッド・オセロット戦')]},
                    'マリオ': {'age_events': [(26, 'ピーチ姫初救出')]},
                }
            },
            '映画・ドラマキャラクター': {
                'keywords': ['movie character', 'film', '映画'],
                'characters': {
                    'ルーク・スカイウォーカー': {'age_events': [(19, 'ジェダイの修行開始'), (23, 'ダース・ベイダーとの対決')]},
                    'ハリー・ポッター': {'age_events': [(11, 'ホグワーツ入学'), (17, 'ヴォルデモート最終決戦')]},
                    'フロド・バギンズ': {'age_events': [(33, '成人'), (50, '指輪の旅')]},
                    'トニー・スターク': {'age_events': [(21, 'MIT卒業'), (38, 'アイアンマン誕生'), (53, '最期の戦い')]},
                }
            },
            'ライトノベル主人公': {
                'keywords': ['light novel', 'ラノベ', '異世界'],
                'characters': {
                    'キリト': {'age_events': [(14, 'SAO事件'), (16, 'アリシゼーション')]},
                    '司波達也': {'age_events': [(15, '魔法科高校入学'), (17, '横浜事変')]},
                    'ナツキ・スバル': {'age_events': [(17, '異世界転生'), (18, '聖域編')]},
                }
            },
            'スポーツ漫画キャラ': {
                'keywords': ['sports manga', 'スポーツ', '部活'],
                'characters': {
                    '日向翔陽': {'age_events': [(15, '烏野高校入学'), (17, '春高優勝')]},
                    '黒子テツヤ': {'age_events': [(15, '誠凛高校入学'), (16, 'ウィンターカップ優勝')]},
                    '沢村栄純': {'age_events': [(15, '青道高校入学'), (17, '甲子園優勝')]},
                }
            },
            'アメコミヒーロー': {
                'keywords': ['superhero', 'marvel', 'DC', 'アメコミ'],
                'characters': {
                    'スパイダーマン': {'age_events': [(15, 'クモに噛まれる'), (17, 'ベンおじさんの死')]},
                    'バットマン': {'age_events': [(8, '両親の死'), (25, 'バットマンデビュー')]},
                    'スーパーマン': {'age_events': [(0, 'クリプトン星爆発'), (25, 'スーパーマンとして活動開始')]},
                }
            },
            '歴史・時代劇キャラ': {
                'keywords': ['historical fiction', '時代劇', '大河ドラマ'],
                'characters': {
                    '緋村剣心': {'age_events': [(14, '人斬り抜刀斎'), (28, '不殺の誓い')]},
                    '坂本龍馬（フィクション版）': {'age_events': [(28, '薩長同盟'), (33, '暗殺')]},
                    '宮本武蔵（フィクション版）': {'age_events': [(13, '関ヶ原の戦い'), (29, '巌流島の決闘')]},
                }
            },
        }
    },
    
    # ============ エピソードタイプ定義 ============
    'episode_types': {
        'achievements': ['記録', '偉業', '達成', '受賞', '表彰', '叙勲', '選出'],
        'challenges': ['挑戦', '決断', '転職', '転機'],
        'failures': ['挫折', '失敗', '転落', '喪失'],
        'discoveries': ['発見', '発明', '創造', '革新'],
        'relationships': ['出会い', '結婚', '誕生', '別れ', '離婚', '死別'],
        'incidents': ['事件', '事故', '遭遇', '逮捕'],
        'milestones': ['退任', '引退', '復活', '復帰'],
        'family': ['子供の誕生', '孫の誕生', '家族の死', '相続'],
    },
    
    # ============ 日本特有のライフイベント ============
    'japanese_life_events': {
        '学業': {
            '中学受験': {'typical_age': 12, 'description': '進学校への第一歩'},
            '高校受験': {'typical_age': 15, 'description': '進路の分岐点'},
            '大学受験': {'typical_age': 18, 'description': '人生の大きな節目'},
            '就職活動': {'typical_age': 22, 'description': '社会人への第一歩'},
        },
        '仕事': {
            '新卒入社': {'typical_age': 22, 'description': '社会人デビュー'},
            '初めての昇進': {'typical_age': 28, 'description': 'キャリアの第一歩'},
            '管理職就任': {'typical_age': 35, 'description': 'マネジメント開始'},
            '転職': {'typical_age': 30, 'description': 'キャリアチェンジ'},
            '起業': {'typical_age': 35, 'description': '独立への挑戦'},
            '定年退職': {'typical_age': 60, 'description': '第二の人生開始'},
        },
        '家族': {
            '結婚': {'typical_age': 29, 'description': '家庭を持つ'},
            '第一子誕生': {'typical_age': 31, 'description': '親になる'},
            '子供の独立': {'typical_age': 50, 'description': '子育て卒業'},
            '孫の誕生': {'typical_age': 55, 'description': '祖父母になる'},
        },
        '芸能界': {
            'デビュー': {'typical_age': 16, 'description': '芸能界入り'},
            'ブレイク': {'typical_age': 22, 'description': '知名度急上昇'},
            'スキャンダル': {'typical_age': 28, 'description': '試練の時'},
            '結婚発表': {'typical_age': 32, 'description': 'ファンへの報告'},
            '事務所独立': {'typical_age': 35, 'description': '独立への道'},
        },
    },
}

def create_comprehensive_database():
    """包括的なカテゴリデータベースを作成"""
    import json
    from datetime import datetime
    
    # 統計情報
    stats = {
        'historical_lessons': len(EXTENDED_CATEGORIES['historical_lessons']['categories']),
        'japanese_subculture': sum(
            len(cat.get('subcategories', {})) 
            for cat in EXTENDED_CATEGORIES['japanese_subculture']['categories'].values()
        ),
        'fictional_characters': sum(
            len(cat.get('characters', {}))
            for cat in EXTENDED_CATEGORIES['fictional_characters']['categories'].values()
        ),
        'episode_types': sum(len(v) for v in EXTENDED_CATEGORIES['episode_types'].values()),
        'japanese_life_events': sum(
            len(events) for events in EXTENDED_CATEGORIES['japanese_life_events'].values()
        ),
    }
    
    output = {
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'version': '3.0',
            'description': '歴史的教訓、日本サブカル、架空人物を含む完全版',
            'warnings': [
                '犯罪者カテゴリは教育目的のみ',
                '架空人物は設定上の年齢を使用',
                '日本市場に最適化'
            ],
        },
        'categories': EXTENDED_CATEGORIES,
        'statistics': {
            'total_categories': sum(stats.values()),
            'breakdown': stats
        }
    }
    
    output_file = f'comprehensive_categories_final_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    return output_file, stats

if __name__ == "__main__":
    file, stats = create_comprehensive_database()
    
    print("="*60)
    print("🎌 完全版カテゴリデータベース（日本市場最適化）")
    print("="*60)
    
    print("\n📊 カテゴリ統計:")
    print(f"  歴史的教訓（犯罪者等）: {stats['historical_lessons']}カテゴリ")
    print(f"  日本サブカルチャー: {stats['japanese_subculture']}サブカテゴリ")
    print(f"  架空の人物: {stats['fictional_characters']}キャラクター")
    print(f"  エピソードタイプ: {stats['episode_types']}種類")
    print(f"  日本のライフイベント: {stats['japanese_life_events']}イベント")
    print("  ────────────────────────")
    print(f"  合計: {sum(stats.values())}要素")
    
    print("\n⚠️ 注意事項:")
    print("  • 犯罪者カテゴリは歴史的教訓として")
    print("  • 架空人物は年齢設定が明確なもののみ")
    print("  • 日本のYouTuber、芸人、アイドル等を網羅")
    
    print(f"\n✅ データベースファイル作成: {file}")