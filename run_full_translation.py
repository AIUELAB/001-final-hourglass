#!/usr/bin/env python3
"""
分割実行型自動翻訳スクリプト
大量データを小分けにして処理（タイムアウト対策）
"""

import json
import time
from datetime import datetime
from pathlib import Path

from auto_translate_names import AutoTranslateNames


def run_batch_translation(start_idx: int = 0, batch_size: int = 500):
    """バッチごとに翻訳を実行"""
    
    print(f"🔄 バッチ翻訳開始 (開始位置: {start_idx}, バッチサイズ: {batch_size})")
    
    # 最新の翻訳済みファイルを探す
    translated_files = list(Path('.').glob('partial_translated_*.json'))
    if translated_files:
        input_file = sorted(translated_files)[-1]
        print(f"  継続ファイル: {input_file}")
    else:
        input_file = 'final_12410_with_display_names.json'
        print(f"  初回ファイル: {input_file}")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        all_data = json.load(f)
    
    # バッチ取得
    data_items = list(all_data.items())
    batch_data = dict(data_items[start_idx:start_idx + batch_size])
    
    if not batch_data:
        print("✅ すべてのデータの処理が完了しました")
        return None, 0
    
    print(f"  処理対象: {len(batch_data)}件")
    
    # 翻訳実行
    translator = AutoTranslateNames()
    updated_batch, log = translator.process_data(batch_data, batch_size=50)
    
    # 元のデータに統合
    for key, value in updated_batch.items():
        all_data[key] = value
    
    # 保存
    output_path = f"partial_translated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    print("\n📊 バッチ結果:")
    print(f"  翻訳成功: {log['stats']['successfully_translated']}件")
    print(f"  出力: {output_path}")
    
    return output_path, log['stats']['successfully_translated']


def main():
    """メイン処理"""
    total_translated = 0
    batch_size = 500
    current_idx = 0
    max_items = 12370
    
    print("🚀 分割型自動翻訳システム起動")
    print(f"  総データ数: {max_items}")
    print(f"  バッチサイズ: {batch_size}")
    print("=" * 60)
    
    while current_idx < max_items:
        batch_num = (current_idx // batch_size) + 1
        print(f"\n📦 バッチ {batch_num} 処理中...")
        
        output_path, translated_count = run_batch_translation(current_idx, batch_size)
        
        if output_path is None:
            break
        
        total_translated += translated_count
        current_idx += batch_size
        
        # 進捗表示
        progress = min(current_idx / max_items * 100, 100)
        print(f"\n📈 全体進捗: {progress:.1f}% ({min(current_idx, max_items)}/{max_items})")
        print(f"  累計翻訳成功: {total_translated}件")
        
        # レート制限対策で少し待機
        if current_idx < max_items:
            print("  ⏳ 次のバッチまで2秒待機...")
            time.sleep(2)
    
    print("\n" + "=" * 60)
    print("✅ 全バッチ処理完了")
    print(f"  総翻訳成功数: {total_translated}件")
    
    # 最終統計レポート生成
    final_files = sorted(Path('.').glob('partial_translated_*.json'))
    if final_files:
        final_file = final_files[-1]
        
        with open(final_file, 'r', encoding='utf-8') as f:
            final_data = json.load(f)
        
        # 統計分析
        japanese_count = 0
        english_count = 0
        
        for item in final_data.values():
            if isinstance(item, dict):
                name = item.get('name', '')
                if any(ord(c) > 127 for c in name):
                    japanese_count += 1
                else:
                    english_count += 1
        
        print("\n📊 最終統計:")
        print(f"  日本語名: {japanese_count}件 ({japanese_count/len(final_data)*100:.1f}%)")
        print(f"  英語名: {english_count}件 ({english_count/len(final_data)*100:.1f}%)")
        print(f"  最終ファイル: {final_file}")


if __name__ == "__main__":
    main()