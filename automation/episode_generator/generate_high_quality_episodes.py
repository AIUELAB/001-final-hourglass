#!/usr/bin/env python3
"""
高品質エピソード生成システム
歴史的事実データベースを使用して具体的で感動的なエピソードを生成
"""

import json
import os
import random
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional

# プロジェクトパスを追加
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import firebase_admin
from episode_quality_system import EpisodeQualityEvaluator
from firebase_admin import credentials, firestore
from historical_facts_database import ExtendedHistoricalFacts

# Firebase初期化
if not firebase_admin._apps:
    cred = credentials.Certificate('keys/firebase-service-account.json')
    firebase_admin.initialize_app(cred)

db = firestore.client()

class HighQualityEpisodeGenerator:
    """高品質エピソード生成器"""
    
    def __init__(self):
        self.evaluator = EpisodeQualityEvaluator()
        self.facts_db = ExtendedHistoricalFacts()
        self.generated_count = 0
        self.high_quality_count = 0
        self.rejected_count = 0
        
    def _get_fact_for_age(self, person_name: str, age: int) -> Optional[str]:
        """特定の年齢の事実を取得"""
        person_data = self.facts_db.facts.get(person_name)
        if not person_data:
            return None
        
        facts = person_data.get('facts', [])
        # 完全一致する年齢の事実を探す
        for fact_age, fact_text in facts:
            if fact_age == age:
                return fact_text
        
        # 近い年齢の事実を探す（±2歳の範囲）
        for fact_age, fact_text in facts:
            if abs(fact_age - age) <= 2:
                return fact_text
        
        return None
    
    def generate_episode(self, person_name: str, age: int) -> Optional[Dict]:
        """
        特定の人物と年齢に対して高品質エピソードを生成
        
        Args:
            person_name: 人物名
            age: 年齢
            
        Returns:
            エピソードデータ（品質基準を満たさない場合はNone）
        """
        # 歴史的事実を取得
        fact = self._get_fact_for_age(person_name, age)
        
        if not fact:
            # 事実データがない場合は生成しない
            return None
        
        # エピソードテンプレートを選択
        templates = self._get_episode_templates(age)
        template = random.choice(templates)
        
        # エピソードを生成
        episode_text = template.format(
            age=age,
            person=person_name,
            fact=fact,
            year=self._calculate_year(person_name, age)
        )
        
        # 品質評価
        evaluation = self.evaluator.evaluate_episode(episode_text, age)
        
        # 品質基準（スコア60以上）を満たさない場合はリトライ
        if evaluation['quality_score'] < 60:
            # 別のテンプレートで再試行
            for _ in range(3):  # 最大3回試行
                template = random.choice(templates)
                episode_text = template.format(
                    age=age,
                    person=person_name,
                    fact=fact,
                    year=self._calculate_year(person_name, age)
                )
                evaluation = self.evaluator.evaluate_episode(episode_text, age)
                if evaluation['quality_score'] >= 60:
                    break
            else:
                self.rejected_count += 1
                return None
        
        self.high_quality_count += 1
        
        # エピソードデータを構築
        episode_data = {
            'person_name': person_name,
            'episode_age': age,
            'episode': episode_text,
            'episode_type': self._determine_episode_type(fact),
            'quality_score': evaluation['quality_score'],
            'is_specific': evaluation['is_specific'],
            'has_facts': evaluation['has_facts'],
            'emotional_impact': evaluation['emotional_impact'],
            'display_priority': evaluation['display_priority'],
            'created_at': datetime.now().isoformat(),
            'generation_method': 'high_quality_facts_based',
            'data_source': 'historical_facts_database'
        }
        
        # 短い表示名を追加
        episode_data['person_short'] = self._get_short_name(person_name)
        
        return episode_data
    
    def _get_episode_templates(self, age: int) -> List[str]:
        """年齢に応じたエピソードテンプレートを返す"""
        if age < 20:
            return [
                "{age}歳。{person}は{fact}",
                "{year}年、{age}歳の{person}。{fact}",
                "{age}歳の時、{person}は{fact}この経験が後の人生を決定づけた。"
            ]
        elif age < 40:
            return [
                "{age}歳の{person}。{fact}",
                "{year}年、{age}歳。{fact}これが{person}の転機となった。",
                "{age}歳で{fact}{person}の人生における重要な節目。"
            ]
        elif age < 60:
            return [
                "{age}歳。{person}は{fact}人生の集大成への第一歩。",
                "{year}年、{age}歳の{person}。{fact}",
                "{age}歳にして{fact}{person}の成熟期の到来。"
            ]
        else:
            return [
                "{age}歳の{person}。{fact}",
                "{year}年、{age}歳。{fact}晩年の{person}の偉業。",
                "{age}歳。{fact}{person}の生涯の集大成。"
            ]
    
    def _calculate_year(self, person_name: str, age: int) -> int:
        """人物の生年から特定の年齢時の年を計算"""
        person_data = self.facts_db.facts.get(person_name, {})
        birth_year = person_data.get('birth', 0)
        return birth_year + age if birth_year else 0
    
    def _determine_episode_type(self, fact: str) -> str:
        """事実の内容からエピソードタイプを判定"""
        if any(word in fact for word in ['発見', '発明', '開発', '研究']):
            return 'discovery'
        elif any(word in fact for word in ['戦い', '戦争', '勝利', '敗北']):
            return 'battle'
        elif any(word in fact for word in ['結婚', '出産', '死', '病']):
            return 'personal'
        elif any(word in fact for word in ['賞', '受賞', '表彰', 'ノーベル']):
            return 'achievement'
        elif any(word in fact for word in ['失敗', '挫折', '苦難', '困難']):
            return 'adversity'
        elif any(word in fact for word in ['創業', '設立', '起業']):
            return 'founding'
        else:
            return 'milestone'
    
    def _get_short_name(self, person_name: str) -> str:
        """長い名前を短縮"""
        # 西洋人名の場合
        if ' ' in person_name:
            parts = person_name.split()
            if len(parts) == 2:
                return parts[-1]  # 姓のみ
            else:
                return f"{parts[0]} {parts[-1]}"  # 名と姓
        
        # 日本人名の場合
        if len(person_name) > 4:
            # 「の」が含まれる古い名前
            if 'の' in person_name:
                return person_name.split('の')[-1]
            # 通常の長い名前は最初の3文字
            return person_name[:3]
        
        return person_name
    
    def generate_batch(self, batch_size: int = 100) -> List[Dict]:
        """バッチでエピソードを生成"""
        episodes = []
        persons = list(self.facts_db.facts.keys())
        
        print("\n=== 高品質エピソード生成開始 ===")
        print(f"対象人物: {len(persons)}人")
        print(f"目標生成数: {batch_size}件")
        print("品質基準: スコア60以上\n")
        
        attempts = 0
        while len(episodes) < batch_size and attempts < batch_size * 3:
            # ランダムに人物と年齢を選択
            person = random.choice(persons)
            person_data = self.facts_db.facts[person]
            
            # 事実がある年齢を優先的に選択
            fact_ages = [fact[0] for fact in person_data.get('facts', [])]
            if fact_ages and random.random() < 0.8:  # 80%の確率で事実がある年齢を選択
                age = random.choice(fact_ages)
            else:
                # 生涯の範囲内でランダムに選択
                birth = person_data.get('birth', 1900)
                death = person_data.get('death', 2000)
                lifespan = death - birth
                age = random.randint(0, min(lifespan, 100))
            
            episode = self.generate_episode(person, age)
            if episode:
                episodes.append(episode)
                if len(episodes) % 10 == 0:
                    print(f"生成済み: {len(episodes)}/{batch_size} (品質合格率: {self.high_quality_count}/{self.high_quality_count + self.rejected_count})")
            
            attempts += 1
        
        print("\n=== 生成完了 ===")
        print(f"生成数: {len(episodes)}件")
        print(f"高品質: {self.high_quality_count}件")
        print(f"却下: {self.rejected_count}件")
        print(f"品質合格率: {self.high_quality_count / max(1, self.high_quality_count + self.rejected_count) * 100:.1f}%")
        
        return episodes
    
    def save_to_firebase(self, episodes: List[Dict], batch_size: int = 500):
        """Firebaseに保存"""
        print("\n=== Firebase保存開始 ===")
        
        batch = db.batch()
        batch_count = 0
        total_saved = 0
        
        for episode in episodes:
            # ドキュメントIDを生成
            doc_id = f"{episode['person_name']}_{episode['episode_age']}_{int(time.time() * 1000)}"
            doc_ref = db.collection('episodes').document(doc_id)
            
            batch.set(doc_ref, episode)
            batch_count += 1
            
            if batch_count >= batch_size:
                batch.commit()
                total_saved += batch_count
                print(f"保存済み: {total_saved}/{len(episodes)}")
                batch = db.batch()
                batch_count = 0
        
        # 最後のバッチをコミット
        if batch_count > 0:
            batch.commit()
            total_saved += batch_count
        
        print(f"Firebase保存完了: {total_saved}件")
        return total_saved
    
    def save_to_json(self, episodes: List[Dict], filename: str = None):
        """JSONファイルに保存"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'high_quality_episodes_{timestamp}.json'
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(episodes, f, ensure_ascii=False, indent=2)
        
        print(f"JSONファイル保存完了: {filename}")
        return filename

def main():
    """メイン処理"""
    generator = HighQualityEpisodeGenerator()
    
    # 100件の高品質エピソードを生成
    episodes = generator.generate_batch(batch_size=100)
    
    if episodes:
        # JSONに保存
        json_file = generator.save_to_json(episodes)
        
        # 自動的にFirebaseに保存
        print("\nFirebaseに保存中...")
        generator.save_to_firebase(episodes)
        
        # 品質分析
        print("\n=== 品質分析 ===")
        scores = [ep['quality_score'] for ep in episodes]
        print(f"平均品質スコア: {sum(scores)/len(scores):.1f}")
        print(f"最高スコア: {max(scores)}")
        print(f"最低スコア: {min(scores)}")
        
        # スコア分布
        score_dist = {
            '60-70': sum(1 for s in scores if 60 <= s < 70),
            '70-80': sum(1 for s in scores if 70 <= s < 80),
            '80-90': sum(1 for s in scores if 80 <= s < 90),
            '90-100': sum(1 for s in scores if 90 <= s <= 100)
        }
        print("\nスコア分布:")
        for range_key, count in score_dist.items():
            print(f"  {range_key}: {count}件 ({count/len(scores)*100:.1f}%)")
        
        # サンプル表示
        print("\n=== サンプルエピソード（上位3件）===")
        top_episodes = sorted(episodes, key=lambda x: x['quality_score'], reverse=True)[:3]
        for i, ep in enumerate(top_episodes, 1):
            print(f"\n{i}. {ep['person_name']} ({ep['episode_age']}歳) - スコア: {ep['quality_score']}")
            print(f"   {ep['episode']}")

if __name__ == "__main__":
    main()