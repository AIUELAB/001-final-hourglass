#!/usr/bin/env python3
"""
曖昧な名前解決システム
同名の芸人を識別し、正しいグループ名を付与する
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import shutil

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AmbiguousNameResolver:
    """曖昧な名前解決クラス"""

    def __init__(self):
        """初期化"""
        self.ambiguous_comedians = {}
        self.resolution_report = []
        self.backup_created = []

        # 曖昧な芸人名とその可能性のあるグループ
        self.ambiguous_names = {
            '村上': [
                {
                    'group': 'マヂカルラブリー',
                    'partner': '野田クリスタル',
                    'birth_year': 1980,
                    'full_name': '村上',
                    'note': 'M-1グランプリ2020優勝'
                },
                {
                    'group': 'Aマッソ',
                    'current_name': 'むらきゃみ',
                    'old_name': '村上',
                    'partner': '加納',
                    'birth_year': 1988,
                    'full_name': '村上愛',
                    'note': '2024年2月に「むらきゃみ」に改名'
                }
            ],
            '田中': [
                {
                    'group': '爆笑問題',
                    'partner': '太田光',
                    'full_name': '田中裕二'
                },
                {
                    'group': 'アンガールズ',
                    'partner': '山根良顕',
                    'full_name': '田中卓志'
                }
            ],
            '山田': [
                {
                    'group': 'かまいたち',
                    'partner': '濱家隆一',
                    'full_name': '山内健司',
                    'note': '山田は誤記の可能性'
                }
            ]
        }

        # グループ識別のための追加情報
        self.group_context = {
            'マヂカルラブリー': {
                'formation_year': 2007,
                'agency': '吉本興業',
                'achievements': ['M-1グランプリ2020優勝', 'キングオブコント2022準優勝'],
                'members': ['野田クリスタル', '村上']
            },
            'Aマッソ': {
                'formation_year': 2010,
                'agency': 'ワタナベエンターテインメント',
                'achievements': ['THE W 2020-2022 3年連続決勝'],
                'members': ['むらきゃみ（旧：村上）', '加納']
            }
        }

    def analyze_context(self, row: pd.Series) -> Dict:
        """
        レコードのコンテキストを分析して所属グループを推定
        """
        context = {
            'person_id': row.get('person_id', ''),
            'person_name': row.get('person_name', ''),
            'birth_year': row.get('birth_year', None),
            'metadata': {}
        }

        # metadataフィールドがある場合は解析
        if 'metadata' in row and pd.notna(row['metadata']):
            try:
                metadata = json.loads(row['metadata']) if isinstance(row['metadata'], str) else row['metadata']
                context['metadata'] = metadata
            except:
                pass

        # calibration_dataから追加情報を取得
        if 'calibration_data' in row and pd.notna(row['calibration_data']):
            try:
                cal_data = json.loads(row['calibration_data']) if isinstance(row['calibration_data'], str) else row['calibration_data']
                context['calibration_data'] = cal_data
            except:
                pass

        return context

    def identify_comedian(self, row: pd.Series) -> Optional[Dict]:
        """
        曖昧な名前の芸人を特定
        """
        person_name = row.get('person_name', '')

        if person_name not in self.ambiguous_names:
            return None

        context = self.analyze_context(row)
        candidates = self.ambiguous_names[person_name]

        # 特定ロジック
        best_match = None
        highest_score = 0

        for candidate in candidates:
            score = 0

            # 生年が一致する場合は高スコア
            if 'birth_year' in candidate and context.get('birth_year'):
                if abs(candidate['birth_year'] - context['birth_year']) <= 2:
                    score += 50

            # metadataに相方の名前が含まれている場合
            if 'partner' in candidate and context.get('metadata'):
                metadata_str = str(context['metadata']).lower()
                if candidate['partner'].lower() in metadata_str:
                    score += 40

            # original_batch_idで判別
            if context.get('metadata', {}).get('original_batch_id') == 'massive_comedians':
                # コメディアンのバッチから来ている
                score += 10

            if score > highest_score:
                highest_score = score
                best_match = candidate

        # スコアが閾値以上の場合のみ返す
        if highest_score >= 10:
            return best_match

        return None

    def resolve_ambiguous_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        曖昧な名前を解決
        """
        df_resolved = df.copy()
        resolved_count = 0

        for idx, row in df.iterrows():
            person_name = row.get('person_name', '')
            display_name = row.get('person_name_display', '')

            # すでにグループ名が付いている場合はスキップ
            if '（' in str(display_name) and '）' in str(display_name):
                continue

            # 曖昧な名前の場合
            if person_name in self.ambiguous_names:
                identified = self.identify_comedian(row)

                if identified:
                    # 現在の芸名を使用
                    if 'current_name' in identified:
                        new_display = f"{identified['current_name']}（{identified['group']}）"
                    else:
                        new_display = f"{person_name}（{identified['group']}）"

                    df_resolved.loc[idx, 'person_name_display'] = new_display

                    self.resolution_report.append({
                        'person_id': row.get('person_id', ''),
                        'original_name': person_name,
                        'identified_as': identified['group'],
                        'new_display': new_display,
                        'confidence': 'medium',  # 完全な特定は困難
                        'note': identified.get('note', ''),
                        'timestamp': datetime.now().isoformat()
                    })

                    resolved_count += 1
                    logger.info(f"  🔍 特定: {person_name} → {identified['group']}")
                    logger.info(f"     新表示: {new_display}")
                else:
                    # 特定できない場合は警告
                    logger.warning(f"  ⚠️ 特定不能: {row.get('person_id', '')} {person_name}")
                    self.resolution_report.append({
                        'person_id': row.get('person_id', ''),
                        'original_name': person_name,
                        'identified_as': 'UNKNOWN',
                        'new_display': display_name,
                        'confidence': 'low',
                        'note': '追加情報が必要',
                        'timestamp': datetime.now().isoformat()
                    })

        logger.info(f"  ✅ {resolved_count}件の曖昧な名前を解決")
        return df_resolved

    def create_backup(self, file_path: str) -> str:
        """
        バックアップファイルを作成
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_path = f"{file_path}.backup_{timestamp}"

        shutil.copy2(file_path, backup_path)
        self.backup_created.append(backup_path)
        logger.info(f"  📦 バックアップ作成: {backup_path}")

        return backup_path

    def process_csv_file(self, file_path: str) -> bool:
        """
        CSVファイルを処理
        """
        logger.info(f"\n🔧 処理開始: {file_path}")

        if not Path(file_path).exists():
            logger.warning(f"  ⚠️ ファイルが存在しません: {file_path}")
            return False

        try:
            # バックアップ作成
            self.create_backup(file_path)

            # データ読み込み
            df = pd.read_csv(file_path, encoding='utf-8-sig')
            logger.info(f"  📊 データ読み込み完了: {len(df)}行")

            # 曖昧な名前を解決
            df_resolved = self.resolve_ambiguous_names(df)

            # ファイル保存（UTF-8 BOM付き）
            df_resolved.to_csv(file_path, index=False, encoding='utf-8-sig')
            logger.info(f"  💾 修正済みファイル保存完了")

            return True

        except Exception as e:
            logger.error(f"  ❌ エラー発生: {e}")
            return False

    def generate_resolution_strategy(self) -> Dict:
        """
        曖昧な名前を解決するための戦略を生成
        """
        strategy = {
            'immediate_actions': [
                '1. 既存データのmetadataフィールドを活用した文脈分析',
                '2. 相方の名前や所属事務所情報からの推定',
                '3. 生年月日や活動期間からの絞り込み'
            ],
            'future_improvements': [
                '1. person_idに事務所コードを含める（例: P003625_YSM for 吉本）',
                '2. グループIDフィールドの追加（group_id）',
                '3. 相方IDフィールドの追加（partner_ids）',
                '4. 活動期間フィールドの追加（active_from, active_to）',
                '5. Wikipedia URLやSNS IDなどの一意識別子の追加'
            ],
            'data_quality_rules': [
                '1. 新規登録時は必ずグループ名を含めた表示名で登録',
                '2. 同名の芸人が存在する場合は識別情報を必須とする',
                '3. 改名した芸人は新旧両方の名前を記録',
                '4. グループメンバーは相互参照可能にする'
            ],
            'validation_process': [
                '1. 定期的な曖昧性チェック（月次）',
                '2. Wikipedia等の外部ソースとの照合',
                '3. グループメンバーの整合性確認',
                '4. 改名履歴の追跡と更新'
            ]
        }

        return strategy


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🎯 曖昧な名前解決システム起動")
    logger.info("=" * 60)

    resolver = AmbiguousNameResolver()

    # 曖昧な名前の詳細表示
    logger.info("📋 曖昧な名前のリスト:")
    for name, candidates in resolver.ambiguous_names.items():
        logger.info(f"  {name}:")
        for candidate in candidates:
            if 'current_name' in candidate:
                logger.info(f"    - {candidate['group']}: {candidate['old_name']} → {candidate['current_name']}")
            else:
                logger.info(f"    - {candidate['group']}: {candidate.get('full_name', name)}")

    # 処理対象ファイルリスト
    target_files = [
        'ultra_think_GROUP_FIXED_20250912_044856.csv',
        'ultra_think_COMPLETE_20250912_042500.csv',
        'ultra_think_FINAL_CLEAN_20250912_042742_FICTIONAL_FIXED_FICTIONAL_COMPLETE.csv',
        'ultra_think_FINAL_CLEAN_20250912_042742.csv',
        'ultra_think_COMPREHENSIVE_FIX_20250912_071739.csv'
    ]

    # 存在するファイルのみ処理
    existing_files = []
    for file_path in target_files:
        if Path(file_path).exists():
            existing_files.append(file_path)

    if not existing_files:
        logger.warning("処理対象ファイルが見つかりません")
        return

    logger.info(f"\n処理対象: {len(existing_files)}ファイル")

    # 各ファイルを処理
    success_count = 0
    for file_path in existing_files:
        if resolver.process_csv_file(file_path):
            success_count += 1

    # 解決戦略の生成
    strategy = resolver.generate_resolution_strategy()

    # レポート生成
    report = {
        'timestamp': datetime.now().isoformat(),
        'resolution_report': resolver.resolution_report,
        'backups_created': resolver.backup_created,
        'resolution_strategy': strategy,
        'summary': {
            'total_ambiguous_names': len(resolver.ambiguous_names),
            'processed_files': success_count,
            'resolutions': len([r for r in resolver.resolution_report if r['identified_as'] != 'UNKNOWN']),
            'unresolved': len([r for r in resolver.resolution_report if r['identified_as'] == 'UNKNOWN'])
        }
    }

    # レポート保存
    report_path = f"ambiguous_name_resolution_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    # 結果表示
    logger.info("\n" + "=" * 60)
    logger.info("📋 解決結果サマリー")
    logger.info("=" * 60)
    logger.info(f"✅ 処理成功: {success_count}/{len(existing_files)}ファイル")
    logger.info(f"🔍 解決済み: {report['summary']['resolutions']}件")
    logger.info(f"⚠️ 未解決: {report['summary']['unresolved']}件")

    # 解決戦略の表示
    logger.info("\n🎯 今後の改善提案:")
    logger.info("\n即座に実施可能な対策:")
    for action in strategy['immediate_actions']:
        logger.info(f"  {action}")

    logger.info("\n将来的な改善案:")
    for improvement in strategy['future_improvements']:
        logger.info(f"  {improvement}")

    logger.info(f"\n📁 レポート保存: {report_path}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
