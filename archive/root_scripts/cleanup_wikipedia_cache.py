#!/usr/bin/env python3
"""
Wikipediaキャッシュのクリーンアップスクリプト
失敗したキャッシュや古いキャッシュを削除
"""

import os
import json
import shutil
from datetime import datetime, timedelta
from pathlib import Path
import logging

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s'
)
logger = logging.getLogger(__name__)

def cleanup_wikipedia_cache():
    """Wikipediaキャッシュをクリーンアップ"""

    cache_dir = Path("/Users/admin/Documents/AIUELAB/001-final-hourglass/cache/wikipedia")

    if not cache_dir.exists():
        logger.warning(f"キャッシュディレクトリが存在しません: {cache_dir}")
        return

    # 統計情報
    total_files = 0
    deleted_files = 0
    failed_searches = 0
    old_caches = 0
    problematic_persons = []

    # 問題のある有名人リスト（確実に存在するはず）
    famous_persons = [
        "ヒカキン", "HIKAKIN",
        "吉田美和", "DREAMS COME TRUE",
        "PSY", "サイ",
        "ル・セラフィム", "LE SSERAFIM"
    ]

    logger.info("="*60)
    logger.info("🧹 Wikipediaキャッシュクリーンアップ開始")
    logger.info("="*60)

    # 現在時刻
    now = datetime.now()

    # キャッシュファイルを確認
    for cache_file in cache_dir.glob("*.json"):
        total_files += 1
        delete_file = False
        reason = ""

        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # 1. 失敗した検索のキャッシュ
            if not data.get('found', True):
                failed_searches += 1
                delete_file = True
                reason = "検索失敗"

                # 有名人かチェック
                for person in famous_persons:
                    if 'search_attempts' in data:
                        for attempt in data['search_attempts']:
                            if person in attempt:
                                problematic_persons.append({
                                    'name': person,
                                    'file': cache_file.name,
                                    'cached_at': data.get('cached_at', 'unknown')
                                })
                                break

            # 2. 24時間以上経過したキャッシュ（失敗のみ）
            if not data.get('found', True) and 'cached_at' in data:
                cached_time = datetime.fromisoformat(data['cached_at'])
                age = now - cached_time

                if age > timedelta(hours=24):
                    old_caches += 1
                    delete_file = True
                    reason = f"古い失敗キャッシュ ({age.days}日経過)"

            # 3. スコアが0の有名人
            if data.get('recognition_score', 1) == 0:
                page_title = data.get('page_title', '')
                for person in famous_persons:
                    if person in page_title or person in str(data):
                        delete_file = True
                        reason = f"有名人なのにスコア0: {person}"
                        problematic_persons.append({
                            'name': person,
                            'file': cache_file.name,
                            'score': 0
                        })
                        break

            # ファイル削除
            if delete_file:
                logger.info(f"削除: {cache_file.name} - 理由: {reason}")
                os.remove(cache_file)
                deleted_files += 1

        except Exception as e:
            logger.error(f"エラー処理中: {cache_file.name} - {e}")

    # バックアップディレクトリ作成
    backup_dir = cache_dir.parent / "cache_backup"
    if cache_dir.exists() and deleted_files > 0:
        backup_dir.mkdir(exist_ok=True)
        logger.info(f"バックアップディレクトリ作成: {backup_dir}")

    # 結果レポート
    logger.info("="*60)
    logger.info("📊 クリーンアップ結果")
    logger.info("="*60)
    logger.info(f"総ファイル数: {total_files}")
    logger.info(f"削除ファイル数: {deleted_files}")
    logger.info(f"  - 検索失敗: {failed_searches}")
    logger.info(f"  - 古いキャッシュ: {old_caches}")

    if problematic_persons:
        logger.info("\n⚠️ 問題のある有名人キャッシュ:")
        for person_info in problematic_persons:
            logger.info(f"  - {person_info}")

    # クリーンアップ後の状態確認
    remaining_files = list(cache_dir.glob("*.json"))
    logger.info(f"\n残存キャッシュファイル: {len(remaining_files)}")

    # 特定の有名人の再確認が必要
    if problematic_persons:
        logger.warning("\n🔄 以下の有名人は再処理が必要:")
        unique_persons = set()
        for p in problematic_persons:
            unique_persons.add(p['name'])
        for person in unique_persons:
            logger.warning(f"  - {person}")

    return {
        'total': total_files,
        'deleted': deleted_files,
        'failed_searches': failed_searches,
        'old_caches': old_caches,
        'problematic_persons': problematic_persons,
        'remaining': len(remaining_files)
    }

def verify_cache_state():
    """キャッシュの状態を検証"""
    cache_dir = Path("/Users/admin/Documents/AIUELAB/001-final-hourglass/cache/wikipedia")

    if not cache_dir.exists():
        logger.info("キャッシュディレクトリが存在しません")
        return

    success_count = 0
    failure_count = 0

    for cache_file in cache_dir.glob("*.json"):
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('found', False):
                    success_count += 1
                else:
                    failure_count += 1
        except:
            pass

    logger.info(f"\n📈 キャッシュ状態:")
    logger.info(f"  成功: {success_count}")
    logger.info(f"  失敗: {failure_count}")
    logger.info(f"  成功率: {success_count/(success_count+failure_count)*100:.1f}%" if (success_count+failure_count) > 0 else "N/A")

def main():
    """メイン処理"""
    logger.info("Wikipediaキャッシュクリーンアップツール")
    logger.info("="*60)

    # クリーンアップ実行
    results = cleanup_wikipedia_cache()

    # 状態検証
    verify_cache_state()

    # 結果保存
    result_file = "cache_cleanup_result.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2, default=str)

    logger.info(f"\n結果を保存: {result_file}")

    if results['deleted'] > 0:
        logger.info(f"\n✅ {results['deleted']}件のキャッシュを削除しました")
        logger.info("Wikipedia検索システムの再実行を推奨します")
    else:
        logger.info("\n✅ 削除対象のキャッシュはありませんでした")

if __name__ == "__main__":
    main()
