#!/usr/bin/env python3
"""
現代人（10代〜50代）が感銘を受ける有名人カテゴリ定義
「同じ年齢でこんなことを！」と共感・刺激を受けるカテゴリを優先度順に定義
"""

INSPIRATIONAL_CATEGORIES = {
    # ============ 優先度1: テック・イノベーション ============
    'priority_1_tech_innovators': {
        'description': '技術革新で世界を変えた起業家・イノベーター',
        'why_inspiring': '現代のデジタル社会を作った人物。若くして起業し、世界を変えた',
        'categories': {
            '10代で起業・プログラミング開始': {
                'keywords': ['teenage entrepreneur', 'young coder', 'student startup'],
                'examples': 'ビル・ゲイツ(17歳でプログラム販売)、マーク・ザッカーバーグ(19歳でFacebook創業)',
                'age_range': '13-19'
            },
            '20代でユニコーン企業創業': {
                'keywords': ['unicorn founder', 'billion dollar company', 'tech startup'],
                'examples': 'スティーブ・ジョブズ(21歳でApple設立)、イーロン・マスク(24歳でZip2起業)',
                'age_range': '20-29'
            },
            '大学中退して起業': {
                'keywords': ['college dropout', 'left university', 'dropped out'],
                'examples': 'ビル・ゲイツ(ハーバード中退)、ザッカーバーグ(ハーバード中退)',
                'age_range': '18-22'
            },
            'AI・機械学習パイオニア': {
                'keywords': ['AI pioneer', 'machine learning', 'deep learning'],
                'examples': 'サム・アルトマン(OpenAI)、デミス・ハサビス(DeepMind)',
                'age_range': '25-40'
            },
            'アプリ・サービス創業者': {
                'keywords': ['app founder', 'SaaS', 'platform creator'],
                'examples': 'ケビン・シストロム(Instagram)、ブライアン・チェスキー(Airbnb)',
                'age_range': '23-35'
            },
        }
    },
    
    # ============ 優先度2: 若手成功者・天才 ============
    'priority_2_young_achievers': {
        'description': '若くして圧倒的な成果を達成した人物',
        'why_inspiring': '同世代や年下が世界レベルで活躍している事実に刺激を受ける',
        'categories': {
            '10代の天才・神童': {
                'keywords': ['child prodigy', 'teenage genius', 'young talent'],
                'examples': 'モーツァルト(5歳で作曲)、ピカソ(13歳で美術学校入学)',
                'age_range': '5-19'
            },
            '20代で世界的成功': {
                'keywords': ['young success', 'twenties achievement', 'early fame'],
                'examples': 'アインシュタイン(26歳で特殊相対性理論)、ビートルズ(20代で世界的成功)',
                'age_range': '20-29'
            },
            '最年少記録保持者': {
                'keywords': ['youngest ever', 'record holder', 'first at age'],
                'examples': 'マララ(17歳でノーベル賞)、グレタ(16歳でTIME誌今年の人)',
                'age_range': '10-30'
            },
            'スポーツ若手スター': {
                'keywords': ['young athlete', 'sports prodigy', 'olympic youth'],
                'examples': 'タイガー・ウッズ(21歳でマスターズ優勝)、大谷翔平(23歳で二刀流)',
                'age_range': '15-25'
            },
            '若手アーティスト': {
                'keywords': ['young artist', 'emerging talent', 'breakthrough artist'],
                'examples': 'ビリー・アイリッシュ(18歳でグラミー賞)、新海誠(29歳で監督デビュー)',
                'age_range': '18-30'
            },
        }
    },
    
    # ============ 優先度3: 挫折からの復活・逆転人生 ============
    'priority_3_comeback_stories': {
        'description': '失敗や挫折を乗り越えて成功した人物',
        'why_inspiring': '困難な状況でも諦めない勇気をもらえる',
        'categories': {
            '倒産・失敗からの復活': {
                'keywords': ['bankruptcy', 'business failure', 'comeback'],
                'examples': 'ウォルト・ディズニー(複数回倒産)、スティーブ・ジョブズ(Apple追放後の復帰)',
                'age_range': '30-50'
            },
            '病気・障害の克服': {
                'keywords': ['overcame illness', 'disability', 'health struggle'],
                'examples': 'ホーキング(21歳でALS診断)、ベートーヴェン(聴覚を失いながら作曲)',
                'age_range': '20-60'
            },
            '貧困からの成功': {
                'keywords': ['rags to riches', 'poverty', 'humble beginnings'],
                'examples': 'オプラ・ウィンフリー(貧困から世界的司会者)、J.K.ローリング(生活保護からベストセラー作家)',
                'age_range': '25-40'
            },
            'セカンドキャリア成功': {
                'keywords': ['career change', 'second career', 'reinvention'],
                'examples': 'カーネル・サンダース(65歳でKFC創業)、ヴェラ・ウォン(40歳でデザイナー転身)',
                'age_range': '40-65'
            },
            'メンタルヘルス克服': {
                'keywords': ['mental health', 'depression', 'anxiety overcome'],
                'examples': 'レディー・ガガ(うつ病公表)、ドウェイン・ジョンソン(うつ病克服)',
                'age_range': '20-50'
            },
        }
    },
    
    # ============ 優先度4: 社会変革者・活動家 ============
    'priority_4_changemakers': {
        'description': '社会を変えようと行動した人物',
        'why_inspiring': '個人の行動が世界を変えられることを示す',
        'categories': {
            '10代の社会活動家': {
                'keywords': ['teenage activist', 'youth movement', 'student leader'],
                'examples': 'グレタ・トゥーンベリ(15歳で気候変動活動)、マララ(11歳でブログ開始)',
                'age_range': '10-19'
            },
            '社会起業家': {
                'keywords': ['social entrepreneur', 'impact business', 'social innovation'],
                'examples': 'ムハマド・ユヌス(グラミン銀行)、ブレイク・マイコスキー(TOMS)',
                'age_range': '25-45'
            },
            '人権・平等運動家': {
                'keywords': ['civil rights', 'equality', 'justice fighter'],
                'examples': 'キング牧師(26歳でバス・ボイコット指導)、ハーヴェイ・ミルク(LGBTQ運動)',
                'age_range': '20-50'
            },
            '環境保護活動家': {
                'keywords': ['environmental activist', 'climate change', 'sustainability'],
                'examples': 'ジェーン・グドール(26歳でチンパンジー研究)、ボヤン・スラット(18歳で海洋清掃)',
                'age_range': '18-40'
            },
            'SNS発信で変革': {
                'keywords': ['social media activist', 'online movement', 'digital campaign'],
                'examples': '#MeToo運動、BLM運動のリーダーたち',
                'age_range': '20-40'
            },
        }
    },
    
    # ============ 優先度5: クリエイター・コンテンツ創造者 ============
    'priority_5_creators': {
        'description': '新しい表現やコンテンツを生み出した人物',
        'why_inspiring': '創造性と個性で成功できることを示す',
        'categories': {
            'YouTuber・配信者': {
                'keywords': ['youtuber', 'content creator', 'streamer'],
                'examples': 'MrBeast(24歳で登録者1億人)、PewDiePie',
                'age_range': '18-35'
            },
            'ゲームクリエイター': {
                'keywords': ['game developer', 'indie game', 'game designer'],
                'examples': '宮本茂(マリオ創造)、小島秀夫(メタルギア)',
                'age_range': '25-40'
            },
            '漫画家・アニメ監督': {
                'keywords': ['manga artist', 'anime director', 'animation'],
                'examples': '尾田栄一郎(22歳でワンピース連載)、新海誠(29歳で監督デビュー)',
                'age_range': '20-35'
            },
            'インフルエンサー': {
                'keywords': ['influencer', 'instagram', 'tiktok star'],
                'examples': 'チャーリー・ダミリオ(TikTok)、エマ・チェンバレン(YouTube)',
                'age_range': '16-30'
            },
            'ポッドキャスター': {
                'keywords': ['podcaster', 'podcast host', 'audio content'],
                'examples': 'ジョー・ローガン、コナン・オブライエン',
                'age_range': '25-50'
            },
        }
    },
    
    # ============ 優先度6: 女性パイオニア ============
    'priority_6_female_pioneers': {
        'description': '男性中心分野で道を切り開いた女性',
        'why_inspiring': 'ジェンダーの壁を越えて活躍する姿に勇気をもらえる',
        'categories': {
            'STEM分野の女性': {
                'keywords': ['women in STEM', 'female scientist', 'women in tech'],
                'examples': 'キュリー夫人(初の女性ノーベル賞)、グレース・ホッパー(プログラミング言語開発)',
                'age_range': '25-50'
            },
            '女性起業家': {
                'keywords': ['female entrepreneur', 'women founder', 'businesswoman'],
                'examples': 'ホイットニー・ウルフ(Bumble創業)、サラ・ブレイクリー(Spanx創業)',
                'age_range': '25-40'
            },
            '女性政治家・リーダー': {
                'keywords': ['female politician', 'women leader', 'first female'],
                'examples': 'ジャシンダ・アーダーン(37歳でNZ首相)、AOC(29歳で最年少下院議員)',
                'age_range': '25-50'
            },
            'ガラスの天井を破った女性': {
                'keywords': ['glass ceiling', 'first woman', 'breakthrough'],
                'examples': 'カマラ・ハリス(初の女性副大統領)、メアリー・バーラ(GM初の女性CEO)',
                'age_range': '40-60'
            },
        }
    },
    
    # ============ 優先度7: 遅咲きの成功者 ============
    'priority_7_late_bloomers': {
        'description': '40代以降で大成功した人物',
        'why_inspiring': '年齢に関係なく挑戦できることを示す',
        'categories': {
            '40代での起業成功': {
                'keywords': ['midlife entrepreneur', 'late starter', '40s success'],
                'examples': 'リード・ヘイスティングス(37歳でNetflix創業)、山田邦子(42歳で起業)',
                'age_range': '40-50'
            },
            '50代以降の新挑戦': {
                'keywords': ['50s new start', 'senior entrepreneur', 'late career'],
                'examples': 'カーネル・サンダース(65歳でKFC)、ハーランド・デイヴィッド・サンダース',
                'age_range': '50-70'
            },
            'キャリアチェンジ成功': {
                'keywords': ['career pivot', 'midlife change', 'second act'],
                'examples': 'ヴェラ・ウォン(40歳でファッション)、ジュリア・チャイルド(50歳で料理番組)',
                'age_range': '40-60'
            },
        }
    },
    
    # ============ 優先度8: 日本の現代成功者 ============
    'priority_8_japanese_modern': {
        'description': '日本人が特に共感しやすい現代の成功者',
        'why_inspiring': '同じ日本の環境から世界へ羽ばたいた',
        'categories': {
            '日本の若手起業家': {
                'keywords': ['japanese entrepreneur', 'startup japan', '日本 起業'],
                'examples': '前澤友作(ZOZO)、堀江貴文(ライブドア)、家入一真(CAMPFIRE)',
                'age_range': '20-40'
            },
            '世界で活躍する日本人': {
                'keywords': ['japanese global', 'international success', '世界で活躍'],
                'examples': '大谷翔平(MLB)、渡辺直美(世界的コメディアン)、YOASOBI(世界的音楽)',
                'age_range': '20-40'
            },
            '日本のクリエイター': {
                'keywords': ['japanese creator', 'japan artist', '日本人クリエイター'],
                'examples': '新海誠、米津玄師、藤井風、あつまれどうぶつの森開発者',
                'age_range': '25-45'
            },
        }
    },
    
    # ============ 優先度9: 学び直し・生涯学習 ============
    'priority_9_lifelong_learners': {
        'description': '常に学び続けて成長した人物',
        'why_inspiring': '何歳からでも学べることを示す',
        'categories': {
            '社会人から博士号': {
                'keywords': ['adult phd', 'mature student', 'back to school'],
                'examples': 'ブライアン・メイ(60歳で天体物理学博士)、シャキール・オニール(MBA取得)',
                'age_range': '30-60'
            },
            '異分野への挑戦': {
                'keywords': ['cross discipline', 'multi talented', 'renaissance'],
                'examples': 'ドナルド・グローヴァー(俳優・音楽家・脚本家)、イーロン・マスク(複数企業CEO)',
                'age_range': '25-50'
            },
            'オンライン学習で成功': {
                'keywords': ['online learning', 'self taught', 'mooc success'],
                'examples': 'プログラミング独学からエンジニア転職した人々',
                'age_range': '20-50'
            },
        }
    },
    
    # ============ 優先度10: ワークライフバランス実現者 ============
    'priority_10_balanced_life': {
        'description': '仕事と人生のバランスを実現した人物',
        'why_inspiring': '成功と幸せの両立が可能であることを示す',
        'categories': {
            '家族優先の成功者': {
                'keywords': ['family first', 'work life balance', 'parenting'],
                'examples': 'ジェフ・ウィーバー(Amazon退職後の家族時間)、北欧の起業家たち',
                'age_range': '30-50'
            },
            'リモートワーク先駆者': {
                'keywords': ['remote work', 'digital nomad', 'location independent'],
                'examples': 'ベースキャンプ創業者、リモート企業CEO',
                'age_range': '25-45'
            },
            'FIRE達成者': {
                'keywords': ['FIRE movement', 'early retirement', 'financial independence'],
                'examples': 'ミスターマネーマスタッシュ(30歳でリタイア)、日本のFIRE実践者',
                'age_range': '30-45'
            },
        }
    },
}

