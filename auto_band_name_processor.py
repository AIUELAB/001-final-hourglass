#!/usr/bin/env python3
"""
自動バンド名処理システム
人物追加時に自動的にバンド名を適用する永続的なルール
"""

import json
import pandas as pd
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class AutoBandNameProcessor:
    """バンド名自動適用プロセッサ"""
    
    def __init__(self, db_file="band_members_database.json"):
        """
        初期化
        Args:
            db_file: バンドメンバーデータベースファイル
        """
        self.db_file = db_file
        self.band_data = self.load_database()
        self.member_to_band_map = self.create_member_map()
        
    def load_database(self) -> Dict:
        """バンドメンバーデータベースを読み込み"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️ データベースファイルが見つかりません: {self.db_file}")
            return {"bands": {}, "metadata": {}}
    
    def save_database(self):
        """データベースを保存"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.band_data, f, ensure_ascii=False, indent=2)
    
    def create_member_map(self) -> Dict[str, str]:
        """メンバー名からバンド名への高速マッピングを作成"""
        member_map = {}
        for band_name, band_info in self.band_data.get("bands", {}).items():
            for member in band_info.get("members", []):
                # 正規化（大文字小文字、スペースを統一）
                normalized_member = self.normalize_name(member)
                member_map[normalized_member] = band_name
        return member_map
    
    def normalize_name(self, name: str) -> str:
        """名前を正規化（検索用）"""
        if not name:
            return ""
        # スペースを統一、前後の空白を削除
        normalized = re.sub(r'\s+', ' ', name.strip())
        return normalized
    
    def find_band_for_member(self, member_name: str) -> Optional[str]:
        """
        メンバー名からバンド名を特定
        Args:
            member_name: メンバー名
        Returns:
            バンド名（見つからない場合はNone）
        """
        normalized = self.normalize_name(member_name)
        
        # 完全一致を試す
        if normalized in self.member_to_band_map:
            return self.member_to_band_map[normalized]
        
        # 部分一致を試す（姓名の一部など）
        for member_key, band_name in self.member_to_band_map.items():
            if normalized in member_key or member_key in normalized:
                return band_name
        
        return None
    
    def apply_band_name_rule(self, person_name: str, current_display: str = None) -> str:
        """
        バンド名ルールを適用
        Args:
            person_name: 人物名
            current_display: 現在のdisplay名（省略可）
        Returns:
            更新後のdisplay名
        """
        # 既に括弧がある場合はそのまま返す
        if current_display and "(" in current_display and ")" in current_display:
            return current_display
        
        # バンド名を検索
        band_name = self.find_band_for_member(person_name)
        
        if band_name:
            # フォーマットに従って生成
            format_template = self.band_data.get("metadata", {}).get("rules", {}).get(
                "display_format", "{member_name} ({band_name})"
            )
            return format_template.format(member_name=person_name, band_name=band_name)
        
        # バンドメンバーでない場合は元の名前を返す
        return current_display if current_display else person_name
    
    def process_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, int]:
        """
        DataFrameの全行を処理
        Args:
            df: 処理対象のDataFrame
        Returns:
            (処理後のDataFrame, 更新件数)
        """
        update_count = 0
        
        # person_name_display列がない場合は作成
        if 'person_name_display' not in df.columns:
            df['person_name_display'] = df.get('person_name', '')
        
        # 各行を処理
        for idx, row in df.iterrows():
            person_name = row.get('person_name', '')
            current_display = row.get('person_name_display', '')
            
            # ルールを適用
            new_display = self.apply_band_name_rule(person_name, current_display)
            
            # 変更があった場合のみ更新
            if new_display != current_display:
                df.at[idx, 'person_name_display'] = new_display
                update_count += 1
        
        return df, update_count
    
    def process_new_person(self, person_data: Dict) -> Dict:
        """
        新しい人物データを処理
        Args:
            person_data: 人物データの辞書
        Returns:
            処理後の人物データ
        """
        person_name = person_data.get('person_name', '')
        current_display = person_data.get('person_name_display', '')
        
        # ルールを適用
        new_display = self.apply_band_name_rule(person_name, current_display)
        person_data['person_name_display'] = new_display
        
        # 処理メタデータを追加
        person_data['band_rule_applied'] = new_display != (current_display or person_name)
        person_data['band_rule_timestamp'] = datetime.now().isoformat()
        
        return person_data
    
    def add_band(self, band_name: str, members: List[str], genre: str = "", country: str = ""):
        """
        新しいバンドを追加
        Args:
            band_name: バンド名
            members: メンバーリスト
            genre: ジャンル
            country: 国
        """
        self.band_data["bands"][band_name] = {
            "members": members,
            "genre": genre,
            "country": country
        }
        
        # メンバーマップを更新
        for member in members:
            normalized = self.normalize_name(member)
            self.member_to_band_map[normalized] = band_name
        
        # メタデータを更新
        self.band_data["metadata"]["last_updated"] = datetime.now().isoformat()
        self.band_data["metadata"]["total_bands"] = len(self.band_data["bands"])
        
        # 保存
        self.save_database()
    
    def update_band_members(self, band_name: str, members: List[str]):
        """
        バンドメンバーを更新
        Args:
            band_name: バンド名
            members: 新しいメンバーリスト
        """
        if band_name in self.band_data["bands"]:
            self.band_data["bands"][band_name]["members"] = members
            
            # メンバーマップを再構築
            self.member_to_band_map = self.create_member_map()
            
            # 保存
            self.save_database()
    
    def get_statistics(self) -> Dict:
        """統計情報を取得"""
        total_bands = len(self.band_data.get("bands", {}))
        total_members = sum(
            len(band_info.get("members", [])) 
            for band_info in self.band_data.get("bands", {}).values()
        )
        
        genre_stats = {}
        for band_info in self.band_data.get("bands", {}).values():
            genre = band_info.get("genre", "Unknown")
            genre_stats[genre] = genre_stats.get(genre, 0) + 1
        
        return {
            "total_bands": total_bands,
            "total_members": total_members,
            "genre_distribution": genre_stats,
            "last_updated": self.band_data.get("metadata", {}).get("last_updated", "")
        }


