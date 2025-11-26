#!/usr/bin/env python3
"""
EPUP: 架空キャラクターエピソードのメタ的説明修正スクリプト

メタ的説明（「このキャラクターは架空であり...」等）を含む
架空キャラクターエピソードを検出し、LLMで再生成して修正する。
"""

import os
import sys
import re
import json
import pandas as pd
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from pathlib import Path

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


# メタ的説明検出パターン（template_blockerと同期）
META_DISCLAIMER_PATTERNS = [
    r"は架空の(キャラクター|人物|存在)であり",
    r"実在(しない|の人物ではない)",
    r"エピソード(は|が)存在しません",
    r"公式(な|の)?描写は.*存在しない",
    r"実際の.*エピソード.*存在しません",
    r"申し訳ございませんが",
    r"生成することは(できません|適切ではありません)",
    r"別の.*人物.*でしたら",
    r"年齢を重ね(たり|ること).*ない",
    r"設定上は",
    r"フィクション(である|として)",
    r"架空.*ため",
]


def detect_meta_episodes(csv_path: str) -> List[Dict]:
    """
    メタ的説明を含むエピソードを検出

    Args:
        csv_path: CSVファイルパス

    Returns:
        問題エピソードのリスト
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    affected = []

    for idx, row in df.iterrows():
        person_type = str(row.get("person_type", "")).upper()
        episode_text = str(row.get("episode_text", ""))

        # FICTIONALのエピソードのみチェック
        if "FICTIONAL" not in person_type:
            continue

        # メタ的説明パターンをチェック
        detected_patterns = []
        for pattern in META_DISCLAIMER_PATTERNS:
            if re.search(pattern, episode_text):
                detected_patterns.append(pattern)

        if detected_patterns:
            affected.append(
                {
                    "index": idx,
                    "episode_id": row.get("episode_id", ""),
                    "person_id": row.get("person_id", ""),
                    "person_name": row.get("person_name", ""),
                    "age": row.get("age", ""),
                    "work_title": row.get("work_title", ""),
                    "episode_text": episode_text,
                    "detected_patterns": detected_patterns,
                }
            )

    return affected


# 架空キャラクター専用プロンプトテンプレート
FICTIONAL_CHARACTER_PROMPT = """あなたは{work_title}の世界観を深く理解するストーリーテラーです。

{person_name}（{work_title}のキャラクター）が{age}歳の時点での作品内エピソードを生成してください。

【重要な制約】
- このキャラクターは作品内の存在として扱い、メタ的言及は禁止
- 作品の設定・世界観に沿った内容にすること
- 冒頭は必ず「あなたと同じ{age}歳のとき、{person_name}『{work_title}』は」で開始
- 200-250文字

【禁止フレーズ】※絶対に使用しないこと
- 「架空のキャラクター」
- 「エピソードは存在しません」
- 「実在しない」
- 「公式な描写は存在しません」
- 「申し訳ございませんが」
- 「フィクションの」
- 「設定上は」

【生成方針】
- 原作で{age}歳時点の描写があればそれを活用
- なければ、キャラクター設定から自然に導かれるエピソードを創作
- キャラクターの性格・口癖・行動パターンを維持
- 作品内の地名、イベント、関係キャラクターを活用

【出力形式】
「あなたと同じ{age}歳のとき、{person_name}『{work_title}』は〜」という形式で、作品世界内の視点で記述してください。
（例: あなたと同じ17歳のとき、毛利蘭『名探偵コナン』は空手大会で優勝した。）
"""

# 作品名マッピング（work_titleが空の場合のフォールバック）
WORK_TITLE_MAP = {
    "ピカチュウ": "ポケットモンスター",
    "サトシ": "ポケットモンスター",
    "フグ田サザエ": "サザエさん",
    "磯野カツオ": "サザエさん",
    "磯野ワカメ": "サザエさん",
    "ティファ・ロックハート": "ファイナルファンタジーVII",
    "クラウド・ストライフ": "ファイナルファンタジーVII",
    "野比のび太": "ドラえもん",
    "ドラえもん": "ドラえもん",
    "竈門炭治郎": "鬼滅の刃",
    "竈門禰豆子": "鬼滅の刃",
    "孫悟空": "ドラゴンボール",
    "モンキー・D・ルフィ": "ONE PIECE",
}


def get_work_title(person_name: str, work_title: str) -> str:
    """作品名を取得（空の場合はマッピングから）"""
    if work_title and str(work_title) != "nan":
        return work_title
    return WORK_TITLE_MAP.get(person_name, "作品")


def regenerate_episode_with_llm(
    person_name: str, age: int, work_title: str, max_retries: int = 3
) -> Tuple[Optional[str], bool]:
    """
    架空キャラクター専用プロンプトでエピソードを再生成

    Args:
        person_name: キャラクター名
        age: 年齢
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
    prompt = FICTIONAL_CHARACTER_PROMPT.format(person_name=person_name, age=int(age), work_title=work)

    for attempt in range(max_retries):
        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]
            )

            episode_text = response.content[0].text.strip()

            # メタ的説明チェック
            has_meta, violations = blocker.check_meta_disclaimer(episode_text)

            if not has_meta:
                return episode_text, True

            print(f"  ⚠️ リトライ {attempt + 1}/{max_retries}: メタ的説明検出")

            # リトライ時はプロンプトを強化
            prompt += "\n\n【注意】前回の出力にメタ的説明が含まれていました。作品内の視点で、キャラクターが実在するかのように記述してください。"

        except Exception as e:
            print(f"  ❌ エラー: {e}")
            return None, False

    return None, False


