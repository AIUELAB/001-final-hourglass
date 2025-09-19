from src.secure_config import config
#!/usr/bin/env python3
"""
nameフィールドを3つのフィールドに分割
- person_name: 原語表記
- person_name_ja: 日本語名
- person_name_display: 表示用短縮名、及び表示用所属先付属の個人名
"""

import json
import re
import shutil
import time
from datetime import datetime

import firebase_admin
from firebase_admin import credentials, firestore

# Firebase初期化
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(config.firebase_credentials_path)
        firebase_admin.initialize_app(cred)
    except FileNotFoundError:
        print("Error: Firebase service account key file not found")
        exit(1)

db = firestore.client()

# 表示用短縮名の辞書（主要な人物）
DISPLAY_NAME_MAP = {
    # 作曲家
    'ヴォルフガング・アマデウス・モーツァルト': 'モーツァルト',
    'Wolfgang Amadeus Mozart': 'モーツァルト',
    'ルートヴィヒ・ヴァン・ベートーヴェン': 'ベートーヴェン',
    'Ludwig van Beethoven': 'ベートーヴェン',
    'ヨハン・セバスチャン・バッハ': 'バッハ',
    'Johann Sebastian Bach': 'バッハ',
    'フレデリック・ショパン': 'ショパン',
    'Frédéric Chopin': 'ショパン',
    
    # 科学者
    'アルベルト・アインシュタイン': 'アインシュタイン',
    'Albert Einstein': 'アインシュタイン',
    'アイザック・ニュートン': 'ニュートン',
    'Isaac Newton': 'ニュートン',
    'ガリレオ・ガリレイ': 'ガリレオ',
    'Galileo Galilei': 'ガリレオ',
    
    # 芸術家
    'レオナルド・ダ・ヴィンチ': 'ダ・ヴィンチ',
    'Leonardo da Vinci': 'ダ・ヴィンチ',
    'パブロ・ピカソ': 'ピカソ',
    'Pablo Picasso': 'ピカソ',
    'フィンセント・ファン・ゴッホ': 'ゴッホ',
    'Vincent van Gogh': 'ゴッホ',
    
    # 政治家
    'マーガレット・サッチャー': 'サッチャー',
    'Margaret Thatcher': 'サッチャー',
    'ウィンストン・チャーチル': 'チャーチル',
    'Winston Churchill': 'チャーチル',
    
    # 日本の歴史人物（短縮形）
    '織田信長': '信長',
    '豊臣秀吉': '秀吉',
    '徳川家康': '家康',
    '坂本龍馬': '龍馬',
    '西郷隆盛': '西郷',
}

# お笑いコンビ名リスト
COMEDY_DUOS = ['中川家', 'サンドウィッチマン', 'フットボールアワー', 
               'ますだおかだ', '千鳥', 'ダウンタウン', 'ナインティナイン',
               'とんねるず', 'ウッチャンナンチャン', '爆笑問題', 'オードリー',
               'バナナマン', 'かまいたち', 'ミルクボーイ', '霜降り明星']

def is_japanese(text):
    """日本語が含まれるかチェック"""
    return bool(re.search(r'[ぁ-ん]|[ァ-ヴ]|[一-龯]', text))

def is_western(text):
    """西洋名かチェック（英語のみ）"""
    return bool(re.search(r'^[A-Za-z\s\-\.\']+$', text))

def is_comedy_duo(name):
    """お笑いコンビ形式かチェック"""
    return any(duo in name for duo in COMEDY_DUOS) and '・' in name

def get_display_name(name):
    """表示用短縮名を取得"""
    # 辞書に登録されている場合
    if name in DISPLAY_NAME_MAP:
        return DISPLAY_NAME_MAP[name]
    
    # お笑いコンビ形式はそのまま
    if is_comedy_duo(name):
        return name
    
    # 中点で区切られた長い名前の場合
    if '・' in name and not is_comedy_duo(name):
        parts = name.split('・')
        # 最後の部分（通常は姓）を返す
        if len(parts) >= 2:
            # 西洋名の場合は最後の部分
            if not is_japanese(name):
                return parts[-1]
            # 日本語の長い名前（例：ヨハン・セバスチャン・バッハ）
            else:
                return parts[-1]
    
    # スペースで区切られた西洋名
    if ' ' in name and is_western(name):
        parts = name.split()
        if len(parts) >= 3:
            # フルネームの場合は姓のみ
            return parts[-1]
    
    # その他はそのまま
    return name

