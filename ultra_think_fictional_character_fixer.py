#!/usr/bin/env python3
"""
Ultra Think 架空キャラクター作品名修正システム
架空キャラクターのperson_name_displayに作品名を追加
"""
import pandas as pd
import json
import re
from datetime import datetime

class FictionalCharacterFixer:
    def __init__(self):
        # 作品データベースを読み込み
        with open('fictional_works_database.json', 'r', encoding='utf-8') as f:
            self.works_db = json.load(f)
        
        self.works_data = self.works_db['作品データベース']
        self.character_to_work = self.works_db['キャラクター名変換']
        
        # キャラクター名から作品名への完全マッピングを構築
        self.build_character_mapping()
        
        self.fixed_records = []
        self.unfixed_records = []
    
    def build_character_mapping(self):
        """キャラクター名から作品名へのマッピングを構築"""
        # 既存のマッピングを拡張
        for work_name, work_data in self.works_data.items():
            for character in work_data['characters']:
                # 既存のマッピングがなければ追加
                if character not in self.character_to_work:
                    self.character_to_work[character] = work_name
    
    def normalize_name(self, name):
        """名前を正規化"""
        if pd.isna(name):
            return ''
        name = str(name).strip()
        # 既存の括弧内容を削除
        name = re.sub(r'[\(（].*?[\)）]', '', name).strip()
        return name
    
    def is_fictional_character(self, row):
        """架空キャラクターかどうか判定"""
        # 複合判定ロジック
        
        # 1. categoryが「架空の存在」
        if row.get('category') == '架空の存在':
            return True
        
        # 2. extended_dataでis_fictional=TRUE
        extended = str(row.get('extended_data', ''))
        if 'is_fictional' in extended and 'TRUE' in extended:
            return True
        
        # 3. occupationが架空的
        occupation = str(row.get('occupation', ''))
        fictional_occupations = [
            '架空キャラクター', 'ヒーロー', '忍者', '探偵', '海賊',
            'エヴァパイロット', '武道家', '戦士', '剣士', '魔法使い',
            '鬼殺隊', '上忍', '宇宙の帝王', '悪役', 'ロボット'
        ]
        if any(occ in occupation for occ in fictional_occupations):
            return True
        
        # 4. キャラクター名がデータベースに存在
        names = [
            self.normalize_name(row.get('person_name', '')),
            self.normalize_name(row.get('person_name_ja', '')),
            self.normalize_name(row.get('person_name_display', ''))
        ]
        for name in names:
            if name in self.character_to_work:
                return True
        
        return False
    
    def find_work_title(self, row):
        """キャラクターの作品名を特定"""
        # 複数の名前フィールドから検索
        names = [
            self.normalize_name(row.get('person_name', '')),
            self.normalize_name(row.get('person_name_ja', '')),
            self.normalize_name(row.get('person_name_display', ''))
        ]
        
        # 直接マッピングから検索
        for name in names:
            if name in self.character_to_work:
                return self.character_to_work[name]
        
        # 部分一致で検索
        for name in names:
            if name:
                # 各作品のキャラクターリストと照合
                for work_name, work_data in self.works_data.items():
                    for character in work_data['characters']:
                        if name in character or character in name:
                            return work_name
        
        # 特殊なパターン処理
        person_name = str(row.get('person_name', ''))
        
        # 名前に作品名のヒントが含まれる場合
        if 'Naruto' in person_name or 'うずまき' in person_name:
            return 'NARUTO'
        if 'Goku' in person_name or '悟空' in person_name:
            return 'ドラゴンボール'
        if 'Luffy' in person_name or 'ルフィ' in person_name:
            return 'ONE PIECE'
        
        return None
    
    def fix_display_name(self, row, work_title):
        """display名に作品名を追加"""
        # 現在のdisplay名を取得
        current_display = row.get('person_name_display', '')
        
        # person_name_jaまたはperson_nameから基本名を取得
        base_name = row.get('person_name_ja', '')
        if not base_name or pd.isna(base_name):
            base_name = row.get('person_name', '')
        
        base_name = self.normalize_name(base_name)
        
        # 既に作品名が含まれているか確認
        if pd.notna(current_display) and ('(' in current_display or '（' in current_display):
            # 既存の括弧内容を確認
            match = re.search(r'[\(（](.*?)[\)）]', current_display)
            if match and match.group(1) == work_title:
                # 既に正しい作品名がある
                return current_display
        
        # 新しいdisplay名を生成
        new_display = f"{base_name}（{work_title}）"
        return new_display
    
    def process_dataframe(self, df):
        """データフレーム全体を処理"""
        print("🎭 架空キャラクター作品名修正を開始...")
        
        # 架空キャラクターを特定
        fictional_characters = []
        for idx, row in df.iterrows():
            if self.is_fictional_character(row):
                fictional_characters.append(idx)
        
        print(f"   架空キャラクター: {len(fictional_characters)}件")
        
        fixed_count = 0
        unfixed_count = 0
        
        for idx in fictional_characters:
            row = df.loc[idx]
            person_id = row['person_id']
            current_display = row.get('person_name_display', '')
            
            # 既に作品名がある場合はスキップ
            if pd.notna(current_display) and ('(' in current_display or '（' in current_display):
                continue
            
            # 作品名を特定
            work_title = self.find_work_title(row)
            
            if work_title:
                # display名を修正
                new_display = self.fix_display_name(row, work_title)
                df.loc[idx, 'person_name_display'] = new_display
                
                self.fixed_records.append({
                    'person_id': person_id,
                    'person_name': row.get('person_name', ''),
                    'original_display': current_display,
                    'new_display': new_display,
                    'work_title': work_title,
                    'occupation': row.get('occupation', '')
                })
                fixed_count += 1
                
                # 重要なレコードの進捗表示
                if person_id in ['P000199', 'P000075', 'P000102', 'P000535']:
                    print(f"   🌟 {person_id}: {current_display or row.get('person_name', '')} → {new_display}")
            else:
                # 作品名を特定できなかった
                self.unfixed_records.append({
                    'person_id': person_id,
                    'person_name': row.get('person_name', ''),
                    'person_name_display': current_display,
                    'occupation': row.get('occupation', ''),
                    'category': row.get('category', '')
                })
                unfixed_count += 1
        
        print(f"✅ {fixed_count}件を修正")
        print(f"⚠️ {unfixed_count}件は作品名を特定できませんでした")
        
        return df
    
    def generate_report(self, output_file):
        """修正レポートを生成"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 作品別に集計
        works_summary = {}
        for record in self.fixed_records:
            work = record['work_title']
            if work not in works_summary:
                works_summary[work] = []
            works_summary[work].append(record)
        
        report = f"""# 🎭 架空キャラクター作品名修正レポート

