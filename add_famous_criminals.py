import pandas as pd
from datetime import datetime

# データベースを読み込む
db_path = 'ultra_think_FINAL_COMPLETE_20250826_000013.csv'
df = pd.read_csv(db_path, encoding='utf-8-sig')

print(f"現在のデータベース: {len(df)}人")

# 有名犯罪者のリスト（教育的・歴史的観点から重要な人物）
# 認知度スコアは低めに設定（20-40）
famous_criminals = [
    # テロリスト
    ("テッド・カジンスキー", 1942, "テロリスト（ユナボマー）", "アメリカ", 35),
    ("オサマ・ビン・ラディン", 1957, "テロリスト", "サウジアラビア", 40),
    ("ティモシー・マクベイ", 1968, "テロリスト", "アメリカ", 30),
    ("ラムジ・ユセフ", 1968, "テロリスト", "クウェート", 25),
    ("アンダース・ブレイビク", 1979, "テロリスト", "ノルウェー", 30),
    ("アブ・バクル・アル＝バグダーディー", 1971, "テロリスト（IS指導者）", "イラク", 30),
    
    # 日本のカルト・事件
    ("松本智津夫", 1955, "カルト教祖（麻原彰晃）", "日本", 35),
    ("宅間守", 1963, "犯罪者", "日本", 25),
    ("加藤智大", 1982, "犯罪者", "日本", 25),
    
    # 組織犯罪
    ("パブロ・エスコバル", 1949, "麻薬王", "コロンビア", 35),
    ("ホアキン・グスマン", 1957, "麻薬王（エル・チャポ）", "メキシコ", 30),
    ("アル・カポネ", 1899, "ギャング", "アメリカ", 40),
    ("ラッキー・ルチアーノ", 1897, "マフィア", "イタリア", 30),
    
    # 連続殺人犯
    ("テッド・バンディ", 1946, "連続殺人犯", "アメリカ", 35),
    ("ジェフリー・ダーマー", 1960, "連続殺人犯", "アメリカ", 35),
    ("ジョン・ウェイン・ゲイシー", 1942, "連続殺人犯", "アメリカ", 30),
    ("デニス・レイダー", 1945, "連続殺人犯（BTK）", "アメリカ", 25),
    ("チャールズ・マンソン", 1934, "カルト指導者・殺人犯", "アメリカ", 35),
    ("リチャード・ラミレス", 1960, "連続殺人犯", "アメリカ", 25),
    ("アイリーン・ウォーノス", 1956, "連続殺人犯", "アメリカ", 25),
    ("アンドレイ・チカチーロ", 1936, "連続殺人犯", "ロシア", 25),
    ("ペドロ・ロペス", 1948, "連続殺人犯", "コロンビア", 20),
    ("ハロルド・シップマン", 1946, "連続殺人犯（医師）", "イギリス", 25),
    ("ルカ・マニョッタ", 1982, "殺人犯", "カナダ", 20),
    ("ポール・ベルナルド", 1964, "連続殺人犯", "カナダ", 20),
    ("カーラ・ホモルカ", 1970, "連続殺人犯", "カナダ", 20),
    
    # 経済犯罪
    ("バーナード・マドフ", 1938, "詐欺師", "アメリカ", 30),
    ("ジェフリー・スキリング", 1953, "経済犯罪者（エンロン）", "アメリカ", 25),
    ("エリザベス・ホームズ", 1984, "詐欺師（Theranos）", "アメリカ", 30),
    
    # 戦争犯罪
    ("ラトコ・ムラディッチ", 1943, "戦争犯罪者", "ボスニア", 20),
    ("ラドヴァン・カラジッチ", 1945, "戦争犯罪者", "ボスニア", 20),
    
    # 歴史的犯罪者（追加）
    ("ジャック・ザ・リッパー", None, "連続殺人犯（未解決）", "イギリス", 35),
    ("ボニー・パーカー", 1910, "強盗犯", "アメリカ", 30),
    ("クライド・バロウ", 1909, "強盗犯", "アメリカ", 30),
    ("ジェシー・ジェームズ", 1847, "無法者", "アメリカ", 30),
    ("ビリー・ザ・キッド", 1859, "無法者", "アメリカ", 30),
]

