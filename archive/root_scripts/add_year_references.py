#!/usr/bin/env python3
"""
年代表記が不足しているエピソードに具体的な年を追加
客観的事実として実際の年代を明記する
"""

import csv
import re
from datetime import datetime

# 各人物の重要な年代データ
PERSON_YEARS = {
    "Ado": {"age": 21, "year": 2023, "birth": 2002},
    "HIKAKIN": {"age": 30, "year": 2019, "birth": 1989},
    "YOSHIKI": {"age": 23, "year": 1989, "birth": 1965},
    "あいみょん": {"age": 23, "year": 2018, "birth": 1995},
    "イチロー": {"age": 27, "year": 2001, "birth": 1973},
    "イモトアヤコ": {"age": 27, "year": 2013, "birth": 1986},
    "オール阪神・巨人": {"age": 5, "year": 1980, "birth": 1975},  # 結成年
    "サカナクション": {"age": 5, "year": 2010, "birth": 2005},  # 結成年
    "ドリカム": {"age": 1989, "year": 1989, "birth": 1988},  # 結成年
    "ピカソ": {"age": 26, "year": 1907, "birth": 1881},
    "ヨハン・クライフ": {"age": 26, "year": 1973, "birth": 1947},
    "三島由紀夫": {"age": 23, "year": 1948, "birth": 1925},
    "上原浩治": {"age": 26, "year": 2001, "birth": 1975},
    "上田桃子": {"age": 21, "year": 2007, "birth": 1986},
    "五木ひろし": {"age": 22, "year": 1970, "birth": 1948},
    "伊調馨": {"age": 20, "year": 2004, "birth": 1984},
    "佐々木朗希": {"age": 20, "year": 2022, "birth": 2001},
    "佐藤健": {"age": 21, "year": 2010, "birth": 1989},
    "前澤友作": {"age": 44, "year": 2020, "birth": 1975},
    "北島康介": {"age": 21, "year": 2004, "birth": 1982},
    "又吉直樹": {"age": 23, "year": 2003, "birth": 1980},
    "古賀稔彦": {"age": 24, "year": 1992, "birth": 1967},
    "吉田栄作": {"age": 20, "year": 1989, "birth": 1969},
    "吉田秀彦": {"age": 23, "year": 1992, "birth": 1969},
    "吉田茂": {"age": 68, "year": 1946, "birth": 1878},
    "坂本九": {"age": 21, "year": 1963, "birth": 1941},
    "堀江貴文": {"age": 32, "year": 2004, "birth": 1972},
    "大久保佳代子": {"age": 28, "year": 2000, "birth": 1971},
    "大坂なおみ": {"age": 21, "year": 2019, "birth": 1997},
    "大島美幸": {"age": 29, "year": 2009, "birth": 1980},
    "大谷翔平": {"age": 23, "year": 2018, "birth": 1994},
    "大隅良典": {"age": 71, "year": 2016, "birth": 1945},
    "天海祐希": {"age": 27, "year": 1995, "birth": 1967},
    "太田光": {"age": 35, "year": 2000, "birth": 1965},
    "奈良美智": {"age": 41, "year": 2001, "birth": 1959},
    "孫正義": {"age": 39, "year": 1996, "birth": 1957},
    "安倍晋三": {"age": 52, "year": 2006, "birth": 1954},
    "宮崎駿": {"age": 44, "year": 1985, "birth": 1941},
    "宮里藍": {"age": 18, "year": 2003, "birth": 1985},
    "寺田心": {"age": 7, "year": 2015, "birth": 2008},
    "小室哲哉": {"age": 35, "year": 1994, "birth": 1958},
    "小林尊": {"age": 23, "year": 2001, "birth": 1978},
    "小泉純一郎": {"age": 59, "year": 2001, "birth": 1942},
    "山下泰裕": {"age": 27, "year": 1984, "birth": 1957},
    "山下智久": {"age": 20, "year": 2005, "birth": 1985},
    "山中伸弥": {"age": 50, "year": 2012, "birth": 1962},
    "岡田准一": {"age": 14, "year": 1995, "birth": 1980},
    "川島なお美": {"age": 29, "year": 1990, "birth": 1960},
    "市川海老蔵": {"age": 27, "year": 2004, "birth": 1977},
    "庵野秀明": {"age": 35, "year": 1995, "birth": 1960},
    "手塚治虫": {"age": 20, "year": 1949, "birth": 1928},
    "新垣結衣": {"age": 18, "year": 2006, "birth": 1988},
    "新庄剛志": {"age": 28, "year": 2000, "birth": 1972},
    "新海誠": {"age": 43, "year": 2016, "birth": 1973},
    "星野仙一": {"age": 41, "year": 1988, "birth": 1947},
    "星野源": {"age": 35, "year": 2016, "birth": 1981},
    "村上春樹": {"age": 30, "year": 1979, "birth": 1949},
    "村上隆": {"age": 38, "year": 2000, "birth": 1962},
    "村田兆治": {"age": 34, "year": 1983, "birth": 1949},
    "松井秀喜": {"age": 22, "year": 1996, "birth": 1974},
    "松任谷由実": {"age": 19, "year": 1973, "birth": 1954},
    "松山英樹": {"age": 29, "year": 2021, "birth": 1992},
    "松岡修造": {"age": 27, "year": 1995, "birth": 1967},
    "松本人志": {"age": 20, "year": 1983, "birth": 1963},
    "松田聖子": {"age": 18, "year": 1980, "birth": 1962},
    "柳井正": {"age": 35, "year": 1984, "birth": 1949},
    "桑田佳祐": {"age": 22, "year": 1978, "birth": 1956},
    "梨花": {"age": 20, "year": 1993, "birth": 1973},
    "椎名林檎": {"age": 20, "year": 1998, "birth": 1978},
    "横綱白鵬": {"age": 22, "year": 2007, "birth": 1985},
    "樹木希林": {"age": 31, "year": 1974, "birth": 1943},
    "武井壮": {"age": 37, "year": 2011, "birth": 1973},
    "池江璃花子": {"age": 18, "year": 2018, "birth": 2000},
    "沖縄": {"age": 27, "year": 1972, "birth": 1945},  # 復帰
    "沢村忠": {"age": 26, "year": 1969, "birth": 1943},
    "渡辺謙": {"age": 36, "year": 1995, "birth": 1959},
    "渡部建": {"age": 40, "year": 2012, "birth": 1972},
    "澤穂希": {"age": 21, "year": 1999, "birth": 1978},
    "瀬戸内寂聴": {"age": 51, "year": 1973, "birth": 1922},
    "牛田茂樹": {"age": 21, "year": 1963, "birth": 1942},
    "田中角栄": {"age": 54, "year": 1972, "birth": 1918},
    "甲本ヒロト": {"age": 22, "year": 1985, "birth": 1963},
    "白石麻衣": {"age": 20, "year": 2012, "birth": 1992},
    "石原さとみ": {"age": 16, "year": 2003, "birth": 1986},
    "石原慎太郎": {"age": 23, "year": 1956, "birth": 1932},
    "石川遼": {"age": 15, "year": 2007, "birth": 1991},
    "神木隆之介": {"age": 12, "year": 2005, "birth": 1993},
    "福原愛": {"age": 15, "year": 2004, "birth": 1988},
    "秋本治": {"age": 24, "year": 1976, "birth": 1952},
    "米津玄師": {"age": 21, "year": 2012, "birth": 1991},
    "紀里谷和明": {"age": 36, "year": 2004, "birth": 1968},
    "綾瀬はるか": {"age": 18, "year": 2004, "birth": 1985},
    "羽生善治": {"age": 26, "year": 1996, "birth": 1970},
    "羽生結弦": {"age": 19, "year": 2014, "birth": 1994},
    "草なぎ剛": {"age": 27, "year": 2001, "birth": 1974},
    "荒川静香": {"age": 24, "year": 2006, "birth": 1981},
    "落合陽一": {"age": 24, "year": 2011, "birth": 1987},
    "藤井フミヤ": {"age": 21, "year": 1983, "birth": 1962},
    "藤井聡太": {"age": 14, "year": 2016, "birth": 2002},
    "藤原竜也": {"age": 18, "year": 2000, "birth": 1982},
    "藤田ニコル": {"age": 18, "year": 2016, "birth": 1998},
    "西川きよし": {"age": 19, "year": 1966, "birth": 1946},
    "西野亮廣": {"age": 19, "year": 1999, "birth": 1980},
    "野口聡一": {"age": 40, "year": 2005, "birth": 1965},
    "野茂英雄": {"age": 26, "year": 1995, "birth": 1968},
    "錦織圭": {"age": 24, "year": 2014, "birth": 1989},
    "長嶋茂雄": {"age": 22, "year": 1958, "birth": 1936},
    "隈研吾": {"age": 30, "year": 1984, "birth": 1954},
    "高倉健": {"age": 29, "year": 1960, "birth": 1931},
    "高橋尚子": {"age": 28, "year": 2000, "birth": 1972},
    "黒木瞳": {"age": 22, "year": 1982, "birth": 1960},
    "黒澤明": {"age": 33, "year": 1943, "birth": 1910}
}

