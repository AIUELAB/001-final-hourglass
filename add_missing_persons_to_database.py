import pandas as pd
from datetime import datetime

# データベースを読み込む
db_path = 'ultra_think_with_recognition_20250825_225556.csv'
df = pd.read_csv(db_path, encoding='utf-8-sig')

print(f"現在のデータベース: {len(df)}人")

# 追加する人物リスト（名前、生年、職業、認知度スコア）
missing_persons = [
    # お笑い芸人・タレント（高認知度）
    ("中田敦彦", 1982, "お笑い芸人・YouTuber", 75),
    ("江頭2:50", 1965, "お笑い芸人・YouTuber", 72),
    
    # 俳優・アイドル（高認知度）
    ("亀梨和也", 1986, "アイドル", 78),
    ("赤西仁", 1984, "歌手・元KAT-TUN", 72),
    ("錦戸亮", 1984, "俳優・歌手", 70),
    ("上戸彩", 1985, "女優", 75),
    ("三浦春馬", 1990, "俳優（故人）", 85),
    
    # 音楽関係者（高認知度）
    ("ikura", 2000, "歌手（YOASOBI）", 82),
    ("西木絢香", 1989, "歌手（Perfume・あ〜ちゃん）", 70),
    ("大本彩乃", 1988, "歌手（Perfume・のっち）", 70),
    ("樫野有香", 1988, "歌手（Perfume・かしゆか）", 70),
    ("ミン・ユンギ", 1993, "歌手（BTS・SUGA）", 85),
    ("西野カナ", 1989, "歌手", 72),
    ("きゃりーぱみゅぱみゅ", 1993, "歌手", 70),
    
    # 音楽プロデューサー・作詞家
    ("小室哲哉", 1958, "音楽プロデューサー", 75),
    ("つんく♂", 1968, "音楽プロデューサー", 70),
    ("秋元康", 1958, "作詞家・プロデューサー", 72),
    
    # 漫画家（高認知度）
    ("尾田栄一郎", 1975, "漫画家", 78),
    ("岸本斉史", 1974, "漫画家", 75),
    ("吾峠呼世晴", 1989, "漫画家", 73),
    
    # その他の著名人
    ("西野亮廣", 1980, "お笑い芸人・絵本作家", 65),
    ("岩井俊二", 1963, "映画監督", 60),
    ("新垣隆", 1970, "作曲家", 55),
    ("櫻井よしこ", 1945, "ジャーナリスト", 65),
    ("羽鳥慎一", 1971, "アナウンサー", 70),
    ("小泉進次郎", 1981, "政治家", 75),
    
    # 外国人著名人
    ("エリザベス2世", 1926, "元イギリス女王（故人）", 85),
    ("金正恩", 1984, "北朝鮮最高指導者", 80),
    
    # アナウンサー
    ("安住紳一郎", 1973, "アナウンサー", 68),
    ("水卜麻美", 1987, "アナウンサー", 65),
    ("加藤綾子", 1985, "アナウンサー", 62),
    ("田中みな実", 1986, "元アナウンサー・タレント", 65),
    
    # 実業家（追加）
    ("堀江貴文", 1972, "実業家", 75),
    ("前澤友作", 1975, "実業家", 72),
    
    # スポーツ選手（追加）
    ("渋野日向子", 1998, "ゴルフ選手", 65),
    ("萩野公介", 1994, "元水泳選手", 60),
    ("瀬戸大也", 1994, "水泳選手", 62),
    ("白井健三", 1996, "元体操選手", 58),
    ("橋本大輝", 2001, "体操選手", 60),
    ("村田諒太", 1986, "元ボクシング選手", 65),
    ("那須川天心", 1998, "格闘家", 70),
    ("朝倉未来", 1992, "格闘家", 68),
    ("朝倉海", 1993, "格闘家", 65),
    
    # 政治家（追加）
    ("東国原英夫", 1957, "元宮崎県知事", 65),
    ("蓮舫", 1967, "政治家", 62),
    ("河野太郎", 1963, "政治家", 68),
    
    # 映画監督（追加）
    ("黒澤明", 1910, "映画監督（故人）", 85),
    ("山田洋次", 1931, "映画監督", 70),
    
    # 作曲家・音楽家
    ("久石譲", 1950, "作曲家", 75),
    ("坂本龍一", 1952, "音楽家（故人）", 80),
    
    # ジャーナリスト
    ("田原総一朗", 1934, "ジャーナリスト", 68),
    ("古舘伊知郎", 1954, "元アナウンサー", 65),
    ("みのもんた", 1944, "元アナウンサー", 68),
    
    # 架空キャラクター（主要なもののみ追加）
    ("ロイド・フォージャー", None, "架空キャラクター（SPY×FAMILY）", 65),
    ("ヨル・フォージャー", None, "架空キャラクター（SPY×FAMILY）", 65),
    ("アーニャ・フォージャー", None, "架空キャラクター（SPY×FAMILY）", 70),
    ("潔世一", None, "架空キャラクター（ブルーロック）", 55),
    ("蜂楽廻", None, "架空キャラクター（ブルーロック）", 55),
    ("糸師凛", None, "架空キャラクター（ブルーロック）", 55),
    ("ナツキ・スバル", None, "架空キャラクター（リゼロ）", 50),
    ("レム", None, "架空キャラクター（リゼロ）", 55),
    ("リムル・テンペスト", None, "架空キャラクター（転スラ）", 55),
    ("アインズ・ウール・ゴウン", None, "架空キャラクター（オーバーロード）", 50),
    ("佐藤和真", None, "架空キャラクター（このすば）", 50),
    ("アクア", None, "架空キャラクター（このすば）", 50),
    ("めぐみん", None, "架空キャラクター（このすば）", 52),
    ("黒子テツヤ", None, "架空キャラクター（黒子のバスケ）", 55),
    ("火神大我", None, "架空キャラクター（黒子のバスケ）", 55),
    ("宮水三葉", None, "架空キャラクター（君の名は。）", 65),
    ("森嶋帆高", None, "架空キャラクター（天気の子）", 60),
    ("天野陽菜", None, "架空キャラクター（天気の子）", 60),
    ("ヴァイオレット・エヴァーガーデン", None, "架空キャラクター", 55),
    ("しろくま", None, "架空キャラクター（すみっコぐらし）", 45),
    ("RX-78-2 ガンダム", None, "架空キャラクター（機動戦士ガンダム）", 60),
]

