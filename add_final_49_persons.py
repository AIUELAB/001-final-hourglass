import pandas as pd
from datetime import datetime

# データベースを読み込む
db_path = 'ultra_think_FINAL_WITH_ALL_20250825_234015.csv'
df = pd.read_csv(db_path, encoding='utf-8-sig')

print(f"現在のデータベース: {len(df)}人")

# 追加する49人のリスト（名前、生年、職業、認知度スコア）
missing_persons = [
    # お笑い芸人
    ("博多大吉", 1971, "お笑い芸人", 75),
    ("博多華丸", 1970, "お笑い芸人", 75),
    ("上島竜兵", 1961, "お笑い芸人（故人）", 70),
    
    # 俳優・女優
    ("佐藤浩市", 1960, "俳優", 72),
    ("大泉洋", 1973, "俳優・タレント", 78),
    ("藤木直人", 1972, "俳優", 65),
    ("綾野剛", 1982, "俳優", 70),
    ("高橋一生", 1980, "俳優", 72),
    ("田中邦衛", 1932, "俳優（故人）", 75),
    ("宮崎あおい", 1985, "女優", 68),
    ("満島ひかり", 1985, "女優", 65),
    
    # ミュージシャン
    ("松任谷由実", 1954, "ミュージシャン", 80),
    ("竹内まりや", 1955, "ミュージシャン", 75),
    ("井上陽水", 1948, "ミュージシャン", 78),
    ("小田和正", 1947, "ミュージシャン", 75),
    ("aiko", 1975, "ミュージシャン", 70),
    ("YUKI", 1972, "ミュージシャン", 65),
    ("斉藤和義", 1966, "ミュージシャン", 62),
    ("GReeeeN", None, "ミュージシャングループ", 68),
    ("hyde", 1969, "ミュージシャン（L'Arc〜en〜Ciel）", 72),
    ("MISIA", 1978, "ミュージシャン", 68),
    ("コブクロ", None, "ミュージシャングループ", 70),
    ("いきものがかり", None, "ミュージシャングループ", 72),
    ("Perfume", None, "ミュージシャングループ", 75),
    ("中田ヤスタカ", 1980, "音楽プロデューサー", 60),
    
    # スポーツ選手
    ("新庄剛志", 1972, "プロ野球監督", 72),
    ("内田篤人", 1988, "元サッカー選手", 65),
    ("澤穂希", 1978, "元女子サッカー選手", 75),
    ("松岡修造", 1967, "元テニス選手・タレント", 75),
    ("武尊", 1991, "キックボクサー", 65),
    ("魔裟斗", 1979, "元キックボクサー", 68),
    ("千代の富士貢", 1955, "元大相撲力士（故人）", 70),
    
    # YouTuber
    ("フィッシャーズ", None, "YouTuberグループ", 68),
    
    # 文化人
    ("芥見下々", 1992, "漫画家", 65),
    ("池井戸潤", 1963, "小説家", 68),
    ("森田一義", 1945, "タレント（タモリ）", 95),  # タモリの本名
    
    # 皇族
    ("上皇陛下", 1933, "皇族", 95),
    ("皇后雅子さま", 1963, "皇族", 90),
    ("上皇后美智子さま", 1934, "皇族", 92),
    ("秋篠宮文仁親王", 1965, "皇族", 85),
    ("小室眞子", 1991, "元皇族", 75),
    ("佳子内親王", 1994, "皇族", 80),
    
    # 架空キャラクター・マスコット
    ("ハローキティ", None, "架空キャラクター（サンリオ）", 85),
    ("スライム", None, "架空キャラクター（ドラゴンクエスト）", 70),
    ("くまモン", None, "ゆるキャラ", 75),
    ("ふなっしー", None, "ゆるキャラ", 70),
    ("ムスカ大佐", None, "架空キャラクター（天空の城ラピュタ）", 65),
    
    # 問題のある人物（データベースには入れるが低認知度で）
    ("宅間守", 1963, "元死刑囚", 30),
    ("植松聖", 1990, "元死刑囚", 25),
]

