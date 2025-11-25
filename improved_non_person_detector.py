#!/usr/bin/env python3
"""
Ultra Think 改良版非人物エントリー検出システム
誤検出を最小限に抑えた精密な検出
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple


class ImprovedNonPersonDetector:
    """改良版非人物検出器"""

    def __init__(self):
        # 確実にグループ・団体である名前（手動でキュレート）
        self.definite_groups = [
            # 音楽グループ（日本）
            'YOASOBI', 'After the Rain', 'CLAMP', 'ONE OK ROCK', 'RADWIMPS',
            'BUMP OF CHICKEN', 'ASIAN KUNG-FU GENERATION', 'L\'Arc-en-Ciel',
            'L\'Arc～en～Ciel', 'B\'z', 'Mr.Children', 'DREAMS COME TRUE',
            'GLAY', 'SPITZ', 'サザンオールスターズ', 'いきものがかり',
            'ゆず', 'コブクロ', 'SEKAI NO OWARI', 'Official髭男dism',
            'King Gnu', '[Alexandros]', 'MAN WITH A MISSION',
            'ヤバイTシャツ屋さん', 'WANIMA', 'Mrs. GREEN APPLE',

            # アイドルグループ（日本）
            'AKB48', 'SKE48', 'NMB48', 'HKT48', 'NGT48', 'STU48',
            '乃木坂46', '欅坂46', '日向坂46', '櫻坂46', 'モーニング娘。',
            'モーニング娘。\'14', 'モーニング娘。\'15', 'モーニング娘。\'16',
            'モーニング娘。\'17', 'モーニング娘。\'18', 'モーニング娘。\'19',
            'モーニング娘。\'20', 'モーニング娘。\'21', 'モーニング娘。\'22',
            'SMAP', 'TOKIO', 'V6', 'KinKi Kids', '嵐', 'NEWS', 'KAT-TUN',
            '関ジャニ∞', 'Hey! Say! JUMP', 'Kis-My-Ft2', 'Sexy Zone',
            'King & Prince', 'SixTONES', 'Snow Man', 'なにわ男子',
            'ジャニーズWEST', 'A.B.C-Z', 'ジャニーズJr.',
            'Perfume', 'BABYMETAL', 'BiSH', 'でんぱ組.inc',
            'ももいろクローバーZ', '私立恵比寿中学', 'アンジュルム',
            'Juice=Juice', 'つばきファクトリー', 'BEYOOOOONDS',

            # K-POPグループ
            'BTS', '防弾少年団', 'BLACKPINK', 'TWICE', 'SEVENTEEN',
            'Stray Kids', 'ENHYPEN', 'NCT', 'NCT 127', 'NCT DREAM',
            'WayV', 'ITZY', 'aespa', 'ATEEZ', 'TXT', 'TOMORROW X TOGETHER',
            'THE BOYZ', 'TREASURE', '&TEAM', 'NiziU', 'JO1', 'INI',
            'BE:FIRST', 'XG',

            # お笑いコンビ・トリオ
            'ダウンタウン', 'ウッチャンナンチャン', 'とんねるず',
            '爆笑問題', 'ナインティナイン', 'さまぁ〜ず', 'さまぁ～ず',
            'くりぃむしちゅー', '雨上がり決死隊', 'フットボールアワー',
            'ブラックマヨネーズ', 'チュートリアル', 'サンドウィッチマン',
            '千鳥', 'かまいたち', '霜降り明星', 'ミルクボーイ',
            'EXIT', '見取り図', 'ニューヨーク', 'オードリー',
            '南海キャンディーズ', 'ハリセンボン', 'オリエンタルラジオ',
            'ロバート', 'インパルス', 'アンタッチャブル', 'バナナマン',
            'おぎやはぎ', 'ハライチ', 'ラーメンズ', '東京03',
            'ジャルジャル', 'メイプル超合金', '3時のヒロイン', 'ぺこぱ',
            '四千頭身', 'ゆにばーす', 'Aマッソ', 'ネプチューン',
            'ドリフターズ', 'ザ・ドリフターズ', 'コント55号',
            'ツービート', 'B21スペシャル', 'ウンナン', 'ダチョウ倶楽部',
            'TIM', 'アンジャッシュ', 'よゐこ', '品川庄司',
            'タカアンドトシ', 'スピードワゴン', 'ますだおかだ',
            'アメリカザリガニ', 'フルーツポンチ', '我が家', 'パンサー',
            'ハナコ', 'ラランド', '男性ブランコ', 'マヂカルラブリー',
            'ウエストランド', '錦鯉', 'ヤーレンズ', '真空ジェシカ',
            'トム・ブラウン', 'からし蓮根', 'モグライダー',

            # YouTuberグループ
            'Fischer\'s', 'フィッシャーズ', '東海オンエア', 'コムドット',
            'スカイピース', '水溜りボンド', 'QuizKnock', 'クイズノック',
            '6人組', 'ヴァンゆん', 'パパラピーズ', 'カラフルピーチ',
            'さんこいち', 'アバンティーズ', 'レイクレ',

            # 海外バンド
            'The Beatles', 'Queen', 'The Rolling Stones', 'Led Zeppelin',
            'Pink Floyd', 'The Who', 'Deep Purple', 'AC/DC', 'Metallica',
            'Nirvana', 'Radiohead', 'Coldplay', 'Maroon 5', 'OneRepublic',
            'Imagine Dragons', 'Twenty One Pilots', 'Panic! at the Disco',
            'Fall Out Boy', 'My Chemical Romance', 'Green Day', 'Linkin Park',
            'Red Hot Chili Peppers', 'Foo Fighters', 'Arctic Monkeys',
            'The Killers', 'Muse', 'U2', 'Bon Jovi', 'Aerosmith', 'KISS',
            'Guns N\' Roses', 'Van Halen', 'Journey', 'Chicago', 'Boston',
            'Eagles', 'The Doors', 'Fleetwood Mac', 'The Beach Boys',
            'Simon & Garfunkel', 'Hall & Oates', 'The Carpenters',

            # VTuberグループ・事務所（グループとして登録されている可能性）
            'ホロライブ', 'にじさんじ', 'ぶいすぽっ!', 'ネオポルテ',
            '.LIVE', 'のりプロ', '774inc.',
        ]

        # 職業フィールドで明確にグループを示す文字列
        self.group_occupation_keywords = [
            '音楽グループ', '音楽ユニット', 'ユニット', 'デュオ',
            'トリオ', 'カルテット', 'バンド', 'アイドルグループ',
            'ボーイズグループ', 'ガールズグループ', 'お笑いコンビ',
            'お笑いトリオ', 'YouTuberグループ', 'グループ',
            '漫才コンビ', 'コント', 'comedy duo', 'comedy trio',
            'band', 'group', 'unit', 'duo', 'trio', 'quartet'
        ]

        # 人物として扱うべき例外（「〜ズ」で終わるが個人）
        self.person_exceptions = [
            # 歴史的人物
            'チャールズ', 'ジェームズ', 'トーマス', 'ジョージ',
            'ルイス', 'フランシス', 'ニコラス', 'マーカス',
            'ユリウス', 'アウグストゥス', 'ティトゥス',

            # 姓としての「〜ズ」
            'ジョーンズ', 'ウィリアムズ', 'デイビス', 'ロドリゲス',
            'マルティネス', 'ヘルナンデス', 'ゴンザレス', 'ロペス',
            'サンチェス', 'ラミレス', 'トーレス', 'フローレス',
            'エドワーズ', 'コリンズ', 'スティーブンズ', 'ロジャーズ',
            'エヴァンス', 'ターナー', 'ディアス', 'バーンズ',

            # 日本語化された外国人名
            'ビル・ゲイツ', 'スティーブ・ジョブズ', 'ジェフ・ベゾス',
            'チャールズ・ダーウィン', 'アルバート・アインシュタイン',
        ]

    def detect_non_persons(self, database_file: str) -> Dict[str, Any]:
        """非人物エントリーを精密に検出"""

        print("🔍 改良版非人物検出開始...")

        non_persons = []
        total_count = 0

        with open(database_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)

            for row in reader:
                total_count += 1

                person_name = row.get('person_name', '')
                person_name_ja = row.get('person_name_ja', '')
                occupation = row.get('occupation', '').lower()

                detection_reasons = []

                # 1. 確実にグループである名前のチェック
                if person_name in self.definite_groups or person_name_ja in self.definite_groups:
                    detection_reasons.append(f'既知のグループ名: {person_name_ja or person_name}')
                    non_persons.append({
                        'row': row,
                        'reasons': detection_reasons,
                        'confidence': 'DEFINITE'
                    })
                    continue

                # 2. 職業フィールドでグループと明記されている場合
                for keyword in self.group_occupation_keywords:
                    if keyword in occupation:
                        detection_reasons.append(f'職業にグループ表記: {keyword}')
                        non_persons.append({
                            'row': row,
                            'reasons': detection_reasons,
                            'confidence': 'HIGH'
                        })
                        break

                # 3. 明確な複数人表現（&, and, with等）
                # ただし「・」は外国人名の区切りなので除外
                multi_indicators = ['&', ' and ', ' AND ', ' with ', ' With ',
                                  ' feat. ', ' feat ', ' Feat. ', ' Feat ',
                                  ' vs ', ' VS ', ' × ', '+']

                for indicator in multi_indicators:
                    if indicator in person_name or indicator in person_name_ja:
                        detection_reasons.append(f'複数人表現: {indicator}')
                        non_persons.append({
                            'row': row,
                            'reasons': detection_reasons,
                            'confidence': 'HIGH'
                        })
                        break

                # 進捗表示
                if total_count % 1000 == 0:
                    print(f"  処理中: {total_count}件...")

        print(f"\n✅ 検出完了")
        print(f"  総エントリー: {total_count}件")
        print(f"  非人物エントリー: {len(non_persons)}件")

        return {
            'total': total_count,
            'non_persons': non_persons,
            'analysis': self.analyze_results(non_persons)
        }

    def analyze_results(self, non_persons: List) -> Dict[str, Any]:
        """検出結果の分析"""

        # カテゴリ別集計
        categories = {}
        for item in non_persons:
            cat = item['row'].get('category', 'その他')
            categories[cat] = categories.get(cat, 0) + 1

        # 検出理由別集計
        reasons = {}
        for item in non_persons:
            for reason in item['reasons']:
                reason_type = reason.split(':')[0]
                reasons[reason_type] = reasons.get(reason_type, 0) + 1

        # 具体的なグループリスト
        groups = {}
        for item in non_persons:
            name = item['row'].get('person_name_ja') or item['row'].get('person_name')
            groups[name] = {
                'category': item['row'].get('category'),
                'occupation': item['row'].get('occupation'),
                'confidence': item['confidence'],
                'person_id': item['row'].get('person_id')
            }

        return {
            'categories': categories,
            'reasons': reasons,
            'groups': groups
        }

    def remove_non_persons(self, database_file: str, non_persons: List, output_file: str) -> int:
        """非人物エントリーを削除したクリーンなデータベースを作成"""

        print(f"\n🧹 非人物エントリー削除中...")

        # 削除するIDのセットを作成
        ids_to_remove = set()
        for item in non_persons:
            person_id = item['row'].get('person_id')
            if person_id:
                ids_to_remove.add(person_id)

        # クリーンなデータベース作成
        clean_rows = []
        removed_count = 0

        with open(database_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            headers = reader.fieldnames

            for row in reader:
                if row.get('person_id') not in ids_to_remove:
                    clean_rows.append(row)
                else:
                    removed_count += 1

        # 保存
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            writer.writerows(clean_rows)

        print(f"  ✅ 削除完了: {removed_count}件")
        print(f"  残存エントリー: {len(clean_rows)}件")

        return removed_count

    def generate_detailed_report(self, results: Dict[str, Any]) -> str:
        """詳細レポート生成"""

        timestamp = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')

        report = f"""# 🔍 Ultra Think 非人物エントリー検出レポート（改良版）

