import pandas as pd
from datetime import datetime
import json
import random

def create_episode_database_schema():
    """エピソードデータベースのスキーマを定義"""
    
    schema = {
        # コアフィールド
        'episode_id': 'str',              # EP000001形式
        'person_id': 'str',               # P000001形式  
        'person_name_ja': 'str',          # 日本語名
        'person_name_display': 'str',     # 表示名
        'episode_title': 'str',           # エピソードタイトル
        'episode_content': 'str',         # エピソード本文（200-500文字）
        'episode_year': 'int',            # エピソードの年代
        'episode_category': 'str',        # カテゴリ
        
        # メタデータ
        'source': 'str',                  # 出典
        'credibility_score': 'int',       # 信憑性スコア（1-100）
        'emotional_tone': 'str',          # 感情トーン
        'difficulty_level': 'str',        # 難易度
        'tags': 'str',                    # JSON配列文字列
        'related_persons': 'str',         # JSON配列文字列
        'location': 'str',                # 場所
        
        # ゲーム用フィールド
        'quiz_potential': 'int',          # クイズ適性（1-100）
        'memorability': 'int',            # 記憶しやすさ（1-100）
        'surprise_factor': 'int',         # 意外性（1-100）
        'educational_value': 'int',       # 教育的価値（1-100）
        'entertainment_value': 'int',     # エンタメ価値（1-100）
        
        # コンテンツ管理
        'created_at': 'datetime',         # 作成日時
        'updated_at': 'datetime',         # 更新日時
        'version': 'str',                 # バージョン
        'is_verified': 'bool',            # 検証済みフラグ
        'is_appropriate': 'bool',         # 子供向けOK
        'language': 'str',                # 言語
        'word_count': 'int',              # 文字数
        'reading_time': 'int',            # 読了時間（秒）
        
        # 関連性フィールド
        'keywords': 'str',                # JSON配列文字列
        'themes': 'str',                  # JSON配列文字列
        'historical_period': 'str',       # 歴史的時代
        'field': 'str',                   # 分野
        'impact_score': 'int',            # 影響度（1-100）
    }
    
    return schema