# 新しいデータフレームを作成
new_rows = []
for item in missing_persons:
    name = item[0]
    birth_year = item[1] if len(item) > 1 else None
    occupation = item[2] if len(item) > 2 else "不明"
    recognition = item[3] if len(item) > 3 else 50
    
    # 国籍を判定
    if '皇族' in occupation or '元皇族' in occupation:
        nationality = '日本'
    elif any(x in name for x in ['ハローキティ', 'スライム', 'くまモン', 'ふなっしー', 'ムスカ']):
        nationality = '架空'
    else:
        nationality = '日本'
    
    # カテゴリを判定
    if 'お笑い' in occupation:
        main_category = 'エンタメ'
    elif '俳優' in occupation or '女優' in occupation:
        main_category = 'エンタメ'
    elif 'ミュージシャン' in occupation or '音楽' in occupation:
        main_category = '音楽'
    elif any(x in occupation for x in ['野球', 'サッカー', 'テニス', 'ボクサー', '相撲', '選手']):
        main_category = 'スポーツ'
    elif 'YouTuber' in occupation:
        main_category = 'インターネット'
    elif '漫画' in occupation or '小説' in occupation:
        main_category = '文化'
    elif '皇族' in occupation:
        main_category = '皇室'
    elif '架空' in occupation or 'ゆるキャラ' in occupation:
        main_category = '架空の存在'
    elif '死刑囚' in occupation:
        main_category = 'その他'
    else:
        main_category = 'その他'
    
    new_row = {
        'person_name_ja': name,
        'person_name_display': name,
        'birth_year': birth_year,
        'occupation': occupation,
        'name_recognition': recognition,
        'nationality': nationality,
        'is_fictional': 'TRUE' if nationality == '架空' else 'FALSE',
        'main_category': main_category,
        'phase': 'FinalAddition'
    }
    
    # 他のフィールドをNaNで埋める
    for col in df.columns:
        if col not in new_row:
            new_row[col] = None
    
    new_rows.append(new_row)

# 新しい行を追加
new_df = pd.DataFrame(new_rows)
combined_df = pd.concat([df, new_df], ignore_index=True)

# 統計情報
print(f"\n追加前: {len(df)}人")
print(f"追加数: {len(new_rows)}人")
print(f"追加後: {len(combined_df)}人")

# 保存
output_path = f'ultra_think_COMPLETE_DATABASE_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
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

# 最終レポート生成
report_path = f'FINAL_DATABASE_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(f"# 🎊 最終データベース完成レポート\n")
    f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"## 📊 最終統計\n")
    f.write(f"- **総人数**: {len(combined_df)}人\n")
    f.write(f"- **平均認知度**: {combined_df['name_recognition'].mean():.1f}\n")
    f.write(f"- **高認知度（70以上）**: {len(combined_df[combined_df['name_recognition'] >= 70])}人\n")
    f.write(f"- **中認知度（50-69）**: {len(combined_df[(combined_df['name_recognition'] >= 50) & (combined_df['name_recognition'] < 70)])}人\n\n")
    
    f.write(f"## 🏆 追加した著名人（最終49人）\n\n")
    f.write(f"### お笑い芸人\n")
    f.write(f"- 博多大吉・博多華丸（博多華丸・大吉）\n")
    f.write(f"- 上島竜兵（ダチョウ倶楽部）\n\n")
    
    f.write(f"### 俳優・女優\n")
    f.write(f"- 佐藤浩市、大泉洋、藤木直人\n")
    f.write(f"- 綾野剛、高橋一生、田中邦衛\n")
    f.write(f"- 宮崎あおい、満島ひかり\n\n")
    
    f.write(f"### ミュージシャン\n")
    f.write(f"- 松任谷由実、竹内まりや、井上陽水、小田和正\n")
    f.write(f"- aiko、YUKI、斉藤和義、GReeeeN\n")
    f.write(f"- hyde（L'Arc〜en〜Ciel）、MISIA\n")
    f.write(f"- コブクロ、いきものがかり、Perfume\n")
    f.write(f"- 中田ヤスタカ\n\n")
    
    f.write(f"### スポーツ選手\n")
    f.write(f"- 新庄剛志、内田篤人、澤穂希\n")
    f.write(f"- 松岡修造、武尊、魔裟斗\n")
    f.write(f"- 千代の富士貢\n\n")
    
    f.write(f"### 皇族\n")
    f.write(f"- 上皇陛下、皇后雅子さま\n")
    f.write(f"- 上皇后美智子さま、秋篠宮文仁親王\n")
    f.write(f"- 小室眞子（元皇族）、佳子内親王\n\n")
    
    f.write(f"### その他\n")
    f.write(f"- フィッシャーズ（YouTuber）\n")
    f.write(f"- 芥見下々（漫画家）\n")
    f.write(f"- 池井戸潤（小説家）\n")
    f.write(f"- 森田一義（タモリ本名）\n")
    f.write(f"- ハローキティ、スライム、くまモン、ふなっしー\n")
    f.write(f"- ムスカ大佐\n\n")
    
    f.write(f"## ✅ データベース完成！\n")
    f.write(f"全ての重要人物が追加され、包括的な日本の有名人データベースが完成しました。")

print(f"\n📄 最終レポート保存: {report_path}")