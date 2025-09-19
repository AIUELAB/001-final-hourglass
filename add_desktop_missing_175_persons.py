import pandas as pd
from datetime import datetime

# 欠落人物のCSVを読み込む
missing_path = 'MISSING_PERSONS_FROM_DESKTOP_20250825_235429.csv'
missing_df = pd.read_csv(missing_path, encoding='utf-8-sig')

# データベースを読み込む
db_path = 'ultra_think_COMPLETE_DATABASE_20250825_235105.csv'
db_df = pd.read_csv(db_path, encoding='utf-8-sig')

print(f"現在のデータベース: {len(db_df)}人")
print(f"追加予定: {len(missing_df)}人")

# 認知度スコアを設定する関数
def get_recognition_score(row):
    field = row['分野']
    name = row['素の名前']
    group = row['グループ/作品']
    
    # お笑い芸人
    if field == 'お笑い':
        if 'ダイアン' in str(group):
            return 55
        elif 'アンタッチャブル' in str(group):
            return 65
        return 60
    
    # 音楽
    elif field == '音楽':
        if 'X JAPAN' in str(group):
            return 75 if name == 'hide' else 70
        elif 'L\'Arc〜en〜Ciel' in str(group):
            return 72
        elif 'Official髭男dism' in str(group):
            return 68
        elif 'サカナクション' in str(group):
            return 55
        return 60
    
    # 海外音楽
    elif field == '音楽（海外）':
        if name == 'ミック・ジャガー':
            return 70
        elif name == 'ブライアン・メイ':
            return 65
        elif name == 'エルトン・ジョン':
            return 72
        return 65
    
    # 俳優
    elif field == '俳優':
        if name == '星野源':
            return 75
        elif name == '川口春奈':
            return 65
        return 60
    
    # アイドル
    elif field == 'アイドル':
        if 'KAT-TUN' in str(group):
            return 65
        elif 'NEWS' in str(group):
            return 60
        elif '関ジャニ∞' in str(group):
            return 62
        elif 'Hey! Say! JUMP' in str(group):
            return 60
        elif 'King & Prince' in str(group):
            return 65
        elif 'SixTONES' in str(group):
            return 58
        elif 'Snow Man' in str(group):
            return 60
        elif 'AKB48' in str(group) or 'SKE48' in str(group) or 'NMB48' in str(group):
            return 55
        elif '乃木坂46' in str(group) or '欅坂46' in str(group):
            return 58
        return 55
    
    # スポーツ
    elif 'スポーツ' in field:
        if field == 'スポーツ（野球）':
            return 65
        elif field == 'スポーツ（サッカー）':
            return 60
        elif field == 'スポーツ（競馬）':
            return 50  # 競走馬
        elif name in ['白鵬翔', '朝青龍', '貴乃花光司', '若乃花勝']:
            return 70
        return 60
    
    # YouTuber
    elif field == 'YouTuber':
        if name == 'SEIKIN':
            return 65
        elif name == '青汁王子':
            return 55
        elif name == 'kemio':
            return 52
        return 50
    
    # キャラクター
    elif field == 'キャラクター':
        if 'ONE PIECE' in str(group):
            if name in ['シャンクス', 'ポートガス・D・エース']:
                return 65
            elif name in ['ウソップ', 'フランキー', 'ブルック']:
                return 60
            return 55
        elif 'ドラゴンボール' in str(group):
            if name in ['ピッコロ', '孫悟飯', 'トランクス']:
                return 65
            elif name in ['クリリン', 'ブルマ', '亀仙人']:
                return 60
            return 55
        elif '鬼滅の刃' in str(group):
            if name in ['我妻善逸', '嘴平伊之助', '冨岡義勇']:
                return 65
            elif name in ['胡蝶しのぶ', '煉獄杏寿郎']:
                return 62
            return 58
        elif '進撃の巨人' in str(group):
            if name in ['ミカサ・アッカーマン', 'アルミン・アルレルト']:
                return 60
            return 55
        elif 'NARUTO' in str(group):
            if name in ['春野サクラ', 'はたけカカシ']:
                return 60
            return 55
        return 50
    
    # マンガ
    elif field == 'マンガ':
        return 55
    
    # 政治・行政
    elif field == '政治・行政':
        return 60
    
    # デフォルト
    return 50