**実行日時**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}
**修正件数**: {len(self.fixed_records)}件
**未修正件数**: {len(self.unfixed_records)}件

## 📊 問題の概要

### 修正前の問題
- 架空キャラクターのperson_name_displayに作品名が表示されていない
- P000199（アルミン）など主要キャラクターの作品情報が欠落

### 修正後の形式
- すべての架空キャラクターに「キャラクター名（作品名）」形式で表示

## 🌟 重要修正事例

"""
        
        # P000199の特別扱い
        p199_fixed = next((r for r in self.fixed_records if r['person_id'] == 'P000199'), None)
        if p199_fixed:
            report += f"""### P000199（アルミン）
- **修正前**: {p199_fixed['original_display'] or p199_fixed['person_name']}
- **修正後**: **{p199_fixed['new_display']}** ✅
- **作品**: 進撃の巨人

"""
        
        # 作品別修正内容
        report += "## 📚 作品別修正内容\n\n"
        
        for work_name in sorted(works_summary.keys()):
            characters = works_summary[work_name]
            report += f"### {work_name} ({len(characters)}名)\n\n"
            report += "| person_id | キャラクター名 | 修正前 | 修正後 |\n"
            report += "|-----------|---------------|--------|--------|\n"
            
            for char in characters[:10]:  # 最初の10名のみ表示
                orig = char['original_display'] or char['person_name']
                report += f"| {char['person_id']} | {char['person_name']} | "
                report += f"{orig} | {char['new_display']} |\n"
            
            if len(characters) > 10:
                report += f"| ... | 他{len(characters)-10}名 | ... | ... |\n"
            
            report += "\n"
        
        # 未修正リスト
        if self.unfixed_records:
            report += "## ⚠️ 作品名を特定できなかったキャラクター\n\n"
            report += "| person_id | キャラクター名 | occupation | category |\n"
            report += "|-----------|---------------|------------|----------|\n"
            
            for record in self.unfixed_records[:20]:
                report += f"| {record['person_id']} | {record['person_name']} | "
                report += f"{record['occupation']} | {record['category']} |\n"
            
            if len(self.unfixed_records) > 20:
                report += f"| ... | 他{len(self.unfixed_records)-20}件 | ... | ... |\n"
        
        # 統計
        report += f"""

