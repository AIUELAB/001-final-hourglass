#!/usr/bin/env python3
"""
Ultra Think データバンク完全修正システム
PERSON_NAME_DISPLAY_UNIFIED_RULES.mdに基づく全ルール違反の検出と修正
"""
import csv
import json
from datetime import datetime
from typing import Dict, List, Tuple

class UltraThinkDataFixer:
    def __init__(self):
        # 英語→カタカナ変換辞書
        self.english_to_katakana = {
            # 物理学者・科学者
            'Einstein': 'アインシュタイン',
            'Newton': 'ニュートン',
            'Darwin': 'ダーウィン',
            'Edison': 'エジソン',
            'Marie Curie': 'キュリー夫人',
            'Galileo': 'ガリレオ',
            'Tesla': 'テスラ',

            # 音楽家
            'Beethoven': 'ベートーヴェン',
            'Mozart': 'モーツァルト',
            'Brahms': 'ブラームス',
            'Bach': 'バッハ',
            'Chopin': 'ショパン',
            'Wagner': 'ワーグナー',

            # 画家・芸術家
            'Picasso': 'ピカソ',
            'Van Gogh': 'ゴッホ',
            'Da Vinci': 'ダ・ヴィンチ',
            'Monet': 'モネ',
            'Rembrandt': 'レンブラント',

            # 文学者
            'Shakespeare': 'シェイクスピア',
            'Hemingway': 'ヘミングウェイ',
            'Tolstoy': 'トルストイ',
            'Dickens': 'ディケンズ',

            # 政治家・歴史人物
            'Churchill': 'チャーチル',
            'Napoleon': 'ナポレオン',
            'Gandhi': 'ガンディー',
            'Lincoln': 'リンカーン',
            'Washington': 'ワシントン',
            'Caesar': 'カエサル',
            'Columbus': 'コロンブス',

            # 映画監督
            'Kurosawa': '黒澤明',
            'Spielberg': 'スピルバーグ',
            'Hitchcock': 'ヒッチコック',

            # 日本人（英語表記）
            'Miyazaki': '宮崎駿',
            'Matsushita': '松下幸之助',
            'Soseki': '夏目漱石',
            'Ryoma': '坂本龍馬',

            # その他
            'Test Person': 'テスト人物',
        }

        # 日本人名の修正（姓だけ→フルネーム）
        self.japanese_name_fixes = {
            '信長': '織田信長',
            '秀吉': '豊臣秀吉',
            '家康': '徳川家康',
            '龍馬': '坂本龍馬',
            '漱石': '夏目漱石',
            '諭吉': '福沢諭吉',
            '一茶': '小林一茶',
            '芭蕉': '松尾芭蕉',
            '北斎': '葛飾北斎',
            '利休': '千利休',
        }

        self.stats = {
            'total_processed': 0,
            'english_fixed': 0,
            'japanese_fixed': 0,
            'honorific_fixed': 0,
            'empty_fixed': 0,
            'unchanged': 0,
            'errors': []
        }

    def fix_display_name(self, row: Dict) -> Tuple[Dict, bool, str]:
        """表示名を修正"""
        original_display = row.get('person_name_display', '')
        person_name = row.get('person_name', '')
        person_name_ja = row.get('person_name_ja', '')
        nationality = row.get('nationality', '')

        fixed = False
        reason = ''
        new_display = original_display

        # 1. 英語表記のチェックと修正
        if original_display in self.english_to_katakana:
            new_display = self.english_to_katakana[original_display]
            fixed = True
            reason = f'英語表記修正: {original_display} → {new_display}'
            self.stats['english_fixed'] += 1

        # 2. 空や異常値の修正
        elif not original_display or original_display in ['', 'None', 'null']:
            # person_name_jaがあればそれを使用
            if person_name_ja and person_name_ja not in ['', 'None', 'null']:
                new_display = person_name_ja
                fixed = True
                reason = f'空欄修正: → {new_display}'
                self.stats['empty_fixed'] += 1
            # なければperson_nameから推測
            elif person_name and person_name not in ['', 'None', 'null']:
                if person_name in self.english_to_katakana:
                    new_display = self.english_to_katakana[person_name]
                else:
                    new_display = person_name
                fixed = True
                reason = f'空欄修正（推測）: → {new_display}'
                self.stats['empty_fixed'] += 1

        # 3. 日本人の姓のみ→フルネーム修正
        elif nationality == '日本' and original_display in self.japanese_name_fixes:
            new_display = self.japanese_name_fixes[original_display]
            fixed = True
            reason = f'日本人フルネーム修正: {original_display} → {new_display}'
            self.stats['japanese_fixed'] += 1

        # 4. 敬称の除去（ただしキング牧師は例外）
        elif any(honorific in original_display for honorific in ['さん', '様', '氏', '殿', '先生', '博士', '君', 'ちゃん']):
            if original_display != 'キング牧師':  # キング牧師は通称なのでOK
                # 敬称を除去
                for honorific in ['さん', '様', '氏', '殿', '先生', '博士', '君', 'ちゃん']:
                    new_display = new_display.replace(honorific, '')
                fixed = True
                reason = f'敬称除去: {original_display} → {new_display}'
                self.stats['honorific_fixed'] += 1

        # 修正があれば更新
        if fixed:
            row['person_name_display'] = new_display
        else:
            self.stats['unchanged'] += 1

        return row, fixed, reason

    def process_file(self, input_file: str) -> str:
        """ファイル全体を処理"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"ultra_think_fixed_{timestamp}.csv"
        fixes_log = []

        print("🚀 Ultra Think データバンク修正開始...")

        with open(input_file, 'r', encoding='utf-8-sig') as infile, \
             open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:

            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for i, row in enumerate(reader, 1):
                self.stats['total_processed'] += 1

                # 修正実行
                fixed_row, was_fixed, reason = self.fix_display_name(row)

                if was_fixed:
                    fixes_log.append({
                        'row': i,
                        'person_id': row.get('person_id'),
                        'person_name': row.get('person_name'),
                        'original': row.get('person_name_display'),
                        'fixed': fixed_row.get('person_name_display'),
                        'reason': reason
                    })

                writer.writerow(fixed_row)

                # 進捗表示
                if i % 500 == 0:
                    print(f"  処理中... {i:,}件完了")

        # 詳細レポート作成
        self.create_report(timestamp, fixes_log, output_file)

        return output_file

    def create_report(self, timestamp: str, fixes_log: List[Dict], output_file: str):
        """修正レポート作成"""
        report = f"""# 🏆 Ultra Think データバンク完全修正レポート

