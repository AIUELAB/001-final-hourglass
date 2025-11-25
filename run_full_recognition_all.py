#!/usr/bin/env python3
"""
Run Full Recognition System - ALL Records
4,701件の完全処理実行スクリプト（全件版）
"""

import pandas as pd
from pathlib import Path
import logging
from datetime import datetime
from integrated_recognition_system import IntegratedRecognitionSystem
import sys
import json

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('full_recognition_all.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def main():
    """完全処理実行（全件）"""
    print("=" * 60)
    print("統合知名度評価システム - 完全処理（全4,701件）")
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
    print(f"  - 予想処理時間: 90-120分")
    print(f"  - 削除率目標: 10-20%")
    print("=" * 60)

    # 処理開始時刻
    start_time = datetime.now()
    print(f"\n🚀 全件処理開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    # 全件処理
    print("📊 4,701件の処理を開始します...")
    print("   （処理中は進捗が100件ごとに表示されます）")
    print()

    # 処理実行
    try:
        result_df = system.process_batch(df)  # 全件処理

        # 結果保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = f"recognition_results_ALL_{timestamp}.csv"
        result_df.to_csv(output_file, index=False, encoding='utf-8-sig')

        # 統計ファイル保存
        stats_file = output_file.replace('.csv', '_stats.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump({
                'stats': {k: str(v) if isinstance(v, datetime) else v for k, v in system.stats.items()},
                'checkpoints': system.checkpoints,
                'quality_metrics': system.quality_metrics,
                'processing_info': {
                    'total_records': len(df),
                    'output_records': len(result_df),
                    'start_time': str(start_time),
                    'end_time': str(datetime.now())
                }
            }, f, ensure_ascii=False, indent=2, default=str)

        # 処理時間計算
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        print("\n" + "=" * 60)
        print("✅ 全件処理完了!")
        print("=" * 60)
        print(f"処理時間: {duration / 60:.1f}分 ({duration / 3600:.1f}時間)")
        print(f"処理速度: {len(df) / (duration / 60):.1f}件/分")
        print(f"結果ファイル: {output_file}")
        print(f"統計ファイル: {stats_file}")
        print()

        # 品質チェック結果
        deletion_rate = system.stats['deletion_candidates'] / max(system.stats['total_processed'], 1)

        print("=" * 60)
        print("📊 最終統計:")
        print("-" * 60)
        print(f"入力件数: {system.stats['total_input']:,}件")
        print(f"処理件数: {system.stats['total_processed']:,}件")
        print(f"グループ展開: {system.stats['groups_expanded']}グループ → {system.stats['individuals_from_groups']}人")
        print(f"Wikipedia発見: {system.stats['wikipedia_found']:,}件 ({system.stats['wikipedia_found']/max(system.stats['total_processed'], 1)*100:.1f}%)")
        print(f"削除候補: {system.stats['deletion_candidates']:,}件 ({deletion_rate*100:.1f}%)")
        print(f"保持対象: {system.stats['preserved_count']:,}件")
        print(f"エラー: {system.stats['errors']}件")
        print("=" * 60)

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

        print()
        print(f"チェックポイント実行回数: {len(system.checkpoints)}回")
        if quality_issues_count > 0:
            print(f"⚠️ {quality_issues_count}回の品質問題が検出されました")
        else:
            print("✅ すべてのチェックポイントで品質基準をクリア")

        # 削除候補の例を表示
        print("\n" + "=" * 60)
        print("削除候補の例（最初の20件）:")
        print("-" * 60)

        deletion_candidates = result_df[result_df['should_delete'] == True].head(20)
        for idx, (i, row) in enumerate(deletion_candidates.iterrows(), 1):
            print(f"{idx:2d}. {row['name']}: {row['reason']}")

        print("\n" + "=" * 60)
        print("保持対象の例（高スコア上位20件）:")
        print("-" * 60)

        high_score = result_df[result_df['should_delete'] == False].nlargest(20, 'recognition_score')
        for idx, (i, row) in enumerate(high_score.iterrows(), 1):
            print(f"{idx:2d}. {row['name']}: スコア {row['recognition_score']:.1f}")

        # API使用統計
        print("\n" + "=" * 60)
        print("📊 API使用統計:")
        print("-" * 60)
        print(f"Wikipedia API呼び出し: {system.wikipedia_system.stats['api_calls']:,}回")
        print(f"キャッシュヒット: {system.wikipedia_system.stats['cache_hits']:,}回")
        cache_rate = system.wikipedia_system.stats['cache_hits'] / max(
            system.wikipedia_system.stats['api_calls'] + system.wikipedia_system.stats['cache_hits'], 1
        )
        print(f"キャッシュヒット率: {cache_rate*100:.1f}%")

        print("\n" + "=" * 60)
        print("次のステップ:")
        print("1. 結果ファイルの詳細レビュー")
        print("2. 削除候補の最終確認")
        print("3. Google Sheetsへのアップロード")
        print("4. 年間拡張計画の策定（月1,100人ペース）")
        print("=" * 60)

        # 最終レポート生成
        final_report = f"""
# Wikipedia知名度評価 - 完全処理結果

処理日時: {start_time.strftime('%Y-%m-%d %H:%M:%S')} - {end_time.strftime('%H:%M:%S')}
処理時間: {duration / 60:.1f}分

## 統計サマリー
- 入力: {system.stats['total_input']:,}件
- 出力: {system.stats['total_processed']:,}件
- 削除候補: {system.stats['deletion_candidates']:,}件 ({deletion_rate*100:.1f}%)
- Wikipedia発見率: {system.stats['wikipedia_found']/max(system.stats['total_processed'], 1)*100:.1f}%

## ファイル
- 結果: {output_file}
- 統計: {stats_file}
"""

        report_file = f"FINAL_REPORT_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(final_report)

        print(f"\n📄 最終レポート: {report_file}")

    except KeyboardInterrupt:
        print("\n\n処理が中断されました")
        print("進捗は recognition_progress.json に保存されています")
        sys.exit(1)

    except Exception as e:
        logger.error(f"処理中にエラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        print("\n❌ エラーが発生しました")
        print("詳細はログファイル full_recognition_all.log を確認してください")
        sys.exit(1)


if __name__ == "__main__":
    main()
