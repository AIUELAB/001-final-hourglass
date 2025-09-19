import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import hashlib
import json
from datetime import datetime
import re

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

def load_person_database():
    """人物データベースを読み込み"""
    try:
        # 最新の人物DBを読み込み
        person_df = pd.read_csv('ultra_think_WITH_CRIMINALS_20250826_001012.csv', encoding='utf-8-sig')
        
        # 人物辞書を作成（高速検索用）
        person_dict = {}
        for idx, row in person_df.iterrows():
            # 複数のキーで検索できるように
            names = [
                row.get('person_name_ja', ''),
                row.get('person_name_display', ''),
                row.get('person_name', '')
            ]
            for name in names:
                if pd.notna(name) and name:
                    person_dict[str(name).strip()] = {
                        'person_id': f"P{str(idx+1).zfill(6)}",
                        'person_name': row.get('person_name', ''),
                        'person_name_ja': row.get('person_name_ja', ''),
                        'person_name_display': row.get('person_name_display', ''),
                        'name_recognition': int(row.get('name_recognition', 50)) if pd.notna(row.get('name_recognition')) else 50,
                        'nationality': row.get('nationality', '不明'),
                        'occupation': row.get('occupation', '不明'),
                        'birth_year': int(row.get('birth_year')) if pd.notna(row.get('birth_year')) else None
                    }
        
        print(f"✅ 人物データベース読み込み完了: {len(person_dict)}人")
        return person_dict
    except Exception as e:
        print(f"⚠️ 人物データベース読み込みエラー: {e}")
        return {}

def generate_episode_hash(person_id, episode_year, episode_title):
    """重複チェック用ハッシュ生成"""
    content = f"{person_id}_{episode_year}_{episode_title}"
    return hashlib.md5(content.encode()).hexdigest()

def determine_era(year):
    """年代から時代を判定"""
    if not year:
        return "不明"
    
    try:
        year = int(year)
        if year < 1600:
            return "戦国時代以前"
        elif year < 1868:
            return "江戸時代"
        elif year < 1912:
            return "明治時代"
        elif year < 1926:
            return "大正時代"
        elif year < 1989:
            return "昭和時代"
        elif year < 2019:
            return "平成時代"
        else:
            return "令和時代"
    except:
        return "不明"

def convert_episode_type(category, event_type=None):
    """エピソードタイプを判定"""
    if event_type:
        event_str = str(event_type).lower()
        if '転機' in event_str:
            return '転機'
        elif '死' in event_str or '病' in event_str:
            return '悲劇'
        elif '誕生' in event_str or '生' in event_str:
            return '誕生'
    
    if category:
        category_str = str(category).lower()
        if '科学' in category_str or '発明' in category_str:
            return '発見'
        elif 'スポーツ' in category_str:
            return '記録'
        elif '芸術' in category_str or '音楽' in category_str:
            return '芸術'
        elif '政治' in category_str:
            return '偉業'
        elif '文学' in category_str:
            return '創作'
    
    return '逸話'

