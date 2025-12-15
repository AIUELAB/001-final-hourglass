from src.secure_config import config
#!/usr/bin/env python3
"""
自動表示名修正ルールシステム
person_name_displayがひらがなになっている場合、person_nameから正しい表記を取得
"""

import json
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import re

# Google Sheets設定
SPREADSHEET_ID = "1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps"

class BandNameProcessor:
    """バンド名処理プロセッサ（統合版）"""

    def __init__(self, db_file="band_members_database.json"):
        self.db_file = db_file
        self.band_data = self.load_database()
        self.member_to_band_map = self.create_member_map()

    def load_database(self) -> Dict[str, Any]:
        """バンドメンバーデータベースを読み込み"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                data: Dict[str, Any] = json.load(f)
                return data
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

    def apply_band_name_rule(self, person_name: str, current_display: Optional[str] = None) -> str:
        """バンド名ルールを適用"""
        if current_display and "(" in current_display and ")" in current_display:
            return current_display

        band_name = self.find_band_for_member(person_name)

        if band_name:
            return f"{person_name} ({band_name})"

        return current_display if current_display else person_name


class FictionalCharacterProcessor:
    """架空キャラクター処理プロセッサ"""

    def __init__(self, db_file="fictional_characters_database.json"):
        self.db_file = db_file
        self.character_data = self.load_database()
        self.character_to_series_map = self.create_character_map()

    def load_database(self) -> Dict[str, Any]:
        """架空キャラクターデータベースを読み込み"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                data: Dict[str, Any] = json.load(f)
                return data
        except FileNotFoundError:
            return {"characters": {}, "metadata": {}}

    def create_character_map(self) -> Dict[str, str]:
        """キャラクター名から作品名への高速マッピングを作成"""
        character_map = {}
        for series_key, series_info in self.character_data.get("characters", {}).items():
            title = series_info.get("title", series_key)
            for character in series_info.get("characters", []):
                normalized = self.normalize_name(character)
                character_map[normalized] = title
        return character_map

    def normalize_name(self, name: str) -> str:
        """名前を正規化"""
        if not name:
            return ""
        # スペースや中点を統一
        normalized = re.sub(r'[・\s]+', '', name.strip())
        return normalized

    def is_fictional_occupation(self, occupation: Optional[str]) -> bool:
        """occupationが架空キャラクターを示すかチェック"""
        if not occupation:
            return False

        occupation_lower = occupation.lower()
        keywords = self.character_data.get("metadata", {}).get("rules", {}).get(
            "occupation_keywords",
            ["架空キャラクター", "架空の存在", "アニメキャラクター", "ゲームキャラクター"]
        )

        for keyword in keywords:
            if keyword.lower() in occupation_lower:
                return True
        return False

    def find_series_for_character(self, character_name: str) -> Optional[str]:
        """キャラクター名から作品名を特定"""
        # 正規化
        normalized = self.normalize_name(character_name)

        # 完全一致を試す
        if normalized in self.character_to_series_map:
            return self.character_to_series_map[normalized]

        # 部分一致を試す
        for member_key, series_title in self.character_to_series_map.items():
            if normalized in member_key or member_key in normalized:
                return series_title

        return None

    def apply_fictional_rule(self, person_name: str, current_display: str, occupation: Optional[str] = None) -> str:
        """架空キャラクタールールを適用"""
        # 既に括弧がある場合はそのまま返す
        if current_display and "(" in current_display and ")" in current_display:
            return current_display

        # occupationが架空キャラクターでない場合
        if not self.is_fictional_occupation(occupation):
            return current_display

        # 作品名を検索
        series_title = self.find_series_for_character(person_name)

        if series_title:
            # フォーマットに従って生成
            format_template = self.character_data.get("metadata", {}).get("rules", {}).get(
                "display_format", "{character_name} ({series_title})"
            )
            result1: str = format_template.format(character_name=person_name, series_title=series_title)
            return result1

        # 作品が特定できない架空キャラクターの場合
        if self.is_fictional_occupation(occupation):
            result2: str = f"{person_name} (架空キャラクター)"
            return result2

        result3: str = current_display if current_display else person_name
        return result3