## 📈 統計

- **修正成功**: {len(self.fixed_records)}件
- **作品数**: {len(works_summary)}作品
- **未修正**: {len(self.unfixed_records)}件
- **成功率**: {len(self.fixed_records)/(len(self.fixed_records)+len(self.unfixed_records))*100:.1f}%

## 💾 出力ファイル

- **修正済みCSV**: {output_file}
- **修正ログ**: fictional_character_fix_log_{timestamp}.json

---
*レポート生成: {datetime.now().isoformat()}*
"""
        
        report_file = f'FICTIONAL_CHARACTER_FIX_REPORT_{timestamp}.md'
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"📄 レポート生成: {report_file}")
        
        return report_file

def main():
    print("=" * 80)
    print("🚀 Ultra Think 架空キャラクター作品名修正システム起動")
    print("=" * 80)
    
    fixer = FictionalCharacterFixer()
    
    # 最新のCSVファイルを処理
    csv_file = 'ultra_think_UNDERSCORE_FIXED_20250828_205441.csv'
    
    # バックアップを作成
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backup_before_fictional_fix_{timestamp}.csv'
    df = pd.read_csv(csv_file)
    df.to_csv(backup_file, index=False)
    print(f"💾 バックアップ作成: {backup_file}")
    
    # 修正実行
    df_fixed = fixer.process_dataframe(df)
    
    # 出力ファイル名を生成
    output_file = f'ultra_think_FICTIONAL_FIXED_{timestamp}.csv'
    df_fixed.to_csv(output_file, index=False)
    print(f"✅ 修正済みファイル: {output_file}")
    
    # 修正ログを保存
    log_file = f'fictional_character_fix_log_{timestamp}.json'
    with open(log_file, 'w', encoding='utf-8') as f:
        json.dump({
            'fixed_records': fixer.fixed_records,
            'unfixed_records': fixer.unfixed_records,
            'summary': {
                'total_fixed': len(fixer.fixed_records),
                'total_unfixed': len(fixer.unfixed_records),
                'timestamp': datetime.now().isoformat()
            }
        }, f, ensure_ascii=False, indent=2)
    print(f"📝 修正ログ: {log_file}")
    
    # レポート生成
    report_file = fixer.generate_report(output_file)
    
    # P000199の最終確認
    print("\n" + "=" * 80)
    p199 = df_fixed[df_fixed['person_id'] == 'P000199']
    if not p199.empty:
        display = p199.iloc[0]['person_name_display']
        print(f"🌟 P000199（アルミン）最終確認:")
        print(f"   person_name_display: {display}")
        if '進撃の巨人' in str(display):
            print("   ✅ 正しく修正されました！")
    
    print("\n✨ 架空キャラクター作品名修正完了!")
    print(f"📊 合計 {len(fixer.fixed_records)} 件のレコードを修正しました")

if __name__ == '__main__':
    main()