def create_age_impact_matrix():
    """年齢別インパクトマトリックスを作成"""
    age_matrix = {
        '10代': {
            'most_impactful': [
                'priority_1_tech_innovators',  # プログラミング開始
                'priority_2_young_achievers',   # 天才・神童
                'priority_4_changemakers',      # 若い活動家
            ],
            'key_message': '若さは武器。今から始めても遅くない'
        },
        '20代': {
            'most_impactful': [
                'priority_1_tech_innovators',   # スタートアップ創業
                'priority_2_young_achievers',   # 若い成功
                'priority_5_creators',          # コンテンツクリエイター
            ],
            'key_message': '挑戦の黄金期。失敗を恐れず行動する時'
        },
        '30代': {
            'most_impactful': [
                'priority_3_comeback_stories',  # 挫折からの復活
                'priority_6_female_pioneers',   # キャリア確立期
                'priority_8_japanese_modern',   # 日本の起業家
            ],
            'key_message': '経験と若さのバランス。大きな決断の時期'
        },
        '40代': {
            'most_impactful': [
                'priority_7_late_bloomers',     # 遅咲きの成功
                'priority_3_comeback_stories',  # セカンドキャリア
                'priority_9_lifelong_learners', # 学び直し
            ],
            'key_message': '人生の折り返し。新しい挑戦はまだ可能'
        },
        '50代': {
            'most_impactful': [
                'priority_7_late_bloomers',     # 50代の新挑戦
                'priority_10_balanced_life',    # ワークライフバランス
                'priority_9_lifelong_learners', # 生涯学習
            ],
            'key_message': '経験の集大成。若い世代への貢献も'
        },
    }
    return age_matrix

