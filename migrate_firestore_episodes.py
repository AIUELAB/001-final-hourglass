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
                        'name_recognition': row.get('name_recognition', 50),
                        'nationality': row.get('nationality', '不明'),
                        'occupation': row.get('occupation', '不明'),
                        'birth_year': row.get('birth_year', None)
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

def convert_episode_type(category, event_type=None):
    """エピソードタイプを判定"""
    if event_type:
        if '転機' in str(event_type):
            return '転機'
        elif '死' in str(event_type):
            return '悲劇'
    
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
    
    return '逸話'

def migrate_episode(old_episode, person_dict):
    """既存エピソードを新スキーマに変換"""
    
    # 人物情報を取得
    person_name = old_episode.get('person_name', '')
    person_name_display = old_episode.get('person_name_display', person_name)
    
    # 人物DBから情報取得
    person_info = person_dict.get(person_name_display) or person_dict.get(person_name) or {}
    
    # 新スキーマのエピソード
    new_episode = {
        # 識別情報
        'episode_id': old_episode.get('episode_id', f"EP_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
        'person_id': person_info.get('person_id', f"P_UNKNOWN_{person_name[:10]}"),
        'episode_hash': '',  # 後で生成
        
        # 人物情報
        'person_name': person_info.get('person_name', ''),
        'person_name_ja': old_episode.get('person_name_ja', person_name),
        'person_name_display': person_name_display,
        
        # エピソード本体
        'episode_title': old_episode.get('episode_title', '無題'),
        'episode_text': old_episode.get('episode', ''),
        'episode_year': None,  # 計算が必要
        'episode_date': None,  # 既存データになし
        'episode_type': convert_episode_type(
            old_episode.get('category'),
            old_episode.get('event_type')
        ),
        'age': old_episode.get('age', None),
        'age_months': old_episode.get('age_months', 0),
        
        # 分類情報
        'category': old_episode.get('category', 'その他'),
        'nationality': person_info.get('nationality', '不明'),
        'occupation': person_info.get('occupation', '不明'),
        'era': '不明',  # 後で計算
        
        # 品質指標
        'name_recognition': person_info.get('name_recognition', 50),
        'accuracy_score': old_episode.get('accuracy', 3) if old_episode.get('accuracy') else 3,
        'impact_score': old_episode.get('emotional_impact', 3) if old_episode.get('emotional_impact') else 3,
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
            'birth_year': person_info.get('birth_year', None)
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

def perform_migration(limit=None, dry_run=True):
    """Firestoreエピソードの移行を実行"""
    
    print("\n🚀 Firestore Episodes 移行開始")
    print("=" * 60)
    
    # 人物データベース読み込み
    person_dict = load_person_database()
    
    try:
        # 既存エピソードを取得
        episodes_ref = db.collection('episodes')
        if limit:
            episodes_query = episodes_ref.limit(limit)
        else:
            episodes_query = episodes_ref
        
        episodes = episodes_query.stream()
        
        migrated_episodes = []
        migration_stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'person_matched': 0,
            'person_unmatched': 0
        }
        
        for episode_doc in episodes:
            migration_stats['total'] += 1
            old_data = episode_doc.to_dict()
            old_data['_doc_id'] = episode_doc.id
            
            try:
                # 新スキーマに変換
                new_data = migrate_episode(old_data, person_dict)
                migrated_episodes.append(new_data)
                migration_stats['success'] += 1
                
                # 人物マッチング確認
                if new_data['person_id'].startswith('P_UNKNOWN'):
                    migration_stats['person_unmatched'] += 1
                else:
                    migration_stats['person_matched'] += 1
                
                # dry_runでなければFirestoreを更新
                if not dry_run:
                    # 新しいコレクションに保存（既存を保持）
                    new_doc_ref = db.collection('episodes_v2').document(episode_doc.id)
                    new_doc_ref.set(new_data)
                
            except Exception as e:
                print(f"❌ 移行エラー ({episode_doc.id}): {e}")
                migration_stats['failed'] += 1
        
        # 結果を表示
        print("\n📊 移行結果:")
        print("-" * 60)
        print(f"総エピソード数: {migration_stats['total']}")
        print(f"成功: {migration_stats['success']}")
        print(f"失敗: {migration_stats['failed']}")
        print(f"人物マッチ: {migration_stats['person_matched']}")
        print(f"人物不明: {migration_stats['person_unmatched']}")
        
        # CSVに保存
        if migrated_episodes:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_file = f"migrated_episodes_{timestamp}.csv"
            df = pd.DataFrame(migrated_episodes)
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            print(f"\n✅ 移行データ保存: {csv_file}")
        
        # dry_runの場合は警告
        if dry_run:
            print("\n⚠️ DRY RUNモード: Firestoreは更新されていません")
            print("実際に移行する場合は dry_run=False を設定してください")
        
        return migrated_episodes
        
    except Exception as e:
        print(f"❌ 移行処理エラー: {e}")
        return []

def show_migration_sample():
    """移行サンプルを表示"""
    
    print("\n📝 移行サンプル（最初の3件）")
    print("=" * 60)
    
    migrated = perform_migration(limit=3, dry_run=True)
    
    for i, episode in enumerate(migrated[:3], 1):
        print(f"\n【サンプル {i}】")
        print(f"person_name_display: {episode['person_name_display']}")
        print(f"episode_title: {episode['episode_title']}")
        print(f"age: {episode['age']}歳 / {episode['age_months']}ヶ月")
        print(f"episode_type: {episode['episode_type']}")
        print(f"name_recognition: {episode['name_recognition']}/100")
        print(f"person_id: {episode['person_id']}")

if __name__ == "__main__":
    print("🔄 Firestore Episodes スキーマ移行ツール")
    print("=" * 60)
    
    # まずサンプル表示
    show_migration_sample()
    
    print("\n" + "=" * 60)
    print("📋 移行オプション:")
    print("1. dry_run=True で全件テスト（Firestore更新なし）")
    print("2. dry_run=False で実際に移行（episodes_v2コレクションに保存）")
    print("\n現在: DRY RUNモードで実行")
    
    # 全件をDRY RUNで実行
    # perform_migration(limit=None, dry_run=True)
    
    # 実際に移行する場合はコメントアウトを外す
    # perform_migration(limit=None, dry_run=False)