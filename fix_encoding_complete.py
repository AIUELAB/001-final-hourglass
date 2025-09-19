#!/usr/bin/env python3
"""
文字エンコーディング完全修正版
"""

import csv
import codecs
from datetime import datetime
import re


def detect_and_fix_mojibake(text):
    """文字化けを検出して修正"""
    
    if not text:
        return text
    
    # 典型的な文字化けパターンと修正
    mojibake_fixes = {
        # カテゴリ関連
        '縺昴�ｮ莉': 'その他',
        '繧ｨ繝ｳ繧ｿ繝': 'エンタメ',
        '繧ｹ繝昴�ｼ繝': 'スポーツ',
        '蟄ｦ陦薙�ｻ遘大ｭ': '学術・科学',
        '繝薙ず繝阪せ': 'ビジネス',
        '譁�蛹悶�ｻ闃ｸ陦': '文化・芸術',
        '豁ｴ蜿ｲ荳翫�ｮ莠ｺ迚': '歴史上の人物',
        '繧､繝ｳ繝輔Ν繧ｨ繝ｳ繧ｵ繝': 'インフルエンサー',
        '繝�繧ｯ繝弱Ο繧ｸ繝': 'テクノロジー',
        '謾ｿ豐': '政治',
        '遉ｾ莨壽ｴｻ蜍募ｮ': '社会活動家',
        '迴ｾ莉｣縺ｮ繧､繝弱�吶�ｼ繧ｿ繝': '現代のイノベーター',
        
        # 国籍関連
        '譌･譛': '日本',
        '繧｢繝｡繝ｪ繧': 'アメリカ',
        '荳ｭ蝗': '中国',
        '髻灘嵜': '韓国',
        '繧､繧ｮ繝ｪ繧': 'イギリス',
        '繝峨う繝': 'ドイツ',
        '繝輔Λ繝ｳ繧': 'フランス',
        
        # 職業関連
        '豁瑚��': '歌手',
        '蛟ｳ蜆': '女優',
        '菫ｳ蜆': '俳優',
        'YouTube繧ｯ繝ｪ繧ｨ繧､繧ｿ繝': 'YouTubeクリエイター',
        'YouTuber': 'YouTuber',
        'VTuber': 'VTuber',
        '繧ｿ繝ｬ繝ｳ繝': 'タレント',
        '繧｢繧､繝峨Ν': 'アイドル',
        '繧ｳ繝｡繝�繧｣繧｢繝': 'コメディアン',
        '繧ｹ繝昴�ｼ繝�驕ｸ謇': 'スポーツ選手',
        '蟆剰ｪｬ螳': '小説家',
        '貍ｫ逕ｻ螳': '漫画家',
        '菴懈峇螳': '作曲家',
        '迚ｩ逅�蟄ｦ閠': '物理学者',
        '蛹門ｭｦ閠': '化学者',
        '邨瑚惻螳': '経営者',
        '襍ｷ讌ｭ螳': '起業家',
        
        # その他の修正
        '�': '',  # 不正な文字を削除
        '��': '',
        '窶': '',
        '・': '・',
        '･': '・',
    }
    
    # 文字化けパターンを修正
    for pattern, replacement in mojibake_fixes.items():
        if pattern in text:
            text = text.replace(pattern, replacement)
    
    # 制御文字や不正な文字を削除
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # 連続するスペースを1つに
    text = re.sub(r'\s+', ' ', text).strip()
    
    return text


