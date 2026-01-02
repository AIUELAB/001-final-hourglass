#!/usr/bin/env python3
"""
同一人物の重複PERSON ID検出スクリプト。

芸名/本名、別表記などで重複登録されている人物を検出する。
"""

import pandas as pd
from pathlib import Path

# 禁止カテゴリプレフィックス
FORBIDDEN_PREFIXES = [
    "歌舞伎",
    "落語",
    "漫才",
    "俳優",
    "女優",
    "歌手",
    "作家",
    "画家",
    "音楽家",
    "政治家",
    "科学者",
    "哲学者",
    "漫画家",
    "小説家",
    "詩人",
    "映画監督",
    "実業家",
    "武将",
    "大名",
    "天皇",
    "皇后",
    "王",
    "皇帝",
]

# 既知の同一人物パターン（短縮名/芸名→正式名）
# 統合済み: 2025-12-24 に113クラスター統合完了
KNOWN_ALIASES = {
    # 芸名→本名（例外として分離維持）
    "ビートたけし": "北野武",  # 例外: 分離維持
    "タモリ": "森田一義",  # 例外: 分離維持
    # 統合済みパターン（監視用）
    "チャップリン": "チャーリー・チャップリン",
    "キング牧師": "キング牧師",  # 正式名として採用
    "ホーキング": "スティーブン・ホーキング",
    "チャーチル": "ウィンストン・チャーチル",
    "ヒカキン": "HIKAKIN",
    "Aimyon": "あいみょん",
    # 短縮名→正式名
    "北斎": "葛飾北斎",
    "ベートーヴェン": "ルートヴィヒ・ヴァン・ベートーヴェン",
    "モーツァルト": "ヴォルフガング・アマデウス・モーツァルト",
    "ダ・ヴィンチ": "レオナルド・ダ・ヴィンチ",
    "ピカソ": "パブロ・ピカソ",
    # ========================================
    # ローマ字/カタカナ表記→正式名（2026-01-03追加）
    # 日本人名の正規化: 漢字表記を正式名とする
    # ========================================
    # 映画監督
    "アキラ・クロサワ": "黒澤明",
    "Akira Kurosawa": "黒澤明",
    "ヤスジロウ・オズ": "小津安二郎",
    "Yasujiro Ozu": "小津安二郎",
    "ケンジ・ミゾグチ": "溝口健二",
    "Kenji Mizoguchi": "溝口健二",
    "ハヤオ・ミヤザキ": "宮崎駿",
    "Hayao Miyazaki": "宮崎駿",
    "イサオ・タカハタ": "高畑勲",
    "Isao Takahata": "高畑勲",
    "タケシ・キタノ": "北野武",
    "Takeshi Kitano": "北野武",
    "ヒデオ・コジマ": "小島秀夫",
    "Hideo Kojima": "小島秀夫",
    # 作家・文学者
    "ハルキ・ムラカミ": "村上春樹",
    "Haruki Murakami": "村上春樹",
    "ユキオ・ミシマ": "三島由紀夫",
    "Yukio Mishima": "三島由紀夫",
    "ヤスナリ・カワバタ": "川端康成",
    "Yasunari Kawabata": "川端康成",
    "ケンザブロウ・オオエ": "大江健三郎",
    "Kenzaburo Oe": "大江健三郎",
    "リュウノスケ・アクタガワ": "芥川龍之介",
    "Ryunosuke Akutagawa": "芥川龍之介",
    "ソウセキ・ナツメ": "夏目漱石",
    "Soseki Natsume": "夏目漱石",
    "オサム・ダザイ": "太宰治",
    "Osamu Dazai": "太宰治",
    # 漫画家・アニメーター
    "オサム・テヅカ": "手塚治虫",
    "Osamu Tezuka": "手塚治虫",
    "アキラ・トリヤマ": "鳥山明",
    "Akira Toriyama": "鳥山明",
    "ルミコ・タカハシ": "高橋留美子",
    "Rumiko Takahashi": "高橋留美子",
    "エイイチロウ・オダ": "尾田栄一郎",
    "Eiichiro Oda": "尾田栄一郎",
    # 音楽家
    "リュウイチ・サカモト": "坂本龍一",
    "Ryuichi Sakamoto": "坂本龍一",
    "ヨウコ・オノ": "オノ・ヨーコ",
    "Yoko Ono": "オノ・ヨーコ",
    "セイジ・オザワ": "小澤征爾",
    "Seiji Ozawa": "小澤征爾",
    # 科学者・学者
    "シンヤ・ヤマナカ": "山中伸弥",
    "Shinya Yamanaka": "山中伸弥",
    # 実業家
    "アキオ・モリタ": "盛田昭夫",
    "Akio Morita": "盛田昭夫",
    "ソウイチロウ・ホンダ": "本田宗一郎",
    "Soichiro Honda": "本田宗一郎",
    "コウノスケ・マツシタ": "松下幸之助",
    "Konosuke Matsushita": "松下幸之助",
    # 歴史的人物
    "ヒデヨシ・トヨトミ": "豊臣秀吉",
    "Hideyoshi Toyotomi": "豊臣秀吉",
    "イエヤス・トクガワ": "徳川家康",
    "Ieyasu Tokugawa": "徳川家康",
    "ノブナガ・オダ": "織田信長",
    "Nobunaga Oda": "織田信長",
}


