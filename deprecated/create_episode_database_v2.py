import pandas as pd
from datetime import datetime
import json
import random
import uuid

def create_episode_schema_v2():
    """エピソードデータベースの新スキーマを定義"""
    
    schema = {
        # 基本識別情報
        'episode_id': 'str',              # エピソードの一意識別子
        'person_id': 'str',               # 人物の一意識別子
        'age': 'int',                     # エピソード発生時の年齢
        'age_months': 'int',              # エピソード発生時の月齢
        
        # 人物基本情報
        'person_name': 'str',             # 人物名（英語・原語表記）
        'person_name_ja': 'str',          # 人物名（日本語表記）
        'person_name_display': 'str',     # 表示用人物名
        
        # エピソード本体
        'episode_title': 'str',           # エピソードのタイトル（30文字程度）
        'episode_text': 'str',            # エピソード本文（100-200文字）
        'episode_year': 'int',            # エピソード発生年（西暦）
        'episode_date': 'str',            # エピソード発生日（MM-DD形式）
        
        # システム管理
        'created_at': 'datetime',         # 作成日時
        'updated_at': 'datetime',         # 更新日時
        'is_published': 'bool',           # 公開フラグ
        
        # 分類情報
        'category': 'str',                # 大分類
        'subcategory': 'str',             # 小分類
        'nationality': 'str',             # 国籍・出身国
        'occupation': 'str',              # 職業・肩書き
        
        # 品質管理
        'accuracy_score': 'int',          # 事実確認スコア（1-5）
        'recognition_level': 'int',       # 一般認知度（1-5）
        'impact_score': 'int',            # インパクトスコア（1-5）
        'source': 'str',                  # 出典・参照元
        
        # 詳細情報
        'birth_year': 'int',              # 生年
        'death_year': 'int',              # 没年
        'era': 'str',                     # 時代区分
        'achievement_type': 'str',        # 功績タイプ
        
        # 検索・フィルタ用
        'keywords': 'str',                # 検索用キーワード（JSON配列）
        'tags': 'str',                    # タグ（JSON配列）
        'language': 'str',                # 対応言語
        'region': 'str',                  # 地域
        
        # 拡張情報
        'related_person_ids': 'str',      # 関連人物ID（JSON配列）
        'related_episode_ids': 'str',     # 関連エピソードID（JSON配列）
        'external_links': 'str',          # 外部リンク（JSON配列）
        'image_url': 'str',               # 画像URL
        
        # 統計・分析用
        'view_count': 'int',              # 閲覧回数
        'share_count': 'int',             # シェア回数
        'favorite_count': 'int',          # お気に入り数
        'api_generation_model': 'str',    # 生成に使用したAIモデル
        'token_count': 'int',             # 生成時のトークン数
        'generation_cost': 'float',       # 生成コスト（円）
    }
    
    return schema

def generate_episode_id():
    """エピソードIDを生成"""
    return f"EP_{datetime.now().strftime('%Y%m%d')}_{uuid.uuid4().hex[:8].upper()}"

def generate_person_id(index):
    """人物IDを生成"""
    return f"P{str(index).zfill(6)}"

def calculate_age(birth_year, episode_year):
    """エピソード発生時の年齢を計算"""
    if birth_year and episode_year:
        return episode_year - birth_year
    return None

def calculate_age_months(birth_year, episode_year, episode_month=6):
    """エピソード発生時の月齢を計算"""
    if birth_year and episode_year:
        age = episode_year - birth_year
        return age * 12 + episode_month
    return None

