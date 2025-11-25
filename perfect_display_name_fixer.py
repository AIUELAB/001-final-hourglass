#!/usr/bin/env python3
"""
person_name_displayフィールドの完全修正
翻訳バグで生じた不適切な混在パターンを完全に修正
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class PerfectDisplayNameFixer:
    """表示名を完全に修正"""

    def __init__(self):
        # 問題のあるパターンのマッピング（実際のデータから）
        self.specific_fixes = {
            # アインシュタイン系
            'alfred アインシュタイン': 'アルフレッド・アインシュタイン',
            'bruno schlアインシュタイン': 'ブルーノ・シュラインシュタイン',

            # ダーウィン系
            'charles ダーウィン': 'チャールズ・ダーウィン',

            # ニュートン系
            'frederick ニュートン': 'フレデリック・ニュートン',

            # ベートーヴェン系
            'ludwig van ベートーヴェン': 'ルートヴィヒ・ヴァン・ベートーヴェン',

            # バッハ系（部分的な置換のバグ）
            'angelika バッハmann': 'アンゲリカ・バッハマン',
            'bernd karバッハer': 'ベルント・カールバッハー',
            'christian goldバッハ': 'クリスティアン・ゴルトバッハ',
            'christian karl august ludwig von massenバッハ': 'クリスティアン・カール・アウグスト・ルートヴィヒ・フォン・マッセンバッハ',
            'christian von seeバッハ': 'クリスティアン・フォン・ゼーバッハ',
            'constant von wurzバッハ': 'コンスタント・フォン・ヴルツバッハ',
            'elias ammerバッハ': 'エリアス・アンマーバッハー',
            'erich auerバッハ': 'エーリヒ・アウエルバッハ',
            'ezriel carleバッハ': 'エズリエル・カールレバッハ',
            'friedrich hölバッハ': 'フリードリヒ・ヘルダーバッハ',
            'fritz steinバッハ': 'フリッツ・シュタインバッハ',
            'harivansh rai バッハchan': 'ハリヴァンシュ・ライ・バッチャン',
            'jacques offenバッハ': 'ジャック・オッフェンバッハ',
            'klaus steinバッハ': 'クラウス・シュタインバッハ',
            'lorenz diefenバッハ': 'ローレンツ・ディーフェンバッハ',
            'paul johann anselm ritter von feuerバッハ': 'パウル・ヨハン・アンゼルム・リッター・フォン・フォイエルバッハ',
            'ralf reichenバッハ': 'ラルフ・ライヒェンバッハ',
            'wolfram von eschenバッハ': 'ヴォルフラム・フォン・エッシェンバッハ',

            # モーツァルト系
            'constanze モーツァルト': 'コンスタンツェ・モーツァルト',

            # レオナルド系
            'レオナルド': 'レオナルド・ダ・ヴィンチ',  # 必要に応じて

            # その他
            'baron d\'holバッハ': 'ドルバック男爵',

            # リンカーン系
            'curt リンカーン': 'カート・リンカーン',
            'abraham リンカーン': 'エイブラハム・リンカーン',

            # カエサル系
            'hyacinth of カエサルea': 'カエサレアのヒュアキントス'
        }

        # 職業による判定
        self.composer_names = {
            'Bach', 'Mozart', 'Beethoven', 'Wagner', 'Brahms', 'Schubert',
            'Chopin', 'Liszt', 'Vivaldi', 'Handel', 'Verdi', 'Tchaikovsky'
        }

        self.stats = {
            'total': 0,
            'fixed': 0,
            'already_correct': 0,
            'problematic_found': 0,
            'pattern_types': {}
        }

    def detect_all_problematic_patterns(self, name: str) -> List[str]:
        """すべての問題パターンを検出"""
        patterns = []

        # パターン1: 小文字で始まる + カタカナ
        if re.match(r'^[a-z].*[\u30A0-\u30FF]', name):
            patterns.append('lowercase_start_with_katakana')

        # パターン2: 英語とカタカナが不自然に混在
        if re.search(r'[a-zA-Z]+[\u30A0-\u30FF]+[a-zA-Z]+', name):
            patterns.append('mixed_english_katakana')

        # パターン3: カタカナが単語の途中に挿入
        if re.search(r'[a-zA-Z]+[\u30A0-\u30FF]+[a-z]+', name):
            patterns.append('katakana_in_middle')

        return patterns

    def fix_display_name_complete(self, name: str, occupation: str = '') -> str:
        """表示名を完全に修正"""

        # 特定の修正マッピングをチェック
        if name in self.specific_fixes:
            return self.specific_fixes[name]

        # 問題パターンを検出
        patterns = self.detect_all_problematic_patterns(name)

        if not patterns:
            return name  # 問題なし

        # パターン統計
        for pattern in patterns:
            self.stats['pattern_types'][pattern] = self.stats['pattern_types'].get(pattern, 0) + 1

        # 修正ロジック

        # 1. カタカナが単語の途中に挿入されている場合（バッハmann → バッハマン）
        if 'katakana_in_middle' in patterns:
            # パターン: 英語+カタカナ+英語小文字
            fixed = re.sub(r'([a-zA-Z]+)([\u30A0-\u30FF]+)([a-z]+)',
                          lambda m: self.merge_katakana_word(m.group(1), m.group(2), m.group(3)),
                          name)
            if fixed != name:
                return fixed

        # 2. 小文字で始まる名前を修正
        if 'lowercase_start_with_katakana' in patterns:
            # 最初の単語を大文字化
            words = name.split()
            if words and words[0][0].islower():
                words[0] = words[0].capitalize()
                return ' '.join(words)

        # 3. デフォルト: そのまま返す（完全な修正が難しい場合）
        return name

    def merge_katakana_word(self, prefix: str, katakana: str, suffix: str) -> str:
        """カタカナが途中に挿入された単語を修正"""
        # 例: karバッハer → カールバッハャー

        # 一般的な語尾変換
        suffix_map = {
            'mann': 'マン',
            'man': 'マン',
            'er': 'ャー',
            'en': 'ェン',
            'on': 'ォン',
            'an': 'アン',
            'chan': 'チャン'
        }

        # 語尾を変換
        katakana_suffix = suffix_map.get(suffix.lower(), suffix.upper())

        # 接頭辞も日本語化（簡単な変換）
        prefix_lower = prefix.lower()
        if prefix_lower in ['kar', 'carl']:
            prefix_katakana = 'カール'
        elif prefix_lower == 'gold':
            prefix_katakana = 'ゴルト'
        elif prefix_lower == 'see':
            prefix_katakana = 'ゼー'
        elif prefix_lower == 'wurz':
            prefix_katakana = 'ヴルツ'
        elif prefix_lower == 'ammer':
            prefix_katakana = 'アンマー'
        elif prefix_lower == 'auer':
            prefix_katakana = 'アウエル'
        elif prefix_lower == 'carle':
            prefix_katakana = 'カールレ'
        elif prefix_lower == 'stein':
            prefix_katakana = 'シュタイン'
        elif prefix_lower == 'diefen':
            prefix_katakana = 'ディーフェン'
        elif prefix_lower == 'feuer':
            prefix_katakana = 'フォイエル'
        elif prefix_lower == 'reichen':
            prefix_katakana = 'ライヒェン'
        elif prefix_lower == 'eschen':
            prefix_katakana = 'エッシェン'
        elif prefix_lower == 'offen':
            prefix_katakana = 'オッフェン'
        elif prefix_lower == 'massen':
            prefix_katakana = 'マッセン'
        elif prefix_lower == 'hol' or prefix_lower == 'hol':
            prefix_katakana = 'ホル'
        else:
            # デフォルト: 最初の文字を大文字化
            return prefix.capitalize() + katakana + suffix

        return prefix_katakana + katakana + katakana_suffix

    def process_all_data(self, input_file: str = None) -> Tuple[str, Dict]:
        """全データを処理"""

        # 入力ファイル
        if not input_file:
            # 前回の修正ファイルを使用
            candidates = list(Path('.').glob('display_name_fixed_*.json'))
            if candidates:
                input_file = str(max(candidates, key=lambda p: p.stat().st_mtime))
            else:
                # なければ birth_year ファイルを使用
                candidates = list(Path('.').glob('final_with_birth_year_*.json'))
                if candidates:
                    input_file = str(max(candidates, key=lambda p: p.stat().st_mtime))
                else:
                    print("⚠️ 入力ファイルが見つかりません")
                    return None, self.stats

        print("🔧 person_name_display 完全修正開始")
        print(f"  入力: {input_file}")

        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.stats['total'] = len(data)

        # 修正サンプル
        fixed_samples = []

        # 各レコードを処理
        for key, value in data.items():
            if isinstance(value, dict):
                occupation = value.get('occupation', '')

                # preferred_display_name を修正
                if 'preferred_display_name' in value:
                    original = value['preferred_display_name']

                    patterns = self.detect_all_problematic_patterns(original)
                    if patterns:
                        self.stats['problematic_found'] += 1
                        fixed = self.fix_display_name_complete(original, occupation)

                        if fixed != original:
                            value['preferred_display_name'] = fixed
                            self.stats['fixed'] += 1

                            if len(fixed_samples) < 30:
                                fixed_samples.append({
                                    'original': original,
                                    'fixed': fixed,
                                    'patterns': patterns
                                })
                    else:
                        self.stats['already_correct'] += 1

                # name フィールドも修正
                if 'name' in value:
                    original_name = value['name']
                    patterns = self.detect_all_problematic_patterns(original_name)
                    if patterns:
                        fixed_name = self.fix_display_name_complete(original_name, occupation)
                        if fixed_name != original_name:
                            value['name'] = fixed_name

        # 結果保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"perfect_display_fixed_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # レポート出力
        print("\n📊 完全修正結果:")
        print(f"  総レコード: {self.stats['total']:,}")
        print(f"  問題検出: {self.stats['problematic_found']:,}")
        print(f"  修正済み: {self.stats['fixed']:,}")
        print(f"  既に正常: {self.stats['already_correct']:,}")

        if self.stats['pattern_types']:
            print("\n📈 パターン分析:")
            for pattern, count in sorted(self.stats['pattern_types'].items(), key=lambda x: -x[1]):
                print(f"  {pattern}: {count}件")

        if fixed_samples:
            print("\n📝 修正例:")
            for sample in fixed_samples[:20]:
                print(f"  {sample['original']:35} → {sample['fixed']}")

        print(f"\n✅ 出力: {output_file}")

        return output_file, self.stats


def main():
    """メイン実行"""
    fixer = PerfectDisplayNameFixer()
    output_file, stats = fixer.process_all_data()

    if output_file:
        print("\n🎯 完全修正完了")
        print(f"  修正率: {stats['fixed'] / max(stats['problematic_found'], 1) * 100:.1f}%")
        print("  次のステップ: correct_csv_exporter.py で最終CSV生成")


if __name__ == "__main__":
    main()