def export_inspirational_categories():
    """インスピレーショナルカテゴリをJSON出力"""
    import json
    from datetime import datetime
    
    output = {
        'metadata': {
            'created_at': datetime.now().isoformat(),
            'version': '1.0',
            'purpose': '現代人が感銘を受ける有名人カテゴリ',
            'target_age': '10代〜50代',
        },
        'priority_categories': INSPIRATIONAL_CATEGORIES,
        'age_impact_matrix': create_age_impact_matrix(),
        'statistics': {
            'total_priority_levels': len(INSPIRATIONAL_CATEGORIES),
            'total_subcategories': sum(
                len(cat['categories']) 
                for cat in INSPIRATIONAL_CATEGORIES.values()
            ),
        }
    }
    
    output_file = f'inspirational_categories_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    return output_file

if __name__ == "__main__":
    output_file = export_inspirational_categories()
    
    print("="*60)
    print("🌟 現代人が感銘を受けるカテゴリ定義")
    print("="*60)
    
    print("\n📊 優先度別カテゴリ:")
    for priority, category in INSPIRATIONAL_CATEGORIES.items():
        priority_num = priority.split('_')[1]
        print(f"\n【優先度{priority_num}】{category['description']}")
        print(f"  → {category['why_inspiring']}")
        print(f"  サブカテゴリ数: {len(category['categories'])}種類")
        for subcat_name in list(category['categories'].keys())[:3]:
            print(f"    ・{subcat_name}")
    
    print("\n📈 年代別おすすめカテゴリ:")
    matrix = create_age_impact_matrix()
    for age_group, data in matrix.items():
        print(f"\n{age_group}: {data['key_message']}")
        for cat in data['most_impactful']:
            cat_name = INSPIRATIONAL_CATEGORIES[cat]['description']
            print(f"  → {cat_name}")
    
    print(f"\n✅ カテゴリ定義ファイル作成: {output_file}")