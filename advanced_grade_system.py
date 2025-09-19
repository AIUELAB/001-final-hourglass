#!/usr/bin/env python3
"""
高度なGradeシステム（A-Z 26段階）
日本人の認知度と世界的有名度に基づく詳細な評価
"""

import json
import re
from datetime import datetime
from typing import Dict, Optional, Tuple


class AdvancedGradeSystem:
    """A-Z 26段階の詳細なGrade評価システム"""
    
    def __init__(self):
        # 超有名人リスト（Grade A-E）
        self.world_famous = {
            'A': [  # 誰でも知ってる超有名人
                'Einstein', 'アインシュタイン', 'Beethoven', 'ベートーヴェン',
                'Shakespeare', 'シェイクスピア', 'Leonardo da Vinci', 'レオナルド・ダ・ヴィンチ',
                'Picasso', 'ピカソ', 'Newton', 'ニュートン', 'Darwin', 'ダーウィン'
            ],
            'B': [  # ほぼ誰でも知ってる
                'Mozart', 'モーツァルト', 'Bach', 'バッハ', 'Van Gogh', 'ゴッホ',
                'Chopin', 'ショパン', 'Columbus', 'コロンブス', 'Napoleon', 'ナポレオン',
                'Edison', 'エジソン', 'Galileo', 'ガリレオ'
            ],
            'C': [  # 大半が知ってる
                'Wagner', 'ワーグナー', 'Brahms', 'ブラームス', 'Schubert', 'シューベルト',
                'Vivaldi', 'ヴィヴァルディ', 'Tchaikovsky', 'チャイコフスキー',
                'Rembrandt', 'レンブラント', 'Michelangelo', 'ミケランジェロ'
            ],
            'D': [  # 教養人なら知ってる
                'Liszt', 'リスト', 'Debussy', 'ドビュッシー', 'Ravel', 'ラヴェル',
                'Verdi', 'ヴェルディ', 'Handel', 'ヘンデル', 'Stravinsky', 'ストラヴィンスキー'
            ],
            'E': [  # 分野に興味があれば知ってる
                'Rachmaninoff', 'ラフマニノフ', 'Prokofiev', 'プロコフィエフ',
                'Mahler', 'マーラー', 'Shostakovich', 'ショスタコーヴィチ'
            ]
        }
        
        # 日本人有名人（Grade F-J）
        self.japanese_famous = {
            'F': ['織田信長', '豊臣秀吉', '徳川家康', '坂本龍馬', '西郷隆盛'],
            'G': ['源頼朝', '平清盛', '武田信玄', '上杉謙信', '伊達政宗'],
            'H': ['聖徳太子', '藤原道長', '菅原道真', '空海', '最澄'],
            'I': ['夏目漱石', '芥川龍之介', '太宰治', '川端康成', '三島由紀夫'],
            'J': ['黒澤明', '宮崎駿', '手塚治虫', '北野武', '小津安二郎']
        }
        
        # 職業別の基本Grade
        self.occupation_base_grades = {
            'composer': 'K',
            'scientist': 'L',
            'philosopher': 'M',
            'writer': 'N',
            'artist': 'O',
            'politician': 'P',
            'athlete': 'Q',
            'actor': 'R',
            'singer': 'R',
            '俳優': 'R',
            '歌手': 'R',
            '芸人': 'S',
            'unknown': 'U'
        }
        
        # 犯罪者・要注意人物のキーワード
        self.criminal_keywords = [
            'criminal', 'terrorist', 'murderer', 'killer', 'dictator',
            '犯罪', 'テロリスト', '殺人', '独裁者'
        ]
        
        self.stats = {
            'total': 0,
            'grade_distribution': {},
            'criminals_flagged': 0,
            'japanese_priority': 0
        }
    
    def calculate_fame_score(self, person: Dict) -> int:
        """有名度スコアを計算（0-100）"""
        score = 0
        
        name = person.get('preferred_display_name', person.get('name', ''))
        occupation = person.get('occupation', '').lower()
        nationality = person.get('nationality', '').lower()
        wikidata_id = person.get('wikidata_id', '')
        birth_date = person.get('birth_date', '')
        
        # Wikidata IDの数値が小さいほど有名（早期登録）
        if wikidata_id and wikidata_id.startswith('Q'):
            try:
                qid_num = int(wikidata_id[1:])
                if qid_num < 1000:
                    score += 30
                elif qid_num < 10000:
                    score += 20
                elif qid_num < 100000:
                    score += 10
                elif qid_num < 1000000:
                    score += 5
            except:
                pass
        
        # 職業による加点
        if 'composer' in occupation:
            score += 15
        elif 'scientist' in occupation:
            score += 12
        elif 'philosopher' in occupation:
            score += 10
        elif any(word in occupation for word in ['emperor', 'king', 'queen']):
            score += 20
        elif any(word in occupation for word in ['俳優', 'actor', '歌手', 'singer']):
            score += 8
        
        # 国籍による加点（日本人優先）
        if 'japan' in nationality or '日本' in nationality:
            score += 25
        elif any(word in nationality for word in ['united states', 'america', 'british', 'france', 'germany']):
            score += 10
        
        # 時代による加点（歴史的人物）
        if birth_date:
            try:
                year = int(birth_date.split('/')[0] if '/' in birth_date else birth_date.split('-')[0])
                if year < 0:  # 紀元前
                    score += 15
                elif year < 1000:  # 古代・中世
                    score += 12
                elif year < 1500:  # 中世
                    score += 10
                elif year < 1800:  # 近世
                    score += 8
                elif year < 1900:  # 近代
                    score += 5
            except:
                pass
        
        return min(score, 100)
    
    def check_criminal_flag(self, person: Dict) -> bool:
        """犯罪者・要注意人物かチェック"""
        occupation = person.get('occupation', '').lower()
        description = person.get('description', '').lower()
        
        for keyword in self.criminal_keywords:
            if keyword in occupation or keyword in description:
                return True
        
        # 特定の名前（独裁者等）
        name = person.get('preferred_display_name', person.get('name', ''))
        if any(criminal in name for criminal in ['Hitler', 'ヒトラー', 'Stalin', 'スターリン', 'Pol Pot', 'ポル・ポト']):
            return True
        
        return False
    
    def determine_grade(self, person: Dict) -> Tuple[str, bool, int]:
        """詳細なGradeを決定"""
        name = person.get('preferred_display_name', person.get('name', ''))
        occupation = person.get('occupation', '').lower()
        
        # 犯罪者チェック
        is_criminal = self.check_criminal_flag(person)
        if is_criminal:
            self.stats['criminals_flagged'] += 1
            # 犯罪者はGradeなし、フラグのみ
            return 'N/A', True, 0
        
        # 超有名人チェック（A-E）
        for grade, names in self.world_famous.items():
            for famous_name in names:
                if famous_name.lower() in name.lower() or name.lower() in famous_name.lower():
                    return grade, False, 95
        
        # 日本の有名人チェック（F-J）
        for grade, names in self.japanese_famous.items():
            for famous_name in names:
                if famous_name in name or name in famous_name:
                    self.stats['japanese_priority'] += 1
                    return grade, False, 85
        
        # 有名度スコアで判定
        fame_score = self.calculate_fame_score(person)
        
        # スコアに基づくGrade割り当て
        if fame_score >= 80:
            return 'K', False, fame_score
        elif fame_score >= 70:
            return 'L', False, fame_score
        elif fame_score >= 60:
            return 'M', False, fame_score
        elif fame_score >= 50:
            return 'N', False, fame_score
        elif fame_score >= 40:
            return 'O', False, fame_score
        elif fame_score >= 35:
            return 'P', False, fame_score
        elif fame_score >= 30:
            return 'Q', False, fame_score
        elif fame_score >= 25:
            return 'R', False, fame_score
        elif fame_score >= 20:
            return 'S', False, fame_score
        elif fame_score >= 15:
            return 'T', False, fame_score
        elif fame_score >= 10:
            return 'U', False, fame_score
        elif fame_score >= 5:
            return 'V', False, fame_score
        elif fame_score >= 3:
            return 'W', False, fame_score
        elif fame_score >= 1:
            return 'X', False, fame_score
        else:
            return 'Y', False, fame_score
    
    def apply_advanced_grades(self, input_file: str = None) -> Tuple[str, Dict]:
        """高度なGradeシステムを適用"""
        
        if not input_file:
            input_file = 'intelligent_fixed_20250824_182313.json'
        
        print("🎯 高度なGradeシステム（A-Z）適用開始")
        print(f"  入力: {input_file}")
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['total'] = len(data)
        
        # Grade適用
        grade_examples = {chr(i): [] for i in range(65, 91)}  # A-Z
        
        for key, value in data.items():
            if isinstance(value, dict):
                # 新Grade計算
                new_grade, is_criminal, fame_score = self.determine_grade(value)
                
                # フィールド更新
                value['advanced_grade'] = new_grade
                value['fame_score'] = fame_score
                value['is_criminal'] = is_criminal
                
                # 古いGradeは参考として保持
                value['old_grade'] = value.get('grade', 'Unknown')
                
                # 統計収集
                if new_grade != 'N/A':
                    if new_grade not in self.stats['grade_distribution']:
                        self.stats['grade_distribution'][new_grade] = 0
                    self.stats['grade_distribution'][new_grade] += 1
                    
                    # サンプル収集（各Gradeで最初の3件）
                    if len(grade_examples[new_grade]) < 3:
                        grade_examples[new_grade].append({
                            'name': value.get('preferred_display_name', ''),
                            'occupation': value.get('occupation', ''),
                            'score': fame_score
                        })
        
        # 結果保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"advanced_grade_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # レポート出力
        print("\n📊 Grade分布（A-Z）:")
        for grade in sorted(self.stats['grade_distribution'].keys()):
            count = self.stats['grade_distribution'][grade]
            percentage = count / self.stats['total'] * 100
            print(f"  Grade {grade}: {count:,}件 ({percentage:.1f}%)")
            
            # サンプル表示
            if grade_examples[grade]:
                for ex in grade_examples[grade][:2]:
                    print(f"    例: {ex['name']} (スコア: {ex['score']})")
        
        print("\n📈 統計:")
        print(f"  総レコード: {self.stats['total']:,}")
        print(f"  犯罪者フラグ: {self.stats['criminals_flagged']:,}")
        print(f"  日本人優先適用: {self.stats['japanese_priority']:,}")
        
        print(f"\n✅ 出力: {output_file}")
        
        return output_file, self.stats


def main():
    """メイン実行"""
    grade_system = AdvancedGradeSystem()
    output_file, stats = grade_system.apply_advanced_grades()
    
    print("\n🏆 高度なGradeシステム適用完了")
    print("  A-E: 世界的超有名人")
    print("  F-J: 日本の有名人")
    print("  K-O: 専門分野で有名")
    print("  P-T: 一般認知度低")
    print("  U-Y: ほぼ無名")
    print("  犯罪者: 別フラグで管理")


if __name__ == "__main__":
    main()