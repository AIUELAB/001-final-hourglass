#!/usr/bin/env python3
"""
データ品質監査スクリプト（改善版）
重複カウントを防ぐ仕組みを追加
"""

import csv
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple


class ImprovedDataQualityAuditor:
    """改善されたデータ品質監査クラス"""

    def __init__(self):
        self.issues = defaultdict(list)
        self.stats = defaultdict(int)
        self.unique_issues = set()  # 重複カウント防止用

    def audit_data(self, data: Dict[str, Dict]) -> Dict:
        """データの品質監査を実行（重複カウント防止）"""

        total_count = len(data)
        self.stats['total_records'] = total_count

        for key, person in data.items():
            # エントリごとの問題フラグ
            entry_has_issue = False
            entry_issues = []

            # 1. 未翻訳チェック
            if self._check_translation(key, person):
                entry_has_issue = True
                entry_issues.append('untranslated')

            # 2. カテゴリー不整合チェック
            if self._check_category_consistency(key, person):
                entry_has_issue = True
                entry_issues.append('category_mismatch')

            # 3. 表示名の適切性チェック
            if self._check_display_name(key, person):
                entry_has_issue = True
                entry_issues.append('display_name')

            # 4. 必須フィールドチェック
            if self._check_required_fields(key, person):
                entry_has_issue = True
                entry_issues.append('missing_field')

            # 5. 既知の誤分類パターンチェック
            if self._check_known_misclassifications(key, person):
                entry_has_issue = True
                entry_issues.append('known_misclassification')

            # エントリごとに1回だけカウント
            if entry_has_issue:
                self.unique_issues.add(key)

        return self._generate_report()

    def _check_translation(self, key: str, person: Dict) -> bool:
        """日本語翻訳のチェック（True = 問題あり）"""
        name = person.get('person_name', '')
        name_ja = person.get('person_name_ja', '')

        # 英語名と日本語名が同じで、ASCII文字のみ
        if name == name_ja and name.replace(' ', '').isascii() and name:
            self.issues['untranslated'].append({
                'id': key,
                'name': name,
                'category': person.get('subcategory', '')
            })
            self.stats['untranslated_count'] += 1
            return True
        return False

    def _check_category_consistency(self, key: str, person: Dict) -> bool:
        """カテゴリーの整合性チェック（True = 問題あり）"""
        occupation = person.get('occupation', '')
        subcategory = person.get('subcategory', '')

        # 既知の不整合パターン
        mismatches = [
            ('ボクサー', 'アニメ監督'),
            ('ミュージシャン', 'アニメ監督'),
            ('歌手', 'アニメ監督'),
            ('俳優', 'アニメ監督'),
            ('プロボクサー', 'アニメ監督'),
        ]

        for occ_pattern, wrong_cat in mismatches:
            if occ_pattern in occupation and subcategory == wrong_cat:
                self.issues['category_mismatch'].append({
                    'id': key,
                    'name': person.get('person_name_ja', ''),
                    'occupation': occupation,
                    'wrong_category': subcategory
                })
                self.stats['category_mismatch_count'] += 1
                return True
        return False

    def _check_display_name(self, key: str, person: Dict) -> bool:
        """表示名の適切性チェック（True = 問題あり）"""
        name_ja = person.get('person_name_ja', '')
        display = person.get('person_name_display', '')
        birth_date = person.get('birth_date', '')

        # 現代人の判定（1900年以降生まれ）
        if birth_date:
            try:
                birth_year = int(birth_date.split('-')[0])
                if birth_year >= 1900:
                    # 中点があって短縮されている
                    if '・' in name_ja and len(display) < len(name_ja):
                        # 既知の歴史的人物は除外
                        historical = ['バッハ', 'モーツァルト', 'ベートーヴェン']
                        if not any(h in name_ja for h in historical):
                            self.issues['display_name'].append({
                                'id': key,
                                'full_name': name_ja,
                                'display': display,
                                'birth_year': birth_year
                            })
                            self.stats['display_name_issue_count'] += 1
                            return True
            except:
                pass
        return False

    def _check_required_fields(self, key: str, person: Dict) -> bool:
        """必須フィールドのチェック（True = 問題あり）"""
        required = ['person_name', 'person_name_ja', 'person_name_display']

        missing_fields = []
        for field in required:
            if field not in person or not person[field]:
                missing_fields.append(field)

        if missing_fields:
            self.issues['missing_field'].append({
                'id': key,
                'fields': missing_fields,
                'name': person.get('person_name', '')
            })
            self.stats['missing_field_count'] += len(missing_fields)
            return True
        return False

    def _check_known_misclassifications(self, key: str, person: Dict) -> bool:
        """既知の誤分類パターンチェック（True = 問題あり）"""
        wikidata_id = person.get('wikidata_id', '')
        subcategory = person.get('subcategory', '')

        # 既知の誤分類
        known_wrong = {
            'Q745408': ('ガッツ石松', 'ボクシング'),
            'Q1197175': ('桑田佳祐', '音楽'),
            'Q210204': ('松林宗恵', '映画監督'),
            'Q55403': ('大島渚', '映画監督'),
        }

        if wikidata_id in known_wrong and subcategory == 'アニメ監督':
            name, correct_cat = known_wrong[wikidata_id]
            self.issues['known_misclassification'].append({
                'id': key,
                'name': name,
                'wikidata_id': wikidata_id,
                'current': subcategory,
                'correct': correct_cat
            })
            self.stats['known_misclassification_count'] += 1
            return True
        return False

    def _generate_report(self) -> Dict:
        """監査レポートの生成（重複なし）"""
        # ユニークな問題件数を使用
        unique_issue_count = len(self.unique_issues)

        return {
            'summary': {
                'total_records': self.stats['total_records'],
                'issues_found': unique_issue_count,  # 重複を除いた件数
                'untranslated': self.stats.get('untranslated_count', 0),
                'category_mismatches': self.stats.get('category_mismatch_count', 0),
                'display_name_issues': self.stats.get('display_name_issue_count', 0),
                'missing_fields': self.stats.get('missing_field_count', 0),
                'known_misclassifications': self.stats.get('known_misclassification_count', 0)
            },
            'details': dict(self.issues),
            'affected_entries': list(self.unique_issues)  # 影響を受けたエントリのリスト
        }

