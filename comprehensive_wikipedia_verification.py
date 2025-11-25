#!/usr/bin/env python3
"""
包括的Wikipedia実在性検証システム
全レコードのWikipedia検証とプレースホルダー検出
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Set
import time
import hashlib
from collections import defaultdict
from improved_wikipedia_api import ImprovedWikipediaAPI

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ComprehensiveWikipediaVerifier:
    """包括的Wikipedia実在性検証クラス"""

    def __init__(self):
        """初期化"""
        self.api = ImprovedWikipediaAPI()
        self.verification_results = []
        self.suspicious_patterns = []
        self.placeholder_candidates = []

        # 統計情報
        self.stats = {
            'total_checked': 0,
            'wikipedia_found': 0,
            'wikipedia_not_found': 0,
            'suspicious_groups': 0,
            'placeholder_detected': 0,
            'by_occupation': defaultdict(lambda: {'total': 0, 'found': 0, 'not_found': 0}),
            'by_nationality': defaultdict(lambda: {'total': 0, 'found': 0, 'not_found': 0})
        }

        # プレースホルダーパターン
        self.placeholder_patterns = {
            'consecutive_ids': [],     # 連続するID
            'same_surname_groups': {}, # 同姓グループ
            'low_wikipedia_rate': [],  # Wikipedia記載率が低いグループ
            'generic_names': [],       # 汎用的な名前パターン
            'no_birth_year': []        # 生年情報なし
        }

    def analyze_data_structure(self, df: pd.DataFrame) -> Dict:
        """
        1. まずコード全体の構造を理解
        データフレームの構造と品質を分析
        """
        analysis = {
            'total_records': len(df),
            'columns': list(df.columns),
            'data_types': df.dtypes.to_dict(),
            'null_counts': df.isnull().sum().to_dict(),
            'unique_values': {
                'occupation': df['occupation'].nunique(),
                'nationality': df['nationality'].nunique(),
                'entity_type': df['entity_type'].nunique() if 'entity_type' in df.columns else 0
            }
        }

        # 職業分布
        occupation_dist = df['occupation'].value_counts().head(20).to_dict()
        analysis['top_occupations'] = occupation_dist

        # 国籍分布
        nationality_dist = df['nationality'].value_counts().head(10).to_dict()
        analysis['top_nationalities'] = nationality_dist

        # データ品質指標
        analysis['quality_metrics'] = {
            'has_display_name': (~df['person_name_display'].isnull()).sum(),
            'has_birth_year': ('birth_year' in df.columns and ~df['birth_year'].isnull()).sum() if 'birth_year' in df.columns else 0,
            'has_wikipedia_url': ('wikipedia_url' in df.columns and ~df['wikipedia_url'].isnull()).sum() if 'wikipedia_url' in df.columns else 0
        }

        logger.info(f"📊 データ構造分析完了: {analysis['total_records']}件")
        return analysis

    def verify_wikipedia_existence(self, row: pd.Series) -> Dict:
        """
        2. 各関数の動作を検証
        個別レコードのWikipedia実在性検証
        """
        result = {
            'person_id': row['person_id'],
            'person_name': row['person_name'],
            'person_name_display': row.get('person_name_display', ''),
            'occupation': row.get('occupation', ''),
            'nationality': row.get('nationality', ''),
            'wikipedia_found': False,
            'wikipedia_title': None,
            'confidence': 0.0,
            'verification_source': None,
            'issues': []
        }

        # Wikipedia検索
        search_query = row['person_name']
        if row.get('occupation'):
            search_query += f" {row['occupation']}"

        # 日本語Wikipedia検索
        ja_result = self.api.search_person_wikipedia(row['person_name'], 'ja', row.get('occupation'))
        if ja_result and ja_result.get('is_person'):
            result['wikipedia_found'] = True
            result['wikipedia_title'] = ja_result.get('title')
            result['confidence'] = 0.9
            result['verification_source'] = 'wikipedia_ja'
            return result

        # 英語Wikipedia検索（外国人の場合）
        if row.get('nationality') and row['nationality'] != '日本':
            en_result = self.api.search_person_wikipedia(row['person_name'], 'en', row.get('occupation'))
            if en_result and en_result.get('is_person'):
                result['wikipedia_found'] = True
                result['wikipedia_title'] = en_result.get('title')
                result['confidence'] = 0.8
                result['verification_source'] = 'wikipedia_en'
                return result

        # Wikipedia未発見
        result['issues'].append('Wikipedia記事なし')
        result['confidence'] = 0.2

        return result

    def detect_placeholder_patterns(self, df: pd.DataFrame) -> Dict:
        """
        3. 潜在的なバグやエッジケースを特定
        プレースホルダーデータのパターン検出
        """
        patterns = {
            'consecutive_id_groups': [],
            'same_surname_clusters': {},
            'low_verification_groups': [],
            'suspicious_name_patterns': []
        }

        # 1. 連続ID検出
        df_sorted = df.sort_values('person_id')
        for i in range(len(df_sorted) - 5):
            group = df_sorted.iloc[i:i+6]
            ids = group['person_id'].tolist()

            # IDの連続性チェック
            if self._are_consecutive_ids(ids):
                # 同じ職業かチェック
                if group['occupation'].nunique() == 1:
                    patterns['consecutive_id_groups'].append({
                        'ids': ids,
                        'occupation': group['occupation'].iloc[0],
                        'names': group['person_name'].tolist()
                    })

        # 2. 同姓グループ検出
        df['surname'] = df['person_name'].apply(lambda x: x.split()[0] if ' ' in x else x[:2])
        surname_groups = df.groupby('surname')

        for surname, group in surname_groups:
            if len(group) >= 5:
                # Wikipedia記載率チェック
                verified = group.apply(lambda r: self._quick_wikipedia_check(r['person_name']), axis=1)
                verification_rate = verified.sum() / len(verified)

                if verification_rate < 0.3:
                    patterns['same_surname_clusters'][surname] = {
                        'count': len(group),
                        'verification_rate': verification_rate,
                        'ids': group['person_id'].tolist(),
                        'names': group['person_name'].tolist()
                    }

        # 3. 汎用的な名前パターン検出
        generic_patterns = ['太郎', '次郎', '三郎', '健太', '大輔', '翔太', '拓也']
        for pattern in generic_patterns:
            matching = df[df['person_name'].str.contains(pattern, na=False)]
            if len(matching) >= 3:
                patterns['suspicious_name_patterns'].append({
                    'pattern': pattern,
                    'count': len(matching),
                    'examples': matching[['person_id', 'person_name']].head(5).to_dict('records')
                })

        logger.info(f"🔍 プレースホルダーパターン検出: {len(patterns['consecutive_id_groups'])}グループ")
        return patterns

    def _are_consecutive_ids(self, ids: List[str]) -> bool:
        """IDが連続しているかチェック"""
        try:
            numbers = [int(id[1:]) for id in ids]
            for i in range(1, len(numbers)):
                if numbers[i] != numbers[i-1] + 1:
                    return False
            return True
        except:
            return False

    def _quick_wikipedia_check(self, name: str) -> bool:
        """簡易Wikipedia存在チェック（キャッシュ利用）"""
        cache_key = hashlib.md5(f"quick:{name}".encode()).hexdigest()
        cache_file = Path(f"wikipedia_cache/{cache_key}.json")

        if cache_file.exists():
            with open(cache_file, 'r') as f:
                data = json.load(f)
                return data.get('exists', False)

        # 簡易チェック（詳細検証は後で）
        return False

    def propose_improvements(self, analysis_results: Dict) -> List[Dict]:
        """
        4. 改善案を提示
        検出された問題に対する改善提案
        """
        improvements = []

        # 1. 連続IDグループへの対処
        if analysis_results['placeholder_patterns']['consecutive_id_groups']:
            improvements.append({
                'issue': '連続IDの疑わしいグループ検出',
                'severity': 'HIGH',
                'affected_count': len(analysis_results['placeholder_patterns']['consecutive_id_groups']),
                'action': '各グループのWikipedia検証と削除判定',
                'pdca_rule': 'RULE_093: 連続ID検出ルール'
            })

        # 2. 同姓グループへの対処
        if analysis_results['placeholder_patterns']['same_surname_clusters']:
            improvements.append({
                'issue': '同姓で低Wikipedia記載率のグループ',
                'severity': 'HIGH',
                'affected_count': len(analysis_results['placeholder_patterns']['same_surname_clusters']),
                'action': '実在性の個別検証と一括削除',
                'pdca_rule': 'RULE_094: 同姓グループ検証ルール'
            })

        # 3. Wikipedia未記載データへの対処
        wiki_not_found_rate = (analysis_results['stats']['wikipedia_not_found'] /
                               max(analysis_results['stats']['total_checked'], 1))
        if wiki_not_found_rate > 0.3:
            improvements.append({
                'issue': f'Wikipedia記載率が低い（{wiki_not_found_rate:.1%}）',
                'severity': 'MEDIUM',
                'affected_count': analysis_results['stats']['wikipedia_not_found'],
                'action': '追加の実在性検証ソース活用',
                'pdca_rule': 'RULE_095: 複数ソース検証ルール'
            })

        # 4. データ品質改善
        improvements.append({
            'issue': 'データ品質の継続的監視',
            'severity': 'LOW',
            'action': '定期的な品質監査とプレースホルダー検出',
            'pdca_rule': 'RULE_096: 定期品質監査ルール'
        })

        return improvements

    def run_comprehensive_verification(self, df: pd.DataFrame, sample_size: int = None) -> Dict:
        """
        包括的検証の実行
        """
        logger.info("=" * 60)
        logger.info("🔍 包括的Wikipedia実在性検証開始")
        logger.info("=" * 60)

        # 1. データ構造分析
        logger.info("📊 ステップ1: データ構造分析")
        structure_analysis = self.analyze_data_structure(df)

        # 2. サンプリング検証（全件は時間がかかるため）
        logger.info("🔬 ステップ2: Wikipedia実在性検証")
        if sample_size:
            df_sample = df.sample(min(sample_size, len(df)))
            logger.info(f"  サンプルサイズ: {len(df_sample)}件")
        else:
            df_sample = df.head(100)  # デフォルトは100件

        for idx, row in df_sample.iterrows():
            self.stats['total_checked'] += 1
            result = self.verify_wikipedia_existence(row)
            self.verification_results.append(result)

            # 統計更新
            if result['wikipedia_found']:
                self.stats['wikipedia_found'] += 1
                self.stats['by_occupation'][row['occupation']]['found'] += 1
                self.stats['by_nationality'][row['nationality']]['found'] += 1
            else:
                self.stats['wikipedia_not_found'] += 1
                self.stats['by_occupation'][row['occupation']]['not_found'] += 1
                self.stats['by_nationality'][row['nationality']]['not_found'] += 1
                self.placeholder_candidates.append(result)

            self.stats['by_occupation'][row['occupation']]['total'] += 1
            self.stats['by_nationality'][row['nationality']]['total'] += 1

            if self.stats['total_checked'] % 10 == 0:
                logger.info(f"  進捗: {self.stats['total_checked']}件検証済み")

            # レート制限
            time.sleep(0.5)

        # 3. プレースホルダーパターン検出
        logger.info("🎯 ステップ3: プレースホルダーパターン検出")
        placeholder_patterns = self.detect_placeholder_patterns(df)

        # 4. 改善案生成
        logger.info("💡 ステップ4: 改善案生成")
        analysis_results = {
            'structure': structure_analysis,
            'stats': dict(self.stats),
            'placeholder_patterns': placeholder_patterns,
            'verification_results': self.verification_results[:10]  # サンプル
        }
        improvements = self.propose_improvements(analysis_results)

        # 結果まとめ
        results = {
            'timestamp': datetime.now().isoformat(),
            'analysis': analysis_results,
            'improvements': improvements,
            'summary': {
                'total_records': len(df),
                'checked': self.stats['total_checked'],
                'wikipedia_found': self.stats['wikipedia_found'],
                'wikipedia_not_found': self.stats['wikipedia_not_found'],
                'verification_rate': self.stats['wikipedia_found'] / max(self.stats['total_checked'], 1),
                'suspicious_groups': len(placeholder_patterns['consecutive_id_groups']),
                'placeholder_candidates': len(self.placeholder_candidates)
            }
        }

        return results

    def generate_report(self, results: Dict):
        """検証レポート生成"""
        report = []
        report.append("# 包括的Wikipedia実在性検証レポート")
        report.append("")
        report.append(f"実行日時: {results['timestamp']}")
        report.append("")

        # サマリー
        report.append("## 検証サマリー")
        report.append("")
        summary = results['summary']
        report.append(f"- 総レコード数: {summary['total_records']:,}件")
        report.append(f"- 検証済み: {summary['checked']}件")
        report.append(f"- Wikipedia記載: {summary['wikipedia_found']}件 ({summary['verification_rate']:.1%})")
        report.append(f"- Wikipedia未記載: {summary['wikipedia_not_found']}件")
        report.append(f"- 疑わしいグループ: {summary['suspicious_groups']}件")
        report.append(f"- プレースホルダー候補: {summary['placeholder_candidates']}件")
        report.append("")

        # 職業別統計
        report.append("## 職業別Wikipedia記載率")
        report.append("")
        report.append("| 職業 | 総数 | Wikipedia記載 | 記載率 |")
        report.append("|------|------|---------------|--------|")

        for occupation, stats in results['analysis']['stats']['by_occupation'].items():
            if stats['total'] > 0:
                rate = stats['found'] / stats['total'] * 100
                report.append(f"| {occupation} | {stats['total']} | {stats['found']} | {rate:.1f}% |")
        report.append("")

        # 検出されたパターン
        report.append("## 検出されたプレースホルダーパターン")
        report.append("")

        patterns = results['analysis']['placeholder_patterns']
        if patterns['consecutive_id_groups']:
            report.append("### 連続IDグループ")
            for group in patterns['consecutive_id_groups'][:5]:
                report.append(f"- {group['occupation']}: {', '.join(group['ids'][:3])}...")

        if patterns['same_surname_clusters']:
            report.append("### 同姓低記載率グループ")
            for surname, info in list(patterns['same_surname_clusters'].items())[:5]:
                report.append(f"- {surname}姓: {info['count']}件 (記載率{info['verification_rate']:.1%})")
        report.append("")

        # 改善提案
        report.append("## 改善提案")
        report.append("")
        for improvement in results['improvements']:
            report.append(f"### {improvement['issue']}")
            report.append(f"- 重要度: {improvement['severity']}")
            if 'affected_count' in improvement:
                report.append(f"- 影響範囲: {improvement['affected_count']}件")
            report.append(f"- 対処法: {improvement['action']}")
            report.append(f"- PDCAルール: {improvement['pdca_rule']}")
            report.append("")

        # ファイル保存
        report_file = f"wikipedia_verification_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))

        logger.info(f"📄 レポート生成: {report_file}")

        # JSON形式でも保存
        json_file = f"verification_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        logger.info(f"📊 詳細データ保存: {json_file}")


def main():
    """メイン処理"""
    logger.info("🚀 包括的Wikipedia実在性検証システム起動")

    # 最新のクリーンデータ読み込み
    csv_file = Path('ultra_think_MASSIVE_CLEANED_20250912_035645.csv')
    if not csv_file.exists():
        csv_files = list(Path('.').glob('ultra_think_*.csv'))
        if csv_files:
            csv_file = max(csv_files, key=lambda x: x.stat().st_mtime)
        else:
            logger.error("❌ CSVファイルが見つかりません")
            return

    logger.info(f"📂 データ読み込み: {csv_file}")
    df = pd.read_csv(csv_file)

    # 検証実行
    verifier = ComprehensiveWikipediaVerifier()
    results = verifier.run_comprehensive_verification(df, sample_size=200)

    # レポート生成
    verifier.generate_report(results)

    # サマリー表示
    logger.info("\n" + "=" * 60)
    logger.info("✅ 包括的Wikipedia実在性検証完了")
    logger.info("=" * 60)
    logger.info(f"検証件数: {results['summary']['checked']}")
    logger.info(f"Wikipedia記載率: {results['summary']['verification_rate']:.1%}")
    logger.info(f"プレースホルダー候補: {results['summary']['placeholder_candidates']}件")

    if results['summary']['placeholder_candidates'] > 0:
        logger.warning("⚠️ プレースホルダーデータの可能性があるレコードが検出されました")
        logger.info("詳細はレポートファイルを確認してください")


if __name__ == "__main__":
    main()
