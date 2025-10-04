#!/usr/bin/env python3
"""
Phase 1: 9件の重要エピソード修正スクリプト

EP011, EP027, EP033, EP035, EP052, EP060, EP061, EP079, EP091の修正を適用
年齢変更6件を含む
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
    """修正を適用"""
    corrections = corrections_data['corrections']
    fix_log = []

    fix_log.append("=" * 80)
    fix_log.append("🔧 9件のエピソード修正処理")
    fix_log.append("=" * 80)
    fix_log.append("")

    modified_count = 0
    age_changes = 0

    for episode in episodes:
        episode_id = episode['episode_id']

        if episode_id in corrections:
            correction = corrections[episode_id]
            old_age = int(episode['episode_age'])
            new_age = correction['new_age']

            # エピソードテキスト更新
            old_text = episode['episode_text']
            new_text = correction['new_text']
            episode['episode_text'] = new_text

            # 文字数更新
            episode['character_count'] = str(len(new_text))

            # 年齢更新（変更がある場合）
            if old_age != new_age:
                episode['episode_age'] = str(new_age)
                age_changes += 1
                fix_log.append(f"✅ {episode_id} - {correction['person_name']}")
                fix_log.append(f"   年齢変更: {old_age}歳 → {new_age}歳")
            else:
                fix_log.append(f"✅ {episode_id} - {correction['person_name']}")
                fix_log.append(f"   テキストのみ修正（年齢: {new_age}歳のまま）")

            fix_log.append(f"   カテゴリ: {correction['category']}")
            fix_log.append(f"   象徴性スコア: {correction['symbolism_score']}点")
            fix_log.append(f"   文字数: {len(old_text)}文字 → {len(new_text)}文字")
            fix_log.append("")
            fix_log.append(f"   旧: {old_text[:80]}...")
            fix_log.append(f"   新: {new_text[:80]}...")
            fix_log.append("")

            modified_count += 1

    fix_log.append("=" * 80)
    fix_log.append("📊 修正サマリー")
    fix_log.append("=" * 80)
    fix_log.append(f"修正件数: {modified_count}/9件")
    fix_log.append(f"年齢変更: {age_changes}件")
    fix_log.append(f"平均象徴性スコア: {corrections_data['statistics']['average_symbolism_score']}点")
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
    corrections_path = base_path / 'fixes' / 'episode_corrections_v2.json'
    input_csv = base_path / '#episodes_fixed_20251002.csv'
    output_csv = base_path / '#episodes_fixed_v2_20251002.csv'
    log_path = base_path / 'fixes' / 'fix_9_episodes_log.txt'

    print("=" * 80)
    print("🔧 Phase 1: 9件の重要エピソード修正")
    print("=" * 80)
    print()

    # 修正データ読み込み
    print("📂 修正データ読み込み中...")
    corrections_data = load_corrections(str(corrections_path))
    print(f"✅ {corrections_data['total_corrections']}件の修正データを読み込みました")
    print()

    # CSV読み込み
    print("📂 CSVファイル読み込み中...")
    episodes, fieldnames = load_csv_episodes(str(input_csv))
    print(f"✅ {len(episodes)}件のエピソードを読み込みました")
    print()

    # 修正適用
    print("🔄 修正適用中...")
    fixed_episodes, fix_log = apply_corrections(episodes, corrections_data)
    print()

    # ログ出力
    for line in fix_log:
        print(line)

    # CSV保存
    print()
    print("💾 修正済みCSV保存中...")
    save_fixed_csv(fixed_episodes, fieldnames, str(output_csv))
    print(f"✅ 保存完了: {output_csv}")
    print()

    # ログファイル保存
    print("💾 修正ログ保存中...")
    save_fix_log(fix_log, str(log_path))
    print(f"✅ ログ保存: {log_path}")
    print()

    print("=" * 80)
    print("✅ Phase 1 修正完了")
    print("=" * 80)
    print()
    print("次のステップ:")
    print("1. 修正済みエピソードの検証")
    print("2. データベース年齢の更新（6件）")
    print("3. 統合パイプラインでの再検証")
    print()


if __name__ == "__main__":
    main()
