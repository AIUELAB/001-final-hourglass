from src.secure_config import config
#!/usr/bin/env python3
"""
集団データ自動削除システム
人物ではない集団（グループ・バンド）のデータ行を完全削除
"""

import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import List, Dict, Tuple
import re
import shutil

# Google Sheets設定
SPREADSHEET_ID = "1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps"

class GroupDataRemover:
    """集団データ削除エンジン"""
    
    def __init__(self):
        self.group_occupations = self.get_group_occupations()
        self.known_groups = self.load_known_groups()
        self.removal_log = []
        
    def get_group_occupations(self) -> List[str]:
        """集団を示すoccupationリスト"""
        return [
            # 日本語
            "音楽ユニット", "音楽グループ", "バンド", "ロックバンド", 
            "アイドルグループ", "ボーイズグループ", "ガールズグループ",
            "K-POPグループ", "J-POPグループ", "音楽デュオ",
            "お笑いコンビ", "お笑いトリオ", "コメディグループ", "漫才コンビ",
            "ダンスグループ", "パフォーマンスグループ", "劇団",
            "ユニット", "グループ", "チーム", "団体", "組織", "集団",
            
            # 英語
            "band", "group", "unit", "duo", "trio", "quartet", 
            "ensemble", "team", "crew", "collective",
            
            # 複合
            "K-POPアイドルグループ", "J-POPアーティストグループ",
        ]
    
    def load_known_groups(self) -> Dict[str, bool]:
        """既知のグループ名を読み込み"""
        known_groups = {}
        
        # band_members_database.jsonから読み込み
        try:
            with open("band_members_database.json", 'r', encoding='utf-8') as f:
                band_data = json.load(f)
                for band_name in band_data.get("bands", {}).keys():
                    known_groups[band_name.lower()] = True
        except:
            pass
        
        # 追加の既知グループ
        additional_groups = [
            "YOASOBI", "After the Rain", "ずっと真夜中でいいのに。",
            "マカロニえんぴつ", "ヨルシカ", "CLAMP", "Official髭男dism",
            "King Gnu", "Mrs. GREEN APPLE", "back number", "RADWIMPS",
            "ONE OK ROCK", "SEKAI NO OWARI", "サカナクション",
            "BUMP OF CHICKEN", "Mr.Children", "B'z", "GLAY",
            "L'Arc~en~Ciel", "X JAPAN", "LUNA SEA", "BOØWY",
            "THE YELLOW MONKEY", "DIR EN GREY", "the GazettE",
            "ASIAN KUNG-FU GENERATION", "ELLEGARDEN", "10-FEET",
            "Dragon Ash", "RIP SLYME", "KICK THE CAN CREW",
            "ORANGE RANGE", "flumpool", "UVERworld", "MAN WITH A MISSION",
            "AAA", "Da-iCE", "Perfume", "BABYMETAL", "モーニング娘。",
            "AKB48", "乃木坂46", "櫻坂46", "日向坂46", "嵐",
            "関ジャニ∞", "Snow Man", "SixTONES", "なにわ男子",
            "BTS", "BLACKPINK", "TWICE", "Stray Kids", "ENHYPEN",
            "The Beatles", "Queen", "Led Zeppelin", "The Rolling Stones",
            "Metallica", "Nirvana", "Oasis", "Coldplay", "Maroon 5"
        ]
        
        for group in additional_groups:
            known_groups[group.lower()] = True
        
        return known_groups
    
    def is_group_entity(self, row: pd.Series) -> bool:
        """
        行が集団エンティティかどうか判定
        Args:
            row: データ行
        Returns:
            集団の場合True
        """
        person_name = str(row.get('person_name', '')).strip()
        occupation = str(row.get('occupation', '')).strip()
        
        # 1. occupationが明らかに集団
        if occupation:
            occupation_lower = occupation.lower()
            for group_term in self.group_occupations:
                if group_term.lower() == occupation_lower:
                    return True
                if group_term and group_term.lower() in occupation_lower:
                    return True
        
        # 2. person_nameが既知のグループ名
        if person_name:
            name_lower = person_name.lower()
            if name_lower in self.known_groups:
                return True
        
        # 3. パターンマッチング
        group_patterns = [
            r".*グループ$", r".*バンド$", r".*ユニット$",
            r".*コンビ$", r".*トリオ$", r".*団$",
            r"^グループ.*", r"^バンド.*", r"^チーム.*",
            r".*\s+band$", r".*\s+group$"
        ]
        
        if occupation:
            for pattern in group_patterns:
                if re.match(pattern, occupation.lower()):
                    return True
        
        # 4. extended_dataのsubcategoryチェック
        extended_data = row.get('extended_data', '')
        if extended_data:
            try:
                ext_dict = json.loads(extended_data) if isinstance(extended_data, str) else extended_data
                subcategory = ext_dict.get('subcategory', '').lower()
                if any(term in subcategory for term in ['グループ', 'ユニット', 'バンド', 'group', 'band']):
                    return True
            except:
                pass
        
        return False
    
    def identify_groups_in_dataframe(self, df: pd.DataFrame) -> List[int]:
        """
        DataFrameから集団データの行インデックスを特定
        Args:
            df: データフレーム
        Returns:
            削除対象の行インデックスリスト
        """
        removal_indices = []
        
        for idx, row in df.iterrows():
            if self.is_group_entity(row):
                removal_indices.append(idx)
                
                # ログに記録
                self.removal_log.append({
                    'index': idx,
                    'person_id': row.get('person_id', ''),
                    'person_name': row.get('person_name', ''),
                    'occupation': row.get('occupation', ''),
                    'reason': self.get_removal_reason(row)
                })
        
        return removal_indices
    
    def get_removal_reason(self, row: pd.Series) -> str:
        """削除理由を取得"""
        reasons = []
        
        occupation = str(row.get('occupation', '')).strip()
        person_name = str(row.get('person_name', '')).strip()
        
        if occupation in self.group_occupations:
            reasons.append(f"occupation='{occupation}'")
        
        if person_name.lower() in self.known_groups:
            reasons.append(f"known_group='{person_name}'")
        
        if not reasons:
            reasons.append("group_pattern_match")
        
        return ", ".join(reasons)
    
    def remove_groups_from_sheets(self):
        """Google Sheetsから集団データを削除"""
        print("🔄 集団データ削除処理開始")
        print("=" * 60)
        
        try:
            # 認証
            print("\n1️⃣ Google Sheets認証中...")
            credentials = Credentials.from_service_account_file(
                config.google_credentials_path,
                scopes=[
                    'https://www.googleapis.com/auth/spreadsheets',
                    'https://www.googleapis.com/auth/drive.file'
                ]
            )
            client = gspread.authorize(credentials)
            
            # スプレッドシートを開く
            print("2️⃣ データ取得中...")
            sheet = client.open_by_key(SPREADSHEET_ID)
            worksheet = sheet.sheet1
            
            # 全データ取得
            all_values = worksheet.get_all_values()
            headers = all_values[0]
            data = all_values[1:]
            
            df = pd.DataFrame(data, columns=headers)
            original_count = len(df)
            print(f"   ✅ {original_count}行のデータを取得")
            
            # バックアップ作成
            print("\n3️⃣ バックアップ作成中...")
            backup_file = f"backup_before_group_removal_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(backup_file, index=False, encoding='utf-8')
            print(f"   ✅ バックアップ: {backup_file}")
            
            # 集団データを特定
            print("\n4️⃣ 集団データ検出中...")
            removal_indices = self.identify_groups_in_dataframe(df)
            print(f"   ✅ {len(removal_indices)}件の集団データを検出")
            
            if removal_indices:
                # 削除対象を表示
                print("\n5️⃣ 削除対象:")
                print("-" * 60)
                for log in self.removal_log[:10]:
                    print(f"   {log['person_name']} ({log['occupation']}) - {log['reason']}")
                if len(self.removal_log) > 10:
                    print(f"   ... 他 {len(self.removal_log) - 10}件")
                
                # データフレームから削除
                df_cleaned = df.drop(removal_indices).reset_index(drop=True)
                new_count = len(df_cleaned)
                
                # Google Sheetsを更新
                print(f"\n6️⃣ Google Sheets更新中...")
                print(f"   {original_count}行 → {new_count}行")
                
                # クリアして新データをアップロード
                worksheet.clear()
                updated_data = [headers] + df_cleaned.values.tolist()
                worksheet.update(updated_data, range_name='A1')
                
                # ローカルCSVも更新
                print("\n7️⃣ ローカルCSV更新中...")
                csv_file = "ultra_think_NO_FAKE_RESEARCHERS_20250827_143418.csv"
                df_cleaned.to_csv(csv_file, index=False, encoding='utf-8')
                
                # 削除レポート作成
                self.create_removal_report(original_count, new_count)
                
                print("\n" + "=" * 60)
                print("✨ 集団データ削除完了！")
                print(f"   削除件数: {len(removal_indices)}件")
                print(f"   残存データ: {new_count}件")
                
            else:
                print("\n✅ 削除対象なし（集団データが見つかりませんでした）")
            
            return len(removal_indices)
            
        except Exception as e:
            print(f"\n❌ エラー: {e}")
            import traceback
            traceback.print_exc()
            return 0
    
    def create_removal_report(self, original_count: int, new_count: int):
        """削除レポートを作成"""
        report = f"""# 集団データ削除レポート
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 統計
- 元のデータ数: {original_count}件
- 削除件数: {len(self.removal_log)}件
- 残存データ数: {new_count}件
- 削除率: {(len(self.removal_log) / original_count * 100):.1f}%

## 削除データ一覧
"""
        
        for log in self.removal_log:
            report += f"\n### {log['person_name']}\n"
            report += f"- ID: {log['person_id']}\n"
            report += f"- 職業: {log['occupation']}\n"
            report += f"- 削除理由: {log['reason']}\n"
        
        # レポート保存
        report_file = f"GROUP_REMOVAL_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        # 削除データCSV保存
        removed_df = pd.DataFrame(self.removal_log)
        removed_csv = f"removed_groups_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        removed_df.to_csv(removed_csv, index=False, encoding='utf-8')
        
        print(f"\n📝 レポート保存:")
        print(f"   - {report_file}")
        print(f"   - {removed_csv}")


