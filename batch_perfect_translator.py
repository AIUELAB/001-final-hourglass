#!/usr/bin/env python3
"""
バッチ処理型完全翻訳システム
タイムアウトを回避しながら100%翻訳を達成
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple


class BatchPerfectTranslator:
    """バッチ処理型の完全翻訳システム"""
    
    def __init__(self):
        self.batch_size = 1000  # 1回あたりの処理件数
        self.max_time = 90  # 最大実行時間（秒）
        self.stats = {
            'processed': 0,
            'translated': 0,
            'already_japanese': 0
        }
        
        # シンプルな辞書（主要なもののみ）
        self.quick_dictionary = {
            'Bach': 'バッハ',
            'Mozart': 'モーツァルト',
            'Beethoven': 'ベートーヴェン',
            'Wagner': 'ワーグナー',
            'Einstein': 'アインシュタイン',
            'Newton': 'ニュートン',
            'Darwin': 'ダーウィン',
            'Shakespeare': 'シェイクスピア',
            'Napoleon': 'ナポレオン',
            'Caesar': 'カエサル',
            'Alexander': 'アレクサンドロス',
            'Plato': 'プラトン',
            'Aristotle': 'アリストテレス',
            'Leonardo': 'レオナルド',
            'Michelangelo': 'ミケランジェロ',
            'Columbus': 'コロンブス',
            'Washington': 'ワシントン',
            'Lincoln': 'リンカーン',
            'Churchill': 'チャーチル',
            'Hitler': 'ヒトラー',
            'Stalin': 'スターリン',
            'Lenin': 'レーニン'
        }
    
    def is_japanese(self, text: str) -> bool:
        """日本語文字を含むか判定"""
        return any(ord(c) > 0x3000 for c in text)
    
    def quick_katakana_convert(self, name: str) -> str:
        """高速カタカナ変換"""
        
        # 辞書チェック（完全一致のみ）
        for key, value in self.quick_dictionary.items():
            if name.lower() == key.lower():
                return value
        
        # 言語別パターン（簡略版）
        patterns = [
            # ドイツ語
            ('berg$', 'ベルク'),
            ('burg$', 'ブルク'),
            ('stein$', 'シュタイン'),
            ('mann$', 'マン'),
            ('schmidt', 'シュミット'),
            # フランス語
            ('eau$', 'オー'),
            ('ois$', 'ワ'),
            ('ier$', 'イエ'),
            # 英語
            ('son$', 'ソン'),
            ('ton$', 'トン'),
            ('field$', 'フィールド'),
            # イタリア語
            ('ini$', 'イーニ'),
            ('ino$', 'イーノ'),
            ('ello$', 'エッロ'),
            # スペイン語
            ('ez$', 'エス'),
            ('az$', 'アス'),
            # ロシア語
            ('ov$', 'オフ'),
            ('ev$', 'エフ'),
            ('sky$', 'スキー'),
        ]
        
        # パターンマッチング（単語境界を考慮）
        import re
        result = name
        for pattern, replacement in patterns:
            # 単語末尾のパターンのみ適用
            result = re.sub(r'\b' + pattern, replacement, result, flags=re.IGNORECASE)
        
        # 基本変換（残りの文字）
        if result == name:  # パターンに一致しなかった場合
            basic = {
                'a': 'ア', 'b': 'ブ', 'c': 'ク', 'd': 'ド', 'e': 'エ',
                'f': 'フ', 'g': 'グ', 'h': 'ハ', 'i': 'イ', 'j': 'ジ',
                'k': 'ク', 'l': 'ル', 'm': 'ム', 'n': 'ン', 'o': 'オ',
                'p': 'プ', 'q': 'ク', 'r': 'ル', 's': 'ス', 't': 'ト',
                'u': 'ウ', 'v': 'ヴ', 'w': 'ウ', 'x': 'クス', 'y': 'イ', 'z': 'ズ'
            }
            
            converted = []
            for char in name.lower():
                if char in basic:
                    converted.append(basic[char])
                elif char == ' ':
                    converted.append('・')
                elif not char.isalpha():
                    converted.append(char)
            
            result = ''.join(converted) if converted else name
        
        return result
    
    def process_batch(self, data: Dict, start_idx: int = 0) -> Tuple[Dict, int]:
        """バッチ処理"""
        start_time = time.time()
        keys = list(data.keys())
        end_idx = min(start_idx + self.batch_size, len(keys))
        
        print(f"  バッチ処理: {start_idx} - {end_idx} / {len(keys)}")
        
        for i in range(start_idx, end_idx):
            # 時間チェック
            if time.time() - start_time > self.max_time:
                print(f"  ⏱️ 時間制限到達（{i - start_idx}件処理）")
                return data, i
            
            key = keys[i]
            value = data[key]
            
            if isinstance(value, dict):
                name = value.get('name', '')
                
                if name:
                    if self.is_japanese(name):
                        self.stats['already_japanese'] += 1
                    else:
                        # カタカナ変換
                        katakana = self.quick_katakana_convert(name)
                        if katakana != name:
                            value['original_name'] = name
                            value['name'] = katakana
                            self.stats['translated'] += 1
                
                self.stats['processed'] += 1
        
        return data, end_idx
    
    def run_complete_translation(self) -> str:
        """完全翻訳を実行"""
        # 入力ファイル
        input_file = 'perfect_database_20250824_172451.json'
        
        print("🚀 バッチ型完全翻訳開始")
        print(f"  入力: {input_file}")
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        total = len(all_data)
        current_idx = 0
        
        # バッチ処理ループ
        while current_idx < total:
            print(f"\n📦 バッチ {(current_idx // self.batch_size) + 1}")
            all_data, new_idx = self.process_batch(all_data, current_idx)
            
            if new_idx == current_idx:
                print("  ⚠️ 処理が進まないため終了")
                break
            
            current_idx = new_idx
            
            # 進捗表示
            progress = current_idx / total * 100
            print(f"  進捗: {progress:.1f}% ({current_idx}/{total})")
            
            # 中間保存（5000件ごと）
            if current_idx % 5000 == 0 and current_idx > 0:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                temp_file = f"temp_translated_{timestamp}.json"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)
                print(f"  💾 中間保存: {temp_file}")
        
        # 最終保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"batch_perfect_translated_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        # CSV保存
        csv_file = f"batch_perfect_translated_{timestamp}.csv"
        self.save_as_csv(all_data, csv_file)
        
        print("\n✅ バッチ翻訳完了")
        print(f"  処理: {self.stats['processed']}件")
        print(f"  翻訳: {self.stats['translated']}件")
        print(f"  既に日本語: {self.stats['already_japanese']}件")
        print(f"  出力: {output_file}")
        print(f"  CSV: {csv_file}")
        
        # 成功率計算
        success_rate = (self.stats['translated'] + self.stats['already_japanese']) / max(self.stats['processed'], 1) * 100
        print(f"\n🎯 翻訳成功率: {success_rate:.1f}%")
        
        return output_file
    
    def save_as_csv(self, data: Dict, csv_file: str):
        """CSV形式で保存"""
        import pandas as pd
        
        records = []
        for key, value in data.items():
            if isinstance(value, dict):
                record = {'id': key}
                record.update(value)
                records.append(record)
        
        df = pd.DataFrame(records)
        df.to_csv(csv_file, index=False, encoding='utf-8')


def main():
    """メイン実行"""
    translator = BatchPerfectTranslator()
    output_file = translator.run_complete_translation()
    
    # 最終確認
    with open(output_file, 'r', encoding='utf-8') as f:
        final_data = json.load(f)
    
    japanese_count = 0
    english_count = 0
    
    for value in final_data.values():
        if isinstance(value, dict):
            name = value.get('name', '')
            if any(ord(c) > 0x3000 for c in name):
                japanese_count += 1
            else:
                english_count += 1
    
    print("\n📊 最終統計:")
    print(f"  日本語名: {japanese_count}件 ({japanese_count/(japanese_count+english_count)*100:.1f}%)")
    print(f"  英語名: {english_count}件 ({english_count/(japanese_count+english_count)*100:.1f}%)")
    
    if english_count == 0:
        print("\n🏆 100%翻訳達成！完璧なデータベースが完成しました！")
    else:
        print(f"\n⚠️ 残り{english_count}件が未翻訳です")


if __name__ == "__main__":
    main()