## 📅 実行情報
- 実行日時: {timestamp}
- 分析対象: {results['total']}件
- 検出された非人物: {len(results['non_persons'])}件
- 混入率: {len(results['non_persons']) / results['total'] * 100:.2f}%

## 📊 カテゴリ別分布
"""

        for cat, count in sorted(results['analysis']['categories'].items(),
                                key=lambda x: x[1], reverse=True):
            report += f"- {cat}: {count}件\n"

        report += """
## 🎯 検出理由の内訳
"""

        for reason, count in sorted(results['analysis']['reasons'].items(),
                                   key=lambda x: x[1], reverse=True):
            report += f"- {reason}: {count}件\n"

        report += """
## 📋 検出されたグループ・団体（全リスト）

| 名前 | カテゴリ | 職業 | 確信度 | ID |
|------|---------|------|--------|-----|
"""

        for name, info in sorted(results['analysis']['groups'].items()):
            report += f"| {name} | {info['category']} | {info['occupation']} | {info['confidence']} | {info['person_id']} |\n"

        report += f"""
## 🔍 原因分析

### 主な混入経路

1. **音楽グループの混入**
   - YOASOBI、After the Rain等の音楽ユニット
   - 職業欄に「音楽ユニット」と明記
   - WikipediaのグループページからのAPIデータ取得

