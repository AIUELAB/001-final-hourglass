#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
エピソード検証システム
日本語エピソードの包括的なバリデーション機能を提供
"""

from typing import Dict, List, Tuple, Optional
import re


class EpisodeValidator:
    """エピソード検証クラス"""

    # 有効な文末パターン（動詞・形容詞・形容動詞）
    VALID_ENDINGS = [
        # 過去形動詞
        'した', 'った', 'んだ', 'いた', 'えた', 'めた', 'せた', 'れた',
        # 現在形動詞
        'する', 'いる', 'ある', 'なる', 'れる', 'せる',
        # 形容詞
        'しい', 'ない', 'たい', 'よい', 'すい',
        # 特定の動詞句
        'を残した', 'を築いた', 'に貢献した', 'を成し遂げた',
        'を果たした', 'に成功した', 'を実現した', 'を達成した',
        'を示した', 'を続けた', 'を広めた', 'に至った',
        'を収めた', 'となった', 'を遂げた', 'に立った',
        'を刻んだ', 'を残している', 'を続けている'
    ]

    # 無効な文末パターン（名詞）
    INVALID_ENDINGS = [
        # 人物を表す名詞
        '者', '家', '人', '官', '師', '手', '員', '長', '王', '士',
        # 物事を表す名詞
        '賞', '作', '品', '業', '場', '国', '界', '体', '物', '代',
        # 職業・役職
        '監督', '選手', '教授', '社長', '会長', '総理', '大臣',
        # その他の名詞
        '天才', '巨匠', '先駆者', '第一人者', '創始者'
    ]

    # 文末修正マッピング
    ENDING_FIXES = {
        "作曲家": "作曲家として活躍した",
        "起業家": "起業家として成功を収めた",
        "研究者": "研究者として大きく貢献した",
        "科学者": "科学者として功績を残した",
        "外交官": "外交官として活躍した",
        "指揮者": "指揮者として名を残した",
        "経営者": "経営者として成功を収めた",
        "天才": "天才と呼ばれた",
        "日本人": "日本人として誇りを示した",
        "選手": "選手として活躍した",
        "監督": "監督として成功を収めた",
        "教授": "教授として後進を育成した",
        "巨匠": "巨匠と呼ばれるようになった",
        "先駆者": "先駆者として道を切り開いた",
        "第一人者": "第一人者として認められた"
    }

    @classmethod
    def validate_sentence_ending(cls, text: str) -> Tuple[bool, str]:
        """
        文末が動詞・形容詞・形容動詞で終わることを確認

        Returns:
            (is_valid, reason)
        """
        # 句点を除去
        clean_text = text.rstrip('。')

        # 無効な文末パターンをチェック
        for invalid_ending in cls.INVALID_ENDINGS:
            if clean_text.endswith(invalid_ending):
                return False, f"名詞「{invalid_ending}」で終わっています"

        # 有効な文末パターンをチェック
        for valid_ending in cls.VALID_ENDINGS:
            if clean_text.endswith(valid_ending):
                return True, "適切な動詞・形容詞で終わっています"

        # デフォルトチェック（最後の文字が動詞活用語尾か）
        last_char = clean_text[-1] if clean_text else ''
        verb_endings = 'たるうくぐすつぬぶむ'
        if last_char in verb_endings:
            return True, f"動詞語尾「{last_char}」で終わっています"

        return False, "文末が名詞の可能性があります"

    @classmethod
    def validate_character_count(cls, text: str) -> Tuple[bool, str]:
        """文字数検証（140-200文字）"""
        count = len(text)
        if count < 140:
            return False, f"文字数不足: {count}文字（最低140文字必要）"
        elif count > 200:
            return False, f"文字数超過: {count}文字（最大200文字）"
        return True, f"適切な文字数: {count}文字"

    @classmethod
    def validate_starts_with(cls, text: str) -> Tuple[bool, str]:
        """開始文検証"""
        if text.startswith("あなたと同じ"):
            return True, "正しく「あなたと同じ」で開始"
        return False, "「あなたと同じ」で開始していません"

    @classmethod
    def validate_contains_numbers(cls, text: str) -> Tuple[bool, str]:
        """数字検証（3桁以上）"""
        digit_count = sum(c.isdigit() for c in text)
        if digit_count >= 3:
            return True, f"数字を{digit_count}個含んでいます"
        return False, f"数字不足: {digit_count}個（最低3個必要）"

    @classmethod
    def validate_episode(cls, text: str) -> Dict[str, Tuple[bool, str]]:
        """
        エピソードの包括的検証

        Returns:
            各検証項目の結果を含む辞書
        """
        return {
            "sentence_ending": cls.validate_sentence_ending(text),
            "character_count": cls.validate_character_count(text),
            "starts_with": cls.validate_starts_with(text),
            "contains_numbers": cls.validate_contains_numbers(text)
        }

    @classmethod
    def is_valid_episode(cls, text: str) -> bool:
        """エピソードが全検証を通過するか確認"""
        validations = cls.validate_episode(text)
        return all(result[0] for result in validations.values())

    @classmethod
    def fix_sentence_ending(cls, text: str) -> str:
        """名詞で終わる文を動詞・形容詞で終わるよう修正"""

        # 句点を一時的に除去
        has_period = text.endswith('。')
        clean_text = text.rstrip('。')

        # 既知の修正パターンを適用
        for noun_ending, verb_phrase in cls.ENDING_FIXES.items():
            if clean_text.endswith(noun_ending):
                # 名詞部分を動詞句に置換
                fixed_text = clean_text[:-len(noun_ending)] + verb_phrase
                return fixed_text + ('。' if has_period else '')

        # 汎用的な修正（名詞で終わる場合）
        is_valid, reason = cls.validate_sentence_ending(clean_text)
        if not is_valid:
            # 最後の単語を分析
            words = clean_text.split('、')[-1].split('。')[-1]

            # 一般的な修正パターン
            for invalid_ending in cls.INVALID_ENDINGS:
                if words.endswith(invalid_ending):
                    fixed_text = clean_text + "として歴史に名を刻んだ"
                    return fixed_text + ('。' if has_period else '')

        # 修正不要または修正できない場合はそのまま返す
        return text

    @classmethod
    def auto_fix_episode(cls, text: str) -> Tuple[str, List[str]]:
        """
        エピソードを自動修正

        Returns:
            (修正済みテキスト, 修正内容のリスト)
        """
        fixes_applied = []
        fixed_text = text

        # 1. 開始文の修正
        is_valid, _ = cls.validate_starts_with(fixed_text)
        if not is_valid:
            fixed_text = "あなたと同じ" + fixed_text
            fixes_applied.append("開始文を追加")

        # 2. 文末の修正
        is_valid, _ = cls.validate_sentence_ending(fixed_text)
        if not is_valid:
            original_ending = fixed_text
            fixed_text = cls.fix_sentence_ending(fixed_text)
            if original_ending != fixed_text:
                fixes_applied.append("文末を動詞・形容詞に修正")

        # 3. 文字数の調整（簡易的な調整のみ）
        is_valid, reason = cls.validate_character_count(fixed_text)
        if not is_valid:
            if "不足" in reason:
                fixes_applied.append("文字数不足（手動調整が必要）")
            else:
                fixes_applied.append("文字数超過（手動調整が必要）")

        # 4. 数字の確認（自動追加は困難なので警告のみ）
        is_valid, _ = cls.validate_contains_numbers(fixed_text)
        if not is_valid:
            fixes_applied.append("数字不足（手動追加が必要）")

        return fixed_text, fixes_applied


def validate_batch(episodes: List[Dict]) -> Dict[str, any]:
    """バッチ全体の検証"""
    results = {
        "total": len(episodes),
        "valid": 0,
        "invalid": 0,
        "issues": [],
        "details": []
    }

    for i, episode in enumerate(episodes):
        text = episode.get("episode_text", episode.get("text", ""))
        name = episode.get("person_name", episode.get("name", f"Episode {i+1}"))

        validation = EpisodeValidator.validate_episode(text)
        is_valid = all(result[0] for result in validation.values())

        if is_valid:
            results["valid"] += 1
        else:
            results["invalid"] += 1
            issues = [reason for valid, reason in validation.values() if not valid]
            results["issues"].append({
                "name": name,
                "issues": issues
            })

        results["details"].append({
            "name": name,
            "valid": is_valid,
            "validation": validation
        })

    results["valid_rate"] = (results["valid"] / results["total"]) * 100 if results["total"] > 0 else 0

    return results


if __name__ == "__main__":
    # テスト用サンプル
    test_episodes = [
        "あなたと同じ41歳のとき、黒澤明は『羅生門』で1951年にヴェネツィア国際映画祭金獅子賞を受賞した。日本映画として初めて国際的評価を獲得し、世界に日本映画の存在を知らしめた。複数の視点から真実を描く斬新な構成は、世界の映画界に衝撃を与えた。",
        "あなたと同じ47歳のとき、久石譲は『もののけ姫』で日本アカデミー賞最優秀音楽賞を受賞した。宮崎駿作品の音楽を30年以上手がけ、世界中のファンを魅了。年間100回以上のコンサートで指揮を執り、クラシックと映画音楽の垣根を超えた。日本音楽を世界に広めた現代最高の作曲家。"
    ]

    print("エピソード検証システム テスト")
    print("=" * 60)

    for i, episode in enumerate(test_episodes, 1):
        print(f"\nエピソード {i}:")
        print(f"文字数: {len(episode)}")

        validation = EpisodeValidator.validate_episode(episode)
        for check_name, (is_valid, reason) in validation.items():
            status = "✅" if is_valid else "❌"
            print(f"  {status} {check_name}: {reason}")

        if not validation["sentence_ending"][0]:
            fixed_text = EpisodeValidator.fix_sentence_ending(episode)
            print(f"\n修正後: ...{fixed_text[-50:]}")