def create_sample_episodes_v2():
    """新スキーマでサンプルエピソードを生成"""
    
    episodes = []
    
    # 1. 織田信長 - 桶狭間の戦い
    episodes.append({
        # 基本識別情報
        'episode_id': generate_episode_id(),
        'person_id': generate_person_id(1),
        'age': calculate_age(1534, 1560),
        'age_months': calculate_age_months(1534, 1560, 5),
        
        # 人物基本情報
        'person_name': 'Oda Nobunaga',
        'person_name_ja': '織田信長',
        'person_name_display': '織田信長',
        
        # エピソード本体
        'episode_title': '桶狭間の戦いで今川義元を破る',
        'episode_text': '1560年5月19日、織田信長はわずか3千の兵で今川義元率いる2万5千の大軍を奇襲攻撃。豪雨の中、今川本陣を急襲し義元を討ち取った。この劇的な勝利により、信長は一躍戦国大名として名を馳せ、天下統一への第一歩を踏み出した。',
        'episode_year': 1560,
        'episode_date': '05-19',
        
        # システム管理
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'is_published': True,
        
        # 分類情報
        'category': '歴史',
        'subcategory': '戦国武将',
        'nationality': '日本',
        'occupation': '戦国大名',
        
        # 品質管理
        'accuracy_score': 5,
        'recognition_level': 5,
        'impact_score': 5,
        'source': '信長公記',
        
        # 詳細情報
        'birth_year': 1534,
        'death_year': 1582,
        'era': '戦国時代',
        'achievement_type': '軍事的勝利',
        
        # 検索・フィルタ用
        'keywords': json.dumps(['桶狭間の戦い', '今川義元', '奇襲', '戦国時代'], ensure_ascii=False),
        'tags': json.dumps(['#戦国時代', '#歴史的勝利', '#下克上'], ensure_ascii=False),
        'language': 'ja',
        'region': 'アジア',
        
        # 拡張情報
        'related_person_ids': json.dumps([generate_person_id(100)], ensure_ascii=False),  # 今川義元
        'related_episode_ids': json.dumps([], ensure_ascii=False),
        'external_links': json.dumps(['https://ja.wikipedia.org/wiki/桶狭間の戦い'], ensure_ascii=False),
        'image_url': None,
        
        # 統計・分析用
        'view_count': 0,
        'share_count': 0,
        'favorite_count': 0,
        'api_generation_model': 'human_created',
        'token_count': 0,
        'generation_cost': 0.0
    })
    
    # 2. アインシュタイン - 相対性理論
    episodes.append({
        # 基本識別情報
        'episode_id': generate_episode_id(),
        'person_id': generate_person_id(2),
        'age': calculate_age(1879, 1905),
        'age_months': calculate_age_months(1879, 1905, 6),
        
        # 人物基本情報
        'person_name': 'Albert Einstein',
        'person_name_ja': 'アルベルト・アインシュタイン',
        'person_name_display': 'アインシュタイン',
        
        # エピソード本体
        'episode_title': '特殊相対性理論を発表',
        'episode_text': '1905年、26歳のアインシュタインは「奇跡の年」と呼ばれる年に特殊相対性理論を発表。E=mc²という有名な方程式を導き出し、時間と空間の概念を根本から覆した。この理論は物理学の歴史において最も重要な発見の一つとなった。',
        'episode_year': 1905,
        'episode_date': '06-30',
        
        # システム管理
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'is_published': True,
        
        # 分類情報
        'category': '科学',
        'subcategory': '物理学者',
        'nationality': 'ドイツ',
        'occupation': '理論物理学者',
        
        # 品質管理
        'accuracy_score': 5,
        'recognition_level': 5,
        'impact_score': 5,
        'source': '物理学史料',
        
        # 詳細情報
        'birth_year': 1879,
        'death_year': 1955,
        'era': '20世紀',
        'achievement_type': '科学的発見',
        
        # 検索・フィルタ用
        'keywords': json.dumps(['相対性理論', 'E=mc²', '物理学', '奇跡の年'], ensure_ascii=False),
        'tags': json.dumps(['#ノーベル賞', '#物理学', '#20世紀最大の発見'], ensure_ascii=False),
        'language': 'ja',
        'region': '欧州',
        
        # 拡張情報
        'related_person_ids': json.dumps([], ensure_ascii=False),
        'related_episode_ids': json.dumps([], ensure_ascii=False),
        'external_links': json.dumps(['https://ja.wikipedia.org/wiki/特殊相対性理論'], ensure_ascii=False),
        'image_url': None,
        
        # 統計・分析用
        'view_count': 0,
        'share_count': 0,
        'favorite_count': 0,
        'api_generation_model': 'human_created',
        'token_count': 0,
        'generation_cost': 0.0
    })
    
    # 3. モーツァルト - 神童エピソード
    episodes.append({
        # 基本識別情報
        'episode_id': generate_episode_id(),
        'person_id': generate_person_id(3),
        'age': 6,
        'age_months': 72,
        
        # 人物基本情報
        'person_name': 'Wolfgang Amadeus Mozart',
        'person_name_ja': 'ヴォルフガング・アマデウス・モーツァルト',
        'person_name_display': 'モーツァルト',
        
        # エピソード本体
        'episode_title': '6歳で皇帝の前で演奏',
        'episode_text': '1762年、わずか6歳のモーツァルトは姉と共にウィーンのシェーンブルン宮殿で女帝マリア・テレジアの前で演奏。演奏後、モーツァルトは皇女マリー・アントワネットに「大きくなったら僕と結婚してね」と言ったという逸話が残っている。',
        'episode_year': 1762,
        'episode_date': '10-13',
        
        # システム管理
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'is_published': True,
        
        # 分類情報
        'category': '芸術',
        'subcategory': '作曲家',
        'nationality': 'オーストリア',
        'occupation': '作曲家・演奏家',
        
        # 品質管理
        'accuracy_score': 4,
        'recognition_level': 5,
        'impact_score': 4,
        'source': 'モーツァルト伝記',
        
        # 詳細情報
        'birth_year': 1756,
        'death_year': 1791,
        'era': '18世紀',
        'achievement_type': '芸術的才能',
        
        # 検索・フィルタ用
        'keywords': json.dumps(['神童', 'マリア・テレジア', 'ウィーン', 'クラシック音楽'], ensure_ascii=False),
        'tags': json.dumps(['#神童', '#クラシック音楽', '#18世紀'], ensure_ascii=False),
        'language': 'ja',
        'region': '欧州',
        
        # 拡張情報
        'related_person_ids': json.dumps([generate_person_id(200), generate_person_id(201)], ensure_ascii=False),  # マリア・テレジア、マリー・アントワネット
        'related_episode_ids': json.dumps([], ensure_ascii=False),
        'external_links': json.dumps(['https://ja.wikipedia.org/wiki/モーツァルト'], ensure_ascii=False),
        'image_url': None,
        
        # 統計・分析用
        'view_count': 0,
        'share_count': 0,
        'favorite_count': 0,
        'api_generation_model': 'human_created',
        'token_count': 0,
        'generation_cost': 0.0
    })
    
    # 4. イチロー - 日米通算4367安打
    episodes.append({
        # 基本識別情報
        'episode_id': generate_episode_id(),
        'person_id': generate_person_id(4),
        'age': calculate_age(1973, 2016),
        'age_months': calculate_age_months(1973, 2016, 6),
        
        # 人物基本情報
        'person_name': 'Ichiro Suzuki',
        'person_name_ja': '鈴木一朗',
        'person_name_display': 'イチロー',
        
        # エピソード本体
        'episode_title': '日米通算4367安打で世界記録達成',
        'episode_text': '2016年6月15日、イチローは日米通算4367安打を達成し、ピート・ローズのMLB記録4256安打を上回った。試合後「人の数字を超えることは大したことではない。自分の数字を超えていくことが大事」と語り、記録よりも過程を重視する姿勢を示した。',
        'episode_year': 2016,
        'episode_date': '06-15',
        
        # システム管理
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'is_published': True,
        
        # 分類情報
        'category': 'スポーツ',
        'subcategory': '野球選手',
        'nationality': '日本',
        'occupation': 'プロ野球選手',
        
        # 品質管理
        'accuracy_score': 5,
        'recognition_level': 5,
        'impact_score': 5,
        'source': 'MLB公式記録',
        
        # 詳細情報
        'birth_year': 1973,
        'death_year': None,
        'era': '平成・令和',
        'achievement_type': 'スポーツ記録',
        
        # 検索・フィルタ用
        'keywords': json.dumps(['安打記録', 'MLB', '日本プロ野球', 'ピート・ローズ'], ensure_ascii=False),
        'tags': json.dumps(['#世界記録', '#野球', '#レジェンド'], ensure_ascii=False),
        'language': 'ja',
        'region': 'アジア',
        
        # 拡張情報
        'related_person_ids': json.dumps([generate_person_id(300)], ensure_ascii=False),  # ピート・ローズ
        'related_episode_ids': json.dumps([], ensure_ascii=False),
        'external_links': json.dumps(['https://ja.wikipedia.org/wiki/イチロー'], ensure_ascii=False),
        'image_url': None,
        
        # 統計・分析用
        'view_count': 0,
        'share_count': 0,
        'favorite_count': 0,
        'api_generation_model': 'human_created',
        'token_count': 0,
        'generation_cost': 0.0
    })
    
    # 5. 手塚治虫 - 鉄腕アトム誕生
    episodes.append({
        # 基本識別情報
        'episode_id': generate_episode_id(),
        'person_id': generate_person_id(5),
        'age': calculate_age(1928, 1952),
        'age_months': calculate_age_months(1928, 1952, 4),
        
        # 人物基本情報
        'person_name': 'Osamu Tezuka',
        'person_name_ja': '手塚治虫',
        'person_name_display': '手塚治虫',
        
        # エピソード本体
        'episode_title': '鉄腕アトムを生み出す',
        'episode_text': '1952年、24歳の手塚治虫は雑誌「少年」で鉄腕アトムの連載を開始。10万馬力のロボット少年アトムは、日本のマンガ・アニメ文化の象徴となり、世界中で愛されるキャラクターとなった。手塚は「マンガの神様」と呼ばれる礎を築いた。',
        'episode_year': 1952,
        'episode_date': '04-01',
        
        # システム管理
        'created_at': datetime.now(),
        'updated_at': datetime.now(),
        'is_published': True,
        
        # 分類情報
        'category': '文学',
        'subcategory': '漫画家',
        'nationality': '日本',
        'occupation': '漫画家',
        
        # 品質管理
        'accuracy_score': 5,
        'recognition_level': 5,
        'impact_score': 5,
        'source': '手塚治虫記念館資料',
        
        # 詳細情報
        'birth_year': 1928,
        'death_year': 1989,
        'era': '昭和',
        'achievement_type': '創作',
        
        # 検索・フィルタ用
        'keywords': json.dumps(['鉄腕アトム', 'マンガ', 'アニメ', '昭和'], ensure_ascii=False),
        'tags': json.dumps(['#マンガの神様', '#鉄腕アトム', '#日本文化'], ensure_ascii=False),
        'language': 'ja',
        'region': 'アジア',
        
        # 拡張情報
        'related_person_ids': json.dumps([], ensure_ascii=False),
        'related_episode_ids': json.dumps([], ensure_ascii=False),
        'external_links': json.dumps(['https://ja.wikipedia.org/wiki/鉄腕アトム'], ensure_ascii=False),
        'image_url': None,
        
        # 統計・分析用
        'view_count': 0,
        'share_count': 0,
        'favorite_count': 0,
        'api_generation_model': 'human_created',
        'token_count': 0,
        'generation_cost': 0.0
    })
    
    return episodes

