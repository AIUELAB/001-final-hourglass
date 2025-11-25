#!/usr/bin/env python3
"""
Phase 1 v3: 文字数削減・品質向上修正

8件のエピソードを132-250文字に削減し、品質スコア7.0以上を目指す
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple


def load_corrections(corrections_path: str) -> Dict:
    """修正データをJSONから読み込み"""
    with open(corrections_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_csv_episodes(csv_path: str) -> Tuple[List[Dict], List[str]]:
    """CSVから全エピソードを読み込み"""
    episodes = []
    fieldnames = []

    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            episodes.append(row)

    return episodes, fieldnames


def apply_corrections(episodes: List[Dict], corrections_data: Dict) -> Tuple[List[Dict], List[str]]:
    """v3修正を適用"""
    corrections = corrections_data['corrections']
    fix_log = []

    fix_log.append("=" * 80)
    fix_log.append("🔧 Phase 1 v3: 文字数削減・品質向上修正")
    fix_log.append("=" * 80)
    fix_log.append("")
    fix_log.append(f"戦略: {corrections_data['correction_strategy']}")
    fix_log.append("")

    modified_count = 0

    for episode in episodes:
        episode_id = episode['episode_id']

        if episode_id in corrections:
            correction = corrections[episode_id]

            # エピソードテキスト更新
            old_text = episode['episode_text']
            new_text = correction['new_text']
            episode['episode_text'] = new_text

            # 文字数更新
            old_count = len(old_text)
            new_count = len(new_text)
            episode['character_count'] = str(new_count)

            fix_log.append(f"✅ {episode_id} - {correction['person_name']}")
            fix_log.append(f"   文字数: {old_count}文字 → {new_count}文字 （-{old_count - new_count}文字）")
            fix_log.append(f"   象徴性スコア: {correction['symbolism_score']}点")
            fix_log.append(f"   修正理由: {correction['reason']}")
            fix_log.append("")
            fix_log.append(f"   旧: {old_text[:60]}...")
            fix_log.append(f"   新: {new_text[:60]}...")
            fix_log.append("")

            modified_count += 1

    fix_log.append("=" * 80)
    fix_log.append("📊 v3修正サマリー")
    fix_log.append("=" * 80)
    fix_log.append(f"修正件数: {modified_count}/8件")
    fix_log.append(f"平均文字数: {corrections_data['statistics']['average_character_count']}文字（132-250文字範囲内）")
    fix_log.append(f"平均象徴性スコア: {corrections_data['statistics']['average_symbolism_score']}点")
    fix_log.append(f"すべて250文字以内: {corrections_data['statistics']['all_within_limit']}")
    fix_log.append(f"客観的事実のみ: {corrections_data['statistics']['objective_only']}")
    fix_log.append("")

    return episodes, fix_log


def save_fixed_csv(episodes: List[Dict], fieldnames: List[str], output_path: str):
    """修正済みCSVを保存（UTF-8 BOM付き）"""
    with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(episodes)


def save_fix_log(log_lines: List[str], output_path: str):
    """修正ログを保存"""
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(log_lines))


def main():
    # パス設定
    base_path = Path('/Users/admin/Documents/AIUELAB/001-final-hourglass')
    corrections_path = base_path / 'fixes' / 'episode_corrections_v3.json'
    input_csv = base_path / '#episodes_fixed_v2_20251002.csv'
    output_csv = base_path / '#episodes_fixed_v3_20251002.csv'
    log_path = base_path / 'fixes' / 'fix_9_episodes_v3_log.txt'

    print("=" * 80)
    print("🔧 Phase 1 v3: 文字数削減・品質向上修正")
    print("=" * 80)
    print()

    # 修正データ読み込み
    print("📂 v3修正データ読み込み中...")
    corrections_data = load_corrections(str(corrections_path))
    print(f"✅ {corrections_data['total_corrections']}件の修正データを読み込みました")
    print()

    # CSV読み込み
    print("📂 CSVファイル読み込み中...")
    episodes, fieldnames = load_csv_episodes(str(input_csv))
    print(f"✅ {len(episodes)}件のエピソードを読み込みました")
    print()

    # 修正適用
    print("🔄 v3修正適用中...")
    fixed_episodes, fix_log = apply_corrections(episodes, corrections_data)
    print()

    # ログ出力
    for line in fix_log:
        print(line)

    # CSV保存
    print()
    print("💾 v3修正済みCSV保存中...")
    save_fixed_csv(fixed_episodes, fieldnames, str(output_csv))
    print(f"✅ 保存完了: {output_csv}")
    print()

    # ログファイル保存
    print("💾 v3修正ログ保存中...")
    save_fix_log(fix_log, str(log_path))
    print(f"✅ ログ保存: {log_path}")
    print()

    print("=" * 80)
    print("✅ Phase 1 v3修正完了")
    print("=" * 80)
    print()
    print("次のステップ:")
    print("1. v3修正済みエピソードの再検証")
    print("2. 合格率98%以上を確認")
    print("3. Phase 2: 新ルール実装に進む")
    print()


if __name__ == "__main__":
    main()