def add_year_to_episode(person_name: str, episode_text: str) -> str:
    """
    エピソードに年代を追加

    Returns:
        年代を追加したテキスト
    """
    # すでに年代が含まれているかチェック
    if re.search(r'(19|20)\d{2}年', episode_text):
        return episode_text

    # 人物データが存在しない場合
    if person_name not in PERSON_YEARS:
        return episode_text

    data = PERSON_YEARS[person_name]
    year = data["year"]
    age = data["age"]

    # エピソードの最初の文に年代を挿入
    # "あなたと同じX歳のとき" の後に年代を追加
    pattern = r'(あなたと同じ\d+歳のとき)(、)'
    replacement = rf'\1の{year}年\2'

    modified_text = re.sub(pattern, replacement, episode_text)

    # パターンがマッチしなかった場合の代替処理
    if modified_text == episode_text:
        # 最初の句点の前に年代を追加
        sentences = episode_text.split('。')
        if sentences:
            # 最初の文に年代を挿入する適切な位置を探す
            first_sentence = sentences[0]

            # 動詞の前に挿入（「した」「なった」など）
            verb_patterns = [
                (r'(を)(達成|獲得|記録|樹立|更新)', rf'\1{year}年に\2'),
                (r'(で)(優勝|制覇|勝利|成功)', rf'\1{year}年に\2'),
                (r'(として)(デビュー|登場|活躍)', rf'\1{year}年に\2'),
                (r'(に)(出場|参戦|登録|到達)', rf'\1{year}年に\2')
            ]

            for pattern, repl in verb_patterns:
                new_first = re.sub(pattern, repl, first_sentence)
                if new_first != first_sentence:
                    sentences[0] = new_first
                    return '。'.join(sentences)

    return modified_text

