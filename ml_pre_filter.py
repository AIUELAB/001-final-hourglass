#!/usr/bin/env python3
"""
機械学習による事前フィルタリングシステム
明らかな有名人/一般人を高速判定し、API呼び出しを削減
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import pickle
from pathlib import Path
import logging
from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
import joblib

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class PredictionResult:
    """予測結果"""
    person_id: str
    person_name: str
    predicted_score: float
    confidence: float
    skip_api: bool
    reason: str


class MLPreFilter:
    """機械学習による事前フィルタリング"""
    
    def __init__(self, model_path: Optional[str] = None):
        self.model = None
        self.label_encoders = {}
        self.feature_columns = []
        self.model_path = model_path or "ml_prefilter_model.pkl"
        
        # 特徴量定義
        self.features_config = {
            'name_features': ['name_length', 'has_kanji', 'has_katakana', 'has_english'],
            'metadata_features': ['has_wikipedia', 'category_encoded', 'birth_year_known'],
            'pattern_features': ['is_group_member', 'name_complexity', 'title_count']
        }
        
        # 高信頼度で判定可能なパターン
        self.high_confidence_patterns = {
            'ultra_famous': {
                'keywords': ['HIKAKIN', '米津玄師', '大谷翔平', '新垣結衣', '嵐'],
                'score': 9.5,
                'confidence': 0.99
            },
            'fictional_protected': {
                'keywords': ['ドラえもん', '孫悟空', 'ピカチュウ', 'ルフィ'],
                'score': 8.0,
                'confidence': 0.95
            },
            'obvious_general': {
                'patterns': [r'^田中\s*\d+$', r'^山田\s*太郎$', r'^test_'],
                'score': 1.0,
                'confidence': 0.90
            }
        }
    
    def extract_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """特徴量抽出"""
        features = pd.DataFrame()
        
        # 名前関連の特徴
        features['name_length'] = df['person_name'].str.len()
        features['has_kanji'] = df['person_name_ja'].str.contains(r'[\u4e00-\u9fff]', na=False).astype(int)
        features['has_katakana'] = df['person_name_ja'].str.contains(r'[\u30a0-\u30ff]', na=False).astype(int)
        features['has_english'] = df['person_name'].str.contains(r'[a-zA-Z]', na=False).astype(int)
        
        # メタデータ特徴
        features['has_wikipedia'] = df.get('wikipedia_url', pd.Series()).notna().astype(int)
        features['birth_year_known'] = df.get('birth_year', pd.Series()).notna().astype(int)
        
        # カテゴリエンコーディング
        if 'category' in df.columns:
            if 'category' not in self.label_encoders:
                self.label_encoders['category'] = LabelEncoder()
                features['category_encoded'] = self.label_encoders['category'].fit_transform(
                    df['category'].fillna('unknown')
                )
            else:
                # 未知のカテゴリは'unknown'として扱う
                known_categories = set(self.label_encoders['category'].classes_)
                df_category = df['category'].fillna('unknown')
                df_category = df_category.apply(lambda x: x if x in known_categories else 'unknown')
                features['category_encoded'] = self.label_encoders['category'].transform(df_category)
        else:
            features['category_encoded'] = 0
        
        # パターン特徴
        features['is_group_member'] = df['person_name_ja'].str.contains(
            r'（.+）', na=False
        ).astype(int)
        
        # 名前の複雑度（文字種の数）
        def name_complexity(name):
            if pd.isna(name):
                return 0
            types = 0
            if any('\u4e00' <= c <= '\u9fff' for c in name):  # 漢字
                types += 1
            if any('\u3040' <= c <= '\u309f' for c in name):  # ひらがな
                types += 1
            if any('\u30a0' <= c <= '\u30ff' for c in name):  # カタカナ
                types += 1
            if any('a' <= c.lower() <= 'z' for c in name):  # 英字
                types += 1
            return types
        
        features['name_complexity'] = df['person_name_ja'].apply(name_complexity)
        
        # 称号・肩書きの数
        titles = ['先生', '博士', '教授', '氏', '様', '殿', '代表', '会長', '社長']
        features['title_count'] = df['person_name_ja'].apply(
            lambda x: sum(1 for title in titles if title in str(x))
        )
        
        return features
    
    def apply_high_confidence_rules(self, df: pd.DataFrame) -> List[PredictionResult]:
        """高信頼度ルールベース判定"""
        results = []
        
        for idx, row in df.iterrows():
            name = row.get('person_name', '')
            name_ja = row.get('person_name_ja', '')
            person_id = row.get('person_id', f'P{idx:05d}')
            
            # 超有名人チェック
            for keyword in self.high_confidence_patterns['ultra_famous']['keywords']:
                if keyword in name or keyword in name_ja:
                    results.append(PredictionResult(
                        person_id=person_id,
                        person_name=name_ja or name,
                        predicted_score=self.high_confidence_patterns['ultra_famous']['score'],
                        confidence=self.high_confidence_patterns['ultra_famous']['confidence'],
                        skip_api=True,
                        reason=f"超有名人パターン: {keyword}"
                    ))
                    break
            
            # 架空キャラクター保護
            for keyword in self.high_confidence_patterns['fictional_protected']['keywords']:
                if keyword in name or keyword in name_ja:
                    results.append(PredictionResult(
                        person_id=person_id,
                        person_name=name_ja or name,
                        predicted_score=self.high_confidence_patterns['fictional_protected']['score'],
                        confidence=self.high_confidence_patterns['fictional_protected']['confidence'],
                        skip_api=True,
                        reason=f"保護対象キャラクター: {keyword}"
                    ))
                    break
        
        return results
    
    def train_model(self, training_data: pd.DataFrame, target_scores: pd.Series):
        """モデル訓練"""
        logger.info("🎯 MLモデル訓練開始")
        
        # 特徴量抽出
        X = self.extract_features(training_data)
        y = target_scores
        
        # モデル訓練
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        
        self.model.fit(X, y)
        self.feature_columns = X.columns.tolist()
        
        # モデル保存
        self.save_model()
        
        logger.info("✅ モデル訓練完了")
        
        # 特徴量重要度
        importance = pd.DataFrame({
            'feature': self.feature_columns,
            'importance': self.model.feature_importances_
        }).sort_values('importance', ascending=False)
        
        logger.info("📊 特徴量重要度:")
        for _, row in importance.head(5).iterrows():
            logger.info(f"  {row['feature']}: {row['importance']:.3f}")
    
    def predict(self, df: pd.DataFrame) -> Tuple[List[PredictionResult], pd.DataFrame]:
        """予測実行"""
        results = []
        
        # 1. 高信頼度ルールベース判定
        rule_based_results = self.apply_high_confidence_rules(df)
        rule_based_ids = {r.person_id for r in rule_based_results}
        results.extend(rule_based_results)
        
        # 2. ルールベースで判定できなかったものをML判定
        remaining_df = df[~df['person_id'].isin(rule_based_ids)]
        
        if len(remaining_df) > 0 and self.model is not None:
            X = self.extract_features(remaining_df)
            
            # 予測
            predictions = self.model.predict(X)
            probabilities = self.model.predict_proba(X)
            confidences = np.max(probabilities, axis=1)
            
            # 結果作成
            for idx, (pred, conf) in enumerate(zip(predictions, confidences)):
                row = remaining_df.iloc[idx]
                
                # 高信頼度の予測のみAPI呼び出しをスキップ
                skip_api = conf > 0.9 and (pred < 2.0 or pred > 8.0)
                
                results.append(PredictionResult(
                    person_id=row.get('person_id', f'P{idx:05d}'),
                    person_name=row.get('person_name_ja', row.get('person_name', '')),
                    predicted_score=float(pred),
                    confidence=float(conf),
                    skip_api=skip_api,
                    reason=f"ML予測 (信頼度: {conf:.2%})"
                ))
        
        # API呼び出しが必要なレコードと不要なレコードを分離
        needs_api_df = df[df['person_id'].isin([r.person_id for r in results if not r.skip_api])]
        
        return results, needs_api_df
    
    def save_model(self):
        """モデル保存"""
        model_data = {
            'model': self.model,
            'label_encoders': self.label_encoders,
            'feature_columns': self.feature_columns,
            'patterns': self.high_confidence_patterns
        }
        joblib.dump(model_data, self.model_path)
        logger.info(f"✅ モデル保存: {self.model_path}")
    
    def load_model(self):
        """モデル読み込み"""
        if Path(self.model_path).exists():
            model_data = joblib.load(self.model_path)
            self.model = model_data['model']
            self.label_encoders = model_data['label_encoders']
            self.feature_columns = model_data['feature_columns']
            self.high_confidence_patterns = model_data['patterns']
            logger.info(f"✅ モデル読み込み: {self.model_path}")
            return True
        return False
    
    def get_statistics(self, results: List[PredictionResult]) -> Dict:
        """統計情報取得"""
        total = len(results)
        skipped = sum(1 for r in results if r.skip_api)
        
        return {
            'total_processed': total,
            'api_skipped': skipped,
            'api_required': total - skipped,
            'skip_rate': (skipped / total * 100) if total > 0 else 0,
            'high_confidence': sum(1 for r in results if r.confidence > 0.9),
            'medium_confidence': sum(1 for r in results if 0.7 <= r.confidence <= 0.9),
            'low_confidence': sum(1 for r in results if r.confidence < 0.7)
        }


def demo_prefilter():
    """デモ実行"""
    # テストデータ作成
    test_data = pd.DataFrame([
        {"person_id": "P001", "person_name": "HIKAKIN", "person_name_ja": "ヒカキン", "category": "YouTuber"},
        {"person_id": "P002", "person_name": "Tanaka123", "person_name_ja": "田中123", "category": None},
        {"person_id": "P003", "person_name": "Doraemon", "person_name_ja": "ドラえもん", "category": "架空"},
        {"person_id": "P004", "person_name": "Unknown Person", "person_name_ja": "不明な人", "category": None},
        {"person_id": "P005", "person_name": "Ohtani Shohei", "person_name_ja": "大谷翔平", "category": "野球選手"},
    ])
    
    # フィルター初期化
    filter_system = MLPreFilter()
    
    # 予測実行
    results, needs_api_df = filter_system.predict(test_data)
    
    # 結果表示
    print("\n📊 事前フィルタリング結果:")
    print("=" * 60)
    
    for result in results:
        status = "🚫 API不要" if result.skip_api else "✅ API必要"
        print(f"{status} {result.person_name}: スコア={result.predicted_score:.1f} "
              f"(信頼度: {result.confidence:.2%}) - {result.reason}")
    
    # 統計表示
    stats = filter_system.get_statistics(results)
    print("\n📈 統計情報:")
    print(f"  処理件数: {stats['total_processed']}")
    print(f"  APIスキップ: {stats['api_skipped']} ({stats['skip_rate']:.1f}%)")
    print(f"  API必要: {stats['api_required']}")
    
    return results, needs_api_df


if __name__ == "__main__":
    demo_prefilter()