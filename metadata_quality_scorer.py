#!/usr/bin/env python3
"""
メタデータ品質スコアリングシステム
Metadata Quality Scoring System

このシステムは、人物データのメタデータ品質を評価します。
フィールドの完全性、一貫性、信頼性を総合的にスコアリング。
"""

import pandas as pd
import json
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import logging
from dataclasses import dataclass

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class QualityResult:
    """品質評価結果"""
    person_id: str
    person_name: str
    person_name_display: str
    overall_quality_score: float
    completeness_score: float
    consistency_score: float
    reliability_score: float
    episode_quality_score: float
    placeholder_indicators: int
    recommendation: str
    issues: List[str]

class MetadataQualityScorer:
    """メタデータ品質スコアリングシステム"""
    
    def __init__(self):
        # 必須フィールド
        self.required_fields = [
            'person_id',
            'person_name',
            'person_name_display',
            'category',
            'nationality',
            'occupation'
        ]
        
        # 重要フィールド（あると品質向上）
        self.important_fields = [
            'person_name_ja',
            'birth_year',
            'name_recognition',
            'episode_text',
            'source'
        ]
        
        # プレースホルダーパターン
        self.placeholder_patterns = [
            # 明らかなテストデータ
            r'^Test\s*',
            r'^テスト',
            r'^Sample\s*',
            r'^Person\s*\d+',
            r'^User\s*\d+',
            r'^人物\d+',
            
            # 一般的な仮名
            r'^田中太郎',
            r'^山田花子',
            r'^佐藤太郎',
            r'^鈴木花子',
            r'^John\s*Doe',
            r'^Jane\s*Doe',
            
            # 番号付き名前
            r'^.*#\d+$',
            r'^.*_\d+$',
            r'^.*\(\d+\)$',
            
            # 不完全な名前
            r'^名前未設定',
            r'^Unknown',
            r'^不明$',
            r'^N/A$',
            r'^TBD$',
            r'^TODO',
            
            # 異常なパターン
            r'^[A-Z]{3,}\d+',  # AAA123のようなパターン
            r'^\d+$',           # 数字のみ
            r'^[^a-zA-Zぁ-んァ-ヶー一-龥]+$'  # 記号のみ
        ]
        
        # 信頼できるソース
        self.trusted_sources = [
            'Wikipedia',
            'Official',
            '公式',
            'Verified',
            '確認済み',
            'Database',
            'API'
        ]
        
        # 疑わしいソース
        self.suspicious_sources = [
            'AI生成',
            'Generated',
            'Auto',
            'Test',
            'Unknown',
            '不明',
            'Placeholder'
        ]
        
        # カテゴリの妥当性チェック
        self.valid_categories = [
            'エンターテイメント',
            'スポーツ',
            '歴史',
            '文学',
            '芸術',
            '音楽',
            '映画',
            '科学',
            '政治',
            'ビジネス',
            '教育',
            '架空のキャラクター',
            'その他'
        ]
        
        # 国籍の妥当性チェック
        self.valid_nationalities = [
            '日本', 'アメリカ', 'イギリス', 'フランス', 'ドイツ', 'イタリア',
            '中国', '韓国', 'インド', 'ロシア', 'カナダ', 'オーストラリア',
            'ブラジル', 'メキシコ', 'スペイン', 'オランダ', 'スウェーデン'
        ]
    
    def check_placeholder_indicators(self, record: Dict) -> int:
        """プレースホルダー指標のチェック"""
        indicators = 0
        
        # 名前フィールドのチェック
        name_fields = ['person_name', 'person_name_display', 'person_name_ja']
        for field in name_fields:
            value = str(record.get(field, ''))
            if value and value != 'nan':
                for pattern in self.placeholder_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        indicators += 2  # 名前のプレースホルダーは重要
                        break
        
        # 職業・国籍の不明チェック
        if str(record.get('occupation', '')).strip() in ['不明', 'Unknown', 'nan', '']:
            indicators += 1
        
        if str(record.get('nationality', '')).strip() in ['不明', 'Unknown', 'nan', '']:
            indicators += 1
        
        # ソースの疑わしさチェック
        source = str(record.get('source', ''))
        for suspicious in self.suspicious_sources:
            if suspicious in source:
                indicators += 1
                break
        
        # エピソードの短さチェック
        episode = str(record.get('episode_text', ''))
        if len(episode) < 20:  # 20文字未満は疑わしい
            indicators += 1
        
        # 同じ値の繰り返しチェック（例：名前が全て同じ）
        if record.get('person_name') == record.get('person_name_display'):
            if record.get('person_name') == record.get('person_name_ja'):
                indicators += 1  # 全部同じは疑わしい
        
        return indicators
    
    def calculate_completeness_score(self, record: Dict) -> float:
        """完全性スコアの計算"""
        score = 0.0
        total_weight = 0.0
        
        # 必須フィールドの確認（重み60%）
        for field in self.required_fields:
            total_weight += 6.0
            value = record.get(field)
            if value and str(value) != 'nan' and str(value).strip():
                score += 6.0
        
        # 重要フィールドの確認（重み40%）
        for field in self.important_fields:
            total_weight += 4.0
            value = record.get(field)
            if value and str(value) != 'nan' and str(value).strip():
                score += 4.0
        
        # 正規化（10点満点）
        return (score / total_weight) * 10 if total_weight > 0 else 0
    
    def calculate_consistency_score(self, record: Dict) -> float:
        """一貫性スコアの計算"""
        score = 10.0  # 減点方式
        
        # カテゴリの妥当性
        category = str(record.get('category', ''))
        if category not in self.valid_categories:
            score -= 2.0
        
        # 国籍の妥当性
        nationality = str(record.get('nationality', ''))
        if nationality not in self.valid_nationalities and nationality not in ['不明', 'その他']:
            score -= 1.0
        
        # 架空キャラクターの一貫性チェック
        if category == '架空のキャラクター':
            # 架空キャラクターなのに実在の国籍がある場合
            if nationality in self.valid_nationalities:
                score -= 0.5  # 軽微な減点（設定として可能性あり）
            
            # 作品名が含まれているかチェック
            display_name = str(record.get('person_name_display', ''))
            if '（' not in display_name and '『' not in display_name:
                score -= 2.0  # 作品名がない架空キャラクターは問題
        
        # 生年のフォーマットチェック
        birth_year = record.get('birth_year')
        if birth_year and birth_year != 'nan':
            try:
                year = int(float(birth_year))
                if year < 1000 or year > 2030:
                    score -= 1.0  # 異常な年
            except:
                score -= 1.0  # 数値でない
        
        # 認知度スコアの妥当性
        recognition = record.get('name_recognition')
        if recognition is not None and recognition != 'nan':
            try:
                rec_score = float(recognition)
                if rec_score < 0 or rec_score > 100:
                    score -= 1.0  # 範囲外
            except:
                score -= 1.0
        
        return max(0, score)
    
    def calculate_reliability_score(self, record: Dict) -> float:
        """信頼性スコアの計算"""
        score = 5.0  # 基準点
        
        # ソースの信頼性
        source = str(record.get('source', ''))
        
        # 信頼できるソース
        for trusted in self.trusted_sources:
            if trusted in source:
                score += 3.0
                break
        
        # 疑わしいソース
        for suspicious in self.suspicious_sources:
            if suspicious in source:
                score -= 3.0
                break
        
        # 作成日時の存在
        if record.get('created_at') and str(record.get('created_at')) != 'nan':
            score += 1.0
        
        # 更新日時の存在
        if record.get('updated_at') and str(record.get('updated_at')) != 'nan':
            score += 1.0
        
        return min(10, max(0, score))
    
    def calculate_episode_quality_score(self, record: Dict) -> float:
        """エピソード品質スコアの計算"""
        episode = str(record.get('episode_text', ''))
        
        if not episode or episode == 'nan':
            return 0
        
        score = 0.0
        
        # 長さによる評価
        length = len(episode)
        if length >= 200:
            score += 4.0
        elif length >= 100:
            score += 3.0
        elif length >= 50:
            score += 2.0
        elif length >= 20:
            score += 1.0
        
        # 内容の豊富さ（句読点の数で判断）
        punctuation_count = episode.count('。') + episode.count('、')
        if punctuation_count >= 5:
            score += 2.0
        elif punctuation_count >= 3:
            score += 1.0
        
        # 固有名詞の存在（カタカナ、漢字の混在）
        has_katakana = bool(re.search(r'[ァ-ヶー]', episode))
        has_kanji = bool(re.search(r'[一-龥]', episode))
        has_numbers = bool(re.search(r'\d', episode))
        
        if has_katakana:
            score += 1.0
        if has_kanji:
            score += 1.0
        if has_numbers:
            score += 1.0
        
        # プレースホルダーテキストの検出
        placeholder_texts = ['テスト', 'test', 'sample', 'TODO', 'ダミー', 'dummy']
        for ph_text in placeholder_texts:
            if ph_text.lower() in episode.lower():
                score -= 3.0
                break
        
        # 繰り返しパターンの検出
        if re.search(r'(.{5,})\1{2,}', episode):  # 同じ文字列の繰り返し
            score -= 2.0
        
        return min(10, max(0, score))
    
    def score_record(self, record: Dict) -> QualityResult:
        """レコードの総合品質スコア計算"""
        issues = []
        
        # 各スコアの計算
        completeness = self.calculate_completeness_score(record)
        consistency = self.calculate_consistency_score(record)
        reliability = self.calculate_reliability_score(record)
        episode_quality = self.calculate_episode_quality_score(record)
        placeholder_indicators = self.check_placeholder_indicators(record)
        
        # 問題点の記録
        if completeness < 5:
            issues.append("不完全なメタデータ")
        if consistency < 5:
            issues.append("データの不整合")
        if reliability < 5:
            issues.append("信頼性の低いソース")
        if episode_quality < 5:
            issues.append("低品質なエピソード")
        if placeholder_indicators >= 3:
            issues.append("プレースホルダーの可能性大")
        
        # 総合スコア計算（プレースホルダー指標でペナルティ）
        overall_score = (
            completeness * 0.25 +
            consistency * 0.25 +
            reliability * 0.25 +
            episode_quality * 0.25
        )
        
        # プレースホルダーペナルティ
        if placeholder_indicators >= 5:
            overall_score *= 0.3  # 70%減
        elif placeholder_indicators >= 3:
            overall_score *= 0.5  # 50%減
        elif placeholder_indicators >= 1:
            overall_score *= 0.8  # 20%減
        
        # 推奨判定
        if overall_score < 2:
            recommendation = 'DELETE_HIGH_CONFIDENCE'
        elif overall_score < 4:
            recommendation = 'DELETE_MEDIUM_CONFIDENCE'
        elif overall_score < 6:
            recommendation = 'REVIEW_REQUIRED'
        else:
            recommendation = 'KEEP'
        
        return QualityResult(
            person_id=str(record.get('person_id', '')),
            person_name=str(record.get('person_name', '')),
            person_name_display=str(record.get('person_name_display', '')),
            overall_quality_score=overall_score,
            completeness_score=completeness,
            consistency_score=consistency,
            reliability_score=reliability,
            episode_quality_score=episode_quality,
            placeholder_indicators=placeholder_indicators,
            recommendation=recommendation,
            issues=issues
        )
    
    def validate_batch(self, df: pd.DataFrame, sample_size: int = None) -> pd.DataFrame:
        """バッチ検証処理"""
        if sample_size:
            df = df.sample(min(sample_size, len(df)))
        
        results = []
        total = len(df)
        
        for idx, row in df.iterrows():
            logger.info(f"Processing {idx + 1}/{total}: {row.get('person_name_display', '')}")
            
            result = self.score_record(row.to_dict())
            
            results.append({
                'person_id': result.person_id,
                'person_name': result.person_name,
                'person_name_display': result.person_name_display,
                'metadata_quality_score': result.overall_quality_score,
                'completeness_score': result.completeness_score,
                'consistency_score': result.consistency_score,
                'reliability_score': result.reliability_score,
                'episode_quality_score': result.episode_quality_score,
                'placeholder_indicators': result.placeholder_indicators,
                'recommendation': result.recommendation,
                'issues': '; '.join(result.issues)
            })
        
        return pd.DataFrame(results)


