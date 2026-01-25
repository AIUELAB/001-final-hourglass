#!/usr/bin/env python3
"""
禁止パターンエピソード修正スクリプト
- META/FUTURE/SPECULATION を LLM で再生成
- バッチ処理 + before/after ログ
"""

import pandas as pd
import json
import os
import re
import time
from datetime import datetime
from pathlib import Path
from anthropic import Anthropic

# 設定
DATA_FILE = Path(__file__).parent.parent / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = Path(__file__).parent.parent / "reports"
BACKUP_DIR = Path(__file__).parent.parent / "backups"


def get_anthropic_client():
    """Anthropicクライアント取得"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY環境変数が設定されていません")
    return Anthropic(api_key=api_key)


def detect_violation_type(episode_text: str) -> list:
    """違反タイプを検出"""
    violations = []

    # 未来予測パターン
    future_patterns = [
        r"今後.*?だろう",
        r"する予定",
        r"予定(です|だ|である)",
        r"まだ到来していない",
        r"まだ到達していない",
        r"この年齢はまだ",
        r"迎えることになります",
        r"(今後|将来).*?(予想|予測|見込)",
    ]
    for p in future_patterns:
        if re.search(p, episode_text):
            violations.append("FUTURE")
            break

    # 推測パターン
    speculation_patterns = [
        r"かもしれない",
        r"かもしれません",
        r"と見られている",
        r"と推測される",
        r"と思われる",
        r"と考えられる",
        r"おそらく",
        r"可能性がある",
    ]
    for p in speculation_patterns:
        if re.search(p, episode_text):
            violations.append("SPECULATION")
            break

    # メタ説明パターン（厳選）
    meta_patterns = [
        r"として知られる",
        r"として知られて",
        r"で知られる",
        r"として有名",
        r"として名を馳せ",
        r"広く認知され",
        r"申し訳ございません",
        r"エピソードはありません",
        r"架空の(キャラクター|人物)",
        r"実在しない",
    ]
    for p in meta_patterns:
        if re.search(p, episode_text):
            violations.append("META")
            break

    return list(set(violations))


def regenerate_episode(client: Anthropic, row: dict, violations: list) -> str:
    """LLMでエピソード再生成"""

    person_name = row.get("person_name", "")
    age = row.get("age", "")
    person_type = row.get("person_type", "REAL")
    category = row.get("category", "")
    original_text = row.get("episode_text", "")

    # person_type に応じたプロンプト
    if person_type == "FICTIONAL":
        context = f"""
【対象】{person_name}（{age}歳時点）
【タイプ】架空キャラクター
【カテゴリ】{category}

【元エピソード】
{original_text}

【検出された違反】{", ".join(violations)}

【修正指示】
このエピソードは架空キャラクターに関するものです。
以下の禁止パターンを含まないよう、「作品世界内の視点」で再生成してください：
- 「架空のキャラクターである」等のメタ説明
- 「実在しない」「エピソードは存在しません」
- 「申し訳ございません」等のお断り文
- 未来予測や推測表現

作品内で実際に描かれた、または設定から自然に導かれる出来事を記述してください。
「あなたと同じ{age}歳のとき、」で開始してください。
"""
    else:
        context = f"""
【対象】{person_name}（{age}歳時点）
【タイプ】実在人物
【カテゴリ】{category}

【元エピソード】
{original_text}

【検出された違反】{", ".join(violations)}

【修正指示】
以下の禁止パターンを含まないよう、「事実ベース」で再生成してください：
- 「〜として知られる」「〜で有名」等のメタ説明
- 「今後〜だろう」「予定」等の未来予測
- 「かもしれない」「と見られている」等の推測
- 日付の過剰な使用（年月日は避ける）

実際に起きた出来事・活動のみを記述してください。
具体的な事実（受賞、記録、発表、イベント等）を中心に構成してください。
「あなたと同じ{age}歳のとき、」で開始してください。
"""

    prompt = f"""あなたは「あの有名人と自分を対比する」エピソードライターです。

{context}

【出力形式】
- 「あなたと同じ{age}歳のとき、」で開始
- 200〜400文字
- 具体的な出来事・事実を中心に
- 禁止パターンを絶対に含めないこと

修正したエピソード本文のみを出力してください（説明や注釈は不要）。
"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=800, messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  ⚠️ LLM生成エラー: {e}")
        return None


