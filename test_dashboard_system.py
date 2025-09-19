#!/usr/bin/env python3
"""
ダッシュボードシステムのテスト
実際のデータでリアルタイム監視を確認
"""

import os
import time
import threading
import logging
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

def simulate_collection_logs():
    """収集プロセスのログをシミュレート"""

    # テスト用の人名リスト
    test_persons = [
        ('安倍晋三', 1954),
        ('菅義偉', 1948),
        ('岸田文雄', 1957),
        ('小泉純一郎', 1942),
        ('野田佳彦', 1957),
        ('HIKAKIN', 1989),
        ('はじめしゃちょー', 1993),
        ('キズナアイ', None),
        ('米津玄師', 1991),
        ('藤井聡太', 2002),
        ('大谷翔平', 1994),
        ('羽生結弦', 1994),
        ('浅田真央', 1990),
        ('石川佳純', 1993),
        ('錦織圭', 1989)
    ]

    total = len(test_persons)

    logger.info("=" * 70)
    logger.info("🚀 誕生年取得システム開始")
    logger.info(f"📊 処理対象: {total}件")
    logger.info("=" * 70)

    for idx, (name, birth_year) in enumerate(test_persons, 1):
        # 進捗ログ
        logger.info(f"進捗: {idx}/{total} ({idx/total*100:.1f}%)")

        # 処理をシミュレート
        time.sleep(2)  # 2秒待機（API呼び出しをシミュレート）

        # 結果ログ
        if birth_year:
            logger.info(f"✅ 取得成功: {name} → {birth_year}")
        else:
            logger.info(f"❌ 取得失敗: {name}")

        # 統計情報
        if idx % 5 == 0:
            success_count = sum(1 for _, y in test_persons[:idx] if y)
            logger.info(f"📊 統計: 取得成功: {success_count}件, 成功率: {success_count/idx*100:.1f}%")

    # 完了ログ
    final_success = sum(1 for _, y in test_persons if y)
    logger.info("=" * 70)
    logger.info("🎯 処理完了")
    logger.info(f"  最終結果: {final_success}/{total} ({final_success/total*100:.1f}%)")
    logger.info("=" * 70)

def main():
    """メイン処理"""
    print("=" * 70)
    print("🧪 ダッシュボードシステムテスト")
    print("=" * 70)
    print()
    print("📋 テスト手順:")
    print("1. 別ターミナルで監視サーバーを起動:")
    print("   python3 birth_collection_server.py")
    print()
    print("2. ブラウザでダッシュボードを開く:")
    print("   http://localhost:5000")
    print()
    print("3. このスクリプトがログを生成（30秒間）")
    print()
    print("⏳ 3秒後にログ生成を開始します...")
    print("=" * 70)

    time.sleep(3)

    # ログ生成を開始
    simulate_collection_logs()

    print()
    print("✅ テスト完了")
    print("ダッシュボードでリアルタイム更新が確認できましたか？")

if __name__ == "__main__":
    main()