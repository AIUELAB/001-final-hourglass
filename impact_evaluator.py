#!/usr/bin/env python3
"""
感情的インパクト評価器（Impact Evaluator）
エピソードの感情的インパクトを5項目で評価

評価項目（各10点満点、合計50点）:
1. 人生の転換点スコア（Turning Point Score）
2. 意外性スコア（Surprise Score）
3. リスクテイキングスコア（Risk-Taking Score）
4. 共感性スコア（Relatability Score）
5. センセーショナル度（Sensational Score）

合格基準: 30点以上（60%）
"""

import re
from typing import Dict, List
from dataclasses import dataclass


@dataclass
class ImpactScore:
    """インパクトスコア"""
    turning_point: int
    surprise: int
    risk_taking: int
    relatability: int
    sensational: int
    total: int
    passed: bool  # 40点以上で合格


class ImpactEvaluator:
    """感情的インパクト評価器"""

    # 人生の転換点キーワード
    TURNING_POINT_KEYWORDS = {
        10: [
            # 既存
            '辞職', '引退', '退職', '全財産', '人生を賭け', '中退', 'すべてを捨て',
            # 栄誉・賞
            'ノーベル賞', '芥川賞', '直木賞', 'アカデミー賞', 'カンヌ国際映画祭',
            # 事件・スキャンダル
            '逮捕', '上場廃止', '有罪', '辞任', '解任',
            # スポーツ最高峰
            'ワールドシリーズMVP', 'オリンピック.*?金メダル', '世界選手権.*?優勝',
            # 創設・設立
            '創設', '設立', '創刊', '開校',
            # 音楽・芸能の最高峰
            '紅白歌合戦.*?出場', '紅白.*?出場',
        ],
        7: [
            # 既存
            '転職', '起業', '創業', '移住', '決断', 'デビュー',
            # 栄誉・選出
            '受賞', '優勝', '選出', '就任', 'MVP',
            # スポーツ記録
            '金メダル', '世界記録', '日本記録', '初優勝', '連覇',
            # 音楽・芸能での成功
            'Billboard.*?1位', 'Billboard.*?年間1位', 'チャート.*?1位',
            '海外進出', '海外公演', '武道館', '東京ドーム', 'ドームツアー',
            # 新しいモデル・スタイルの確立
            '確立した', 'モデルを確立', 'スタイルを確立',
            # 業界や社会への影響
            '変革', '革命', '再定義', '市場を創出',
        ],
        4: ['新事業', '新プロジェクト', '挑戦', '開始', '完売'],
        0: ['通常業務', '定期', '日常']
    }

    # 意外性キーワード
    SURPRISE_KEYWORDS = {
        10: [
            # 既存
            'ガレージで', 'エリートが', '誰も予想しなかった', '常識を覆', '前例のない',
            # 驚きの経歴
            'ボクサー.*?建築家', '医師.*?研究者', '独学', '学歴.*?ない',
            # 異例の展開
            '周囲.*?反対', '無謀', '不可能.*?言われ',
            # 匿名・覆面での成功
            '顔を公開せず', '匿名', '覆面', '素顔.*?明かさず', '正体不明',
            # 新しいモデル・概念
            '新しい.*?モデル', '新しい.*?形態', '新しい成功モデル',
        ],
        7: [
            # 既存
            '初めて', '史上最年少', '史上初', '日本人初', '世界初',
            # 記録
            '最年少', '最年長', '最速', '最短',
            # 性別初・期間ぶり
            '女子初', '男子初', '女性初', '男性初',
            '年ぶり', '〜ぶり', 'ぶりの', 'ぶりと', '以来',
        ],
        4: ['業界初', '国内初', '新しい'],
        0: ['順当に', '予想通り', '計画通り']
    }

    # リスクテイキングキーワード
    RISK_KEYWORDS = {
        10: ['年収.*?を捨て', '年収.*?円.*?を辞め', '全財産を投資', '無一文', 'すべてを失', '借金'],
        7: ['安定を捨て', '辞めて', '中退', '退職', '辞め', '副社長.*?辞め'],
        4: ['新分野に挑戦', 'リスクを取', '挑戦的', '前例のない.*?挑戦'],
        0: ['既存事業で', '安全に', '確実に']
    }

    # 共感性キーワード
    RELATABILITY_KEYWORDS = {
        10: ['安定.*?夢', '失敗の恐怖', '周囲の反対', '誰もが', '迷い', '葛藤', '反対した'],
        7: ['キャリアの選択', '人生の岐路', '決断', '挫折', '横断', '妻とともに', '若者.*?支持', '若い世代', '感動', '世界中.*?感動', '涙'],
        4: ['仕事の挑戦', '新しい道', '支持を集め', '共感', '魅了'],
        0: ['大企業の戦略', '投資判断', 'M&A']
    }

    # センセーショナルキーワード
    SENSATIONAL_KEYWORDS = {
        10: [
            # 既存
            '車で横断しながら', '車でアメリカを横断', 'ガレージから世界企業', 'ガレージで',
            '伝説', 'ドラマ', '奇跡', 'ノートパソコンで',
            # 事件・スキャンダル
            '逮捕', 'スキャンダル', '疑惑', '事件',
            # 栄誉（特に世界的）
            'ノーベル賞', 'アカデミー賞', 'カンヌ',
            # 記録・偉業
            '日本人初', '史上初', '世界初', '歴史的', '世界記録',
            # 年齢記録
            '最年少', '最年長',
            # 音楽・芸能での象徴的な成功
            '紅白歌合戦', '紅白', 'Billboard', '新時代.*?象徴', '時代.*?象徴',
        ],
        7: [
            # 既存
            '劇的な転換', '常識を覆す', '革命', '衝撃', '手作り', '自ら.*?作業',
            # 栄誉
            '芥川賞', '直木賞', 'MVP', '金メダル',
            # インパクト
            '上場廃止', '解任', '辞任',
            # 音楽シーンでのインパクト
            '音楽シーン', '匿名アーティスト', '新しいスタイル',
            # スポーツでの記録的成功
            '連覇', '〜ぶり', '年ぶり', '偉業', '巻き返し',
        ],
        4: ['注目を集めた', '話題', '人気', '先駆者', '広範な支持'],
        0: ['通常の', '標準的な', '一般的']
    }

    def __init__(self):
        self.min_passing_score = 30  # 50点満点中30点で合格（60%）

    def evaluate(self, episode_text: str, person_name: str, age: int) -> ImpactScore:
        """
        エピソードの感情的インパクトを評価

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名
            age: 年齢

        Returns:
            ImpactScore: インパクトスコア
        """
        turning_point = self.score_turning_point(episode_text)
        surprise = self.score_surprise(episode_text)
        risk_taking = self.score_risk_taking(episode_text)
        relatability = self.score_relatability(episode_text)
        sensational = self.score_sensational(episode_text)

        total = turning_point + surprise + risk_taking + relatability + sensational
        passed = total >= self.min_passing_score

        return ImpactScore(
            turning_point=turning_point,
            surprise=surprise,
            risk_taking=risk_taking,
            relatability=relatability,
            sensational=sensational,
            total=total,
            passed=passed
        )

    def score_turning_point(self, text: str) -> int:
        """
        人生の転換点スコア（0-10点）

        10点: 人生を賭けた決断（辞職、引退、全財産）
        7点: 重要な決断（転職、起業、移住）
        4点: 重要だが予想可能（新事業、挑戦）
        0点: 日常業務の延長
        """
        return self._score_by_keywords(text, self.TURNING_POINT_KEYWORDS)

    def score_surprise(self, text: str) -> int:
        """
        意外性スコア（0-10点）

        10点: 常識を覆す行動（ガレージで、エリートが）
        7点: 前例のない挑戦（史上初、最年少）
        4点: 業界標準を超える（業界初）
        0点: 当然の結果（順当、予想通り）
        """
        return self._score_by_keywords(text, self.SURPRISE_KEYWORDS)

    def score_risk_taking(self, text: str) -> int:
        """
        リスクテイキングスコア（0-10点）

        10点: 全てを失うリスク（年収捨てる、全財産、無一文）
        7点: 大きなリスク（安定を捨て、中退）
        4点: 計算されたリスク（新分野挑戦）
        0点: リスクなし（既存事業、安全）
        """
        return self._score_by_keywords(text, self.RISK_KEYWORDS)

    def score_relatability(self, text: str) -> int:
        """
        共感性スコア（0-10点）

        10点: 誰もが経験する葛藤（安定vs夢、失敗の恐怖）
        7点: 一部が経験する選択（キャリア、人生の岐路）
        4点: 特定の人が経験（仕事の挑戦）
        0点: 一般人に無関係（大企業戦略、M&A）
        """
        return self._score_by_keywords(text, self.RELATABILITY_KEYWORDS)

    def score_sensational(self, text: str) -> int:
        """
        センセーショナル度（0-10点）

        10点: 映画になりそう（車で横断、ガレージから世界へ）
        7点: 劇的な展開（常識を覆す、革命）
        4点: 興味深い（注目、話題）
        0点: ニュース価値なし（通常、標準的）
        """
        return self._score_by_keywords(text, self.SENSATIONAL_KEYWORDS)

    def _score_by_keywords(self, text: str, keyword_dict: Dict[int, List[str]]) -> int:
        """
        キーワードマッチングでスコアリング

        Args:
            text: テキスト
            keyword_dict: {スコア: [キーワードリスト]}

        Returns:
            int: スコア（0-10）
        """
        # 高いスコアから順にチェック
        for score in sorted(keyword_dict.keys(), reverse=True):
            keywords = keyword_dict[score]
            for keyword in keywords:
                if re.search(keyword, text):
                    return score
        return 0

    def get_impact_report(self, score: ImpactScore, person_name: str, age: int) -> str:
        """
        インパクト評価レポートを生成

        Args:
            score: インパクトスコア
            person_name: 人物名
            age: 年齢

        Returns:
            str: レポート文字列
        """
        status = "✅ 合格" if score.passed else "❌ 不合格"
        percentage = (score.total / 50) * 100

        report = f"""
感情的インパクト評価: {status}

人物: {person_name}（{age}歳）
総合スコア: {score.total}/50点（{percentage:.0f}%）

詳細スコア:
  1. 人生の転換点: {score.turning_point}/10点 {"★" * score.turning_point}
  2. 意外性: {score.surprise}/10点 {"★" * score.surprise}
  3. リスクテイキング: {score.risk_taking}/10点 {"★" * score.risk_taking}
  4. 共感性: {score.relatability}/10点 {"★" * score.relatability}
  5. センセーショナル度: {score.sensational}/10点 {"★" * score.sensational}

合格基準: 30点以上（60%）
結果: {"✅ 合格" if score.passed else f"❌ 不合格（あと{30 - score.total}点必要）"}
"""
        return report