class PriorityBasedAuditor(ImprovedDataQualityAuditor):
    """優先度ベースの監査クラス（上位の問題を優先）"""

    def audit_data_with_priority(self, data: Dict[str, Dict]) -> Dict:
        """優先度付き監査（既知の誤分類を最優先）"""

        total_count = len(data)
        self.stats['total_records'] = total_count

        for key, person in data.items():
            # 優先度順にチェック（高優先度の問題が見つかったら、それ以降はスキップ）

            # 優先度1: 既知の誤分類
            if self._check_known_misclassifications(key, person):
                self.unique_issues.add(key)
                continue  # 他のチェックをスキップ

            # 優先度2: カテゴリー不整合
            if self._check_category_consistency(key, person):
                self.unique_issues.add(key)
                continue

            # 優先度3: 未翻訳
            if self._check_translation(key, person):
                self.unique_issues.add(key)
                continue

            # 優先度4: 必須フィールド欠落
            if self._check_required_fields(key, person):
                self.unique_issues.add(key)
                continue

            # 優先度5: 表示名問題
            if self._check_display_name(key, person):
                self.unique_issues.add(key)
                continue

        return self._generate_report()

def generate_improvement_report(original_report: Dict, improved_report: Dict) -> str:
    """改善前後の比較レポート生成"""

    report = []
    report.append("=" * 60)
    report.append("データ品質監査改善レポート")
    report.append("=" * 60)
    report.append(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report.append("")

    report.append("## 改善のポイント")
    report.append("1. 重複カウントの防止")
    report.append("   - 同一エントリが複数の問題カテゴリーに該当する場合、1件としてカウント")
    report.append("2. 優先度ベースの問題検出")
    report.append("   - 既知の誤分類 > カテゴリー不整合 > 未翻訳 > 必須フィールド > 表示名")
    report.append("3. 影響エントリの明確化")
    report.append("   - 問題があるエントリのIDリストを提供")
    report.append("")

    if original_report and improved_report:
        report.append("## 改善前後の比較")
        report.append(f"- 改善前の問題件数: {original_report.get('summary', {}).get('issues_found', 0)}")
        report.append(f"- 改善後の問題件数: {improved_report.get('summary', {}).get('issues_found', 0)}")

        # 品質スコアの計算
        total = improved_report['summary']['total_records']
        issues = improved_report['summary']['issues_found']
        quality_score = ((total - issues) / total * 100) if total > 0 else 0
        report.append(f"- 品質スコア: {quality_score:.1f}%")

    return "\n".join(report)

def main():
    """メイン処理"""
    print("=" * 60)
    print("改善版データ品質監査")
    print("=" * 60)

    # データ読み込み
    input_file = 'final_12410_firebase_20250822_201828.json'
    print(f"📂 データ読み込み中: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 改善版監査実行
    print("🔍 改善版監査実行中...")
    auditor = ImprovedDataQualityAuditor()
    report = auditor.audit_data(data)

    # 優先度ベース監査実行
    print("🎯 優先度ベース監査実行中...")
    priority_auditor = PriorityBasedAuditor()
    priority_report = priority_auditor.audit_data_with_priority(data)

    # レポート保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # JSON形式
    json_file = f'improved_audit_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump({
            'standard': report,
            'priority_based': priority_report
        }, f, ensure_ascii=False, indent=2)
    print(f"✅ JSONレポート: {json_file}")

    # コンソール出力
    print("\n" + "=" * 60)
    print("📊 改善版監査結果サマリー")
    print("=" * 60)
    print(f"総レコード数: {report['summary']['total_records']:,}")
    print(f"問題のあるエントリ数: {report['summary']['issues_found']:,}件（重複除去済み）")
    print(f"  - 未翻訳: {report['summary']['untranslated']:,}件")
    print(f"  - カテゴリー不整合: {report['summary']['category_mismatches']:,}件")
    print(f"  - 表示名問題: {report['summary']['display_name_issues']:,}件")
    print(f"  - 必須フィールド欠落: {report['summary']['missing_fields']:,}件")
    print(f"  - 既知の誤分類: {report['summary']['known_misclassifications']:,}件")

    # 品質スコア計算
    total = report['summary']['total_records']
    issues = report['summary']['issues_found']
    quality_score = ((total - issues) / total * 100) if total > 0 else 0

    print(f"\n🎯 品質スコア: {quality_score:.1f}%")

    # 優先度ベースとの比較
    print("\n📊 優先度ベース監査との比較")
    print(f"標準監査: {report['summary']['issues_found']}件の問題")
    print(f"優先度ベース: {priority_report['summary']['issues_found']}件の問題")

    return report

if __name__ == "__main__":
    main()
