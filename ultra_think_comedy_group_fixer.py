#!/usr/bin/env python3
"""
Ultra Think お笑い芸人グループ名修正システム
包括的にお笑い芸人のグループ名表示を修正
"""
import pandas as pd
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple, Optional

class ComedyGroupFixer:
    def __init__(self, csv_file: str, groups_db_file: str):
        self.csv_file = csv_file
        self.groups_db_file = groups_db_file
        self.df = pd.read_csv(csv_file)
        self.groups_db = self.load_groups_database(groups_db_file)
        self.fixes = []
        self.stats = {
            'total_comedians': 0,
            'already_correct': 0,
            'fixed': 0,
            'not_found': 0,
            'errors': 0
        }
    
    def load_groups_database(self, file_path: str) -> Dict:
        """groups_database.jsonを読み込み"""
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def normalize_name(self, name: str) -> str:
        """名前を正規化（比較用）"""
        if pd.isna(name):
            return ""
        # スペース、アンダースコア、グループ名を除去
        name = str(name).strip()
        # グループ名部分を除去
        if '(' in name:
            name = name.split('(')[0].strip()
        # アンダースコアとグループ名を除去
        if '_' in name:
            name = name.split('_')[0].strip()
        # 英語の敬称を除去
        name = re.sub(r'\s+(san|kun|chan|sama)$', '', name, flags=re.IGNORECASE)
        return name.lower()
    
    def find_group_for_member(self, person_name: str, person_name_ja: str) -> Optional[Tuple[str, str]]:
        """メンバー名からグループを検索"""
        # 名前を正規化
        normalized_name = self.normalize_name(person_name)
        normalized_name_ja = self.normalize_name(person_name_ja)
        
        # groups_databaseを検索
        for group_name, members in self.groups_db.items():
            # メタデータやルールセクションをスキップ
            if group_name in ['rules', 'comedians', 'youtubers']:
                continue
            
            if not isinstance(members, list):
                continue
            
            # メンバーリストと照合
            for member in members:
                normalized_member = self.normalize_name(member)
                
                # person_nameと一致
                if normalized_name and normalized_member == normalized_name:
                    return group_name, member
                
                # person_name_jaと一致
                if normalized_name_ja and normalized_member == normalized_name_ja:
                    return group_name, member
                
                # 部分一致（名前の一部が含まれる）
                if normalized_name and normalized_name in normalized_member:
                    return group_name, member
                if normalized_name_ja and normalized_name_ja in normalized_member:
                    return group_name, member
        
        return None
    
    def create_display_name(self, base_name: str, group_name: str) -> str:
        """表示名を作成"""
        # すでに括弧がある場合は置換
        if '(' in base_name:
            base_name = base_name.split('(')[0].strip()
        return f"{base_name} ({group_name})"
    
    def fix_comedian_groups(self):
        """お笑い芸人のグループ名を修正"""
        # お笑い芸人のみフィルタ
        comedians_mask = self.df['occupation'] == 'お笑い芸人'
        comedians = self.df[comedians_mask].copy()
        self.stats['total_comedians'] = len(comedians)
        
        print(f"\n📊 {len(comedians)}人のお笑い芸人を処理中...")
        
        for idx, row in comedians.iterrows():
            person_id = row['person_id']
            person_name = row['person_name']
            person_name_ja = row.get('person_name_ja', '')
            current_display = row['person_name_display']
            
            # 既に正しいグループ名が付いているか確認
            if '(' in str(current_display) and ')' in str(current_display):
                # 括弧内のグループ名を抽出
                match = re.search(r'\((.+?)\)', str(current_display))
                if match:
                    current_group = match.group(1)
                    # グループが正しいか確認
                    group_result = self.find_group_for_member(person_name, person_name_ja)
                    if group_result and group_result[0] == current_group:
                        self.stats['already_correct'] += 1
                        continue
            
            # グループを検索
            group_result = self.find_group_for_member(person_name, person_name_ja)
            
            if group_result:
                group_name, matched_member = group_result
                
                # 表示名を決定（日本語名優先）
                if person_name_ja and not pd.isna(person_name_ja):
                    # 日本語名がある場合はそれを使用
                    base_name = person_name_ja
                else:
                    # なければperson_nameを使用
                    base_name = person_name
                
                # 新しい表示名を作成
                new_display = self.create_display_name(base_name, group_name)
                
                # 更新
                if new_display != current_display:
                    self.df.loc[idx, 'person_name_display'] = new_display
                    self.fixes.append({
                        'person_id': person_id,
                        'person_name': person_name,
                        'person_name_ja': person_name_ja,
                        'old_display': current_display,
                        'new_display': new_display,
                        'group': group_name,
                        'matched_as': matched_member
                    })
                    self.stats['fixed'] += 1
            else:
                # グループが見つからない場合
                # 既に括弧がある場合はそのまま
                if '(' in str(current_display):
                    self.stats['already_correct'] += 1
                else:
                    self.stats['not_found'] += 1
                    # デバッグ用に記録
                    self.fixes.append({
                        'person_id': person_id,
                        'person_name': person_name,
                        'person_name_ja': person_name_ja,
                        'status': 'not_found',
                        'current_display': current_display
                    })
    
    def save_results(self):
        """結果を保存"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # 修正済みCSVを保存
        output_csv = f'ultra_think_COMEDY_GROUPS_FIXED_{timestamp}.csv'
        self.df.to_csv(output_csv, index=False, encoding='utf-8')
        
        # 修正ログを保存
        fix_log = {
            'timestamp': datetime.now().isoformat(),
            'stats': self.stats,
            'fixes': self.fixes
        }
        
        with open(f'comedy_groups_fix_log_{timestamp}.json', 'w', encoding='utf-8') as f:
            json.dump(fix_log, f, ensure_ascii=False, indent=2)
        
        return output_csv, fix_log
    
    def print_report(self):
        """レポートを表示"""
        print("\n" + "="*60)
        print("📊 修正レポート")
        print("="*60)
        print(f"お笑い芸人総数: {self.stats['total_comedians']}")
        print(f"既に正しい: {self.stats['already_correct']}")
        print(f"修正済み: {self.stats['fixed']}")
        print(f"グループ不明: {self.stats['not_found']}")
        print(f"エラー: {self.stats['errors']}")
        print("-"*60)
        
        if self.stats['fixed'] > 0:
            print("\n✅ 修正例（最初の10件）:")
            for fix in self.fixes[:10]:
                if 'new_display' in fix:
                    print(f"  {fix['person_id']}: {fix['old_display']} → {fix['new_display']}")
        
        if self.stats['not_found'] > 0:
            print(f"\n⚠️ グループが見つからなかった芸人: {self.stats['not_found']}人")
            # 最初の5人を表示
            not_found = [f for f in self.fixes if 'status' in f and f['status'] == 'not_found']
            for fix in not_found[:5]:
                print(f"  {fix['person_id']}: {fix['person_name']} / {fix['person_name_ja']}")
    
    def fix_specific_person(self, person_id: str, group_name: str):
        """特定の人物のグループ名を手動で修正"""
        mask = self.df['person_id'] == person_id
        if mask.any():
            idx = self.df[mask].index[0]
            row = self.df.loc[idx]
            
            # 表示名を決定
            if row['person_name_ja'] and not pd.isna(row['person_name_ja']):
                base_name = row['person_name_ja']
            else:
                base_name = row['person_name']
            
            new_display = self.create_display_name(base_name, group_name)
            self.df.loc[idx, 'person_name_display'] = new_display
            
            print(f"✅ {person_id}: {new_display}")
            return True
        return False

def main():
    print("🚀 Ultra Think お笑い芸人グループ名修正システム起動")
    
    # 修正システムを初期化
    fixer = ComedyGroupFixer(
        csv_file='ultra_think_WRONG_GROUPS_FIXED.csv',
        groups_db_file='groups_database.json'
    )
    
    # P000057（おたけ）を特別に修正
    print("\n🎯 P000057（おたけ）を特別処理...")
    fixer.fix_specific_person('P000057', 'ジャングルポケット')
    
    # 全体の修正を実行
    print("\n🔧 全お笑い芸人のグループ名を修正中...")
    fixer.fix_comedian_groups()
    
    # 結果を保存
    output_file, log = fixer.save_results()
    
    # レポートを表示
    fixer.print_report()
    
    print(f"\n📁 出力ファイル: {output_file}")
    
    # 修正率を計算
    fix_rate = (fixer.stats['fixed'] / fixer.stats['total_comedians']) * 100 if fixer.stats['total_comedians'] > 0 else 0
    print(f"\n🎯 修正率: {fix_rate:.1f}%")
    
    # 問題解決率
    problem_solved = fixer.stats['fixed'] + fixer.stats['already_correct']
    solve_rate = (problem_solved / fixer.stats['total_comedians']) * 100 if fixer.stats['total_comedians'] > 0 else 0
    print(f"✨ 問題解決率: {solve_rate:.1f}%")
    
    return output_file, fixer.stats

if __name__ == "__main__":
    output, stats = main()