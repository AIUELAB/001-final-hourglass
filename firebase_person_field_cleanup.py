from src.secure_config import config
#!/usr/bin/env python3
"""
Firebase person関連フィールドの整理
- person_short → person_name_short への変換（26件）
- person_name: 原語表記として整理
- person_name_ja: 日本語名
- person_name_short: 表示用短縮名
"""

import json
import time
from datetime import datetime
from typing import Dict, List, Optional

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

class PersonFieldCleaner:
    """Person関連フィールド整理クラス"""
    
    def __init__(self):
        self.processed_count = 0
        self.updated_count = 0
        self.person_short_count = 0
        self.backup_data = []
        self.update_log = []
        
    def backup_episodes(self) -> str:
        """
        全エピソードをバックアップ
        
        Returns:
            バックアップファイル名
        """
        print("\n=== バックアップ作成中 ===")
        
        episodes_ref = db.collection('episodes')
        episodes = episodes_ref.stream()
        
        for doc in episodes:
            doc_data = doc.to_dict()
            doc_data['_document_id'] = doc.id
            self.backup_data.append(doc_data)
        
        # バックアップファイルに保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'person_field_backup_{timestamp}.json'
        
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(self.backup_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ バックアップ完了: {backup_filename}")
        print(f"   保存件数: {len(self.backup_data)}件")
        
        return backup_filename
    
    def analyze_structure(self) -> Dict:
        """現在のperson関連フィールド構造を分析"""
        print("\n=== 現在のperson関連フィールド分析 ===")
        
        stats = {
            'total': 0,
            'has_person': 0,
            'has_person_short': 0,
            'has_person_name': 0,
            'has_person_name_ja': 0,
            'has_person_name_short': 0,
            'has_person_name_en': 0,
            'person_short_values': []
        }
        
        for doc_data in self.backup_data:
            stats['total'] += 1
            
            # 各フィールドの存在確認
            if 'person' in doc_data:
                stats['has_person'] += 1
            
            if 'person_short' in doc_data:
                stats['has_person_short'] += 1
                # person_shortの値をサンプル収集（最初の10件）
                if len(stats['person_short_values']) < 10:
                    stats['person_short_values'].append({
                        'id': doc_data.get('_document_id', 'unknown'),
                        'value': doc_data['person_short'],
                        'person_name': doc_data.get('person_name'),
                        'person_name_ja': doc_data.get('person_name_ja')
                    })
            
            if 'person_name' in doc_data:
                stats['has_person_name'] += 1
            if 'person_name_ja' in doc_data:
                stats['has_person_name_ja'] += 1
            if 'person_name_short' in doc_data:
                stats['has_person_name_short'] += 1
            if 'person_name_en' in doc_data:
                stats['has_person_name_en'] += 1
        
        print("📊 分析結果:")
        print(f"  総ドキュメント数: {stats['total']}")
        print(f"  personフィールド: {stats['has_person']}件")
        print(f"  person_shortフィールド: {stats['has_person_short']}件")
        print(f"  person_nameフィールド: {stats['has_person_name']}件")
        print(f"  person_name_jaフィールド: {stats['has_person_name_ja']}件")
        print(f"  person_name_shortフィールド: {stats['has_person_name_short']}件")
        print(f"  person_name_enフィールド: {stats['has_person_name_en']}件")
        
        if stats['person_short_values']:
            print("\n📝 person_shortのサンプル:")
            for sample in stats['person_short_values'][:5]:
                print(f"   ID: {sample['id'][:20]}...")
                print(f"      person_short: {sample['value']}")
                print(f"      person_name: {sample['person_name']}")
                print(f"      person_name_ja: {sample['person_name_ja']}")
        
        return stats
    
    def dry_run(self) -> List[Dict]:
        """
        ドライラン実行（実際の更新はしない）
        
        Returns:
            変換結果のリスト
        """
        print("\n=== ドライラン実行 ===")
        
        conversion_results = []
        person_short_samples = []
        
        for doc_data in self.backup_data:
            doc_id = doc_data.get('_document_id', 'unknown')
            changes = []
            
            # person_short → person_name_short
            if 'person_short' in doc_data:
                person_short_samples.append({
                    'doc_id': doc_id,
                    'person_short': doc_data['person_short'],
                    'existing_person_name_short': doc_data.get('person_name_short'),
                    'action': 'rename to person_name_short'
                })
                changes.append('person_short → person_name_short')
            
            # person → 適切なフィールドに振り分け
            if 'person' in doc_data:
                changes.append('person → 適切なフィールドに振り分け')
            
            if changes:
                conversion_results.append({
                    'doc_id': doc_id,
                    'changes': changes
                })
        
        # person_shortのサンプル表示
        if person_short_samples:
            print(f"\n📝 person_short → person_name_short 変換対象（全{len(person_short_samples)}件）:")
            for sample in person_short_samples[:5]:
                print(f"   ID: {sample['doc_id'][:20]}...")
                print(f"      値: {sample['person_short']}")
                if sample['existing_person_name_short']:
                    print(f"      ⚠️  既存のperson_name_short: {sample['existing_person_name_short']}")
        
        print("\n📊 ドライラン結果:")
        print(f"   更新対象: {len(conversion_results)}件")
        
        return conversion_results
    
    def clean_fields(self, batch_size: int = 500):
        """
        フィールドのクリーンアップを実行
        
        Args:
            batch_size: バッチサイズ（最大500）
        """
        print("\n=== フィールドクリーンアップ開始 ===")
        
        batch = db.batch()
        batch_count = 0
        
        for doc_data in self.backup_data:
            doc_id = doc_data.get('_document_id')
            if not doc_id:
                continue
            
            doc_ref = db.collection('episodes').document(doc_id)
            update_data = {}
            
            # person_short → person_name_short
            if 'person_short' in doc_data:
                # 既存のperson_name_shortがない場合のみ移行
                if 'person_name_short' not in doc_data:
                    update_data['person_name_short'] = doc_data['person_short']
                # person_shortフィールドを削除
                update_data['person_short'] = firestore.DELETE_FIELD
                self.person_short_count += 1
                
                # ログ記録
                self.update_log.append({
                    'doc_id': doc_id,
                    'action': 'person_short_to_person_name_short',
                    'old_value': doc_data['person_short'],
                    'new_field': 'person_name_short'
                })
            
            # person フィールドの処理（存在する場合）
            if 'person' in doc_data:
                person_value = doc_data['person']
                
                # 適切なフィールドに振り分け
                # 日本語が含まれる場合はperson_name_jaへ
                if person_value and self._contains_japanese(person_value):
                    if 'person_name_ja' not in doc_data:
                        update_data['person_name_ja'] = person_value
                # それ以外はperson_nameへ（原語表記として）
                else:
                    if 'person_name' not in doc_data:
                        update_data['person_name'] = person_value
                
                # personフィールドを削除
                update_data['person'] = firestore.DELETE_FIELD
                
                self.update_log.append({
                    'doc_id': doc_id,
                    'action': 'person_field_migration',
                    'old_value': person_value,
                    'migrated_to': 'person_name_ja' if self._contains_japanese(person_value) else 'person_name'
                })
            
            # バッチに追加
            if update_data:
                batch.update(doc_ref, update_data)
                batch_count += 1
                self.processed_count += 1
                self.updated_count += 1
                
                # バッチがいっぱいになったらコミット
                if batch_count >= batch_size:
                    batch.commit()
                    print(f"  処理済み: {self.processed_count}件")
                    batch = db.batch()
                    batch_count = 0
                    time.sleep(0.5)  # レート制限対策
        
        # 最後のバッチをコミット
        if batch_count > 0:
            batch.commit()
        
        print("\n✅ クリーンアップ完了")
        print(f"   処理件数: {self.processed_count}")
        print(f"   更新件数: {self.updated_count}")
        print(f"   person_short → person_name_short: {self.person_short_count}件")
        
        # ログファイル保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f'person_field_cleanup_log_{timestamp}.json'
        
        with open(log_filename, 'w', encoding='utf-8') as f:
            json.dump(self.update_log, f, ensure_ascii=False, indent=2)
        
        print(f"   ログファイル: {log_filename}")
    
    def _contains_japanese(self, text: str) -> bool:
        """
        テキストに日本語が含まれるかチェック
        
        Args:
            text: チェック対象のテキスト
            
        Returns:
            日本語が含まれる場合True
        """
        if not text:
            return False
        
        for char in text:
            # ひらがな、カタカナ、漢字のチェック
            if ('\u3040' <= char <= '\u309F' or  # ひらがな
                '\u30A0' <= char <= '\u30FF' or  # カタカナ
                '\u4E00' <= char <= '\u9FAF'):   # 漢字
                return True
        return False
    
    def verify_results(self):
        """処理結果を検証"""
        print("\n=== 結果検証 ===")
        
        # 更新後のデータを取得
        episodes_ref = db.collection('episodes')
        
        # person_shortフィールドが残っていないか確認
        remaining_person_short = 0
        sample_docs = []
        
        for doc in episodes_ref.limit(100).stream():
            data = doc.to_dict()
            if 'person_short' in data:
                remaining_person_short += 1
            
            if len(sample_docs) < 5:
                sample_docs.append((doc.id, data))
        
        print("📊 検証結果:")
        print(f"   残存person_shortフィールド: {remaining_person_short}件")
        
        print("\n📄 サンプル確認（最初の5件）:")
        for doc_id, data in sample_docs:
            print(f"\n   ID: {doc_id[:20]}...")
            print(f"      person_name: {data.get('person_name', 'なし')}")
            print(f"      person_name_ja: {data.get('person_name_ja', 'なし')}")
            print(f"      person_name_short: {data.get('person_name_short', 'なし')}")
            print(f"      person_short: {'削除済み' if 'person_short' not in data else data.get('person_short')}")
            print(f"      person: {'削除済み' if 'person' not in data else data.get('person')}")

def main():
    """メイン処理"""
    cleaner = PersonFieldCleaner()
    
    try:
        # 1. バックアップ作成
        cleaner.backup_episodes()
        
        # 2. 現在の構造を分析
        stats = cleaner.analyze_structure()
        
        # 3. ドライラン
        cleaner.dry_run()
        
        # 4. 実行確認
        if stats['has_person_short'] > 0 or stats['has_person'] > 0:
            print("\n⚠️  フィールドクリーンアップを開始します")
            print(f"   - {stats['has_person_short']}件のperson_short → person_name_short")
            print(f"   - {stats['has_person']}件のpersonフィールドを適切に振り分け")
            
            # ユーザー確認（自動実行）
            print("\n処理を開始しています...")
            
            # 5. フィールドクリーンアップ実行
            cleaner.clean_fields()
            
            # 6. 結果検証
            cleaner.verify_results()
        else:
            print("\n✅ クリーンアップ不要")
            print("   person_shortとpersonフィールドは存在しません")
            
            # person_nameフィールドの役割を確認
            if stats['has_person_name'] > 0:
                print(f"\n📌 person_nameフィールド: {stats['has_person_name']}件")
                print("   → 原語表記として維持")
    
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()