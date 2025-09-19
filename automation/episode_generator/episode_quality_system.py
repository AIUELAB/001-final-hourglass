#!/usr/bin/env python3
"""
エピソード品質評価システム
生成されたエピソードの品質を多角的に評価
"""

import re
from typing import Dict, List, Optional


class EpisodeQualityEvaluator:
    """エピソード品質評価器"""
    
    def __init__(self):
        # 評価基準の重み付け
        self.weights = {
            'specificity': 0.3,      # 具体性
            'emotional_impact': 0.25, # 感情的インパクト
            'length': 0.15,          # 適切な長さ
            'coherence': 0.15,       # 一貫性
            'age_relevance': 0.15    # 年齢との関連性
        }
        
        # 感情的な言葉のリスト
        self.emotional_words = [
            '感動', '驚き', '喜び', '悲しみ', '希望', '絶望', '勇気', '恐怖',
            '愛', '憎しみ', '誇り', '屈辱', '感激', '失望', '興奮', '平穏',
            '幸せ', '不安', '安心', '焦り', '満足', '後悔', '感謝', '怒り',
            '初めて', '最初', '革命', '画期的', '歴史的', '伝説', '奇跡',
            '運命', '偉大', '革新', '突破', '克服', '挑戦', '成功', '失敗'
        ]
        
        # 具体的な要素を示す言葉
        self.specific_indicators = [
            '年', '歳', '月', '日', '時', '円', 'ドル', '人', '個', '回',
            '%', '第', '初', '最', '約', '以上', '以下', '世界', '日本',
            '発明', '発見', '開発', '設立', '創業', '発表', '受賞', '達成'
        ]
        
    def evaluate_episode(self, episode_text: str, age: int) -> Dict:
        """
        エピソードを評価
        
        Args:
            episode_text: エピソードのテキスト
            age: 対象年齢
            
        Returns:
            評価結果の辞書
        """
        scores = {}
        
        # 各項目を評価
        scores['specificity'] = self._evaluate_specificity(episode_text)
        scores['emotional_impact'] = self._evaluate_emotional_impact(episode_text)
        scores['length'] = self._evaluate_length(episode_text)
        scores['coherence'] = self._evaluate_coherence(episode_text)
        scores['age_relevance'] = self._evaluate_age_relevance(episode_text, age)
        
        # 総合スコアを計算
        total_score = sum(
            scores[key] * self.weights[key] 
            for key in scores
        )
        
        # 詳細な評価結果を返す
        return {
            'quality_score': round(total_score, 2),
            'detailed_scores': scores,
            'passed': total_score >= 60,
            'feedback': self._generate_feedback(scores),
            'strengths': self._identify_strengths(scores),
            'improvements': self._identify_improvements(scores)
        }
    
    def _evaluate_specificity(self, text: str) -> float:
        """具体性を評価（0-100）"""
        score = 0
        text_lower = text.lower()
        
        # 具体的な数字が含まれているか
        numbers = re.findall(r'\d+', text)
        if numbers:
            score += min(len(numbers) * 10, 30)
        
        # 具体的な指標語が含まれているか
        specific_count = sum(1 for word in self.specific_indicators if word in text)
        score += min(specific_count * 5, 40)
        
        # 固有名詞（大文字で始まる単語）の数
        proper_nouns = re.findall(r'[A-Z][a-z]+|[ァ-ヴー]+', text)
        if proper_nouns:
            score += min(len(proper_nouns) * 5, 30)
        
        return min(score, 100)
    
    def _evaluate_emotional_impact(self, text: str) -> float:
        """感情的インパクトを評価（0-100）"""
        score = 0
        text_lower = text.lower()
        
        # 感情的な言葉の使用
        emotional_count = sum(1 for word in self.emotional_words if word in text)
        score += min(emotional_count * 15, 60)
        
        # 感嘆符や疑問符の使用
        exclamations = text.count('！') + text.count('!')
        questions = text.count('？') + text.count('?')
        score += min((exclamations + questions) * 10, 20)
        
        # 引用符の使用（直接話法）
        quotes = text.count('「') + text.count('」') + text.count('"')
        if quotes > 0:
            score += 20
        
        return min(score, 100)
    
    def _evaluate_length(self, text: str) -> float:
        """長さの適切性を評価（0-100）"""
        # 理想的な長さは100-300文字
        length = len(text)
        
        if 100 <= length <= 300:
            return 100
        elif 50 <= length < 100:
            return 70
        elif 300 < length <= 500:
            return 80
        elif length < 50:
            return 30
        else:  # > 500
            return 50
    
    def _evaluate_coherence(self, text: str) -> float:
        """文章の一貫性を評価（0-100）"""
        score = 100
        
        # 文の数を数える
        sentences = re.split(r'[。！？\n]', text)
        sentences = [s for s in sentences if s.strip()]
        
        if len(sentences) == 0:
            return 0
        
        # 文が短すぎたり長すぎたりしないか
        for sentence in sentences:
            if len(sentence) < 10:
                score -= 10
            elif len(sentence) > 100:
                score -= 5
        
        # 接続詞や順序を示す言葉があるか
        connectors = ['そして', 'しかし', 'また', 'さらに', 'その後', 'やがて', 'ついに']
        connector_count = sum(1 for word in connectors if word in text)
        if connector_count > 0:
            score = min(score + connector_count * 5, 100)
        
        return max(score, 0)
    
    def _evaluate_age_relevance(self, text: str, age: int) -> float:
        """年齢との関連性を評価（0-100）"""
        score = 50  # ベーススコア
        
        # 年齢が直接言及されているか
        age_str = str(age)
        if age_str in text:
            score += 30
        
        # 年齢に関連する言葉があるか
        age_words = ['歳', '才', '年齢', '当時']
        for word in age_words:
            if word in text:
                score += 10
                break
        
        # 成長段階に応じた言葉があるか
        if age < 20:
            youth_words = ['子供', '少年', '少女', '学生', '青春']
            if any(word in text for word in youth_words):
                score += 10
        elif 20 <= age < 40:
            adult_words = ['青年', '若者', '成人', 'キャリア']
            if any(word in text for word in adult_words):
                score += 10
        else:
            mature_words = ['中年', '熟年', '経験', '円熟']
            if any(word in text for word in mature_words):
                score += 10
        
        return min(score, 100)
    
    def _generate_feedback(self, scores: Dict[str, float]) -> str:
        """評価に基づくフィードバックを生成"""
        feedback_parts = []
        
        if scores['specificity'] < 50:
            feedback_parts.append("より具体的な数字や固有名詞を追加してください")
        if scores['emotional_impact'] < 50:
            feedback_parts.append("感情的な要素や印象的な表現を強化してください")
        if scores['length'] < 50:
            feedback_parts.append("エピソードの長さを調整してください")
        if scores['coherence'] < 50:
            feedback_parts.append("文章の流れと一貫性を改善してください")
        if scores['age_relevance'] < 50:
            feedback_parts.append("年齢との関連性をより明確にしてください")
        
        return "。".join(feedback_parts) if feedback_parts else "良質なエピソードです"
    
    def _identify_strengths(self, scores: Dict[str, float]) -> List[str]:
        """強みを特定"""
        strengths = []
        for key, score in scores.items():
            if score >= 80:
                if key == 'specificity':
                    strengths.append("具体性が高い")
                elif key == 'emotional_impact':
                    strengths.append("感情的インパクトが強い")
                elif key == 'length':
                    strengths.append("適切な長さ")
                elif key == 'coherence':
                    strengths.append("文章が一貫している")
                elif key == 'age_relevance':
                    strengths.append("年齢との関連性が明確")
        return strengths
    
    def _identify_improvements(self, scores: Dict[str, float]) -> List[str]:
        """改善点を特定"""
        improvements = []
        for key, score in scores.items():
            if score < 60:
                if key == 'specificity':
                    improvements.append("具体性を高める")
                elif key == 'emotional_impact':
                    improvements.append("感情的要素を追加")
                elif key == 'length':
                    improvements.append("長さを調整")
                elif key == 'coherence':
                    improvements.append("文章の流れを改善")
                elif key == 'age_relevance':
                    improvements.append("年齢との関連を明確化")
        return improvements


