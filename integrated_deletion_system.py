#!/usr/bin/env python3
"""
知名度ベース統合削除システム
Integrated Deletion System Based on Recognition

このシステムは、Wikipedia、Web検索、メタデータ品質の
3つの観点から人物データを評価し、削除推奨を行います。
"""

import pandas as pd
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Set
import logging
from dataclasses import dataclass, asdict
import yaml

# 各バリデーターのインポート
from wikipedia_validator_ultimate import WikipediaValidator
from web_search_validator import WebSearchValidator
from metadata_quality_scorer import MetadataQualityScorer

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class IntegratedResult:
    """統合評価結果"""
    person_id: str
    person_name: str
    person_name_display: str
    person_name_ja: str
    category: str
    nationality: str
    occupation: str
    
    # 各システムのスコア
    wikipedia_score: float
    web_search_score: float
    metadata_quality_score: float
    
    # 統合スコアと判定
    integrated_score: float
    deletion_recommendation: str
    confidence_level: str
    
    # 詳細情報
    reasons: List[str]
    safety_flags: List[str]
    protected: bool
    
    # 各システムの推奨
    wikipedia_recommendation: str
    web_search_recommendation: str
    metadata_recommendation: str

class IntegratedDeletionSystem:
    """統合削除システム"""
    
    def __init__(self, config_file: str = 'deletion_config.yaml'):
        """初期化"""
        self.config = self.load_config(config_file)
        
        # 各バリデーターの初期化
        logger.info("Initializing validators...")
        self.wikipedia_validator = WikipediaValidator()
        self.web_search_validator = WebSearchValidator()
        self.metadata_scorer = MetadataQualityScorer()
        
        # 重み設定（設定ファイルから）
        self.weights = self.config.get('weights', {
            'wikipedia': 0.40,
            'web_search': 0.30,
            'metadata_quality': 0.30
        })
        
        # 閾値設定
        self.thresholds = self.config.get('thresholds', {
            'delete_high_confidence': 2.0,
            'delete_medium_confidence': 4.0,
            'review_required': 6.0
        })
        
        # ホワイトリスト・ブラックリストの初期化
        self.whitelist = self.load_whitelist()
        self.blacklist = self.load_blacklist()
        
        # 結果保存用
        self.results = {}
        self.statistics = {
            'total_processed': 0,
            'delete_high_confidence': 0,
            'delete_medium_confidence': 0,
            'review_required': 0,
            'keep': 0,
            'protected': 0,
            'errors': 0
        }
    
    def load_config(self, config_file: str) -> Dict:
        """設定ファイルの読み込み"""
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            logger.warning(f"Config file {config_file} not found, using defaults")
            return {}
    
    def load_whitelist(self) -> Set[str]:
        """ホワイトリストの読み込み"""
        whitelist = set()
        
        # ファイルから読み込み
        if os.path.exists('whitelist.json'):
            with open('whitelist.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                whitelist.update(data.get('person_ids', []))
                whitelist.update(data.get('person_names', []))
        
        # 歴史的人物の自動保護
        historical_figures = [
            'カント', 'ヘレン・ケラー', 'ガンジー', 'マンデラ', 
            'アインシュタイン', 'ニュートン', 'ダーウィン',
            'マリー・キュリー', 'ライト兄弟', 'エジソン'
        ]
        whitelist.update(historical_figures)
        
        logger.info(f"Loaded {len(whitelist)} whitelist entries")
        return whitelist
    
    def load_blacklist(self) -> Set[str]:
        """ブラックリストの読み込み"""
        blacklist = set()
        
        if os.path.exists('blacklist.json'):
            with open('blacklist.json', 'r', encoding='utf-8') as f:
                data = json.load(f)
                blacklist.update(data.get('person_ids', []))
                blacklist.update(data.get('patterns', []))
        
        logger.info(f"Loaded {len(blacklist)} blacklist entries")
        return blacklist
    
    def is_protected(self, record: Dict) -> Tuple[bool, List[str]]:
        """保護対象かどうかのチェック"""
        safety_flags = []
        
        # ホワイトリストチェック
        if record.get('person_id') in self.whitelist:
            safety_flags.append("WHITELIST_ID")
            return True, safety_flags
        
        if record.get('person_name') in self.whitelist:
            safety_flags.append("WHITELIST_NAME")
            return True, safety_flags
        
        if record.get('person_name_display') in self.whitelist:
            safety_flags.append("WHITELIST_DISPLAY_NAME")
            return True, safety_flags
        
        # 歴史的人物の保護（1950年以前生まれ）
        birth_year = record.get('birth_year')
        if birth_year and birth_year != 'nan':
            try:
                year = int(float(birth_year))
                if year < 1950:
                    safety_flags.append("HISTORICAL_FIGURE")
                    if self.config.get('safety', {}).get('require_manual_review_for_historical', True):
                        return True, safety_flags
            except:
                pass
        
        # 文化的重要性の保護
        category = record.get('category', '')
        if category in ['歴史', '文学', '科学', '哲学', '芸術']:
            if self.config.get('safety', {}).get('cultural_significance_protection', True):
                safety_flags.append("CULTURAL_SIGNIFICANCE")
                # 完全保護ではなく、追加チェックのフラグとして使用
        
        return False, safety_flags
    
    def is_blacklisted(self, record: Dict) -> bool:
        """ブラックリスト対象かどうかのチェック"""
        # IDチェック
        if record.get('person_id') in self.blacklist:
            return True
        
        # パターンマッチング
        for pattern in self.blacklist:
            if pattern in str(record.get('person_name', '')):
                return True
            if pattern in str(record.get('person_name_display', '')):
                return True
        
        return False
    
    def evaluate_person(self, record: Dict) -> IntegratedResult:
        """個人の統合評価"""
        person_id = record.get('person_id', '')
        person_name = record.get('person_name', '')
        person_name_display = record.get('person_name_display', '')
        
        logger.info(f"Evaluating: {person_id} - {person_name_display}")
        
        # 保護チェック
        protected, safety_flags = self.is_protected(record)
        
        # ブラックリストチェック
        if self.is_blacklisted(record):
            safety_flags.append("BLACKLISTED")
        
        # 各システムでの評価
        try:
            # Wikipedia評価
            wiki_result = self.wikipedia_validator.calculate_wikipedia_score(
                person_name=person_name,
                person_name_display=person_name_display,
                occupation=record.get('occupation'),
                nationality=record.get('nationality')
            )
            wikipedia_score = wiki_result['total_score']
            wikipedia_recommendation = wiki_result['recommendation']
            
        except Exception as e:
            logger.error(f"Wikipedia validation error for {person_id}: {e}")
            wikipedia_score = 0
            wikipedia_recommendation = 'ERROR'
        
        try:
            # Web検索評価
            web_result = self.web_search_validator.calculate_web_search_score(
                person_name=person_name,
                person_name_display=person_name_display,
                occupation=record.get('occupation'),
                nationality=record.get('nationality')
            )
            web_search_score = web_result['total_score']
            web_search_recommendation = web_result['recommendation']
            
        except Exception as e:
            logger.error(f"Web search validation error for {person_id}: {e}")
            web_search_score = 0
            web_search_recommendation = 'ERROR'
        
        try:
            # メタデータ品質評価
            metadata_result = self.metadata_scorer.score_record(record)
            metadata_quality_score = metadata_result.overall_quality_score
            metadata_recommendation = metadata_result.recommendation
            
        except Exception as e:
            logger.error(f"Metadata scoring error for {person_id}: {e}")
            metadata_quality_score = 0
            metadata_recommendation = 'ERROR'
        
        # 統合スコアの計算
        integrated_score = (
            wikipedia_score * self.weights['wikipedia'] +
            web_search_score * self.weights['web_search'] +
            metadata_quality_score * self.weights['metadata_quality']
        )
        
        # 削除理由の収集
        reasons = []
        if wikipedia_score < 2:
            reasons.append("Wikipedia情報なし")
        if web_search_score < 2:
            reasons.append("Web検索結果少")
        if metadata_quality_score < 2:
            reasons.append("メタデータ品質低")
        
        # 保護対象の場合、スコアを上方修正
        if protected:
            integrated_score = max(integrated_score, 6.0)  # 最低でもREVIEW_REQUIRED
            reasons.append("保護対象")
        
        # ブラックリスト対象の場合、スコアを下方修正
        if "BLACKLISTED" in safety_flags:
            integrated_score = min(integrated_score, 1.0)
            reasons.append("ブラックリスト対象")
        
        # 削除推奨の判定
        if integrated_score < self.thresholds['delete_high_confidence']:
            deletion_recommendation = 'DELETE_HIGH_CONFIDENCE'
            confidence_level = 'HIGH'
        elif integrated_score < self.thresholds['delete_medium_confidence']:
            deletion_recommendation = 'DELETE_MEDIUM_CONFIDENCE'
            confidence_level = 'MEDIUM'
        elif integrated_score < self.thresholds['review_required']:
            deletion_recommendation = 'REVIEW_REQUIRED'
            confidence_level = 'LOW'
        else:
            deletion_recommendation = 'KEEP'
            confidence_level = 'KEEP'
        
        return IntegratedResult(
            person_id=person_id,
            person_name=str(person_name),
            person_name_display=str(person_name_display),
            person_name_ja=str(record.get('person_name_ja', '')),
            category=str(record.get('category', '')),
            nationality=str(record.get('nationality', '')),
            occupation=str(record.get('occupation', '')),
            wikipedia_score=wikipedia_score,
            web_search_score=web_search_score,
            metadata_quality_score=metadata_quality_score,
            integrated_score=integrated_score,
            deletion_recommendation=deletion_recommendation,
            confidence_level=confidence_level,
            reasons=reasons,
            safety_flags=safety_flags,
            protected=protected,
            wikipedia_recommendation=wikipedia_recommendation,
            web_search_recommendation=web_search_recommendation,
            metadata_recommendation=metadata_recommendation
        )
    
    def process_batch(self, records, output_dir: str = 'deletion_results'):
        """バッチ処理"""
        import pandas as pd
        
        os.makedirs(output_dir, exist_ok=True)
        
        # DataFrameの場合、辞書のリストに変換
        if isinstance(records, pd.DataFrame):
            records_list = records.to_dict('records')
            total = len(records_list)
        else:
            records_list = records
            total = len(records_list)
        
        results = []
        
        for idx, record in enumerate(records_list):
            logger.info(f"Processing {idx + 1}/{total}")
            
            try:
                result = self.evaluate_person(record)
                
                # 結果を辞書形式で保存
                result_dict = {
                    'person_id': result.person_id,
                    'person_name': result.person_name,
                    'person_name_display': result.person_name_display,
                    'integrated_score': result.integrated_score,
                    'wikipedia_score': result.wikipedia_score,
                    'web_search_score': result.web_search_score,
                    'metadata_quality_score': result.metadata_quality_score,
                    'recommendation': result.deletion_recommendation,
                    'protected': result.protected,
                    'safety_flags': ', '.join(result.safety_flags) if result.safety_flags else ''
                }
                results.append(result_dict)
                
                # 統計更新
                self.statistics['total_processed'] += 1
                
                if result.deletion_recommendation == 'DELETE_HIGH_CONFIDENCE':
                    self.statistics['delete_high_confidence'] += 1
                elif result.deletion_recommendation == 'DELETE_MEDIUM_CONFIDENCE':
                    self.statistics['delete_medium_confidence'] += 1
                elif result.deletion_recommendation == 'REVIEW_REQUIRED':
                    self.statistics['review_required'] += 1
                else:
                    self.statistics['keep'] += 1
                
                if result.protected:
                    self.statistics['protected'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing {record.get('person_id')}: {e}")
                self.statistics['errors'] += 1
            
            # 定期的にキャッシュ保存
            if (idx + 1) % 50 == 0:
                self.save_intermediate_results(results, output_dir)
        
        # 最終結果保存
        self.save_final_results(results, output_dir)
        
        # DataFrameとして返す
        return pd.DataFrame(results)
    
    def save_intermediate_results(self, results, output_dir: str):
        """中間結果の保存"""
        import pandas as pd
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # JSON形式で保存
        output_file = os.path.join(output_dir, f"intermediate_results_{timestamp}.json")
        
        # resultsがリストの場合の処理
        data = {
            'timestamp': timestamp,
            'statistics': self.statistics,
            'results': results if isinstance(results, list) else [asdict(r) for r in results.values()]
        }
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def save_final_results(self, results, output_dir: str):
        """最終結果の保存"""
        import pandas as pd
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # resultsがリストの場合とDict[str, IntegratedResult]の場合を処理
        if isinstance(results, list):
            results_list = results
        else:
            results_list = [asdict(r) for r in results.values()]
        
        # 1. 削除候補リスト（CSV）
        delete_candidates = []
        for result in results_list:
            if isinstance(result, dict):
                if result.get('recommendation') in ['DELETE_HIGH_CONFIDENCE', 'DELETE_MEDIUM_CONFIDENCE']:
                    delete_candidates.append(result)
            else:
                if result.deletion_recommendation in ['DELETE_HIGH_CONFIDENCE', 'DELETE_MEDIUM_CONFIDENCE']:
                    delete_candidates.append({
                        'person_id': result.person_id,
                        'person_name': result.person_name,
                        'person_name_display': result.person_name_display,
                        'integrated_score': result.integrated_score,
                        'recommendation': result.deletion_recommendation,
                        'reasons': '; '.join(result.reasons) if hasattr(result, 'reasons') else ''
                    })
        
        if delete_candidates:
            df_delete = pd.DataFrame(delete_candidates)
            df_delete.to_csv(
                os.path.join(output_dir, f"delete_candidates_{timestamp}.csv"),
                index=False,
                encoding='utf-8'
            )
        
        # 2. 完全な結果（JSON）
        full_results_file = os.path.join(output_dir, f"deletion_analysis_complete_{timestamp}.json")
        
        data = {
            'timestamp': timestamp,
            'config': {
                'weights': self.weights,
                'thresholds': self.thresholds
            },
            'statistics': self.statistics,
            'results': results_list
        }
        
        with open(full_results_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 3. サマリーレポート（JSON）
        summary_file = os.path.join(output_dir, f"deletion_summary_{timestamp}.json")
        
        summary = {
            'timestamp': timestamp,
            'total_processed': self.statistics['total_processed'],
            'deletion_rate': (self.statistics['delete_high_confidence'] + 
                            self.statistics['delete_medium_confidence']) / 
                           max(self.statistics['total_processed'], 1) * 100,
            'statistics': self.statistics,
            'score_distribution': self.calculate_score_distribution(results),
            'top_delete_candidates': self.get_top_delete_candidates(results, 10),
            'protected_entries': self.get_protected_entries(results)
        }
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        # 4. 推奨アクションリスト（CSV）
        recommendations = []
        
        # resultsがリストか辞書かを判定
        if isinstance(results, list):
            results_to_process = results
        else:
            results_to_process = [asdict(r) for r in results.values()]
        
        for result in results_to_process:
            if isinstance(result, dict):
                recommendations.append({
                    'person_id': result.get('person_id'),
                    'person_name_display': result.get('person_name_display'),
                    'integrated_score': round(result.get('integrated_score', 0), 2),
                    'action': result.get('recommendation'),
                    'confidence': result.get('confidence_level', 'UNKNOWN'),
                    'wikipedia': round(result.get('wikipedia_score', 0), 2),
                    'web_search': round(result.get('web_search_score', 0), 2),
                    'metadata': round(result.get('metadata_quality_score', 0), 2)
                })
            else:
                recommendations.append({
                    'person_id': result.person_id,
                    'person_name_display': result.person_name_display,
                    'integrated_score': round(result.integrated_score, 2),
                    'action': result.deletion_recommendation,
                    'confidence': result.confidence_level,
                    'wikipedia': round(result.wikipedia_score, 2),
                    'web_search': round(result.web_search_score, 2),
                    'metadata': round(result.metadata_quality_score, 2)
                })
        
        df_rec = pd.DataFrame(recommendations)
        df_rec.to_csv(
            os.path.join(output_dir, f"deletion_recommendations_{timestamp}.csv"),
            index=False,
            encoding='utf-8'
        )
        
        logger.info(f"Results saved to {output_dir}")
        self.print_summary()
    
    def calculate_score_distribution(self, results) -> Dict:
        """スコア分布の計算"""
        if isinstance(results, list):
            scores = [r.get('integrated_score', 0) if isinstance(r, dict) else r.integrated_score 
                     for r in results]
        else:
            scores = [r.integrated_score for r in results.values()]
        
        if not scores:
            return {}
        
        return {
            'min': min(scores),
            'max': max(scores),
            'mean': sum(scores) / len(scores),
            'median': sorted(scores)[len(scores) // 2],
            'ranges': {
                '0-2': sum(1 for s in scores if s < 2),
                '2-4': sum(1 for s in scores if 2 <= s < 4),
                '4-6': sum(1 for s in scores if 4 <= s < 6),
                '6-8': sum(1 for s in scores if 6 <= s < 8),
                '8-10': sum(1 for s in scores if 8 <= s <= 10)
            }
        }
    
    def get_top_delete_candidates(self, results, limit: int = 10) -> List[Dict]:
        """削除候補上位の取得"""
        if isinstance(results, list):
            candidates = [
                {
                    'person_id': r.get('person_id') if isinstance(r, dict) else r.person_id,
                    'person_name': r.get('person_name_display') if isinstance(r, dict) else r.person_name_display,
                    'score': r.get('integrated_score') if isinstance(r, dict) else r.integrated_score,
                    'reasons': r.get('reasons', []) if isinstance(r, dict) else r.reasons
                }
                for r in results
                if (r.get('recommendation') if isinstance(r, dict) else r.deletion_recommendation) 
                   in ['DELETE_HIGH_CONFIDENCE', 'DELETE_MEDIUM_CONFIDENCE']
            ]
        else:
            candidates = [
                {
                    'person_id': r.person_id,
                    'person_name': r.person_name_display,
                    'score': r.integrated_score,
                    'reasons': r.reasons
                }
                for r in results.values()
                if r.deletion_recommendation in ['DELETE_HIGH_CONFIDENCE', 'DELETE_MEDIUM_CONFIDENCE']
            ]
        
        # スコアの低い順にソート
        candidates.sort(key=lambda x: x['score'])
        
        return candidates[:limit]
    
    def get_protected_entries(self, results) -> List[Dict]:
        """保護対象エントリの取得"""
        if isinstance(results, list):
            protected = [
                {
                    'person_id': r.get('person_id') if isinstance(r, dict) else r.person_id,
                    'person_name': r.get('person_name_display') if isinstance(r, dict) else r.person_name_display,
                    'safety_flags': r.get('safety_flags') if isinstance(r, dict) else r.safety_flags
                }
                for r in results
                if (r.get('protected') if isinstance(r, dict) else r.protected)
            ]
        else:
            protected = [
                {
                    'person_id': r.person_id,
                    'person_name': r.person_name_display,
                    'safety_flags': r.safety_flags,
                    'score': r.integrated_score
                }
                for r in results.values()
                if r.protected
            ]
        
        return protected
    
    def print_summary(self):
        """サマリーの表示"""
        print("\n" + "="*60)
        print("統合削除システム - 処理サマリー")
        print("="*60)
        
        total = self.statistics['total_processed']
        if total == 0:
            print("処理されたレコードがありません")
            return
        
        print(f"\n処理件数: {total}")
        print(f"エラー: {self.statistics['errors']}")
        print(f"保護対象: {self.statistics['protected']}")
        
        print("\n削除推奨内訳:")
        print(f"  高信頼度削除: {self.statistics['delete_high_confidence']} "
              f"({self.statistics['delete_high_confidence']/total*100:.1f}%)")
        print(f"  中信頼度削除: {self.statistics['delete_medium_confidence']} "
              f"({self.statistics['delete_medium_confidence']/total*100:.1f}%)")
        print(f"  要レビュー: {self.statistics['review_required']} "
              f"({self.statistics['review_required']/total*100:.1f}%)")
        print(f"  保持: {self.statistics['keep']} "
              f"({self.statistics['keep']/total*100:.1f}%)")
        
        deletion_total = (self.statistics['delete_high_confidence'] + 
                         self.statistics['delete_medium_confidence'])
        print(f"\n総削除推奨: {deletion_total} ({deletion_total/total*100:.1f}%)")


def main():
    """メイン実行関数"""
    print("="*60)
    print("知名度ベース統合削除システム")
    print("Integrated Deletion System Based on Recognition")
    print("="*60)
    
    # システム初期化
    system = IntegratedDeletionSystem()
    
    # テストデータ
    test_data = [
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
            'episode_text': 'スタジオジブリの創設者',
            'source': 'Wikipedia'
        },
        {
            'person_id': 'P_TEST_001',
            'person_name': 'Test Person',
            'person_name_display': 'テスト太郎',
            'category': 'その他',
            'nationality': '不明',
            'occupation': '不明',
            'name_recognition': 0,
            'episode_text': 'テスト',
            'source': 'AI生成'
        }
    ]
    
    print("\n🔍 Testing integrated system...")
    results = system.process_batch(test_data, "test_output")
    
    print("\n📊 Test Results:")
    for person_id, result in results.items():
        print(f"\n{result.person_name_display}:")
        print(f"  統合スコア: {result.integrated_score:.2f}/10")
        print(f"  推奨: {result.deletion_recommendation}")
        print(f"  信頼度: {result.confidence_level}")
        if result.reasons:
            print(f"  理由: {', '.join(result.reasons)}")
    
    print("\n✅ Integrated deletion system ready!")


if __name__ == "__main__":
    main()