# 新しいデータフレームを作成
new_rows = []
for name, birth_year, occupation, recognition in missing_persons:
    new_row = {
        'person_name_ja': name,
        'person_name_display': name,
        'birth_year': birth_year,
        'occupation': occupation,
        'name_recognition': recognition,
        'nationality': '日本' if not any(x in name for x in ['BTS', 'エリザベス', '金正恩']) else ('韓国' if 'BTS' in occupation else ('イギリス' if 'エリザベス' in name else ('北朝鮮' if '金正恩' in name else '架空'))),
        'is_fictional': 'TRUE' if '架空' in occupation else 'FALSE',
        'main_category': 'エンタメ' if any(x in occupation for x in ['お笑い', '俳優', '女優', 'アイドル', 'タレント']) else ('音楽' if any(x in occupation for x in ['歌手', 'ミュージシャン', 'プロデューサー', '作曲', '作詞']) else ('文化' if any(x in occupation for x in ['漫画', '作家', '監督']) else ('メディア' if any(x in occupation for x in ['アナウンサー', 'ジャーナリスト']) else ('政治・経済' if any(x in occupation for x in ['政治', '実業']) else ('スポーツ' if any(x in occupation for x in ['選手', '格闘']) else ('架空の存在' if '架空' in occupation else 'その他'))))))
    }
    
    # 他のフィールドをNaNで埋める
    for col in df.columns:
        if col not in new_row:
            new_row[col] = None
    
    new_rows.append(new_row)

# 新しい行を追加
new_df = pd.DataFrame(new_rows)
combined_df = pd.concat([df, new_df], ignore_index=True)

# 重複チェック
print(f"\n追加前: {len(df)}人")
print(f"追加数: {len(new_rows)}人")
print(f"追加後: {len(combined_df)}人")

# 保存
output_path = f'ultra_think_FINAL_WITH_ALL_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
combined_df.to_csv(output_path, index=False, encoding='utf-8-sig')
print(f"\n✅ 保存完了: {output_path}")

# 認知度スコアの統計
print("\n📊 認知度スコア統計:")
print(f"- 平均: {combined_df['name_recognition'].mean():.1f}")
print(f"- 70以上: {len(combined_df[combined_df['name_recognition'] >= 70])}人")
print(f"- 50以上: {len(combined_df[combined_df['name_recognition'] >= 50])}人")

# カテゴリ別統計
print("\n📊 カテゴリ別統計:")
category_counts = combined_df['main_category'].value_counts()
for category, count in category_counts.head(10).items():
    print(f"- {category}: {count}人")