# ユーティリティ関数
def apply_band_rules_to_csv(csv_file: str, output_file: str = None):
    """
    CSVファイルにバンド名ルールを適用
    Args:
        csv_file: 入力CSVファイル
        output_file: 出力CSVファイル（省略時は上書き）
    """
    processor = AutoBandNameProcessor()
    
    # CSVを読み込み
    df = pd.read_csv(csv_file, encoding='utf-8')
    
    # 処理
    df, update_count = processor.process_dataframe(df)
    
    # 保存
    if output_file is None:
        output_file = csv_file
    
    df.to_csv(output_file, index=False, encoding='utf-8')
    
    print(f"✅ {update_count}件のバンドメンバー名を更新しました")
    print(f"   出力: {output_file}")
    
    return update_count


def test_processor():
    """プロセッサのテスト"""
    processor = AutoBandNameProcessor()
    
    # テストデータ
    test_cases = [
        {"person_name": "Ayase", "person_name_display": ""},
        {"person_name": "桜井和寿", "person_name_display": ""},
        {"person_name": "John Lennon", "person_name_display": ""},
        {"person_name": "田中太郎", "person_name_display": ""},  # バンドメンバーでない
    ]
    
    print("🧪 バンド名ルール適用テスト")
    print("-" * 60)
    
    for test in test_cases:
        result = processor.process_new_person(test.copy())
        print(f"入力: {test['person_name']}")
        print(f"出力: {result['person_name_display']}")
        print(f"ルール適用: {result.get('band_rule_applied', False)}")
        print()


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--test":
            test_processor()
        else:
            # CSVファイルを処理
            csv_file = sys.argv[1]
            apply_band_rules_to_csv(csv_file)
    else:
        print("使用方法:")
        print("  python auto_band_name_processor.py <CSVファイル>")
        print("  python auto_band_name_processor.py --test")
        
        # デフォルトCSVを処理
        print("\nデフォルトCSVを処理中...")
        apply_band_rules_to_csv("ultra_think_NO_FAKE_RESEARCHERS_20250827_143418.csv")