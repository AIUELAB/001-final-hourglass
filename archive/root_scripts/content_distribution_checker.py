#!/usr/bin/env python3
"""
配分チェッカー（Content Distribution Checker）
年齢時点の事実 vs その後の事実の配分を測定

ルール:
- 年齢時点の事実: 70-100%（推奨80%）
- その後の事実: 0-30%（推奨20%）
"""

import re
from typing import Dict, List, Tuple
from dataclasses import dataclass


@dataclass
class DistributionAnalysis:
    """配分分析結果"""
    age_specific_percentage: float
    subsequent_percentage: float
    compliant: bool
    age_specific_sentences: List[str]
    subsequent_sentences: List[str]
    age_specific_chars: int
    subsequent_chars: int
    total_chars: int


class ContentDistributionChecker:
    """エピソード内容の配分を測定"""

    # 年齢時点を示すマーカー
    AGE_MARKERS = [
        r'のとき',
        r'で',
        r'この年',
        r'当時',
        r'同年',
        r'その年',
        r'初年度',
        r'デビュー',
        r'創業',
    ]

    # その後を示すマーカー（これがあれば年齢時点ではない）
    SUBSEQUENT_MARKERS = [
        r'後に',
        r'その後',
        r'最終的に',
        r'現在',
        r'今では',
        r'やがて',
        r'将来',
        r'後の',
        r'のちに',
        r'生涯で',
        r'通算',
        r'累計',
        r'合計.*(?:勝|本|回|冠)',
        # 追加: スポーツ通算記録
        r'メジャー通算',
        r'日米通算',
        r'ツアー通算',
        r'プロ通算',
        # 追加: 生涯成果
        r'生涯獲得',
        r'総額.*(?:億円|兆円)',
        r'年俸総額',
        # 追加: 永久的な評価
        r'永久欠番',
        r'殿堂入り',
        # 追加: 現在の状態
        r'現在.*(?:億円|兆円|ドル)',
    ]

    # 未来の成果を示すパターン
    FUTURE_ACHIEVEMENT_PATTERNS = [
        r'\d+年後',
        r'\d+年で',
        r'\d+回(?:出場|受賞|獲得|達成)',
        r'\d+本(?:出演|制作|公開)',
        r'(?:配信|ダウンロード)\s*\d+(?:万|億)',
        r'(?:YouTube|再生|視聴)\s*\d+億',
        r'紅白.*?\d+回',
        r'映画.*?\d+本',
    ]

    def __init__(self):
        self.min_age_percentage = 70.0  # 最低70%
        self.max_subsequent_percentage = 30.0  # 最大30%

    def analyze_distribution(self, episode_text: str, age: int) -> DistributionAnalysis:
        """
        年齢時点の事実 vs その後の事実の配分を分析

        Args:
            episode_text: エピソードテキスト
            age: 年齢

        Returns:
            DistributionAnalysis: 配分分析結果
        """
        # 文を分割
        sentences = self.split_sentences(episode_text)

        age_specific = []
        subsequent = []

        for sentence in sentences:
            if self.is_age_specific(sentence, age):
                age_specific.append(sentence)
            else:
                subsequent.append(sentence)

        total_chars = len(episode_text)
        age_chars = sum(len(s) for s in age_specific)
        sub_chars = sum(len(s) for s in subsequent)

        age_percentage = (age_chars / total_chars * 100) if total_chars > 0 else 0
        sub_percentage = (sub_chars / total_chars * 100) if total_chars > 0 else 0

        # 年齢時点が70%以上かつ、その後が30%以下
        compliant = (age_percentage >= self.min_age_percentage and
                    sub_percentage <= self.max_subsequent_percentage)

        return DistributionAnalysis(
            age_specific_percentage=age_percentage,
            subsequent_percentage=sub_percentage,
            compliant=compliant,
            age_specific_sentences=age_specific,
            subsequent_sentences=subsequent,
            age_specific_chars=age_chars,
            subsequent_chars=sub_chars,
            total_chars=total_chars
        )

    def split_sentences(self, text: str) -> List[str]:
        """テキストを文に分割"""
        # 句点で分割
        sentences = re.split(r'[。\.]', text)
        # 空文字を除外
        sentences = [s.strip() for s in sentences if s.strip()]
        return sentences

    def is_age_specific(self, sentence: str, age: int) -> bool:
        """
        文が年齢時点の事実かどうかを判定

        Args:
            sentence: 判定する文
            age: 年齢

        Returns:
            bool: 年齢時点の事実ならTrue
        """
        # その後のマーカーがあれば即座にFalse
        for marker in self.SUBSEQUENT_MARKERS:
            if re.search(marker, sentence):
                return False

        # 未来の成果パターンがあれば即座にFalse
        for pattern in self.FUTURE_ACHIEVEMENT_PATTERNS:
            if re.search(pattern, sentence):
                return False

        # 年齢時点のマーカーがあればTrue
        for marker in self.AGE_MARKERS:
            if re.search(marker, sentence):
                return True

        # どちらもない場合、文脈から判定
        return self.judge_by_context(sentence, age)

    def judge_by_context(self, sentence: str, age: int) -> bool:
        """
        文脈から年齢時点の事実かどうかを判定

        Args:
            sentence: 判定する文
            age: 年齢

        Returns:
            bool: 年齢時点の事実ならTrue
        """
        # 具体的な数値データがある場合は年齢時点と判定
        if re.search(r'\d+(?:円|ドル|万|億|%|点|位|回|本|人)', sentence):
            return True

        # 過去形の動詞がある場合は年齢時点と判定
        past_tense_verbs = ['した', 'した。', 'だった', 'になった', '成し遂げた', '達成した']
        for verb in past_tense_verbs:
            if verb in sentence:
                return True

        # 歴史的評価を示す表現があれば「その後」と判定
        historical_expressions = ['歴史', '伝説', '偉業', '記録', '功績']
        for expr in historical_expressions:
            if expr in sentence:
                return False

        # デフォルトは年齢時点と判定（保守的）
        return True

    def get_compliance_report(self, analysis: DistributionAnalysis) -> str:
        """
        配分の適合性レポートを生成

        Args:
            analysis: 配分分析結果

        Returns:
            str: レポート文字列
        """
        status = "✅ 合格" if analysis.compliant else "❌ 不合格"

        report = f"""
配分チェック結果: {status}

年齢時点の事実: {analysis.age_specific_percentage:.1f}% ({analysis.age_specific_chars}文字)
その後の事実: {analysis.subsequent_percentage:.1f}% ({analysis.subsequent_chars}文字)
総文字数: {analysis.total_chars}文字

基準:
- 年齢時点の事実: 70%以上 → {"✅" if analysis.age_specific_percentage >= 70 else "❌"}
- その後の事実: 30%以下 → {"✅" if analysis.subsequent_percentage <= 30 else "❌"}

年齢時点の文:
{self._format_sentences(analysis.age_specific_sentences)}

その後の文:
{self._format_sentences(analysis.subsequent_sentences)}
"""
        return report

    def _format_sentences(self, sentences: List[str]) -> str:
        """文のリストをフォーマット"""
        if not sentences:
            return "  (なし)"
        return "\n".join(f"  - {s}" for s in sentences)


