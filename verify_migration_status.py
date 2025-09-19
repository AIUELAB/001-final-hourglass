import firebase_admin
from firebase_admin import credentials, firestore
from datetime import datetime

from src.secure_config import config
# Firebase初期化
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(config.firebase_credentials_path)
        firebase_admin.initialize_app(cred)
    except FileNotFoundError:
        print("Error: Firebase service account key file not found")
        exit(1)

db = firestore.client()

def check_migration_status():
    """移行状況を確認"""
    
    print("🔍 Firestore移行状況確認")
    print("=" * 60)
    
    try:
        # 旧コレクション（episodes）の件数確認
        episodes_ref = db.collection('episodes')
        episodes_count = len(list(episodes_ref.limit(1).stream()))
        if episodes_count > 0:
            # より正確なカウントを取得（最初の100件で確認）
            episodes_sample = list(episodes_ref.limit(100).stream())
            print(f"✅ 旧コレクション 'episodes': 存在（少なくとも{len(episodes_sample)}件）")
        else:
            print("❌ 旧コレクション 'episodes': 空またはアクセス不可")
        
        # 新コレクション（episodes_v2）の件数確認
        episodes_v2_ref = db.collection('episodes_v2')
        episodes_v2_docs = list(episodes_v2_ref.limit(10).stream())
        
        if len(episodes_v2_docs) > 0:
            print(f"✅ 新コレクション 'episodes_v2': 既に存在（データあり）")
            
            # サンプルデータ表示
            print("\n📋 episodes_v2 サンプルデータ（最初の3件）:")
            print("-" * 60)
            
            for i, doc in enumerate(episodes_v2_docs[:3], 1):
                data = doc.to_dict()
                print(f"\n【{i}】 ID: {doc.id}")
                print(f"  person_name_display: {data.get('person_name_display', 'N/A')}")
                print(f"  episode_title: {data.get('episode_title', 'N/A')}")
                print(f"  age: {data.get('age', 'N/A')}歳")
                print(f"  episode_type: {data.get('episode_type', 'N/A')}")
                print(f"  name_recognition: {data.get('name_recognition', 'N/A')}/100")
                
                # 新フィールドの確認
                if 'episode_hash' in data:
                    print(f"  ✅ episode_hash: {data['episode_hash'][:16]}...")
                if 'person_id' in data:
                    print(f"  ✅ person_id: {data['person_id']}")
            
            print("\n" + "=" * 60)
            print("📊 移行状況:")
            print("✅ episodes_v2コレクションは既に移行済みです")
            print(f"✅ 少なくとも{len(episodes_v2_docs)}件のデータが確認されました")
            
            return True
            
        else:
            print("⚠️ 新コレクション 'episodes_v2': 空または未作成")
            print("\n移行が必要です。execute_firestore_migration.pyを実行してください。")
            return False
            
    except Exception as e:
        print(f"❌ エラー: {str(e)}")
        return False

def get_collection_stats():
    """コレクションの統計情報を取得"""
    
    print("\n📊 コレクション統計情報")
    print("=" * 60)
    
    try:
        # episodes_v2の詳細統計
        episodes_v2_ref = db.collection('episodes_v2')
        
        # フィールド統計
        sample_docs = list(episodes_v2_ref.limit(100).stream())
        
        if sample_docs:
            field_stats = {}
            person_matched = 0
            person_unmatched = 0
            
            for doc in sample_docs:
                data = doc.to_dict()
                
                # person_idのマッチング確認
                if data.get('person_id', '').startswith('P_UNKNOWN'):
                    person_unmatched += 1
                else:
                    person_matched += 1
                
                # フィールドの存在確認
                for field in ['episode_hash', 'person_id', 'name_recognition', 'episode_type', 'era']:
                    if field in data and data[field]:
                        field_stats[field] = field_stats.get(field, 0) + 1
            
            print(f"サンプル数: {len(sample_docs)}件")
            print(f"人物マッチ: {person_matched}件 ({person_matched*100//len(sample_docs)}%)")
            print(f"人物不明: {person_unmatched}件 ({person_unmatched*100//len(sample_docs)}%)")
            
            print("\n新フィールド充実度:")
            for field, count in field_stats.items():
                percentage = count * 100 // len(sample_docs)
                print(f"  - {field}: {count}/{len(sample_docs)} ({percentage}%)")
        
    except Exception as e:
        print(f"統計取得エラー: {str(e)}")

if __name__ == "__main__":
    print("🔄 Firestore Episodes 移行状況確認")
    print("=" * 60)
    
    # 移行状況確認
    is_migrated = check_migration_status()
    
    if is_migrated:
        # 統計情報表示
        get_collection_stats()
        
        print("\n✨ 移行済み確認完了！")
        print("Firebaseコンソールで確認:")
        print("https://console.firebase.google.com/u/0/project/final-hourglass-claude/firestore/databases/-default-/data/~2Fepisodes_v2")
    else:
        print("\n⚠️ 移行が必要です")