def transform_name_field(person_data):
    """
    nameフィールドを3つのフィールドに変換
    
    Args:
        person_data: 人物データ（辞書）
        
    Returns:
        変換後のデータ（辞書）
    """
    if 'name' not in person_data:
        return person_data
    
    name = person_data['name']
    
    # 初期値設定
    person_name = name  # デフォルトは元のname
    person_name_ja = name  # デフォルトは元のname
    person_name_display = get_display_name(name)
    
    # 日本語名の場合
    if is_japanese(name):
        person_name_ja = name
        # 英語版があるか確認（nationality等から推測）
        if person_data.get('nationality') not in ['日本', 'Japan', '']:
            # 外国人だが日本語表記の場合、person_nameは空または同じ
            person_name = name  # または適切な英語名があれば設定
    
    # 西洋名の場合
    elif is_western(name):
        person_name = name
        # 日本語版を生成（ここでは仮に同じ値を設定）
        person_name_ja = name  # 本来は変換テーブルが必要
    
    # 新しいフィールドを追加
    person_data['person_name'] = person_name
    person_data['person_name_ja'] = person_name_ja
    person_data['person_name_display'] = person_name_display
    
    # 元のnameフィールドは削除
    if 'name' in person_data:
        del person_data['name']
    
    return person_data

def process_json_file():
    """JSONファイルを処理"""
    print("\n=== JSONファイル処理 ===")
    
    input_file = 'final_12410_firebase_20250822_201828.json'
    
    # バックアップ作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'final_12410_name_transform_backup_{timestamp}.json'
    shutil.copy2(input_file, backup_file)
    print(f"✅ バックアップ作成: {backup_file}")
    
    # JSON読み込み
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 変換処理
    transform_count = 0
    transform_log = []
    
    for key, person in data.items():
        if 'name' in person:
            original_name = person['name']
            transformed = transform_name_field(person.copy())
            
            # ログ記録
            transform_log.append({
                'id': key,
                'original_name': original_name,
                'person_name': transformed.get('person_name'),
                'person_name_ja': transformed.get('person_name_ja'),
                'person_name_display': transformed.get('person_name_display')
            })
            
            # データ更新
            data[key] = transformed
            transform_count += 1
    
    # 結果を保存
    output_file = f'final_12410_name_transformed_{timestamp}.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    # ログ保存
    log_file = f'name_transform_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'transform_count': transform_count,
            'timestamp': timestamp,
            'samples': transform_log[:50]  # 最初の50件をサンプルとして保存
        }, f, ensure_ascii=False, indent=2)
    
    # 元のファイルを更新
    shutil.copy2(output_file, input_file)
    
    print(f"✅ 変換件数: {transform_count}件")
    print(f"✅ 出力ファイル: {output_file}")
    print(f"✅ ログファイル: {log_file}")
    print(f"✅ 元のファイルを更新: {input_file}")
    
    # サンプル表示
    print("\n📝 変換例（最初の10件）:")
    for log in transform_log[:10]:
        print(f"  {log['original_name']}")
        print(f"    → person_name: {log['person_name']}")
        print(f"    → person_name_ja: {log['person_name_ja']}")
        print(f"    → person_name_display: {log['person_name_display']}")
    
    return transform_count, transform_log

def process_firebase():
    """Firebaseのエピソードを処理"""
    print("\n=== Firebase エピソード処理 ===")
    
    episodes_ref = db.collection('episodes')
    
    # person_name_shortをperson_name_displayに変更も同時に行う
    docs = episodes_ref.stream()
    update_needed = []
    
    for doc in docs:
        data = doc.to_dict()
        update_data = {}
        
        # person_name_shortがある場合はperson_name_displayに変更
        if 'person_name_short' in data:
            update_data['person_name_display'] = data['person_name_short']
            update_data['person_name_short'] = firestore.DELETE_FIELD
            update_needed.append({
                'id': doc.id,
                'update_data': update_data
            })
    
    print(f"更新対象: {len(update_needed)}件")
    
    # バッチ更新
    if update_needed:
        batch_size = 500
        for i in range(0, len(update_needed), batch_size):
            batch = db.batch()
            batch_items = update_needed[i:i+batch_size]
            
            for item in batch_items:
                doc_ref = episodes_ref.document(item['id'])
                batch.update(doc_ref, item['update_data'])
            
            batch.commit()
            print(f"  処理済み: {min(i+batch_size, len(update_needed))}/{len(update_needed)}")
            time.sleep(0.5)
    
    return len(update_needed)

def main():
    """メイン処理"""
    print("=" * 60)
    print("name → person_name, person_name_ja, person_name_display 変換")
    print("=" * 60)
    
    try:
        # JSONファイル処理
        json_count, transform_log = process_json_file()
        
        # Firebase処理
        firebase_count = process_firebase()
        
        print("\n🎉 変換完了!")
        print(f"   JSONファイル: {json_count}件")
        print(f"   Firebase: {firebase_count}件")
        
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()