#!/usr/bin/env python3
"""
person_name_displayフィールドのバグ修正
「小文字英語＋カタカナ」パターンを正しい形式に修正
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple


class DisplayNameFixer:
    """表示名の不適切な混在を修正"""
    
    def __init__(self):
        # 完全翻訳辞書（フルネーム用）
        self.full_name_translations = {
            # アインシュタイン関連
            'alfred einstein': 'アルフレッド・アインシュタイン',
            'albert einstein': 'アルベルト・アインシュタイン',
            
            # シュラインシュタイン関連
            'bruno schleinstein': 'ブルーノ・シュラインシュタイン',
            
            # 有名人
            'charles darwin': 'チャールズ・ダーウィン',
            'frederick newton': 'フレデリック・ニュートン',
            'isaac newton': 'アイザック・ニュートン',
            'ludwig van beethoven': 'ルートヴィヒ・ヴァン・ベートーヴェン',
            
            # バッハ関連
            'johann sebastian bach': 'ヨハン・セバスティアン・バッハ',
            'johann christoph bach': 'ヨハン・クリストフ・バッハ',
            'angelika bachmann': 'アンゲリカ・バッハマン',
            'baron d\'holbach': 'ドルバック男爵',
            
            # その他の音楽家
            'bernd karbach': 'ベルント・カールバッハ',
            'christian goldbach': 'クリスティアン・ゴルトバッハ',
            'christian karl august ludwig von massenbach': 'クリスティアン・カール・アウグスト・ルートヴィヒ・フォン・マッセンバッハ',
            'christian von seebach': 'クリスティアン・フォン・ゼーバッハ',
            'constant von wurzbach': 'コンスタント・フォン・ヴルツバッハ',
            'constanze mozart': 'コンスタンツェ・モーツァルト',
            
            # 作曲家
            'elias ammerbacher': 'エリアス・アンマーバッハー',
            'erich auerbach': 'エーリッヒ・アウエルバッハ',
            'ezriel carlebach': 'エズリエル・カールレバッハ',
            'friedrich holderlin': 'フリードリヒ・ヘルダーリン',
            'fritz steinbach': 'フリッツ・シュタインバッハ',
            
            # その他
            'harivansh rai bachchan': 'ハリヴァンシュ・ライ・バッチャン',
            'jacques offenbach': 'ジャック・オッフェンバック',
            'klaus steinbach': 'クラウス・シュタインバッハ',
            'lorenz diefenbach': 'ローレンツ・ディーフェンバッハ',
            'paul johann anselm ritter von feuerbach': 'パウル・ヨハン・アンゼルム・リッター・フォン・フォイエルバッハ',
            'ralf reichenbach': 'ラルフ・ライヒェンバッハ',
            'wolfram von eschenbach': 'ヴォルフラム・フォン・エッシェンバッハ'
        }
        
        # 名前のパーツ変換
        self.first_name_translations = {
            'alfred': 'アルフレッド',
            'albert': 'アルベルト', 
            'bruno': 'ブルーノ',
            'charles': 'チャールズ',
            'frederick': 'フレデリック',
            'johann': 'ヨハン',
            'christian': 'クリスティアン',
            'wolfgang': 'ヴォルフガング',
            'ludwig': 'ルートヴィヒ',
            'friedrich': 'フリードリヒ',
            'paul': 'パウル',
            'karl': 'カール',
            'wilhelm': 'ヴィルヘルム',
            'georg': 'ゲオルク',
            'heinrich': 'ハインリヒ',
            'otto': 'オットー',
            'ernst': 'エルンスト',
            'max': 'マックス',
            'hans': 'ハンス',
            'franz': 'フランツ'
        }
        
        self.stats = {
            'total': 0,
            'fixed': 0,
            'already_correct': 0,
            'problematic_patterns': 0
        }
    
    def detect_problematic_pattern(self, name: str) -> bool:
        """問題のあるパターンを検出"""
        # パターン: 小文字英語 + スペース + カタカナ
        pattern = r'^[a-z]+[\s\w]*[\u30A0-\u30FF]'
        return bool(re.match(pattern, name))
    
    def fix_display_name(self, name: str) -> str:
        """表示名を修正"""
        # まず完全一致を探す
        name_lower = name.lower()
        if name_lower in self.full_name_translations:
            return self.full_name_translations[name_lower]
        
        # 問題のあるパターンを検出
        if not self.detect_problematic_pattern(name):
            return name  # 問題なければそのまま
        
        # 小文字英語部分とカタカナ部分を分離
        match = re.match(r'^([a-z\s]+?)\s*([\u30A0-\u30FF\u30FC・]+.*)$', name)
        if match:
            english_part = match.group(1).strip()
            katakana_part = match.group(2).strip()
            
            # 英語部分を変換
            # 複数の単語がある場合
            words = english_part.split()
            translated_words = []
            
            for word in words:
                if word in self.first_name_translations:
                    translated_words.append(self.first_name_translations[word])
                else:
                    # 最初の文字を大文字にして返す（修正できない場合）
                    translated_words.append(word.capitalize())
            
            # 結合
            if translated_words and all('・' not in w and not re.match(r'^[A-Z]', w) for w in translated_words):
                # すべて日本語に変換できた場合
                return '・'.join(translated_words) + '・' + katakana_part
            else:
                # 一部変換できなかった場合は、元の形式を維持
                return ' '.join(translated_words) + ' ' + katakana_part
        
        return name
    
    def process_all_data(self, input_file: str = None) -> Tuple[str, Dict]:
        """全データを処理"""
        
        # 最新のデータファイルを探す
        if not input_file:
            candidates = list(Path('.').glob('final_with_birth_year_*.json'))
            if candidates:
                input_file = str(max(candidates, key=lambda p: p.stat().st_mtime))
            else:
                print("⚠️ 入力ファイルが見つかりません")
                return None, self.stats
        
        print("🔧 person_name_display バグ修正開始")
        print(f"  入力: {input_file}")
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['total'] = len(data)
        
        # 問題のあるデータのサンプル
        problematic_samples = []
        fixed_samples = []
        
        # 各レコードを処理
        for key, value in data.items():
            if isinstance(value, dict):
                # preferred_display_name を修正
                if 'preferred_display_name' in value:
                    original = value['preferred_display_name']
                    
                    if self.detect_problematic_pattern(original):
                        self.stats['problematic_patterns'] += 1
                        fixed = self.fix_display_name(original)
                        
                        if fixed != original:
                            value['preferred_display_name'] = fixed
                            self.stats['fixed'] += 1
                            
                            if len(fixed_samples) < 20:
                                fixed_samples.append({
                                    'original': original,
                                    'fixed': fixed
                                })
                        
                        if len(problematic_samples) < 10:
                            problematic_samples.append(original)
                    else:
                        self.stats['already_correct'] += 1
                
                # name フィールドも同様に修正
                if 'name' in value:
                    original_name = value['name']
                    if self.detect_problematic_pattern(original_name):
                        fixed_name = self.fix_display_name(original_name)
                        if fixed_name != original_name:
                            value['name'] = fixed_name
        
        # 結果保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"display_name_fixed_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # レポート出力
        print("\n📊 修正結果:")
        print(f"  総レコード: {self.stats['total']:,}")
        print(f"  問題パターン検出: {self.stats['problematic_patterns']:,}")
        print(f"  修正済み: {self.stats['fixed']:,}")
        print(f"  既に正常: {self.stats['already_correct']:,}")
        
        if fixed_samples:
            print("\n📝 修正例:")
            for sample in fixed_samples[:10]:
                print(f"  {sample['original']:30} → {sample['fixed']}")
        
        print(f"\n✅ 出力: {output_file}")
        
        return output_file, self.stats


def main():
    """メイン実行"""
    fixer = DisplayNameFixer()
    output_file, stats = fixer.process_all_data()
    
    if output_file:
        print("\n🎯 バグ修正完了")
        print(f"  修正率: {stats['fixed'] / max(stats['problematic_patterns'], 1) * 100:.1f}%")
        print("  次のステップ: correct_csv_exporter.py で最終CSV生成")


if __name__ == "__main__":
    main()