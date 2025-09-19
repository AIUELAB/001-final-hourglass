from src.secure_config import config
#!/usr/bin/env python3
"""
自動データ処理ルールシステム
人物データベースの永続的な自動処理ルール集
"""

import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import re
import sys
import os

# パスを通す
sys.path.insert(0, os.path.dirname(__file__))
from auto_display_name_rules import AutoDisplayNameFixer

# Google Sheets設定
SPREADSHEET_ID = "1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps"

class AutoDataRules:
    """自動データ処理ルールエンジン"""
    
    def __init__(self):
        """初期化"""
        self.display_fixer = AutoDisplayNameFixer()
        self.group_occupations = self.load_group_occupations()
        self.rules_log = []
        
    def load_group_occupations(self) -> List[str]:
        """
        集団を示すoccupationのリストを定義
        これらは削除対象
        """
        return [
            # 音楽グループ
            "音楽ユニット", "音楽グループ", "バンド", "ロックバンド", "アイドルグループ",
            "K-POPグループ", "J-POPグループ", "ボーイズグループ", "ガールズグループ",
            "音楽デュオ", "コーラスグループ", "インストゥルメンタルバンド",
            
            # お笑い
            "お笑いコンビ", "お笑いトリオ", "コメディグループ", "漫才コンビ",
            
            # その他のグループ
            "ダンスグループ", "パフォーマンスグループ", "劇団", "ユニット",
            "グループ", "チーム", "団体", "組織", "集団",
            
            # 英語表記
            "band", "group", "unit", "duo", "trio", "quartet", "ensemble",
            "team", "crew", "collective"
        ]
    
    def is_group_occupation(self, occupation: str) -> bool:
        """
        occupationが集団を示すかどうか判定
        Args:
            occupation: 職業文字列
        Returns:
            集団の場合True
        """
        if not occupation:
            return False
            
        occupation_lower = str(occupation).lower().strip()
        
        # 完全一致チェック
        for group_term in self.group_occupations:
            if group_term.lower() == occupation_lower:
                return True
        
        # 部分一致チェック（より厳密に）
        group_patterns = [
            r".*グループ$", r".*バンド$", r".*ユニット$",
            r".*コンビ$", r".*トリオ$", r".*団$",
            r"^グループ.*", r"^バンド.*", r"^チーム.*"
        ]
        
        for pattern in group_patterns:
            if re.match(pattern, occupation_lower):
                return True
        
        return False
    
    def apply_all_rules(self, row: Dict) -> Dict:
        """
        すべてのルールを適用
        Args:
            row: データ行（辞書形式）
        Returns:
            処理後のデータ行
        """
        original_row = row.copy()
        
        # ルール1: 表示名の総合的な修正（バンド、グループ、架空キャラクター、ひらがな修正）
        person_name = row.get('person_name', '')
        current_display = row.get('person_name_display', '')
        occupation = row.get('occupation', '')
        new_display = self.display_fixer.fix_display_name(person_name, current_display, occupation)
        row['person_name_display'] = new_display
        
        # ルール2: occupation列から集団を削除
        if self.is_group_occupation(occupation):
            row['occupation'] = ''  # 削除
            self.rules_log.append({
                'rule': 'remove_group_occupation',
                'person': person_name,
                'removed_value': occupation,
                'timestamp': datetime.now().isoformat()
            })
        
        # 変更があったか記録
        if row != original_row:
            row['rules_applied'] = True
            row['rules_applied_at'] = datetime.now().isoformat()
        
        return row
    
    def process_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        DataFrameに全ルールを適用
        Args:
            df: 処理対象のDataFrame
        Returns:
            (処理後のDataFrame, 統計情報)
        """
        stats = {
            'total_rows': len(df),
            'display_names_modified': 0,
            'group_occupations_removed': 0
        }
        
        for idx, row in df.iterrows():
            original_row = row.to_dict()
            
            # person_name_displayルール（統合版）
            person_name = row.get('person_name', '')
            current_display = row.get('person_name_display', '')
            occupation = row.get('occupation', '')
            new_display = self.display_fixer.fix_display_name(person_name, current_display, occupation)
            
            if new_display != current_display:
                df.at[idx, 'person_name_display'] = new_display
                stats['display_names_modified'] += 1
            
            # occupationルール（集団の場合は削除）
            if self.is_group_occupation(occupation):
                df.at[idx, 'occupation'] = ''
                stats['group_occupations_removed'] += 1
        
        return df, stats
    
    def process_google_sheets(self):
        """Google Sheetsのデータを直接処理"""
        print("🔄 Google Sheetsの自動ルール処理開始")
        
        try:
            # 認証
            credentials = Credentials.from_service_account_file(
                config.google_credentials_path,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive.file'
                ]
            )
            client = gspread.authorize(credentials)
            
            # スプレッドシートを開く
            sheet = client.open_by_key(SPREADSHEET_ID)
            worksheet = sheet.sheet1
            
            # データ取得
            all_values = worksheet.get_all_values()
            headers = all_values[0]
            data = all_values[1:]
            
            df = pd.DataFrame(data, columns=headers)
            print(f"📊 {len(df)}行のデータを取得")
            
            # ルール適用
            df, stats = self.process_dataframe(df)
            
            # 更新が必要な場合のみアップロード
            if any([stats['band_names_added'], stats['group_occupations_removed'], stats['display_names_filled']]):
                # データを準備
                updated_data = [headers] + df.values.tolist()
                
                # Google Sheetsを更新
                worksheet.clear()
                worksheet.update(updated_data, range_name='A1')
                
                print("✅ Google Sheets更新完了")
            else:
                print("✅ 更新不要（すべてのルールが適用済み）")
            
            # 統計を表示
            print("\n📈 処理統計:")
            print(f"   - 表示名修正: {stats['display_names_modified']}件")
            print(f"   - 集団occupation削除: {stats['group_occupations_removed']}件")
            
            return stats
            
        except Exception as e:
            print(f"❌ エラー: {e}")
            return None


class AutoBandNameProcessor:
    """バンド名自動適用プロセッサ（統合版）"""
    
    def __init__(self, db_file="band_members_database.json"):
        self.db_file = db_file
        self.band_data = self.load_database()
        self.member_to_band_map = self.create_member_map()
        
    def load_database(self) -> Dict:
        """バンドメンバーデータベースを読み込み"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"bands": {}, "metadata": {}}
    
    def create_member_map(self) -> Dict[str, str]:
        """メンバー名からバンド名への高速マッピングを作成"""
        member_map = {}
        for band_name, band_info in self.band_data.get("bands", {}).items():
            for member in band_info.get("members", []):
                normalized_member = self.normalize_name(member)
                member_map[normalized_member] = band_name
        return member_map
    
    def normalize_name(self, name: str) -> str:
        """名前を正規化"""
        if not name:
            return ""
        return re.sub(r'\s+', ' ', name.strip())
    
    def find_band_for_member(self, member_name: str) -> Optional[str]:
        """メンバー名からバンド名を特定"""
        normalized = self.normalize_name(member_name)
        
        if normalized in self.member_to_band_map:
            return self.member_to_band_map[normalized]
        
        for member_key, band_name in self.member_to_band_map.items():
            if normalized in member_key or member_key in normalized:
                return band_name
        
        return None
    
    def apply_band_name_rule(self, person_name: str, current_display: str = None) -> str:
        """バンド名ルールを適用"""
        if current_display and "(" in current_display and ")" in current_display:
            return current_display
        
        band_name = self.find_band_for_member(person_name)
        
        if band_name:
            return f"{person_name} ({band_name})"
        
        return current_display if current_display else person_name


