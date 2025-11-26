#!/usr/bin/env python3
"""
エピソードリード文生成モジュール

実在人物と架空キャラクターで異なる冒頭フォーマットを生成する。

フォーマット仕様:
- 実在人物: 「あなたと同じ{age}歳のとき、{name}は」
- 架空キャラクター: 「あなたと同じ{age}歳のとき、{name}『{work_title}』は」
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple


class PersonType(Enum):
    """人物タイプ"""

    REAL = "REAL"
    FICTIONAL = "FICTIONAL"


@dataclass
class LeadSentenceResult:
    """リード文生成結果"""

    lead_sentence: str
    person_type: PersonType
    work_title_used: Optional[str] = None
    warning: Optional[str] = None


# 作品名マッピング（work_titleが欠損している場合のフォールバック）
WORK_TITLE_MAP = {
    # ポケットモンスター
    "ピカチュウ": "ポケットモンスター",
    "サトシ": "ポケットモンスター",
    # サザエさん
    "フグ田サザエ": "サザエさん",
    "サザエさん": "サザエさん",
    "磯野カツオ": "サザエさん",
    "磯野ワカメ": "サザエさん",
    # ファイナルファンタジー
    "ティファ・ロックハート": "ファイナルファンタジーVII",
    "クラウド・ストライフ": "ファイナルファンタジーVII",
    "セフィロス": "ファイナルファンタジーVII",
    # ドラえもん
    "野比のび太": "ドラえもん",
    "ドラえもん": "ドラえもん",
    # 鬼滅の刃
    "竈門炭治郎": "鬼滅の刃",
    "竈門禰豆子": "鬼滅の刃",
    "胡蝶しのぶ": "鬼滅の刃",
    # ドラゴンボール
    "孫悟空": "ドラゴンボール",
    "孫悟飯": "ドラゴンボール",
    # ONE PIECE
    "モンキー・D・ルフィ": "ONE PIECE",
    "ロロノア・ゾロ": "ONE PIECE",
    "ナミ": "ONE PIECE",
    "サンジ": "ONE PIECE",
    "ニコ・ロビン": "ONE PIECE",
    "トニートニー・チョッパー": "ONE PIECE",
    # ルパン三世
    "ルパン三世": "ルパン三世",
    # NARUTO
    "うずまきナルト": "NARUTO",
    "うちはサスケ": "NARUTO",
    "はたけカカシ": "NARUTO",
    # 名探偵コナン
    "毛利蘭": "名探偵コナン",
    "毛利小五郎": "名探偵コナン",
    "江戸川コナン": "名探偵コナン",
    "工藤新一": "名探偵コナン",
    # 新世紀エヴァンゲリオン
    "碇シンジ": "新世紀エヴァンゲリオン",
    # スーパーマリオ
    "マリオ": "スーパーマリオブラザーズ",
    # ウルトラマン
    "ウルトラマン": "ウルトラマン",
    # アンパンマン
    "アンパンマン": "それいけ！アンパンマン",
    # クレヨンしんちゃん
    "クレヨンしんちゃん（野原しんのすけ）": "クレヨンしんちゃん",
    "野原しんのすけ": "クレヨンしんちゃん",
    # ガンダム
    "ガンダム（RX-78-2）": "機動戦士ガンダム",
    # セーラームーン
    "セーラームーン（月野うさぎ）": "美少女戦士セーラームーン",
    "月野うさぎ": "美少女戦士セーラームーン",
    # 鉄腕アトム
    "鉄腕アトム": "鉄腕アトム",
    # 北斗の拳
    "ケンシロウ": "北斗の拳",
    # るろうに剣心
    "緋村剣心": "るろうに剣心",
    # VOCALOID
    "初音ミク": "VOCALOID",
    # VTuber
    "キズナアイ": "バーチャルYouTuber",
    "輝夜月": "バーチャルYouTuber",
    "ミライアカリ": "バーチャルYouTuber",
    "ホロライブ": "hololive production",
    "にじさんじ": "NIJISANJI",
}


def get_work_title(person_name: str, work_title: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
    """
    作品名を取得（欠損時はMAPから補完）

    Args:
        person_name: 人物名
        work_title: データベースのwork_title値

    Returns:
        (作品名, 警告メッセージ)
    """
    # work_titleが有効な場合はそのまま使用
    if work_title and str(work_title) not in ("", "nan", "None"):
        return work_title, None

    # MAPから補完
    if person_name in WORK_TITLE_MAP:
        return WORK_TITLE_MAP[person_name], None

    # 補完できない場合
    return None, f"作品名が見つかりません: {person_name}"


def build_episode_lead_sentence(
    person_name: str, age: int, person_type: str, work_title: Optional[str] = None
) -> LeadSentenceResult:
    """
    エピソードの冒頭リード文を生成

    Args:
        person_name: 人物名
        age: 年齢
        person_type: 人物タイプ（REAL/FICTIONAL）
        work_title: 作品名（架空キャラクターの場合）

    Returns:
        LeadSentenceResult: 生成結果
    """
    ptype = person_type.upper() if person_type else "REAL"

    # 実在人物の場合
    if ptype == "REAL" or "FICTIONAL" not in ptype:
        lead = f"あなたと同じ{int(age)}歳のとき、{person_name}は"
        return LeadSentenceResult(lead_sentence=lead, person_type=PersonType.REAL)

    # 架空キャラクターの場合
    resolved_title, warning = get_work_title(person_name, work_title)

    if resolved_title:
        lead = f"あなたと同じ{int(age)}歳のとき、{person_name}『{resolved_title}』は"
        return LeadSentenceResult(lead_sentence=lead, person_type=PersonType.FICTIONAL, work_title_used=resolved_title)
    else:
        # 作品名がない場合は従来形式にフォールバック（警告付き）
        lead = f"あなたと同じ{int(age)}歳のとき、{person_name}は"
        return LeadSentenceResult(lead_sentence=lead, person_type=PersonType.FICTIONAL, warning=warning)


def convert_episode_lead(
    episode_text: str, person_name: str, age: int, person_type: str, work_title: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    既存エピソードのリード文を新フォーマットに変換

    Args:
        episode_text: 元のエピソードテキスト
        person_name: 人物名
        age: 年齢
        person_type: 人物タイプ
        work_title: 作品名

    Returns:
        (変換後のエピソードテキスト, 警告メッセージ)
    """
    # 実在人物は変換不要
    ptype = person_type.upper() if person_type else "REAL"
    if ptype == "REAL" or "FICTIONAL" not in ptype:
        return episode_text, None

    # 現在のリード文パターン
    current_pattern = rf"^あなたと同じ{int(age)}歳のとき、{re.escape(person_name)}は"

    # すでに新フォーマット（作品名付き）かチェック
    new_pattern = rf"^あなたと同じ{int(age)}歳のとき、{re.escape(person_name)}『.+?』は"
    if re.match(new_pattern, episode_text):
        return episode_text, None  # 変換不要

    # 現在のフォーマットに一致するか確認
    if not re.match(current_pattern, episode_text):
        return episode_text, f"リード文パターンが一致しません: {episode_text[:50]}"

    # 新しいリード文を生成
    result = build_episode_lead_sentence(person_name, age, person_type, work_title)

    if result.warning:
        return episode_text, result.warning

    # リード文を置換
    new_text = re.sub(current_pattern, result.lead_sentence, episode_text)
    return new_text, None


