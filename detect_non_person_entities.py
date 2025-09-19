#!/usr/bin/env python3
"""
Ultra Think 非人物エントリー検出・分析システム
グループ、団体、バンド、ユニット等を徹底的に検出
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, List, Any, Tuple


class NonPersonEntityDetector:
    """非人物エントリーの検出と分析"""
    
    def __init__(self):
        # グループ・団体を示すパターン
        self.group_patterns = [
            # 日本語パターン
            r'.*団$',  # 〜団
            r'.*隊$',  # 〜隊
            r'.*組$',  # 〜組
            r'.*会$',  # 〜会
            r'.*軍$',  # 〜軍
            r'.*ズ$',  # 〜ズ
            r'.*ーズ$',  # 〜ーズ
            r'.*s$',  # 英語複数形
            r'.*S$',  # 英語複数形大文字
            
            # カタカナグループ名パターン
            r'.*バンド$',
            r'.*ユニット$',
            r'.*クラブ$',
            r'.*チーム$',
            r'.*グループ$',
            r'.*オーケストラ$',
            r'.*アンサンブル$',
            r'.*カルテット$',
            r'.*トリオ$',
            r'.*デュオ$',
            
            # 英語パターン
            r'The .*',  # The で始まる
            r'.* Band$',
            r'.* Group$',
            r'.* Team$',
            r'.* Club$',
            r'.* Orchestra$',
            r'.* Ensemble$',
            r'.* Brothers$',
            r'.* Sisters$',
        ]
        
        # 明確にグループ・団体であることが分かっている名前
        self.known_groups = [
            # 音楽グループ
            'YOASOBI', 'After the Rain', 'CLAMP', 'ONE OK ROCK', 'RADWIMPS',
            'BUMP OF CHICKEN', 'ASIAN KUNG-FU GENERATION', 'L\'Arc-en-Ciel',
            'B\'z', 'Mr.Children', 'DREAMS COME TRUE', 'GLAY', 'SPITZ',
            'サザンオールスターズ', 'いきものがかり', 'ゆず', 'コブクロ',
            'EXILE', 'AAA', 'AKB48', 'SKE48', 'NMB48', 'HKT48', 'NGT48',
            '乃木坂46', '欅坂46', '日向坂46', '櫻坂46', 'モーニング娘。',
            'SMAP', 'TOKIO', 'V6', 'KinKi Kids', '嵐', 'NEWS', 'KAT-TUN',
            '関ジャニ∞', 'Hey! Say! JUMP', 'Kis-My-Ft2', 'Sexy Zone',
            'King & Prince', 'SixTONES', 'Snow Man', 'なにわ男子',
            'TWICE', 'BLACKPINK', 'BTS', '防弾少年団', 'SEVENTEEN',
            'Stray Kids', 'ENHYPEN', 'NCT', 'ITZY', 'aespa',
            'The Beatles', 'Queen', 'The Rolling Stones', 'Led Zeppelin',
            'Pink Floyd', 'The Who', 'Deep Purple', 'AC/DC', 'Metallica',
            'Nirvana', 'Radiohead', 'Coldplay', 'Maroon 5', 'OneRepublic',
            'Imagine Dragons', 'Twenty One Pilots', 'Panic! at the Disco',
            
            # お笑いコンビ・トリオ
            'ダウンタウン', 'ウッチャンナンチャン', 'とんねるず', '爆笑問題',
            'ナインティナイン', 'さまぁ〜ず', 'くりぃむしちゅー', '雨上がり決死隊',
            'フットボールアワー', 'ブラックマヨネーズ', 'チュートリアル',
            'サンドウィッチマン', '千鳥', 'かまいたち', '霜降り明星',
            'ミルクボーイ', 'EXIT', '見取り図', 'ニューヨーク',
            'オードリー', '南海キャンディーズ', 'ハリセンボン', 
            'オリエンタルラジオ', 'ロバート', 'インパルス', 'アンタッチャブル',
            'バナナマン', 'おぎやはぎ', 'ハライチ', 'ラーメンズ',
            '東京03', 'ジャルジャル', 'メイプル超合金', '3時のヒロイン',
            'ぺこぱ', '四千頭身', 'ゆにばーす', 'Aマッソ',
            'ネプチューン', 'ドリフターズ', 'ザ・ドリフターズ',
            
            # その他のグループ・団体
            'Fischer\'s', 'フィッシャーズ', '東海オンエア', 'コムドット',
            'スカイピース', '水溜りボンド', 'QuizKnock', 'クイズノック',
            
            # 企業・組織（誤って入っている可能性）
            'Nintendo', '任天堂', 'Sony', 'ソニー', 'Apple', 'Google',
            'Microsoft', 'Amazon', 'Facebook', 'Meta', 'Twitter', 'X',
            
            # アニメ・ゲームのグループ（架空）
            'μ\'s', 'Aqours', '虹ヶ咲学園スクールアイドル同好会', 'Liella!',
            '765プロ', '346プロ', '315プロ', 'ホロライブ', 'にじさんじ',
        ]
        
        # 職業フィールドでグループを示す可能性のある文字列
        self.group_occupations = [
            'バンド', 'ユニット', 'グループ', 'デュオ', 'トリオ',
            'カルテット', 'クインテット', 'アンサンブル', 'オーケストラ',
            'コンビ', 'トリオ', 'カルテット', '音楽グループ', '音楽ユニット',
            'アイドルグループ', 'ダンスグループ', 'ボーイズグループ',
            'ガールズグループ', 'お笑いコンビ', 'お笑いトリオ',
            'YouTuberグループ', 'クリエイターチーム'
        ]
        
        # 人物の可能性が高い例外パターン
        self.person_exceptions = [
            r'^DJ.*',  # DJ〜は個人の場合が多い
            r'^MC.*',  # MC〜は個人の場合が多い
            r'.*Jr\.$',  # 〜Jr.は個人
            r'.*三世$',  # 〜三世は個人
            r'.*二世$',  # 〜二世は個人
        ]
        
    def detect_non_person_entities(self, database_file: str) -> Dict[str, Any]:
        """データベースから非人物エントリーを検出"""
        
        print("🔍 非人物エントリー検出開始...")
        
        non_persons = []
        suspicious = []
        total_count = 0
        
        # CSVファイル読み込み
        with open(database_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                total_count += 1
                
                person_name = row.get('person_name', '')
                person_name_ja = row.get('person_name_ja', '')
                occupation = row.get('occupation', '')
                category = row.get('category', '')
                
                # 検出理由を記録
                detection_reasons = []
                
                # 1. 既知のグループ名チェック
                if person_name in self.known_groups or person_name_ja in self.known_groups:
                    detection_reasons.append('既知のグループ・団体名')
                    non_persons.append({
                        'row': row,
                        'reasons': detection_reasons,
                        'confidence': 'HIGH'
                    })
                    continue
                
                # 2. パターンマッチング
                is_group = False
                for pattern in self.group_patterns:
                    if re.match(pattern, person_name) or re.match(pattern, person_name_ja):
                        # 例外チェック
                        is_exception = False
                        for exception in self.person_exceptions:
                            if re.match(exception, person_name) or re.match(exception, person_name_ja):
                                is_exception = True
                                break
                        
                        if not is_exception:
                            detection_reasons.append(f'パターンマッチ: {pattern}')
                            is_group = True
                            break
                
                # 3. 職業フィールドチェック
                for group_occ in self.group_occupations:
                    if group_occ in occupation:
                        detection_reasons.append(f'職業にグループ関連語: {group_occ}')
                        is_group = True
                        break
                
                # 4. 複数人を示す表現チェック
                multi_person_indicators = [
                    '&', 'and', 'AND', 'feat.', 'Feat.', 'with', 'With',
                    '×', '・', '+', 'vs', 'VS', 'feat', 'Feat'
                ]
                for indicator in multi_person_indicators:
                    if indicator in person_name or indicator in person_name_ja:
                        detection_reasons.append(f'複数人を示す記号: {indicator}')
                        is_group = True
                        break
                
                # 5. 括弧内にメンバー名がある場合
                if '（' in person_name_ja and '）' in person_name_ja:
                    # 例：「田中太郎（グループ名）」の形式かチェック
                    if any(group in person_name_ja for group in self.known_groups):
                        # これは個人なので除外
                        pass
                    else:
                        # グループ名（メンバー）の可能性
                        if re.search(r'（[^）]+[、,][^）]+）', person_name_ja):
                            detection_reasons.append('括弧内に複数メンバー')
                            is_group = True
                
                # 結果の分類
                if is_group:
                    if len(detection_reasons) >= 2:
                        # 複数の理由がある場合は確信度高
                        non_persons.append({
                            'row': row,
                            'reasons': detection_reasons,
                            'confidence': 'HIGH'
                        })
                    else:
                        # 単一の理由の場合は疑い
                        suspicious.append({
                            'row': row,
                            'reasons': detection_reasons,
                            'confidence': 'MEDIUM'
                        })
                
                # 進捗表示
                if total_count % 1000 == 0:
                    print(f"  処理中: {total_count}件...")
        
        print(f"\n✅ 検出完了")
        print(f"  総エントリー: {total_count}件")
        print(f"  非人物（確実）: {len(non_persons)}件")
        print(f"  非人物（疑い）: {len(suspicious)}件")
        
        return {
            'total': total_count,
            'non_persons': non_persons,
            'suspicious': suspicious,
            'analysis': self.analyze_detection_results(non_persons, suspicious)
        }
    
    def analyze_detection_results(self, non_persons: List, suspicious: List) -> Dict[str, Any]:
        """検出結果の分析"""
        
        # カテゴリ別集計
        category_counts = {}
        for item in non_persons + suspicious:
            category = item['row'].get('category', 'その他')
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # 検出理由別集計
        reason_counts = {}
        for item in non_persons + suspicious:
            for reason in item['reasons']:
                reason_type = reason.split(':')[0]
                reason_counts[reason_type] = reason_counts.get(reason_type, 0) + 1
        
        # 職業別集計
        occupation_counts = {}
        for item in non_persons + suspicious:
            occupation = item['row'].get('occupation', '不明')
            occupation_counts[occupation] = occupation_counts.get(occupation, 0) + 1
        
        return {
            'category_distribution': category_counts,
            'detection_reasons': reason_counts,
            'occupation_distribution': dict(sorted(occupation_counts.items(), 
                                                  key=lambda x: x[1], reverse=True)[:20])
        }
    
    def generate_report(self, results: Dict[str, Any]) -> str:
        """詳細レポートの生成"""
        
        timestamp = datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')
        
        report = f"""# 🔍 Ultra Think 非人物エントリー検出レポート

