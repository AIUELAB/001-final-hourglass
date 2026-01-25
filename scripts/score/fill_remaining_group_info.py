#!/usr/bin/env python3
"""
残り59件のis_group_member未設定を手動マッピングで補完
Web検索結果に基づく確定情報を使用
"""

import pandas as pd
from datetime import datetime
import shutil

# グループ情報マッピング（Web検索結果に基づく）
GROUP_MAPPING = {
    # === ONE PIECE - 麦わらの一味 ===
    "モンキー・D・ルフィ": ("麦わらの一味", True),
    "ロロノア・ゾロ": ("麦わらの一味", True),
    "ナミ": ("麦わらの一味", True),
    "サンジ": ("麦わらの一味", True),
    "トニートニー・チョッパー": ("麦わらの一味", True),
    "ニコ・ロビン": ("麦わらの一味", True),
    # === 鬼滅の刃 - 鬼殺隊 ===
    "竈門炭治郎": ("鬼殺隊", True),
    "竈門禰豆子": ("鬼殺隊", True),
    "胡蝶しのぶ": ("鬼殺隊・柱", True),
    # === NARUTO ===
    "うずまきナルト": ("第七班", True),
    "うちはサスケ": ("第七班", True),
    "はたけカカシ": ("第七班", True),
    # === ドラゴンボール ===
    "孫悟空": (None, False),  # 個人
    "孫悟飯": (None, False),  # 個人
    # === 名探偵コナン ===
    "江戸川コナン": ("少年探偵団", True),
    "工藤新一": (None, False),  # 個人
    "毛利小五郎": ("毛利探偵事務所", True),
    "毛利蘭": (None, False),  # 個人
    # === その他アニメキャラクター（個人活動） ===
    "ドラえもん": (None, False),  # 個人キャラ
    "フグ田サザエ": ("磯野家", True),
    "サザエさん": ("磯野家", True),
    "クレヨンしんちゃん（野原しんのすけ）": ("野原家", True),
    "鉄腕アトム": (None, False),  # 個人
    "ルパン三世": ("ルパン一味", True),
    "碇シンジ": ("NERV", True),
    "ガンダム（RX-78-2）": (None, False),  # メカ
    "アンパンマン": (None, False),  # 個人
    "ウルトラマン": ("ウルトラ兄弟", True),
    "セーラームーン（月野うさぎ）": ("セーラー戦士", True),
    "マリオ": (None, False),  # 個人
    "ピカチュウ": (None, False),  # 個人（サトシのパートナー）
    "サトシ": (None, False),  # 個人
    "ケンシロウ": (None, False),  # 個人
    "緋村剣心": (None, False),  # 個人
    "ティファ・ロックハート": ("アバランチ", True),
    "セフィロス": (None, False),  # 個人（敵キャラ）
    # === VTuber ===
    "キズナアイ": (None, False),  # バーチャルYouTuber個人
    "輝夜月": (None, False),  # VTuber個人
    "ミライアカリ": (None, False),  # VTuber個人
    "にじさんじ": (None, False),  # これはグループ名そのもの
    "ホロライブ": (None, False),  # これはグループ名そのもの
    # === 音楽 ===
    "初音ミク": ("ピアプロキャラクターズ", True),  # クリプトン社のキャラクター群
    "BLACKPINK": (None, False),  # これはグループ名そのもの（個人ではない）
    # === 一般人（情報不足→ソロ扱い） ===
    "福井谷祐子": (None, False),
    "田中信行": (None, False),
    "中村美紀": (None, False),
    "山田恵子": (None, False),
    "山本義彦": (None, False),
    "小川桂子": (None, False),
    "小田原淳": (None, False),
    "北野日奈子": ("乃木坂46", True),  # 乃木坂46元メンバー
}


def main():
    csv_path = "/Users/admin/Documents/AIUELAB/001-final-hourglass/preserved/data/MASTER_EPISODES_CURRENT.csv"

    # バックアップ
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = csv_path.replace(".csv", f"_backup_manual_fill_{timestamp}.csv")
    shutil.copy(csv_path, backup_path)
    print(f"📦 バックアップ: {backup_path}")

    # CSV読み込み
    df = pd.read_csv(csv_path)
    print(f"📊 読み込み完了: {len(df)}件")

    # 未設定件数
    before_count = df["is_group_member"].isna().sum()
    print(f"🎯 未設定件数: {before_count}件")

    # マッピング適用
    updated = 0
    for person_name, (group_name, is_member) in GROUP_MAPPING.items():
        mask = (df["person_name"] == person_name) & (df["is_group_member"].isna())
        if mask.any():
            df.loc[mask, "is_group_member"] = is_member
            df.loc[mask, "group_name"] = group_name if group_name else ""
            count = mask.sum()
            updated += count
            status = f"所属({group_name})" if is_member else "無所属"
            print(f"  ✅ {person_name}: {status} ({count}件)")

    # 保存
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n💾 保存完了: {csv_path}")

    # 結果
    after_count = df["is_group_member"].isna().sum()
    print("\n📈 結果:")
    print(f"  更新前未設定: {before_count}件")
    print(f"  更新後未設定: {after_count}件")
    print(f"  更新件数: {updated}件")

    # 設定率
    total = len(df)
    set_count = total - after_count
    print(f"\n✅ is_group_member設定率: {set_count / total * 100:.1f}% ({set_count}/{total}件)")

    if after_count == 0:
        print("\n🎉 100%達成！")


if __name__ == "__main__":
    main()
