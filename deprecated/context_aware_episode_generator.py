#!/usr/bin/env python3
"""
文脈認識型エピソード生成システム
内容に応じた適切な文章を追加し、重複を防ぐ
"""

import json
import csv
from datetime import datetime
from typing import Dict, List, Optional, Set
from pathlib import Path


class ContextAwareEpisodeGenerator:
    """文脈認識型エピソード生成システム"""

    def __init__(self):
        self.MIN_LENGTH = 150
        self.MAX_LENGTH = 300

        # カテゴリ別の適切な追加文章
        self.context_additions = {
            'sports': [
                "その勇姿は多くの人々に感動と勇気を与えました。",
                "スポーツの持つ力が、国境を越えて人々を繋ぎました。",
                "限界に挑む姿勢は、後進への道標となりました。"
            ],
            'art': [
                "その作品は時代を超えて愛され続けています。",
                "芸術の普遍的価値が、ここに結実しました。",
                "創造性の極致が、新たな表現の地平を開きました。"
            ],
            'science': [
                "この発見は人類の未来に希望をもたらしました。",
                "科学の進歩が、新たな可能性を切り開きました。",
                "真理への探求が、世界を変える一歩となりました。"
            ],
            'politics': [
                "この決断は日本の歴史に大きな転換点をもたらしました。",
                "政治的リーダーシップが、時代を動かした瞬間でした。",
                "国民の選択が、新たな時代の扉を開きました。"
            ],
            'business': [
                "この革新は産業界に大きなインパクトを与えました。",
                "ビジネスの新たな可能性が、ここから始まりました。",
                "起業家精神が、社会を変革する力となりました。"
            ],
            'entertainment': [
                "エンターテインメントの力が、人々に夢と希望を届けました。",
                "その才能は、多くの人々の心を豊かにしました。",
                "新しい表現が、時代の空気を変えました。"
            ],
            'challenge': [  # 真の挑戦的な内容にのみ使用
                "不可能と思われた挑戦に立ち向かう勇気が、歴史を変えました。",
                "困難を乗り越えた先に、新たな地平が開けました。",
                "挑戦する精神が、次世代への贈り物となりました。"
            ],
            'generic': [  # 汎用（最後の手段）
                "この出来事は、多くの人々の記憶に刻まれています。",
                "その功績は、今も語り継がれています。",
                "時代の証人となった瞬間でした。"
            ]
        }

    def _categorize_content(self, fact_text: str, person_name: str) -> str:
        """
        内容をカテゴライズして適切な文脈を判定

        Args:
            fact_text: 事実テキスト
            person_name: 人物名

        Returns:
            カテゴリ名
        """
        # キーワードベースのカテゴリ判定
        if any(k in fact_text for k in ['オリンピック', '金メダル', '銀メダル', '世界記録', '優勝']):
            return 'sports'
        elif any(k in fact_text for k in ['映画', '作品', '監督', '発表', '音楽', '作曲']):
            return 'art'
        elif any(k in fact_text for k in ['ノーベル', '研究', '発見', 'iPS', '開発']):
            return 'science'
        elif any(k in fact_text for k in ['総理', '大臣', '選挙', '政策', '解散', '民営化']):
            return 'politics'
        elif any(k in fact_text for k in ['創業', '起業', '設立', '買収', 'CEO']):
            return 'business'
        elif any(k in fact_text for k in ['紅白', 'YouTube', 'ヒット', '歌手', 'アイドル']):
            return 'entertainment'
        elif any(k in fact_text for k in ['史上初', '前人未到', '世界初']):
            return 'challenge'
        else:
            return 'generic'

    def _add_contextual_content(self, episode: str, fact_text: str,
                               person_name: str, used_phrases: Set[str]) -> tuple[str, Set[str]]:
        """
        文脈に応じた適切な内容を追加（重複防止機能付き）

        Args:
            episode: 現在のエピソード
            fact_text: 事実テキスト
            person_name: 人物名
            used_phrases: 既に使用されたフレーズのセット

        Returns:
            (拡張されたエピソード, 更新されたused_phrases)
        """
        category = self._categorize_content(fact_text, person_name)
        available_additions = self.context_additions[category].copy()

        # 既に使用されたフレーズを除外
        available_additions = [a for a in available_additions if a not in used_phrases]

        if not available_additions:
            # カテゴリの追加文が全て使用済みの場合、汎用から選択
            available_additions = [a for a in self.context_additions['generic']
                                 if a not in used_phrases]

        if available_additions:
            addition = available_additions[0]
            episode += addition
            used_phrases.add(addition)

        return episode, used_phrases

    def _adjust_length_with_context(self, episode: str, fact_text: str,
                                   person_name: str) -> str:
        """
        文脈を考慮した文字数調整（重複防止付き）

        Args:
            episode: エピソードテキスト
            fact_text: 事実テキスト
            person_name: 人物名

        Returns:
            調整されたエピソード
        """
        used_phrases = set()  # 使用済みフレーズを追跡
        current_length = len(episode)

        # 短すぎる場合
        while current_length < self.MIN_LENGTH:
            old_length = current_length
            episode, used_phrases = self._add_contextual_content(
                episode, fact_text, person_name, used_phrases
            )
            current_length = len(episode)

            # 追加できるフレーズがなくなった場合
            if current_length == old_length:
                # 最小限の汎用文を追加
                if current_length < self.MIN_LENGTH:
                    episode += f"（{self.MIN_LENGTH - current_length}文字不足）"
                break

        # 長すぎる場合
        if current_length > self.MAX_LENGTH:
            sentences = episode.split('。')
            if sentences[-1] == '':
                sentences = sentences[:-1]

            while len('。'.join(sentences) + '。') > self.MAX_LENGTH and len(sentences) > 2:
                sentences.pop()

            episode = '。'.join(sentences) + '。'

        return episode

    def check_logical_consistency(self, episode: str, fact_text: str) -> Dict:
        """
        論理的整合性をチェック

        Args:
            episode: エピソードテキスト
            fact_text: 事実テキスト

        Returns:
            チェック結果
        """
        issues = []

        # 政治的内容に「挑戦の素晴らしさ」は不適切
        if any(k in fact_text for k in ['選挙', '民営化', '政策', '解散']):
            if '挑戦することの素晴らしさ' in episode:
                issues.append("政治的決定に『挑戦の素晴らしさ』は不適切")

        # 芸術作品発表に「挑戦」より「芸術的価値」が適切
        if '発表' in fact_text and any(k in fact_text for k in ['映画', '作品', '小説']):
            if '挑戦することの素晴らしさ' in episode:
                issues.append("作品発表に『挑戦の素晴らしさ』より『芸術的価値』が適切")

        # 同じフレーズの重複チェック
        phrases = [
            "この瞬間は、私たちに挑戦することの素晴らしさを教えてくれます。",
            "この出来事は、私たちの心に深く刻まれています。"
        ]

        for phrase in phrases:
            count = episode.count(phrase)
            if count >= 2:
                issues.append(f"『{phrase[:20]}...』が{count}回重複")

        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'severity': 'high' if issues else 'none'
        }