def check_episode_lead_format(
    episode_text: str, person_type: str, work_title: Optional[str] = None
) -> Tuple[bool, str]:
    """
    エピソードの冒頭フォーマットが仕様に準拠しているかチェック

    Args:
        episode_text: エピソードテキスト
        person_type: 人物タイプ
        work_title: 作品名

    Returns:
        (準拠しているか, メッセージ)
    """
    ptype = person_type.upper() if person_type else "REAL"

    # 実在人物の場合
    if ptype == "REAL" or "FICTIONAL" not in ptype:
        pattern = r"^あなたと同じ\d+歳のとき、.+は"
        if re.match(pattern, episode_text):
            return True, "実在人物フォーマット準拠"
        return False, "実在人物の標準フォーマットに準拠していません"

    # 架空キャラクターの場合
    pattern = r"^あなたと同じ\d+歳のとき、.+『.+?』は"
    if re.match(pattern, episode_text):
        return True, "架空キャラクターフォーマット準拠"

    # 旧フォーマット（作品名なし）かチェック
    old_pattern = r"^あなたと同じ\d+歳のとき、.+は"
    if re.match(old_pattern, episode_text):
        return False, "架空キャラクターですが作品名が含まれていません"

    return False, "標準フォーマットに準拠していません"


if __name__ == "__main__":
    # テスト
    print("=== リード文生成テスト ===")

    # 実在人物
    result = build_episode_lead_sentence("イチロー", 45, "REAL")
    print(f"実在: {result.lead_sentence}")

    # 架空キャラ（作品名あり）
    result = build_episode_lead_sentence("毛利蘭", 17, "FICTIONAL", "名探偵コナン")
    print(f"架空（作品あり）: {result.lead_sentence}")

    # 架空キャラ（MAP補完）
    result = build_episode_lead_sentence("ピカチュウ", 66, "FICTIONAL", None)
    print(f"架空（MAP補完）: {result.lead_sentence} [補完: {result.work_title_used}]")

    # 架空キャラ（欠損）
    result = build_episode_lead_sentence("不明キャラ", 20, "FICTIONAL", None)
    print(f"架空（欠損）: {result.lead_sentence} [警告: {result.warning}]")

    print("\n=== 変換テスト ===")
    old_text = "あなたと同じ17歳のとき、毛利蘭は母の代わりに毛利家の家事をこなしていた。"
    new_text, warning = convert_episode_lead(old_text, "毛利蘭", 17, "FICTIONAL", "名探偵コナン")
    print(f"変換前: {old_text}")
    print(f"変換後: {new_text}")

    print("\n=== フォーマットチェックテスト ===")
    test_cases = [
        ("あなたと同じ45歳のとき、イチローは引退した。", "REAL", None),
        ("あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手大会に出場した。", "FICTIONAL", "名探偵コナン"),
        ("あなたと同じ17歳のとき、毛利蘭は空手大会に出場した。", "FICTIONAL", "名探偵コナン"),
    ]
    for text, ptype, wtitle in test_cases:
        is_valid, msg = check_episode_lead_format(text, ptype, wtitle)
        status = "✅" if is_valid else "❌"
        print(f"{status} {msg}: {text[:50]}...")
