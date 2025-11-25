#!/usr/bin/env python3
"""
スロット値をデータベースに同期するスクリプト

MASTER_EPISODES_CURRENT.csvのslot値をバックエンドデータベースに反映
"""

import pandas as pd
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from app.database import SessionLocal
from app.models import Episode

CSV_PATH = PROJECT_ROOT / "MASTER_EPISODES_CURRENT.csv"


def sync_slots_to_database():
    """CSVからデータベースへスロット値を同期"""

    print("=" * 80)
    print("📋 スロット値のデータベース同期")
    print("=" * 80)
    print()

    # Step 1: CSVファイル読み込み
    print("Step 1: CSVファイル読み込み中...")
    df = pd.read_csv(CSV_PATH, encoding='utf-8-sig')
    print(f"  ✅ 読み込み完了: {len(df):,}件")
    print(f"  スロット割り当て済み: {df['slot'].notna().sum():,}件")
    print()

    # Step 2: データベース接続
    print("Step 2: データベース接続中...")
    db = SessionLocal()
    try:
        # 既存のエピソード数を確認
        total_episodes_db = db.query(Episode).count()
        print(f"  ✅ データベース接続成功")
        print(f"  データベース内エピソード数: {total_episodes_db:,}件")
        print()

        # Step 3: スロット値を更新
        print("Step 3: スロット値をデータベースに同期中...")

        updated_count = 0
        skipped_count = 0
        error_count = 0

        for idx, row in df.iterrows():
            episode_id = row['episode_id']
            slot_value = row['slot']

            # スロット値がNaNの場合はスキップ
            if pd.isna(slot_value):
                skipped_count += 1
                continue

            # データベースでエピソードを検索
            episode = db.query(Episode).filter(Episode.episode_id == episode_id).first()

            if episode:
                # スロット値を更新（intに変換）
                episode.slot = int(slot_value)
                updated_count += 1

                # 100件ごとにコミット
                if updated_count % 100 == 0:
                    db.commit()
                    print(f"    進捗: {updated_count:,}件更新完了...")
            else:
                error_count += 1
                if error_count <= 10:  # 最初の10件のみ表示
                    print(f"    ⚠️  エピソードが見つかりません: {episode_id}")

        # 最終コミット
        db.commit()

        print(f"  ✅ データベース同期完了")
        print()

        # Step 4: 検証
        print("Step 4: 同期結果の検証")
        print(f"  更新成功: {updated_count:,}件")
        print(f"  スキップ（スロット値なし）: {skipped_count:,}件")
        print(f"  エラー（エピソードが見つからない）: {error_count:,}件")
        print()

        # データベース内のスロット分布を確認
        print("  データベース内のスロット分布:")
        from sqlalchemy import func
        slot_distribution = db.query(
            Episode.slot,
            func.count(Episode.slot)
        ).filter(Episode.slot.isnot(None)).group_by(Episode.slot).order_by(Episode.slot).all()

        total_with_slot = sum(count for _, count in slot_distribution)
        for slot, count in slot_distribution:
            pct = count / total_with_slot * 100 if total_with_slot > 0 else 0
            bar = '█' * int(pct / 2)
            print(f"    slot {int(slot):2d}: {count:4d}件 ({pct:5.1f}%) {bar}")
        print()

        # サマリー
        print("=" * 80)
        print("✅ スロット値のデータベース同期が完了しました！")
        print("=" * 80)
        print()
        print(f"📊 サマリー:")
        print(f"  - CSV総エピソード数: {len(df):,}件")
        print(f"  - 更新成功: {updated_count:,}件")
        print(f"  - スキップ: {skipped_count:,}件")
        print(f"  - エラー: {error_count:,}件")
        print()

    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    sync_slots_to_database()
