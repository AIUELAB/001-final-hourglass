#!/usr/bin/env python3
"""
インテリジェント名前修正システム
芸名はローマ字を維持し、歴史的人物は適切な日本語表記を使用
"""

import json
import re
from datetime import datetime
from typing import Dict, Optional, Tuple


class IntelligentNameFixer:
    """名前の表示を賢く修正するシステム"""

    def __init__(self):
        # 歴史的人物の定訳辞書（主要なもの）
        self.historical_translations = self.build_historical_dictionary()

        # 芸名として維持すべきパターン
        self.stage_name_patterns = [
            'R-1', 'お笑い芸人', 'アイドル', 'タレント', '芸人',
            'YouTuber', 'インフルエンサー', 'DJ', 'MC'
        ]

        # 統計
        self.stats = {
            'total': 0,
            'stage_names': 0,
            'historical': 0,
            'translated': 0,
            'original_kept': 0
        }

    def build_historical_dictionary(self) -> Dict[str, str]:
        """歴史的人物の確立された日本語表記"""
        return {
            # 作曲家
            'Bach': 'バッハ',
            'Johann Sebastian Bach': 'ヨハン・セバスティアン・バッハ',
            'Johann Christoph Bach': 'ヨハン・クリストフ・バッハ',
            'Mozart': 'モーツァルト',
            'Wolfgang Amadeus Mozart': 'ヴォルフガング・アマデウス・モーツァルト',
            'Beethoven': 'ベートーヴェン',
            'Ludwig van Beethoven': 'ルートヴィヒ・ヴァン・ベートーヴェン',
            'Wagner': 'ワーグナー',
            'Richard Wagner': 'リヒャルト・ワーグナー',
            'Brahms': 'ブラームス',
            'Johannes Brahms': 'ヨハネス・ブラームス',
            'Schubert': 'シューベルト',
            'Franz Schubert': 'フランツ・シューベルト',
            'Chopin': 'ショパン',
            'Liszt': 'リスト',
            'Franz Liszt': 'フランツ・リスト',
            'Verdi': 'ヴェルディ',
            'Giuseppe Verdi': 'ジュゼッペ・ヴェルディ',
            'Vivaldi': 'ヴィヴァルディ',
            'Antonio Vivaldi': 'アントニオ・ヴィヴァルディ',
            'Handel': 'ヘンデル',
            'Tchaikovsky': 'チャイコフスキー',
            'Debussy': 'ドビュッシー',
            'Claude Debussy': 'クロード・ドビュッシー',
            'Ravel': 'ラヴェル',
            'Maurice Ravel': 'モーリス・ラヴェル',
            'Stravinsky': 'ストラヴィンスキー',

            # 科学者
            'Einstein': 'アインシュタイン',
            'Albert Einstein': 'アルベルト・アインシュタイン',
            'Newton': 'ニュートン',
            'Isaac Newton': 'アイザック・ニュートン',
            'Darwin': 'ダーウィン',
            'Charles Darwin': 'チャールズ・ダーウィン',
            'Galileo': 'ガリレオ',
            'Galileo Galilei': 'ガリレオ・ガリレイ',
            'Copernicus': 'コペルニクス',
            'Kepler': 'ケプラー',
            'Faraday': 'ファラデー',
            'Maxwell': 'マクスウェル',
            'Planck': 'プランク',
            'Bohr': 'ボーア',
            'Heisenberg': 'ハイゼンベルク',
            'Schrödinger': 'シュレーディンガー',

            # 哲学者
            'Plato': 'プラトン',
            'Aristotle': 'アリストテレス',
            'Socrates': 'ソクラテス',
            'Descartes': 'デカルト',
            'Kant': 'カント',
            'Hegel': 'ヘーゲル',
            'Nietzsche': 'ニーチェ',
            'Schopenhauer': 'ショーペンハウアー',
            'Rousseau': 'ルソー',
            'Voltaire': 'ヴォルテール',
            'Locke': 'ロック',
            'Hume': 'ヒューム',
            'Spinoza': 'スピノザ',
            'Marx': 'マルクス',
            'Freud': 'フロイト',
            'Jung': 'ユング',

            # 作家・詩人
            'Shakespeare': 'シェイクスピア',
            'Goethe': 'ゲーテ',
            'Dante': 'ダンテ',
            'Cervantes': 'セルバンテス',
            'Hugo': 'ユーゴー',
            'Tolstoy': 'トルストイ',
            'Dostoevsky': 'ドストエフスキー',
            'Dickens': 'ディケンズ',
            'Twain': 'トウェイン',
            'Wilde': 'ワイルド',
            'Poe': 'ポー',
            'Hemingway': 'ヘミングウェイ',
            'Orwell': 'オーウェル',
            'Kafka': 'カフカ',

            # 画家・芸術家
            'Leonardo': 'レオナルド',
            'Leonardo da Vinci': 'レオナルド・ダ・ヴィンチ',
            'Michelangelo': 'ミケランジェロ',
            'Raphael': 'ラファエロ',
            'Rembrandt': 'レンブラント',
            'Van Gogh': 'ゴッホ',
            'Vincent van Gogh': 'フィンセント・ファン・ゴッホ',
            'Picasso': 'ピカソ',
            'Pablo Picasso': 'パブロ・ピカソ',
            'Monet': 'モネ',
            'Renoir': 'ルノワール',
            'Dalí': 'ダリ',
            'Warhol': 'ウォーホル',

            # 音楽家（現代）
            'Beatles': 'ビートルズ',
            'Lennon': 'レノン',
            'John Lennon': 'ジョン・レノン',
            'McCartney': 'マッカートニー',
            'Harrison': 'ハリスン',
            'Presley': 'プレスリー',
            'Elvis Presley': 'エルヴィス・プレスリー',
            'Jackson': 'ジャクソン',
            'Michael Jackson': 'マイケル・ジャクソン',
            'Madonna': 'マドンナ',
            'Dylan': 'ディラン',
            'Bob Dylan': 'ボブ・ディラン',
            'Bowie': 'ボウイ',
            'Mercury': 'マーキュリー',

            # 映画関係
            'Chaplin': 'チャップリン',
            'Charlie Chaplin': 'チャーリー・チャップリン',
            'Monroe': 'モンロー',
            'Marilyn Monroe': 'マリリン・モンロー',
            'Hepburn': 'ヘプバーン',
            'Audrey Hepburn': 'オードリー・ヘプバーン',
            'Dean': 'ディーン',
            'James Dean': 'ジェームズ・ディーン',
            'Hitchcock': 'ヒッチコック',
            'Kubrick': 'キューブリック',
            'Spielberg': 'スピルバーグ',
            'Scorsese': 'スコセッシ',
            'Tarantino': 'タランティーノ',

            # 古代ローマ
            'Caesar': 'カエサル',
            'Julius Caesar': 'ユリウス・カエサル',
            'Augustus': 'アウグストゥス',
            'Marcus Aurelius': 'マルクス・アウレリウス',
            'Nero': 'ネロ',
            'Cicero': 'キケロ',
            'Seneca': 'セネカ',

            # 君主・政治家
            'Napoleon': 'ナポレオン',
            'Napoleon Bonaparte': 'ナポレオン・ボナパルト',
            'Alexander': 'アレクサンドロス',
            'Alexander the Great': 'アレクサンドロス大王',
            'Charlemagne': 'カール大帝',
            'Peter the Great': 'ピョートル大帝',
            'Catherine the Great': 'エカテリーナ2世',
            'Elizabeth I': 'エリザベス1世',
            'Louis XIV': 'ルイ14世',
        }

    def determine_name_type(self, person: Dict) -> str:
        """名前のタイプを判定"""
        occupation = person.get('occupation', '')
        nationality = person.get('nationality', '')
        display_name = person.get('display_name', '')

        # 芸名パターンチェック
        for pattern in self.stage_name_patterns:
            if pattern in str(occupation):
                return 'stage_name'

        # 日本のエンターテイメント関係
        if any(word in str(occupation) for word in ['俳優', '女優', '歌手', '声優']):
            # 日本人っぽい場合は芸名の可能性
            if not nationality or 'Japan' in str(nationality) or '日本' in str(nationality):
                # 全角文字を含まない = ローマ字芸名の可能性
                if display_name and not any(ord(c) > 0x3000 for c in display_name):
                    return 'stage_name'

        # 歴史的人物
        if any(word in str(occupation) for word in ['composer', 'scientist', 'philosopher', 'Ancient']):
            return 'historical'

        # 古代人
        if 'Ancient' in str(nationality):
            return 'historical'

        return 'translated'

    def get_preferred_display_name(self, person: Dict) -> Tuple[str, str]:
        """最適な表示名を決定"""
        name = person.get('name', '')
        display_name = person.get('display_name', '')
        original_name = person.get('original_name', '')

        # 名前タイプを判定
        name_type = self.determine_name_type(person)

        if name_type == 'stage_name':
            # 芸名はオリジナルを維持
            self.stats['stage_names'] += 1
            if display_name and not any(ord(c) > 0x3000 for c in display_name):
                return display_name, name_type
            elif original_name:
                return original_name, name_type
            else:
                return name, name_type

        elif name_type == 'historical':
            # 歴史的人物は定訳を探す
            self.stats['historical'] += 1

            # display_nameで辞書を検索
            if display_name:
                # 完全一致
                if display_name in self.historical_translations:
                    return self.historical_translations[display_name], name_type

                # 部分一致（姓のみ等）
                for eng_name, jp_name in self.historical_translations.items():
                    if eng_name in display_name or display_name in eng_name:
                        return jp_name, name_type

            # 見つからない場合は翻訳済みの名前を使用
            if any(ord(c) > 0x3000 for c in name):
                return name, name_type

        # デフォルトは翻訳済み名を使用
        self.stats['translated'] += 1
        if any(ord(c) > 0x3000 for c in name):
            return name, 'translated'
        else:
            return display_name or name, 'translated'

    def fix_database(self, input_file: str = None) -> Tuple[str, Dict]:
        """データベース全体を修正"""

        if not input_file:
            input_file = 'batch_perfect_translated_20250824_174356.json'

        print("🔧 インテリジェント名前修正開始")
        print(f"  入力: {input_file}")

        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self.stats['total'] = len(data)

        # 各レコードを処理
        fixed_count = 0
        examples = []

        for key, value in data.items():
            if isinstance(value, dict):
                # 最適な表示名を決定
                preferred_name, name_type = self.get_preferred_display_name(value)

                # 新フィールドを追加
                value['name_display_type'] = name_type
                value['preferred_display_name'] = preferred_name

                # サンプル収集
                if len(examples) < 20 and name_type in ['stage_name', 'historical']:
                    examples.append({
                        'original': value.get('display_name', ''),
                        'preferred': preferred_name,
                        'type': name_type,
                        'occupation': value.get('occupation', '')
                    })

                fixed_count += 1

        # 結果保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"intelligent_fixed_{timestamp}.json"

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # レポート出力
        print("\n📊 修正結果:")
        print(f"  総レコード: {self.stats['total']:,}")
        print(f"  芸名（ローマ字維持）: {self.stats['stage_names']:,}")
        print(f"  歴史的人物（定訳使用）: {self.stats['historical']:,}")
        print(f"  翻訳済み: {self.stats['translated']:,}")

        if examples:
            print("\n📝 修正例:")
            for ex in examples[:10]:
                print(f"  {ex['original']:20} → {ex['preferred']:20} ({ex['type']})")

        print(f"\n✅ 出力: {output_file}")

        return output_file, self.stats


def main():
    """メイン実行"""
    fixer = IntelligentNameFixer()
    output_file, stats = fixer.fix_database()

    print("\n🎯 処理完了")
    print("  最適な表示名が設定されました")
    print("  TAIGAのような芸名: ローマ字維持")
    print("  Beethovenのような歴史的人物: 定訳使用")


if __name__ == "__main__":
    main()
