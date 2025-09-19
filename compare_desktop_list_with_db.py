import pandas as pd
from datetime import datetime

# デスクトップのCSVファイルを読み込む
desktop_path = '/Users/admin/Desktop/______________1_______300__.csv'
desktop_df = pd.read_csv(desktop_path, encoding='utf-8-sig')

# データベースを読み込む
db_path = 'ultra_think_COMPLETE_DATABASE_20250825_235105.csv'
db_df = pd.read_csv(db_path, encoding='utf-8-sig')

print(f"デスクトップCSV: {len(desktop_df)}人")
print(f"データベース: {len(db_df)}人")
print("=" * 60)

# データベース内の人物名を取得
db_names = set()
if 'person_name_ja' in db_df.columns:
    db_names.update(db_df['person_name_ja'].dropna().str.strip().tolist())
if 'person_name_display' in db_df.columns:
    db_names.update(db_df['person_name_display'].dropna().str.strip().tolist())

# 名前の正規化関数
def normalize_name(name):
    if pd.isna(name):
        return ""
    import re
    # 括弧内のグループ名を除去
    name = str(name)
    name = re.sub(r'[（\(][^）\)]+[）\)]', '', name)
    return name.strip()

# データベース内の正規化された名前セットを作成
db_normalized = set()
for name in db_names:
    if isinstance(name, str):
        normalized = normalize_name(name)
        if normalized:
            db_normalized.add(normalized)

# デスクトップCSVから人物をチェック
missing_persons = []
found_persons = []

# 表示名と素の名前の両方をチェック
for idx, row in desktop_df.iterrows():
    display_name = str(row['表示名']) if pd.notna(row['表示名']) else ""
    raw_name = str(row['素の名前']) if pd.notna(row['素の名前']) else ""
    
    # 両方の名前でチェック
    found = False
    
    # 表示名でチェック
    if display_name in db_names:
        found = True
    # 素の名前でチェック
    elif raw_name in db_names or raw_name in db_normalized:
        found = True
    # 正規化した名前でチェック
    elif normalize_name(display_name) in db_normalized:
        found = True
    elif normalize_name(raw_name) in db_normalized:
        found = True
    
    if found:
        found_persons.append({
            '表示名': display_name,
            '素の名前': raw_name,
            'グループ/作品': row['グループ/作品'] if pd.notna(row['グループ/作品']) else "",
            '区分': row['区分'] if pd.notna(row['区分']) else "",
            '分野': row['分野'] if pd.notna(row['分野']) else ""
        })
    else:
        missing_persons.append({
            '表示名': display_name,
            '素の名前': raw_name,
            'グループ/作品': row['グループ/作品'] if pd.notna(row['グループ/作品']) else "",
            '区分': row['区分'] if pd.notna(row['区分']) else "",
            '分野': row['分野'] if pd.notna(row['分野']) else ""
        })

# 結果を出力
print(f"\n📊 分析結果:")
print(f"- デスクトップCSVの人物: {len(desktop_df)}人")
print(f"- データベースに存在: {len(found_persons)}人")
print(f"- データベースに存在しない: {len(missing_persons)}人")
print("=" * 60)

if missing_persons:
    print(f"\n📋 データベースに存在しない人物 (上位50人):")
    print("-" * 60)
    
    # 分野別に分類
    categories = {}
    for person in missing_persons:
        field = person['分野']
        if field not in categories:
            categories[field] = []
        categories[field].append(person)
    
    # 分野別に出力
    for field, persons in categories.items():
        if persons:
            print(f"\n【{field}】({len(persons)}人)")
            for i, person in enumerate(persons[:10], 1):  # 各分野最大10人まで表示
                display = person['表示名']
                raw = person['素の名前']
                group = person['グループ/作品']
                if group:
                    print(f"  {i}. {display} (素の名前: {raw}, グループ: {group})")
                else:
                    print(f"  {i}. {display} (素の名前: {raw})")
            if len(persons) > 10:
                print(f"  ... 他{len(persons)-10}人")

# レポートファイル生成
report_path = f'DESKTOP_LIST_MISSING_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(f"# デスクトップリスト欠落人物レポート\n")
    f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"## 📊 統計\n")
    f.write(f"- デスクトップCSV: {len(desktop_df)}人\n")
    f.write(f"- データベースに存在: {len(found_persons)}人\n")
    f.write(f"- データベースに欠落: {len(missing_persons)}人\n\n")
    
    if missing_persons:
        f.write(f"## 📋 欠落人物リスト\n\n")
        for field, persons in categories.items():
            if persons:
                f.write(f"### {field} ({len(persons)}人)\n\n")
                for person in persons:
                    display = person['表示名']
                    raw = person['素の名前']
                    group = person['グループ/作品']
                    if group:
                        f.write(f"- {display} (素: {raw}, グループ: {group})\n")
                    else:
                        f.write(f"- {display} (素: {raw})\n")
                f.write("\n")

print(f"\n📄 レポート保存: {report_path}")

# CSVファイルに欠落人物を保存
if missing_persons:
    missing_df = pd.DataFrame(missing_persons)
    missing_csv_path = f'MISSING_PERSONS_FROM_DESKTOP_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    missing_df.to_csv(missing_csv_path, index=False, encoding='utf-8-sig')
    print(f"📄 欠落人物CSV保存: {missing_csv_path}")