#!/usr/bin/env python3
"""
エピソードフォーマット修正スクリプト

標準フォーマット「あなたと同じ◯◯歳のとき、◯◯は〜」で始まっていない
架空キャラエピソードをLLMで再生成して修正する。
"""

import os
import re
import sys
from pathlib import Path
from typing import Optional, Tuple

import pandas as pd

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from episode_quality_system.template_blocker import TemplateBlocker

# Anthropic APIを使用
try:
    import anthropic

    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

# 定数
CSV_PATH = project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
STANDARD_PREFIX_PATTERN = r"^あなたと同じ\d+歳のとき、.+は"

# 作品名マッピング
WORK_TITLE_MAP = {
    "毛利蘭": "名探偵コナン",
    "毛利小五郎": "名探偵コナン",
    "江戸川コナン": "名探偵コナン",
    "工藤新一": "名探偵コナン",
    "輝夜月": "バーチャルYouTuber",
    "鉄腕アトム": "鉄腕アトム",
    "碇シンジ": "新世紀エヴァンゲリオン",
    "胡蝶しのぶ": "鬼滅の刃",
    "竈門禰豆子": "鬼滅の刃",
    "竈門炭治郎": "鬼滅の刃",
    "マリオ": "スーパーマリオブラザーズ",
    "ミライアカリ": "バーチャルYouTuber",
    "ホロライブ": "バーチャルYouTuber",
    "モンキー・D・ルフィ": "ONE PIECE",
    "ルパン三世": "ルパン三世",
    "ニコ・ロビン": "ONE PIECE",
    "ナミ": "ONE PIECE",
    "ドラえもん": "ドラえもん",
    "トニートニー・チョッパー": "ONE PIECE",
    "フグ田サザエ": "サザエさん",
    "ピカチュウ": "ポケットモンスター",
    "ロロノア・ゾロ": "ONE PIECE",
    "はたけカカシ": "NARUTO",
    "にじさんじ": "バーチャルYouTuber",
    "うずまきナルト": "NARUTO",
    "サンジ": "ONE PIECE",
    "セーラームーン（月野うさぎ）": "美少女戦士セーラームーン",
    "サトシ": "ポケットモンスター",
    "ウルトラマン": "ウルトラマン",
    "アンパンマン": "それいけ！アンパンマン",
    "キズナアイ": "バーチャルYouTuber",
    "サザエさん": "サザエさん",
    "クレヨンしんちゃん（野原しんのすけ）": "クレヨンしんちゃん",
    "ガンダム（RX-78-2）": "機動戦士ガンダム",
    "孫悟飯": "ドラゴンボール",
    "孫悟空": "ドラゴンボール",
    "初音ミク": "VOCALOID",
}

# フォーマット修正用プロンプト
FORMAT_FIX_PROMPT = """あなたは{work_title}のエピソード編集者です。

以下のエピソードを「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で始まるように書き直してください。
内容は可能な限り維持し、冒頭のフォーマットのみ修正してください。

【元のエピソード】
{original_text}

【出力形式】
「あなたと同じ{age}歳のとき、{person_name}は〜」で始まる200-300文字のエピソード

【注意】
- 元のエピソードの重要な内容は維持すること
- メタ的説明（「架空のキャラクター」等）は絶対に含めないこと
- 作品世界内の視点で記述すること
"""


def get_work_title(person_name: str, work_title: str = None) -> str:
    """作品名を取得"""
    if work_title and str(work_title) != "nan" and work_title:
        return work_title
    return WORK_TITLE_MAP.get(person_name, "作品")


def regenerate_with_format(
    person_name: str, age: int, original_text: str, work_title: str, max_retries: int = 3
) -> Tuple[Optional[str], bool]:
    """
    標準フォーマットでエピソードを再生成

    Args:
        person_name: キャラクター名
        age: 年齢
        original_text: 元のエピソードテキスト
        work_title: 作品名
        max_retries: 最大リトライ回数

    Returns:
        (生成されたエピソード, 成功フラグ)
    """
    if not HAS_ANTHROPIC:
        print("❌ anthropicライブラリがインストールされていません")
        return None, False

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ ANTHROPIC_API_KEYが設定されていません")
        return None, False

    client = anthropic.Anthropic(api_key=api_key)
    blocker = TemplateBlocker()

    work = get_work_title(person_name, work_title)
    prompt = FORMAT_FIX_PROMPT.format(
        person_name=person_name, age=int(age), work_title=work, original_text=original_text
    )

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]
            )

            episode_text = response.content[0].text.strip()

            # フォーマットチェック
            if re.match(STANDARD_PREFIX_PATTERN, episode_text):
                # メタ的説明チェック
                has_meta, _ = blocker.check_meta_disclaimer(episode_text)
                if not has_meta:
                    return episode_text, True

            print(f"  ⚠️ リトライ {attempt + 1}/{max_retries}: フォーマット不正またはメタ説明検出")

        except Exception as e:
            print(f"  ❌ エラー: {e}")
            return None, False

    return None, False


