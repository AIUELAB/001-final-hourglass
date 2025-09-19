#!/usr/bin/env python3
"""
リアルタイム同期テスト
実際のログを生成してダッシュボードの更新を確認
"""

import time
import logging
import random
from pathlib import Path

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('wikipedia_birth_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_test_logs():
    """テスト用ログを生成"""

    # テスト用の人物データ
    test_persons = [
        ('大谷翔平', 1994, True),
        ('藤井聡太', 2002, True),
        ('羽生結弦', 1994, True),
        ('浅田真央', 1990, True),
        ('石川佳純', 1993, True),
        ('錦織圭', 1989, True),
        ('本田真凜', 2001, True),
        ('池江璃花子', 2000, True),
        ('張本智和', 2003, True),
        ('伊藤美誠', 2000, True),
        ('キズナアイ', None, False),
        ('ミライアカリ', None, False),
        ('電脳少女シロ', None, False),
        ('富士葵', None, False),
        ('輝夜月', None, False),
        ('田中太郎', None, False),
        ('山田次郎', None, False),
        ('佐藤三郎', None, False),
        ('鈴木四郎', None, False),
        ('高橋五郎', None, False)
    ]

    total = len(test_persons)
    found = 0
    not_found = 0

    logger.info("=" * 70)
    logger.info("🚀 誕生年取得システム開始（リアルタイムテスト）")
    logger.info(f"📊 処理対象: {total}件")
    logger.info("=" * 70)

    for idx, (name, birth_year, should_find) in enumerate(test_persons, 1):
        # 進捗ログ
        logger.info(f"進捗: {idx}/{total} ({idx/total*100:.1f}%)")

        # 処理を模擬（0.5〜2秒のランダム待機）
        time.sleep(random.uniform(0.5, 2.0))

        # 成功/失敗をシミュレート
        if should_find and birth_year:
            found += 1
            logger.info(f"✅ 取得成功: {name} → {birth_year}")
        else:
            not_found += 1
            logger.info(f"❌ 取得失敗: {name}")

        # 5件ごとに統計情報
        if idx % 5 == 0:
            success_rate = (found / idx * 100) if idx > 0 else 0
            logger.info(f"📊 統計: 取得成功: {found}件, 成功率: {success_rate:.1f}%")

    # 処理完了
    logger.info("=" * 70)
    logger.info("🎯 処理完了")
    logger.info(f"  試行数: {total}件")
    logger.info(f"  取得成功: {found}件")
    logger.info(f"  取得失敗: {not_found}件")
    logger.info(f"  成功率: {found/total*100:.1f}%")
    logger.info("=" * 70)

def main():
    """メイン処理"""
    print("=" * 70)
    print("🧪 リアルタイム同期テスト")
    print("=" * 70)
    print()
    print("このスクリプトがログを生成します。")
    print("ダッシュボード（http://localhost:5002）で")
    print("リアルタイムに更新されることを確認してください。")
    print()
    print("⏳ 3秒後に開始します...")
    print("=" * 70)

    time.sleep(3)

    # テストログ生成
    generate_test_logs()

    print()
    print("✅ テスト完了")
    print("ダッシュボードでリアルタイム更新を確認してください。")

if __name__ == "__main__":
    main()