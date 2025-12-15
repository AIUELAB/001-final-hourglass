#!/usr/bin/env python3
"""
自動翻訳実行スクリプト（制限付き）
レート制限を考慮して段階的に実行
"""

import json
from datetime import datetime
from pathlib import Path

from auto_translate_names import AutoTranslateNames


def run_limited_translation(max_records: int = 1000):
    """制限付き自動翻訳を実行"""

    print(f"🚀 自動翻訳開始（最大{max_records}件）")
    print("=" * 60)

    # データ読み込み
    input_file = 'final_12410_with_display_names.json'
    print(f"📂 入力ファイル: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        all_data = json.load(f)

    print(f"  総データ数: {len(all_data)}")

    # 制限付きデータ取得（英語名を優先的に処理）
    limited_data = {}
    count = 0

    for key, value in all_data.items():
        if count >= max_records:
            break

        # 辞書であることを確認
        if isinstance(value, dict):
            name = value.get('name', '')
            # 英語名っぽいものを優先
            if name and not any(ord(c) > 127 for c in name):
                limited_data[key] = value
                count += 1

    # 足りない場合は残りから追加
    if count < max_records:
        for key, value in all_data.items():
            if count >= max_records:
                break
            if key not in limited_data:
                limited_data[key] = value
                count += 1

    print(f"  処理対象: {len(limited_data)}件")

    # バックアップ
    backup_path = f"backup_limited_translate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(limited_data, f, ensure_ascii=False, indent=2)
    print(f"  バックアップ: {backup_path}")

    # 翻訳実行
    translator = AutoTranslateNames()
    updated_data, log = translator.process_data(limited_data, batch_size=30)

    # 結果を元のデータに統合
    for key, value in updated_data.items():
        all_data[key] = value

    # 統合結果を保存
    output_path = f"partial_translated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)

    # レポート出力
    print("\n" + "=" * 60)
    print("📊 翻訳結果統計")
    print(f"  処理済み: {log['stats']['total_processed']}件")
    print(f"  翻訳成功: {log['stats']['successfully_translated']}件")
    print(f"  既に日本語: {log['stats']['already_japanese']}件")
    print(f"  翻訳失敗: {log['stats']['translation_failed']}件")
    print(f"  Wikidata IDなし: {log['stats']['no_wikidata_id']}件")

    # 成功率計算
    if log['stats']['total_processed'] > 0:
        success_rate = log['stats']['successfully_translated'] / log['stats']['total_processed'] * 100
        print(f"\n  翻訳成功率: {success_rate:.1f}%")

    print(f"\n📁 出力ファイル: {output_path}")
    print("\n✅ 部分翻訳完了")

    return output_path, log


if __name__ == "__main__":
    # 最初は1000件で実行
    output_path, log = run_limited_translation(1000)

    # 成功率が高ければ追加実行を提案
    if log['stats']['successfully_translated'] > 100:
        print("\n💡 翻訳が成功しています。")
        print("   さらに翻訳を続ける場合は、以下を実行してください:")
        print("   python3 run_auto_translate.py --continue")
