#!/usr/bin/env python3
"""
Ultra Think復元システム - 較正済みname_recognition追加
品質第一原則に基づく処理
"""

import csv
import json
from datetime import datetime
import io


class JapaneseRecognitionCalibrator:
    """日本の文脈に最適化した知名度較正システム"""
    
    def __init__(self):
        self.weights = {
            'education': 0.35,    # 教科書・教育での扱い
            'media': 0.30,        # メディア露出
            'sns': 0.20,          # SNS影響力
            'global': 0.15        # 国際的認知度
        }
    
    def calibrate(self, person):
        """個人の知名度を較正"""
        
        # 基本情報取得
        name = person.get('person_name', '')
        name_ja = person.get('person_name_ja', '')
        category = person.get('category', '') or person.get('main_category', '')
        occupation = person.get('occupation', '')
        nationality = person.get('nationality', '日本')
        grade = person.get('grade', 'B')
        
        # グレードベースの初期スコア
        grade_scores = {
            'S': 85, 'A': 75, 'B': 65, 'C': 55, 'D': 45
        }
        score = grade_scores.get(grade, 50)
        
        # カテゴリベース
        if category == '歴史的偉人' or '歴史' in category:
            score = self._calibrate_historical(person)
        elif category in ['スポーツ', 'エンタメ', 'エンターテインメント']:
            score = self._calibrate_entertainment(person)
        elif category in ['学術・科学', '科学', '学術']:
            score = self._calibrate_academic(person)
        elif category in ['ビジネス', '経営']:
            score = self._calibrate_business(person)
        elif category in ['文化・芸術', '国際', '文化', '芸術']:
            score = self._calibrate_cultural(person)
        else:
            score = self._calibrate_general(person)
        
        # 日本人補正
        if nationality == '日本' or 'Japan' in nationality:
            score = min(100, score + 5)
        
        # 範囲制限
        return max(1, min(100, round(score)))
    
    def _calibrate_historical(self, person):
        """歴史的偉人の較正"""
        name_display = person.get('person_name_display', '')
        name = person.get('person_name', '')
        
        # 教科書掲載レベル
        top_tier = ['織田信長', '豊臣秀吉', '徳川家康', '坂本龍馬', 
                   'エジソン', 'アインシュタイン', 'ニュートン', 'ダーウィン',
                   'キュリー夫人', 'ガリレオ', 'コロンブス', 'ナポレオン']
        
        if name_display in top_tier:
            return 95
        
        # 英語名でもチェック
        top_names = ['Edison', 'Einstein', 'Newton', 'Darwin', 'Columbus',
                    'Napoleon', 'Shakespeare', 'Lincoln', 'Washington']
        
        if any(n in name for n in top_names):
            return 95
        
        # 歴史上の重要人物
        educational = person.get('educational_value', 0)
        historical = person.get('historical_impact', 0)
        
        try:
            edu_score = float(educational) if educational else 5
            hist_score = float(historical) if historical else 5
            return 50 + (edu_score * 3) + (hist_score * 2)
        except:
            return 75
    
    def _calibrate_entertainment(self, person):
        """エンタメ・スポーツの較正"""
        name = person.get('person_name', '')
        name_ja = person.get('person_name_ja', '')
        name_display = person.get('person_name_display', '')
        
        # トップアスリート
        top_athletes = ['大谷翔平', 'イチロー', '松井秀喜', '中田英寿',
                       '羽生結弦', '錦織圭', '内村航平', '吉田沙保里']
        
        if any(athlete in name_ja or athlete in name_display for athlete in top_athletes):
            return 90
        
        # エンタメトップ
        top_entertainers = ['明石家さんま', 'ビートたけし', '松本人志',
                          '新垣結衣', '米津玄師', '星野源', '菅田将暉']
        
        if any(ent in name_ja or ent in name_display for ent in top_entertainers):
            return 85
        
        # フォロワー数で判定
        followers = person.get('followers', '')
        if followers:
            try:
                follower_count = int(followers.replace(',', '').replace('万', '0000'))
                if follower_count > 1000000:
                    return 80
                elif follower_count > 100000:
                    return 70
            except:
                pass
        
        return 60
    
    def _calibrate_academic(self, person):
        """学術・科学の較正"""
        global_recognition = person.get('global_recognition', 0)
        
        try:
            global_score = float(global_recognition) if global_recognition else 3
            return 40 + (global_score * 6)
        except:
            return 55
    
    def _calibrate_business(self, person):
        """ビジネスの較正"""
        name = person.get('person_name', '')
        name_ja = person.get('person_name_ja', '')
        name_display = person.get('person_name_display', '')
        
        # 世界的起業家
        if any(n in name for n in ['Jobs', 'Gates', 'Bezos', 'Musk', 'Zuckerberg']):
            return 90
        
        # 日本の著名経営者
        japanese_leaders = ['孫正義', '柳井正', '三木谷浩史', '稲盛和夫', '本田宗一郎']
        if any(n in name_ja or n in name_display for n in japanese_leaders):
            return 80
        
        return 55
    
    def _calibrate_cultural(self, person):
        """文化・芸術の較正"""
        cultural = person.get('cultural_significance', 0)
        
        try:
            cult_score = float(cultural) if cultural else 3
            return 45 + (cult_score * 5)
        except:
            return 55
    
    def _calibrate_general(self, person):
        """その他の較正"""
        # デフォルトスコア
        return 50


