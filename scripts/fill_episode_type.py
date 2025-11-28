#!/usr/bin/env python3
"""
episode_typeが空のエピソードをLLMで埋めるスクリプト
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime
from anthropic import Anthropic

# 有効なepisode_type値
VALID_TYPES = [
    "ACHIEVEMENT",  # 達成・成功
    "TURNING_POINT",  # 転機・転換点
    "CHALLENGE",  # 挑戦・困難
    "INNOVATION",  # 革新・発明
    "FOUNDING",  # 創業・設立
    "FAILURE",  # 失敗・挫折
    "COMEBACK",  # 復活・再起
    "FAMILY",  # 家族・人間関係
]


def classify_episode_type(client, episodes_batch):
    """LLMでepisode_typeを分類（改善版v2）"""

    episodes_text = "\n".join(
        [f"ID:{ep['episode_id']} | {ep['person_name']} | {ep['episode_text']}" for ep in episodes_batch]
    )

    prompt = f"""以下のエピソードを分析し、それぞれに最も適切なepisode_typeを割り当ててください。

【重要】デフォルトはCHALLENGEです。ACHIEVEMENTは厳格に判定してください。

■ ACHIEVEMENT（達成）の厳格な条件 - 以下すべてを満たす場合のみ:
  1. 明確な達成の瞬間が描かれている
  2. 「達成した」「成功した」「獲得した」「受賞した」「優勝した」等の表現がある
  3. 結果が確定している（将来への伏線や「後の土台になった」はNG）

■ その他のタイプ:
- CHALLENGE: 困難への挑戦、試練、迷いながらも努力を続ける（デフォルト）
- TURNING_POINT: 人生の岐路、重要な決断、方向転換
- INNOVATION: 革新、発明、新しいアイデアの創出
- FOUNDING: 創業、設立、組織の立ち上げ
- FAILURE: 失敗、挫折、敗北からの学び
- COMEBACK: 復活、再起、逆境からの復帰
- FAMILY: 家族関係、人間関係、絆

■ 判定の注意点:
- 「後の成功の土台となった」→ CHALLENGE（達成ではない）
- 「迷いながらも続けた」→ CHALLENGE
- 「不安と葛藤」→ CHALLENGE
- 判断に迷う場合 → CHALLENGE（ACHIEVEMENTではない）

エピソード:
{episodes_text}

JSON形式で回答してください:
{{"results": [{{"episode_id": "EP-XXXXXX", "episode_type": "TYPE"}}]}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=2000, messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text

    # JSON抽出
    import re

    json_match = re.search(r"\{[\s\S]*\}", text)
    if json_match:
        try:
            result = json.loads(json_match.group())
            return result.get("results", [])
        except json.JSONDecodeError:
            pass

    return []


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=30)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    # データ読み込み
    csv_path = "preserved/MASTER_EPISODES_CURRENT.csv"
    df = pd.read_csv(csv_path)

    # episode_typeが空のエピソードを抽出
    empty_mask = df["episode_type"].isna() | (df["episode_type"] == "")
    empty_episodes = df[empty_mask].copy()

    print(f"📊 episode_type空: {len(empty_episodes)}件")

    if len(empty_episodes) == 0:
        print("✅ すべてのepisode_typeが埋まっています")
        return

    if not args.execute:
        print("\n--execute フラグを付けて実行してください")
        return

    # Anthropic client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY が設定されていません")
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    # バッチ処理
    episodes_list = empty_episodes.to_dict("records")
    total = len(episodes_list)
    updated = 0

    for i in range(0, total, args.batch_size):
        batch = episodes_list[i : i + args.batch_size]
        print(f"\n🔄 バッチ {i//args.batch_size + 1}: {len(batch)}件処理中...")

        try:
            results = classify_episode_type(client, batch)

            for r in results:
                ep_id = r.get("episode_id")
                ep_type = r.get("episode_type")

                if ep_type and ep_type in VALID_TYPES:
                    df.loc[df["episode_id"] == ep_id, "episode_type"] = ep_type
                    updated += 1
                elif ep_type:
                    # 無効なタイプの場合はACHIEVEMENTにフォールバック
                    df.loc[df["episode_id"] == ep_id, "episode_type"] = "ACHIEVEMENT"
                    updated += 1

            print(f"   ✅ {len(results)}件分類完了")

        except Exception as e:
            print(f"   ❌ エラー: {e}")
            continue

    # 保存
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n✅ 完了: {updated}件のepisode_typeを更新")

    # 残りを確認
    remaining = df[df["episode_type"].isna() | (df["episode_type"] == "")]
    if len(remaining) > 0:
        print(f"⚠️ 残り: {len(remaining)}件")


if __name__ == "__main__":
    main()
