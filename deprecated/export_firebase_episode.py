from src.secure_config import config
#!/usr/bin/env python3
"""
特定のFirestoreエピソードをCSV出力
"""

import csv
import json
from datetime import datetime
from pathlib import Path

import firebase_admin
from firebase_admin import credentials, firestore

# Firebase初期化
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(config.firebase_credentials_path)
        firebase_admin.initialize_app(cred)
    except FileNotFoundError:
        print("Error: Firebase service account key file not found")
        print("Firebaseコンソールからサービスアカウントキーをダウンロードしてください")
        exit(1)

db = firestore.client()

def export_episode_to_csv(episode_id: str = "EOF < "):
    """特定のエピソードをCSVに出力"""
    
    print(f"🔍 エピソード '{episode_id}' を取得中...")
    
    try:
        # 特定のエピソードを取得
        episode_ref = db.collection('episodes').document(episode_id)
        episode_doc = episode_ref.get()
        
        if not episode_doc.exists:
            print(f"❌ エピソード '{episode_id}' が見つかりません")
            return None
        
        # エピソードデータを取得
        episode_data = episode_doc.to_dict()
        
        # タイムスタンプ付きファイル名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"firebase_episode_{episode_id.replace(' ', '_').replace('<', 'LT').replace('>', 'GT')}_{timestamp}.csv"
        json_filename = f"firebase_episode_{episode_id.replace(' ', '_').replace('<', 'LT').replace('>', 'GT')}_{timestamp}.json"
        
        # JSON形式で保存（バックアップ用）
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(episode_data, f, ensure_ascii=False, indent=2, default=str)
        print(f"✅ JSON保存: {json_filename}")
        
        # CSVに出力
        with open(csv_filename, 'w', encoding='utf-8-sig', newline='') as f:
            # フィールド名を動的に取得
            fieldnames = list(episode_data.keys())
            
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerow(episode_data)
        
        print(f"✅ CSV保存: {csv_filename}")
        
        # データの詳細を表示
        print("\n📋 エピソード詳細:")
        print("=" * 60)
        for key, value in episode_data.items():
            # 長いテキストは短縮表示
            if isinstance(value, str) and len(value) > 100:
                display_value = value[:97] + "..."
            else:
                display_value = value
            print(f"  {key}: {display_value}")
        print("=" * 60)
        
        # 統計情報
        print("\n📊 統計情報:")
        print(f"  - フィールド数: {len(fieldnames)}")
        print(f"  - エピソードID: {episode_id}")
        
        # 主要フィールドの確認
        key_fields = ['person_name', 'age', 'year', 'month', 'day', 'content', 'title']
        print("\n🔑 主要フィールド:")
        for field in key_fields:
            if field in episode_data:
                value = episode_data[field]
                if isinstance(value, str) and len(value) > 50:
                    value = value[:47] + "..."
                print(f"  - {field}: {value}")
        
        return csv_filename
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        print("\n考えられる原因:")
        print("1. Firebase認証情報が正しくない")
        print("2. エピソードIDが正しくない")
        print("3. ネットワーク接続の問題")
        return None

def export_all_episodes_to_csv():
    """全エピソードをCSVに出力（オプション）"""
    
    print("📚 全エピソードを取得中...")
    
    try:
        episodes_ref = db.collection('episodes')
        episodes = episodes_ref.stream()
        
        # データを収集
        all_episodes = []
        fieldnames_set = set()
        
        for episode_doc in episodes:
            data = episode_doc.to_dict()
            data['_id'] = episode_doc.id  # ドキュメントIDを追加
            all_episodes.append(data)
            fieldnames_set.update(data.keys())
        
        if not all_episodes:
            print("❌ エピソードが見つかりません")
            return None
        
        # タイムスタンプ付きファイル名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filename = f"firebase_all_episodes_{timestamp}.csv"
        
        # CSVに出力
        fieldnames = sorted(list(fieldnames_set))
        with open(csv_filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for episode in all_episodes:
                # 欠損フィールドを空文字で埋める
                row = {field: episode.get(field, '') for field in fieldnames}
                writer.writerows([row])
        
        print(f"✅ 全エピソードをCSVに保存: {csv_filename}")
        print(f"  - 総エピソード数: {len(all_episodes)}")
        print(f"  - フィールド数: {len(fieldnames)}")
        
        return csv_filename
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {str(e)}")
        return None

def main():
    """メイン実行"""
    print("🚀 Firebase エピソード CSV エクスポーター")
    print("=" * 60)
    
    # 特定のエピソード "EOF < " を出力
    result = export_episode_to_csv("EOF < ")
    
    if result:
        print(f"\n✨ エクスポート完了: {result}")
        print("\nCSVファイルはExcelで直接開けます（UTF-8 BOM付き）")
    else:
        print("\n⚠️ エクスポートに失敗しました")
    
    # 全エピソードも出力するか確認（コメントアウトで無効化）
    # print("\n全エピソードもエクスポートしますか？")
    # export_all_episodes_to_csv()

if __name__ == "__main__":
    main()