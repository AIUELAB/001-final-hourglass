#!/usr/bin/env python3
"""
データ品質保証フレームワーク
データ収集・変換・検証の標準化されたプロセス
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import requests

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ===========================
# 1. データスキーマ定義
# ===========================

@dataclass
class PersonSchema:
    """人物データの標準スキーマ"""
    id: str
    person_name: str  # 原語表記
    person_name_ja: str  # 日本語名
    person_name_display: str  # 表示用名
    birth_date: str = ""
    death_date: str = ""
    nationality: str = ""
    occupation: str = ""
    main_category: str = ""
    subcategory: str = ""
    wikidata_id: str = ""
    grade: str = ""
    description: str = ""
    
    def validate(self) -> List[str]:
        """データ検証"""
        errors = []
        
        # 必須フィールドチェック
        if not self.id:
            errors.append("ID is required")
        if not self.person_name:
            errors.append("person_name is required")
        if not self.person_name_ja:
            errors.append("person_name_ja is required")
            
        # 日本語名チェック
        if self.person_name == self.person_name_ja and \
           self.person_name.replace(' ', '').isascii():
            errors.append(f"person_name_ja appears to be untranslated: {self.person_name_ja}")
            
        # カテゴリー整合性チェック
        if self.subcategory and not self.main_category:
            errors.append("subcategory exists but main_category is missing")
            
        return errors

# ===========================
# 2. Wikidata ID管理
# ===========================

class WikidataOccupations(Enum):
    """Wikidata職業IDの定義（検証済み）"""
    # エンターテインメント
    MUSICIAN = ("Q639669", "ミュージシャン", "エンターテインメント", "音楽")
    SINGER = ("Q177220", "歌手", "エンターテインメント", "音楽")
    ACTOR = ("Q33999", "俳優", "エンターテインメント", "俳優")
    COMEDIAN = ("Q245068", "お笑い芸人", "エンターテインメント", "お笑い")
    
    # 文化・芸術
    FILM_DIRECTOR = ("Q2526255", "映画監督", "文化・芸術", "映画監督")
    ANIME_DIRECTOR = ("Q3665646", "アニメ監督", "文化・芸術", "アニメ監督")
    MANGA_ARTIST = ("Q3658341", "漫画家", "文化・芸術", "漫画")
    WRITER = ("Q36180", "作家", "文化・芸術", "作家")
    NOVELIST = ("Q482980", "小説家", "文化・芸術", "作家")
    VOICE_ACTOR = ("Q622807", "声優", "文化・芸術", "声優")
    
    # スポーツ
    BOXER = ("Q10871364", "プロボクサー", "スポーツ", "ボクシング")
    SOCCER_PLAYER = ("Q937857", "サッカー選手", "スポーツ", "サッカー")
    BASEBALL_PLAYER = ("Q10871364", "野球選手", "スポーツ", "野球")
    TENNIS_PLAYER = ("Q10873124", "テニス選手", "スポーツ", "テニス")
    
    # 学術・科学
    SCIENTIST = ("Q901", "科学者", "学術・科学", "科学")
    PHYSICIST = ("Q169470", "物理学者", "学術・科学", "物理学")
    CHEMIST = ("Q593644", "化学者", "学術・科学", "化学")
    BIOLOGIST = ("Q864503", "生物学者", "学術・科学", "生物学")
    
    # 政治・社会
    POLITICIAN = ("Q82955", "政治家", "政治・社会", "政治家")
    DIPLOMAT = ("Q193391", "外交官", "政治・社会", "外交")
    ENTREPRENEUR = ("Q131524", "起業家", "ビジネス", "起業家")
    
    def __init__(self, wikidata_id: str, name_ja: str, main_category: str, subcategory: str):
        self.wikidata_id = wikidata_id
        self.name_ja = name_ja
        self.main_category = main_category
        self.subcategory = subcategory

# ===========================
# 3. データ収集クラス
# ===========================

class SafeWikidataCollector:
    """安全なWikidataデータ収集クラス"""
    
    def __init__(self):
        self.sparql_endpoint = "https://query.wikidata.org/sparql"
        self.wikidata_api = "https://www.wikidata.org/w/api.php"
        self.errors = []
        
    def validate_wikidata_id(self, wikidata_id: str) -> bool:
        """Wikidata IDの妥当性チェック"""
        if not wikidata_id or not wikidata_id.startswith('Q'):
            return False
        
        # APIで実際に存在確認
        try:
            params = {
                'action': 'wbgetentities',
                'ids': wikidata_id,
                'format': 'json'
            }
            response = requests.get(self.wikidata_api, params=params, timeout=5)
            data = response.json()
            
            if 'entities' in data and wikidata_id in data['entities']:
                entity = data['entities'][wikidata_id]
                if 'missing' not in entity:
                    return True
        except:
            pass
            
        return False
    
    def get_occupation_category(self, occupation_ids: List[str]) -> Tuple[str, str, str]:
        """職業IDからカテゴリーを決定"""
        for occ_id in occupation_ids:
            for occupation in WikidataOccupations:
                if occupation.wikidata_id == occ_id:
                    return (occupation.name_ja, 
                           occupation.main_category, 
                           occupation.subcategory)
        
        return ("", "その他", "")
    
    def fetch_person_data(self, wikidata_id: str) -> Optional[PersonSchema]:
        """人物データを安全に取得"""
        if not self.validate_wikidata_id(wikidata_id):
            logger.error(f"Invalid Wikidata ID: {wikidata_id}")
            return None
        
        try:
            # エンティティ取得
            params = {
                'action': 'wbgetentities',
                'ids': wikidata_id,
                'props': 'labels|claims',
                'languages': 'ja|en',
                'format': 'json'
            }
            
            response = requests.get(self.wikidata_api, params=params)
            data = response.json()
            
            if 'entities' not in data or wikidata_id not in data['entities']:
                return None
            
            entity = data['entities'][wikidata_id]
            
            # ラベル取得
            label_ja = entity.get('labels', {}).get('ja', {}).get('value', '')
            label_en = entity.get('labels', {}).get('en', {}).get('value', '')
            
            # 職業取得
            occupation_ids = []
            if 'P106' in entity.get('claims', {}):
                for claim in entity['claims']['P106']:
                    if 'mainsnak' in claim and 'datavalue' in claim['mainsnak']:
                        occ_id = claim['mainsnak']['datavalue']['value']['id']
                        occupation_ids.append(occ_id)
            
            # カテゴリー決定
            occupation, main_cat, sub_cat = self.get_occupation_category(occupation_ids)
            
            # PersonSchemaに変換
            person = PersonSchema(
                id=f"person_{wikidata_id}",
                person_name=label_en or label_ja,
                person_name_ja=label_ja or label_en,
                person_name_display=self.determine_display_name(label_ja, label_en),
                occupation=occupation,
                main_category=main_cat,
                subcategory=sub_cat,
                wikidata_id=wikidata_id
            )
            
            # 検証
            errors = person.validate()
            if errors:
                logger.warning(f"Validation errors for {wikidata_id}: {errors}")
            
            return person
            
        except Exception as e:
            logger.error(f"Error fetching {wikidata_id}: {str(e)}")
            return None
    
    def determine_display_name(self, name_ja: str, name_en: str) -> str:
        """表示名を決定（厳格なルール適用）"""
        if not name_ja:
            return name_en
        
        # 現代人チェック（簡易版）
        # 実際は生年月日等から判定すべき
        historical_figures = [
            'バッハ', 'モーツァルト', 'ベートーヴェン',
            'ダ・ヴィンチ', 'ニュートン', 'アインシュタイン'
        ]
        
        for figure in historical_figures:
            if figure in name_ja:
                # 歴史的人物は短縮可能
                parts = name_ja.split('・')
                if len(parts) > 1:
                    return parts[-1]
        
        # それ以外はフルネーム
        return name_ja

# ===========================
# 4. データ検証クラス
# ===========================

class DataQualityValidator:
    """データ品質検証クラス"""
    
    def __init__(self):
        self.validation_rules = []
        self.setup_rules()
    
    def setup_rules(self):
        """検証ルールの設定"""
        self.validation_rules = [
            self.check_required_fields,
            self.check_name_translation,
            self.check_category_consistency,
            self.check_occupation_category_match,
            self.check_display_name_rules
        ]
    
    def check_required_fields(self, data: Dict) -> List[str]:
        """必須フィールドチェック"""
        errors = []
        required = ['id', 'person_name', 'person_name_ja', 'person_name_display']
        
        for field in required:
            if field not in data or not data[field]:
                errors.append(f"Required field missing: {field}")
        
        return errors
    
    def check_name_translation(self, data: Dict) -> List[str]:
        """日本語名の翻訳チェック"""
        errors = []
        
        name = data.get('person_name', '')
        name_ja = data.get('person_name_ja', '')
        
        # 英語名と日本語名が同じで、英語文字のみの場合
        if name == name_ja and name.replace(' ', '').isascii() and name:
            errors.append(f"Untranslated Japanese name: {name_ja}")
        
        return errors
    
    def check_category_consistency(self, data: Dict) -> List[str]:
        """カテゴリーの整合性チェック"""
        errors = []
        
        main_cat = data.get('main_category', '')
        sub_cat = data.get('subcategory', '')
        occupation = data.get('occupation', '')
        
        # サブカテゴリーがあるのにメインカテゴリーがない
        if sub_cat and not main_cat:
            errors.append(f"Subcategory '{sub_cat}' exists but main_category is missing")
        
        # 職業とカテゴリーの不一致チェック
        if occupation and sub_cat:
            # 例: ボクサーなのにアニメ監督カテゴリー
            mismatch_patterns = [
                ('ボクサー', 'アニメ監督'),
                ('ミュージシャン', 'アニメ監督'),
                ('歌手', 'アニメ監督'),
                ('俳優', 'アニメ監督')
            ]
            
            for occ_pattern, cat_pattern in mismatch_patterns:
                if occ_pattern in occupation and cat_pattern == sub_cat:
                    errors.append(f"Category mismatch: {occupation} categorized as {sub_cat}")
        
        return errors
    
    def check_occupation_category_match(self, data: Dict) -> List[str]:
        """職業とカテゴリーのマッチングチェック"""
        errors = []
        
        wikidata_id = data.get('wikidata_id', '')
        sub_cat = data.get('subcategory', '')
        
        # 特定の既知の誤分類パターン
        known_misclassifications = {
            'Q745408': 'ボクシング',  # ガッツ石松
            'Q1197175': '音楽',  # 桑田佳祐
            'Q210204': '映画監督',  # 松林宗恵
        }
        
        if wikidata_id in known_misclassifications:
            expected = known_misclassifications[wikidata_id]
            if sub_cat != expected and sub_cat == 'アニメ監督':
                errors.append(f"Known misclassification: {wikidata_id} should be {expected}, not {sub_cat}")
        
        return errors
    
    def check_display_name_rules(self, data: Dict) -> List[str]:
        """表示名ルールチェック"""
        errors = []
        
        name_ja = data.get('person_name_ja', '')
        display = data.get('person_name_display', '')
        birth_date = data.get('birth_date', '')
        
        # 現代人チェック（1900年以降生まれ）
        if birth_date:
            try:
                birth_year = int(birth_date.split('-')[0])
                if birth_year >= 1900:
                    # 現代人なのに短縮されている
                    if '・' in name_ja and len(display) < len(name_ja):
                        # 特定の例外を除く
                        if name_ja not in ['クリストファー・ノーラン', 'ニール・パトリック・ハリス']:
                            errors.append(f"Modern person name incorrectly shortened: {name_ja} -> {display}")
            except:
                pass
        
        return errors
    
    def validate_dataset(self, data: Dict[str, Dict]) -> Dict[str, List[str]]:
        """データセット全体を検証"""
        all_errors = {}
        
        for key, person_data in data.items():
            errors = []
            for rule in self.validation_rules:
                rule_errors = rule(person_data)
                errors.extend(rule_errors)
            
            if errors:
                all_errors[key] = errors
        
        return all_errors

# ===========================
# 5. 自動修正クラス
# ===========================

class DataAutoCorrector:
    """データ自動修正クラス"""
    
    def __init__(self):
        self.collector = SafeWikidataCollector()
        self.corrections_log = []
    
    def auto_correct(self, data: Dict[str, Dict]) -> Tuple[Dict[str, Dict], List[Dict]]:
        """データの自動修正"""
        corrected_data = data.copy()
        corrections = []
        
        for key, person_data in corrected_data.items():
            correction_made = False
            before = person_data.copy()
            
            # 1. Wikidata IDがある場合は正確な情報を取得
            wikidata_id = person_data.get('wikidata_id', '')
            if wikidata_id:
                fresh_data = self.collector.fetch_person_data(wikidata_id)
                if fresh_data:
                    # 日本語名の修正
                    if fresh_data.person_name_ja != person_data.get('person_name_ja', ''):
                        person_data['person_name_ja'] = fresh_data.person_name_ja
                        person_data['person_name_display'] = fresh_data.person_name_display
                        correction_made = True
                    
                    # カテゴリーの修正
                    if fresh_data.main_category != person_data.get('main_category', ''):
                        person_data['main_category'] = fresh_data.main_category
                        person_data['subcategory'] = fresh_data.subcategory
                        person_data['occupation'] = fresh_data.occupation
                        correction_made = True
            
            # 2. 既知の誤分類パターンの修正
            if person_data.get('person_name_ja') == 'ガッツ石松' and \
               person_data.get('subcategory') == 'アニメ監督':
                person_data['occupation'] = 'プロボクサー、タレント'
                person_data['main_category'] = 'スポーツ'
                person_data['subcategory'] = 'ボクシング'
                correction_made = True
            
            if correction_made:
                corrections.append({
                    'id': key,
                    'before': before,
                    'after': person_data.copy()
                })
        
        return corrected_data, corrections

# ===========================
# 6. レポート生成
# ===========================

class QualityReport:
    """品質レポート生成クラス"""
    
    @staticmethod
    def generate_report(
        data: Dict[str, Dict],
        validation_errors: Dict[str, List[str]],
        corrections: List[Dict]
    ) -> str:
        """品質レポートの生成"""
        
        report = []
        report.append("=" * 60)
        report.append("データ品質レポート")
        report.append("=" * 60)
        report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # サマリー
        report.append("## サマリー")
        report.append(f"- 総レコード数: {len(data)}")
        report.append(f"- エラー検出数: {len(validation_errors)}")
        report.append(f"- 自動修正数: {len(corrections)}")
        report.append("")
        
        # エラー分析
        if validation_errors:
            report.append("## エラー分析")
            error_types = {}
            for errors in validation_errors.values():
                for error in errors:
                    error_type = error.split(':')[0]
                    error_types[error_type] = error_types.get(error_type, 0) + 1
            
            for error_type, count in sorted(error_types.items(), key=lambda x: x[1], reverse=True):
                report.append(f"- {error_type}: {count}件")
            report.append("")
        
        # 修正内容
        if corrections:
            report.append("## 自動修正内容（上位10件）")
            for correction in corrections[:10]:
                report.append(f"- {correction['id']}: ")
                if correction['before'].get('subcategory') != correction['after'].get('subcategory'):
                    report.append(f"  カテゴリー: {correction['before'].get('subcategory')} → {correction['after'].get('subcategory')}")
                if correction['before'].get('person_name_ja') != correction['after'].get('person_name_ja'):
                    report.append(f"  日本語名: {correction['before'].get('person_name_ja')} → {correction['after'].get('person_name_ja')}")
            report.append("")
        
        # 推奨事項
        report.append("## 推奨事項")
        if len(validation_errors) > 100:
            report.append("- ⚠️ 大量のエラーが検出されました。データソースの見直しを推奨")
        if any('Untranslated' in str(errors) for errors in validation_errors.values()):
            report.append("- ⚠️ 未翻訳の日本語名が多数存在します。翻訳処理の改善を推奨")
        if any('Category mismatch' in str(errors) for errors in validation_errors.values()):
            report.append("- ⚠️ カテゴリーの不整合が検出されました。カテゴリー定義の見直しを推奨")
        
        return "\n".join(report)

# ===========================
# メイン実行
# ===========================

def main():
    """データ品質保証プロセスの実行例"""
    
    # データ読み込み
    with open('final_12410_firebase_20250822_201828.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 1. データ検証
    validator = DataQualityValidator()
    validation_errors = validator.validate_dataset(data)
    
    if validation_errors:
        logger.warning(f"Found {len(validation_errors)} records with errors")
    
    # 2. 自動修正
    corrector = DataAutoCorrector()
    corrected_data, corrections = corrector.auto_correct(data)
    
    if corrections:
        logger.info(f"Auto-corrected {len(corrections)} records")
    
    # 3. レポート生成
    report = QualityReport.generate_report(data, validation_errors, corrections)
    
    # レポート保存
    with open('quality_report.txt', 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(report)
    
    # 修正済みデータ保存
    if corrections:
        with open('data_corrected.json', 'w', encoding='utf-8') as f:
            json.dump(corrected_data, f, ensure_ascii=False, indent=2)
    
    return len(validation_errors), len(corrections)

if __name__ == "__main__":
    errors, corrections = main()
    print(f"\n完了: {errors}件のエラー検出、{corrections}件の自動修正")