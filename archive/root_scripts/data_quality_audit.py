#!/usr/bin/env python3
"""
データ品質監査スクリプト
既存データの品質問題を効率的に検出・レポート
"""

import csv
import json
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Tuple


class DataQualityAuditor:
    """データ品質監査クラス"""

    def __init__(self):
        self.issues = defaultdict(list)
        self.stats = defaultdict(int)

    def audit_data(self, data: Dict[str, Dict]) -> Dict:
        """データの品質監査を実行"""

        total_count = len(data)
        self.stats['total_records'] = total_count

        for key, person in data.items():
            # 1. 未翻訳チェック
            self._check_translation(key, person)

            # 2. カテゴリー不整合チェック
            self._check_category_consistency(key, person)

            # 3. 表示名の適切性チェック
            self._check_display_name(key, person)

            # 4. 必須フィールドチェック
            self._check_required_fields(key, person)

            # 5. 既知の誤分類パターンチェック
            self._check_known_misclassifications(key, person)

        return self._generate_report()

    def _check_translation(self, key: str, person: Dict):
        """日本語翻訳のチェック"""
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

    def _check_category_consistency(self, key: str, person: Dict):
        """カテゴリーの整合性チェック"""
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
                break

    def _check_display_name(self, key: str, person: Dict):
        """表示名の適切性チェック"""
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
            except:
                pass

    def _check_required_fields(self, key: str, person: Dict):
        """必須フィールドのチェック"""
        required = ['person_name', 'person_name_ja', 'person_name_display']

        for field in required:
            if field not in person or not person[field]:
                self.issues['missing_field'].append({
                    'id': key,
                    'field': field,
                    'name': person.get('person_name', '')
                })
                self.stats['missing_field_count'] += 1

    def _check_known_misclassifications(self, key: str, person: Dict):
        """既知の誤分類パターンチェック"""
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

    def _generate_report(self) -> Dict:
        """監査レポートの生成"""
        return {
            'summary': {
                'total_records': self.stats['total_records'],
                'issues_found': sum(len(v) for v in self.issues.values()),
                'untranslated': self.stats.get('untranslated_count', 0),
                'category_mismatches': self.stats.get('category_mismatch_count', 0),
                'display_name_issues': self.stats.get('display_name_issue_count', 0),
                'missing_fields': self.stats.get('missing_field_count', 0),
                'known_misclassifications': self.stats.get('known_misclassification_count', 0)
            },
            'details': dict(self.issues)
        }

def generate_html_report(report: Dict, filename: str = 'quality_report.html'):
    """HTML形式のレポート生成"""
    html = f"""
    <!DOCTYPE html>
    <html lang="ja">
    <head>
        <meta charset="UTF-8">
        <title>データ品質監査レポート</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            .summary {{ background: #f0f0f0; padding: 15px; border-radius: 5px; }}
            .issue-section {{ margin: 20px 0; }}
            .issue-list {{ background: #fff; padding: 10px; border: 1px solid #ddd; }}
            .error {{ color: red; }}
            .warning {{ color: orange; }}
            .info {{ color: blue; }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
        </style>
    </head>
    <body>
        <h1>データ品質監査レポート</h1>
        <p>生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>

        <div class="summary">
            <h2>サマリー</h2>
            <ul>
                <li>総レコード数: {report['summary']['total_records']:,}</li>
                <li class="error">検出された問題: {report['summary']['issues_found']:,}件</li>
                <li>未翻訳: {report['summary']['untranslated']:,}件</li>
                <li>カテゴリー不整合: {report['summary']['category_mismatches']:,}件</li>
                <li>表示名問題: {report['summary']['display_name_issues']:,}件</li>
                <li>必須フィールド欠落: {report['summary']['missing_fields']:,}件</li>
                <li>既知の誤分類: {report['summary']['known_misclassifications']:,}件</li>
            </ul>
        </div>
    """

    # 未翻訳の詳細
    if 'untranslated' in report['details'] and report['details']['untranslated']:
        html += """
        <div class="issue-section">
            <h2>未翻訳の英語名（上位20件）</h2>
            <table>
                <tr><th>ID</th><th>名前</th><th>カテゴリー</th></tr>
        """
        for item in report['details']['untranslated'][:20]:
            html += f"""
                <tr>
                    <td>{item['id']}</td>
                    <td>{item['name']}</td>
                    <td>{item['category']}</td>
                </tr>
            """
        html += "</table></div>"

    # カテゴリー不整合の詳細
    if 'category_mismatch' in report['details'] and report['details']['category_mismatch']:
        html += """
        <div class="issue-section">
            <h2>カテゴリー不整合</h2>
            <table>
                <tr><th>ID</th><th>名前</th><th>職業</th><th>誤カテゴリー</th></tr>
        """
        for item in report['details']['category_mismatch']:
            html += f"""
                <tr>
                    <td>{item['id']}</td>
                    <td>{item['name']}</td>
                    <td>{item['occupation']}</td>
                    <td class="error">{item['wrong_category']}</td>
                </tr>
            """
        html += "</table></div>"

    # 既知の誤分類
    if 'known_misclassification' in report['details'] and report['details']['known_misclassification']:
        html += """
        <div class="issue-section">
            <h2>既知の誤分類</h2>
            <table>
                <tr><th>名前</th><th>Wikidata ID</th><th>現在</th><th>正しいカテゴリー</th></tr>
        """
        for item in report['details']['known_misclassification']:
            html += f"""
                <tr>
                    <td>{item['name']}</td>
                    <td>{item['wikidata_id']}</td>
                    <td class="error">{item['current']}</td>
                    <td class="info">{item['correct']}</td>
                </tr>
            """
        html += "</table></div>"

    html += """
    </body>
    </html>
    """

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html)

    return filename

def main():
    """メイン処理"""
    print("=" * 60)
    print("データ品質監査")
    print("=" * 60)

    # データ読み込み
    input_file = 'final_12410_firebase_20250822_201828.json'
    print(f"📂 データ読み込み中: {input_file}")

    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 監査実行
    print("🔍 品質監査実行中...")
    auditor = DataQualityAuditor()
    report = auditor.audit_data(data)

    # レポート保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # JSON形式
    json_file = f'quality_audit_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"✅ JSONレポート: {json_file}")

    # HTML形式
    html_file = f'quality_audit_{timestamp}.html'
    generate_html_report(report, html_file)
    print(f"✅ HTMLレポート: {html_file}")

    # コンソール出力
    print("\n" + "=" * 60)
    print("📊 監査結果サマリー")
    print("=" * 60)
    print(f"総レコード数: {report['summary']['total_records']:,}")
    print(f"検出された問題: {report['summary']['issues_found']:,}件")
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

    if quality_score < 70:
        print("⚠️ 品質スコアが低いです。データ修正が必要です。")
    elif quality_score < 90:
        print("📝 品質改善の余地があります。")
    else:
        print("✅ 良好な品質です。")

    return report

if __name__ == "__main__":
    main()
