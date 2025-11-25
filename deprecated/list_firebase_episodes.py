from src.secure_config import config
#!/usr/bin/env python3
"""
Firestoreのepisodesコレクションをリスト表示
"""

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

def list_episodes(limit=20):
    """episodesコレクションのIDをリスト表示"""

    print("📚 エピソード一覧を取得中...")
    print("=" * 60)

    try:
        episodes_ref = db.collection('episodes')
        episodes = episodes_ref.limit(limit).stream()

        count = 0
        for episode in episodes:
            count += 1
            doc_id = episode.id
            data = episode.to_dict()

            # 主要フィールドを取得
            person_name = data.get('person_name', data.get('person', 'Unknown'))
            age = data.get('age', 'N/A')
            year = data.get('year', 'N/A')

            print(f"{count:3}. ID: '{doc_id}'")
            print(f"     人物: {person_name}, 年齢: {age}, 年: {year}")
            print("-" * 60)

        print(f"\n合計: {count} エピソード（最大{limit}件表示）")

        # 特殊文字を含むIDを検索
        print("\n🔍 特殊文字を含むエピソードIDを検索中...")
        all_episodes = episodes_ref.stream()
        special_ids = []

        for episode in all_episodes:
            doc_id = episode.id
            # 特殊文字を含むIDを検出
            if any(char in doc_id for char in ['<', '>', '/', '\\', '"', "'", '\n', '\r', '\t']):
                special_ids.append(doc_id)

        if special_ids:
            print(f"\n⚠️ 特殊文字を含むID: {len(special_ids)}件")
            for sid in special_ids[:10]:  # 最初の10件のみ表示
                print(f"  - '{sid}'")
        else:
            print("特殊文字を含むIDは見つかりませんでした")

    except Exception as e:
        print(f"エラー: {str(e)}")

if __name__ == "__main__":
    list_episodes(50)  # 最初の50件を表示
