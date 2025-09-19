#!/usr/bin/env python3
"""
客観性を重視した日本語人名短縮名生成
- 敬称なしで客観性を保つ
- 文化的バイアスを排除
- データの一貫性を重視
"""

from dataclasses import dataclass


@dataclass
class PersonInfo:
    """人物情報"""
    name: str
    occupation: str | None = None
    age: int | None = None
    gender: str | None = None
    field: str | None = None

class ObjectiveNameShortener:
    """客観性を重視した人名短縮名生成クラス"""

    def __init__(self):
        # 敬称なしを基本とする
        self.use_honorifics = False

        # 短縮名のパターン（敬称なし、姓名を基本とする）
        self.shortening_patterns = {
            'default': 'full_name',      # フルネーム
            'family': 'family_name',     # 姓のみ（例：安倍、山中）
            'given': 'given_name',       # 下の名前のみ（例：晋三、伸弥）
            'nickname': 'nickname'       # ニックネーム（例：安倍、山中）
        }

    def generate_objective_name(self, person: PersonInfo, pattern: str = 'default') -> str:
        """
        客観的な短縮名を生成（敬称なし）

        Args:
            person: 人物情報
            pattern: 短縮パターン

        Returns:
            客観的な短縮名
        """
        if not person.name:
            return '[名前不明]'

        # 敬称なしで名前のみを返す
        if pattern == 'default':
            return person.name
        elif pattern == 'family':
            # 姓のみ（例：安倍、山中）
            return self.extract_family_name(person.name)
        elif pattern == 'given':
            # 下の名前のみ（例：晋三、伸弥）
            return self.extract_given_name(person.name)
        elif pattern == 'nickname':
            # ニックネーム（例：安倍、山中）
            return self.generate_nickname(person.name)
        else:
            return person.name

    def extract_given_name(self, full_name: str) -> str:
        """
        下の名前を抽出

        Args:
            full_name: フルネーム

        Returns:
            下の名前
        """
        # 日本語の名前の場合
        if any(ord(char) > 127 for char in full_name):
            # 漢字・ひらがな・カタカナの名前
            if len(full_name) >= 2:
                return full_name[1:]  # 2文字目以降
            else:
                return full_name
        else:
            # 英語の名前の場合
            parts = full_name.split()
            if len(parts) >= 2:
                return parts[1]  # 2番目の部分
            else:
                return full_name

    def extract_family_name(self, full_name: str) -> str:
        """
        姓を抽出

        Args:
            full_name: フルネーム

        Returns:
            姓
        """
        # 日本語の名前の場合
        if any(ord(char) > 127 for char in full_name):
            # 漢字・ひらがな・カタカナの名前
            if len(full_name) >= 2:
                # 2文字の姓を優先（例：安倍、山中、三浦、大谷、田中）
                if len(full_name) >= 3:
                    return full_name[:2]  # 最初の2文字
                else:
                    return full_name[0]  # 1文字の場合は1文字目
            else:
                return full_name
        else:
            # 英語の名前の場合
            parts = full_name.split()
            if len(parts) >= 2:
                return parts[0]  # 1番目の部分
            else:
                return full_name

    def generate_nickname(self, full_name: str) -> str:
        """
        ニックネームを生成

        Args:
            full_name: フルネーム

        Returns:
            ニックネーム
        """
        # 日本語の名前の場合
        if any(ord(char) > 127 for char in full_name):
            # 漢字・ひらがな・カタカナの名前
            if len(full_name) >= 3:
                return full_name[:2]  # 最初の2文字
            else:
                return full_name
        else:
            # 英語の名前の場合
            parts = full_name.split()
            if len(parts) >= 2:
                return parts[0][:3]  # 姓の最初の3文字
            else:
                return full_name[:3] if len(full_name) >= 3 else full_name

    def generate_batch_objective_names(self, people: list[PersonInfo], pattern: str = 'default') -> list[tuple[str, str]]:
        """
        複数人物の客観的な短縮名を一括生成

        Args:
            people: 人物情報のリスト
            pattern: 短縮パターン

        Returns:
            (元の名前, 客観的短縮名)のタプルのリスト
        """
        results = []
        for person in people:
            objective_name = self.generate_objective_name(person, pattern)
            results.append((person.name, objective_name))
        return results

def main():
    """メイン処理"""
    shortener = ObjectiveNameShortener()

    # テストケース
    test_cases = [
        PersonInfo("安倍晋三", "政治家", 67, "male", "politics"),
        PersonInfo("山中伸弥", "科学者", 60, "male", "academia"),
        PersonInfo("三浦春馬", "俳優", 30, "male", "entertainment"),
        PersonInfo("大谷翔平", "野球選手", 29, "male", "sports"),
        PersonInfo("田中太郎", "会社員", 35, "male", "business"),
        PersonInfo("佐藤花子", "学生", 16, "female", "education"),
        PersonInfo("鈴木一郎", "医師", 45, "male", "medical"),
        PersonInfo("高橋美咲", "歌手", 25, "female", "entertainment"),
        PersonInfo("伊藤健太", "小学生", 10, "male", "education"),
        PersonInfo("渡辺真理", "作家", 55, "female", "arts")
    ]

    print("=== 客観性を重視した短縮名生成テスト ===")
    print("🔤 敬称なしで文化的バイアスを排除")
    print()

    # 各パターンでの短縮名生成
    patterns = ['default', 'family', 'given', 'nickname']

    for pattern in patterns:
        print(f"📝 パターン: {pattern}")
        batch_results = shortener.generate_batch_objective_names(test_cases, pattern)

        for original, short in batch_results[:5]:  # 最初の5件のみ表示
            print(f"  {original} → {short}")
        print()

    print("✅ 客観性を保った短縮名生成が完了しました")
    print("🎯 敬称なしにより、文化的バイアスや主観性を排除")
    print("🔍 データの一貫性と公平性を重視")

if __name__ == "__main__":
    main()
