#!/usr/bin/env python3
"""
事務所vsグループ自動判定システム
エンティティタイプを自動分類し、誤分類を防止
"""

import pandas as pd
import json
import re
from datetime import datetime
from typing import Dict, List, Tuple

class EntityClassifier:
    """エンティティ（事務所/グループ）分類器"""
    
    def __init__(self):
        # 事務所判定キーワード
        self.agency_keywords = [
            '事務所', 'プロダクション', 'マネジメント', 
            'エンターテインメント', 'Entertainment',
            'Inc', 'LLC', 'Corp', '株式会社', '有限会社',
            'Agency', 'Management', 'Production'
        ]
        
        # グループ判定キーワード
        self.group_keywords = [
            'バンド', 'ユニット', 'コンビ', 'トリオ',
            'チーム', 'collective', 'crew', '兄弟',
            'ズ', 'たち', 'メンバー', 'グループ'
        ]
        
        # 活動形態判定キーワード
        self.collaborative_keywords = [
            '共同', '一緒に', 'チャンネル', '合作',
            'コラボ', '結成', 'デビュー'
        ]
        
        # 既知の事務所リスト
        self.known_agencies = {
            'UUUM', 'ジェネシスワン', '吉本興業', 
            'ホリプロ', 'ジャニーズ事務所', 'アミューズ',
            'エイベックス', 'ワタナベエンターテインメント',
            'ケイダッシュステージ', 'グレープカンパニー'
        }
        
        # 既知のグループリスト
        self.known_groups = {
            'QuizKnock', '東海オンエア', 'フィッシャーズ',
            'ONE OK ROCK', 'SEKAI NO OWARI', 'L\'Arc~en~Ciel',
            'After the Rain', 'BTS', 'The Beatles',
            'さまぁ〜ず', 'ダウンタウン', 'オードリー'
        }
    
    def classify_entity(self, name: str, description: str = None) -> Tuple[str, float]:
        """
        エンティティを分類
        Returns: (type, confidence) where type is 'AGENCY', 'GROUP', or 'UNKNOWN'
        """
        
        # 既知のエンティティチェック
        if name in self.known_agencies:
            return 'AGENCY', 1.0
        if name in self.known_groups:
            return 'GROUP', 1.0
        
        # キーワードベース判定
        agency_score = 0
        group_score = 0
        
        # 名前でチェック
        for keyword in self.agency_keywords:
            if keyword in name:
                agency_score += 2
        
        for keyword in self.group_keywords:
            if keyword in name:
                group_score += 2
        
        # 説明文でチェック（もしあれば）
        if description:
            for keyword in self.agency_keywords:
                if keyword in description:
                    agency_score += 1
            
            for keyword in self.group_keywords:
                if keyword in description:
                    group_score += 1
            
            for keyword in self.collaborative_keywords:
                if keyword in description:
                    group_score += 0.5
        
        # 判定
        total_score = agency_score + group_score
        if total_score == 0:
            return 'UNKNOWN', 0.0
        
        if agency_score > group_score:
            confidence = agency_score / total_score
            return 'AGENCY', confidence
        elif group_score > agency_score:
            confidence = group_score / total_score
            return 'GROUP', confidence
        else:
            return 'UNKNOWN', 0.5
    
    def validate_group_membership(self, person_name: str, group_name: str, 
                                 occupation: str) -> bool:
        """
        グループメンバーシップの妥当性を検証
        """
        
        # 職業とグループの整合性チェック
        inconsistency_patterns = [
            ('お笑い芸人', 'ONE OK ROCK'),  # お笑い芸人がロックバンドにいるのは変
            ('芸術家', 'ONE OK ROCK'),      # 芸術家がロックバンドにいるのは変
            ('YouTuber', 'The Beatles'),    # YouTuberがビートルズにいるのは変
        ]
        
        for occ_pattern, group_pattern in inconsistency_patterns:
            if occ_pattern in occupation and group_pattern in group_name:
                return False
        
        return True