def test_distribution_checker():
    """配分チェッカーのテスト"""
    checker = ContentDistributionChecker()

    # テストケース1: 良い配分（80:20）
    print("=" * 80)
    print("テストケース1: 良い配分（80:20）")
    print("=" * 80)

    good_episode = """あなたと同じ30歳のとき、ジェフ・ベゾスはヘッジファンドの副社長職を辞め、妻とともに車でアメリカを横断。移動中にノートパソコンでビジネスプランを書き、シアトルのガレージでオンライン書店Amazonを創業した。初年度の売上は51万ドルを記録。自ら本の梱包作業を行い、注文が入るたびに鳴るベルの音が励みになった。この年、20カ国への配送を実現。ウォールストリート・ジャーナルが『インターネット書店の先駆者』として取り上げた。"""

    analysis = checker.analyze_distribution(good_episode, 30)
    print(checker.get_compliance_report(analysis))

    # テストケース2: 悪い配分（60:40）
    print("\n" + "=" * 80)
    print("テストケース2: 悪い配分（60:40）")
    print("=" * 80)

    bad_episode = """あなたと同じ30歳のとき、ジェフ・ベゾスはAmazonを創業した。ガレージで本の梱包を始めた。後に世界最大のEC企業となり、時価総額1.5兆ドルを達成。クラウドサービスAWSも展開し、世界を変えた。現在では従業員150万人を抱え、年間売上50兆円を超える巨大企業に成長した。"""

    analysis = checker.analyze_distribution(bad_episode, 30)
    print(checker.get_compliance_report(analysis))

    # テストケース3: 現在のジェフ・ベゾスエピソード（Amazon Prime）
    print("\n" + "=" * 80)
    print("テストケース3: 現在のAmazon Primeエピソード")
    print("=" * 80)

    current_episode = """あなたと同じ35歳のとき、ジェフ・ベゾスはAmazonPrimeサービスを開始し、年会費79ドルで無制限の2日間配送を実現した。会員数は初年度で100万人を突破し、顧客満足度97%を記録した。オンライン書店から総合ECへの転換を果たし、小売業界に革命をもたらした。この新サービスは顧客ロイヤルティの概念を変えた。"""

    analysis = checker.analyze_distribution(current_episode, 35)
    print(checker.get_compliance_report(analysis))


if __name__ == '__main__':
    test_distribution_checker()
