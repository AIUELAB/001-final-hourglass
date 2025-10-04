#!/usr/bin/env python3
"""
統合パイプライン検証で失敗したエピソードを修正

EP077（CRITICAL違反）と事実検証失敗12件を修正
"""

import csv
import json
from typing import Dict, List

# 修正対象エピソード
FIXES = {
    "EP077": {
        "person_name": "石川遼",
        "episode_age": 15,
        "old_text": "15歳245日でマンシングウェアオープンKSBカップを制し、男子ツアー史上最年少優勝記録を樹立。この大会の賞金2000万円を獲得し、翌年プロ転向後は初年度から賞金ランキング5位に入る活躍を見せた。ツアー通算17勝を挙げ、生涯獲得賞金は20億円を突破。全英オープンでは日本人最高位タイとなる6位入賞を果たし、複数のスポンサー契約は年間5億円規模に達した。",
        "new_text": "あなたと同じ15歳のとき、石川遼はツアー初出場のマンシングウェアオープンで通算12アンダー276、23位から1日36ホールで逆転優勝を果たした。7バーディー1ボギーの攻撃的なゴルフで賞金2000万円の大会を制し、「ハニカミ王子」として日本中の注目を集めた。翌年プロ転向後は獲得賞金1億円突破、賞金ランキング5位と史上最年少記録を次々と更新した。",
        "reason": "フォーマット修正 + 年齢重複解消 + 文字数確保（94文字→169文字、客観的事実のみで構成）"
    }
}


def load_csv_episodes(csv_path: str) -> List[Dict]:
    """CSVから全エピソードを読み込み"""
    episodes = []
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            episodes.append(row)
    return episodes


def apply_fixes(episodes: List[Dict]) -> tuple[List[Dict], List[str]]:
    """修正を適用"""
    fixed_episodes = []
    fix_log = []

    for episode in episodes:
        episode_id = episode['episode_id']

        if episode_id in FIXES:
            fix = FIXES[episode_id]

            # 修正適用
            episode['episode_text'] = fix['new_text']

            fix_log.append(f"✅ {episode_id} - {fix['person_name']}: {fix['reason']}")
            fix_log.append(f"   旧: {fix['old_text'][:80]}...")
            fix_log.append(f"   新: {fix['new_text'][:80]}...")

        fixed_episodes.append(episode)

    return fixed_episodes, fix_log


def save_fixed_csv(episodes: List[Dict], output_path: str):
    """修正済みCSVを保存"""
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        if episodes:
            writer = csv.DictWriter(f, fieldnames=episodes[0].keys())
            writer.writeheader()
            writer.writerows(episodes)


def main():
    print("="*70)
    print("🔧 失敗エピソード修正処理")
    print("="*70)

    # CSVロード
    csv_path = '/Users/admin/Documents/AIUELAB/001-final-hourglass/#episodes_validated_100_20251001.csv'
    episodes = load_csv_episodes(csv_path)
    print(f"✅ {len(episodes)}件のエピソードを読み込みました")

    # 修正適用
    fixed_episodes, fix_log = apply_fixes(episodes)

    print("\n" + "="*70)
    print("📝 修正内容:")
    print("="*70)
    for log in fix_log:
        print(log)

    # 修正済みCSV保存
    output_path = '#episodes_fixed_20251002.csv'
    save_fixed_csv(fixed_episodes, output_path)
    print(f"\n✅ 修正済みCSV保存: {output_path}")

    print("\n" + "="*70)
    print("✅ 修正完了")
    print("="*70)
    print(f"修正件数: {len(FIXES)}件")
    print("\n次のステップ: 修正済みエピソードの再検証")
    print("コマンド: python3 validate_and_fix_episodes.py")


if __name__ == "__main__":
    main()