def detect_duplicates(csv_path: Path) -> list[dict]:
    """重複の可能性がある人物を検出"""
    df = pd.read_csv(csv_path, low_memory=False)

    persons = (
        df.groupby("person_id")
        .agg(
            {
                "person_name": "first",
            }
        )
        .reset_index()
    )

    duplicates = []

    # 1. 既知のエイリアスをチェック
    for alias, real_name in KNOWN_ALIASES.items():
        alias_rows = persons[persons["person_name"] == alias]
        real_rows = persons[persons["person_name"] == real_name]

        if len(alias_rows) > 0 and len(real_rows) > 0:
            duplicates.append(
                {
                    "type": "known_alias",
                    "short": alias,
                    "short_id": alias_rows.iloc[0]["person_id"],
                    "full": real_name,
                    "full_id": real_rows.iloc[0]["person_id"],
                }
            )

    # 2. 部分一致検出（短い名前が長い名前に含まれる）
    names = persons["person_name"].tolist()
    ids = persons["person_id"].tolist()

    for i, short in enumerate(names):
        if len(short) < 2 or len(short) > 6:
            continue
        for j, full in enumerate(names):
            if i == j or len(full) <= len(short):
                continue
            if short in full and ids[i] != ids[j]:
                duplicates.append(
                    {
                        "type": "substring",
                        "short": short,
                        "short_id": ids[i],
                        "full": full,
                        "full_id": ids[j],
                    }
                )

    # 3. 禁止プレフィックス検出
    for pid, name in zip(ids, names):
        for prefix in FORBIDDEN_PREFIXES:
            if name.startswith(prefix + "・") or name.startswith(prefix + "　"):
                duplicates.append(
                    {
                        "type": "forbidden_prefix",
                        "short": prefix,
                        "short_id": pid,
                        "full": name,
                        "full_id": pid,
                    }
                )
                break

    return duplicates


def main():
    csv_path = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    print("=== 同一人物 重複PERSON ID検出 ===\n")

    duplicates = detect_duplicates(csv_path)

    known = [d for d in duplicates if d["type"] == "known_alias"]
    substr = [d for d in duplicates if d["type"] == "substring"]
    forbidden = [d for d in duplicates if d["type"] == "forbidden_prefix"]

    if forbidden:
        print(f"[禁止プレフィックス] {len(forbidden)}件 ⚠️ 要修正")
        for d in forbidden:
            print(f"  {d['full_id']}: {d['full']}")

    if known:
        print(f"\n[既知エイリアス] {len(known)}件")
        for d in known:
            print(f"  {d['short']} ({d['short_id']}) → {d['full']} ({d['full_id']})")

    if substr:
        print(f"\n[部分一致候補] {len(substr)}件 (要確認)")
        for d in substr[:20]:
            print(f"  {d['short']} ({d['short_id']}) ⊂ {d['full']} ({d['full_id']})")
        if len(substr) > 20:
            print(f"  ... 他{len(substr)-20}件")

    if not duplicates:
        print("問題は検出されませんでした。")


if __name__ == "__main__":
    main()