def create_sample_episodes():
    """サンプルエピソードを生成"""
    
    episodes = []
    
    # 織田信長のエピソード
    episodes.append({
        'episode_id': 'EP000001',
        'person_id': 'P000001',
        'person_name_ja': '織田信長',
        'person_name_display': '織田信長',
        'episode_title': '桶狭間の奇跡',
        'episode_content': '1560年、今川義元率いる2万5千の大軍に対し、織田信長はわずか3千の兵で奇襲攻撃を敢行。豪雨の中、今川本陣を急襲し、義元を討ち取るという歴史的勝利を収めた。この勝利により信長は一躍戦国大名として名を馳せ、天下統一への第一歩を踏み出した。',
        'episode_year': 1560,
        'episode_category': '偉業',
        'source': '信長公記',
        'credibility_score': 95,
        'emotional_tone': '劇的',
        'difficulty_level': '一般',
        'tags': json.dumps(['戦略', '勇気', '逆転'], ensure_ascii=False),
        'related_persons': json.dumps(['今川義元'], ensure_ascii=False),
        'location': '桶狭間（愛知県）',
        'quiz_potential': 90,
        'memorability': 95,
        'surprise_factor': 85,
        'educational_value': 90,
        'entertainment_value': 95,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'version': '1.0',
        'is_verified': True,
        'is_appropriate': True,
        'language': 'ja',
        'word_count': 120,
        'reading_time': 30,
        'keywords': json.dumps(['桶狭間の戦い', '奇襲', '戦国時代'], ensure_ascii=False),
        'themes': json.dumps(['勇気', '戦略', '下克上'], ensure_ascii=False),
        'historical_period': '戦国時代',
        'field': '歴史',
        'impact_score': 95
    })
    
    # イチローのエピソード
    episodes.append({
        'episode_id': 'EP000002',
        'person_id': 'P000002',
        'person_name_ja': 'イチロー',
        'person_name_display': 'イチロー',
        'episode_title': '10年連続200安打の偉業',
        'episode_content': '2001年から2010年まで、イチローはMLB史上初となる10年連続200安打を達成。特に2004年にはシーズン262安打という84年ぶりの新記録を樹立。毎日の地道な練習と、独自の準備ルーティンを欠かさず続けた結果、「安打製造機」と呼ばれる伝説的選手となった。',
        'episode_year': 2010,
        'episode_category': '偉業',
        'source': 'MLB公式記録',
        'credibility_score': 100,
        'emotional_tone': '感動的',
        'difficulty_level': '一般',
        'tags': json.dumps(['努力', '継続', '記録'], ensure_ascii=False),
        'related_persons': json.dumps([], ensure_ascii=False),
        'location': 'シアトル（アメリカ）',
        'quiz_potential': 85,
        'memorability': 90,
        'surprise_factor': 70,
        'educational_value': 85,
        'entertainment_value': 80,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'version': '1.0',
        'is_verified': True,
        'is_appropriate': True,
        'language': 'ja',
        'word_count': 115,
        'reading_time': 30,
        'keywords': json.dumps(['MLB', '200安打', '記録'], ensure_ascii=False),
        'themes': json.dumps(['努力', '継続', '偉業'], ensure_ascii=False),
        'historical_period': '平成',
        'field': 'スポーツ',
        'impact_score': 90
    })
    
    # 手塚治虫のエピソード
    episodes.append({
        'episode_id': 'EP000003',
        'person_id': 'P000003',
        'person_name_ja': '手塚治虫',
        'person_name_display': '手塚治虫',
        'episode_title': '週刊連載を同時に7本',
        'episode_content': '1960年代、手塚治虫は週刊誌7誌で同時連載という超人的な仕事量をこなしていた。締切に追われ、新幹線の中でも原稿を描き続け、時には編集者を待たせたまま別の出版社へ移動することも。「漫画の神様」と呼ばれる所以は、その圧倒的な創作への情熱と驚異的な仕事量にあった。',
        'episode_year': 1965,
        'episode_category': '秘話',
        'source': '手塚治虫物語',
        'credibility_score': 90,
        'emotional_tone': '驚愕',
        'difficulty_level': '一般',
        'tags': json.dumps(['情熱', '創作', '超人的'], ensure_ascii=False),
        'related_persons': json.dumps([], ensure_ascii=False),
        'location': '東京',
        'quiz_potential': 75,
        'memorability': 85,
        'surprise_factor': 90,
        'educational_value': 70,
        'entertainment_value': 85,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'version': '1.0',
        'is_verified': True,
        'is_appropriate': True,
        'language': 'ja',
        'word_count': 118,
        'reading_time': 30,
        'keywords': json.dumps(['漫画', '連載', '創作'], ensure_ascii=False),
        'themes': json.dumps(['情熱', '創造性', '努力'], ensure_ascii=False),
        'historical_period': '昭和',
        'field': '文化',
        'impact_score': 85
    })
    
    # 坂本龍馬のエピソード
    episodes.append({
        'episode_id': 'EP000004',
        'person_id': 'P000004',
        'person_name_ja': '坂本龍馬',
        'person_name_display': '坂本龍馬',
        'episode_title': '薩長同盟の立役者',
        'episode_content': '1866年、犬猿の仲だった薩摩藩と長州藩を結びつけ、薩長同盟を成立させた坂本龍馬。両藩の間を何度も往復し、西郷隆盛と桂小五郎を説得。「日本を今一度洗濯いたし申し候」という手紙の言葉通り、幕末の日本を大きく動かした。',
        'episode_year': 1866,
        'episode_category': '偉業',
        'source': '龍馬の手紙',
        'credibility_score': 95,
        'emotional_tone': '感動的',
        'difficulty_level': '一般',
        'tags': json.dumps(['交渉', '志', '改革'], ensure_ascii=False),
        'related_persons': json.dumps(['西郷隆盛', '桂小五郎'], ensure_ascii=False),
        'location': '京都',
        'quiz_potential': 85,
        'memorability': 90,
        'surprise_factor': 75,
        'educational_value': 95,
        'entertainment_value': 85,
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'version': '1.0',
        'is_verified': True,
        'is_appropriate': True,
        'language': 'ja',
        'word_count': 105,
        'reading_time': 25,
        'keywords': json.dumps(['薩長同盟', '幕末', '維新'], ensure_ascii=False),
        'themes': json.dumps(['志', '交渉', '改革'], ensure_ascii=False),
        'historical_period': '幕末',
        'field': '歴史',
        'impact_score': 100
    })
    
    return episodes

