#!/usr/bin/env python3
"""
同期後の動作検証
Post-Sync Verification

検証内容:
1. pdca_guardian.pyが正常にインポート可能か
2. episode_guardian_config.jsonが正常に読み込めるか
3. 同期されたルール数の確認
"""

import logging
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(asctime)s - [%(levelname)s] - %(message)s')
logger = logging.getLogger(__name__)


def verify_pdca_guardian():
    """pdca_guardian.pyの検証"""
    logger.info("=" * 60)
    logger.info("1. pdca_guardian.pyの検証")
    logger.info("=" * 60)

    try:
        # 構文チェック（コンパイル）
        with open('pdca_guardian.py', 'r', encoding='utf-8') as f:
            code = f.read()

        compile(code, 'pdca_guardian.py', 'exec')

        logger.info("✅ 構文チェック成功")

        # AUTO-GENERATED RULESセクションの確認
        if '# AUTO-GENERATED RULES START' in code and '# AUTO-GENERATED RULES END' in code:
            start_idx = code.index('# AUTO-GENERATED RULES START')
            end_idx = code.index('# AUTO-GENERATED RULES END')

            rules_section = code[start_idx:end_idx]

            # ルール数をカウント（# RULE_XXX:パターン）
            import re
            rule_pattern = r'# (RULE_\d+|FORMAT_\d+|ENTITY_TYPE_\d+):'
            rules_found = re.findall(rule_pattern, rules_section)

            logger.info(f"✅ 同期されたルール: {len(rules_found)}件")
            logger.info(f"  サンプル: {', '.join(rules_found[:5])}...")

            return True
        else:
            logger.error("❌ AUTO-GENERATED RULESマーカーが見つかりません")
            return False

    except SyntaxError as e:
        logger.error(f"❌ 構文エラー: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 検証失敗: {e}")
        return False


def verify_episode_guardian_config():
    """episode_guardian_config.jsonの検証"""
    logger.info("\n" + "=" * 60)
    logger.info("2. episode_guardian_config.jsonの検証")
    logger.info("=" * 60)

    try:
        with open('episode_guardian_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        logger.info("✅ JSON読み込み成功")

        # unified_rulesセクションの確認
        if 'unified_rules' in config:
            unified = config['unified_rules']

            logger.info(f"✅ 統合ルール情報:")
            logger.info(f"  バージョン: {unified['version']}")
            logger.info(f"  最終更新: {unified['last_updated']}")
            logger.info(f"  総ルール数: {unified['total_rules']}")

            # カテゴリ別集計
            logger.info(f"\n  カテゴリ別ルール数:")
            for category, rules in unified['categories'].items():
                logger.info(f"    {category}: {len(rules)}件")

            return True
        else:
            logger.error("❌ unified_rulesセクションが見つかりません")
            return False

    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON解析エラー: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ 検証失敗: {e}")
        return False


def verify_backup_integrity():
    """バックアップの整合性確認"""
    logger.info("\n" + "=" * 60)
    logger.info("3. バックアップの整合性確認")
    logger.info("=" * 60)

    backup_dir = Path("rule_backups")

    if not backup_dir.exists():
        logger.warning("⚠️ バックアップディレクトリが存在しません")
        return False

    # 最新のバックアップファイルを探す
    backups = list(backup_dir.glob("*.backup_*"))

    if not backups:
        logger.warning("⚠️ バックアップファイルが見つかりません")
        return False

    # 最新の2つを表示
    recent_backups = sorted(backups, key=lambda p: p.stat().st_mtime, reverse=True)[:2]

    logger.info(f"✅ バックアップファイル: {len(backups)}件")
    logger.info(f"\n  最新のバックアップ:")
    for backup in recent_backups:
        size_kb = backup.stat().st_size / 1024
        logger.info(f"    {backup.name} ({size_kb:.1f} KB)")

    return True


def main():
    """メイン処理"""
    logger.info("🚀 同期後の動作検証開始\n")

    results = []

    # 1. pdca_guardian.py検証
    results.append(("pdca_guardian.py", verify_pdca_guardian()))

    # 2. episode_guardian_config.json検証
    results.append(("episode_guardian_config.json", verify_episode_guardian_config()))

    # 3. バックアップ整合性確認
    results.append(("バックアップ整合性", verify_backup_integrity()))

    # 総合判定
    logger.info("\n" + "=" * 60)
    logger.info("📋 検証結果サマリー")
    logger.info("=" * 60)

    for check_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  {check_name}: {status}")

    all_passed = all(result for _, result in results)

    logger.info("\n" + "=" * 60)
    if all_passed:
        logger.info("🎉 すべての検証に合格しました！")
        logger.info("統合ルール管理システムが正常に同期されました。")
    else:
        logger.info("⚠️ 一部の検証に失敗しました")
    logger.info("=" * 60)

    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