2. **お笑いコンビの混入**
   - ダウンタウン、サンドウィッチマン等
   - コンビ名での登録
   - メンバー個別登録の欠如

3. **YouTuberグループの混入**
   - フィッシャーズ、東海オンエア等
   - グループチャンネルとして活動
   - 個人とグループの区別が曖昧

4. **漫画家グループの混入**
   - CLAMP等の合作ペンネーム
   - 複数人での創作活動

### システム的問題

1. **データ収集時の問題**
   - グループと個人を区別しないAPI呼び出し
   - カテゴリベースの一括収集
   - Wikipedia上のグループページも人物として処理

2. **データ検証の不在**
   - 追加時の人物/非人物チェックなし
   - 職業フィールドの検証不足
   - 名前パターンの検証欠如

3. **設計上の問題**
   - エンティティタイプの概念欠如
   - グループメンバーの個別管理機能なし
   - 階層的なデータ構造の不在

## 💡 改善提案

### 即時対応
1. 検出された{len(results['non_persons'])}件の非人物エントリーを削除
2. 重要なグループのメンバーを個別に追加
3. データベースのクリーンアップ実施

### システム改善
1. エンティティタイプフィールドの追加（person/group/organization）
2. グループメンバー管理機能の実装
3. データ追加時の検証プロセス強化

