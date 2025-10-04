from src.secure_config import config
#!/usr/bin/env python3
"""
FirestoreのepisodesコレクションからEOF関連のエピソードを検索
"""

import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime
import json
import csv

# Firebase初期化
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(config.firebase_credentials_path)
        firebase_admin.initialize_app(cred)
    except FileNotFoundError:
        print("Error: Firebase service account key file not found")
        exit(1)

db = firestore.client()

def search_episodes(search_term="EOF"):
    """エピソードを検索してCSVに出力"""
    
    print(f"🔍 '{search_term}' を含むエピソードを検索中...")
    print("=" * 60)
    
    try:
        episodes_ref = db.collection('episodes')
        all_episodes = episodes_ref.stream()
        
        matching_episodes = []
        total_count = 0
        
        for episode in all_episodes:
            total_count += 1
            doc_id = episode.id
            data = episode.to_dict()
            
            # IDまたはデータ内に検索語が含まれるか確認
            if search_term.lower() in doc_id.lower():
                matching_episodes.append({
                    'id': doc_id,
                    'data': data,
                    'match_type': 'ID'
                })
            else:
                # データ内の全フィールドを検索
                for key, value in data.items():
                    if isinstance(value, str) and search_term.lower() in value.lower():
                        matching_episodes.append({
                            'id': doc_id,
                            'data': data,
                            'match_type': f'Field: {key}'
                        })
                        break
        
        print(f"✅ 検索完了: {total_count}件中{len(matching_episodes)}件が一致")
        
        if matching_episodes:
            # タイムスタンプ付きファイル名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"firebase_search_results_{timestamp}.csv"
            json_filename = f"firebase_search_results_{timestamp}.json"
            
            # JSON保存
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(matching_episodes, f, ensure_ascii=False, indent=2, default=str)
            print(f"📄 JSON保存: {json_filename}")
            
            # CSV保存
            if matching_episodes:
                # 全フィールドを収集
                all_fields = set()
                for match in matching_episodes:
                    all_fields.update(match['data'].keys())
                all_fields = sorted(list(all_fields))
                
                with open(csv_filename, 'w', encoding='utf-8-sig', newline='') as f:
                    fieldnames = ['_id', '_match_type'] + all_fields
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    
                    for match in matching_episodes:
                        row = {'_id': match['id'], '_match_type': match['match_type']}
                        for field in all_fields:
                            row[field] = match['data'].get(field, '')
                        writer.writerow(row)
                
                print(f"📊 CSV保存: {csv_filename}")
            
            # 最初の5件を表示
            print(f"\n📋 検索結果（最初の5件）:")
            for i, match in enumerate(matching_episodes[:5], 1):
                print(f"\n{i}. ID: {match['id']}")
                print(f"   一致箇所: {match['match_type']}")
                data = match['data']
                if 'person_name' in data:
                    print(f"   人物: {data['person_name']}")
                if 'age' in data:
                    print(f"   年齢: {data['age']}")
                if 'content' in data:
                    content = data['content']
                    if len(content) > 100:
                        content = content[:97] + "..."
                    print(f"   内容: {content}")
        else:
            print(f"\n❌ '{search_term}' を含むエピソードは見つかりませんでした")
        
        # 全エピソードをCSVに出力（バックアップ用）
        print("\n📚 全エピソードをバックアップ中...")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        all_csv = f"firebase_all_episodes_backup_{timestamp}.csv"
        
        # 全エピソードを再取得
        all_episodes = episodes_ref.limit(100).stream()  # 最初の100件のみ
        episodes_list = []
        all_fields = set()
        
        for episode in all_episodes:
            data = episode.to_dict()
            data['_id'] = episode.id
            episodes_list.append(data)
            all_fields.update(data.keys())
        
        if episodes_list:
            all_fields = sorted(list(all_fields))
            with open(all_csv, 'w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=all_fields)
                writer.writeheader()
                
                for episode_data in episodes_list:
                    row = {field: episode_data.get(field, '') for field in all_fields}
                    writer.writerow(row)
            
            print(f"✅ 全エピソードバックアップ: {all_csv}")
            print(f"   （最初の100件のみ）")
        
        return matching_episodes
        
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return []

def main():
    """メイン実行"""
    print("🚀 Firebase エピソード検索ツール")
    print("=" * 60)
    
    # "EOF"を検索
    results = search_episodes("EOF")
    
    # 他の検索語も試す
    other_searches = ["<", ">", "end", "END", "finish"]
    for term in other_searches:
        print(f"\n追加検索: '{term}'")
        search_episodes(term)

if __name__ == "__main__":
    main()