def test_impact_evaluator():
    """インパクト評価器のテスト"""
    evaluator = ImpactEvaluator()

    # テストケース1: ガレージ創業エピソード（高インパクト）
    print("=" * 80)
    print("テストケース1: ジェフ・ベゾス - ガレージ創業（30歳）")
    print("=" * 80)

    garage_episode = """あなたと同じ30歳のとき、ジェフ・ベゾスはヘッジファンドの副社長職（年収数千万円）を辞め、妻とともに車でアメリカを横断。移動中にノートパソコンでビジネスプランを書き、シアトルのガレージでオンライン書店Amazonを創業した。初年度の売上は51万ドルを記録。自ら本の梱包作業を行い、注文が入るたびに鳴るベルの音が励みになった。この年、20カ国への配送を実現。ウォールストリート・ジャーナルが『インターネット書店の先駆者』として取り上げた。"""

    score = evaluator.evaluate(garage_episode, "ジェフ・ベゾス", 30)
    print(evaluator.get_impact_report(score, "ジェフ・ベゾス", 30))

    # テストケース2: Amazon Primeエピソード（低インパクト）
    print("\n" + "=" * 80)
    print("テストケース2: ジェフ・ベゾス - Amazon Prime開始（35歳）")
    print("=" * 80)

    prime_episode = """あなたと同じ35歳のとき、ジェフ・ベゾスはAmazonPrimeサービスを開始し、年会費79ドルで無制限の2日間配送を実現した。会員数は初年度で100万人を突破し、顧客満足度97%を記録した。オンライン書店から総合ECへの転換を果たし、小売業界に革命をもたらした。この新サービスは顧客ロイヤルティの概念を変えた。"""

    score = evaluator.evaluate(prime_episode, "ジェフ・ベゾス", 35)
    print(evaluator.get_impact_report(score, "ジェフ・ベゾス", 35))

    # テストケース3: スティーブ・ジョブズ - Apple創業（21歳）
    print("\n" + "=" * 80)
    print("テストケース3: スティーブ・ジョブズ - Apple創業（21歳）")
    print("=" * 80)

    jobs_episode = """あなたと同じ21歳のとき、スティーブ・ジョブズはリード大学を中退後、両親のガレージでスティーブ・ウォズニアックとApple Computerを創業した。初代Appleコンピューターを手作りし、地元の電子部品店に50台を666.66ドルで売り込んだ。大学中退という決断に周囲は反対したが、この年、売上8万ドルを記録した。パーソナルコンピューター革命の第一歩となった。"""

    score = evaluator.evaluate(jobs_episode, "スティーブ・ジョブズ", 21)
    print(evaluator.get_impact_report(score, "スティーブ・ジョブズ", 21))


if __name__ == '__main__':
    test_impact_evaluator()