if __name__ == "__main__":
    # テスト実行
    evaluator = EpisodeQualityEvaluator()
    
    # サンプルエピソード
    sample_episodes = [
        {
            'text': "26歳のアインシュタインは、特殊相対性理論を発表し、E=mc²の方程式を導出しました。この革命的な発見により、物理学の歴史が変わりました。",
            'age': 26
        },
        {
            'text': "若い頃の出来事です。",
            'age': 20
        },
        {
            'text': "12歳の時、エジソンは列車内で新聞を販売しながら、同時に化学実験を行っていました。ある日、実験中の事故で列車内で火災を起こしてしまい、車掌に叱られましたが、それでも実験への情熱は冷めませんでした。この経験が、後の「失敗は成功の母」という信念につながりました。",
            'age': 12
        }
    ]
    
    for i, episode in enumerate(sample_episodes, 1):
        print(f"\n=== エピソード {i} ===")
        print(f"テキスト: {episode['text'][:50]}...")
        result = evaluator.evaluate_episode(episode['text'], episode['age'])
        print(f"品質スコア: {result['quality_score']}/100")
        print(f"合格: {result['passed']}")
        print(f"強み: {', '.join(result['strengths']) if result['strengths'] else 'なし'}")
        print(f"改善点: {', '.join(result['improvements']) if result['improvements'] else 'なし'}")