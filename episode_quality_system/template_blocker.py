#!/usr/bin/env python3
"""
TemplateBlocker - 定型文検出・ブロックシステム
定型文や曖昧な表現を検出し、エピソード生成時に即座にブロック
"""

import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

class ViolationType(Enum):
    """違反タイプ"""
    TEMPLATE = "定型文"
    SUBJECTIVE = "主観的表現"
    VAGUE = "曖昧表現"
    NOUN_ENDING = "名詞終了"
    DATE_NOISE = "日付ノイズ"
    SUPERLATIVE = "過剰な最上級"
    CLICHE = "陳腐な表現"
    META_DISCLAIMER = "メタ的説明"  # EPUP: 架空キャラクター用

@dataclass
class Violation:
    """違反情報"""
    type: ViolationType
    pattern: str
    matched_text: str
    position: int
    severity: str  # "critical", "major", "minor"
    suggestion: str

class TemplateBlocker:
    """定型文ブロッカー"""

    def __init__(self):
        """初期化"""
        # 定型文パターン（絶対禁止）
        self.template_patterns = [
            # 継続・持続系
            (r'その後も.*?続け', "具体的な成果を記述"),
            (r'今も.*?続いて', "現在の具体的状況を記述"),
            (r'現在も.*?継続', "最新の具体的データを記述"),

            # 影響・記憶系
            (r'多くの.*?影響を与え', "具体的な影響例を記述"),
            (r'.*?に影響を与えた', "具体的な影響対象と内容を記述"),
            (r'後世.*?道標', "具体的な継承例を記述"),
            (r'永遠に.*?残', "具体的な記録や成果を記述"),
            (r'.*?記憶され', "具体的な記録・記念を記述"),
            (r'.*?語り継が', "具体的な伝承例を記述"),

            # 評価・称賛系
            (r'この偉業は', "偉業ではなく具体的成果を記述"),
            (r'この功績', "功績ではなく具体的成果を記述"),
            (r'この活躍', "活躍ではなく具体的行動を記述"),
            (r'この成果', "成果の具体的内容を記述"),

            # 時代・新風系
            (r'新風を吹き込', "具体的な変化内容を記述"),
            (r'新たな可能性', "具体的な可能性の内容を記述"),
            (r'時代を.*?象徴', "具体的な時代背景を記述"),
            (r'.*?の先駆け', "具体的な先駆的要素を記述"),

            # その他の定型文
            (r'道を切り開', "具体的な開拓内容を記述"),
            (r'礎を築', "具体的な基盤内容を記述"),
            (r'歴史に名を刻', "具体的な歴史的記録を記述"),
            (r'伝説となった', "具体的な記録・評価を記述"),
            (r'神話を作った', "具体的な成果を記述"),

            # RULE_205: 石ノ森章太郎事例で発見されたテンプレートパターン
            (r'画期的な成果を達成しました', "具体的な成果名・数値を記述"),
            (r'それまでの努力と経験が結実し', "具体的な努力内容を記述"),
            (r'長年の準備と戦略的な取り組みの賜物', "具体的な準備内容を記述"),
            (r'周囲からの評価も高まり', "具体的な評価内容を記述"),
            (r'次のステージへと進む重要な節目', "具体的な節目の内容を記述"),
            (r'業界に大きな影響を与える実績', "具体的な実績名を記述"),
            (r'この功績により、業界全体に新たな基準', "具体的な基準内容を記述"),
            (r'困難な課題に直面しながらも', "具体的な困難内容を記述"),
            (r'長期間の準備と努力の結果', "具体的な準備内容を記述"),
            (r'周囲からの信頼も厚くなり', "具体的な信頼の証拠を記述"),
            (r'業界内での評価が一層高まる転機', "具体的な転機の内容を記述"),
            (r'業績は国内外で広く認められる', "具体的な認定・受賞を記述"),
            (r'周囲の協力を得ながら、着実に目標', "具体的な目標内容を記述"),
            (r'歴史に名を刻む重要な成果', "具体的な成果名を記述"),
            (r'確固たる地位を業界内で築き上げる', "具体的な地位・役職を記述"),
            (r'その後の活動における重要な基盤', "具体的な基盤内容を記述"),
            (r'この実績が次のステージへの扉を開いた', "具体的な次のステージを記述"),
            (r'多くの人々に希望と勇気を与える結果', "具体的な影響例を記述"),
            (r'この成果が後進の目標となっていきました', "具体的な後進の名前を記述"),
            (r'この成果は後の展開に大きな影響を与えた', "具体的な展開内容を記述"),
            (r'この達成により、新たな可能性が開かれた', "具体的な可能性を記述"),
            (r'この成功体験が今後の活動の基盤となった', "具体的な活動内容を記述"),
        ]

        # 主観的表現（禁止）
        self.subjective_patterns = [
            (r'素晴らしい', "客観的評価に変更"),
            (r'凄い', "具体的な数値・事実に変更"),
            (r'驚くべき', "客観的事実に変更"),
            (r'感動的な', "客観的描写に変更"),
            (r'衝撃的な', "客観的描写に変更"),
            (r'見事な', "客観的評価に変更"),
            (r'華麗な', "客観的描写に変更"),
            (r'圧巻の', "客観的評価に変更"),
            (r'奇跡の', "客観的事実に変更"),
            (r'伝説的な', "客観的評価に変更"),
        ]

        # 曖昧表現（要修正）
        self.vague_patterns = [
            (r'多くの', "具体的な数を記述"),
            (r'たくさんの', "具体的な数を記述"),
            (r'数々の', "具体的な数を記述"),
            (r'様々な', "具体的な種類を記述"),
            (r'いくつもの', "具体的な数を記述"),
            (r'幅広い', "具体的な範囲を記述"),
            (r'大きな', "具体的な規模を記述"),
            (r'小さな', "具体的な規模を記述"),
            (r'高い評価', "具体的な評価内容を記述"),
            (r'低い評価', "具体的な評価内容を記述"),
        ]

        # 名詞終了パターン
        self.noun_endings = [
            '革命児', '先駆者', '開拓者', '巨人', '天才',
            'レジェンド', 'カリスマ', '英雄', '巨匠', '偉人',
            '第一人者', 'パイオニア', '立役者', '功労者', '貢献者'
        ]

        # 日付ノイズパターン（RULE_164準拠）
        self.date_noise_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',  # 年月日
            r'\d{1,2}月\d{1,2}日',          # 月日
            r'\d{4}年\d{1,2}月(?!\d)',      # 年月
            r'午前\d+時',                    # 時刻
            r'午後\d+時',                    # 時刻
            r'\d+時\d+分',                   # 時分
        ]

        # 過剰な最上級表現
        self.superlative_patterns = [
            (r'史上最.*?の', "客観的記録に変更"),
            (r'世界最.*?の', "客観的記録に変更"),
            (r'日本最.*?の', "客観的記録に変更"),
            (r'最も.*?な', "客観的評価に変更"),
            (r'もっとも.*?な', "客観的評価に変更"),
            (r'一番.*?な', "客観的評価に変更"),
            (r'最高の', "客観的評価に変更"),
            (r'最強の', "客観的評価に変更"),
            (r'最大の', "具体的規模に変更"),
            (r'唯一の', "事実確認が必要"),
        ]

        # 陳腐な表現
        self.cliche_patterns = [
            (r'夢を与え', "具体的な影響を記述"),
            (r'希望の光', "具体的な成果を記述"),
            (r'勇気を与え', "具体的な影響を記述"),
            (r'感動を呼', "具体的な反響を記述"),
            (r'心に残る', "具体的な記録を記述"),
            (r'忘れられない', "具体的な記録を記述"),
            (r'歴史的瞬間', "具体的な記録を記述"),
            (r'運命の', "客観的描写に変更"),
            (r'奇跡の', "客観的事実に変更"),
            (r'伝説の', "客観的評価に変更"),
        ]

        # EPUP: メタ的説明パターン（架空キャラクター用 - Critical）
        # 架空キャラクターのエピソードで絶対に使用してはいけない表現
        self.meta_disclaimer_patterns = [
            # 存在否定系
            (r'は架空の(キャラクター|人物|存在)であり', "作品世界内の視点で記述"),
            (r'実在(しない|の人物ではない)', "作品世界内の視点で記述"),
            (r'エピソード(は|が)存在しません', "作品内エピソードを記述"),
            (r'公式(な|の)?描写は.*存在しない', "作品設定に基づいて記述"),
            (r'実際の.*エピソード.*存在しません', "作品内エピソードを記述"),

            # 生成拒否系
            (r'申し訳ございませんが', "作品世界内の視点で生成"),
            (r'生成することは(できません|適切ではありません)', "作品設定に基づいて生成"),
            (r'別の.*人物.*でしたら', "架空キャラとして生成"),
            (r'このような.*対応とさせていただきます', "作品内エピソードを生成"),

            # メタ言及系
            (r'年齢を重ね(たり|ること).*ない', "作品世界での成長を記述"),
            (r'設定上は', "作品世界の事実として記述"),
            (r'フィクション(である|として)', "作品内の事実として記述"),
            (r'虚構(の|として)', "作品内の事実として記述"),
            (r'創作(として|上)', "作品内の事実として記述"),
            (r'物語(の中|として)', "作品内の事実として記述"),

            # 情報不足言及系
            (r'情報(が|は).*ない', "作品設定から外挿"),
            (r'描写(が|は).*ない', "キャラクター設定から外挿"),
            (r'言及(が|は).*ない', "作品世界観に基づいて記述"),

            # その他メタ表現
            (r'※.*キャラクター', "メタ注釈を削除"),
            (r'※注：', "メタ注釈を削除"),
            (r'架空.*ため', "作品世界内の視点で記述"),
        ]

    def check_episode(self, episode_text: str, person_type: str = None) -> Tuple[bool, List[Violation]]:
        """
        エピソードをチェック

        Args:
            episode_text: エピソードテキスト
            person_type: 人物タイプ（"REAL" or "FICTIONAL"）- メタ的説明チェック用

        Returns:
            (ブロック判定, 違反リスト)
        """
        violations = []
        should_block = False

        # 1. 定型文チェック（Critical）
        for pattern, suggestion in self.template_patterns:
            matches = re.finditer(pattern, episode_text)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.TEMPLATE,
                    pattern=pattern,
                    matched_text=match.group(),
                    position=match.start(),
                    severity="critical",
                    suggestion=suggestion
                ))
                should_block = True

        # 2. 主観的表現チェック（Major）
        for pattern, suggestion in self.subjective_patterns:
            matches = re.finditer(pattern, episode_text)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.SUBJECTIVE,
                    pattern=pattern,
                    matched_text=match.group(),
                    position=match.start(),
                    severity="major",
                    suggestion=suggestion
                ))
                should_block = True

        # 3. 曖昧表現チェック（Major）
        for pattern, suggestion in self.vague_patterns:
            matches = re.finditer(pattern, episode_text)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.VAGUE,
                    pattern=pattern,
                    matched_text=match.group(),
                    position=match.start(),
                    severity="major",
                    suggestion=suggestion
                ))
                should_block = True

        # 4. 名詞終了チェック（Critical）
        text_without_period = episode_text.rstrip('。')
        for noun in self.noun_endings:
            if text_without_period.endswith(noun):
                violations.append(Violation(
                    type=ViolationType.NOUN_ENDING,
                    pattern=f"文末: {noun}",
                    matched_text=f"{noun}。",
                    position=len(text_without_period) - len(noun),
                    severity="critical",
                    suggestion=f"「{noun}となった」等の動詞で終わらせる"
                ))
                should_block = True

        # 5. 日付ノイズチェック（Critical - RULE_164）
        for pattern in self.date_noise_patterns:
            matches = re.finditer(pattern, episode_text)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.DATE_NOISE,
                    pattern=pattern,
                    matched_text=match.group(),
                    position=match.start(),
                    severity="critical",
                    suggestion="日付を削除（年齢対比に集中）"
                ))
                should_block = True

        # 6. 過剰な最上級表現チェック（Major）
        for pattern, suggestion in self.superlative_patterns:
            matches = re.finditer(pattern, episode_text)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.SUPERLATIVE,
                    pattern=pattern,
                    matched_text=match.group(),
                    position=match.start(),
                    severity="major",
                    suggestion=suggestion
                ))
                # 最上級は事実確認が必要なのでブロックはしない（警告のみ）

        # 7. 陳腐な表現チェック（Major）
        for pattern, suggestion in self.cliche_patterns:
            matches = re.finditer(pattern, episode_text)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.CLICHE,
                    pattern=pattern,
                    matched_text=match.group(),
                    position=match.start(),
                    severity="major",
                    suggestion=suggestion
                ))
                should_block = True

        # 8. EPUP: メタ的説明チェック（Critical - 架空キャラクターのみ）
        # person_typeがFICTIONAL、またはperson_type未指定でも
        # メタ的説明が含まれていれば検出（安全側に倒す）
        for pattern, suggestion in self.meta_disclaimer_patterns:
            matches = re.finditer(pattern, episode_text)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.META_DISCLAIMER,
                    pattern=pattern,
                    matched_text=match.group(),
                    position=match.start(),
                    severity="critical",
                    suggestion=suggestion
                ))
                should_block = True

        return should_block, violations

    def check_meta_disclaimer(self, episode_text: str) -> Tuple[bool, List[Violation]]:
        """
        EPUP: メタ的説明のみをチェック（架空キャラクターエピソード専用）

        Args:
            episode_text: エピソードテキスト

        Returns:
            (メタ説明検出フラグ, 違反リスト)
        """
        violations = []
        has_meta = False

        for pattern, suggestion in self.meta_disclaimer_patterns:
            matches = re.finditer(pattern, episode_text)
            for match in matches:
                violations.append(Violation(
                    type=ViolationType.META_DISCLAIMER,
                    pattern=pattern,
                    matched_text=match.group(),
                    position=match.start(),
                    severity="critical",
                    suggestion=suggestion
                ))
                has_meta = True

        return has_meta, violations

    def get_meta_patterns(self) -> list:
        """メタ的説明パターンのリストを取得（外部参照用）"""
        return [pattern for pattern, _ in self.meta_disclaimer_patterns]

    def get_violation_report(self, violations: List[Violation]) -> str:
        """
        違反レポートを生成

        Args:
            violations: 違反リスト

        Returns:
            レポート文字列
        """
        if not violations:
            return "✅ 違反なし"

        report = []
        report.append("❌ 違反検出:")
        report.append("")

        # 重要度順にソート
        severity_order = {"critical": 0, "major": 1, "minor": 2}
        sorted_violations = sorted(violations, key=lambda v: severity_order[v.severity])

        for violation in sorted_violations:
            severity_mark = {
                "critical": "🔴",
                "major": "🟡",
                "minor": "🟢"
            }[violation.severity]

            report.append(f"{severity_mark} [{violation.type.value}] {violation.matched_text}")
            report.append(f"   → {violation.suggestion}")
            report.append("")

        report.append(f"合計違反数: {len(violations)}")
        critical_count = sum(1 for v in violations if v.severity == "critical")
        if critical_count > 0:
            report.append(f"⚠️ Critical違反 {critical_count}件 - 即座に修正が必要")

        return "\n".join(report)

    def suggest_fix(self, episode_text: str, violations: List[Violation]) -> str:
        """
        修正提案を生成

        Args:
            episode_text: 元のエピソードテキスト
            violations: 違反リスト

        Returns:
            修正提案テキスト
        """
        suggestions = []
        suggestions.append("📝 修正提案:")
        suggestions.append("")

        # 違反箇所ごとに提案
        for violation in violations:
            suggestions.append(f"• {violation.matched_text}")
            suggestions.append(f"  → {violation.suggestion}")

        suggestions.append("")
        suggestions.append("💡 修正のポイント:")
        suggestions.append("1. 定型文を具体的事実に置き換える")
        suggestions.append("2. 主観的表現を客観的データに変更")
        suggestions.append("3. 曖昧な表現を具体的数値にする")
        suggestions.append("4. 文末は動詞・形容詞で終わらせる")
        suggestions.append("5. 日付は削除し年齢対比に集中")

        return "\n".join(suggestions)


def test_template_blocker():
    """テスト実行"""
    blocker = TemplateBlocker()

    # テストケース
    test_episodes = [
        # 定型文を含む例
        "あなたと同じ25歳のとき、彼は素晴らしい功績を残した。その後も活躍を続け、多くの人に影響を与えた。この偉業は永遠に記憶される革命児。",

        # 日付ノイズを含む例
        "あなたと同じ30歳のとき、2020年3月15日に優勝を果たした。午後3時に表彰式が行われ、歴史的瞬間となった。",

        # 良い例
        "あなたと同じ28歳のとき、松井秀喜はヤンキースで31本塁打を記録し、日本人野手として初めて100打点を達成した。"
    ]

    for i, episode in enumerate(test_episodes, 1):
        print(f"\n{'='*60}")
        print(f"テストケース {i}:")
        print(f"エピソード: {episode}")
        print("")

        should_block, violations = blocker.check_episode(episode)

        if should_block:
            print("🚫 ブロック: このエピソードは使用できません")
        else:
            print("✅ 合格: このエピソードは使用可能です")

        print("")
        print(blocker.get_violation_report(violations))

        if violations:
            print("")
            print(blocker.suggest_fix(episode, violations))


if __name__ == "__main__":
    test_template_blocker()
