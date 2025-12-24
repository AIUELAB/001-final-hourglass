#!/usr/bin/env python3
"""
コンビ/グループ名エピソードを個人に変換

Phase 10: 個人専用エピソード化
"""

import pandas as pd
from datetime import datetime

# 変換設定
CONVERSIONS = {
    # === 削除（個人に帰属不可） ===
    "DELETE": [
        "EP-000000918",  # BAD HOP（グループ全体）
        "EP-000002395",  # ゆでたまご（二人組）
        "EP-000003756",  # ダフト・パンク（二人組）
        "EP-000006646",  # 林家ペー・パー子（二人組）
    ],
    # === PERSON ID統合（既存個人IDへ移動） ===
    "MERGE": {
        "EP-000004252": {  # ワンダイレクション → ハリー・スタイルズ
            "new_person_id": "P2E813C0",
            "new_person_name": "ハリー・スタイルズ",
        },
        "EP-000004484": {  # クラッシュ・ギャルズ → 長与千種
            "new_person_id": "P8041695",
            "new_person_name": "長与千種",
        },
        "EP-000007954": {  # ナイナイ・矢部浩之 → 矢部浩之
            "new_person_id": "PF566BFB",
            "new_person_name": "矢部浩之",
        },
    },
    # === 名前変更のみ（グループプレフィックス削除） ===
    "RENAME": {
        "EP-000004153": "川島明",  # 麒麟・川島
        "EP-000004154": "桂三度",  # 世界のナベアツ
        "EP-000007948": "桂三度",  # 世界のナベアツ
        "EP-000004158": "大島美幸",  # 森三中・大島
        "EP-000007934": "田中直樹",  # ココリコ・田中直樹
        "EP-000007935": "遠藤章造",  # ココリコ・遠藤章造
        "EP-000004169": "博多華丸",  # 博多華丸・大吉
        "EP-000000409": "盛山晋太郎",  # 見取り図
        "EP-000004151": "中川礼二",  # 中川家
        "EP-000007755": "中田カウス",  # 中田カウス・ボタン
    },
}


def main():
    csv_path = "preserved/data/MASTER_EPISODES_CURRENT.csv"
    df = pd.read_csv(csv_path, low_memory=False)
    print(f"読み込み: {len(df)}件")

    stats = {"deleted": 0, "merged": 0, "renamed": 0}

    # 1. 削除
    for ep_id in CONVERSIONS["DELETE"]:
        before = len(df)
        df = df[df["episode_id"] != ep_id]
        if len(df) < before:
            stats["deleted"] += 1
            print(f"  削除: {ep_id}")

    # 2. PERSON ID統合
    for ep_id, config in CONVERSIONS["MERGE"].items():
        mask = df["episode_id"] == ep_id
        if mask.any():
            old_name = df.loc[mask, "person_name"].values[0]
            df.loc[mask, "person_id"] = config["new_person_id"]
            df.loc[mask, "person_name"] = config["new_person_name"]
            stats["merged"] += 1
            print(f"  統合: {ep_id} ({old_name} → {config['new_person_name']})")

    # 3. 名前変更
    for ep_id, new_name in CONVERSIONS["RENAME"].items():
        mask = df["episode_id"] == ep_id
        if mask.any():
            old_name = df.loc[mask, "person_name"].values[0]
            df.loc[mask, "person_name"] = new_name
            stats["renamed"] += 1
            print(f"  改名: {ep_id} ({old_name} → {new_name})")

    # 4. 保存
    df.to_csv(csv_path, index=False)
    print(f"\n完了: 削除{stats['deleted']}件, 統合{stats['merged']}件, 改名{stats['renamed']}件")
    print(f"保存: {len(df)}件")


if __name__ == "__main__":
    main()