def fix_fictional_episodes(queue_path: Path, dry_run: bool = True) -> dict:
    """
    再生成キューのエピソードを修正

    Args:
        queue_path: 再生成キューCSVのパス
        dry_run: Trueの場合は実際に更新しない

    Returns:
        修正結果
    """
    # キューを読み込み
    queue_df = pd.read_csv(queue_path, encoding="utf-8-sig")
    print(f"📂 再生成キュー読み込み: {len(queue_df)}件")

    # メインCSVを読み込み
    main_df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    print(f"📂 メインCSV読み込み: {len(main_df)}件")

    results = {"success": [], "failed": [], "skipped": [], "total": len(queue_df)}

    for _, row in queue_df.iterrows():
        person_name = row["person_name"]
        age = row["age"]
        episode_id = row["episode_id"]

        # メインCSVから元のエピソードを取得
        match = main_df[main_df["episode_id"] == episode_id]
        if match.empty:
            print(f"⏭️ スキップ: {person_name} ({age}歳) - エピソードが見つかりません")
            results["skipped"].append({"person_name": person_name, "age": age, "reason": "not_found"})
            continue

        original_text = match.iloc[0]["episode_text"]
        work_title = match.iloc[0].get("work_title", "")
        idx = match.index[0]

        # すでに標準フォーマットか確認
        if re.match(STANDARD_PREFIX_PATTERN, str(original_text)):
            print(f"⏭️ スキップ: {person_name} ({age}歳) - すでに標準フォーマット")
            results["skipped"].append({"person_name": person_name, "age": age, "reason": "already_standard"})
            continue

        print(f"\n🔄 再生成中: {person_name} ({age}歳)")

        new_episode, success = regenerate_with_format(
            person_name=person_name,
            age=age,
            original_text=original_text,
            work_title=work_title,
            max_retries=3,
        )

        if success:
            print("  ✅ 成功")
            print(f"  新エピソード: {new_episode[:80]}...")

            if not dry_run:
                main_df.loc[idx, "episode_text"] = new_episode
                main_df.loc[idx, "fact_check_result"] = "FORMAT_FIXED"

            results["success"].append(
                {
                    "person_name": person_name,
                    "age": age,
                    "old_episode": original_text[:80],
                    "new_episode": new_episode[:80],
                }
            )
        else:
            print("  ❌ 失敗")
            results["failed"].append({"person_name": person_name, "age": age})

    if not dry_run and results["success"]:
        # 保存
        main_df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        print(f"\n💾 CSV更新完了: {len(main_df)}件")

    return results


def detect_non_standard_episodes() -> list:
    """非標準フォーマットの架空キャラエピソードを検出"""
    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    issues = []

    for idx, row in df.iterrows():
        person_type = str(row.get("person_type", "")).upper()
        episode_text = str(row.get("episode_text", ""))

        if person_type == "FICTIONAL":
            if not re.match(STANDARD_PREFIX_PATTERN, episode_text):
                issues.append(
                    {
                        "index": idx,
                        "episode_id": row.get("episode_id", ""),
                        "person_name": row.get("person_name", ""),
                        "age": row.get("age", ""),
                        "episode_preview": episode_text[:100],
                    }
                )

    return issues


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="エピソードフォーマット修正")
    parser.add_argument("--fix", action="store_true", help="実際に修正を実行")
    parser.add_argument("--detect", action="store_true", help="非標準フォーマットを検出")
    parser.add_argument("--queue", type=str, help="再生成キューCSVのパス")
    args = parser.parse_args()

    if args.detect:
        print("🔍 非標準フォーマット検出中...")
        issues = detect_non_standard_episodes()
        print(f"\n検出結果: {len(issues)}件")
        for item in issues[:10]:
            print(f"  - {item['person_name']} ({item['age']}歳): {item['episode_preview'][:50]}...")
        if len(issues) > 10:
            print(f"  ... 他 {len(issues) - 10}件")
        return

    if not args.queue:
        # 最新の再生成キューを探す
        reports_dir = project_root / "reports"
        queues = sorted(reports_dir.glob("regeneration_queue_*.csv"), reverse=True)
        if queues:
            queue_path = queues[0]
            print(f"📄 最新の再生成キュー: {queue_path}")
        else:
            print("❌ 再生成キューが見つかりません")
            return
    else:
        queue_path = Path(args.queue)

    if args.fix:
        print("⚠️ --fix オプション: 実際に修正を実行します")
        results = fix_fictional_episodes(queue_path, dry_run=False)
    else:
        print("ℹ️ ドライラン: 実際の修正は行いません（--fix で実行）")
        results = fix_fictional_episodes(queue_path, dry_run=True)

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 修正結果")
    print("=" * 60)
    print(f"成功: {len(results['success'])}件")
    print(f"失敗: {len(results['failed'])}件")
    print(f"スキップ: {len(results['skipped'])}件")

    if results["failed"]:
        print("\n❌ 失敗したエピソード:")
        for f in results["failed"]:
            print(f"  - {f['person_name']} ({f['age']}歳)")

    if not args.fix and results["success"]:
        print("\n💡 実際に修正を適用するには --fix オプションを付けて実行してください")


if __name__ == "__main__":
    main()
