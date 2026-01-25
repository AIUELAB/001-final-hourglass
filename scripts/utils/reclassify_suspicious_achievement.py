#!/usr/bin/env python3
"""
疑わしいACHIEVEMENTエピソードを再分類するスクリプト

達成キーワードがなく困難キーワードがあるエピソードを
改善版プロンプトで再分類する。
"""

import os
import sys
import json
import pandas as pd
from datetime import datetime
from anthropic import Anthropic

# 有効なepisode_type値
VALID_TYPES = ["ACHIEVEMENT", "TURNING_POINT", "CHALLENGE", "INNOVATION", "FOUNDING", "FAILURE", "COMEBACK", "FAMILY"]

# 検出キーワード
ACHIEVEMENT_KEYWORDS = ["達成", "成功", "獲得", "受賞", "優勝", "完成", "実現", "勝利", "突破", "制覇"]
STRUGGLE_KEYWORDS = ["困難", "迷い", "不安", "葛藤", "挫折", "苦悩", "模索", "試行錯誤"]


def detect_suspicious_achievements(df):
    """疑わしいACHIEVEMENTを検出"""
    achievement_eps = df[df["episode_type"] == "ACHIEVEMENT"]
    suspicious_ids = []

    for idx, row in achievement_eps.iterrows():
        text = str(row.get("episode_text", ""))
        has_achievement = any(kw in text for kw in ACHIEVEMENT_KEYWORDS)
        has_struggle = any(kw in text for kw in STRUGGLE_KEYWORDS)

        if not has_achievement and has_struggle:
            suspicious_ids.append(row["episode_id"])

    return suspicious_ids


def reclassify_episodes(client, episodes_batch):
    """LLMでepisode_typeを再分類（厳格版）"""

    episodes_text = "\n---\n".join(
        [f"ID:{ep['episode_id']}\n{ep['person_name']}\n{ep['episode_text']}" for ep in episodes_batch]
    )

    prompt = f"""以下のエピソードを分析し、それぞれに最も適切なepisode_typeを割り当ててください。

【重要】これらは現在「ACHIEVEMENT」とラベルされていますが、再評価が必要です。
デフォルトはCHALLENGEです。ACHIEVEMENTは厳格に判定してください。

■ ACHIEVEMENT（達成）の厳格な条件 - 以下すべてを満たす場合のみ:
  1. 明確な達成の瞬間が描かれている
  2. 「達成した」「成功した」「獲得した」「受賞した」「優勝した」等の表現がある
  3. 結果が確定している（将来への伏線や「後の土台になった」はNG）

■ その他のタイプ:
- CHALLENGE: 困難への挑戦、試練、迷いながらも努力を続ける（デフォルト）
- TURNING_POINT: 人生の岐路、重要な決断、方向転換
- FAILURE: 失敗、挫折、敗北からの学び
- COMEBACK: 復活、再起、逆境からの復帰

■ 重要な判定基準:
- 「後の成功の土台となった」→ CHALLENGE（達成ではない）
- 「迷いながらも続けた」→ CHALLENGE
- 「不安と葛藤の中で」→ CHALLENGE
- 「重要な決断をした」→ TURNING_POINT
- 判断に迷う場合 → CHALLENGE

エピソード:
{episodes_text}

JSON形式で回答してください:
{{"results": [{{"episode_id": "EP-XXXXXX", "episode_type": "TYPE"}}]}}"""

    response = client.messages.create(
        model="claude-sonnet-4-20250514", max_tokens=4000, messages=[{"role": "user", "content": prompt}]
    )

    text = response.content[0].text

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
    parser.add_argument("--batch-size", type=int, default=20)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--episode", type=str, help="特定のエピソードIDのみ処理")
    args = parser.parse_args()

    csv_path = "preserved/MASTER_EPISODES_CURRENT.csv"
    df = pd.read_csv(csv_path)

    # 特定エピソード指定の場合
    if args.episode:
        suspicious_ids = [args.episode]
        print(f"📋 指定エピソード: {args.episode}")
    else:
        # 疑わしいACHIEVEMENTを検出
        suspicious_ids = detect_suspicious_achievements(df)
        print(f"📊 疑わしいACHIEVEMENT検出: {len(suspicious_ids)}件")

    if len(suspicious_ids) == 0:
        print("✅ 疑わしいエピソードはありません")
        return

    if not args.execute:
        print("\n検出例（最初の10件）:")
        for ep_id in suspicious_ids[:10]:
            row = df[df["episode_id"] == ep_id].iloc[0]
            print(f"  {ep_id}: {row['person_name']}")
        print("\n--execute フラグを付けて実行してください")
        return

    # Anthropic client
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEY が設定されていません")
        sys.exit(1)

    client = Anthropic(api_key=api_key)

    # 対象エピソードを抽出
    target_df = df[df["episode_id"].isin(suspicious_ids)]
    episodes_list = target_df.to_dict("records")

    total = len(episodes_list)
    updated = 0
    changes = []

    for i in range(0, total, args.batch_size):
        batch = episodes_list[i : i + args.batch_size]
        print(f"\n🔄 バッチ {i // args.batch_size + 1}: {len(batch)}件処理中...")

        try:
            results = reclassify_episodes(client, batch)

            for r in results:
                ep_id = r.get("episode_id")
                new_type = r.get("episode_type")

                if new_type and new_type in VALID_TYPES:
                    old_type = df.loc[df["episode_id"] == ep_id, "episode_type"].values[0]
                    if old_type != new_type:
                        df.loc[df["episode_id"] == ep_id, "episode_type"] = new_type
                        changes.append({"episode_id": ep_id, "old_type": old_type, "new_type": new_type})
                        updated += 1

            print(f"   ✅ {len(results)}件処理完了")

        except Exception as e:
            print(f"   ❌ エラー: {e}")
            continue

    # 保存
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")

    # レポート
    print(f"\n{'=' * 60}")
    print(f"✅ 完了: {updated}件のepisode_typeを変更")
    print(f"{'=' * 60}")

    if changes:
        print("\n変更内容:")
        type_summary = {}
        for c in changes:
            key = f"{c['old_type']} → {c['new_type']}"
            type_summary[key] = type_summary.get(key, 0) + 1

        for change_type, count in sorted(type_summary.items(), key=lambda x: -x[1]):
            print(f"  {change_type}: {count}件")

    # レポート保存
    report = {
        "timestamp": datetime.now().isoformat(),
        "total_suspicious": len(suspicious_ids),
        "total_changed": updated,
        "changes": changes,
    }

    report_path = f"reports/episode_type_reclassify_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"\n📄 レポート: {report_path}")


if __name__ == "__main__":
    main()