def demonstrate_fix():
    """問題の修正を実演"""

    generator = ContextAwareEpisodeGenerator()

    # 問題のあるケース
    test_cases = [
        {
            'person': '小泉純一郎',
            'age': 63,
            'fact': '2005年、郵政解散・総選挙で圧勝、郵政民営化を実現',
            'problem': '政治的決定に「挑戦の素晴らしさ」は不適切'
        },
        {
            'person': '黒澤明',
            'age': 44,
            'fact': '1954年、『七人の侍』を発表、世界映画史上最高傑作の一つと評される',
            'problem': '芸術作品に「挑戦の素晴らしさ」より芸術的価値が適切'
        }
    ]

    print("=" * 60)
    print("文脈認識型エピソード生成の実演")
    print("=" * 60)

    for case in test_cases:
        print(f"\n【{case['person']}】")
        print(f"問題: {case['problem']}")

        # 基本エピソード
        base = f"あなたと同じ{case['age']}歳のとき、{case['person']}は{case['fact']}。"

        # 文脈を考慮した調整
        adjusted = generator._adjust_length_with_context(
            base, case['fact'], case['person']
        )

        print(f"\n修正後のエピソード({len(adjusted)}文字):")
        print(adjusted)

        # 論理的整合性チェック
        check_result = generator.check_logical_consistency(adjusted, case['fact'])
        if check_result['is_valid']:
            print("✅ 論理的整合性: OK")
        else:
            print("❌ 問題点:")
            for issue in check_result['issues']:
                print(f"   - {issue}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    demonstrate_fix()