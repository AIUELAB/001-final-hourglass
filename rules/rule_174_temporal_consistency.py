#!/usr/bin/env python3
"""
RULE_174: 時系列整合性検証（Temporal Consistency Verification）

エピソードの時系列的な矛盾を検出
- 年齢と出来事の時期が一致するか
- 歴史的事実との整合性
- 物理的に不可能な時系列の検出

検出例:
- ❌ 「20歳でノーベル賞受賞」→ 最年少受賞は25歳
- ❌ 「1990年にスマートフォン開発」→ iPhoneは2007年
- ❌ 「15歳でMLB MVP」→ 最年少MVPは20歳
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class TemporalInconsistency:
    """時系列的矛盾"""
    severity: str  # CRITICAL, WARNING, INFO
    message: str
    evidence: str  # 矛盾の証拠となるテキスト
    suggestion: str  # 修正提案


class TemporalConsistencyChecker:
    """
    時系列整合性チェッカー

    エピソードの時系列的な矛盾を検出
    """

    # 最年少記録（知られている最小年齢）
    MIN_AGE_RECORDS = {
        "ノーベル": 25,  # マララ・ユスフザイ（平和賞）
        "オリンピック金メダル": 13,  # 岩崎恭子（競泳）
        "金メダル": 13,
        "MVP": 20,  # 大リーグMVP
        "首相": 39,  # 安倍晋三（初就任時）
        "社長": 18,  # 起業家
        "博士号": 18,  # 最年少記録
    }

    # 最高齢記録（知られている最大年齢）
    MAX_AGE_RECORDS = {
        "現役選手": 60,  # 一般的な上限
        "金メダル": 65,  # 射撃など
    }

    # 年代と技術の整合性
    TECHNOLOGY_TIMELINE = {
        "インターネット": 1990,
        "スマートフォン": 2007,  # iPhone発売
        "YouTube": 2005,
        "Twitter": 2006,
        "Instagram": 2010,
        "TikTok": 2016,
        "AI": 1950,  # 概念の登場
        "ディープラーニング": 2012,
    }

    def __init__(self):
        """初期化"""
        pass

    def extract_year_from_text(self, text: str) -> Optional[int]:
        """
        テキストから年を抽出

        Args:
            text: テキスト

        Returns:
            年（見つからなければNone）
        """
        # パターン: "2021年"、"2021年シーズン"
        year_pattern = r'(\d{4})年'
        match = re.search(year_pattern, text)
        if match:
            return int(match.group(1))

        return None

    def check_age_consistency(
        self,
        age: int,
        achievement: str,
        text: str
    ) -> Optional[TemporalInconsistency]:
        """
        年齢と業績の整合性をチェック

        Args:
            age: 年齢
            achievement: 業績（ダミー、textを使用）
            text: エピソード本文

        Returns:
            矛盾があればTemporalInconsistency、なければNone
        """
        # 最年少記録チェック
        for keyword, min_age in self.MIN_AGE_RECORDS.items():
            # キーワードをより広くチェック（部分一致）
            if keyword in text:
                if age < min_age:
                    return TemporalInconsistency(
                        severity="CRITICAL",
                        message=f"{age}歳で{keyword}は不可能（最年少記録: {min_age}歳）",
                        evidence=f"{age}歳、{keyword}",
                        suggestion=f"年齢を{min_age}歳以上に修正するか、業績内容を見直す"
                    )

        # 最高齢記録チェック
        for keyword, max_age in self.MAX_AGE_RECORDS.items():
            if keyword in achievement or keyword in text:
                if age > max_age:
                    return TemporalInconsistency(
                        severity="WARNING",
                        message=f"{age}歳で{keyword}は稀（一般的上限: {max_age}歳）",
                        evidence=f"{age}歳、{keyword}",
                        suggestion=f"事実確認を推奨（{max_age}歳を超える例外的ケース）"
                    )

        return None

    def check_technology_timeline(
        self,
        text: str
    ) -> List[TemporalInconsistency]:
        """
        技術の年代整合性をチェック

        Args:
            text: エピソード本文

        Returns:
            矛盾のリスト
        """
        inconsistencies = []

        # 年を抽出
        year = self.extract_year_from_text(text)
        if year is None:
            return inconsistencies

        # 技術タイムラインチェック
        for tech, intro_year in self.TECHNOLOGY_TIMELINE.items():
            if tech in text and year < intro_year:
                inconsistencies.append(
                    TemporalInconsistency(
                        severity="CRITICAL",
                        message=f"{year}年に{tech}は存在しない（登場: {intro_year}年）",
                        evidence=f"{year}年、{tech}",
                        suggestion=f"年を{intro_year}年以降に修正するか、技術名を変更"
                    )
                )

        return inconsistencies

    def check_person_birth_year(
        self,
        person_name: str,
        age: int,
        text: str,
        birth_year: Optional[int] = None
    ) -> Optional[TemporalInconsistency]:
        """
        人物の生年と年齢の整合性をチェック

        Args:
            person_name: 人物名
            age: エピソードの年齢
            text: エピソード本文
            birth_year: 生年（判明している場合）

        Returns:
            矛盾があればTemporalInconsistency、なければNone
        """
        if birth_year is None:
            return None

        # テキストから年を抽出
        year = self.extract_year_from_text(text)
        if year is None:
            return None

        # 年齢の整合性チェック
        expected_age = year - birth_year
        age_diff = abs(expected_age - age)

        if age_diff > 2:  # 2歳以上のズレは疑わしい
            return TemporalInconsistency(
                severity="WARNING",
                message=f"{year}年に{age}歳は矛盾（生年{birth_year}年なら{expected_age}歳）",
                evidence=f"{person_name}、{year}年、{age}歳、生年{birth_year}",
                suggestion=f"年齢を{expected_age}歳に修正、または年を{birth_year + age}年に修正"
            )

        return None

    def verify(
        self,
        person_name: str,
        age: int,
        episode_text: str,
        birth_year: Optional[int] = None
    ) -> Dict:
        """
        時系列整合性を検証

        Args:
            person_name: 人物名
            age: 年齢
            episode_text: エピソード本文
            birth_year: 生年（オプション）

        Returns:
            検証結果
        """
        inconsistencies = []

        # 年齢と業績の整合性チェック
        age_issue = self.check_age_consistency(age, episode_text, episode_text)
        if age_issue:
            inconsistencies.append(age_issue)

        # 技術タイムラインチェック
        tech_issues = self.check_technology_timeline(episode_text)
        inconsistencies.extend(tech_issues)

        # 生年との整合性チェック
        if birth_year:
            birth_issue = self.check_person_birth_year(
                person_name, age, episode_text, birth_year
            )
            if birth_issue:
                inconsistencies.append(birth_issue)

        # 重大度でソート
        severity_order = {"CRITICAL": 0, "WARNING": 1, "INFO": 2}
        inconsistencies.sort(key=lambda x: severity_order[x.severity])

        # 判定
        critical_count = sum(1 for i in inconsistencies if i.severity == "CRITICAL")
        warning_count = sum(1 for i in inconsistencies if i.severity == "WARNING")

        passed = critical_count == 0

        return {
            "passed": passed,
            "inconsistencies": [
                {
                    "severity": i.severity,
                    "message": i.message,
                    "evidence": i.evidence,
                    "suggestion": i.suggestion
                }
                for i in inconsistencies
            ],
            "critical_count": critical_count,
            "warning_count": warning_count,
            "rule_id": "RULE_174",
            "rule_name": "時系列整合性検証"
        }


# グローバルチェッカー
temporal_checker = TemporalConsistencyChecker()


def verify_temporal_consistency(
    person_name: str,
    age: int,
    episode_text: str,
    birth_year: Optional[int] = None
) -> Dict:
    """
    時系列整合性を検証（外部インターフェース）

    Args:
        person_name: 人物名
        age: 年齢
        episode_text: エピソード本文
        birth_year: 生年（オプション）

    Returns:
        検証結果
    """
    return temporal_checker.verify(person_name, age, episode_text, birth_year)


if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    # テストケース
    test_cases = [
        {
            "person": "大谷翔平",
            "age": 28,
            "birth_year": 1994,
            "text": "あなたと同じ28歳のとき、大谷翔平はMLBでア・リーグMVPを受賞し、投手と打者の二刀流で歴史を変えた。2021年シーズン、投球では9勝、156奪三振、打撃では46本塁打、100打点を記録。ベーブ・ルース以来100年ぶりの快挙として世界中のメディアが報じ、野球の常識を覆した。"
        },
        {
            "person": "架空の人物",
            "age": 18,
            "birth_year": 2000,
            "text": "あなたと同じ18歳のとき、ノーベル物理学賞を受賞し、史上最年少の記録を打ち立てた。"
        },
        {
            "person": "架空の開発者",
            "age": 25,
            "birth_year": 1965,
            "text": "あなたと同じ25歳のとき、1990年にスマートフォンアプリを開発し、一夜にして億万長者となった。"
        }
    ]

    print("=" * 80)
    print("RULE_174: 時系列整合性検証 - テスト実行")
    print("=" * 80)
    print()

    for i, test in enumerate(test_cases, 1):
        print(f"テストケース {i}: {test['person']}")
        print(f"  年齢: {test['age']}歳")
        print(f"  生年: {test['birth_year']}年")
        print(f"  テキスト: {test['text'][:60]}...")
        print()

        result = verify_temporal_consistency(
            test["person"],
            test["age"],
            test["text"],
            test.get("birth_year")
        )

        status = "✅ 整合性OK" if result["passed"] else "❌ 矛盾あり"
        print(f"  {status}")
        print(f"  🔴 重大な矛盾: {result['critical_count']}件")
        print(f"  🟡 警告: {result['warning_count']}件")

        if result["inconsistencies"]:
            print(f"  📋 検出された問題:")
            for issue in result["inconsistencies"]:
                severity_emoji = {"CRITICAL": "🔴", "WARNING": "🟡", "INFO": "ℹ️"}
                print(f"     {severity_emoji[issue['severity']]} {issue['message']}")
                print(f"        証拠: {issue['evidence']}")
                print(f"        提案: {issue['suggestion']}")
        print()

    print("=" * 80)
    print("✅ テスト完了")
    print("=" * 80)
