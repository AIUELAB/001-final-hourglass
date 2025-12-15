#!/usr/bin/env python3
"""
Run Full Recognition System (Auto)
4,701件の完全処理実行スクリプト（自動実行版）
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
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_recognition.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """完全処理実行（自動）"""
    print("=" * 60)
    print("統合知名度評価システム - 完全処理（自動実行）")
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

    # 処理開始時刻
    start_time = datetime.now()
    print(f"\n🚀 自動処理開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # 最初の100件だけ処理（デモンストレーション用）
    print("⚠️ デモモード: 最初の100件のみ処理します")
    print("   （全件処理する場合は df_sample = df に変更）")
    print()

    df_sample = df.head(100)  # デモ用に100件に制限

    # 処理実行
    try:
        result_df = system.process_batch(df_sample)

        # 結果保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"recognition_results_demo_{timestamp}.csv"
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')

        # 統計ファイル保存
        stats_file = output_file.replace('.csv', '_stats.json')
        import json
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump({
                'stats': {k: str(v) if isinstance(v, datetime) else v for k, v in system.stats.items()},
                'checkpoints': system.checkpoints,
                'quality_metrics': system.quality_metrics
            }, f, ensure_ascii=False, indent=2, default=str)

        # 処理時間計算
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("✅ 処理完了!")
        print("=" * 60)
        print(f"処理時間: {duration / 60:.1f}分")
        print(f"結果ファイル: {output_file}")
        print(f"統計ファイル: {stats_file}")
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

        # 削除候補の例を表示
        print("\n" + "=" * 60)
        print("削除候補の例（最初の10件）:")
        print("-" * 60)

        deletion_candidates = result_df[result_df['should_delete'] == True].head(10)
        for i, row in deletion_candidates.iterrows():
            print(f"- {row['name']}: {row['reason']}")

        print("\n" + "=" * 60)
        print("保持対象の例（高スコア上位10件）:")
        print("-" * 60)

        high_score = result_df[result_df['should_delete'] == False].nlargest(10, 'recognition_score')
        for i, row in high_score.iterrows():
            print(f"- {row['name']}: スコア {row['recognition_score']:.1f}")

        print("\n" + "=" * 60)
        print("次のステップ:")
        print("1. 結果ファイルの詳細レビュー")
        print("2. 削除候補の最終確認")
        print("3. 全件処理の実行（df_sample = df に変更）")
        print("4. Google Sheetsへのアップロード")
        print("=" * 60)

        # 進捗ファイルの保存
        with open('recognition_progress.json', 'r', encoding='utf-8') as f:
            progress_data = json.load(f)

        print(f"\n📊 処理統計:")
        print(f"  - Wikipedia発見: {system.stats['wikipedia_found']}/{system.stats['total_processed']}")
        print(f"  - キャッシュヒット: {system.wikipedia_system.stats['cache_hits']}")
        print(f"  - APIコール: {system.wikipedia_system.stats['api_calls']}")
        print(f"  - エラー: {system.stats['errors']}")

    except KeyboardInterrupt:
        print("\n\n処理が中断されました")
        print("進捗は recognition_progress.json に保存されています")
        sys.exit(1)

    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n❌ エラーが発生しました")
        print("詳細はログファイル full_recognition.log を確認してください")
        sys.exit(1)


if __name__ == "__main__":
    main()
