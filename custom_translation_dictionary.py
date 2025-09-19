#!/usr/bin/env python3
"""
カスタム翻訳辞書システム
頻出する名前、歴史的人物、有名人の確立された日本語表記を管理
"""

import json
from pathlib import Path
from typing import Dict, Optional, Tuple


class CustomTranslationDictionary:
    """カスタム翻訳辞書システム"""
    
    def __init__(self):
        self.dictionary = self.build_comprehensive_dictionary()
        self.translation_cache = self.load_cache()
        self.stats = {
            'processed': 0,
            'translated': 0,
            'cached': 0,
            'not_found': 0
        }
    
    def load_cache(self) -> Dict[str, str]:
        """翻訳キャッシュを読み込み"""
        cache_file = Path('translation_cache.json')
        if cache_file.exists():
            with open(cache_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def save_cache(self):
        """翻訳キャッシュを保存"""
        with open('translation_cache.json', 'w', encoding='utf-8') as f:
            json.dump(self.translation_cache, f, ensure_ascii=False, indent=2)
    
    def build_comprehensive_dictionary(self) -> Dict[str, str]:
        """包括的な翻訳辞書を構築"""
        return {
            # 古代ローマの人物
            'Gaius Julius Caesar': 'ガイウス・ユリウス・カエサル',
            'Marcus Aurelius': 'マルクス・アウレリウス',
            'Augustus': 'アウグストゥス',
            'Nero': 'ネロ',
            'Cicero': 'キケロ',
            'Seneca': 'セネカ',
            'Marcus Antonius': 'マルクス・アントニウス',
            'Pompey': 'ポンペイウス',
            'Brutus': 'ブルータス',
            'Hadrian': 'ハドリアヌス',
            'Trajan': 'トラヤヌス',
            'Constantine': 'コンスタンティヌス',
            'Diocletian': 'ディオクレティアヌス',
            'Tiberius': 'ティベリウス',
            'Caligula': 'カリグラ',
            'Claudius': 'クラウディウス',
            'Vespasian': 'ウェスパシアヌス',
            'Titus': 'ティトゥス',
            'Domitian': 'ドミティアヌス',
            
            # 古代ギリシャの人物
            'Socrates': 'ソクラテス',
            'Plato': 'プラトン',
            'Aristotle': 'アリストテレス',
            'Alexander the Great': 'アレクサンドロス大王',
            'Homer': 'ホメロス',
            'Pythagoras': 'ピタゴラス',
            'Herodotus': 'ヘロドトス',
            'Thucydides': 'トゥキディデス',
            'Pericles': 'ペリクレス',
            'Sophocles': 'ソフォクレス',
            'Euripides': 'エウリピデス',
            'Archimedes': 'アルキメデス',
            
            # 中世・近世の君主
            'Charlemagne': 'カール大帝',
            'Napoleon Bonaparte': 'ナポレオン・ボナパルト',
            'Louis XIV': 'ルイ14世',
            'Elizabeth I': 'エリザベス1世',
            'Henry VIII': 'ヘンリー8世',
            'Peter the Great': 'ピョートル大帝',
            'Catherine the Great': 'エカテリーナ2世',
            'Frederick the Great': 'フリードリヒ大王',
            'Charles V': 'カール5世',
            'Philip II': 'フェリペ2世',
            
            # 作曲家
            'Johann Sebastian Bach': 'ヨハン・セバスティアン・バッハ',
            'Ludwig van Beethoven': 'ルートヴィヒ・ヴァン・ベートーヴェン',
            'Wolfgang Amadeus Mozart': 'ヴォルフガング・アマデウス・モーツァルト',
            'Johannes Brahms': 'ヨハネス・ブラームス',
            'Richard Wagner': 'リヒャルト・ワーグナー',
            'Franz Schubert': 'フランツ・シューベルト',
            'Frédéric Chopin': 'フレデリック・ショパン',
            'Franz Liszt': 'フランツ・リスト',
            'Giuseppe Verdi': 'ジュゼッペ・ヴェルディ',
            'Pyotr Tchaikovsky': 'ピョートル・チャイコフスキー',
            'Claude Debussy': 'クロード・ドビュッシー',
            'Maurice Ravel': 'モーリス・ラヴェル',
            'Igor Stravinsky': 'イーゴリ・ストラヴィンスキー',
            'Antonio Vivaldi': 'アントニオ・ヴィヴァルディ',
            'George Frideric Handel': 'ゲオルク・フリードリヒ・ヘンデル',
            
            # 科学者
            'Albert Einstein': 'アルベルト・アインシュタイン',
            'Isaac Newton': 'アイザック・ニュートン',
            'Charles Darwin': 'チャールズ・ダーウィン',
            'Marie Curie': 'マリー・キュリー',
            'Galileo Galilei': 'ガリレオ・ガリレイ',
            'Johannes Kepler': 'ヨハネス・ケプラー',
            'Nicolaus Copernicus': 'ニコラウス・コペルニクス',
            'Michael Faraday': 'マイケル・ファラデー',
            'James Clerk Maxwell': 'ジェームズ・クラーク・マクスウェル',
            'Max Planck': 'マックス・プランク',
            'Niels Bohr': 'ニールス・ボーア',
            'Werner Heisenberg': 'ヴェルナー・ハイゼンベルク',
            'Erwin Schrödinger': 'エルヴィン・シュレーディンガー',
            'Stephen Hawking': 'スティーヴン・ホーキング',
            
            # 哲学者・思想家
            'René Descartes': 'ルネ・デカルト',
            'Immanuel Kant': 'イマヌエル・カント',
            'Georg Wilhelm Friedrich Hegel': 'ゲオルク・ヴィルヘルム・フリードリヒ・ヘーゲル',
            'Friedrich Nietzsche': 'フリードリヒ・ニーチェ',
            'Arthur Schopenhauer': 'アルトゥル・ショーペンハウアー',
            'Jean-Jacques Rousseau': 'ジャン＝ジャック・ルソー',
            'Voltaire': 'ヴォルテール',
            'John Locke': 'ジョン・ロック',
            'David Hume': 'デイヴィッド・ヒューム',
            'Baruch Spinoza': 'バルーフ・スピノザ',
            'Karl Marx': 'カール・マルクス',
            'Sigmund Freud': 'ジークムント・フロイト',
            'Carl Jung': 'カール・ユング',
            
            # 作家・詩人
            'William Shakespeare': 'ウィリアム・シェイクスピア',
            'Johann Wolfgang von Goethe': 'ヨハン・ヴォルフガング・フォン・ゲーテ',
            'Dante Alighieri': 'ダンテ・アリギエーリ',
            'Miguel de Cervantes': 'ミゲル・デ・セルバンテス',
            'Victor Hugo': 'ヴィクトル・ユーゴー',
            'Leo Tolstoy': 'レフ・トルストイ',
            'Fyodor Dostoevsky': 'フョードル・ドストエフスキー',
            'Charles Dickens': 'チャールズ・ディケンズ',
            'Mark Twain': 'マーク・トウェイン',
            'Oscar Wilde': 'オスカー・ワイルド',
            'Edgar Allan Poe': 'エドガー・アラン・ポー',
            'Ernest Hemingway': 'アーネスト・ヘミングウェイ',
            'George Orwell': 'ジョージ・オーウェル',
            'Franz Kafka': 'フランツ・カフカ',
            
            # 画家・芸術家
            'Leonardo da Vinci': 'レオナルド・ダ・ヴィンチ',
            'Michelangelo': 'ミケランジェロ',
            'Raphael': 'ラファエロ',
            'Rembrandt': 'レンブラント',
            'Vincent van Gogh': 'フィンセント・ファン・ゴッホ',
            'Pablo Picasso': 'パブロ・ピカソ',
            'Claude Monet': 'クロード・モネ',
            'Pierre-Auguste Renoir': 'ピエール＝オーギュスト・ルノワール',
            'Salvador Dalí': 'サルバドール・ダリ',
            'Andy Warhol': 'アンディ・ウォーホル',
            
            # 現代の有名人（音楽）
            'The Beatles': 'ザ・ビートルズ',
            'John Lennon': 'ジョン・レノン',
            'Paul McCartney': 'ポール・マッカートニー',
            'George Harrison': 'ジョージ・ハリスン',
            'Ringo Starr': 'リンゴ・スター',
            'Elvis Presley': 'エルヴィス・プレスリー',
            'Michael Jackson': 'マイケル・ジャクソン',
            'Madonna': 'マドンナ',
            'Bob Dylan': 'ボブ・ディラン',
            'David Bowie': 'デヴィッド・ボウイ',
            'Freddie Mercury': 'フレディ・マーキュリー',
            'Prince': 'プリンス',
            
            # 映画俳優・監督
            'Charlie Chaplin': 'チャーリー・チャップリン',
            'Marilyn Monroe': 'マリリン・モンロー',
            'Audrey Hepburn': 'オードリー・ヘプバーン',
            'James Dean': 'ジェームズ・ディーン',
            'Alfred Hitchcock': 'アルフレッド・ヒッチコック',
            'Stanley Kubrick': 'スタンリー・キューブリック',
            'Steven Spielberg': 'スティーヴン・スピルバーグ',
            'Martin Scorsese': 'マーティン・スコセッシ',
            'Quentin Tarantino': 'クエンティン・タランティーノ',
            
            # 日本の歴史人物（ローマ字表記）
            'Oda Nobunaga': '織田信長',
            'Toyotomi Hideyoshi': '豊臣秀吉',
            'Tokugawa Ieyasu': '徳川家康',
            'Minamoto no Yoritomo': '源頼朝',
            'Taira no Kiyomori': '平清盛',
            'Fujiwara no Michinaga': '藤原道長',
            'Sakamoto Ryoma': '坂本龍馬',
            'Saigo Takamori': '西郷隆盛',
            'Okubo Toshimichi': '大久保利通',
            
            # 単名の有名人
            'Plato': 'プラトン',
            'Aristotle': 'アリストテレス',
            'Homer': 'ホメロス',
            'Virgil': 'ウェルギリウス',
            'Ovid': 'オウィディウス',
            'Confucius': '孔子',
            'Laozi': '老子',
            'Buddha': 'ブッダ',
            'Jesus': 'イエス',
            'Muhammad': 'ムハンマド',
            'Moses': 'モーセ',
            
            # 頻出する名前の部分
            'Saint': '聖',
            'Pope': '教皇',
            'King': '王',
            'Queen': '女王',
            'Prince': '王子',
            'Princess': '王女',
            'Duke': '公爵',
            'Count': '伯爵',
            'Baron': '男爵',
            'Lord': '卿',
            'Sir': 'サー',
            'Emperor': '皇帝',
            'Empress': '皇后',
        }
    
    def translate_name(self, name: str) -> Optional[str]:
        """名前を辞書で翻訳"""
        
        # 完全一致を探す
        if name in self.dictionary:
            self.stats['translated'] += 1
            return self.dictionary[name]
        
        # 部分一致を探す（姓名の順序を考慮）
        for eng_name, jp_name in self.dictionary.items():
            if eng_name.lower() == name.lower():
                self.stats['translated'] += 1
                return jp_name
        
        # 名前の一部が辞書にある場合
        parts = name.split()
        translated_parts = []
        found_translation = False
        
        for part in parts:
            if part in self.dictionary:
                translated_parts.append(self.dictionary[part])
                found_translation = True
            else:
                # 部分文字列として探す
                for key, value in self.dictionary.items():
                    if key in part or part in key:
                        translated_parts.append(value)
                        found_translation = True
                        break
                else:
                    translated_parts.append(part)
        
        if found_translation:
            self.stats['translated'] += 1
            return '・'.join(translated_parts)
        
        self.stats['not_found'] += 1
        return None
    
    def translate_database(self, input_file: str = None) -> Tuple[str, Dict]:
        """データベース全体を辞書翻訳"""
        
        # 入力ファイル決定（前段階の出力を優先）
        if not input_file:
            from pathlib import Path
            phonetic_files = list(Path('.').glob('phonetic_converted_*.json'))
            if phonetic_files:
                input_file = str(sorted(phonetic_files)[-1])
            else:
                wikipedia_files = list(Path('.').glob('wikipedia_translated_*.json'))
                if wikipedia_files:
                    input_file = str(sorted(wikipedia_files)[-1])
                else:
                    input_file = 'perfect_database_20250824_172451.json'
        
        print("📚 カスタム辞書翻訳開始")
        print(f"  入力: {input_file}")
        print(f"  辞書サイズ: {len(self.dictionary)}項目")
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        # 翻訳処理
        translated_count = 0
        for key, value in all_data.items():
            if isinstance(value, dict):
                name = value.get('name', '')
                
                # 英語名の場合のみ処理
                if name and not any(ord(c) > 0x3000 for c in name):
                    self.stats['processed'] += 1
                    
                    # キャッシュチェック
                    cache_key = f"dict_{name}"
                    if cache_key in self.translation_cache:
                        value['original_name'] = name
                        value['name'] = self.translation_cache[cache_key]
                        self.stats['cached'] += 1
                        translated_count += 1
                        continue
                    
                    # 辞書翻訳
                    japanese_name = self.translate_name(name)
                    if japanese_name:
                        value['original_name'] = name
                        value['name'] = japanese_name
                        self.translation_cache[cache_key] = japanese_name
                        translated_count += 1
                        
                        if translated_count <= 10:
                            print(f"  ✓ {name} → {japanese_name}")
        
        # キャッシュ保存
        self.save_cache()
        
        # 出力ファイル保存
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"dictionary_translated_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        print("\n📊 辞書翻訳結果:")
        print(f"  処理: {self.stats['processed']}件")
        print(f"  翻訳成功: {self.stats['translated']}件")
        print(f"  キャッシュ使用: {self.stats['cached']}件")
        print(f"  辞書にない: {self.stats['not_found']}件")
        print(f"  出力: {output_file}")
        
        return output_file, self.stats


def main():
    """メイン実行"""
    dictionary = CustomTranslationDictionary()
    
    # カスタム辞書翻訳実行
    output_file, stats = dictionary.translate_database()
    
    # 成功率計算
    if stats['processed'] > 0:
        success_rate = stats['translated'] / stats['processed'] * 100
        print(f"\n🎯 翻訳成功率: {success_rate:.1f}%")


if __name__ == "__main__":
    main()