def migrate_episode(old_episode, person_dict):
    """既存エピソードを新スキーマに変換"""
    
    # 人物情報を取得
    person_name = old_episode.get('person_name', '')
    person_name_display = old_episode.get('person_name_display', person_name)
    person_name_ja = old_episode.get('person_name_ja', person_name)
    
    # 人物DBから情報取得（複数の名前で試行）
    person_info = (
        person_dict.get(person_name_display) or 
        person_dict.get(person_name_ja) or 
        person_dict.get(person_name) or 
        {}
    )
    
    # 新スキーマのエピソード
    new_episode = {
        # 識別情報
        'episode_id': old_episode.get('episode_id', f"EP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
        'person_id': person_info.get('person_id', f"P_UNKNOWN_{hashlib.md5(person_name.encode()).hexdigest()[:8]}"),
        'episode_hash': '',  # 後で生成
        
        # 人物情報
        'person_name': person_info.get('person_name', ''),
        'person_name_ja': person_name_ja or person_name,
        'person_name_display': person_name_display or person_name_ja or person_name,
        
        # エピソード本体
        'episode_title': old_episode.get('episode_title', '無題のエピソード'),
        'episode_text': old_episode.get('episode', ''),
        'episode_year': None,  # 計算が必要
        'episode_date': None,  # 既存データになし
        'episode_type': convert_episode_type(
            old_episode.get('category'),
            old_episode.get('event_type')
        ),
        'age': int(old_episode.get('age')) if old_episode.get('age') else None,
        'age_months': int(old_episode.get('age_months')) if old_episode.get('age_months') else 0,
        
        # 分類情報
        'category': old_episode.get('category', 'その他'),
        'nationality': person_info.get('nationality', '不明'),
        'occupation': person_info.get('occupation', '不明'),
        'era': '不明',  # 後で計算
        
        # 品質指標
        'name_recognition': person_info.get('name_recognition', 50),
        'accuracy_score': int(old_episode.get('accuracy')) if old_episode.get('accuracy') else 3,
        'impact_score': int(old_episode.get('emotional_impact')) if old_episode.get('emotional_impact') else 3,
        'source': old_episode.get('source', 'AI生成'),
        
        # システム管理
        'created_at': old_episode.get('created_at', datetime.now().isoformat()),
        'is_published': True,
        
        # 拡張データ（既存の追加情報を保存）
        'extended_data': json.dumps({
            'original_id': old_episode.get('_doc_id', ''),
            'migration_info': old_episode.get('_migration', {}),
            'quality_score': old_episode.get('quality_score', 0),
            'generation_version': old_episode.get('generation_version', ''),
            'birth_year': person_info.get('birth_year', None),
            'migrated_at': datetime.now().isoformat()
        }, ensure_ascii=False)
    }
    
    # episode_yearを計算
    if person_info.get('birth_year') and new_episode['age']:
        new_episode['episode_year'] = person_info['birth_year'] + new_episode['age']
        new_episode['era'] = determine_era(new_episode['episode_year'])
    
    # episode_hashを生成
    new_episode['episode_hash'] = generate_episode_hash(
        new_episode['person_id'],
        new_episode['episode_year'] or 0,
        new_episode['episode_title']
    )
    
    return new_episode

def execute_full_migration():
    """全エピソードの本番移行を実行"""
    
    print("\n🚀 Firestore Episodes 本番移行開始")
    print("=" * 60)
    print("⚠️ 警告: episodes_v2コレクションに書き込みます")
    print("=" * 60)
    
    # 人物データベース読み込み
    person_dict = load_person_database()
    
    try:
        # 既存エピソードを取得
        episodes_ref = db.collection('episodes')
        episodes = episodes_ref.stream()
        
        migrated_episodes = []
        migration_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'person_matched': 0,
            'person_unmatched': 0,
            'skipped': 0
        }
        
        batch = db.batch()
        batch_count = 0
        max_batch_size = 500  # Firestoreのバッチ制限
        
        print("\n⏳ 移行処理中...")
        
        for episode_doc in episodes:
            migration_stats['total'] += 1
            
            # 進捗表示
            if migration_stats['total'] % 100 == 0:
                print(f"  処理中: {migration_stats['total']}件...")
            
            old_data = episode_doc.to_dict()
            old_data['_doc_id'] = episode_doc.id
            
            try:
                # 新スキーマに変換
                new_data = migrate_episode(old_data, person_dict)
                migrated_episodes.append(new_data)
                
                # 人物マッチング確認
                if new_data['person_id'].startswith('P_UNKNOWN'):
                    migration_stats['person_unmatched'] += 1
                else:
                    migration_stats['person_matched'] += 1
                
                # バッチに追加
                new_doc_ref = db.collection('episodes_v2').document(episode_doc.id)
                batch.set(new_doc_ref, new_data)
                batch_count += 1
                
                # バッチがいっぱいになったらコミット
                if batch_count >= max_batch_size:
                    batch.commit()
                    print(f"  ✅ {migration_stats['total']}件コミット完了")
                    batch = db.batch()
                    batch_count = 0
                
                migration_stats['success'] += 1
                
            except Exception as e:
                print(f"  ❌ 移行エラー ({episode_doc.id}): {e}")
                migration_stats['failed'] += 1
        
        # 残りのバッチをコミット
        if batch_count > 0:
            batch.commit()
            print(f"  ✅ 最終バッチ {batch_count}件コミット完了")
        
        # 結果を表示
        print("\n" + "=" * 60)
        print("📊 移行完了レポート")
        print("=" * 60)
        print(f"総エピソード数: {migration_stats['total']:,}件")
        print(f"✅ 成功: {migration_stats['success']:,}件")
        print(f"❌ 失敗: {migration_stats['failed']:,}件")
        print(f"👤 人物マッチ: {migration_stats['person_matched']:,}件")
        print(f"❓ 人物不明: {migration_stats['person_unmatched']:,}件")
        
        # CSVに保存（バックアップ）
        if migrated_episodes:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = f"migrated_episodes_final_{timestamp}.csv"
            df = pd.DataFrame(migrated_episodes)
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"\n📁 バックアップCSV: {csv_file}")
            
            # 統計情報も保存
            stats_file = f"migration_stats_{timestamp}.json"
            with open(stats_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'migration_stats': migration_stats,
                    'timestamp': timestamp,
                    'person_db_count': len(person_dict),
                    'new_schema_fields': 23
                }, f, ensure_ascii=False, indent=2)
            print(f"📊 統計レポート: {stats_file}")
        
        print("\n✨ 移行完了！")
        print(f"新コレクション: episodes_v2")
        print(f"旧コレクション: episodes（保持）")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 移行処理エラー: {e}")
        return False

if __name__ == "__main__":
    print("🔄 Firestore Episodes 本番移行実行")
    print("=" * 60)
    
    # 確認
    print("⚠️ これから本番移行を実行します")
    print("  - 対象: 全エピソード")
    print("  - 書込先: episodes_v2コレクション")
    print("  - 既存データ: episodesコレクション（保持）")
    print("=" * 60)
    
    # 本番移行実行
    success = execute_full_migration()
    
    if success:
        print("\n🎊 移行成功！")
        print("次のステップ:")
        print("1. Firebaseコンソールでepisodes_v2を確認")
        print("2. アプリケーションのコレクション参照を更新")
        print("3. 動作確認後、旧episodesコレクションの扱いを決定")
    else:
        print("\n⚠️ 移行に問題が発生しました")
        print("ログを確認してください")