#!/usr/bin/env python3
"""
groups_database.jsonに60の新しいお笑いグループを追加
現在のCSVから自動抽出して追加
"""
import pandas as pd
import json
import re
from collections import defaultdict
from datetime import datetime

def extract_groups_from_csv():
    # 修正済みのCSVを読み込み
    df = pd.read_csv('ultra_think_WRONG_GROUPS_FIXED.csv')
    
    # お笑い芸人のみフィルタ
    comedians = df[df['occupation'] == 'お笑い芸人'].copy()
    
    # グループ名を抽出（括弧内の文字列）
    group_members = defaultdict(list)
    
    for _, row in comedians.iterrows():
        display_name = str(row['person_name_display'])
        # 括弧内のグループ名を抽出
        match = re.search(r'(.+?)\s*\((.+?)\)', display_name)
        if match:
            member_name = match.group(1).strip()
            group_name = match.group(2).strip()
            group_members[group_name].append(member_name)
    
    return group_members

def load_existing_groups():
    """既存のgroups_database.jsonを読み込み"""
    try:
        with open('groups_database.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def merge_groups(existing, new_groups):
    """既存のグループと新しいグループをマージ"""
    merged = existing.copy()
    
    for group_name, members in new_groups.items():
        if group_name in merged:
            # 既存グループにメンバーを追加（重複除外）
            existing_members = set(merged[group_name])
            all_members = existing_members.union(set(members))
            merged[group_name] = sorted(list(all_members))
        else:
            # 新規グループとして追加
            merged[group_name] = sorted(members)
    
    return merged

def main():
    print("📊 CSVからお笑いグループを抽出中...")
    new_groups = extract_groups_from_csv()
    
    print(f"✅ {len(new_groups)}個のグループを検出")
    
    # 主要な新規グループのリスト（手動追加分）
    additional_groups = {
        "ぼる塾": ["あんり", "きりやはるか", "はるか", "田辺智加"],
        "ぺこぱ": ["シュウペイ", "松陰寺太勇"],
        "EXIT": ["りんたろー。", "兼近大樹"],
        "見取り図": ["盛山晋太郎", "リリー"],
        "ハナコ": ["岡部大", "秋山寛貴", "菊田竜大"],
        "3時のヒロイン": ["かなで", "ゆめっち", "福田麻貴"],
        "空気階段": ["水川かたまり", "鈴木もぐら"],
        "ミルクボーイ": ["駒場孝", "内海崇"],
        "霜降り明星": ["せいや", "粗品"],
        "かまいたち": ["山内健司", "濱家隆一"],
        "和牛": ["水田信二", "川西賢志郎"],
        "マヂカルラブリー": ["野田クリスタル", "村上"],
        "錦鯉": ["長谷川雅紀", "渡辺隆"],
        "ウエストランド": ["井口浩之", "河本太"],
        "とろサーモン": ["久保田かずのぶ", "村田秀亮"],
        "コロコロチキチキペッパーズ": ["ナダル", "西野創人"],
        "ニューヨーク": ["嶋佐和也", "屋敷裕政"],
        "ラランド": ["サーヤ", "ニシダ"],
        "オズワルド": ["畠中悠", "伊藤俊介"],
        "蛙亭": ["岩倉美里", "中野周平"],
        "インディアンス": ["田渕章裕", "きむ"],
        "ゆにばーす": ["はら", "川瀬名人"],
        "天竺鼠": ["瀬下豊", "川原克己"],
        "アインシュタイン": ["稲田直樹", "河井ゆずる"],
        "ミキ": ["昴生", "亜生"],
        "祇園": ["木﨑太郎", "櫻井健一朗"],
        "からし蓮根": ["伊織", "杉本青空"],
        "ダイタク": ["吉本大", "板垣卓也"],
        "男性ブランコ": ["平井まさあき", "浦井のりひろ"],
        "さや香": ["新山士彦", "石井誠一"],
        "ロングコートダディ": ["堂前透", "兎"],
        "真空ジェシカ": ["ガク", "川北茂澄"],
        "令和ロマン": ["松井ケムリ", "高比良くるま"],
        "ヨネダ2000": ["誠", "愛"],
        "カベポスター": ["永見大吾", "浜田順平"],
        "ママタルト": ["檜原洋平", "大鶴肥満"],
        "エルフ": ["荒川", "はる"],
        "おいでやすこが": ["おいでやす小田", "こがけん"],
        "きつね": ["淡路", "大津"],
        "どぶろっく": ["江口直人", "森慎太郎"],
    }
    
    # CSVから抽出したグループと手動追加分をマージ
    for group, members in additional_groups.items():
        if group in new_groups:
            new_groups[group] = list(set(new_groups[group] + members))
        else:
            new_groups[group] = members
    
    # 既存のgroups_database.jsonを読み込み
    print("\n📂 既存のgroups_database.jsonを読み込み中...")
    existing_groups = load_existing_groups()
    print(f"  既存グループ数: {len(existing_groups)}")
    
    # グループをマージ
    merged_groups = merge_groups(existing_groups, new_groups)
    
    # バックアップを作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    with open(f'groups_database_backup_{timestamp}.json', 'w', encoding='utf-8') as f:
        json.dump(existing_groups, f, ensure_ascii=False, indent=2)
    
    # 更新済みのデータベースを保存
    with open('groups_database.json', 'w', encoding='utf-8') as f:
        json.dump(merged_groups, f, ensure_ascii=False, indent=2)
    
    # 統計を表示
    new_count = len(merged_groups) - len(existing_groups)
    print(f"\n✅ groups_database.jsonを更新しました")
    print(f"  新規追加グループ数: {new_count}")
    print(f"  合計グループ数: {len(merged_groups)}")
    
    # 新規追加されたグループのリストを表示
    new_group_names = set(merged_groups.keys()) - set(existing_groups.keys())
    if new_group_names:
        print("\n🆕 新規追加されたグループ:")
        for group in sorted(new_group_names)[:20]:  # 最初の20個を表示
            members = merged_groups[group]
            print(f"  - {group}: {', '.join(members[:3])}{'...' if len(members) > 3 else ''}")
        if len(new_group_names) > 20:
            print(f"  ... 他{len(new_group_names) - 20}グループ")
    
    return merged_groups, new_count

if __name__ == "__main__":
    groups, count = main()