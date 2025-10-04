#!/usr/bin/env python3
"""
修正済みCSVの再検証

EP077修正 + FactChecker判定ロジック改善後の再検証
"""

import sys
sys.path.insert(0, '/Users/admin/Documents/AIUELAB/001-final-hourglass')

from validate_and_fix_episodes import validate_all_episodes, generate_report

def main():
    print("="*70)
    print("🔄 修正済みエピソードの再検証")
    print("="*70)

    # 修正済みCSVを検証
    csv_path = '#episodes_fixed_20251002.csv'

    print(f"\n📂 入力ファイル: {csv_path}")
    print("📋 検証内容:")
    print("  - EP077: フォーマット修正済み")
    print("  - FactChecker: 判定ロジック改善（PARTIAL/UNVERIFIEDも合格）")
    print()

    # 全エピソード検証
    results = validate_all_episodes(csv_path)

    # レポート生成
    generate_report(results, output_path='validation_report_fixed_20251002.json')

    print("\n" + "="*70)
    print("✅ 再検証完了")
    print("="*70)


if __name__ == "__main__":
    main()