def create_episode_database_v2():
    """新スキーマでエピソードデータベースを作成"""
    
    # サンプルエピソード生成
    episodes = create_sample_episodes_v2()
    
    # DataFrameに変換
    df = pd.DataFrame(episodes)
    
    # CSVとして保存
    csv_path = f'episode_database_v2_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    
    # JSON形式でも保存
    json_path = f'episode_database_v2_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    df.to_json(json_path, orient='records', force_ascii=False, indent=2, date_format='iso')
    
    print(f"✅ エピソードデータベースV2作成完了")
    print(f"- CSV: {csv_path}")
    print(f"- JSON: {json_path}")
    print(f"- エピソード数: {len(episodes)}件")
    
    # スキーマ情報を保存
    schema = create_episode_schema_v2()
    schema_path = 'episode_database_schema_v2.json'
    with open(schema_path, 'w', encoding='utf-8') as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)
    print(f"- スキーマ: {schema_path}")
    
    return df

def display_episode_summary(df):
    """エピソードサマリーを表示"""
    
    print("\n" + "=" * 60)
    print("📊 エピソードデータベース サマリー")
    print("=" * 60)
    
    print("\n【収録エピソード】")
    for idx, row in df.iterrows():
        print(f"\n{idx+1}. {row['person_name_display']} ({row['age']}歳)")
        print(f"   📅 {row['episode_year']}年 - {row['episode_title']}")
        print(f"   📝 {row['episode_text'][:50]}...")
        print(f"   🏷️ {row['category']} / {row['subcategory']}")
        print(f"   ⭐ 認知度:{row['recognition_level']}/5, インパクト:{row['impact_score']}/5")
    
    print("\n【カテゴリ分布】")
    category_counts = df['category'].value_counts()
    for category, count in category_counts.items():
        print(f"- {category}: {count}件")
    
    print("\n【時代分布】")
    era_counts = df['era'].value_counts()
    for era, count in era_counts.items():
        print(f"- {era}: {count}件")
    
    print("\n【フィールド統計】")
    print(f"- 総フィールド数: {len(df.columns)}個")
    print(f"- 必須フィールド: 15個")
    print(f"- 推奨フィールド: 12個")
    print(f"- オプション: 13個")

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 エピソードデータベースV2 生成開始")
    print("=" * 60)
    
    # データベース作成
    df = create_episode_database_v2()
    
    # サマリー表示
    display_episode_summary(df)
    
    print("\n" + "=" * 60)
    print("✨ 完了！")
    print("=" * 60)