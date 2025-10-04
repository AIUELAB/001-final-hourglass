#!/usr/bin/env python3
"""
FORMAT_ERROR一括修正スクリプト
最大の違反要因（90件）を一括修正
"""

import pandas as pd
import re
from datetime import datetime
from pdca_guardian import PDCAGuardian
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

def fix_format_error(episode_text: str, person_name: str, age: int) -> str:
    """
    FORMAT_ERRORを修正
    正しいフォーマット: 「あなたと同じX歳のとき、名前（X歳）は」
    """

    # パターン1: 「実は」で始まる場合
    if episode_text.startswith("実は"):
        # 「実はあなたと同じX歳のとき、名前は」→「あなたと同じX歳のとき、名前（X歳）は実は」
        pattern = f"実はあなたと同じ{age}歳のとき、{person_name}は"
        replacement = f"あなたと同じ{age}歳のとき、{person_name}（{age}歳）は実は"
        episode_text = episode_text.replace(pattern, replacement)

    # パターン2: 「あなたと同じX歳のとき、名前は」（年齢表記なし）
    elif f"あなたと同じ{age}歳のとき、{person_name}は" in episode_text:
        pattern = f"あなたと同じ{age}歳のとき、{person_name}は"
        replacement = f"あなたと同じ{age}歳のとき、{person_name}（{age}歳）は"
        episode_text = episode_text.replace(pattern, replacement)

    # パターン3: その他の開始パターン
    else:
        # 標準フォーマットで開始するよう修正
        if not episode_text.startswith(f"あなたと同じ{age}歳のとき"):
            # 名前で始まる場合
            if episode_text.startswith(person_name):
                episode_text = f"あなたと同じ{age}歳のとき、{episode_text}"
            else:
                # その他の場合は先頭に追加
                episode_text = f"あなたと同じ{age}歳のとき、{person_name}（{age}歳）は{episode_text}"

    return episode_text


def process_csv():
    """CSVファイルを処理してFORMAT_ERRORを修正"""

    # CSVファイル読み込み
    csv_file = 'ultra_think_improved_20250922_063204.csv'
    logger.info(f"📂 読み込みファイル: {csv_file}")

    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    logger.info(f"✅ {len(df)}件のエピソードを読み込み")

    guardian = PDCAGuardian()

    format_error_count = 0
    fixed_count = 0
    fixed_episodes = []

    logger.info("\n" + "="*60)
    logger.info("FORMAT_ERROR修正開始")
    logger.info("="*60)

    for idx, row in df.iterrows():
        person_name = row['person_name']
        age = row['episode_age']
        original_episode = row.get('episode_improved', row['episode_text'])
        person_name_display = f"{person_name}（{age}歳）"

        # 違反チェック
        violations = guardian.check_episode_quality(
            episode_text=original_episode,
            age=age,
            person_name_display=person_name_display
        )

        # FORMAT_ERRORがあるか確認
        has_format_error = any(v.get('type') == 'FORMAT_ERROR' for v in violations)

        if has_format_error:
            format_error_count += 1

            # 修正実行
            fixed_episode = fix_format_error(original_episode, person_name, age)

            # 修正後の違反チェック
            new_violations = guardian.check_episode_quality(
                episode_text=fixed_episode,
                age=age,
                person_name_display=person_name_display
            )

            # FORMAT_ERRORが解消されたか確認
            still_has_format_error = any(v.get('type') == 'FORMAT_ERROR' for v in new_violations)

            if not still_has_format_error:
                fixed_count += 1
                logger.info(f"✅ [{idx+1}/{len(df)}] {person_name}（{age}歳）: FORMAT_ERROR修正成功")
                fixed_episodes.append(fixed_episode)
            else:
                logger.warning(f"⚠️ [{idx+1}/{len(df)}] {person_name}（{age}歳）: FORMAT_ERROR修正失敗")
                fixed_episodes.append(original_episode)
        else:
            fixed_episodes.append(original_episode)

    # 修正結果をDataFrameに反映
    df['episode_fixed_format'] = fixed_episodes

    # 結果を保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_format_fixed_{timestamp}.csv'
    df.to_csv(output_file, index=False, encoding='utf-8-sig')

    logger.info("\n" + "="*60)
    logger.info("修正結果サマリー")
    logger.info("="*60)
    logger.info(f"📊 FORMAT_ERROR検出数: {format_error_count}")
    logger.info(f"✅ 修正成功数: {fixed_count}")
    logger.info(f"⚠️ 修正失敗数: {format_error_count - fixed_count}")
    logger.info(f"📈 修正成功率: {(fixed_count/format_error_count*100) if format_error_count > 0 else 0:.1f}%")
    logger.info(f"💾 保存先: {output_file}")

    return output_file, fixed_count, format_error_count


if __name__ == "__main__":
    output_file, fixed, total = process_csv()

    if fixed > 0:
        print(f"\n✨ {fixed}件のFORMAT_ERRORを修正しました")
        print(f"📄 修正済みファイル: {output_file}")
    else:
        print("\n⚠️ FORMAT_ERRORの修正ができませんでした")