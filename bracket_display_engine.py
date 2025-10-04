#!/usr/bin/env python3
"""
括弧表示エンジン (Bracket Display Engine)

目的:
1. 人物名の横にグループ名・作品名を括弧表示するか判定
2. エピソード本文から括弧内ワードを除去

設計ドキュメント: DESIGN_BRACKET_DISPLAY_SYSTEM.md
"""

import re
import logging
from typing import Dict, Tuple, Optional, List
from dataclasses import dataclass
from enum import Enum


# ================================================================================
# データクラス定義
# ================================================================================

class EntityType(Enum):
    """人物の種類"""
    REAL_PERSON = "real_person"
    FICTIONAL_CHARACTER = "fictional_character"


class GroupStatus(Enum):
    """グループ活動状態"""
    ACTIVE = "active"          # 活動中
    DISBANDED = "disbanded"    # 解散済み
    HIATUS = "hiatus"          # 活動休止中


class FameLevel(Enum):
    """知名度レベル"""
    PERSONAL_MORE_FAMOUS = "personal_more_famous"  # 本人の方が有名
    GROUP_MORE_FAMOUS = "group_more_famous"        # グループの方が有名
    EQUAL = "equal"                                 # 同等


@dataclass
class BracketDisplayResult:
    """括弧表示判定結果"""
    should_show: bool                    # 表示するか
    bracket_text: Optional[str]          # 括弧内テキスト
    formatted_name: str                  # フォーマット済み名前
    reason: str                          # 判定理由（デバッグ用）


# ================================================================================
# 括弧表示エンジン
# ================================================================================