class GroupProcessor:
    """グループ処理プロセッサ（YouTuber、お笑い芸人）"""

    def __init__(self, db_file="groups_database.json"):
        self.db_file = db_file
        self.group_data = self.load_database()
        self.member_to_group_map = self.create_member_map()

    def load_database(self) -> Dict[str, Any]:
        """グループデータベースを読み込み"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                data: Dict[str, Any] = json.load(f)
                return data
        except FileNotFoundError:
            return {"youtuber_groups": {}, "comedy_groups": {}, "metadata": {}}

    def create_member_map(self) -> Dict[str, Tuple[str, str]]:
        """メンバー名からグループ名とタイプへのマッピングを作成"""
        member_map = {}

        # YouTuberグループ
        for group_name, group_info in self.group_data.get("youtuber_groups", {}).items():
            for member in group_info.get("members", []):
                normalized = self.normalize_name(member)
                member_map[normalized] = (group_name, "youtuber")

        # お笑いグループ
        for group_name, group_info in self.group_data.get("comedy_groups", {}).items():
            for member in group_info.get("members", []):
                normalized = self.normalize_name(member)
                member_map[normalized] = (group_name, "comedy")

        return member_map

    def normalize_name(self, name: str) -> str:
        """名前を正規化"""
        if not name:
            return ""
        return re.sub(r'\s+', ' ', name.strip())

    def is_target_occupation(self, occupation: Optional[str], group_type: str) -> bool:
        """occupationが対象かチェック"""
        if not occupation:
            return False

        occupation_lower = occupation.lower()
        keywords = self.group_data.get("metadata", {}).get("rules", {}).get(
            "apply_to_occupation", {}
        ).get(group_type, [])

        for keyword in keywords:
            if keyword.lower() in occupation_lower:
                return True
        return False

    def find_group_for_member(self, member_name: str, occupation: Optional[str] = None) -> Optional[str]:
        """メンバー名からグループ名を特定"""
        normalized = self.normalize_name(member_name)

        # 完全一致を試す
        if normalized in self.member_to_group_map:
            group_name, group_type = self.member_to_group_map[normalized]
            # occupationチェック
            if occupation and self.is_target_occupation(occupation, group_type):
                return group_name
            elif not occupation:  # occupationがない場合はそのまま返す
                return group_name

        # 部分一致を試す
        for member_key, (group_name, group_type) in self.member_to_group_map.items():
            if normalized in member_key or member_key in normalized:
                if occupation and self.is_target_occupation(occupation, group_type):
                    return group_name
                elif not occupation:
                    return group_name

        return None

    def apply_group_rule(self, person_name: str, current_display: str, occupation: Optional[str] = None) -> str:
        """グループ名ルールを適用（YouTuber、お笑い芸人）"""
        # 既に括弧がある場合はそのまま返す
        if current_display and "(" in current_display and ")" in current_display:
            return current_display

        # グループ名を検索
        group_name = self.find_group_for_member(person_name, occupation)

        if group_name:
            return f"{person_name} ({group_name})"

        # グループに属さない場合（ピン芸人、個人YouTuber）はそのまま
        return current_display if current_display else person_name


class AutoDisplayNameFixer:
    """自動表示名修正エンジン"""

    def __init__(self):
        """初期化"""
        self.band_processor = BandNameProcessor()
        self.fictional_processor = FictionalCharacterProcessor()
        self.group_processor = GroupProcessor()
        self.fix_log = []

    def is_hiragana_only(self, text: str) -> bool:
        """
        テキストがひらがな（とスペース）のみかチェック
        Args:
            text: チェック対象のテキスト
        Returns:
            ひらがなのみの場合True
        """
        if not text:
            return False

        # スペースを除いてチェック
        text_no_space = text.replace(' ', '').replace('　', '')

        # ひらがなの範囲: \u3040-\u309F
        # 「ー」も許可
        return all(
            '\u3040' <= char <= '\u309F' or char == 'ー'
            for char in text_no_space
        )

    def should_fix_display_name(self, person_name: str, display_name: str) -> bool:
        """
        表示名を修正すべきか判定
        Args:
            person_name: person_name列の値
            display_name: person_name_display列の値
        Returns:
            修正が必要な場合True
        """
        # display_nameが空の場合
        if not display_name or display_name.strip() == '':
            return True

        # display_nameがひらがなのみの場合
        if self.is_hiragana_only(display_name):
            # person_nameに漢字やカタカナが含まれていれば修正対象
            if person_name and not self.is_hiragana_only(person_name):
                return True

        return False

    def fix_display_name(self, person_name: str, current_display: str, occupation: Optional[str] = None) -> str:
        """
        表示名を修正
        Args:
            person_name: person_name列の値
            current_display: 現在のperson_name_display列の値
            occupation: occupation列の値（架空キャラクター判定用）
        Returns:
            修正後の表示名
        """
        # 修正が必要かチェック
        if not self.should_fix_display_name(person_name, current_display):
            # バンド名処理は常に適用
            display = self.band_processor.apply_band_name_rule(person_name, current_display)
            # 既に括弧がある場合は後続処理をスキップ
            if "(" in display and ")" in display:
                return display
            # グループ処理（YouTuber、お笑い芸人）
            display = self.group_processor.apply_group_rule(person_name, display, occupation)
            # 既に括弧がある場合は後続処理をスキップ
            if "(" in display and ")" in display:
                return display
            # 架空キャラクター処理も適用
            return self.fictional_processor.apply_fictional_rule(person_name, display, occupation)

        # person_nameを基本の表示名として使用
        base_display = person_name.strip() if person_name else current_display

        # バンドメンバーの場合はバンド名を追加
        display = self.band_processor.apply_band_name_rule(person_name, base_display)
        # 既に括弧がある場合は後続処理をスキップ
        if "(" in display and ")" in display:
            return display

        # グループメンバー（YouTuber、お笑い芸人）の場合はグループ名を追加
        display = self.group_processor.apply_group_rule(person_name, display, occupation)
        # 既に括弧がある場合は後続処理をスキップ
        if "(" in display and ")" in display:
            return display

        # 架空キャラクターの場合は作品名を追加
        final_display: str = self.fictional_processor.apply_fictional_rule(person_name, display, occupation)

        return final_display

    def process_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict]:
        """
        DataFrameの表示名を修正
        Args:
            df: 処理対象のDataFrame
        Returns:
            (処理後のDataFrame, 統計情報)
        """
        stats = {
            'total_rows': len(df),
            'hiragana_fixed': 0,
            'empty_fixed': 0,
            'band_names_added': 0
        }

        for idx, row in df.iterrows():
            person_name = str(row.get('person_name', '')).strip()
            current_display = str(row.get('person_name_display', '')).strip()
            occupation = str(row.get('occupation', '')).strip()

            # 修正前の状態を記録
            original_display = current_display

            # 表示名を修正
            new_display = self.fix_display_name(person_name, current_display, occupation)

            # 変更があった場合
            if new_display != original_display:
                df.at[idx, 'person_name_display'] = new_display

                # 統計を更新
                if not original_display:
                    stats['empty_fixed'] += 1
                elif self.is_hiragana_only(original_display):
                    stats['hiragana_fixed'] += 1

                # バンド名が追加された場合
                if '(' in new_display and ')' in new_display:
                    if '(' not in original_display:
                        stats['band_names_added'] += 1

                # ログに記録
                self.fix_log.append({
                    'person_name': person_name,
                    'original_display': original_display,
                    'new_display': new_display,
                    'reason': self.get_fix_reason(person_name, original_display)
                })

        return df, stats

    def get_fix_reason(self, person_name: str, original_display: str) -> str:
        """修正理由を取得"""
        reasons = []

        if not original_display:
            reasons.append("空のdisplay_name")
        elif self.is_hiragana_only(original_display):
            reasons.append("ひらがなのみ")

        return ", ".join(reasons) if reasons else "その他"

    def fix_google_sheets(self):
        """Google Sheetsの表示名を修正"""
        print("🔄 表示名自動修正処理開始")
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
            backup_file = f"backup_before_display_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(backup_file, index=False, encoding='utf-8')
            print(f"   ✅ バックアップ: {backup_file}")

            # 表示名を修正
            print("\n4️⃣ 表示名修正中...")
            df, stats = self.process_dataframe(df)

            # 修正があった場合のみ更新
            total_fixed = stats['hiragana_fixed'] + stats['empty_fixed'] + stats['band_names_added']
            if total_fixed > 0:
                print(f"   ✅ {total_fixed}件の表示名を修正")
                print(f"      - ひらがな修正: {stats['hiragana_fixed']}件")
                print(f"      - 空欄修正: {stats['empty_fixed']}件")
                print(f"      - バンド名追加: {stats['band_names_added']}件")

                # Google Sheetsを更新
                print("\n5️⃣ Google Sheets更新中...")
                worksheet.clear()
                updated_data = [headers] + df.values.tolist()
                worksheet.update(updated_data, range_name='A1')

                # ローカルCSVも更新
                print("\n6️⃣ ローカルCSV更新中...")
                csv_file = "ultra_think_NO_FAKE_RESEARCHERS_20250827_143418.csv"
                df.to_csv(csv_file, index=False, encoding='utf-8')

                # 修正レポート作成
                self.create_fix_report(stats)

                print("\n" + "=" * 60)
                print("✨ 表示名修正完了！")

            else:
                print("\n✅ 修正対象なし（すべての表示名が正常です）")

            return stats

        except Exception as e:
            print(f"\n❌ エラー: {e}")
            import traceback
            traceback.print_exc()
            return None

    def create_fix_report(self, stats: Dict):
        """修正レポートを作成"""
        report = f"""# 表示名自動修正レポート