## 📅 実行情報
- 実行日時: {timestamp}
- 分析対象: {results['total']}件

## 🚨 検出結果サマリー

### 数値統計
- **非人物エントリー（確実）**: {len(results['non_persons'])}件
- **非人物エントリー（疑い）**: {len(results['suspicious'])}件
- **合計問題エントリー**: {len(results['non_persons']) + len(results['suspicious'])}件
- **混入率**: {(len(results['non_persons']) + len(results['suspicious'])) / results['total'] * 100:.2f}%

## 📊 詳細分析

### 1. カテゴリ別分布
"""
        
        for category, count in sorted(results['analysis']['category_distribution'].items(), 
                                     key=lambda x: x[1], reverse=True):
            report += f"- {category}: {count}件\n"
        
        report += """
### 2. 検出理由の内訳
"""
        
        for reason, count in sorted(results['analysis']['detection_reasons'].items(), 
                                   key=lambda x: x[1], reverse=True):
            report += f"- {reason}: {count}件\n"
        
        report += """
### 3. 職業フィールド分析（上位20）
"""
        
        for occupation, count in list(results['analysis']['occupation_distribution'].items())[:20]:
            report += f"- {occupation}: {count}件\n"
        
        report += """
## 📋 具体例（確実な非人物）

### 音楽グループ・ユニット
"""
        
        music_groups = []
        for item in results['non_persons'][:50]:
            if item['row'].get('category') in ['エンタメ', '文化・芸術', 'その他']:
                name = item['row'].get('person_name_ja') or item['row'].get('person_name')
                occupation = item['row'].get('occupation', '不明')
                reasons = ', '.join(item['reasons'])
                music_groups.append(f"- **{name}** ({occupation}) - 理由: {reasons}")
        
        report += '\n'.join(music_groups[:10])
        
        report += """