class BracketDisplayEngine:
    """
    括弧表示判定エンジン

    機能:
    1. should_show_bracket: 括弧表示の可否判定
    2. apply_display_format: 表示形式の適用
    3. remove_bracket_word_from_text: エピソード本文からワード除去
    """

    def __init__(self):
        """初期化"""
        self.logger = logging.getLogger(__name__)

        # カテゴリ別の括弧表示対象
        self.bracket_eligible_categories = {
            "お笑い芸人",
            "コメディアン",
            "ミュージシャン",
            "バンド",
            "YouTuber",
            "アイドル"
        }

    def should_show_bracket(self, person_data: Dict) -> BracketDisplayResult:
        """
        括弧表示判定

        Args:
            person_data: 人物データ
                - person_name: 人物名
                - entity_type: 人物種類
                - group_affiliation: 所属グループ
                - primary_work: 作品名（架空キャラクター）
                - group_status: グループ活動状態
                - fame_level: 知名度レベル
                - category: カテゴリ
                - show_group_in_bracket: 強制表示フラグ（オプション）

        Returns:
            BracketDisplayResult
        """
        person_name = person_data.get('person_name', '')
        entity_type = person_data.get('entity_type', 'real_person')

        # ==========================================
        # Rule 1: 架空キャラクターは必ず作品名を表示
        # ==========================================
        if entity_type == EntityType.FICTIONAL_CHARACTER.value:
            primary_work = person_data.get('primary_work')

            if not primary_work:
                self.logger.warning(
                    f"架空キャラクター '{person_name}' に作品名が設定されていません"
                )
                return BracketDisplayResult(
                    should_show=False,
                    bracket_text=None,
                    formatted_name=person_name,
                    reason="架空キャラクターだが作品名が未設定"
                )

            return BracketDisplayResult(
                should_show=True,
                bracket_text=primary_work,
                formatted_name=f"{person_name}({primary_work})",
                reason="架空キャラクターのため作品名を表示"
            )

        # ==========================================
        # Rule 2: 実在人物のグループ表示判定
        # ==========================================

        # 強制表示フラグのチェック（データベースで明示的に指定されている場合）
        if person_data.get('show_group_in_bracket') == 1:
            bracket_text = person_data.get('bracket_display_text') or person_data.get('group_affiliation')
            if bracket_text:
                return BracketDisplayResult(
                    should_show=True,
                    bracket_text=bracket_text,
                    formatted_name=f"{person_name}({bracket_text})",
                    reason="データベースで明示的に表示指定"
                )

        # グループ所属情報がない場合
        group_affiliation = person_data.get('group_affiliation')
        if not group_affiliation:
            return BracketDisplayResult(
                should_show=False,
                bracket_text=None,
                formatted_name=person_name,
                reason="グループ所属情報なし"
            )

        # グループ活動状態のチェック
        group_status = person_data.get('group_status', 'active')
        if group_status == GroupStatus.DISBANDED.value:
            return BracketDisplayResult(
                should_show=False,
                bracket_text=None,
                formatted_name=person_name,
                reason=f"グループ '{group_affiliation}' は解散済み"
            )

        if group_status == GroupStatus.HIATUS.value:
            return BracketDisplayResult(
                should_show=False,
                bracket_text=None,
                formatted_name=person_name,
                reason=f"グループ '{group_affiliation}' は活動休止中"
            )

        # 知名度レベルのチェック
        fame_level = person_data.get('fame_level', 'equal')
        if fame_level == FameLevel.PERSONAL_MORE_FAMOUS.value:
            return BracketDisplayResult(
                should_show=False,
                bracket_text=None,
                formatted_name=person_name,
                reason=f"本人の知名度がグループ '{group_affiliation}' より高い"
            )

        # カテゴリ別の判定
        category = person_data.get('category', '')
        if category not in self.bracket_eligible_categories:
            return BracketDisplayResult(
                should_show=False,
                bracket_text=None,
                formatted_name=person_name,
                reason=f"カテゴリ '{category}' は括弧表示対象外"
            )

        # すべての条件をクリア → 表示
        return BracketDisplayResult(
            should_show=True,
            bracket_text=group_affiliation,
            formatted_name=f"{person_name}({group_affiliation})",
            reason=f"活動中のグループ '{group_affiliation}' メンバーのため表示"
        )

    def apply_display_format(self, person_name: str, bracket_text: Optional[str]) -> str:
        """
        表示形式の適用

        Args:
            person_name: 人物名
            bracket_text: 括弧内テキスト（Noneの場合は括弧なし）

        Returns:
            フォーマット済み文字列（例: "松本人志(ダウンタウン)"）
        """
        if bracket_text:
            return f"{person_name}({bracket_text})"
        return person_name

    def remove_bracket_word_from_text(
        self,
        text: str,
        bracket_word: str,
        person_name: str
    ) -> str:
        """
        エピソード本文から括弧内ワードを除去

        重要: 人物名部分（"名前(グループ名)"）は除去対象外

        Args:
            text: エピソードテキスト
            bracket_word: 括弧内ワード（グループ名・作品名）
            person_name: 人物名

        Returns:
            除去後のテキスト
        """
        if not bracket_word or not text:
            return text

        # 人物名部分を一時的に保護
        formatted_name_pattern = re.escape(f"{person_name}({bracket_word})")
        placeholder = "<<<PERSON_NAME_PLACEHOLDER>>>"

        # 人物名部分を一時的にプレースホルダーに置換
        protected_text = re.sub(formatted_name_pattern, placeholder, text)

        # 括弧内ワードを除去（様々なパターンに対応）
        patterns = [
            # パターン1: "グループ名は" → 削除
            f"{re.escape(bracket_word)}は",
            # パターン2: "グループ名として" → 削除
            f"{re.escape(bracket_word)}として",
            # パターン3: "グループ名で" → 削除
            f"{re.escape(bracket_word)}で",
            # パターン4: "グループ名の" → 削除
            f"{re.escape(bracket_word)}の",
            # パターン5: 単独の "グループ名" → 削除
            f"\\b{re.escape(bracket_word)}\\b"
        ]

        result = protected_text
        for pattern in patterns:
            result = re.sub(pattern, "", result)

        # プレースホルダーを元に戻す
        result = result.replace(placeholder, f"{person_name}({bracket_word})")

        # 連続した空白・句読点の整形
        result = re.sub(r'\s+', ' ', result)  # 複数空白を1つに
        result = re.sub(r'\s([。、])', r'\1', result)  # 句読点の前の空白削除
        result = result.strip()

        return result

    def validate_no_word_duplication(
        self,
        episode_text: str,
        bracket_word: str,
        person_name: str
    ) -> Tuple[bool, List[str]]:
        """
        エピソード本文に括弧内ワードが重複していないか検証

        Args:
            episode_text: エピソードテキスト
            bracket_word: 括弧内ワード
            person_name: 人物名

        Returns:
            (検証結果, 重複箇所リスト)
        """
        if not bracket_word:
            return (True, [])

        # 人物名部分（"名前(グループ名)"）を除外
        formatted_name = f"{person_name}({bracket_word})"
        text_without_person_name = episode_text.replace(formatted_name, "")

        # 括弧内ワードが含まれているかチェック
        if bracket_word in text_without_person_name:
            # 重複箇所を特定
            pattern = re.escape(bracket_word)
            matches = re.finditer(pattern, text_without_person_name)
            duplications = [
                text_without_person_name[max(0, m.start()-20):min(len(text_without_person_name), m.end()+20)]
                for m in matches
            ]

            self.logger.warning(
                f"⚠️ 括弧内ワード '{bracket_word}' がエピソード本文に含まれています: {duplications}"
            )

            return (False, duplications)

        return (True, [])

    def auto_correct_duplication(
        self,
        episode_text: str,
        bracket_word: str,
        person_name: str
    ) -> str:
        """
        重複検出時の自動修正

        括弧内ワードを適切な一般名詞に置換します。

        Args:
            episode_text: エピソードテキスト
            bracket_word: 括弧内ワード
            person_name: 人物名

        Returns:
            修正後のテキスト

        Examples:
            >>> engine.auto_correct_duplication(
            ...     "上田晋也(くりぃむしちゅー)は...くりぃむしちゅーを結成",
            ...     "くりぃむしちゅー",
            ...     "上田晋也"
            ... )
            "上田晋也(くりぃむしちゅー)は...コンビを結成"
        """
        if not bracket_word:
            return episode_text

        # プレースホルダー保護（人物名部分は置換対象外）
        formatted_name_pattern = f"{person_name}({bracket_word})"
        placeholder = "<<<PERSON_NAME_PLACEHOLDER>>>"

        protected_text = episode_text.replace(formatted_name_pattern, placeholder)

        # 置換マッピング（カテゴリ判定）
        replacement = self._get_replacement_word(bracket_word)

        # 括弧内ワードを一般名詞に置換
        corrected_text = protected_text.replace(bracket_word, replacement)

        # プレースホルダー復元
        final_text = corrected_text.replace(placeholder, formatted_name_pattern)

        return final_text

    def _get_replacement_word(self, bracket_word: str) -> str:
        """
        括弧内ワードに対する適切な置換語を取得

        Args:
            bracket_word: 括弧内ワード

        Returns:
            置換語（一般名詞）
        """
        # お笑いコンビ判定
        comedian_groups = [
            "くりぃむしちゅー", "千鳥", "サンドウィッチマン",
            "爆笑問題", "ダウンタウン", "とんねるず",
            "ナインティナイン", "雨上がり決死隊", "ピース"
        ]
        if bracket_word in comedian_groups:
            return "コンビ"

        # バンド判定
        bands = [
            "RADWIMPS", "L'Arc～en～Ciel", "GLAY", "X JAPAN",
            "B'z", "サザンオールスターズ", "Mr.Children",
            "ONE OK ROCK", "LUNA SEA", "BUMP OF CHICKEN"
        ]
        if bracket_word in bands:
            return "バンド"

        # YouTuberグループ判定
        youtuber_groups = [
            "東海オンエア", "Fischer's", "水溜りボンド",
            "コムドット", "ヴァンゆんチャンネル"
        ]
        if bracket_word in youtuber_groups:
            return "グループ"

        # アニメ・漫画作品判定
        anime_manga = [
            "ちびまる子ちゃん", "ONE PIECE", "ドラえもん",
            "ドラゴンボール", "鬼滅の刃", "呪術廻戦",
            "進撃の巨人", "NARUTO", "サザエさん"
        ]
        if bracket_word in anime_manga:
            return "作品"

        # デフォルト（グループ名として扱う）
        return "グループ"