def apply_group_removal_to_new_data(person_data: Dict) -> Dict:
    """
    新規データに集団削除ルールを適用
    Args:
        person_data: 人物データ
    Returns:
        処理後のデータ（集団の場合はNone）
    """
    remover = GroupDataRemover()
    
    # DataFrameの1行として変換
    df_row = pd.Series(person_data)
    
    if remover.is_group_entity(df_row):
        # 集団データは追加しない
        print(f"⚠️ 集団データのため追加をスキップ: {person_data.get('person_name')}")
        return None
    
    return person_data


def test_group_detection():
    """集団検出テスト"""
    remover = GroupDataRemover()
    
    test_cases = [
        {"person_name": "YOASOBI", "occupation": "音楽ユニット"},
        {"person_name": "Ayase", "occupation": "ミュージシャン"},
        {"person_name": "After the Rain", "occupation": "音楽ユニット"},
        {"person_name": "まふまふ", "occupation": "歌手"},
        {"person_name": "CLAMP", "occupation": "漫画家"},
        {"person_name": "BTS", "occupation": "K-POPグループ"},
        {"person_name": "Jimin", "occupation": "歌手"},
    ]
    
    print("🧪 集団検出テスト")
    print("=" * 60)
    
    for test in test_cases:
        df_row = pd.Series(test)
        is_group = remover.is_group_entity(df_row)
        
        print(f"名前: {test['person_name']}")
        print(f"職業: {test['occupation']}")
        print(f"判定: {'❌ 集団（削除）' if is_group else '✅ 個人（保持）'}")
        print("-" * 40)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_group_detection()
    else:
        # 実行
        remover = GroupDataRemover()
        removed_count = remover.remove_groups_from_sheets()