### お笑いコンビ・トリオ
"""
        
        comedy_groups = []
        for item in results['non_persons']:
            if 'お笑い' in item['row'].get('occupation', ''):
                name = item['row'].get('person_name_ja') or item['row'].get('person_name')
                occupation = item['row'].get('occupation', '不明')
                comedy_groups.append(f"- **{name}** ({occupation})")
        
        report += '\n'.join(comedy_groups[:10])
        
        report += """

## 🔍 原因分析

### 根本原因

1. **データ収集時の設計問題**
   - Wikipedia APIがグループページも人物として収集
   - グループと個人を区別するロジックの欠如
   - カテゴリ「音楽家」に音楽グループが混入

2. **名前正規化の問題**
   - グループ名を人名として処理
   - メンバー名とグループ名の混在
   - 「○○（グループ名）」形式の誤解釈

3. **職業フィールドの曖昧さ**
   - 「音楽ユニット」「お笑いコンビ」等が職業として登録
   - グループ活動を個人の職業として記載

4. **検証プロセスの不在**
   - 追加時の人物/非人物チェックなし
   - バッチ処理での一括追加
   - 重複チェックはあるが種別チェックなし

### 技術的問題

1. **API制限による妥協**
   - 大量データ収集のため精度を犠牲に
   - カテゴリベースの一括収集
   - 詳細チェックのスキップ

