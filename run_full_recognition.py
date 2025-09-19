#!/usr/bin/env python3
"""
Run Full Recognition System
4,701件の完全処理実行スクリプト
"""

import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
from integrated_recognition_system import IntegratedRecognitionSystem
import sys

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """完全処理実行"""
    print("=" * 60)
    print("統合知名度評価システム - 完全処理")
    print("Wikipedia API中心の客観的評価")
    print("=" * 60)
    print()
    
    # 処理対象ファイル
    target_file = "ultra_think_RANKED_20250907_161756.csv"
    
    if not Path(target_file).exists():
        logger.error(f"ファイルが見つかりません: {target_file}")
        return
    
    logger.info(f"処理対象ファイル: {target_file}")
    
    # データ読み込み
    try:
        df = pd.read_csv(target_file, encoding='utf-8-sig')
        logger.info(f"データ読み込み完了: {len(df)}件")
        
        # 必須フィールドチェック
        required_fields = ['person_name', 'person_name_display']
        missing_fields = [f for f in required_fields if f not in df.columns]
        if missing_fields:
            logger.error(f"必須フィールドが不足: {missing_fields}")
            return
        
    except Exception as e:
        logger.error(f"CSVファイル読み込みエラー: {str(e)}")
        return
    
    # システム初期化
    system = IntegratedRecognitionSystem(checkpoint_interval=100)
    
    # 処理時間見積もり
    print("\n" + "=" * 60)
    print("処理概要:")
    print(f"  - 入力データ: {len(df)}件")
    print(f"  - 処理方式: Wikipedia API（レート制限なし）")
    print(f"  - チェックポイント: 100人ごと")
    print(f"  - 予想処理時間: 2-3時間")
    print(f"  - 削除率目標: 10-20%")
    print("=" * 60)
    
    # 確認
    print("\n処理を開始しますか？ (y/n): ", end='')
    response = input().strip().lower()
    
    if response != 'y':
        print("処理をキャンセルしました")
        return
    
    # 処理開始時刻
    start_time = datetime.now()
    print(f"\n処理開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()
    
    # 処理実行
    try:
        result_df = system.process_batch(df)
        
        # 結果保存
        output_file = system.save_results(result_df)
        
        # 処理時間計算
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("✅ 処理完了!")
        print("=" * 60)
        print(f"処理時間: {duration / 60:.1f}分")
        print(f"結果ファイル: {output_file}")
        print()
        
        # 品質チェック結果
        deletion_rate = system.stats['deletion_candidates'] / max(system.stats['total_processed'], 1)
        
        if 0.10 <= deletion_rate <= 0.20:
            print("✅ 削除率は正常範囲内です: {:.1%}".format(deletion_rate))
        else:
            print("⚠️ 削除率が異常範囲です: {:.1%}".format(deletion_rate))
            print("   （正常範囲: 10-20%）")
        
        # チェックポイントサマリー
        quality_issues_count = sum(
            1 for cp in system.checkpoints 
            if not cp.get('quality_ok', True)
        )
        
        if quality_issues_count > 0:
            print(f"⚠️ {quality_issues_count}回の品質問題が検出されました")
            print("   詳細は recognition_progress.json を確認してください")
        else:
            print("✅ すべてのチェックポイントで品質基準をクリア")
        
        print("\n" + "=" * 60)
        print("次のステップ:")
        print("1. 結果ファイルの詳細レビュー")
        print("2. 削除候補の最終確認")
        print("3. Google Sheetsへのアップロード")
        print("4. 年間拡張計画の策定（月1,100人ペース）")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\n処理が中断されました")
        print("進捗は recognition_progress.json に保存されています")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {str(e)}")
        print("\n❌ エラーが発生しました")
        print("詳細はログファイル integrated_recognition.log を確認してください")
        sys.exit(1)


if __name__ == "__main__":
    main()