def create_episode_database():
    """エピソードデータベースを作成"""
    
    # スキーマ取得
    schema = create_episode_database_schema()
    
    # サンプルエピソード生成
    episodes = create_sample_episodes()
    
    # DataFrameに変換
    df = pd.DataFrame(episodes)
    
    # CSVとして保存
    output_path = f'episode_database_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    
    # JSON形式でも保存（構造化データとして）
    json_path = f'episode_database_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    df.to_json(json_path, orient='records', force_ascii=False, indent=2)
    
    print(f"✅ エピソードデータベース作成完了")
    print(f"- CSV: {output_path}")
    print(f"- JSON: {json_path}")
    print(f"- エピソード数: {len(episodes)}件")
    
    # スキーマ情報を保存
    schema_path = 'episode_database_schema.json'
    with open(schema_path, 'w', encoding='utf-8') as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)
    print(f"- スキーマ: {schema_path}")
    
    return df

def display_episode_categories():
    """エピソードカテゴリの定義を表示"""
    
    categories = {
        '偉業': '歴史的な功績や記録的な達成',
        '失敗': '失敗から学んだ教訓',
        '転機': '人生の転換点となった出来事',
        '日常': '人柄が分かる日常的エピソード',
        '秘話': 'あまり知られていない裏話',
        '名言': '有名な言葉とその背景',
        '友情': '他者との関わりのエピソード',
        '挑戦': '困難への挑戦',
        '発見': '新しい発見や発明',
        '感動': '人々を感動させたエピソード'
    }
    
    print("\n📚 エピソードカテゴリ:")
    for category, description in categories.items():
        print(f"- {category}: {description}")
    
    return categories

def display_emotional_tones():
    """感情トーンの定義を表示"""
    
    tones = {
        '感動的': '心を動かす感動的な内容',
        '劇的': 'ドラマチックな展開',
        '悲劇的': '悲しい結末や苦難',
        'コミカル': 'ユーモアのある内容',
        '中立': '客観的な事実の記述',
        '驚愕': '驚きや意外性のある内容',
        '勇壮': '勇気や力強さを感じる内容',
        '温かい': '人情味や優しさを感じる内容'
    }
    
    print("\n🎭 感情トーン:")
    for tone, description in tones.items():
        print(f"- {tone}: {description}")
    
    return tones

if __name__ == "__main__":
    print("=" * 60)
    print("📖 エピソードデータベース設計")
    print("=" * 60)
    
    # カテゴリと感情トーンを表示
    display_episode_categories()
    display_emotional_tones()
    
    # データベース作成
    print("\n" + "=" * 60)
    print("🔨 サンプルデータベース作成中...")
    print("=" * 60)
    
    df = create_episode_database()
    
    # サンプル表示
    print("\n📊 サンプルエピソード:")
    print("-" * 60)
    for idx, row in df.iterrows():
        print(f"\n【{row['person_name_display']}】{row['episode_title']}")
        print(f"  カテゴリ: {row['episode_category']} | 年代: {row['episode_year']}")
        print(f"  内容: {row['episode_content'][:50]}...")
        print(f"  スコア: クイズ適性={row['quiz_potential']}, 記憶={row['memorability']}, 意外性={row['surprise_factor']}")