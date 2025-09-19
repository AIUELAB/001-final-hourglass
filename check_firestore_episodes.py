from src.secure_config import config
#!/usr/bin/env python3
"""
Firestoreのepisodesコレクションから有名人データを確認
"""

import json
from collections import defaultdict

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

def analyze_episodes():
    """episodesコレクションを分析"""
    
    try:
        # episodesコレクションから全ドキュメントを取得
        episodes_ref = db.collection('episodes')
        episodes = episodes_ref.stream()
        
        # 統計情報を収集
        total_episodes = 0
        person_count = defaultdict(int)
        age_count = defaultdict(int)
        person_age_combinations = set()
        
        for episode_doc in episodes:
            total_episodes += 1
            data = episode_doc.to_dict()
            
            # person_nameフィールドとageフィールドを確認
            person = data.get('person_name', data.get('person', 'Unknown'))
            age = data.get('age', -1)
            
            person_count[person] += 1
            age_count[age] += 1
            person_age_combinations.add((person, age))
        
        # 結果を表示
        print("=" * 60)
        print("Firestore Episodes コレクション分析結果")
        print("=" * 60)
        print("\n📊 基本統計:")
        print(f"  - 総エピソード数: {total_episodes:,}")
        print(f"  - 有名人の人数: {len(person_count)}")
        print(f"  - カバーされている年齢数: {len(age_count)}")
        print(f"  - ユニークな(人物, 年齢)の組み合わせ: {len(person_age_combinations)}")
        
        print("\n👥 有名人リスト (上位20名):")
        sorted_persons = sorted(person_count.items(), key=lambda x: x[1], reverse=True)
        for i, (person, count) in enumerate(sorted_persons[:20], 1):
            print(f"  {i:2}. {person}: {count}個のエピソード")
        
        if len(sorted_persons) > 20:
            print(f"  ... 他 {len(sorted_persons) - 20} 名")
        
        print("\n📈 年齢分布:")
        min_age = min(age_count.keys()) if age_count else 0
        max_age = max(age_count.keys()) if age_count else 0
        print(f"  - 最小年齢: {min_age}歳")
        print(f"  - 最大年齢: {max_age}歳")
        
        # 必要数との比較
        print("\n🎯 目標との比較:")
        required_episodes = 102 * 365  # 37,230個
        print(f"  - 必要なエピソード数: {required_episodes:,}")
        print(f"  - 現在のエピソード数: {total_episodes:,}")
        print(f"  - 不足数: {max(0, required_episodes - total_episodes):,}")
        
        if total_episodes > 0:
            coverage = (total_episodes / required_episodes) * 100
            print(f"  - カバー率: {coverage:.2f}%")
        
        # 一人あたり平均3個使用する場合の必要人数
        required_persons = required_episodes // 3
        print(f"\n  - 必要な有名人数 (3個/人): {required_persons:,}")
        print(f"  - 現在の有名人数: {len(person_count)}")
        print(f"  - 不足人数: {max(0, required_persons - len(person_count)):,}")
        
    except Exception as e:
        print(f"エラーが発生しました: {str(e)}")
        print("\n考えられる原因:")
        print("1. Firebase認証情報が正しくない")
        print("2. Firestoreのコレクション名が異なる")
        print("3. ネットワーク接続の問題")

if __name__ == "__main__":
    analyze_episodes()