# ================================================================================
# ヘルパー関数
# ================================================================================

def format_person_name_with_bracket(person_data: Dict) -> Tuple[str, Optional[str]]:
    """
    人物名を括弧付きでフォーマット

    Args:
        person_data: 人物データ

    Returns:
        (フォーマット済み名前, 括弧内テキスト)
    """
    engine = BracketDisplayEngine()
    result = engine.should_show_bracket(person_data)

    return (result.formatted_name, result.bracket_text)


def create_episode_prompt_with_bracket_constraint(
    person_data: Dict,
    age: int,
    template: str
) -> str:
    """
    括弧制約付きエピソード生成プロンプト作成

    Args:
        person_data: 人物データ
        age: 年齢
        template: プロンプトテンプレート

    Returns:
        プロンプト文字列
    """
    engine = BracketDisplayEngine()
    result = engine.should_show_bracket(person_data)

    # テンプレートに人物名を埋め込み
    prompt = template.format(
        person_name=result.formatted_name,
        age=age
    )

    # 括弧内ワードがある場合は制約を追加
    if result.bracket_text:
        constraint = f"""

【重要な制約】
- 名前に括弧が付いている場合、括弧内のワード「{result.bracket_text}」をエピソード本文では使用しないでください
- 例: "{result.formatted_name}" → エピソード内で「{result.bracket_text}」という単語を使わない
"""
        prompt += constraint

    return prompt