生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 統計
- 総データ数: {stats['total_rows']}件
- ひらがな修正: {stats['hiragana_fixed']}件
- 空欄修正: {stats['empty_fixed']}件
- バンド名追加: {stats['band_names_added']}件

## 修正詳細
"""

        for log in self.fix_log[:20]:  # 最初の20件のみ
            report += f"\n### {log['person_name']}\n"
            report += f"- 修正前: {log['original_display']}\n"
            report += f"- 修正後: {log['new_display']}\n"
            report += f"- 理由: {log['reason']}\n"

        if len(self.fix_log) > 20:
            report += f"\n... 他 {len(self.fix_log) - 20}件\n"

        # レポート保存
        report_file = f"DISPLAY_NAME_FIX_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        print(f"\n📝 レポート保存: {report_file}")








def apply_display_fix_to_new_data(person_data: Dict) -> Dict:
    """
    新規データに表示名修正ルールを適用
    Args:
        person_data: 人物データ
    Returns:
        処理後のデータ
    """
    fixer = AutoDisplayNameFixer()

    person_name = person_data.get('person_name', '')
    current_display = person_data.get('person_name_display', '')
    occupation = person_data.get('occupation', '')

    # 表示名を修正
    new_display = fixer.fix_display_name(person_name, current_display, occupation)
    person_data['person_name_display'] = new_display

    # 修正フラグを記録
    if new_display != current_display:
        person_data['display_fixed'] = True
        person_data['display_fixed_at'] = datetime.now().isoformat()

    return person_data


def test_display_fixer():
    """表示名修正テスト"""
    fixer = AutoDisplayNameFixer()

    test_cases = [
        {"person_name": "志村けん", "person_name_display": "しむら けん", "occupation": "コメディアン"},
        {"person_name": "加藤茶", "person_name_display": "かとう ちゃ", "occupation": "コメディアン"},
        {"person_name": "いかりや長介", "person_name_display": "いかりや ちょうすけ", "occupation": "コメディアン"},
        {"person_name": "仲本工事", "person_name_display": "なかもと こうじ", "occupation": "コメディアン"},
        {"person_name": "高木ブー", "person_name_display": "たかぎ ぶー", "occupation": "コメディアン"},
        {"person_name": "松本人志", "person_name_display": "松本人志", "occupation": "お笑い芸人"},
        {"person_name": "浜田雅功", "person_name_display": "浜田雅功", "occupation": "お笑い芸人"},
        {"person_name": "明石家さんま", "person_name_display": "明石家さんま", "occupation": "お笑い芸人"},
        {"person_name": "てつや", "person_name_display": "てつや", "occupation": "YouTuber"},
        {"person_name": "HIKAKIN", "person_name_display": "HIKAKIN", "occupation": "YouTuber"},
        {"person_name": "エレン・イェーガー", "person_name_display": "エレン・イェーガー", "occupation": "架空キャラクター"},
        {"person_name": "田中太郎", "person_name_display": "", "occupation": ""},  # 空欄のケース
        {"person_name": "山田花子", "person_name_display": "山田花子", "occupation": "女優"},  # 正常なケース
    ]

    print("🧪 表示名修正テスト")
    print("=" * 60)

    for test in test_cases:
        person_name = test['person_name']
        current_display = test['person_name_display']
        occupation = test.get('occupation', '')
        new_display = fixer.fix_display_name(person_name, current_display, occupation)

        print(f"人物名: {person_name}")
        print(f"職業: {occupation}")
        print(f"修正前: {current_display}")
        print(f"修正後: {new_display}")
        print(f"要修正: {fixer.should_fix_display_name(person_name, current_display)}")
        print("-" * 40)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_display_fixer()
    else:
        # 実行
        fixer = AutoDisplayNameFixer()
        fixer.fix_google_sheets()
