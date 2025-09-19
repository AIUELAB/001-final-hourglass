from src.secure_config import config
#!/usr/bin/env python3
"""
Firebaseエピソードフィールドの整理
age_years, age_displayフィールドから数値を抽出してageフィールドに統合
"""

import json
import re
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

class FirebaseFieldCleaner:
    """Firebaseフィールド整理クラス"""
    
    def __init__(self):
        self.processed_count = 0
        self.success_count = 0
        self.error_count = 0
        self.skip_count = 0
        self.backup_data = []
        self.update_log = []
        
    def extract_age_number(self, value) -> Optional[int]:
        """
        様々な形式から年齢の数値を抽出
        
        Args:
            value: 年齢を含む可能性のある値
            
        Returns:
            抽出された年齢の数値、抽出できない場合はNone
        """
        # すでに数値の場合
        if isinstance(value, (int, float)):
            return int(value)
        
        # 文字列の場合
        if isinstance(value, str):
            # 数値を探す（"26歳"、"26歳の時"、"晩年の72歳"など）
            match = re.search(r'(\d+)', value)
            if match:
                age = int(match.group(1))
                # 妥当な年齢範囲かチェック（0-150歳）
                if 0 <= age <= 150:
                    return age
        
        return None
    
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
            doc_data['_document_id'] = doc.id  # ドキュメントIDも保存
            self.backup_data.append(doc_data)
        
        # バックアップファイルに保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'episodes_backup_{timestamp}.json'
        
        with open(backup_filename, 'w', encoding='utf-8') as f:
            json.dump(self.backup_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ バックアップ完了: {backup_filename}")
        print(f"   保存件数: {len(self.backup_data)}件")
        
        return backup_filename
    
    def analyze_current_structure(self) -> Dict:
        """現在のデータ構造を分析"""
        print("\n=== 現在のデータ構造分析 ===")
        
        stats = {
            'total': 0,
            'has_age': 0,
            'has_age_years': 0,
            'has_age_display': 0,
            'has_all_three': 0,
            'has_none': 0,
            'age_extractable': 0
        }
        
        for doc_data in self.backup_data:
            stats['total'] += 1
            
            has_age = 'age' in doc_data and doc_data['age'] is not None
            has_age_years = 'age_years' in doc_data and doc_data['age_years']
            has_age_display = 'age_display' in doc_data and doc_data['age_display']
            
            if has_age:
                stats['has_age'] += 1
            if has_age_years:
                stats['has_age_years'] += 1
            if has_age_display:
                stats['has_age_display'] += 1
            
            if has_age and has_age_years and has_age_display:
                stats['has_all_three'] += 1
            elif not has_age and not has_age_years and not has_age_display:
                stats['has_none'] += 1
            
            # 年齢が抽出可能かチェック
            if not has_age:
                age_value = None
                if has_age_years:
                    age_value = self.extract_age_number(doc_data['age_years'])
                if age_value is None and has_age_display:
                    age_value = self.extract_age_number(doc_data['age_display'])
                
                if age_value is not None:
                    stats['age_extractable'] += 1
        
        print("📊 分析結果:")
        print(f"  総ドキュメント数: {stats['total']}")
        print(f"  ageフィールドあり: {stats['has_age']}")
        print(f"  age_yearsフィールドあり: {stats['has_age_years']}")
        print(f"  age_displayフィールドあり: {stats['has_age_display']}")
        print(f"  3つ全てあり: {stats['has_all_three']}")
        print(f"  全てなし: {stats['has_none']}")
        print(f"  年齢抽出可能（ageなし）: {stats['age_extractable']}")
        
        return stats
    
    def dry_run(self) -> List[Dict]:
        """
        ドライラン実行（実際の更新はしない）
        
        Returns:
            変換結果のリスト
        """
        print("\n=== ドライラン実行 ===")
        
        conversion_results = []
        
        for doc_data in self.backup_data[:10]:  # 最初の10件だけサンプル表示
            doc_id = doc_data.get('_document_id', 'unknown')
            
            original_age = doc_data.get('age')
            age_years = doc_data.get('age_years')
            age_display = doc_data.get('age_display')
            
            # 新しいage値を決定
            new_age = original_age
            source = "original"
            
            if original_age is None or not isinstance(original_age, (int, float)):
                # age_yearsから抽出を試みる
                extracted = self.extract_age_number(age_years)
                if extracted is not None:
                    new_age = extracted
                    source = "age_years"
                else:
                    # age_displayから抽出を試みる
                    extracted = self.extract_age_number(age_display)
                    if extracted is not None:
                        new_age = extracted
                        source = "age_display"
            
            result = {
                'doc_id': doc_id,
                'original_age': original_age,
                'age_years': age_years,
                'age_display': age_display,
                'new_age': new_age,
                'source': source,
                'will_update': new_age != original_age
            }
            
            conversion_results.append(result)
            
            if result['will_update']:
                print(f"\n📝 ID: {doc_id[:20]}...")
                print(f"   元のage: {original_age}")
                print(f"   age_years: {age_years}")
                print(f"   age_display: {age_display}")
                print(f"   → 新しいage: {new_age} (from {source})")
        
        # 統計
        update_count = sum(1 for r in conversion_results if r['will_update'])
        print("\n📊 ドライラン結果（サンプル10件）:")
        print(f"   更新対象: {update_count}件")
        print(f"   変更なし: {len(conversion_results) - update_count}件")
        
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
            
            # 現在の値を取得
            original_age = doc_data.get('age')
            age_years = doc_data.get('age_years')
            age_display = doc_data.get('age_display')
            
            # 新しいage値を決定
            new_age = original_age
            update_needed = False
            
            if original_age is None or not isinstance(original_age, (int, float)):
                # age_yearsから抽出
                extracted = self.extract_age_number(age_years)
                if extracted is not None:
                    new_age = extracted
                    update_needed = True
                else:
                    # age_displayから抽出
                    extracted = self.extract_age_number(age_display)
                    if extracted is not None:
                        new_age = extracted
                        update_needed = True
            
            # 更新データを作成
            update_data = {}
            
            if new_age is not None:
                update_data['age'] = new_age
            
            # age_yearsとage_displayを削除
            if 'age_years' in doc_data:
                update_data['age_years'] = firestore.DELETE_FIELD
            if 'age_display' in doc_data:
                update_data['age_display'] = firestore.DELETE_FIELD
            
            # バッチに追加
            if update_data:
                batch.update(doc_ref, update_data)
                batch_count += 1
                self.processed_count += 1
                
                # ログ記録
                self.update_log.append({
                    'doc_id': doc_id,
                    'original_age': original_age,
                    'new_age': new_age,
                    'updated': update_needed
                })
                
                if update_needed:
                    self.success_count += 1
            else:
                self.skip_count += 1
            
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
        print(f"   更新件数: {self.success_count}")
        print(f"   スキップ: {self.skip_count}")
        
        # ログファイル保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        log_filename = f'field_cleanup_log_{timestamp}.json'
        
        with open(log_filename, 'w', encoding='utf-8') as f:
            json.dump(self.update_log, f, ensure_ascii=False, indent=2)
        
        print(f"   ログファイル: {log_filename}")
    
    def verify_results(self):
        """処理結果を検証"""
        print("\n=== 結果検証 ===")
        
        # 更新後のデータを取得
        episodes_ref = db.collection('episodes')
        episodes = episodes_ref.limit(10).stream()
        
        print("サンプル確認（最初の5件）:")
        count = 0
        for doc in episodes:
            if count >= 5:
                break
            
            data = doc.to_dict()
            print(f"\n📄 ID: {doc.id[:20]}...")
            print(f"   age: {data.get('age', 'なし')}")
            print(f"   age_years: {'削除済み' if 'age_years' not in data else data.get('age_years')}")
            print(f"   age_display: {'削除済み' if 'age_display' not in data else data.get('age_display')}")
            count += 1

def main():
    """メイン処理"""
    cleaner = FirebaseFieldCleaner()
    
    try:
        # 1. バックアップ作成
        cleaner.backup_episodes()
        
        # 2. 現在の構造を分析
        stats = cleaner.analyze_current_structure()
        
        # 3. ドライラン
        print("\n=== ドライラン実行（自動） ===")
        cleaner.dry_run()
        
        # 4. 自動実行判定
        # age_yearsまたはage_displayフィールドがある場合のみ実行
        if stats['has_age_years'] > 0 or stats['has_age_display'] > 0:
            print("\n⚠️  フィールドクリーンアップを開始します")
            print(f"   - {stats['has_age_years']}件のage_yearsフィールドを削除")
            print(f"   - {stats['has_age_display']}件のage_displayフィールドを削除")
            print("   - ageフィールドはそのまま保持（すでに全件に存在）")
            
            # 5. フィールドクリーンアップ実行
            cleaner.clean_fields()
            
            # 6. 結果検証
            cleaner.verify_results()
        else:
            print("\n✅ クリーンアップ不要")
            print("   age_yearsとage_displayフィールドは存在しません")
    
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()