def apply_classifier(csv_file: str):
    """分類器を適用して問題を検出"""
    
    print("🤖 自動分類システムを適用中...")
    
    classifier = EntityClassifier()
    
    # CSVファイル読み込み
    df = pd.read_csv(csv_file, dtype=str)
    print(f"📊 データ読み込み完了: {len(df)}件")
    
    # 括弧内のエンティティを抽出して分類
    issues = []
    
    for idx, row in df.iterrows():
        display_name = str(row.get('person_name_display', ''))
        
        # 括弧内の文字列を抽出
        match = re.search(r'\((.*?)\)', display_name)
        if match:
            entity_name = match.group(1)
            person_id = row.get('person_id', '')
            person_name = row.get('person_name', '')
            occupation = str(row.get('occupation', ''))
            
            # エンティティを分類
            entity_type, confidence = classifier.classify_entity(entity_name)
            
            # グループメンバーシップの妥当性チェック
            if entity_type == 'GROUP':
                is_valid = classifier.validate_group_membership(
                    person_name, entity_name, occupation
                )
                if not is_valid:
                    issues.append({
                        'person_id': person_id,
                        'person_name': person_name,
                        'display_name': display_name,
                        'entity': entity_name,
                        'entity_type': entity_type,
                        'occupation': occupation,
                        'issue': 'INVALID_GROUP_MEMBERSHIP',
                        'confidence': confidence
                    })
            
            elif entity_type == 'AGENCY':
                issues.append({
                    'person_id': person_id,
                    'person_name': person_name,
                    'display_name': display_name,
                    'entity': entity_name,
                    'entity_type': entity_type,
                    'issue': 'AGENCY_AS_GROUP',
                    'confidence': confidence
                })
    
    # 結果レポート
    print(f"\n📊 分析結果:")
    print(f"  検出された問題: {len(issues)}件")
    
    if issues:
        print("\n⚠️ 検出された問題:")
        for issue in issues[:10]:  # 最初の10件を表示
            print(f"  {issue['person_id']}: {issue['display_name']}")
            print(f"    問題: {issue['issue']}")
            print(f"    エンティティタイプ: {issue['entity_type']} (信頼度: {issue['confidence']:.2f})")
    
    # レポート保存
    report_file = f'ENTITY_CLASSIFICATION_REPORT_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_records': len(df),
            'issues_found': len(issues),
            'issues': issues
        }, f, ensure_ascii=False, indent=2)
    
    print(f"\n📄 レポート保存: {report_file}")
    
    return issues

def fix_detected_issues(csv_file: str, issues: List[Dict]):
    """検出された問題を修正"""
    
    if not issues:
        print("✅ 修正が必要な問題はありません")
        return None
    
    print(f"\n🔧 {len(issues)}件の問題を修正中...")
    
    # CSVファイル読み込み
    df = pd.read_csv(csv_file, dtype=str)
    
    fixed_count = 0
    
    for issue in issues:
        person_id = issue['person_id']
        mask = df['person_id'] == person_id
        
        if mask.any():
            current_display = df.loc[mask, 'person_name_display'].values[0]
            entity = issue['entity']
            
            # 括弧内のエンティティを削除
            new_display = str(current_display).replace(f' ({entity})', '').strip()
            df.loc[mask, 'person_name_display'] = new_display
            fixed_count += 1
            
            print(f"  ✅ {person_id}: {current_display} → {new_display}")
    
    # 修正済みCSVを保存
    output_file = f'ultra_think_AUTO_CLASSIFIED_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    df.to_csv(output_file, index=False)
    
    print(f"\n✅ 修正完了: {output_file}")
    print(f"📊 修正件数: {fixed_count}件")
    
    return output_file

if __name__ == "__main__":
    # 最新の修正済みCSVファイルを使用
    csv_file = 'ultra_think_UUUM_FIXED_20250829_195729.csv'
    
    # 分類器を適用
    issues = apply_classifier(csv_file)
    
    # 問題があれば修正
    if issues:
        fixed_file = fix_detected_issues(csv_file, issues)
    else:
        print("\n✅ すべてのデータが正しく分類されています！")