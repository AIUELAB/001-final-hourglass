#!/usr/bin/env python3
"""
統合検証システム (Unified Validation System)
PDCAガーディアンとOptimizedValidationSystemの矛盾を解消した統一品質基準

Author: Claude Code
Date: 2025-10-01
Version: 1.0.0
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum


class SeverityLevel(Enum):
    """違反の重要度レベル"""
    CRITICAL = "critical"  # 即座に修正必須
    IMPORTANT = "important"  # 修正推奨
    WARNING = "warning"  # 注意喚起
    INFO = "info"  # 情報提供


@dataclass
class RuleResult:
    """検証ルールの結果"""
    rule_name: str
    is_violation: bool
    severity: SeverityLevel = SeverityLevel.INFO
    message: str = ""
    suggestion: str = ""
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


@dataclass
class ValidationResult:
    """エピソード検証の総合結果"""
    episode_id: str
    is_valid: bool
    violations: List[RuleResult]
    warnings: List[RuleResult]
    emotional_impact_score: float
    specificity_score: float
    improvement_suggestions: List[str]

    def get_critical_violations(self) -> List[RuleResult]:
        """クリティカルな違反のみ抽出"""
        return [v for v in self.violations if v.severity == SeverityLevel.CRITICAL]

    def to_dict(self) -> Dict:
        """辞書形式に変換"""
        return {
            "episode_id": self.episode_id,
            "is_valid": self.is_valid,
            "emotional_impact_score": self.emotional_impact_score,
            "specificity_score": self.specificity_score,
            "critical_violations": len(self.get_critical_violations()),
            "total_violations": len(self.violations),
            "warnings": len(self.warnings),
            "violations_detail": [
                {
                    "rule": v.rule_name,
                    "severity": v.severity.value,
                    "message": v.message,
                    "suggestion": v.suggestion
                }
                for v in self.violations
            ]
        }


class ValidationRule(ABC):
    """検証ルールの抽象基底クラス"""

    @abstractmethod
    def check(self, episode: Dict) -> RuleResult:
        """エピソードの検証を実行"""
        pass

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """ルール名を返す"""
        pass

    @property
    @abstractmethod
    def severity(self) -> SeverityLevel:
        """重要度を返す"""
        pass


class CharacterCountRule(ValidationRule):
    """文字数制限ルール: 130-250文字"""

    def __init__(self, min_chars: int = 130, max_chars: int = 250):
        self.min_chars = min_chars
        self.max_chars = max_chars

    @property
    def rule_name(self) -> str:
        return "character_count"

    @property
    def severity(self) -> SeverityLevel:
        return SeverityLevel.CRITICAL

    def check(self, episode: Dict) -> RuleResult:
        text = episode.get('episode_text', '')
        char_count = len(text)

        if char_count < self.min_chars:
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=True,
                severity=self.severity,
                message=f"文字数不足: {char_count}文字 (最低{self.min_chars}文字必要)",
                suggestion=f"あと{self.min_chars - char_count}文字追加してください。具体的な数値や固有名詞を追加すると効果的です。",
                details={"current": char_count, "required_min": self.min_chars}
            )

        if char_count > self.max_chars:
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=True,
                severity=self.severity,
                message=f"文字数超過: {char_count}文字 (最大{self.max_chars}文字)",
                suggestion=f"{char_count - self.max_chars}文字削減してください。冗長な表現を簡潔にしてください。",
                details={"current": char_count, "allowed_max": self.max_chars}
            )

        return RuleResult(
            rule_name=self.rule_name,
            is_violation=False,
            severity=SeverityLevel.INFO,
            message=f"文字数適正: {char_count}文字",
            details={"current": char_count}
        )


class HistoricalMomentRule(ValidationRule):
    """歴史的瞬間ルール: 具体的な意義が必須、曖昧な表現禁止"""

    FORBIDDEN_PATTERNS = [
        r"標準的な.*年齢",
        r"一般的な.*年齢",
        r"通常.*年齢",
        r"普通.*年齢",
        r"平均的.*年齢"
    ]

    REQUIRED_SIGNIFICANCE_PATTERNS = [
        r"(史上|歴史|初めて|初の|唯一|前人未到)",
        r"(世界|全世界|国民|全国|日本|世界初)",
        r"(記録|快挙|偉業|達成)"
    ]

    @property
    def rule_name(self) -> str:
        return "historical_moment"

    @property
    def severity(self) -> SeverityLevel:
        return SeverityLevel.IMPORTANT

    def check(self, episode: Dict) -> RuleResult:
        text = episode.get('episode_text', '')

        # 禁止パターンのチェック
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, text):
                return RuleResult(
                    rule_name=self.rule_name,
                    is_violation=True,
                    severity=self.severity,
                    message=f"曖昧な表現が含まれています: {pattern}",
                    suggestion="具体的な歴史的意義や記録を明示してください（例: 史上最年少、日本人初、世界記録など）",
                    details={"forbidden_pattern": pattern}
                )

        # 具体的意義の存在確認
        has_significance = any(
            re.search(pattern, text)
            for pattern in self.REQUIRED_SIGNIFICANCE_PATTERNS
        )

        if not has_significance:
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=False,
                severity=SeverityLevel.WARNING,
                message="具体的な歴史的意義が不明瞭です",
                suggestion="「史上初」「世界記録」「日本人初」などの具体的な意義を追加してください"
            )

        return RuleResult(
            rule_name=self.rule_name,
            is_violation=False,
            severity=SeverityLevel.INFO,
            message="歴史的意義が明確に記述されています"
        )


class ObjectiveEmotionalRule(ValidationRule):
    """客観的感動表現ルール: 事実ベースで感動を生む"""

    FORBIDDEN_SUBJECTIVE = [
        "素晴らしい", "すごい", "驚異的", "圧倒的",
        "感動的", "劇的", "衝撃的", "奇跡的",
        "伝説的", "壮大な"
    ]

    OBJECTIVE_EMOTION_PATTERNS = {
        "numerical_records": r"(史上|世界|日本|アジア).*\d+",
        "uniqueness": r"(初|唯一|前人未到|史上初)",
        "scale": r"(世界|全世界|国民|全国)",
        "proper_nouns": r"([A-Z][a-z]+|[一-龯]{2,}(賞|杯|大会|選手権))"
    }

    @property
    def rule_name(self) -> str:
        return "objective_emotional"

    @property
    def severity(self) -> SeverityLevel:
        return SeverityLevel.IMPORTANT

    def check(self, episode: Dict) -> RuleResult:
        text = episode.get('episode_text', '')

        # 禁止された主観表現のチェック
        found_subjective = [kw for kw in self.FORBIDDEN_SUBJECTIVE if kw in text]
        if found_subjective:
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=True,
                severity=self.severity,
                message=f"主観的表現が含まれています: {', '.join(found_subjective)}",
                suggestion=self._suggest_objective_alternative(found_subjective[0]),
                details={"forbidden_words": found_subjective}
            )

        # 客観的感動要素のスコア計算
        emotional_score = self._calculate_objective_emotion(text)

        if emotional_score < 0.5:
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=False,
                severity=SeverityLevel.WARNING,
                message=f"客観的感動要素が不足しています (スコア: {emotional_score:.2f})",
                suggestion="数値記録、「初」「唯一」などの独自性、または規模を示す表現を追加してください",
                details={"emotional_score": emotional_score}
            )

        return RuleResult(
            rule_name=self.rule_name,
            is_violation=False,
            severity=SeverityLevel.INFO,
            message=f"客観的感動表現が適切です (スコア: {emotional_score:.2f})",
            details={"emotional_score": emotional_score}
        )

    def _calculate_objective_emotion(self, text: str) -> float:
        """客観的事実ベースの感銘スコア算出"""
        score = 0.0

        # 数値的記録の存在
        if re.search(self.OBJECTIVE_EMOTION_PATTERNS["numerical_records"], text):
            score += 0.3

        # 独自性表現
        if re.search(self.OBJECTIVE_EMOTION_PATTERNS["uniqueness"], text):
            score += 0.3

        # 規模の明示
        if re.search(self.OBJECTIVE_EMOTION_PATTERNS["scale"], text):
            score += 0.2

        # 固有名詞の数
        proper_nouns = re.findall(self.OBJECTIVE_EMOTION_PATTERNS["proper_nouns"], text)
        score += min(len(proper_nouns) * 0.1, 0.2)

        return min(score, 1.0)

    def _suggest_objective_alternative(self, keyword: str) -> str:
        """客観的表現への変換提案"""
        alternatives = {
            "素晴らしい": "史上初の/世界記録の",
            "すごい": "前人未到の/記録的な",
            "驚異的": "XX歳という若さで",
            "圧倒的": "圧倒的な得票数XXで/XX点差で",
            "感動的": "歴史的な瞬間",
            "劇的": "劇的な逆転劇（具体的なスコアで）",
            "衝撃的": "史上最年少/初の快挙",
            "奇跡的": "確率XX%の",
            "伝説的": "歴史に残る",
            "壮大な": "規模XX人の"
        }
        return alternatives.get(keyword, "具体的な数値や固有名詞で表現してください")


class AchievementRule(ValidationRule):
    """実績・成果ルール: キーワード方式 OR スコア方式"""

    ACHIEVEMENT_KEYWORDS = [
        "達成", "獲得", "受賞", "記録", "優勝", "成功", "制作", "発表"
    ]

    IMPACT_SCORE_THRESHOLD = 0.7

    @property
    def rule_name(self) -> str:
        return "achievement"

    @property
    def severity(self) -> SeverityLevel:
        return SeverityLevel.IMPORTANT

    def check(self, episode: Dict) -> RuleResult:
        text = episode.get('episode_text', '')

        # キーワード方式チェック
        has_keyword = any(kw in text for kw in self.ACHIEVEMENT_KEYWORDS)

        # スコア方式チェック
        impact_score = self._calculate_impact_score(text)

        if has_keyword or impact_score >= self.IMPACT_SCORE_THRESHOLD:
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=False,
                severity=SeverityLevel.INFO,
                message="実績・成果が明確に記述されています",
                details={
                    "has_keyword": has_keyword,
                    "impact_score": impact_score
                }
            )

        return RuleResult(
            rule_name=self.rule_name,
            is_violation=False,
            severity=SeverityLevel.WARNING,
            message="実績・成果の記述が不明瞭です",
            suggestion=f"実績キーワード（{', '.join(self.ACHIEVEMENT_KEYWORDS[:3])}等）または具体的な数値データを追加してください",
            details={"impact_score": impact_score}
        )

    def _calculate_impact_score(self, text: str) -> float:
        """インパクトスコアの計算"""
        score = 0.0

        # 数値データの存在
        if re.search(r'\d+[歳億万千百十回連覇勝]', text):
            score += 0.4

        # 固有名詞（賞、大会名など）
        proper_nouns = len(re.findall(r'[一-龯]{2,}(賞|杯|大会|選手権|記録)', text))
        score += min(proper_nouns * 0.15, 0.3)

        # 規模を示す表現
        if re.search(r'(世界|全世界|国民|アジア|日本)', text):
            score += 0.2

        return min(score, 1.0)


class DuplicateAgeRule(ValidationRule):
    """年齢重複禁止ルール: 最高優先度"""

    AGE_PATTERNS = [
        r'(\d+)[歳才]',
        r'(\d+)\s*years\s*old'
    ]

    @property
    def rule_name(self) -> str:
        return "duplicate_age"

    @property
    def severity(self) -> SeverityLevel:
        return SeverityLevel.CRITICAL

    def check(self, episode: Dict) -> RuleResult:
        text = episode.get('episode_text', '')
        person_name = episode.get('person_display_name', '')

        # テキスト内での年齢の出現回数
        all_ages = []
        for pattern in self.AGE_PATTERNS:
            matches = re.findall(pattern, text)
            all_ages.extend(matches)

        # 重複チェック
        if len(all_ages) != len(set(all_ages)):
            duplicates = [age for age in set(all_ages) if all_ages.count(age) > 1]
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=True,
                severity=self.severity,
                message=f"年齢の重複が検出されました: {', '.join(duplicates)}歳",
                suggestion="""年齢の重複を解消してください。

