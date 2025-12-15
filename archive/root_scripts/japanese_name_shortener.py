#!/usr/bin/env python3
"""
日本語人名の表示用短縮名生成
- 職業・年齢・性別に基づく適切な敬称の選択
- 文化的配慮と一貫性の両立
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

class JapaneseNameShortener:
    """日本語人名短縮名生成クラス"""

    def __init__(self):
        # 職業別敬称ルール
        self.occupation_honorifics = {
            'politician': '氏',           # 政治家
            'government_official': '氏',  # 公務員
            'scientist': '先生',         # 科学者
            'doctor': '先生',            # 医師
            'teacher': '先生',           # 教師
            'professor': '先生',         # 教授
            'artist': 'さん',            # 芸術家
            'actor': 'さん',             # 俳優
            'singer': 'さん',            # 歌手
            'athlete': '選手',           # スポーツ選手
            'business_person': '氏',     # ビジネスパーソン
            'writer': 'さん',            # 作家
            'musician': 'さん',          # 音楽家
            'default': 'さん'            # デフォルト
        }

        # 職業キーワードマッピング
        self.occupation_keywords = {
            'politician': ['政治家', '議員', '大臣', '知事', '市長', 'politician', 'minister', 'mayor'],
            'government_official': ['公務員', '官僚', 'official', 'bureaucrat'],
            'scientist': ['科学者', '研究者', 'scientist', 'researcher'],
            'doctor': ['医師', '医者', 'doctor', 'physician'],
            'teacher': ['教師', '先生', 'teacher', 'instructor'],
            'professor': ['教授', 'professor'],
            'artist': ['芸術家', '画家', 'artist', 'painter'],
            'actor': ['俳優', '女優', 'actor', 'actress'],
            'singer': ['歌手', 'singer', 'vocalist'],
            'athlete': ['選手', 'アスリート', 'athlete', 'player'],
            'business_person': ['実業家', '経営者', 'businessman', 'entrepreneur'],
            'writer': ['作家', '小説家', 'writer', 'author'],
            'musician': ['音楽家', 'musician', 'composer']
        }

        # 年齢別敬称ルール
        self.age_honorifics = {
            'child': 'ちゃん',           # 0-12歳
            'teen': 'くん/ちゃん',       # 13-19歳
            'young_adult': 'さん',       # 20-29歳
            'adult': 'さん',             # 30-59歳
            'senior': 'さん'             # 60歳以上
        }

        # 性別別敬称ルール
        self.gender_honorifics = {
            'male': {
                'child': 'くん',
                'teen': 'くん',
                'adult': 'さん',
                'senior': 'さん'
            },
            'female': {
                'child': 'ちゃん',
                'teen': 'ちゃん',
                'adult': 'さん',
                'senior': 'さん'
            }
        }

        # 分野別敬称ルール
        self.field_honorifics = {
            'politics': '氏',            # 政治
            'academia': '先生',          # 学術
            'entertainment': 'さん',     # 芸能
            'sports': '選手',            # スポーツ
            'business': '氏',            # ビジネス
            'arts': 'さん',              # 芸術
            'media': 'さん',             # メディア
            'default': 'さん'            # デフォルト
        }

    def detect_occupation_category(self, occupation: str) -> str:
        """
        職業からカテゴリを判定

        Args:
            occupation: 職業文字列

        Returns:
            職業カテゴリ
        """
        if not occupation:
            return 'default'

        occupation_lower = occupation.lower()

        for category, keywords in self.occupation_keywords.items():
            for keyword in keywords:
                if keyword.lower() in occupation_lower:
                    return category

        return 'default'

    def get_age_category(self, age: int) -> str:
        """
        年齢からカテゴリを判定

        Args:
            age: 年齢

        Returns:
            年齢カテゴリ
        """
        if age < 13:
            return 'child'
        elif age < 20:
            return 'teen'
        elif age < 30:
            return 'young_adult'
        elif age < 60:
            return 'adult'
        else:
            return 'senior'

    def get_appropriate_honorific(self, person: PersonInfo) -> str:
        """
        適切な敬称を決定

        Args:
            person: 人物情報

        Returns:
            適切な敬称
        """
        # 職業ベースの敬称を優先
        if person.occupation:
            occupation_category = self.detect_occupation_category(person.occupation)
            occupation_honorific = self.occupation_honorifics.get(occupation_category, 'さん')

            # 特殊な職業の場合は職業ベースを優先
            if occupation_category in ['politician', 'government_official', 'scientist', 'doctor', 'teacher', 'professor']:
                return occupation_honorific

        # 年齢・性別ベースの敬称
        if person.age and person.gender:
            age_category = self.get_age_category(person.age)
            gender_honorifics = self.gender_honorifics.get(person.gender, {})
            age_gender_honorific = gender_honorifics.get(age_category, 'さん')

            # 若年層の場合は年齢・性別ベースを優先
            if age_category in ['child', 'teen']:
                return age_gender_honorific

        # デフォルト
        return 'さん'

    def generate_short_name(self, person: PersonInfo) -> str:
        """
        短縮名を生成

        Args:
            person: 人物情報

        Returns:
            短縮名
        """
        honorific = self.get_appropriate_honorific(person)

        # 敬称なしの場合
        if not honorific:
            return person.name

        # 敬称を付ける
        return f"{person.name}{honorific}"

    def generate_short_name_no_honorific(self, person: PersonInfo) -> str:
        """
        敬称なしの短縮名を生成（エピソードデータ用）

        Args:
            person: 人物情報

        Returns:
            敬称なしの短縮名
        """
        # 敬称なしで名前のみを返す
        return person.name

    def generate_short_name_batch(self, people: list[PersonInfo]) -> list[tuple[str, str]]:
        """
        複数人物の短縮名を一括生成

        Args:
            people: 人物情報のリスト

        Returns:
            (元の名前, 短縮名)のタプルのリスト
        """
        results = []
        for person in people:
            short_name = self.generate_short_name(person)
            results.append((person.name, short_name))
        return results

    def generate_short_name_batch_no_honorific(self, people: list[PersonInfo]) -> list[tuple[str, str]]:
        """
        複数人物の敬称なし短縮名を一括生成（エピソードデータ用）

        Args:
            people: 人物情報のリスト

        Returns:
            (元の名前, 敬称なし短縮名)のタプルのリスト
        """
        results = []
        for person in people:
            short_name = self.generate_short_name_no_honorific(person)
            results.append((person.name, short_name))
        return results

def main():
    """メイン処理"""
    shortener = JapaneseNameShortener()

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

    print("=== 日本語人名短縮名生成テスト ===")
    print()

    for person in test_cases:
        short_name = shortener.generate_short_name(person)
        honorific = shortener.get_appropriate_honorific(person)

        print(f"名前: {person.name}")
        print(f"職業: {person.occupation or '不明'}")
        print(f"年齢: {person.age or '不明'}歳")
        print(f"性別: {person.gender or '不明'}")
        print(f"選択された敬称: {honorific}")
        print(f"短縮名: {short_name}")
        print("-" * 40)

    # 一括処理のテスト
    print("\n=== 一括処理テスト ===")
    batch_results = shortener.generate_short_name_batch(test_cases)

    for original, short in batch_results:
        print(f"{original} → {short}")

if __name__ == "__main__":
    main()