def apply_rules_to_new_person(person_data: Dict) -> Dict:
    """
    新しい人物データに自動ルールを適用
    この関数は人物追加時に呼び出される
    
    Args:
        person_data: 人物データの辞書
    Returns:
        ルール適用後の人物データ
    """
    rules = AutoDataRules()
    processed_data = rules.apply_all_rules(person_data)
    
    # ログを記録
    if processed_data.get('rules_applied'):
        with open('rules_application_log.json', 'a', encoding='utf-8') as f:
            log_entry = {
                'person_id': processed_data.get('person_id'),
                'person_name': processed_data.get('person_name'),
                'rules_applied': True,
                'timestamp': datetime.now().isoformat()
            }
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    return processed_data


def test_rules():
    """ルールのテスト"""
    rules = AutoDataRules()
    
    test_cases = [
        {
            "person_name": "Ayase",
            "person_name_display": "",
            "occupation": "ミュージシャン"
        },
        {
            "person_name": "YOASOBI",
            "person_name_display": "YOASOBI",
            "occupation": "音楽ユニット"  # これは削除される
        },
        {
            "person_name": "新垣結衣",
            "person_name_display": "",
            "occupation": "女優"
        },
        {
            "person_name": "BTS",
            "person_name_display": "BTS",
            "occupation": "K-POPグループ"  # これは削除される
        }
    ]
    
    print("🧪 自動ルールテスト")
    print("=" * 60)
    
    for test in test_cases:
        result = rules.apply_all_rules(test.copy())
        print(f"入力:")
        print(f"  名前: {test['person_name']}")
        print(f"  表示: {test['person_name_display']}")
        print(f"  職業: {test['occupation']}")
        print(f"出力:")
        print(f"  表示: {result['person_name_display']}")
        print(f"  職業: {result['occupation']}")
        print(f"  ルール適用: {result.get('rules_applied', False)}")
        print("-" * 40)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_rules()
    elif len(sys.argv) > 1 and sys.argv[1] == "--sheets":
        # Google Sheetsを直接処理
        rules = AutoDataRules()
        rules.process_google_sheets()
    else:
        print("使用方法:")
        print("  python auto_data_rules.py --test    # ルールのテスト")
        print("  python auto_data_rules.py --sheets  # Google Sheetsを処理")
        
        # デフォルト: ローカルCSVを処理
        print("\nローカルCSVにルールを適用中...")
        rules = AutoDataRules()
        
        csv_file = "ultra_think_NO_FAKE_RESEARCHERS_20250827_143418.csv"
        df = pd.read_csv(csv_file, encoding='utf-8')
        df, stats = rules.process_dataframe(df)
        
        # バックアップ作成
        backup_file = f"{csv_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        pd.read_csv(csv_file, encoding='utf-8').to_csv(backup_file, index=False, encoding='utf-8')
        
        # 保存
        df.to_csv(csv_file, index=False, encoding='utf-8')
        
        print(f"✅ 処理完了")
        print(f"   - バンド名追加: {stats['band_names_added']}件")
        print(f"   - 集団occupation削除: {stats['group_occupations_removed']}件")