# ================================================================================
# テスト用サンプルデータ
# ================================================================================

SAMPLE_DATA = {
    # 架空キャラクター
    "luffy": {
        "person_name": "モンキー・D・ルフィ",
        "entity_type": "fictional_character",
        "primary_work": "ONE PIECE",
        "category": "架空キャラクター"
    },

    # 現役お笑いコンビ
    "matayoshi": {
        "person_name": "又吉直樹",
        "entity_type": "real_person",
        "category": "お笑い芸人",
        "group_affiliation": "ピース",
        "group_status": "active",
        "fame_level": "equal"
    },

    # 解散バンド
    "yoshiki": {
        "person_name": "YOSHIKI",
        "entity_type": "real_person",
        "category": "ミュージシャン",
        "group_affiliation": "X JAPAN",
        "group_status": "disbanded",
        "fame_level": "personal_more_famous"
    },

    # 本人の方が有名
    "hikakin": {
        "person_name": "HIKAKIN",
        "entity_type": "real_person",
        "category": "YouTuber",
        "group_affiliation": "HIKAKIN & SEIKIN",
        "group_status": "active",
        "fame_level": "personal_more_famous"
    },

    # 現役ダウンタウン
    "matsumoto": {
        "person_name": "松本人志",
        "entity_type": "real_person",
        "category": "お笑い芸人",
        "group_affiliation": "ダウンタウン",
        "group_status": "active",
        "fame_level": "group_more_famous"
    }
}


def run_sample_tests():
    """サンプルテストの実行"""

    logging.basicConfig(level=logging.INFO)
    engine = BracketDisplayEngine()

    print("="*80)
    print("括弧表示エンジン - サンプルテスト")
    print("="*80)

    for key, data in SAMPLE_DATA.items():
        print(f"\n【{key}】: {data['person_name']}")
        result = engine.should_show_bracket(data)

        print(f"  表示判定: {'✅ 表示' if result.should_show else '❌ 非表示'}")
        print(f"  括弧内テキスト: {result.bracket_text}")
        print(f"  フォーマット済み名前: {result.formatted_name}")
        print(f"  判定理由: {result.reason}")

    print("\n" + "="*80)
    print("ワード除去テスト")
    print("="*80)

    # テストケース1: ダウンタウン
    text1 = "あなたと同じ31歳のとき、松本人志(ダウンタウン)はダウンタウンとして「ごっつええ感じ」で最高視聴率28.8％を記録した。"
    cleaned1 = engine.remove_bracket_word_from_text(text1, "ダウンタウン", "松本人志")
    print(f"\nBefore: {text1}")
    print(f"After: {cleaned1}")

    is_valid, duplications = engine.validate_no_word_duplication(cleaned1, "ダウンタウン", "松本人志")
    print(f"検証: {'✅ OK' if is_valid else '❌ NG'}")

    # テストケース2: ONE PIECE
    text2 = "あなたと同じ19歳のとき、モンキー・D・ルフィ(ONE PIECE)はONE PIECEの冒険で東の海から偉大なる航路へと旅立った。"
    cleaned2 = engine.remove_bracket_word_from_text(text2, "ONE PIECE", "モンキー・D・ルフィ")
    print(f"\nBefore: {text2}")
    print(f"After: {cleaned2}")

    is_valid, duplications = engine.validate_no_word_duplication(cleaned2, "ONE PIECE", "モンキー・D・ルフィ")
    print(f"検証: {'✅ OK' if is_valid else '❌ NG'}")


if __name__ == '__main__':
    run_sample_tests()