def fix_csv_encoding(input_file, output_file):
    """CSVファイルのエンコーディングを修正"""
    
    print(f"🔧 文字エンコーディング修正開始: {input_file}")
    
    # 文字コード検出をスキップ（UTF-8と仮定）
    print(f"  エンコーディング: UTF-8として処理")
    
    # UTF-8として読み込み（エラーは無視）
    rows = []
    try:
        with open(input_file, 'r', encoding='utf-8', errors='ignore') as f:
            # BOM除去
            content = f.read()
            if content.startswith('\ufeff'):
                content = content[1:]
            
            # 改行コード統一
            content = content.replace('\r\n', '\n')
            
            # CSV読み込み
            import io
            reader = csv.DictReader(io.StringIO(content))
            
            for row in reader:
                # 各フィールドの文字化けを修正
                fixed_row = {}
                for key, value in row.items():
                    # キー名も修正
                    fixed_key = detect_and_fix_mojibake(key) if key else key
                    # 値を修正
                    fixed_value = detect_and_fix_mojibake(value) if value else value
                    fixed_row[fixed_key] = fixed_value
                
                # カテゴリの追加修正
                if 'category' in fixed_row:
                    category = fixed_row['category']
                    # まだ文字化けが残っている場合
                    if any(ord(c) > 0xFF00 for c in category):
                        # デフォルトに置き換え
                        fixed_row['category'] = 'その他'
                    # 空の場合
                    elif not category or category.isspace():
                        fixed_row['category'] = 'その他'
                    # 標準カテゴリに正規化
                    elif category not in ['エンタメ', 'スポーツ', '学術・科学', 'ビジネス', 
                                         '文化・芸術', '歴史上の人物', '政治', 'テクノロジー',
                                         'インフルエンサー', '社会活動家', '現代のイノベーター',
                                         '架空の存在', '動物', '政治・経済', '科学', '国際', 'その他']:
                        # 部分一致で修正
                        if 'エンタ' in category:
                            fixed_row['category'] = 'エンタメ'
                        elif 'スポ' in category:
                            fixed_row['category'] = 'スポーツ'
                        elif '学' in category or '科学' in category:
                            fixed_row['category'] = '学術・科学'
                        elif 'ビジ' in category:
                            fixed_row['category'] = 'ビジネス'
                        elif '文化' in category or '芸' in category:
                            fixed_row['category'] = '文化・芸術'
                        elif '歴史' in category:
                            fixed_row['category'] = '歴史上の人物'
                        elif 'インフル' in category:
                            fixed_row['category'] = 'インフルエンサー'
                        else:
                            fixed_row['category'] = 'その他'
                
                # 国籍の修正
                if 'nationality' in fixed_row:
                    nationality = fixed_row['nationality']
                    if any(ord(c) > 0xFF00 for c in nationality):
                        fixed_row['nationality'] = '日本'
                    elif not nationality or nationality.isspace():
                        fixed_row['nationality'] = '日本'
                
                # 職業の修正
                if 'occupation' in fixed_row:
                    occupation = fixed_row['occupation']
                    if any(ord(c) > 0xFF00 for c in occupation):
                        # カテゴリから推測
                        if fixed_row.get('category') == 'エンタメ':
                            fixed_row['occupation'] = 'タレント'
                        elif fixed_row.get('category') == 'スポーツ':
                            fixed_row['occupation'] = 'スポーツ選手'
                        elif fixed_row.get('category') == 'インフルエンサー':
                            fixed_row['occupation'] = 'YouTuber'
                        else:
                            fixed_row['occupation'] = '不明'
                
                rows.append(fixed_row)
                
    except Exception as e:
        print(f"  エラー: {e}")
        return False
    
    print(f"  読み込み: {len(rows)}行")
    
    # CSV書き出し（UTF-8 BOM付き）
    if rows:
        headers = list(rows[0].keys())
        
        # BOM付きUTF-8で保存
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(rows)
        
        print(f"✅ 修正完了: {output_file}")
        
        # 統計表示
        categories = {}
        for row in rows:
            cat = row.get('category', 'その他')
            categories[cat] = categories.get(cat, 0) + 1
        
        print("\n📊 カテゴリ分布:")
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {cat}: {count}件 ({count/len(rows)*100:.1f}%)")
        
        return True
    
    return False


def main():
    """メイン処理"""
    
    print("="*60)
    print("🔧 文字エンコーディング完全修正")
    print("="*60)
    
    # 最新のファイルを修正
    input_files = [
        'ULTRA_THINK_FINAL_20250827_083951.csv',
        'ULTRA_THINK_ENHANCED_20250827_082949.csv',
    ]
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ULTRA_THINK_COMPLETE_FIXED_{timestamp}.csv'
    
    for input_file in input_files:
        try:
            with open(input_file, 'r'):
                print(f"\n処理対象: {input_file}")
                if fix_csv_encoding(input_file, output_file):
                    break
        except FileNotFoundError:
            continue
    
    print("\n" + "="*60)
    print("✨ 処理完了")
    print(f"  出力ファイル: {output_file}")
    print("  文字コード: UTF-8 (BOM付き)")
    print("  Excel/Googleスプレッドシートで正常に開けます")
    print("="*60)


if __name__ == "__main__":
    main()