def run_fix(batch_size: int = 30, target_categories: list = None, dry_run: bool = True):
    """修正を実行"""

    print("=" * 70)
    print("🔧 禁止パターンエピソード修正")
    print("=" * 70)

    if target_categories is None:
        target_categories = ["FUTURE", "SPECULATION", "META"]

    print(f"\n対象カテゴリ: {target_categories}")
    print(f"バッチサイズ: {batch_size}")
    print(f"モード: {'Dry-run（プレビュー）' if dry_run else '実行'}")

    # データ読み込み
    print(f"\n📂 データ読み込み: {DATA_FILE}")
    df = pd.read_csv(DATA_FILE, encoding="utf-8-sig")
    print(f"   総エピソード数: {len(df):,}件")

    # 違反エピソード抽出
    print("\n🔍 違反エピソード検出中...")

    target_rows = []
    for idx, row in df.iterrows():
        episode_text = row.get("episode_text", "")
        if pd.isna(episode_text) or not episode_text:
            continue

        violations = detect_violation_type(str(episode_text))
        if any(v in target_categories for v in violations):
            target_rows.append(
                {
                    "idx": idx,
                    "episode_id": row.get("episode_id", ""),
                    "person_name": row.get("person_name", ""),
                    "age": row.get("age", ""),
                    "person_type": row.get("person_type", "REAL"),
                    "category": row.get("category", ""),
                    "episode_text": episode_text,
                    "violations": violations,
                }
            )

    print(f"   検出件数: {len(target_rows):,}件")

    if not target_rows:
        print("✅ 修正対象なし")
        return

    # バッチ処理
    targets = target_rows[:batch_size]
    print(f"\n📝 処理対象: {len(targets)}件（バッチサイズ上限）")

    if dry_run:
        print("\n【Dry-run プレビュー】")
        for i, t in enumerate(targets[:5], 1):
            print(f"\n{i}. {t['episode_id']} - {t['person_name']}（{t['age']}歳）")
            print(f"   違反: {', '.join(t['violations'])}")
            print(f"   本文: {t['episode_text'][:100]}...")

        print(f"\n... 他 {len(targets) - 5}件")
        print("\n--execute オプションで実際に修正を実行します")
        return

    # 実行モード
    client = get_anthropic_client()

    # バックアップ作成
    BACKUP_DIR.mkdir(exist_ok=True)
    backup_path = BACKUP_DIR / f"MASTER_EPISODES_BEFORE_FIX_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(backup_path, index=False, encoding="utf-8-sig")
    print(f"\n💾 バックアップ保存: {backup_path}")

    # 修正ログ
    changes = []

    print("\n🔄 修正処理中...")

    for i, target in enumerate(targets, 1):
        idx = target["idx"]
        episode_id = target["episode_id"]
        person_name = target["person_name"]

        print(f"\n[{i}/{len(targets)}] {episode_id} - {person_name}")
        print(f"  違反: {', '.join(target['violations'])}")

        # 再生成
        new_text = regenerate_episode(client, target, target["violations"])

        if new_text:
            # 再チェック
            new_violations = detect_violation_type(new_text)
            if new_violations:
                print(f"  ⚠️ 再生成後も違反あり: {new_violations}")
                # 2回目のトライ
                new_text = regenerate_episode(client, target, target["violations"])
                new_violations = detect_violation_type(new_text) if new_text else []

            if new_text and not new_violations:
                # 更新
                old_text = df.loc[idx, "episode_text"]
                df.loc[idx, "episode_text"] = new_text
                df.loc[idx, "source"] = (
                    str(df.loc[idx, "source"]) + "→PROHIBITED_FIX"
                    if pd.notna(df.loc[idx, "source"])
                    else "PROHIBITED_FIX"
                )

                changes.append(
                    {
                        "episode_id": episode_id,
                        "person_name": person_name,
                        "age": target["age"],
                        "violations_fixed": target["violations"],
                        "old_text": old_text[:200] + "..." if len(old_text) > 200 else old_text,
                        "new_text": new_text[:200] + "..." if len(new_text) > 200 else new_text,
                    }
                )

                print("  ✅ 修正完了")
            else:
                print("  ❌ 修正失敗（違反解消されず）")
        else:
            print("  ❌ 生成失敗")

        # レート制限対策
        time.sleep(0.5)

    # 保存
    if changes:
        df.to_csv(DATA_FILE, index=False, encoding="utf-8-sig")
        print(f"\n💾 データ保存完了: {DATA_FILE}")

        # レポート保存
        REPORT_DIR.mkdir(exist_ok=True)
        report = {
            "timestamp": datetime.now().isoformat(),
            "target_categories": target_categories,
            "batch_size": batch_size,
            "total_targets": len(target_rows),
            "processed": len(targets),
            "fixed": len(changes),
            "changes": changes,
        }

        report_path = REPORT_DIR / f"prohibited_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"📄 レポート保存: {report_path}")

    print(f"\n✅ 完了: {len(changes)}件修正")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="禁止パターンエピソード修正")
    parser.add_argument("--batch-size", type=int, default=30, help="バッチサイズ")
    parser.add_argument(
        "--categories",
        nargs="+",
        default=["FUTURE", "SPECULATION", "META"],
        help="対象カテゴリ（FUTURE, SPECULATION, META）",
    )
    parser.add_argument("--execute", action="store_true", help="実行モード")
    parser.add_argument("--future-only", action="store_true", help="FUTUREのみ対象")

    args = parser.parse_args()

    if args.future_only:
        args.categories = ["FUTURE"]

    run_fix(batch_size=args.batch_size, target_categories=args.categories, dry_run=not args.execute)