# 新しいデータフレームを作成
new_rows = []
for item in famous_criminals:
    name = item[0]
    birth_year = item[1] if len(item) > 1 else None
    occupation = item[2] if len(item) > 2 else "犯罪者"
    nationality = item[3] if len(item) > 3 else "不明"
    recognition = item[4] if len(item) > 4 else 20
    
    # カテゴリを判定
    if 'テロ' in occupation:
        main_category = '歴史的人物（負）'
    elif 'カルト' in occupation:
        main_category = '歴史的人物（負）'
    elif '麻薬' in occupation or 'マフィア' in occupation or 'ギャング' in occupation:
        main_category = '組織犯罪'
    elif '連続殺人' in occupation or '殺人' in occupation:
        main_category = '犯罪者'
    elif '詐欺' in occupation or '経済犯罪' in occupation:
        main_category = '経済犯罪'
    elif '戦争犯罪' in occupation:
        main_category = '戦争犯罪'
    elif '無法者' in occupation or '強盗' in occupation:
        main_category = '歴史的犯罪者'
    else:
        main_category = 'その他'
    
    new_row = {
        'person_name_ja': name,
        'person_name_display': name,
        'birth_year': birth_year,
        'occupation': occupation,
        'name_recognition': recognition,
        'nationality': nationality,
        'is_fictional': 'FALSE',
        'main_category': main_category,
        'phase': 'CriminalAddition',
        'note': '教育的・歴史的観点から追加'
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
output_path = f'ultra_think_WITH_CRIMINALS_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
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
for category, count in category_counts.head(20).items():
    print(f"- {category}: {count}人")

# 犯罪者関連の統計
criminal_categories = ['歴史的人物（負）', '組織犯罪', '犯罪者', '経済犯罪', '戦争犯罪', '歴史的犯罪者']
criminal_count = combined_df[combined_df['main_category'].isin(criminal_categories)].shape[0]
print(f"\n⚠️ 犯罪者関連: {criminal_count}人")

# 最終レポート生成
report_path = f'CRIMINAL_ADDITION_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(f"# 有名犯罪者追加レポート\n")
    f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"## 📊 統計\n")
    f.write(f"- **追加前**: {len(df)}人\n")
    f.write(f"- **追加数**: {len(new_rows)}人\n")
    f.write(f"- **追加後**: {len(combined_df)}人\n\n")
    
    f.write(f"## ⚠️ 追加した犯罪者カテゴリ\n\n")
    f.write(f"### テロリスト（6人）\n")
    f.write(f"- テッド・カジンスキー（ユナボマー）\n")
    f.write(f"- オサマ・ビン・ラディン\n")
    f.write(f"- ティモシー・マクベイ\n")
    f.write(f"- その他\n\n")
    
    f.write(f"### 日本の事件関係者（3人）\n")
    f.write(f"- 松本智津夫（麻原彰晃）\n")
    f.write(f"- 宅間守\n")
    f.write(f"- 加藤智大\n\n")
    
    f.write(f"### 組織犯罪（4人）\n")
    f.write(f"- パブロ・エスコバル\n")
    f.write(f"- アル・カポネ\n")
    f.write(f"- その他\n\n")
    
    f.write(f"### 連続殺人犯（13人）\n")
    f.write(f"- テッド・バンディ\n")
    f.write(f"- ジェフリー・ダーマー\n")
    f.write(f"- チャールズ・マンソン\n")
    f.write(f"- その他\n\n")
    
    f.write(f"### 経済犯罪（3人）\n")
    f.write(f"- バーナード・マドフ\n")
    f.write(f"- エリザベス・ホームズ\n")
    f.write(f"- ジェフリー・スキリング\n\n")
    
    f.write(f"### 歴史的犯罪者（5人）\n")
    f.write(f"- ジャック・ザ・リッパー\n")
    f.write(f"- ボニー&クライド\n")
    f.write(f"- ジェシー・ジェームズ\n")
    f.write(f"- ビリー・ザ・キッド\n\n")
    
    f.write(f"## 📝 注記\n")
    f.write(f"- 教育的・歴史的観点から重要な人物として追加\n")
    f.write(f"- 認知度スコアは意図的に低く設定（20-40）\n")
    f.write(f"- 被害者への配慮から詳細な情報は最小限に留めています\n")

print(f"\n📄 レポート保存: {report_path}")
print("\n🎊 データベース更新完了！")
print(f"総人数: {len(combined_df)}人")