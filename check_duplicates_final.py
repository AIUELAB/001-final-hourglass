import pandas as pd
from datetime import datetime
from collections import Counter

# CSVファイルを読み込む
csv_path = 'ultra_think_with_recognition_20250825_225556.csv'
df = pd.read_csv(csv_path, encoding='utf-8-sig')

print(f"データベース総数: {len(df)}人")
print("=" * 60)

# 1. person_name_ja + birth_year でのチェック
print("\n📊 person_name_ja + birth_year での重複チェック")
print("-" * 60)

# NaNを文字列に変換して比較可能にする
df['check_key'] = df.apply(lambda x: (
    str(x['person_name_ja']) if pd.notna(x['person_name_ja']) else 'NONE',
    str(x['birth_year']) if pd.notna(x['birth_year']) else 'NONE'
), axis=1)

# 重複をカウント
duplicate_counts = Counter(df['check_key'])
duplicates = {k: v for k, v in duplicate_counts.items() if v > 1}

if duplicates:
    print(f"⚠️ 重複が見つかりました: {len(duplicates)}組")
    print("\n重複詳細:")
    
    for (name_ja, birth_year), count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True):
        print(f"\n  {name_ja} (誕生年: {birth_year}) - {count}件")
        
        # 該当する行を表示
        mask = df['check_key'] == (name_ja, birth_year)
        dup_rows = df[mask][['person_name_ja', 'birth_year', 'person_name_display', 
                             'occupation', 'nationality', 'name_recognition', 'phase']]
        
        for idx, row in dup_rows.iterrows():
            print(f"    [{idx}] display: {row['person_name_display']}, "
                  f"職業: {row['occupation']}, 国籍: {row['nationality']}, "
                  f"認知度: {row['name_recognition']}, phase: {row['phase']}")
else:
    print("✅ person_name_ja + birth_year での重複はありません")

# 2. person_name_display での重複チェック
print("\n📊 person_name_display での重複チェック")
print("-" * 60)

display_counts = df['person_name_display'].value_counts()
display_duplicates = display_counts[display_counts > 1]

if len(display_duplicates) > 0:
    print(f"⚠️ 同じ表示名を持つ人物: {len(display_duplicates)}組")
    print("\n重複詳細 (上位20件):")
    
    for display_name, count in display_duplicates.head(20).items():
        print(f"\n  '{display_name}' - {count}件")
        
        # 該当する行を表示
        mask = df['person_name_display'] == display_name
        dup_rows = df[mask][['person_name_ja', 'birth_year', 'occupation', 
                             'nationality', 'name_recognition', 'phase']]
        
        for idx, row in dup_rows.iterrows():
            print(f"    [{idx}] {row['person_name_ja']} ({row['birth_year']}), "
                  f"職業: {row['occupation']}, 認知度: {row['name_recognition']}")
else:
    print("✅ person_name_display での重複はありません")

# 3. 完全一致チェック（全フィールド）
print("\n📊 完全一致する行のチェック")
print("-" * 60)

# 完全に同じ行があるかチェック
duplicated_rows = df.duplicated(keep=False)
num_duplicated = duplicated_rows.sum()

if num_duplicated > 0:
    print(f"⚠️ 完全に同じ行が {num_duplicated} 件見つかりました")
    
    # 重複している行を表示
    dup_df = df[duplicated_rows].sort_values(['person_name_ja', 'birth_year'])
    print("\n完全一致の詳細:")
    for idx, row in dup_df.head(10).iterrows():
        print(f"  [{idx}] {row['person_name_ja']} - {row['person_name_display']} ({row['birth_year']})")
else:
    print("✅ 完全に同じ行はありません")

# 4. 統計情報
print("\n📊 統計情報")
print("-" * 60)
print(f"総人数: {len(df)}人")
print(f"ユニークな person_name_ja: {df['person_name_ja'].nunique()}人")
print(f"ユニークな person_name_display: {df['person_name_display'].nunique()}人")
print(f"ユニークな (person_name_ja, birth_year): {len(set(df['check_key']))}組")

# 5. 推奨される削除対象
print("\n🎯 削除推奨リスト")
print("-" * 60)

remove_indices = []

# person_name_ja + birth_year が重複している場合、認知度が低い方を削除候補に
if duplicates:
    for (name_ja, birth_year), count in duplicates.items():
        mask = df['check_key'] == (name_ja, birth_year)
        dup_rows = df[mask].sort_values('name_recognition', ascending=False)
        
        # 最初の1つ以外を削除候補に
        if len(dup_rows) > 1:
            for idx in dup_rows.index[1:]:
                remove_indices.append(idx)
                print(f"削除候補 [{idx}]: {df.loc[idx, 'person_name_ja']} - "
                      f"{df.loc[idx, 'person_name_display']} (認知度: {df.loc[idx, 'name_recognition']})")

if remove_indices:
    print(f"\n削除推奨数: {len(remove_indices)}件")
    
    # 削除後のデータを保存
    clean_df = df.drop(remove_indices)
    output_path = f'ultra_think_no_duplicates_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    clean_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"\n✅ 重複削除後のファイルを保存: {output_path}")
    print(f"   削除前: {len(df)}人 → 削除後: {len(clean_df)}人")
else:
    print("削除推奨なし - データベースはクリーンです！")

# レポート生成
report_path = f'DUPLICATE_CHECK_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.md'
with open(report_path, 'w', encoding='utf-8') as f:
    f.write(f"# 重複チェックレポート\n")
    f.write(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    f.write(f"## 📊 サマリー\n")
    f.write(f"- 総人数: {len(df)}人\n")
    f.write(f"- person_name_ja + birth_year の重複: {len(duplicates)}組\n")
    f.write(f"- person_name_display の重複: {len(display_duplicates)}組\n")
    f.write(f"- 完全一致する行: {num_duplicated}件\n")
    f.write(f"- 削除推奨: {len(remove_indices)}件\n\n")
    
    if duplicates:
        f.write(f"## ⚠️ 重複詳細\n\n")
        for (name_ja, birth_year), count in sorted(duplicates.items(), key=lambda x: x[1], reverse=True)[:20]:
            f.write(f"### {name_ja} ({birth_year}) - {count}件\n")
            mask = df['check_key'] == (name_ja, birth_year)
            dup_rows = df[mask]
            for idx, row in dup_rows.iterrows():
                f.write(f"- [{idx}] {row['person_name_display']} | {row['occupation']} | 認知度: {row['name_recognition']}\n")
            f.write("\n")

print(f"\n📄 レポートを保存: {report_path}")