def main():
    """メイン実行関数"""
    print("="*60)
    print("メタデータ品質スコアリングシステム")
    print("Metadata Quality Scoring System")
    print("="*60)
    
    # スコアラー初期化
    scorer = MetadataQualityScorer()
    
    # テストケース
    test_cases = [
        {
            'person_id': 'P007713',
            'person_name': 'Hayao Miyazaki',
            'person_name_display': '宮崎駿',
            'person_name_ja': 'みやざき はやお',
            'category': 'エンターテイメント',
            'nationality': '日本',
            'occupation': '映画監督',
            'birth_year': 1941,
            'name_recognition': 95,
            'episode_text': '「となりのトトロ」「千と千尋の神隠し」などを手がけた世界的に有名なアニメーション監督。スタジオジブリの創設者の一人で、日本アニメーションを世界に広めた功績は計り知れない。',
            'source': 'Wikipedia',
            'created_at': '2024-01-01'
        },
        {
            'person_id': 'P_TEST_001',
            'person_name': 'Test Person 123',
            'person_name_display': 'テスト太郎',
            'category': 'その他',
            'nationality': '不明',
            'occupation': '不明',
            'name_recognition': 0,
            'episode_text': 'テストテストテスト',
            'source': 'AI生成'
        }
    ]
    
    print("\n🔍 Testing metadata quality scoring...")
    for test in test_cases:
        print(f"\nTesting: {test['person_name_display']}")
        result = scorer.score_record(test)
        print(f"  Overall Score: {result.overall_quality_score:.2f}/10")
        print(f"  Completeness: {result.completeness_score:.2f}")
        print(f"  Consistency: {result.consistency_score:.2f}")
        print(f"  Reliability: {result.reliability_score:.2f}")
        print(f"  Episode Quality: {result.episode_quality_score:.2f}")
        print(f"  Placeholder Indicators: {result.placeholder_indicators}")
        print(f"  Recommendation: {result.recommendation}")
        if result.issues:
            print(f"  Issues: {', '.join(result.issues)}")
    
    # データベース検証の準備
    csv_file = 'ultra_think_EPISODE_FINAL_20250901_020106.csv'
    if pd.io.common.file_exists(csv_file):
        print(f"\n📂 Loading database: {csv_file}")
        df = pd.read_csv(csv_file, encoding='utf-8')
        print(f"✅ Total records: {len(df)}")
        
        # サンプル検証
        print("\n🔍 Validating sample records...")
        results_df = scorer.validate_batch(df, sample_size=10)
        
        # 結果保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"metadata_quality_results_{timestamp}.csv"
        results_df.to_csv(output_file, index=False, encoding='utf-8')
        print(f"\n💾 Results saved to: {output_file}")
        
        # サマリー表示
        print("\n📊 Validation Summary:")
        print(f"  DELETE_HIGH_CONFIDENCE: {len(results_df[results_df['recommendation'] == 'DELETE_HIGH_CONFIDENCE'])}")
        print(f"  DELETE_MEDIUM_CONFIDENCE: {len(results_df[results_df['recommendation'] == 'DELETE_MEDIUM_CONFIDENCE'])}")
        print(f"  REVIEW_REQUIRED: {len(results_df[results_df['recommendation'] == 'REVIEW_REQUIRED'])}")
        print(f"  KEEP: {len(results_df[results_df['recommendation'] == 'KEEP'])}")
        
        # プレースホルダー指標の分布
        print("\n📊 Placeholder Indicators Distribution:")
        for i in range(0, 10):
            count = len(results_df[results_df['placeholder_indicators'] == i])
            if count > 0:
                print(f"  {i} indicators: {count} records")
    
    print("\n✅ Metadata quality scoring system ready!")


if __name__ == "__main__":
    main()