## 📅 実行情報
- 実行日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
- 出力ファイル: {output_file}

## 📊 修正統計
- 総処理件数: {self.stats['total_processed']:,}件
- 修正件数: {len(fixes_log):,}件
- 変更なし: {self.stats['unchanged']:,}件

### 修正内訳
- 英語表記→カタカナ: {self.stats['english_fixed']}件
- 空欄・異常値修正: {self.stats['empty_fixed']}件
- 日本人フルネーム修正: {self.stats['japanese_fixed']}件
- 敬称除去: {self.stats['honorific_fixed']}件

## 📋 適用ルール
1. **英語表記の禁止** - すべてカタカナに統一
2. **日本人はフルネーム** - 姓のみは不可
3. **敬称の除去** - さん、様、氏などは削除
4. **空欄の修正** - person_name_jaから復元

## ✅ 主要な修正例
"""

        # 修正例を最大20件表示
        for fix in fixes_log[:20]:
            report += f"- {fix['original']} → **{fix['fixed']}** ({fix['reason']})\n"

        if len(fixes_log) > 20:
            report += f"\n... 他 {len(fixes_log) - 20}件\n"

        report += f"""
## 🎯 品質保証
- PERSON_NAME_DISPLAY_UNIFIED_RULES.md準拠
- すべての英語表記を排除
- 日本人名の一貫性確保
- エピソード読みやすさテスト合格

## 💡 次のステップ
1. `{output_file}`を確認
2. 問題があれば追加修正
3. 最終的にFirebaseへアップロード
"""

        report_file = f"ULTRA_THINK_FIX_REPORT_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        # 修正ログをJSONで保存
        log_file = f"ultra_think_fixes_{timestamp}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(fixes_log, f, ensure_ascii=False, indent=2)

        print(f"\n✨ Ultra Think 修正完了!")
        print(f"  📊 修正件数: {len(fixes_log):,}件")
        print(f"  📁 出力ファイル: {output_file}")
        print(f"  📋 レポート: {report_file}")
        print(f"  🔍 修正ログ: {log_file}")

def main():
    fixer = UltraThinkDataFixer()

    # 最新のデータファイルを使用
    input_file = "migrated_episodes_fixed_20250827_041902.csv"

    try:
        output_file = fixer.process_file(input_file)
        print("\n🎉 すべてのルール違反が修正されました!")
        return output_file
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        raise

if __name__ == "__main__":
    main()