def generate_report(affected: List[Dict]) -> str:
    """
    検出結果のレポートを生成

    Args:
        affected: 問題エピソードのリスト

    Returns:
        レポート文字列
    """
    lines = []
    lines.append("=" * 60)
    lines.append("EPUP: メタ的説明検出レポート")
    lines.append(f"検出日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 60)
    lines.append("")
    lines.append(f"検出件数: {len(affected)}件")
    lines.append("")

    for i, ep in enumerate(affected, 1):
        lines.append(f"--- [{i}] {ep['person_name']} ({ep['age']}歳) ---")
        lines.append(f"episode_id: {ep['episode_id']}")
        lines.append(f"person_id: {ep['person_id']}")
        lines.append(f"work_title: {ep['work_title']}")
        lines.append(f"検出パターン: {len(ep['detected_patterns'])}件")
        for p in ep["detected_patterns"]:
            lines.append(f"  - {p}")
        lines.append("エピソード（先頭200文字）:")
        lines.append(f"  {ep['episode_text'][:200]}...")
        lines.append("")

    return "\n".join(lines)


def fix_episodes(csv_path: str, affected: List[Dict], dry_run: bool = True) -> Dict:
    """
    問題エピソードをLLMで再生成して修正

    Args:
        csv_path: CSVファイルパス
        affected: 問題エピソードのリスト
        dry_run: Trueの場合は実際に更新しない

    Returns:
        修正結果
    """
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    results = {"success": [], "failed": [], "total": len(affected)}

    for ep in affected:
        print(f"\n🔄 再生成中: {ep['person_name']} ({ep['age']}歳)")

        new_episode, success = regenerate_episode_with_llm(
            person_name=ep["person_name"], age=ep["age"], work_title=ep["work_title"], max_retries=3
        )

        if success:
            print("  ✅ 成功")
            print(f"  新エピソード: {new_episode[:100]}...")

            if not dry_run:
                # CSVを更新
                df.loc[ep["index"], "episode_text"] = new_episode
                df.loc[ep["index"], "fact_check_result"] = "EPUP_REGENERATED"

            results["success"].append(
                {
                    "person_name": ep["person_name"],
                    "age": ep["age"],
                    "old_episode": ep["episode_text"][:100],
                    "new_episode": new_episode,
                }
            )
        else:
            print("  ❌ 失敗")
            results["failed"].append(
                {
                    "person_name": ep["person_name"],
                    "age": ep["age"],
                }
            )

    if not dry_run and results["success"]:
        # バックアップ作成
        backup_path = csv_path.replace(
            ".csv", f'_backup_before_epup_fix_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        )
        df_original = pd.read_csv(csv_path, encoding="utf-8-sig")
        df_original.to_csv(backup_path, index=False, encoding="utf-8-sig")
        print(f"\n📦 バックアップ: {backup_path}")

        # 更新を保存
        df.to_csv(csv_path, index=False, encoding="utf-8-sig")
        print(f"💾 CSV更新完了: {csv_path}")

    return results


def main():
    """メイン処理"""
    import argparse

    parser = argparse.ArgumentParser(description="EPUP: メタ的説明修正スクリプト")
    parser.add_argument("--fix", action="store_true", help="実際に修正を実行")
    parser.add_argument("--detect-only", action="store_true", help="検出のみ実行")
    args = parser.parse_args()

    # CSVファイルパス
    csv_path = project_root / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return

    print("🔍 メタ的説明を含むエピソードを検出中...")
    affected = detect_meta_episodes(str(csv_path))

    if not affected:
        print("✅ メタ的説明を含むエピソードは見つかりませんでした")
        return

    # レポート表示
    report = generate_report(affected)
    print(report)

    # レポートをファイルに保存
    report_path = project_root / "reports" / f"meta_episode_detection_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    report_path.parent.mkdir(exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"📄 レポート保存: {report_path}")

    # サマリー
    print("")
    print("=" * 60)
    print("📊 サマリー")
    print("=" * 60)
    print(f"検出件数: {len(affected)}件")
    print("")
    print("検出されたキャラクター:")
    for ep in affected:
        work = get_work_title(ep["person_name"], ep["work_title"])
        print(f"  - {ep['person_name']} ({ep['age']}歳) - {work}")

    if args.detect_only:
        print("\n--detect-only オプション: 検出のみ実行しました")
        return

    # LLM再生成
    print("")
    print("=" * 60)
    print("🔧 LLM再生成")
    print("=" * 60)

    if args.fix:
        print("⚠️ --fix オプション: 実際に修正を実行します")
        results = fix_episodes(str(csv_path), affected, dry_run=False)
    else:
        print("ℹ️ ドライラン: 実際の修正は行いません（--fix で実行）")
        results = fix_episodes(str(csv_path), affected, dry_run=True)

    # 結果サマリー
    print("")
    print("=" * 60)
    print("📊 修正結果")
    print("=" * 60)
    print(f"成功: {len(results['success'])}件")
    print(f"失敗: {len(results['failed'])}件")

    if results["failed"]:
        print("\n❌ 失敗したエピソード:")
        for f in results["failed"]:
            print(f"  - {f['person_name']} ({f['age']}歳)")

    if not args.fix and results["success"]:
        print("\n💡 実際に修正を適用するには --fix オプションを付けて実行してください")
        print(f"   python {Path(__file__).name} --fix")


if __name__ == "__main__":
    main()