# 新しいデータフレームを作成
new_rows = []
for idx, row in missing_df.iterrows():
    display_name = row['表示名']
    raw_name = row['素の名前']
    group = row['グループ/作品'] if pd.notna(row['グループ/作品']) else None
    field = row['分野']
    
    # 誕生年を設定（キャラクターと競走馬以外）
    birth_year = None
    if field not in ['キャラクター', 'スポーツ（競馬）']:
        # 実在人物の推定誕生年（必要に応じて後で正確な値に更新）
        if raw_name == 'hide':
            birth_year = 1964
        elif raw_name == '星野源':
            birth_year = 1981
        elif raw_name == '川口春奈':
            birth_year = 1995
        elif raw_name == 'SEIKIN':
            birth_year = 1987
        elif raw_name == '山田涼介':
            birth_year = 1993
        # 他は後で更新可能
    
    # 国籍を判定
    if field == '音楽（海外）':
        if 'ジャガー' in raw_name:
            nationality = 'イギリス'
        elif 'ブライアン' in raw_name:
            nationality = 'イギリス'
        elif 'エルトン' in raw_name:
            nationality = 'イギリス'
        else:
            nationality = '外国'
    elif field == 'キャラクター':
        nationality = '架空'
    elif field == 'スポーツ（競馬）':
        nationality = '日本'  # 競走馬
    else:
        nationality = '日本'
    
    # 職業を設定
    if field == 'お笑い':
        occupation = 'お笑い芸人'
    elif field == '音楽':
        occupation = 'ミュージシャン'
    elif field == '音楽（海外）':
        occupation = 'ミュージシャン'
    elif field == '俳優':
        occupation = '俳優'
    elif field == 'アイドル':
        occupation = 'アイドル'
    elif field == 'スポーツ（野球）':
        occupation = '野球監督'
    elif field == 'スポーツ（サッカー）':
        occupation = 'サッカー選手'
    elif field == 'スポーツ':
        if raw_name in ['白鵬翔', '朝青龍', '貴乃花光司', '若乃花勝']:
            occupation = '元大相撲力士'
        else:
            occupation = 'スポーツ選手'
    elif field == 'スポーツ（競馬）':
        occupation = '競走馬'
    elif field == 'YouTuber':
        occupation = 'YouTuber'
    elif field == 'キャラクター':
        occupation = f'架空キャラクター（{group}）' if group else '架空キャラクター'
    elif field == 'マンガ':
        occupation = '漫画家'
    elif field == '政治・行政':
        occupation = '政治家'
    else:
        occupation = '不明'
    
    # カテゴリを判定
    if field == 'お笑い':
        main_category = 'エンタメ'
    elif '音楽' in field:
        main_category = '音楽'
    elif field == '俳優':
        main_category = 'エンタメ'
    elif field == 'アイドル':
        main_category = 'エンタメ'
    elif 'スポーツ' in field:
        main_category = 'スポーツ'
    elif field == 'YouTuber':
        main_category = 'インターネット'
    elif field == 'キャラクター':
        main_category = '架空の存在'
    elif field == 'マンガ':
        main_category = '文化'
    elif field == '政治・行政':
        main_category = '政治・経済'
    else:
        main_category = 'その他'
    
    new_row = {
        'person_name_ja': raw_name,
        'person_name_display': display_name,
        'birth_year': birth_year,
        'occupation': occupation,
        'name_recognition': get_recognition_score(row),
        'nationality': nationality,
        'is_fictional': 'TRUE' if field == 'キャラクター' else 'FALSE',
        'main_category': main_category,
        'phase': 'DesktopListAddition'
    }
    
    # 他のフィールドをNaNで埋める
    for col in db_df.columns:
        if col not in new_row:
            new_row[col] = None
    
    new_rows.append(new_row)

# 新しい行を追加
new_df = pd.DataFrame(new_rows)
combined_df = pd.concat([db_df, new_df], ignore_index=True)

# 統計情報
print(f"\n追加前: {len(db_df)}人")
print(f"追加数: {len(new_rows)}人")
print(f"追加後: {len(combined_df)}人")

# 保存
output_path = f'ultra_think_FINAL_COMPLETE_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
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
for category, count in category_counts.head(15).items():
    print(f"- {category}: {count}人")

# 最終レポート
print(f"\n🎊 データベース完成！")
print(f"総人数: {len(combined_df)}人")
print(f"架空キャラクター: {len(combined_df[combined_df['is_fictional'] == 'TRUE'])}人")
print(f"実在人物: {len(combined_df[combined_df['is_fictional'] != 'TRUE'])}人")