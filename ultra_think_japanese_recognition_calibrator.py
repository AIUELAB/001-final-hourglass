#!/usr/bin/env python3
"""
日本人向け知名度（name_recognition）精度向上システム
Ultra Think Japanese Recognition Calibrator

このシステムは日本人の視点・文化的背景・言語的ニーズに最適化された
高精度な知名度評価を実現します。
"""

import json
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import math

class JapaneseRecognitionCalibrator:
    """日本人向け知名度較正システム"""
    
    def __init__(self):
        """初期化"""
        # 4層評価システムの重み付け
        self.weights = {
            'education_impact': 0.35,    # 教育認知度 35%
            'media_presence': 0.30,       # メディア露出 30%
            'social_relevance': 0.20,     # SNS言及 20%
            'global_score': 0.15          # グローバル認知度 15%
        }
        
        # カテゴリ別基準値
        self.category_baselines = {
            '歴史上の人物': {
                'range': (40, 100),
                'adjustments': {
                    '教科書必修': (90, 100),  # 織田信長、徳川家康など
                    '教科書選択': (70, 89),   # 小松左京、野口英世など
                    '専門知識': (40, 69)      # 特定分野の専門家
                }
            },
            'エンタメ': {
                'range': (30, 100),
                'adjustments': {
                    'テレビ常連': (80, 100),  # SMAP、嵐など
                    'メディア露出中': (60, 79),
                    'ニッチ層人気': (30, 59)
                }
            },
            'スポーツ': {
                'range': (30, 100),
                'adjustments': {
                    '国民的スター': (85, 100),  # 大谷翔平、イチローなど
                    'プロ選手': (50, 84),
                    '専門競技': (30, 49)
                }
            },
            '学術・科学': {
                'range': (30, 90),
                'adjustments': {
                    'ノーベル賞': (70, 90),
                    '著名研究者': (50, 69),
                    '専門家': (30, 49)
                }
            },
            'ビジネス': {
                'range': (30, 85),
                'adjustments': {
                    '大企業創業者': (70, 85),  # 松下幸之助、本田宗一郎など
                    '有名経営者': (50, 69),
                    '業界著名人': (30, 49)
                }
            },
            'その他': {
                'range': (30, 80),
                'adjustments': {
                    '高': (60, 80),
                    '中': (45, 59),
                    '低': (30, 44)
                }
            }
        }
        
        # 特別な人物の固定スコア
        self.special_persons = {
            # 歴史上の人物（教科書必修レベル）
            '織田信長': 98, '豊臣秀吉': 97, '徳川家康': 98,
            '坂本龍馬': 94, '西郷隆盛': 92, '福沢諭吉': 90,
            '聖徳太子': 95, '源頼朝': 90, '平清盛': 88,
            
            # 国民的エンタメ
            'SMAP': 95, '嵐': 93, '木村拓哉': 94,
            'ビートたけし': 92, '明石家さんま': 93, 'タモリ': 91,
            
            # 国民的スポーツ選手
            '大谷翔平': 97, 'イチロー': 95, '羽生結弦': 93,
            '松井秀喜': 88, '長嶋茂雄': 90, '王貞治': 91,
            
            # 世界的日本人
            '黒澤明': 88, '宮崎駿': 92, '村上春樹': 85,
            '安藤忠雄': 75, '草間彌生': 78, '坂本龍一': 82
        }
        
    def calibrate_score(self, person_data: Dict) -> int:
        """知名度スコアを較正する"""
        
        # 特別な人物の場合は固定スコアを返す
        if person_data.get('person_name_ja') in self.special_persons:
            return self.special_persons[person_data['person_name_ja']]
        
        # recognition_metadataから既存のスコアを取得
        metadata = self._parse_metadata(person_data.get('recognition_metadata', '{}'))
        
        if metadata and all(key in metadata for key in ['japan_score', 'global_score']):
            # メタデータがある場合は重み付け計算
            score = self._calculate_weighted_score(metadata, person_data)
        else:
            # メタデータがない場合は推定
            score = self._estimate_score(person_data)
        
        # カテゴリ別調整
        score = self._apply_category_adjustment(score, person_data)
        
        # 1-100の範囲に収める
        return max(1, min(100, int(score)))
    
    def _parse_metadata(self, metadata_str: str) -> Optional[Dict]:
        """メタデータ文字列をパース"""
        if not metadata_str or metadata_str == '{}':
            return None
        
        try:
            # シングルクォートをダブルクォートに変換
            metadata_str = metadata_str.replace("'", '"')
            return json.loads(metadata_str)
        except:
            return None
    
    def _calculate_weighted_score(self, metadata: Dict, person_data: Dict) -> float:
        """重み付けスコアを計算"""
        # 日本での知名度を重視
        japan_score = float(metadata.get('japan_score', 50))
        global_score = float(metadata.get('global_score', 30))
        
        # 日本人の場合は日本スコアをより重視
        if person_data.get('nationality') == '日本':
            base_score = japan_score * 0.8 + global_score * 0.2
        else:
            # 外国人の場合はバランス型
            base_score = japan_score * 0.6 + global_score * 0.4
        
        # その他のメタデータがあれば考慮
        if 'education_impact' in metadata:
            education = float(metadata['education_impact'])
            media = float(metadata.get('media_presence', 50))
            social = float(metadata.get('social_relevance', 30))
            
            # 詳細な重み付け計算
            detailed_score = (
                education * self.weights['education_impact'] +
                media * self.weights['media_presence'] +
                social * self.weights['social_relevance'] +
                global_score * self.weights['global_score']
            )
            
            # 基本スコアと詳細スコアの平均
            return (base_score + detailed_score) / 2
        
        return base_score
    
    def _estimate_score(self, person_data: Dict) -> float:
        """メタデータがない場合のスコア推定"""
        category = person_data.get('category', 'その他')
        occupation = person_data.get('occupation', '')
        nationality = person_data.get('nationality', '')
        
        # カテゴリ別基本スコア
        if category in self.category_baselines:
            min_score, max_score = self.category_baselines[category]['range']
            base_score = (min_score + max_score) / 2
        else:
            base_score = 50
        
        # 職業による調整
        if 'ノーベル' in occupation or 'Nobel' in occupation:
            base_score += 20
        elif '大統領' in occupation or '首相' in occupation:
            base_score += 15
        elif 'オリンピック' in occupation:
            base_score += 10
        
        # 日本人補正
        if nationality == '日本':
            base_score *= 1.1
        
        return base_score
    
    def _apply_category_adjustment(self, score: float, person_data: Dict) -> float:
        """カテゴリ別の調整を適用"""
        category = person_data.get('category', 'その他')
        
        if category not in self.category_baselines:
            return score
        
        # カテゴリの範囲内に収める
        min_range, max_range = self.category_baselines[category]['range']
        
        # 特定の条件による調整
        occupation = person_data.get('occupation', '').lower()
        name_ja = person_data.get('person_name_ja', '')
        
        # 職業による微調整
        if category == '歴史上の人物':
            if any(word in name_ja for word in ['天皇', '将軍', '大名']):
                score = max(score, 85)
        elif category == 'エンタメ':
            if any(word in occupation for word in ['歌手', '俳優', 'タレント']):
                score = max(score, 60)
        elif category == 'スポーツ':
            if any(word in occupation for word in ['金メダル', 'world champion']):
                score = max(score, 75)
        
        # 範囲内に収める
        return max(min_range, min(max_range, score))
    
    def calibrate_batch(self, persons: List[Dict]) -> List[Dict]:
        """バッチ処理で複数人の較正を実行"""
        calibrated_persons = []
        
        for person in persons:
            original_score = person.get('name_recognition', 50)
            
            # スコアを較正
            calibrated_score = self.calibrate_score(person)
            
            # 更新
            person['name_recognition'] = calibrated_score
            
            # メタデータを更新
            metadata = self._parse_metadata(person.get('recognition_metadata', '{}'))
            if not metadata:
                metadata = {}
            
            metadata['calibrated_at'] = datetime.now().isoformat()
            metadata['original_score'] = original_score
            metadata['calibrated_score'] = calibrated_score
            
            person['recognition_metadata'] = json.dumps(metadata, ensure_ascii=False)
            
            calibrated_persons.append(person)
        
        return calibrated_persons
    
    def generate_report(self, original_data: List[Dict], calibrated_data: List[Dict]) -> Dict:
        """較正レポートを生成"""
        report = {
            'total_persons': len(calibrated_data),
            'calibration_date': datetime.now().isoformat(),
            'changes': {
                'improved': 0,
                'decreased': 0,
                'unchanged': 0
            },
            'score_distribution': {
                '90-100': 0,
                '80-89': 0,
                '70-79': 0,
                '60-69': 0,
                '50-59': 0,
                '40-49': 0,
                '30-39': 0,
                '1-29': 0
            },
            'category_averages': {},
            'examples': []
        }
        
        # スコア変化の分析
        for orig, cal in zip(original_data, calibrated_data):
            orig_score = int(orig.get('name_recognition', 50))
            cal_score = int(cal.get('name_recognition', 50))
            
            if cal_score > orig_score:
                report['changes']['improved'] += 1
            elif cal_score < orig_score:
                report['changes']['decreased'] += 1
            else:
                report['changes']['unchanged'] += 1
            
            # スコア分布
            if cal_score >= 90:
                report['score_distribution']['90-100'] += 1
            elif cal_score >= 80:
                report['score_distribution']['80-89'] += 1
            elif cal_score >= 70:
                report['score_distribution']['70-79'] += 1
            elif cal_score >= 60:
                report['score_distribution']['60-69'] += 1
            elif cal_score >= 50:
                report['score_distribution']['50-59'] += 1
            elif cal_score >= 40:
                report['score_distribution']['40-49'] += 1
            elif cal_score >= 30:
                report['score_distribution']['30-39'] += 1
            else:
                report['score_distribution']['1-29'] += 1
            
            # 変化の大きい例を収集
            if abs(cal_score - orig_score) > 20 and len(report['examples']) < 10:
                report['examples'].append({
                    'name': cal.get('person_name_ja', cal.get('person_name')),
                    'category': cal.get('category'),
                    'original': orig_score,
                    'calibrated': cal_score,
                    'change': cal_score - orig_score
                })
        
        # カテゴリ別平均
        category_scores = {}
        for person in calibrated_data:
            category = person.get('category', 'その他')
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(int(person.get('name_recognition', 50)))
        
        for category, scores in category_scores.items():
            report['category_averages'][category] = {
                'average': sum(scores) / len(scores),
                'count': len(scores),
                'max': max(scores),
                'min': min(scores)
            }
        
        return report

if __name__ == "__main__":
    # テスト実行
    calibrator = JapaneseRecognitionCalibrator()
    
    # サンプルデータでテスト
    test_person = {
        'person_name': 'Nobunaga Oda',
        'person_name_ja': '織田信長',
        'category': '歴史上の人物',
        'nationality': '日本',
        'occupation': '戦国大名',
        'name_recognition': 50,
        'recognition_metadata': '{}'
    }
    
    score = calibrator.calibrate_score(test_person)
    print(f"織田信長の較正スコア: {score}")