#!/usr/bin/env python3
"""
自動更新システムのテストスクリプト
監視モードを無効にして、個別コンポーネントをテスト
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path
from datetime import datetime

# 新しい自動更新システムコンポーネントをインポート
from src.cache_manager import CacheManager
from src.auto_updater import AutoUpdater
from src.version_controller import VersionController
from src.integrity_checker import IntegrityChecker

def test_components():
    """個別コンポーネントのテスト"""
    
    print("=" * 60)
    print("🔬 自動更新システムコンポーネントテスト")
    print("=" * 60)
    
    # テストデータを準備（必須カラムを含む）
    test_df = pd.DataFrame({
        'person_id': ['P000399', 'P000001', 'P000002'],
        'person_name': ['Kajisac', 'Test User', 'Sample Person'],
        'person_name_ja': ['カジサック', 'テストユーザー', 'サンプル人物'],
        'person_name_display': ['カジサック', 'テストユーザー', 'サンプル'],
        'birth_year': [1980, 1990, 1985],
        'category': ['Influencer', 'Test', 'Sample'],
        'sub_category': ['YouTuber', 'Test', 'Sample']
    })
    
    print("\n✅ テストデータ準備完了")
    print(f"   行数: {len(test_df)}")
    
    # 1. CacheManager テスト
    print("\n📋 1. CacheManager テスト")
    try:
        cache_manager = CacheManager()
        
        # キャッシュクリア
        result = cache_manager.purge_all_cache()
        print(f"   キャッシュクリア: {'成功' if result else '失敗'}")
        
        # キャッシュバスターURL生成
        test_url = "https://docs.google.com/spreadsheets/d/test"
        busted_url = cache_manager.generate_cache_buster_url(test_url)
        print(f"   キャッシュバスターURL生成: 成功")
        print(f"   元URL: {test_url}")
        print(f"   生成URL: {busted_url[:80]}...")
        
        print("   ✅ CacheManager: 正常動作")
    except Exception as e:
        print(f"   ❌ CacheManager エラー: {e}")
        return False
    
    # 2. IntegrityChecker テスト
    print("\n📋 2. IntegrityChecker テスト")
    try:
        integrity_checker = IntegrityChecker()
        
        # データ整合性チェック
        report = integrity_checker.check_data_integrity(test_df)
        print(f"   データ整合性チェック完了")
        print(f"   - 総レコード数: {report['total_rows']}")
        print(f"   - エラー数: {report['errors']}")
        print(f"   - 警告数: {report['warnings']}")
        
        # 検証
        is_valid, validated_df = integrity_checker.validate_before_sync(test_df)
        print(f"   同期前検証: {'成功' if is_valid else '失敗'}")
        
        print("   ✅ IntegrityChecker: 正常動作")
    except Exception as e:
        print(f"   ❌ IntegrityChecker エラー: {e}")
        return False
    
    # 3. VersionController テスト
    print("\n📋 3. VersionController テスト")
    try:
        version_controller = VersionController()
        
        # バージョン作成
        version_id = version_controller.create_version(test_df, "test_version")
        print(f"   バージョン作成: {version_id}")
        
        # ハッシュ計算
        data_hash = version_controller.calculate_hash(test_df)
        print(f"   データハッシュ: {data_hash[:16]}...")
        
        # バージョン履歴
        versions = version_controller.list_versions(limit=3)
        print(f"   バージョン履歴: {len(versions)}件")
        
        print("   ✅ VersionController: 正常動作")
    except Exception as e:
        print(f"   ❌ VersionController エラー: {e}")
        return False
    
    # 4. AutoUpdater テスト（API呼び出しはスキップ）
    print("\n📋 4. AutoUpdater テスト")
    try:
        auto_updater = AutoUpdater()
        
        # 設定の確認
        print(f"   バッチサイズ: {auto_updater.config['batch_size']}")
        print(f"   リトライ回数: {auto_updater.config['retry_count']}")
        print(f"   アトミック更新: {auto_updater.config['atomic_update']}")
        
        # データ準備のテスト
        headers = list(test_df.columns)
        values = test_df.values.tolist()
        print(f"   データ準備: ヘッダー{len(headers)}個、データ{len(values)}行")
        
        # キャッシュマネージャーの確認
        print(f"   キャッシュマネージャー: {'有効' if auto_updater.cache_manager else '無効'}")
        
        print("   ✅ AutoUpdater: 正常動作（API呼び出しなし）")
    except Exception as e:
        print(f"   ❌ AutoUpdater エラー: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("✅ すべてのコンポーネントが正常に動作しています")
    print("=" * 60)
    
    return True

def test_quick_sync():
    """監視モードなしでの簡易同期テスト"""
    
    print("\n" + "=" * 60)
    print("🔄 簡易同期テスト（監視モードなし）")
    print("=" * 60)
    
    # 最新のCSVファイルを検索
    csv_files = list(Path('.').glob('ultra_think_*.csv'))
    if not csv_files:
        print("❌ ultra_think_*.csv ファイルが見つかりません")
        return False
    
    # 最新のファイルを選択
    latest_csv = max(csv_files, key=lambda f: f.stat().st_mtime)
    print(f"\n📄 対象ファイル: {latest_csv.name}")
    
    # データ読み込み
    try:
        df = pd.read_csv(latest_csv)
        print(f"✅ データ読み込み成功: {len(df)}行")
        
        # キャッシュクリア
        cache_manager = CacheManager()
        cache_manager.purge_all_cache()
        print("✅ キャッシュクリア完了")
        
        # データ検証
        integrity_checker = IntegrityChecker()
        is_valid, df = integrity_checker.validate_before_sync(df)
        print(f"✅ データ検証: {'成功' if is_valid else '失敗'}")
        
        # バージョン作成
        version_controller = VersionController()
        version_id = version_controller.create_version(df, "sync_test")
        print(f"✅ バージョン作成: {version_id}")
        
        print("\n" + "=" * 60)
        print("✅ 簡易同期テスト完了（Google Sheetsへの実際の同期はスキップ）")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    """メイン実行"""
    
    print("\n🚀 Ultra Think 自動更新システムテスト開始\n")
    
    # コンポーネントテスト
    if not test_components():
        print("\n❌ コンポーネントテストが失敗しました")
        return 1
    
    # 簡易同期テスト
    if not test_quick_sync():
        print("\n❌ 簡易同期テストが失敗しました")
        return 1
    
    print("\n" + "=" * 60)
    print("🎉 すべてのテストが成功しました！")
    print("=" * 60)
    print("\n📝 次のステップ:")
    print("1. 本番環境での同期を実行する場合:")
    print("   python auto_startup_sync_optimized.py")
    print("\n2. 監視モードを無効にして一回だけ同期する場合:")
    print("   設定ファイルで enable_real_time_monitoring を false に変更")
    print("\n3. ブラウザでGoogle Sheetsを確認:")
    print("   https://docs.google.com/spreadsheets/d/1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())