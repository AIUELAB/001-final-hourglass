#!/usr/bin/env python3
"""
RULE_175: ネガティブエピソード評価（Negative Episode Evaluation）

転落・挫折エピソードの適切性を評価
- センセーショナリズムの検出（過度に刺激的な表現）
- 教訓的価値の評価
- 倫理的配慮のチェック
- 人権尊重の確認

評価基準:
✅ 適切: 教訓的価値があり、事実ベースで冷静な記述
❌ 不適切: センセーショナル、侮辱的、プライバシー侵害

例:
- ✅ 「証券取引法違反で逮捕され、実刑判決を受けた」
- ❌ 「悪質な詐欺師として世間から糾弾された」
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import re
import logging

logger = logging.getLogger(__name__)


@dataclass
class NegativeIssue:
    """ネガティブな問題"""
    severity: str  # CRITICAL, WARNING, INFO
    issue_type: str  # sensationalism, disrespect, privacy, bias
    message: str
    evidence: str
    suggestion: str


class NegativeEpisodeEvaluator:
    """
    ネガティブエピソード評価エンジン

    転落・挫折エピソードの適切性を評価
    """

    # センセーショナルな表現（過度に刺激的）
    SENSATIONAL_EXPRESSIONS = [
        "悪質", "卑劣", "最低", "最悪", "糾弾", "非難の嵐",
        "炎上", "バッシング", "叩かれ", "批判殺到", "大炎上",
        "世間から", "社会から", "国民から", "全国から"
    ]

    # 侮辱的・差別的表現
    DISRESPECTFUL_EXPRESSIONS = [
        "愚か", "馬鹿", "間抜け", "無能", "クズ", "ゴミ",
        "最低の人間", "人間のクズ", "社会の敵", "恥"
    ]

    # プライバシー侵害の可能性
    PRIVACY_CONCERNS = [
        "家族が", "妻が", "夫が", "子供が", "親が", "自宅",
        "住所", "電話番号", "個人情報", "プライベート"
    ]

    # 適切な客観的表現
    OBJECTIVE_EXPRESSIONS = [
        "逮捕", "起訴", "有罪", "判決", "辞任", "引退",
        "謝罪", "説明", "発表", "記者会見", "報道", "報じ"
    ]

    # 教訓的価値を示すキーワード
    EDUCATIONAL_VALUE = [
        "教訓", "学び", "反省", "再起", "復活", "乗り越え",
        "成長", "経験", "挫折から", "失敗を", "困難を"
    ]

    def __init__(self):
        """初期化"""
        pass

    def detect_sensationalism(self, text: str) -> List[NegativeIssue]:
        """
        センセーショナリズムを検出

        Args:
            text: エピソードテキスト

        Returns:
            検出された問題のリスト
        """
        issues = []

        for expression in self.SENSATIONAL_EXPRESSIONS:
            if expression in text:
                issues.append(
                    NegativeIssue(
                        severity="WARNING",
                        issue_type="sensationalism",
                        message=f"センセーショナルな表現: 「{expression}」",
                        evidence=expression,
                        suggestion="より客観的で事実ベースの表現に変更"
                    )
                )

        return issues

    def detect_disrespect(self, text: str) -> List[NegativeIssue]:
        """
        侮辱的・差別的表現を検出

        Args:
            text: エピソードテキスト

        Returns:
            検出された問題のリスト
        """
        issues = []

        for expression in self.DISRESPECTFUL_EXPRESSIONS:
            if expression in text:
                issues.append(
                    NegativeIssue(
                        severity="CRITICAL",
                        issue_type="disrespect",
                        message=f"侮辱的表現: 「{expression}」",
                        evidence=expression,
                        suggestion="人権を尊重した表現に変更（削除推奨）"
                    )
                )

        return issues

    def detect_privacy_concerns(self, text: str) -> List[NegativeIssue]:
        """
        プライバシー侵害の可能性を検出

        Args:
            text: エピソードテキスト

        Returns:
            検出された問題のリスト
        """
        issues = []

        for expression in self.PRIVACY_CONCERNS:
            if expression in text:
                issues.append(
                    NegativeIssue(
                        severity="WARNING",
                        issue_type="privacy",
                        message=f"プライバシー懸念: 「{expression}」",
                        evidence=expression,
                        suggestion="本人以外の情報削除を検討"
                    )
                )

        return issues

    def evaluate_objectivity(self, text: str) -> int:
        """
        客観性スコアを評価

        Args:
            text: エピソードテキスト

        Returns:
            客観性スコア（0-100）
        """
        score = 50  # ベーススコア

        # 客観的表現のカウント
        objective_count = sum(1 for expr in self.OBJECTIVE_EXPRESSIONS if expr in text)
        score += min(objective_count * 10, 30)  # 最大+30点

        # センセーショナルな表現のペナルティ
        sensational_count = sum(1 for expr in self.SENSATIONAL_EXPRESSIONS if expr in text)
        score -= sensational_count * 15  # -15点/個

        # 侮辱的表現のペナルティ
        disrespect_count = sum(1 for expr in self.DISRESPECTFUL_EXPRESSIONS if expr in text)
        score -= disrespect_count * 30  # -30点/個（重大）

        return max(0, min(score, 100))

    def evaluate_educational_value(self, text: str) -> int:
        """
        教訓的価値を評価

        Args:
            text: エピソードテキスト

        Returns:
            教訓的価値スコア（0-100）
        """
        score = 30  # ベーススコア（事実記述の基本価値）

        # 教訓的キーワードのカウント
        educational_count = sum(1 for expr in self.EDUCATIONAL_VALUE if expr in text)
        score += min(educational_count * 20, 60)  # 最大60点

        # 社会的影響や歴史的意義の記述
        if any(word in text for word in ["影響", "変化", "結果", "衝撃", "波紋"]):
            score += 10

        # 再起・復活の要素
        if any(word in text for word in ["再起", "復活", "乗り越え", "克服"]):
            score += 10

        return min(score, 100)

    def evaluate(
        self,
        episode_text: str,
        person_name: str = ""
    ) -> Dict:
        """
        ネガティブエピソードを評価

        Args:
            episode_text: エピソードテキスト
            person_name: 人物名（オプション）

        Returns:
            評価結果
        """
        issues = []

        # 各種問題を検出
        issues.extend(self.detect_sensationalism(episode_text))
        issues.extend(self.detect_disrespect(episode_text))
        issues.extend(self.detect_privacy_concerns(episode_text))

        # 重大度でソート
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        issues.sort(key=lambda x: severity_order[x.severity])

        # スコア評価
        objectivity_score = self.evaluate_objectivity(episode_text)
        educational_score = self.evaluate_educational_value(episode_text)

        # 総合スコア（客観性60%、教訓的価値40%）
        total_score = objectivity_score * 0.6 + educational_score * 0.4

        # 判定基準
        critical_count = sum(1 for i in issues if i.severity == "CRITICAL")
        warning_count = sum(1 for i in issues if i.severity == "WARNING")

        # CRITICALがゼロ、かつ総合スコア60点以上で合格
        passed = (critical_count == 0) and (total_score >= 60)

        if person_name:
            logger.info(f"📊 {person_name} ネガティブエピソード評価:")
            logger.info(f"   客観性スコア: {objectivity_score:.1f}点")
            logger.info(f"   教訓的価値: {educational_score:.1f}点")
            logger.info(f"   総合スコア: {total_score:.1f}点")
            logger.info(f"   問題数: CRITICAL={critical_count}, WARNING={warning_count}")

        return {
            "passed": passed,
            "total_score": total_score,
            "objectivity_score": objectivity_score,
            "educational_score": educational_score,
            "issues": [
                {
                    "severity": i.severity,
                    "type": i.issue_type,
                    "message": i.message,
                    "evidence": i.evidence,
                    "suggestion": i.suggestion
                }
                for i in issues
            ],
            "critical_count": critical_count,
            "warning_count": warning_count,
            "rule_id": "RULE_175",
            "rule_name": "ネガティブエピソード評価"
        }


# グローバル評価エンジン
negative_evaluator = NegativeEpisodeEvaluator()


def evaluate_negative_episode(
    episode_text: str,
    person_name: str = ""
) -> Dict:
    """
    ネガティブエピソードを評価（外部インターフェース）

    Args:
        episode_text: エピソードテキスト
        person_name: 人物名

    Returns:
        評価結果
    """
    return negative_evaluator.evaluate(episode_text, person_name)


if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # テストケース
    test_cases = [
        {
            "person": "堀江貴文（適切な例）",
            "text": "あなたと同じ38歳のとき、堀江貴文は証券取引法違反で逮捕された。24歳で起業したオン・ザ・エッヂは2000年に売上高100億円、株価100倍に成長しライブドアに改称。ニッポン放送買収、プロ野球参入など次々と挑戦したが、株式分割を繰り返した資金調達が法に抵触し実刑判決を受けた。時代の寵児の転落は日本経済界に衝撃を与えた。"
        },
        {
            "person": "架空の人物（センセーショナル）",
            "text": "あなたと同じ30歳のとき、悪質な詐欺師として世間から糾弾され、全国から非難の嵐を浴びた。最低の人間として社会から追放され、家族も恥をかき、自宅には嫌がらせが殺到した。"
        },
        {
            "person": "架空の人物（教訓的）",
            "text": "あなたと同じ35歳のとき、業績不振で社長を辞任した。しかし、この失敗から多くの教訓を学び、3年後に再起を果たした。挫折を乗り越えた経験が、その後の成功の礎となった。"
        }
    ]

    print("=" * 80)
    print("RULE_175: ネガティブエピソード評価 - テスト実行")
    print("=" * 80)
    print()

    for i, test in enumerate(test_cases, 1):
        print(f"テストケース {i}: {test['person']}")
        print(f"  テキスト: {test['text'][:60]}...")
        print()

        result = evaluate_negative_episode(
            test["text"],
            test["person"]
        )

        status = "✅ 適切" if result["passed"] else "❌ 不適切"
        print(f"  {status}")
        print(f"  📊 総合スコア: {result['total_score']:.1f}点")
        print(f"  📈 客観性: {result['objectivity_score']:.1f}点")
        print(f"  📚 教訓的価値: {result['educational_score']:.1f}点")
        print(f"  🔴 重大な問題: {result['critical_count']}件")
        print(f"  🟡 警告: {result['warning_count']}件")

        if result["issues"]:
            print(f"  📋 検出された問題:")
            for issue in result["issues"]:
                severity_emoji = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "ℹ️"}
                print(f"     {severity_emoji[issue['severity']]} [{issue['type']}] {issue['message']}")
                print(f"        提案: {issue['suggestion']}")
        print()

    print("=" * 80)
    print("✅ テスト完了")
    print("=" * 80)
