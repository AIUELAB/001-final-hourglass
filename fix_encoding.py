#!/usr/bin/env python3
"""
文字エンコーディング修正
"""

import csv
import io
from datetime import datetime


def fix_encoding(input_file: str, output_file: str):
    """エンコーディングを修正"""
    
    print(f"📝 エンコーディング修正中: {input_file}")
    
    # ファイル読み込み（UTF-8で強制）
    with open(input_file, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()
        
        # BOM除去
        if content.startswith('\ufeff'):
            content = content[1:]
        
        # 改行コード統一
        content = content.replace('\r\n', '\n')
        content = content.replace('\r', '\n')
        
        # CSV読み込み
        csv_file = io.StringIO(content)
        reader = csv.DictReader(csv_file)
        rows = list(reader)
    
    print(f"  読み込み: {len(rows)}行")
    
    # カテゴリ修正マップ
    category_fixes = {
        'エンターテイメント': 'エンタメ',
        '歴史的偉人': '歴史上の人物',
        '現代のイノベーター': '現代のイノベーター',
    }
    
    # 文字化けしたカテゴリを修正
    for row in rows:
        # カテゴリフィールドをチェック
        category = row.get('category', '')
        
        # 文字化けチェック（非ASCII文字の異常パターン）
        if any(ord(c) > 127 and ord(c) < 256 for c in category):
            # デフォルトカテゴリに置換
            if 'エンタ' in category or 'music' in category.lower():
                row['category'] = 'エンタメ'
            elif 'スポ' in category or 'sport' in category.lower():
                row['category'] = 'スポーツ'
            elif '学' in category or 'academ' in category.lower():
                row['category'] = '学術・科学'
            elif 'ビジ' in category or 'business' in category.lower():
                row['category'] = 'ビジネス'
            elif '文化' in category or 'art' in category.lower():
                row['category'] = '文化・芸術'
            elif '歴史' in category or 'histor' in category.lower():
                row['category'] = '歴史上の人物'
            elif 'インフル' in category or 'influenc' in category.lower():
                row['category'] = 'インフルエンサー'
            elif 'テクノ' in category or 'tech' in category.lower():
                row['category'] = 'テクノロジー'
            elif '政治' in category or 'politic' in category.lower():
                row['category'] = '政治'
            else:
                row['category'] = 'その他'
        
        # 空のカテゴリも修正
        if not row.get('category'):
            row['category'] = 'その他'
        
        # その他のフィールドも確認
        for field in ['occupation', 'nationality']:
            value = row.get(field, '')
            if any(ord(c) > 127 and ord(c) < 256 for c in value):
                # 文字化けしている場合は既知の値に置換
                if field == 'nationality':
                    if '日' in value or 'japan' in value.lower():
                        row[field] = '日本'
                    elif 'america' in value.lower() or 'usa' in value.lower():
                        row[field] = 'アメリカ'
                    else:
                        row[field] = '不明'
                elif field == 'occupation':
                    # 職業は元の日本語部分を抽出
                    row[field] = ''.join(c for c in value if ord(c) > 256 or ord(c) < 127)
                    if not row[field]:
                        row[field] = '不明'
    
    # CSV書き出し
    if rows:
        headers = list(rows[0].keys())
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
    
    print(f"✅ 修正完了: {output_file}")
    print(f"  行数: {len(rows)}")
    
    # カテゴリ分布確認
    categories = {}
    for row in rows:
        cat = row.get('category', 'その他')
        categories[cat] = categories.get(cat, 0) + 1
    
    print("\n📊 カテゴリ分布:")
    for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {cat}: {count}件")


def main():
    """メイン処理"""
    
    print("="*60)
    print("🔧 文字エンコーディング修正")
    print("="*60)
    
    input_file = 'ULTRA_THINK_ENHANCED_20250827_082949.csv'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ULTRA_THINK_FINAL_{timestamp}.csv'
    
    fix_encoding(input_file, output_file)
    
    print("="*60)


if __name__ == "__main__":
    main()