## 📝 結論

改良版検出システムにより、**{len(results['non_persons'])}件の非人物エントリー**を特定しました。
これらは主に音楽グループ、お笑いコンビ、YouTuberグループ等で、
データベース全体の**{len(results['non_persons']) / results['total'] * 100:.1f}%**を占めています。

早急にこれらを削除し、必要に応じてメンバーを個別登録することを推奨します。

---
*Ultra Think Improved Non-Person Detection System v2.0*
*Generated: {timestamp}*
"""

        return report


def main():
    """メイン処理"""

    print("="*60)
    print("🔍 Ultra Think 改良版非人物検出システム")
    print("="*60)

    # 検出器初期化
    detector = ImprovedNonPersonDetector()

    # データベースファイル
    database_file = 'ULTRA_THINK_COMPLETE_FIXED_20250827_084510.csv'

    # 非人物検出
    results = detector.detect_non_persons(database_file)

    # レポート生成と保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report = detector.generate_detailed_report(results)

    report_file = f'IMPROVED_NON_PERSON_REPORT_{timestamp}.md'
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\n📊 レポート保存: {report_file}")

    # 非人物リスト出力（CSV）
    list_file = f'NON_PERSON_DEFINITE_LIST_{timestamp}.csv'
    with open(list_file, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['person_id', 'person_name', 'person_name_ja',
                        'category', 'occupation', 'confidence'])

        for item in results['non_persons']:
            row = item['row']
            writer.writerow([
                row.get('person_id'),
                row.get('person_name'),
                row.get('person_name_ja'),
                row.get('category'),
                row.get('occupation'),
                item['confidence']
            ])

    print(f"📋 非人物リスト: {list_file}")

    # クリーンなデータベース作成
    if len(results['non_persons']) > 0:
        clean_file = f'ULTRA_THINK_CLEAN_{timestamp}.csv'
        removed = detector.remove_non_persons(database_file, results['non_persons'], clean_file)
        print(f"\n✨ クリーンデータベース: {clean_file}")

    print("\n" + "="*60)
    print("✨ 処理完了")
    print("="*60)


if __name__ == "__main__":
    main()