【修正方法】
1. 標準フォーマット「あなたと同じ〇歳のとき」は維持
2. 本文中の重複する年齢表現を削除または言い換え

【修正例】
❌ 悪い例:
「あなたと同じ15歳のとき、石川遼は史上最年少の15歳245日で優勝した」
→ 15歳が2回出現

✅ 良い例:
「あなたと同じ15歳のとき、石川遼は男子ツアー史上最年少でマンシングウェアオープンKSBカップを制覇した。この快挙により賞金2000万円を獲得し、「ハニカミ王子」として日本中の注目を集めた。」
→ 15歳は1回のみ、詳細は偉業の内容で表現""",
                details={"duplicate_ages": duplicates}
            )

        # 人名に年齢が含まれている場合のチェック
        if re.search(r'\d+歳', person_name) and re.search(r'\d+歳', text):
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=True,
                severity=self.severity,
                message="人名と本文で年齢が重複しています",
                suggestion="人名に年齢が含まれる場合、本文では年齢を記載しないでください",
                details={"name": person_name}
            )

        return RuleResult(
            rule_name=self.rule_name,
            is_violation=False,
            severity=SeverityLevel.INFO,
            message="年齢の重複はありません"
        )


class TemplateProhibitionRule(ValidationRule):
    """定型文禁止ルール: 安易な定型文による文字数水増しを防止"""

    FORBIDDEN_TEMPLATES = [
        "日本中が歓喜に包まれ、次世代アスリートたちに夢と希望を与えた瞬間だった。",
        "この瞬間から始まった物語は、今も多くの人々に夢を与えている。",
        "数多くの名作を世に送り出した。作品は世代を超えて愛され、日本文学の宝となっている。",
        "この作品は時代を超えて読み継がれ、多くの読者の心に深い感動を与え続けている。",
        "この楽曲は時代の象徴となり、多くのリスナーの心に深く刻まれた。",
        "この技術革新は未来への扉を開き、次世代のイノベーターたちに大きなインスピレーションを与えた。",
        "この受賞は日本のエンターテインメント界の実力を世界に示す快挙となった。",
        "このスタートアップは後に業界を変革し、新たなビジネスモデルの先駆けとなった。",
        "この挑戦が現代のビジネスシーンを形作っている。"
    ]

    @property
    def rule_name(self) -> str:
        return "template_prohibition"

    @property
    def severity(self) -> SeverityLevel:
        return SeverityLevel.CRITICAL

    def check(self, episode: Dict) -> RuleResult:
        text = episode.get('episode_text', '')

        # 定型文の検出
        found_templates = [template for template in self.FORBIDDEN_TEMPLATES if template in text]

        if found_templates:
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=True,
                severity=self.severity,
                message=f"定型文が含まれています: {found_templates[0][:50]}...",
                suggestion="定型文を削除し、Web検索やMCP APIで取得した具体的な事実情報で置き換えてください。数値データ、固有名詞、独自性のある表現を追加することで、重厚な情報を持ったエピソードに進化させてください。",
                details={"template_count": len(found_templates), "templates": found_templates}
            )

        return RuleResult(
            rule_name=self.rule_name,
            is_violation=False,
            severity=SeverityLevel.INFO,
            message="定型文は含まれていません"
        )


class SpecificityRule(ValidationRule):
    """具体性ルール: 年号・日付を避けつつ数値と固有名詞を重視"""

    TEMPORAL_NOISE_PATTERNS = [
        r'\d{4}年',
        r'令和\d+年',
        r'平成\d+年',
        r'\d+月\d+日',
        r'\d{4}/\d{2}/\d{2}'
    ]

    @property
    def rule_name(self) -> str:
        return "specificity"

    @property
    def severity(self) -> SeverityLevel:
        return SeverityLevel.CRITICAL

    def check(self, episode: Dict) -> RuleResult:
        text = episode.get('episode_text', '')

        # 時間的ノイズのチェック
        temporal_noise = []
        for pattern in self.TEMPORAL_NOISE_PATTERNS:
            matches = re.findall(pattern, text)
            temporal_noise.extend(matches)

        if temporal_noise:
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=True,
                severity=self.severity,
                message=f"年号・日付が含まれています: {', '.join(temporal_noise)}",
                suggestion="年齢比較コンテンツでは年号・日付を避けてください。代わりに「XX歳で」のような表現を使用してください。",
                details={"temporal_noise": temporal_noise}
            )

        # 数値データの存在確認（拡張パターン）
        numerical_patterns = [
            r'\d+[歳億万千百十回連覇勝本枚冊人件個]',  # 基本単位
            r'\d+年間',  # 期間
            r'\d+シーズン',  # スポーツ期間
            r'\d+位',  # 順位
            r'\d+円',  # 金額
            r'\d+ドル',  # 外貨
            r'\d+%',  # パーセント
        ]
        has_numerical = any(re.search(pattern, text) for pattern in numerical_patterns)

        # 固有名詞の数
        proper_nouns = re.findall(r'([一-龯]{2,}(賞|杯|大会|選手権|記録|作品|番組))', text)
        has_proper_nouns = len(proper_nouns) >= 2

        if not has_numerical:
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=True,
                severity=self.severity,
                message="数値データが不足しています",
                suggestion="年齢、記録、回数などの具体的な数値を追加してください",
                details={"has_numerical": False, "proper_noun_count": len(proper_nouns)}
            )

        if not has_proper_nouns:
            return RuleResult(
                rule_name=self.rule_name,
                is_violation=False,
                severity=SeverityLevel.WARNING,
                message=f"固有名詞が不足しています (現在{len(proper_nouns)}個、推奨2個以上)",
                suggestion="賞名、大会名、作品名などの固有名詞を追加してください",
                details={"proper_noun_count": len(proper_nouns)}
            )

        specificity_score = self._calculate_specificity_score(text)
        return RuleResult(
            rule_name=self.rule_name,
            is_violation=False,
            severity=SeverityLevel.INFO,
            message=f"具体性が適切です (スコア: {specificity_score:.2f})",
            details={
                "specificity_score": specificity_score,
                "has_numerical": has_numerical,
                "proper_noun_count": len(proper_nouns)
            }
        )

    def _calculate_specificity_score(self, text: str) -> float:
        """具体性スコアの計算"""
        score = 0.0

        # 数値データ
        numerical_count = len(re.findall(r'\d+[歳億万千百十回連覇勝]', text))
        score += min(numerical_count * 0.3, 0.5)

        # 固有名詞
        proper_noun_count = len(re.findall(r'[一-龯]{2,}(賞|杯|大会|選手権|記録)', text))
        score += min(proper_noun_count * 0.25, 0.5)

        return min(score, 1.0)


class UnifiedValidationSystem:
    """
    統合検証システム
    PDCAガーディアンとOptimizedValidationSystemの矛盾を解消
    """

    def __init__(self):
        self.rules: List[ValidationRule] = [
            DuplicateAgeRule(),  # 年齢重複禁止（同一エピソード内）
            TemplateProhibitionRule(),  # 定型文禁止（文字数水増し防止）
            CharacterCountRule(130, 250),
            SpecificityRule(),
            HistoricalMomentRule(),
            ObjectiveEmotionalRule(),
            AchievementRule()
        ]

    def validate_episode(self, episode: Dict) -> ValidationResult:
        """エピソードの完全検証"""
        violations = []
        warnings = []

        # 各ルールを実行
        for rule in self.rules:
            result = rule.check(episode)

            if result.is_violation:
                violations.append(result)
            elif result.severity == SeverityLevel.WARNING:
                warnings.append(result)

        # 感銘スコアの計算
        emotional_impact = self._calculate_emotional_impact(episode.get('episode_text', ''))

        # 具体性スコアの計算
        specificity_score = self._calculate_specificity_score(episode.get('episode_text', ''))

        # 改善提案の生成
        suggestions = self._generate_suggestions(violations, warnings)

        return ValidationResult(
            episode_id=episode.get('episode_id', 'unknown'),
            is_valid=len(violations) == 0,
            violations=violations,
            warnings=warnings,
            emotional_impact_score=emotional_impact,
            specificity_score=specificity_score,
            improvement_suggestions=suggestions
        )

    def validate_batch(self, episodes: List[Dict]) -> List[ValidationResult]:
        """複数エピソードの一括検証"""
        return [self.validate_episode(ep) for ep in episodes]

    def _calculate_emotional_impact(self, text: str) -> float:
        """客観的事実ベースの感銘スコア"""
        score = 0.0

        # 数値的記録
        if re.search(r'\d+[歳億万千百十]', text):
            score += 0.3

        # 独自性表現
        if re.search(r'(初|唯一|史上初|前人未到)', text):
            score += 0.3

        # 規模の明示
        if re.search(r'(世界|全世界|国民|全国)', text):
            score += 0.2

        # 固有名詞
        proper_nouns = len(re.findall(r'[一-龯]{2,}(賞|杯|大会)', text))
        score += min(proper_nouns * 0.1, 0.2)

        return min(score, 1.0)

    def _calculate_specificity_score(self, text: str) -> float:
        """具体性スコア"""
        score = 0.0

        # 数値データ
        numerical = len(re.findall(r'\d+', text))
        score += min(numerical * 0.15, 0.5)

        # 固有名詞
        proper_nouns = len(re.findall(r'[一-龯]{2,}(賞|杯|大会|選手権)', text))
        score += min(proper_nouns * 0.25, 0.5)

        return min(score, 1.0)

    def _generate_suggestions(self, violations: List[RuleResult], warnings: List[RuleResult]) -> List[str]:
        """改善提案の生成"""
        suggestions = []

        # クリティカルな違反から提案
        for violation in violations:
            if violation.severity == SeverityLevel.CRITICAL and violation.suggestion:
                suggestions.append(f"🔴 {violation.suggestion}")

        # 重要な違反から提案
        for violation in violations:
            if violation.severity == SeverityLevel.IMPORTANT and violation.suggestion:
                suggestions.append(f"🟡 {violation.suggestion}")

        # 警告から提案
        for warning in warnings:
            if warning.suggestion:
                suggestions.append(f"⚠️ {warning.suggestion}")

        return suggestions


def main():
    """動作確認用のメイン関数"""
    # サンプルエピソード
    test_episodes = [
        {
            "episode_id": "EP001",
            "person_display_name": "大谷翔平",
            "episode_text": "17歳でプロ野球選手としてデビューし、史上初の二刀流として活躍。日本ハムファイターズで投手と打者の両方で圧倒的な成績を残した。"
        },
        {
            "episode_id": "EP002",
            "person_display_name": "羽生結弦",
            "episode_text": "19歳でソチオリンピック金メダルを獲得。フィギュアスケート史上、男子シングルで66年ぶりとなるオリンピック2連覇を達成した。"
        },
        {
            "episode_id": "EP003",
            "person_display_name": "藤井聡太",
            "episode_text": "2016年、14歳で四段に昇段。将棋界の最年少記録を次々と更新し、素晴らしい活躍を見せた。"
        }
    ]

    # 検証システムのインスタンス化
    validator = UnifiedValidationSystem()

    # 検証実行
    print("=" * 80)
    print("統合検証システム - 動作確認")
    print("=" * 80)

    for episode in test_episodes:
        print(f"\n【エピソードID: {episode['episode_id']}】")
        print(f"人物: {episode['person_display_name']}")
        print(f"内容: {episode['episode_text']}")
        print("-" * 80)

        result = validator.validate_episode(episode)

        print(f"検証結果: {'✅ 合格' if result.is_valid else '❌ 不合格'}")
        print(f"感銘スコア: {result.emotional_impact_score:.2f}")
        print(f"具体性スコア: {result.specificity_score:.2f}")

        if result.violations:
            print("\n【違反事項】")
            for v in result.violations:
                print(f"  {v.severity.value.upper()}: {v.message}")
                if v.suggestion:
                    print(f"  → {v.suggestion}")

        if result.warnings:
            print("\n【警告】")
            for w in result.warnings:
                print(f"  {w.message}")
                if w.suggestion:
                    print(f"  → {w.suggestion}")

        print("=" * 80)


if __name__ == "__main__":
    main()
