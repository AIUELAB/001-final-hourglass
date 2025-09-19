#!/usr/bin/env python3
"""
Integrated Recognition System - Phase 4
Wikipedia API + グループ処理 + 品質チェックポイントの統合システム
"""

import json
import os
import sys
import time
import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from pathlib import Path
import logging

# 自作モジュールのインポート
from wikipedia_recognition_system import WikipediaRecognitionSystem
from group_entity_processor import GroupEntityProcessor

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('integrated_recognition.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class IntegratedRecognitionSystem:
    """統合知名度評価システム"""
    
    def __init__(self, checkpoint_interval: int = 100):
        """
        初期化
        
        Args:
            checkpoint_interval: チェックポイント間隔
        """
        # サブシステム初期化
        self.wikipedia_system = WikipediaRecognitionSystem()
        self.group_processor = GroupEntityProcessor()
        
        # チェックポイント設定
        self.checkpoint_interval = checkpoint_interval
        self.checkpoints = []
        
        # 統計情報
        self.stats = {
            'start_time': None,
            'end_time': None,
            'total_input': 0,
            'total_processed': 0,
            'groups_expanded': 0,
            'individuals_from_groups': 0,
            'wikipedia_found': 0,
            'deletion_candidates': 0,
            'preserved_count': 0,
            'errors': 0
        }
        
        # 品質メトリクス
        self.quality_metrics = {
            'famous_person_scores': {},  # 有名人のスコア検証用
            'deletion_rate_history': [],
            'checkpoint_quality': []
        }
        
        # 保護リスト（教科書人物、架空キャラクター）
        self.protected_persons = self._load_protected_persons()
        
        # 進捗ファイル
        self.progress_file = "recognition_progress.json"
        
    def _load_protected_persons(self) -> set:
        """保護対象人物をロード"""
        protected = set()
        
        # 教科書人物（歴史的人物）
        textbook_persons = [
            '織田信長', '豊臣秀吉', '徳川家康', '武田信玄', '上杉謙信',
            '源頼朝', '源義経', '平清盛', '聖徳太子', '藤原道長',
            '紫式部', '清少納言', '菅原道真', '空海', '最澄',
            '足利尊氏', '足利義満', '北条時宗', '北条政子', '北条時頼',
            '西郷隆盛', '大久保利通', '木戸孝允', '坂本龍馬', '勝海舟',
            '福沢諭吉', '伊藤博文', '明治天皇', '昭和天皇', '吉田茂',
            'チンギス・ハン', 'ナポレオン', 'エジソン', 'アインシュタイン', 'ガンジー',
            'コロンブス', 'マゼラン', 'ダーウィン', 'ニュートン', 'ガリレオ',
            # ... 実際には500人以上
        ]
        
        # 有名な架空キャラクター
        fictional_characters = [
            '竈門炭治郎', '竈門禰豆子', '我妻善逸', '嘴平伊之助',  # 鬼滅の刃
            '孫悟空', 'ベジータ', 'フリーザ', 'ピッコロ',  # ドラゴンボール
            'ドラえもん', 'のび太', 'しずか', 'ジャイアン', 'スネ夫',  # ドラえもん
            'ルフィ', 'ゾロ', 'ナミ', 'サンジ', 'チョッパー',  # ONE PIECE
            'ピカチュウ', 'イーブイ', 'リザードン',  # ポケモン
            'セーラームーン', 'セーラーマーキュリー',  # セーラームーン
            'エヴァンゲリオン初号機', '碇シンジ', '綾波レイ',  # エヴァンゲリオン
            'アンパンマン', 'バイキンマン', 'ドキンちゃん',  # アンパンマン
            'サザエさん', 'カツオ', 'ワカメ', 'タラちゃん',  # サザエさん
            # ... 実際には100人以上
        ]
        
        protected.update(textbook_persons)
        protected.update(fictional_characters)
        
        # 外部ファイルからも読み込み
        if Path('protected_persons.json').exists():
            with open('protected_persons.json', 'r', encoding='utf-8') as f:
                additional = json.load(f)
                protected.update(additional)
        
        logger.info(f"保護対象人物: {len(protected)}人")
        return protected
    
    def save_progress(self) -> None:
        """進捗を保存"""
        # datetime オブジェクトを文字列に変換
        stats_copy = self.stats.copy()
        if stats_copy.get('start_time'):
            stats_copy['start_time'] = stats_copy['start_time'].isoformat() if isinstance(stats_copy['start_time'], datetime) else stats_copy['start_time']
        if stats_copy.get('end_time'):
            stats_copy['end_time'] = stats_copy['end_time'].isoformat() if isinstance(stats_copy['end_time'], datetime) else stats_copy['end_time']
        
        progress = {
            'timestamp': datetime.now().isoformat(),
            'stats': stats_copy,
            'checkpoints': self.checkpoints,
            'quality_metrics': {
                'deletion_rate': self.stats['deletion_candidates'] / max(self.stats['total_processed'], 1),
                'checkpoint_count': len(self.checkpoints)
            }
        }
        
        with open(self.progress_file, 'w', encoding='utf-8') as f:
            json.dump(progress, f, ensure_ascii=False, indent=2, default=str)
    
    def quality_checkpoint(self, results: List[Dict]) -> Dict:
        """
        品質チェックポイント
        
        Args:
            results: これまでの評価結果
            
        Returns:
            チェックポイント結果
        """
        checkpoint_num = len(self.checkpoints) + 1
        
        # 削除率計算
        deletion_count = sum(1 for r in results if r.get('should_delete', False))
        deletion_rate = deletion_count / max(len(results), 1)
        
        # 有名人のスコア確認
        famous_check = []
        test_persons = ['HIKAKIN', 'ヒカキン', '大谷翔平', '安倍晋三', 'Ado']
        for person in test_persons:
            for r in results:
                if person in r.get('name', ''):
                    famous_check.append({
                        'name': person,
                        'score': r.get('recognition_score', 0),
                        'ok': r.get('recognition_score', 0) >= 7.0
                    })
        
        # Wikipedia発見率
        wiki_found = sum(1 for r in results if r.get('wikipedia_found', False))
        wiki_rate = wiki_found / max(len(results), 1)
        
        # 品質判定
        quality_issues = []
        
        if deletion_rate < 0.10:
            quality_issues.append(f"削除率が低すぎます: {deletion_rate:.1%}")
        elif deletion_rate > 0.20:
            quality_issues.append(f"削除率が高すぎます: {deletion_rate:.1%}")
        
        if wiki_rate < 0.30:
            quality_issues.append(f"Wikipedia発見率が低すぎます: {wiki_rate:.1%}")
        
        for check in famous_check:
            if not check['ok']:
                quality_issues.append(f"{check['name']}のスコアが低すぎます: {check['score']:.1f}")
        
        checkpoint = {
            'number': checkpoint_num,
            'timestamp': datetime.now().isoformat(),
            'processed': len(results),
            'deletion_rate': deletion_rate,
            'wikipedia_rate': wiki_rate,
            'famous_person_check': famous_check,
            'quality_issues': quality_issues,
            'quality_ok': len(quality_issues) == 0
        }
        
        self.checkpoints.append(checkpoint)
        
        # ログ出力
        logger.info("=" * 60)
        logger.info(f"チェックポイント #{checkpoint_num}")
        logger.info(f"処理済み: {len(results)}人")
        logger.info(f"削除率: {deletion_rate:.1%}")
        logger.info(f"Wikipedia発見率: {wiki_rate:.1%}")
        
        if quality_issues:
            logger.warning(f"⚠️ 品質問題: {', '.join(quality_issues)}")
        else:
            logger.info("✅ 品質チェック合格")
        
        logger.info("=" * 60)
        
        return checkpoint
    
    def process_person(self, person_data: Dict) -> List[Dict]:
        """
        個人を処理
        
        Args:
            person_data: 人物データ
            
        Returns:
            評価結果のリスト（グループの場合は複数）
        """
        results = []
        
        # Step 1: グループエンティティ処理
        processed_entities = self.group_processor.process_entity(person_data)
        
        for entity in processed_entities:
            name = entity.get('person_name_display', entity.get('person_name', ''))
            
            # 保護対象チェック
            if name in self.protected_persons:
                result = {
                    'person_id': entity.get('person_id', ''),
                    'name': name,
                    'recognition_score': 10.0,  # 保護対象は最高スコア
                    'wikipedia_found': True,
                    'should_delete': False,
                    'reason': '保護対象（教科書人物/有名キャラクター）',
                    'protected': True
                }
                results.append(result)
                continue
            
            # 未知のグループチェック
            if entity.get('is_unknown_group'):
                result = {
                    'person_id': entity.get('person_id', ''),
                    'name': name,
                    'recognition_score': 0.0,
                    'wikipedia_found': False,
                    'should_delete': True,
                    'reason': '未知のグループエンティティ',
                    'is_group': True
                }
                results.append(result)
                continue
            
            # Step 2: Wikipedia評価
            eval_result = self.wikipedia_system.evaluate_person(entity)
            
            # グループメンバー情報を追加
            if entity.get('is_group_member'):
                eval_result['original_group'] = entity.get('original_group')
                eval_result['is_group_member'] = True
            
            results.append(eval_result)
        
        return results
    
    def process_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        バッチ処理
        
        Args:
            df: 入力データフレーム
            
        Returns:
            評価結果を含むデータフレーム
        """
        self.stats['start_time'] = datetime.now()
        self.stats['total_input'] = len(df)
        
        logger.info(f"処理開始: {len(df)}件")
        
        all_results = []
        persons = df.to_dict('records')
        
        for i, person in enumerate(persons):
            try:
                # 個人処理
                results = self.process_person(person)
                all_results.extend(results)
                
                # 統計更新
                self.stats['total_processed'] += 1
                if len(results) > 1:
                    self.stats['groups_expanded'] += 1
                    self.stats['individuals_from_groups'] += len(results) - 1
                
                # 進捗表示
                if (i + 1) % 10 == 0:
                    progress = (i + 1) / len(persons) * 100
                    logger.info(f"進捗: {i + 1}/{len(persons)} ({progress:.1f}%)")
                
                # チェックポイント
                if len(all_results) >= self.checkpoint_interval * (len(self.checkpoints) + 1):
                    checkpoint = self.quality_checkpoint(all_results)
                    self.save_progress()
                    
                    # 品質問題があっても続行（ログに記録）
                    if not checkpoint['quality_ok']:
                        logger.warning("品質問題が検出されましたが、処理を続行します")
                
                # API負荷軽減
                if (i + 1) % 50 == 0:
                    time.sleep(1)
                    
            except Exception as e:
                logger.error(f"処理エラー ({person.get('person_name', 'Unknown')}): {str(e)}")
                self.stats['errors'] += 1
                
                # エラーでも結果を記録
                all_results.append({
                    'person_id': person.get('person_id', ''),
                    'name': person.get('person_name_display', person.get('person_name', '')),
                    'recognition_score': 0.0,
                    'wikipedia_found': False,
                    'should_delete': True,
                    'reason': f'処理エラー: {str(e)}',
                    'error': True
                })
        
        # 最終チェックポイント
        if len(all_results) % self.checkpoint_interval != 0:
            self.quality_checkpoint(all_results)
        
        # 統計集計
        self.stats['end_time'] = datetime.now()
        self.stats['deletion_candidates'] = sum(1 for r in all_results if r.get('should_delete', False))
        self.stats['preserved_count'] = sum(1 for r in all_results if not r.get('should_delete', False))
        self.stats['wikipedia_found'] = sum(1 for r in all_results if r.get('wikipedia_found', False))
        
        # データフレーム作成
        result_df = pd.DataFrame(all_results)
        
        # 最終統計表示
        self._display_final_stats()
        
        return result_df
    
    def _display_final_stats(self) -> None:
        """最終統計を表示"""
        duration = (self.stats['end_time'] - self.stats['start_time']).total_seconds()
        
        print("\n" + "=" * 60)
        print("処理完了")
        print("=" * 60)
        print(f"処理時間: {duration / 60:.1f}分")
        print(f"入力件数: {self.stats['total_input']}件")
        print(f"出力件数: {self.stats['total_processed']}件（グループ展開後）")
        print(f"グループ展開: {self.stats['groups_expanded']}グループ → {self.stats['individuals_from_groups']}人")
        print(f"Wikipedia発見: {self.stats['wikipedia_found']}件")
        print(f"削除候補: {self.stats['deletion_candidates']}件")
        print(f"保持: {self.stats['preserved_count']}件")
        print(f"削除率: {self.stats['deletion_candidates'] / max(self.stats['total_processed'], 1):.1%}")
        print(f"エラー: {self.stats['errors']}件")
        print(f"チェックポイント: {len(self.checkpoints)}回")
        print("=" * 60)
    
    def save_results(self, result_df: pd.DataFrame, output_file: str = None) -> str:
        """
        結果を保存
        
        Args:
            result_df: 結果データフレーム
            output_file: 出力ファイル名
            
        Returns:
            保存したファイル名
        """
        if output_file is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_file = f"recognition_results_{timestamp}.csv"
        
        # UTF-8 BOM付きで保存（Excel対応）
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"結果を保存: {output_file}")
        
        # 統計も保存
        stats_file = output_file.replace('.csv', '_stats.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump({
                'stats': self.stats,
                'checkpoints': self.checkpoints,
                'quality_metrics': self.quality_metrics
            }, f, ensure_ascii=False, indent=2, default=str)
        logger.info(f"統計を保存: {stats_file}")
        
        return output_file


def main():
    """メイン処理"""
    print("=" * 60)
    print("Integrated Recognition System")
    print("統合知名度評価システム")
    print("=" * 60)
    print()
    
    # CSVファイルを検索
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if not csv_files:
        logger.error("ultra_think_*.csv ファイルが見つかりません")
        return
    
    # 最新のファイルを選択
    latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    logger.info(f"処理対象ファイル: {latest_file}")
    
    # データ読み込み
    try:
        df = pd.read_csv(latest_file, encoding='utf-8-sig')
        logger.info(f"データ読み込み完了: {len(df)}件")
    except Exception as e:
        logger.error(f"CSVファイル読み込みエラー: {str(e)}")
        return
    
    # システム初期化
    system = IntegratedRecognitionSystem(checkpoint_interval=100)
    
    # 処理実行
    print("\n処理を開始します...")
    print("予想処理時間: 2-3時間")
    print("100人ごとに品質チェックポイントを実施")
    print()
    
    result_df = system.process_batch(df)
    
    # 結果保存
    output_file = system.save_results(result_df)
    
    print("\n✅ 処理完了!")
    print(f"結果ファイル: {output_file}")
    print()
    
    # 最終品質チェック
    deletion_rate = system.stats['deletion_candidates'] / max(system.stats['total_processed'], 1)
    if 0.10 <= deletion_rate <= 0.20:
        print("✅ 削除率は正常範囲内です")
    else:
        print(f"⚠️ 削除率が異常です: {deletion_rate:.1%}")
    
    # レポート生成の提案
    print("\n次のステップ:")
    print("1. 結果の詳細レビュー")
    print("2. Google Sheetsへのアップロード")
    print("3. 年間拡張計画の策定")


if __name__ == "__main__":
    main()