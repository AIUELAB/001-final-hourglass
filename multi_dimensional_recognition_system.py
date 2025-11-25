#!/usr/bin/env python3
"""
多次元知名度認識システム
Multi-Dimensional Recognition System

知名度を多面的に評価し、より正確な削除判定を行うシステム。
時代性、分野、地域、持続性など複数の次元で評価します。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
import numpy as np
from datetime import datetime, timedelta
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RecognitionDimension(Enum):
    """知名度の評価次元"""
    GLOBAL = "国際的知名度"
    NATIONAL = "国内知名度"
    PROFESSIONAL = "専門分野内知名度"
    CULTURAL = "文化的影響度"
    HISTORICAL = "歴史的重要性"
    CONTEMPORARY = "現代的関連性"
    DIGITAL = "デジタルプレゼンス"
    ACADEMIC = "学術的認知度"
    MEDIA = "メディア露出度"
    SOCIAL = "社会的影響力"


class TimePeriod(Enum):
    """時代区分"""
    ANCIENT = "古代（〜1600年）"
    EARLY_MODERN = "近世（1600-1868年）"
    MODERN = "近代（1868-1945年）"
    POSTWAR = "戦後（1945-1989年）"
    CONTEMPORARY = "現代（1989-2010年）"
    DIGITAL_AGE = "デジタル時代（2010年〜）"


class FieldCategory(Enum):
    """分野カテゴリ"""
    POLITICS = "政治"
    SCIENCE = "科学・技術"
    ARTS = "芸術・文化"
    SPORTS = "スポーツ"
    ENTERTAINMENT = "エンターテインメント"
    BUSINESS = "ビジネス"
    EDUCATION = "教育"
    RELIGION = "宗教・思想"
    MILITARY = "軍事"
    SOCIAL = "社会活動"
    DIGITAL_CREATOR = "デジタルクリエイター"


@dataclass
class RecognitionProfile:
    """個人の知名度プロファイル"""
    person_id: str
    person_name: str

    # 基本属性
    field: FieldCategory
    time_period: TimePeriod
    nationality: str

    # 多次元スコア（0-10）
    dimension_scores: Dict[RecognitionDimension, float] = field(default_factory=dict)

    # 時系列データ
    peak_year: Optional[int] = None
    active_years: List[int] = field(default_factory=list)

    # 特殊指標
    is_living: bool = True
    has_wikipedia: bool = False
    wikipedia_languages: int = 0
    google_trends_score: float = 0.0
    social_media_followers: int = 0
    news_mentions_recent: int = 0
    academic_citations: int = 0

    # 文脈的重要性
    cultural_significance: float = 0.0
    educational_importance: float = 0.0
    historical_importance: float = 0.0

    # 最終評価
    total_recognition_score: float = 0.0
    confidence_level: float = 0.0
    preservation_priority: str = "MEDIUM"


class MultiDimensionalRecognitionSystem:
    """多次元知名度認識システム"""

    def __init__(self):
        """初期化"""
        self.dimension_weights = self._initialize_dimension_weights()
        self.field_specific_weights = self._initialize_field_weights()
        self.time_decay_factors = self._initialize_time_decay()

    def _initialize_dimension_weights(self) -> Dict[RecognitionDimension, float]:
        """次元別の基本重み"""
        return {
            RecognitionDimension.GLOBAL: 1.5,
            RecognitionDimension.NATIONAL: 1.2,
            RecognitionDimension.PROFESSIONAL: 1.0,
            RecognitionDimension.CULTURAL: 1.3,
            RecognitionDimension.HISTORICAL: 1.1,
            RecognitionDimension.CONTEMPORARY: 1.0,
            RecognitionDimension.DIGITAL: 0.8,
            RecognitionDimension.ACADEMIC: 0.9,
            RecognitionDimension.MEDIA: 1.0,
            RecognitionDimension.SOCIAL: 1.0,
        }

    def _initialize_field_weights(self) -> Dict[FieldCategory, Dict[RecognitionDimension, float]]:
        """分野別の次元重み調整"""
        return {
            FieldCategory.SCIENCE: {
                RecognitionDimension.ACADEMIC: 2.0,
                RecognitionDimension.PROFESSIONAL: 1.8,
                RecognitionDimension.DIGITAL: 0.5,
            },
            FieldCategory.ENTERTAINMENT: {
                RecognitionDimension.MEDIA: 2.0,
                RecognitionDimension.DIGITAL: 1.5,
                RecognitionDimension.CONTEMPORARY: 1.8,
                RecognitionDimension.ACADEMIC: 0.3,
            },
            FieldCategory.DIGITAL_CREATOR: {
                RecognitionDimension.DIGITAL: 2.5,
                RecognitionDimension.CONTEMPORARY: 2.0,
                RecognitionDimension.SOCIAL: 1.8,
                RecognitionDimension.HISTORICAL: 0.2,
            },
            FieldCategory.POLITICS: {
                RecognitionDimension.HISTORICAL: 1.8,
                RecognitionDimension.NATIONAL: 1.5,
                RecognitionDimension.GLOBAL: 1.3,
            },
        }

    def _initialize_time_decay(self) -> Dict[TimePeriod, float]:
        """時代による減衰係数"""
        return {
            TimePeriod.ANCIENT: 0.7,  # 古い時代は別の基準
            TimePeriod.EARLY_MODERN: 0.8,
            TimePeriod.MODERN: 0.9,
            TimePeriod.POSTWAR: 1.0,
            TimePeriod.CONTEMPORARY: 1.1,
            TimePeriod.DIGITAL_AGE: 1.2,  # 現代は高めの係数
        }

    def evaluate_person(self, person_data: Dict[str, Any]) -> RecognitionProfile:
        """
        人物の多次元評価

        Args:
            person_data: 人物データ

        Returns:
            知名度プロファイル
        """
        profile = RecognitionProfile(
            person_id=person_data.get('person_id', ''),
            person_name=person_data.get('person_name_display', ''),
            field=self._determine_field(person_data),
            time_period=self._determine_time_period(person_data),
            nationality=person_data.get('nationality', '不明')
        )

        # 各次元のスコア計算
        profile.dimension_scores = self._calculate_dimension_scores(person_data, profile)

        # 特殊指標の設定
        self._set_special_indicators(profile, person_data)

        # 総合スコア計算
        profile.total_recognition_score = self._calculate_total_score(profile)

        # 保存優先度決定
        profile.preservation_priority = self._determine_preservation_priority(profile)

        return profile

    def _determine_field(self, person_data: Dict) -> FieldCategory:
        """分野の判定"""
        occupation = person_data.get('occupation', '').lower()
        category = person_data.get('category', '').lower()

        # キーワードマッチング
        if any(word in occupation for word in ['youtuber', 'インフルエンサー', 'ブロガー']):
            return FieldCategory.DIGITAL_CREATOR
        elif any(word in occupation for word in ['俳優', '歌手', 'タレント', '芸人']):
            return FieldCategory.ENTERTAINMENT
        elif any(word in occupation for word in ['科学者', '研究者', '博士', '教授']):
            return FieldCategory.SCIENCE
        elif any(word in occupation for word in ['政治家', '大統領', '首相', '議員']):
            return FieldCategory.POLITICS
        elif any(word in category for word in ['スポーツ', '野球', 'サッカー']):
            return FieldCategory.SPORTS
        elif any(word in occupation for word in ['経営者', '実業家', 'CEO']):
            return FieldCategory.BUSINESS
        else:
            return FieldCategory.ARTS

    def _determine_time_period(self, person_data: Dict) -> TimePeriod:
        """活動時期の判定"""
        birth_year = person_data.get('birth_year')

        if not birth_year:
            # デフォルトは現代
            return TimePeriod.CONTEMPORARY

        try:
            year = int(birth_year)
            if year < 1600:
                return TimePeriod.ANCIENT
            elif year < 1868:
                return TimePeriod.EARLY_MODERN
            elif year < 1945:
                return TimePeriod.MODERN
            elif year < 1989:
                return TimePeriod.POSTWAR
            elif year < 2010:
                return TimePeriod.CONTEMPORARY
            else:
                return TimePeriod.DIGITAL_AGE
        except:
            return TimePeriod.CONTEMPORARY

    def _calculate_dimension_scores(self,
                                   person_data: Dict,
                                   profile: RecognitionProfile) -> Dict[RecognitionDimension, float]:
        """各次元のスコア計算"""
        scores = {}

        # グローバル知名度
        scores[RecognitionDimension.GLOBAL] = self._calculate_global_recognition(person_data)

        # 国内知名度
        scores[RecognitionDimension.NATIONAL] = self._calculate_national_recognition(person_data)

        # 専門分野内知名度
        scores[RecognitionDimension.PROFESSIONAL] = self._calculate_professional_recognition(person_data, profile.field)

        # 文化的影響度
        scores[RecognitionDimension.CULTURAL] = self._calculate_cultural_impact(person_data)

        # 歴史的重要性
        scores[RecognitionDimension.HISTORICAL] = self._calculate_historical_importance(person_data, profile.time_period)

        # 現代的関連性
        scores[RecognitionDimension.CONTEMPORARY] = self._calculate_contemporary_relevance(person_data)

        # デジタルプレゼンス
        scores[RecognitionDimension.DIGITAL] = self._calculate_digital_presence(person_data)

        # 学術的認知度
        scores[RecognitionDimension.ACADEMIC] = self._calculate_academic_recognition(person_data)

        # メディア露出度
        scores[RecognitionDimension.MEDIA] = self._calculate_media_exposure(person_data)

        # 社会的影響力
        scores[RecognitionDimension.SOCIAL] = self._calculate_social_impact(person_data)

        return scores

    def _calculate_global_recognition(self, data: Dict) -> float:
        """国際的知名度の計算"""
        score = 0.0

        # Wikipedia言語版数
        wiki_langs = data.get('wikipedia_languages', 0)
        if wiki_langs > 20:
            score += 10
        elif wiki_langs > 10:
            score += 8
        elif wiki_langs > 5:
            score += 6
        elif wiki_langs > 2:
            score += 4
        elif wiki_langs > 0:
            score += 2

        # 国際的な賞・称号
        if any(award in str(data.get('awards', '')) for award in ['Nobel', 'Olympic', 'Grammy', 'Oscar']):
            score = min(10, score + 3)

        return min(10, score)

    def _calculate_national_recognition(self, data: Dict) -> float:
        """国内知名度の計算"""
        score = 5.0  # ベーススコア

        # 日本のWikipediaページビュー
        if data.get('wikipedia_ja_pageviews', 0) > 10000:
            score += 3
        elif data.get('wikipedia_ja_pageviews', 0) > 1000:
            score += 2
        elif data.get('wikipedia_ja_pageviews', 0) > 100:
            score += 1

        # 国内メディア言及
        if data.get('news_mentions_japan', 0) > 100:
            score += 2

        return min(10, score)

    def _calculate_professional_recognition(self, data: Dict, field: FieldCategory) -> float:
        """専門分野内での認知度"""
        base_score = 5.0

        # 分野別の評価
        if field == FieldCategory.SCIENCE:
            # 論文引用数で評価
            citations = data.get('academic_citations', 0)
            if citations > 1000:
                return 10
            elif citations > 100:
                return 8
            elif citations > 10:
                return 6
            else:
                return 4

        elif field == FieldCategory.DIGITAL_CREATOR:
            # フォロワー数で評価
            followers = data.get('social_media_followers', 0)
            if followers > 10000000:  # 1000万以上
                return 10
            elif followers > 1000000:  # 100万以上
                return 8
            elif followers > 100000:  # 10万以上
                return 6
            elif followers > 10000:  # 1万以上
                return 4
            else:
                return 2

        return base_score

    def _calculate_cultural_impact(self, data: Dict) -> float:
        """文化的影響度"""
        score = 0.0

        # 文化財・作品の存在
        if data.get('has_major_works', False):
            score += 5

        # 教科書掲載
        if data.get('in_textbooks', False):
            score += 3

        # 記念館・銅像等
        if data.get('has_memorial', False):
            score += 2

        return min(10, score)

    def _calculate_historical_importance(self, data: Dict, period: TimePeriod) -> float:
        """歴史的重要性"""
        if period in [TimePeriod.ANCIENT, TimePeriod.EARLY_MODERN]:
            # 古い時代の人物は存在自体が重要
            return 8.0
        elif period == TimePeriod.MODERN:
            return 6.0
        else:
            # 現代人は歴史的評価が定まっていない
            return 3.0

    def _calculate_contemporary_relevance(self, data: Dict) -> float:
        """現代的関連性"""
        score = 5.0

        # 最近のニュース言及
        recent_news = data.get('news_mentions_recent', 0)
        if recent_news > 100:
            score += 3
        elif recent_news > 10:
            score += 2
        elif recent_news > 0:
            score += 1

        # SNSトレンド
        if data.get('trending_on_social', False):
            score += 2

        return min(10, score)

    def _calculate_digital_presence(self, data: Dict) -> float:
        """デジタルプレゼンス"""
        score = 0.0

        # YouTube登録者数
        youtube_subs = data.get('youtube_subscribers', 0)
        if youtube_subs > 10000000:
            score += 5
        elif youtube_subs > 1000000:
            score += 4
        elif youtube_subs > 100000:
            score += 3
        elif youtube_subs > 10000:
            score += 2
        elif youtube_subs > 1000:
            score += 1

        # Twitter/Xフォロワー
        twitter_followers = data.get('twitter_followers', 0)
        if twitter_followers > 1000000:
            score += 3
        elif twitter_followers > 100000:
            score += 2
        elif twitter_followers > 10000:
            score += 1

        # Instagram フォロワー
        ig_followers = data.get('instagram_followers', 0)
        if ig_followers > 1000000:
            score += 2

        return min(10, score)

    def _calculate_academic_recognition(self, data: Dict) -> float:
        """学術的認知度"""
        score = 0.0

        # 学術論文での言及
        academic_mentions = data.get('academic_mentions', 0)
        if academic_mentions > 100:
            score += 5
        elif academic_mentions > 10:
            score += 3
        elif academic_mentions > 0:
            score += 1

        # 専門書での記載
        if data.get('in_academic_books', False):
            score += 3

        # 大学講座
        if data.get('university_course', False):
            score += 2

        return min(10, score)

    def _calculate_media_exposure(self, data: Dict) -> float:
        """メディア露出度"""
        score = 0.0

        # TV出演回数
        tv_appearances = data.get('tv_appearances', 0)
        if tv_appearances > 100:
            score += 4
        elif tv_appearances > 10:
            score += 2
        elif tv_appearances > 0:
            score += 1

        # 新聞記事
        newspaper_articles = data.get('newspaper_articles', 0)
        if newspaper_articles > 100:
            score += 3
        elif newspaper_articles > 10:
            score += 2
        elif newspaper_articles > 0:
            score += 1

        # 雑誌特集
        if data.get('magazine_features', 0) > 10:
            score += 3

        return min(10, score)

    def _calculate_social_impact(self, data: Dict) -> float:
        """社会的影響力"""
        score = 5.0  # ベーススコア

        # 社会運動・改革
        if data.get('social_movement_leader', False):
            score += 3

        # チャリティ活動
        if data.get('charity_work', False):
            score += 1

        # 社会的賞
        if data.get('social_awards', 0) > 0:
            score += 1

        return min(10, score)

    def _set_special_indicators(self, profile: RecognitionProfile, data: Dict):
        """特殊指標の設定"""
        profile.has_wikipedia = data.get('has_wikipedia', False)
        profile.wikipedia_languages = data.get('wikipedia_languages', 0)
        profile.google_trends_score = data.get('google_trends_score', 0.0)
        profile.social_media_followers = data.get('total_followers', 0)
        profile.news_mentions_recent = data.get('news_mentions_recent', 0)
        profile.academic_citations = data.get('academic_citations', 0)

        # 文脈的重要性
        profile.cultural_significance = data.get('cultural_significance', 0.0)
        profile.educational_importance = data.get('educational_importance', 0.0)
        profile.historical_importance = data.get('historical_importance', 0.0)

    def _calculate_total_score(self, profile: RecognitionProfile) -> float:
        """総合スコアの計算"""
        total = 0.0
        weight_sum = 0.0

        # 基本重みを取得
        base_weights = self.dimension_weights.copy()

        # 分野別の重み調整を適用
        if profile.field in self.field_specific_weights:
            field_weights = self.field_specific_weights[profile.field]
            for dim, weight in field_weights.items():
                base_weights[dim] = weight

        # 時代による減衰を適用
        time_decay = self.time_decay_factors.get(profile.time_period, 1.0)

        # 重み付き平均を計算
        for dim, score in profile.dimension_scores.items():
            weight = base_weights[dim] * time_decay
            total += score * weight
            weight_sum += weight

        if weight_sum > 0:
            final_score = total / weight_sum
        else:
            final_score = 0.0

        # 特殊ケースの補正
        final_score = self._apply_special_corrections(profile, final_score)

        return min(10, final_score)

    def _apply_special_corrections(self, profile: RecognitionProfile, base_score: float) -> float:
        """特殊ケースの補正"""
        corrected_score = base_score

        # 超有名人の保護（Wikipedia20言語以上）
        if profile.wikipedia_languages >= 20:
            corrected_score = max(8.0, corrected_score)

        # デジタルクリエイターの補正（フォロワー1000万以上）
        if profile.field == FieldCategory.DIGITAL_CREATOR and profile.social_media_followers >= 10000000:
            corrected_score = max(7.0, corrected_score)

        # 歴史的人物の補正
        if profile.time_period in [TimePeriod.ANCIENT, TimePeriod.EARLY_MODERN]:
            corrected_score = max(6.0, corrected_score)

        # 文化的重要人物の補正
        if profile.cultural_significance > 8.0:
            corrected_score = max(7.0, corrected_score)

        return corrected_score

    def _determine_preservation_priority(self, profile: RecognitionProfile) -> str:
        """保存優先度の決定"""
        score = profile.total_recognition_score

        if score >= 8.0:
            return "CRITICAL"  # 絶対保存
        elif score >= 6.0:
            return "HIGH"      # 高優先度保存
        elif score >= 4.0:
            return "MEDIUM"    # 中優先度（要レビュー）
        elif score >= 2.0:
            return "LOW"       # 低優先度（削除候補）
        else:
            return "MINIMAL"   # 削除推奨

    def generate_deletion_recommendation(self, profile: RecognitionProfile) -> Dict[str, Any]:
        """削除推奨の生成"""
        return {
            'person_id': profile.person_id,
            'person_name': profile.person_name,
            'total_score': profile.total_recognition_score,
            'preservation_priority': profile.preservation_priority,
            'action': self._get_action(profile),
            'confidence': self._calculate_confidence(profile),
            'reasoning': self._generate_reasoning(profile),
            'dimension_breakdown': {
                dim.value: score for dim, score in profile.dimension_scores.items()
            }
        }

    def _get_action(self, profile: RecognitionProfile) -> str:
        """推奨アクション"""
        if profile.preservation_priority == "CRITICAL":
            return "KEEP_ABSOLUTE"
        elif profile.preservation_priority == "HIGH":
            return "KEEP_HIGH_CONFIDENCE"
        elif profile.preservation_priority == "MEDIUM":
            return "REVIEW_REQUIRED"
        elif profile.preservation_priority == "LOW":
            return "DELETE_LOW_CONFIDENCE"
        else:
            return "DELETE_HIGH_CONFIDENCE"

    def _calculate_confidence(self, profile: RecognitionProfile) -> float:
        """判定の信頼度計算"""
        # スコアの分散が小さいほど信頼度が高い
        scores = list(profile.dimension_scores.values())
        if scores:
            std_dev = np.std(scores)
            confidence = max(0.0, min(1.0, 1.0 - (std_dev / 5.0)))
        else:
            confidence = 0.5

        # 極端なスコアは信頼度を上げる
        if profile.total_recognition_score > 8 or profile.total_recognition_score < 2:
            confidence = min(1.0, confidence + 0.2)

        return confidence

    def _generate_reasoning(self, profile: RecognitionProfile) -> str:
        """判定理由の生成"""
        reasons = []

        # 最も高いスコアと低いスコアの次元を特定
        if profile.dimension_scores:
            sorted_dims = sorted(profile.dimension_scores.items(), key=lambda x: x[1], reverse=True)

            if sorted_dims[0][1] >= 7:
                reasons.append(f"{sorted_dims[0][0].value}が特に高い（{sorted_dims[0][1]:.1f}）")

            if sorted_dims[-1][1] <= 3:
                reasons.append(f"{sorted_dims[-1][0].value}が低い（{sorted_dims[-1][1]:.1f}）")

        # 分野特性
        if profile.field == FieldCategory.DIGITAL_CREATOR:
            reasons.append("デジタル時代の創作者として評価")
        elif profile.field == FieldCategory.SCIENCE:
            reasons.append("学術的貢献を重視")

        # 時代特性
        if profile.time_period in [TimePeriod.ANCIENT, TimePeriod.EARLY_MODERN]:
            reasons.append("歴史的価値を考慮")

        return "、".join(reasons) if reasons else "標準的な評価基準を適用"


def main():
    """テストとデモ"""
    print("="*60)
    print("多次元知名度認識システム")
    print("="*60)

    system = MultiDimensionalRecognitionSystem()

    # テストケース
    test_cases = [
        {
            'person_id': 'P000013',
            'person_name_display': 'HIKAKIN',
            'occupation': 'YouTuber',
            'category': 'エンターテインメント',
            'birth_year': 1989,
            'youtube_subscribers': 11000000,
            'twitter_followers': 2500000,
            'wikipedia_languages': 5,
            'news_mentions_recent': 150,
            'social_media_followers': 15000000
        },
        {
            'person_id': 'P000001',
            'person_name_display': '宮崎駿',
            'occupation': '映画監督',
            'category': '芸術',
            'birth_year': 1941,
            'wikipedia_languages': 45,
            'has_major_works': True,
            'cultural_significance': 9.5,
            'in_textbooks': True
        },
        {
            'person_id': 'P999999',
            'person_name_display': '架空太郎',
            'occupation': '不明',
            'category': 'その他',
            'birth_year': 1990,
            'wikipedia_languages': 0,
            'social_media_followers': 100
        }
    ]

    for test_data in test_cases:
        print(f"\n📊 評価対象: {test_data['person_name_display']}")
        print("-" * 40)

        profile = system.evaluate_person(test_data)
        recommendation = system.generate_deletion_recommendation(profile)

        print(f"分野: {profile.field.value}")
        print(f"時代: {profile.time_period.value}")
        print(f"\n各次元スコア:")
        for dim, score in profile.dimension_scores.items():
            print(f"  {dim.value}: {score:.1f}")

        print(f"\n総合スコア: {profile.total_recognition_score:.2f}/10")
        print(f"保存優先度: {profile.preservation_priority}")
        print(f"推奨アクション: {recommendation['action']}")
        print(f"信頼度: {recommendation['confidence']:.2%}")
        print(f"理由: {recommendation['reasoning']}")

    print("\n" + "="*60)
    print("✅ 多次元評価により、より精密な知名度判定が可能になりました")


if __name__ == "__main__":
    main()
