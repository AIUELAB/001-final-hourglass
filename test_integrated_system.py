#!/usr/bin/env python3
"""
Test Integrated System
統合システムのテスト実行（10人サンプル）
"""

import pandas as pd
from pathlib import Path
import logging
from integrated_recognition_system import IntegratedRecognitionSystem

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """テスト実行"""
    print("=" * 60)
    print("統合知名度評価システム - テスト実行")
    print("最初の10人でシステム動作確認")
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
    
    # データ読み込み（最初の10件のみ）
    try:
        df = pd.read_csv(latest_file, encoding='utf-8-sig', nrows=10)
        logger.info(f"テストデータ読み込み完了: {len(df)}件")
        
        # データ内容確認
        print("\n=== テストデータ ===")
        for i, row in df.iterrows():
            name = row.get('person_name_display', row.get('person_name', 'Unknown'))
            print(f"{i+1}. {name}")
        print()
        
    except Exception as e:
        logger.error(f"CSVファイル読み込みエラー: {str(e)}")
        return
    
    # システム初期化（チェックポイント間隔を短く）
    system = IntegratedRecognitionSystem(checkpoint_interval=5)
    
    # 処理実行
    print("テスト処理を開始します...")
    print()
    
    result_df = system.process_batch(df)
    
    # 結果表示
    print("\n=== テスト結果 ===")
    for i, row in result_df.iterrows():
        name = row.get('name', 'Unknown')
        score = row.get('recognition_score', 0)
        wiki = "○" if row.get('wikipedia_found', False) else "×"
        action = "削除" if row.get('should_delete', False) else "保持"
        reason = row.get('reason', '')
        
        print(f"{i+1}. {name}")
        print(f"   スコア: {score:.1f} | Wikipedia: {wiki} | 判定: {action}")
        print(f"   理由: {reason}")
        
        if row.get('is_group_member'):
            print(f"   (元グループ: {row.get('original_group', '')})")
        print()
    
    # 統計表示
    print("=== 統計情報 ===")
    deletion_count = sum(1 for _, r in result_df.iterrows() if r.get('should_delete', False))
    print(f"削除候補: {deletion_count}/{len(result_df)} ({deletion_count/max(len(result_df), 1)*100:.1f}%)")
    
    wiki_count = sum(1 for _, r in result_df.iterrows() if r.get('wikipedia_found', False))
    print(f"Wikipedia発見: {wiki_count}/{len(result_df)} ({wiki_count/max(len(result_df), 1)*100:.1f}%)")
    
    # 結果保存
    test_output = "test_recognition_results.csv"
    result_df.to_csv(test_output, index=False, encoding='utf-8-sig')
    print(f"\nテスト結果を保存: {test_output}")
    
    print("\n✅ テスト完了!")
    print("\n全データ（4,701件）の処理を実行する場合は:")
    print("python3 integrated_recognition_system.py")


if __name__ == "__main__":
    main()