def fix_year_references():
    """年代表記を追加"""

    print("=" * 60)
    print("年代表記追加処理")
    print("=" * 60)

    # 最新の修正済みファイルを読み込み
    csv_file = 'episodes_fixed_complete_20250923_140509.csv'

    episodes = []
    with open(csv_file, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        episodes = list(reader)

    fixed_count = 0
    fix_log = []

    # 各エピソードを処理
    for episode in episodes:
        person_name = episode['person_name']
        original_text = episode['episode_text']

        # 年代を追加
        fixed_text = add_year_to_episode(person_name, original_text)

        if fixed_text != original_text:
            episode['episode_text'] = fixed_text
            episode['character_count'] = str(len(fixed_text))
            episode['created_date'] = datetime.now().strftime('%Y%m%d_%H%M%S')

            fixed_count += 1
            fix_log.append({
                'person_name': person_name,
                'year_added': PERSON_YEARS.get(person_name, {}).get('year', 'N/A')
            })

            print(f"✅ 年代追加: {person_name} ({PERSON_YEARS[person_name]['year']}年)")

    # 修正されたCSVを保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'episodes_with_years_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
        fieldnames = list(episodes[0].keys())
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(episodes)

    print(f"\n修正完了: {fixed_count}件")
    print(f"出力ファイル: {output_file}")

    # 検証：年代が追加されたか確認
    print("\n" + "=" * 60)
    print("年代表記検証")
    print("=" * 60)

    no_year_count = 0
    for episode in episodes:
        if not re.search(r'(19|20)\d{2}年', episode['episode_text']):
            no_year_count += 1
            print(f"⚠️ 年代なし: {episode['person_name']}")

    if no_year_count == 0:
        print("✅ すべてのエピソードに年代表記があります")
    else:
        print(f"⚠️ {no_year_count}件のエピソードに年代表記がありません")

    return output_file, fixed_count

if __name__ == "__main__":
    output_file, count = fix_year_references()

    if count > 0:
        print(f"\n✅ {count}件のエピソードに年代を追加しました")