2. **パフォーマンス優先の設計**
   - 高速処理のため検証を簡略化
   - バッチサイズ優先で品質チェック不足

## 💡 改善提案

### 即時対応
1. 検出された非人物エントリーの削除
2. グループメンバーを個人として再登録
3. 職業フィールドの正規化

### システム改善
1. **追加時の検証強化**
   - グループ名パターンマッチング
   - 職業フィールドチェック
   - 複数人表現の検出

2. **データ収集の改良**
   - グループページの除外フィルター
   - メンバー個別収集ロジック
   - カテゴリ別の収集ルール

3. **品質管理プロセス**
   - 定期的な非人物チェック
   - 新規追加時の承認フロー
   - 自動テストの実装

## 📝 結論

データベースに **{len(results['non_persons'])}件以上の非人物エントリー**が混入していることが判明しました。
これは全体の約**{len(results['non_persons']) / results['total'] * 100:.1f}%**に相当します。

主な原因は：
- データ収集システムの設計不備
- グループ/個人の区別ロジック欠如
- 品質チェックプロセスの不在

これらの問題を解決するため、即座に非人物エントリーを削除し、
システムの改善を実施する必要があります。

---
*Ultra Think Non-Person Detection System v1.0*
*Generated: {timestamp}*
"""
        
        return report
    
    def export_non_persons_list(self, results: Dict[str, Any], output_file: str):
        """非人物リストをCSVで出力"""
        
        print(f"\n📝 非人物リスト出力中: {output_file}")
        
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['person_id', 'person_name', 'person_name_ja', 
                         'category', 'occupation', 'confidence', 'reasons']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            
            for item in results['non_persons']:
                writer.writerow({
                    'person_id': item['row'].get('person_id'),
                    'person_name': item['row'].get('person_name'),
                    'person_name_ja': item['row'].get('person_name_ja'),
                    'category': item['row'].get('category'),
                    'occupation': item['row'].get('occupation'),
                    'confidence': item['confidence'],
                    'reasons': '; '.join(item['reasons'])
                })
            
            for item in results['suspicious']:
                writer.writerow({
                    'person_id': item['row'].get('person_id'),
                    'person_name': item['row'].get('person_name'),
                    'person_name_ja': item['row'].get('person_name_ja'),
                    'category': item['row'].get('category'),
                    'occupation': item['row'].get('occupation'),
                    'confidence': item['confidence'],
                    'reasons': '; '.join(item['reasons'])
                })
        
        print(f"  ✅ 出力完了")


def main():
    """メイン処理"""
    
    print("="*60)
    print("🔍 Ultra Think 非人物エントリー検出システム")
    print("="*60)
    
    # 検出器初期化
    detector = NonPersonEntityDetector()
    
    # 最新のデータベースファイル
    database_file = 'ULTRA_THINK_COMPLETE_FIXED_20250827_084510.csv'
    
    # 検出実行
    results = detector.detect_non_person_entities(database_file)
    
    # レポート生成
    report = detector.generate_report(results)
    
    # レポート保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f'NON_PERSON_DETECTION_REPORT_{timestamp}.md'
    
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"\n📊 レポート保存: {report_file}")
    
    # 非人物リスト出力
    list_file = f'NON_PERSON_LIST_{timestamp}.csv'
    detector.export_non_persons_list(results, list_file)
    
    print(f"📋 非人物リスト: {list_file}")
    
    print("\n" + "="*60)
    print("✨ 分析完了")
    print("="*60)


if __name__ == "__main__":
    main()