def add_calibrated_recognition():
    """較正済みname_recognition値を追加"""
    
    print("=" * 60)
    print("🔧 Ultra Think データベース復元")
    print("name_recognition較正追加処理")
    print("=" * 60)
    
    input_file = 'ultra_think_RESTORED_BASE.csv'
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_CALIBRATED_{timestamp}.csv'
    
    # 較正器初期化
    calibrator = JapaneseRecognitionCalibrator()
    
    # データ読み込み
    persons = []
    with open(input_file, 'r', encoding='utf-8') as f:
        content = f.read()
        if content.startswith('\ufeff'):
            content = content[1:]
        
        reader = csv.DictReader(io.StringIO(content))
        
        for i, row in enumerate(reader):
            # name_recognition追加
            row['name_recognition'] = calibrator.calibrate(row)
            persons.append(row)
            
            # デバッグ出力（最初の5件）
            if i < 5:
                print(f"  Debug: {row['person_name_display']} - category:{row.get('category')} - grade:{row.get('grade')} -> {row['name_recognition']}点")
            
            # 進捗表示
            if (i + 1) % 1000 == 0:
                print(f"  処理中: {i + 1}件完了")
    
    print(f"\n✅ 較正完了: {len(persons)}人")
    
    # 出力フィールド定義（24フィールド）
    output_fields = [
        'person_id', 'episode_id', 'person_name', 'person_name_ja', 'person_name_display',
        'birth_year', 'death_year', 'nationality', 'occupation', 'category',
        'known_for_jp', 'known_for_en', 'wikipedia_link_jp', 'wikipedia_link_en',
        'description_jp', 'description_en', 'popularity_score', 'name_recognition',
        'educational_value', 'historical_impact', 'cultural_significance', 
        'global_recognition', 'created_at', 'source'
    ]
    
    # エピソード形式に変換
    episodes = []
    for i, person in enumerate(persons):
        episode = {
            'person_id': f"P{i+1:05d}",
            'episode_id': f"E{i+1:05d}",
            'person_name': person.get('person_name', ''),
            'person_name_ja': person.get('person_name_ja', ''),
            'person_name_display': person.get('person_name_display', ''),
            'birth_year': person.get('birth_year', ''),
            'death_year': '',
            'nationality': person.get('nationality', ''),
            'occupation': person.get('occupation', ''),
            'category': person.get('category', ''),
            'known_for_jp': '',
            'known_for_en': '',
            'wikipedia_link_jp': '',
            'wikipedia_link_en': '',
            'description_jp': person.get('description', ''),
            'description_en': '',
            'popularity_score': person.get('grade', 'A'),
            'name_recognition': person['name_recognition'],
            'educational_value': person.get('educational_value', ''),
            'historical_impact': person.get('historical_impact', ''),
            'cultural_significance': person.get('cultural_significance', ''),
            'global_recognition': person.get('global_recognition', ''),
            'created_at': datetime.now().isoformat(),
            'source': 'ultra_think_restored'
        }
        episodes.append(episode)
    
    # CSV保存
    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=output_fields)
        writer.writeheader()
        writer.writerows(episodes)
    
    print(f"✅ 保存完了: {output_file}")
    
    # 統計レポート
    print("\n📊 較正結果統計:")
    
    # name_recognition分布
    recognition_ranges = {
        '90-100': 0, '80-89': 0, '70-79': 0,
        '60-69': 0, '50-59': 0, '40-49': 0,
        '30-39': 0, '20-29': 0, '10-19': 0, '1-9': 0
    }
    
    for episode in episodes:
        score = episode['name_recognition']
        if score >= 90:
            recognition_ranges['90-100'] += 1
        elif score >= 80:
            recognition_ranges['80-89'] += 1
        elif score >= 70:
            recognition_ranges['70-79'] += 1
        elif score >= 60:
            recognition_ranges['60-69'] += 1
        elif score >= 50:
            recognition_ranges['50-59'] += 1
        elif score >= 40:
            recognition_ranges['40-49'] += 1
        elif score >= 30:
            recognition_ranges['30-39'] += 1
        elif score >= 20:
            recognition_ranges['20-29'] += 1
        elif score >= 10:
            recognition_ranges['10-19'] += 1
        else:
            recognition_ranges['1-9'] += 1
    
    for range_name, count in recognition_ranges.items():
        if count > 0:
            print(f"  {range_name}: {count}人")
    
    # 品質チェック
    print("\n🔍 品質確認:")
    
    sample_count = 5
    print(f"  サンプル（最初の{sample_count}件）:")
    for episode in episodes[:sample_count]:
        print(f"    {episode['person_name_display']}: {episode['name_recognition']}点")
    
    return output_file


if __name__ == "__main__":
    add_calibrated_recognition()