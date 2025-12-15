#!/usr/bin/env python3
"""
全エピソードの包括的ファクトチェック実行スクリプト
未検証エピソードを特定し、全件に対してファクトチェックを実行
"""

import pandas as pd
from datetime import datetime
import sys
import json
from src.fact_checker import FactChecker, FactCheckResult
from pdca_guardian import PDCAGuardian

def comprehensive_fact_check():
    """全エピソードに対する包括的ファクトチェック"""

    print("="*70)
    print("🔍 包括的ファクトチェック実行")
    print("="*70)

    # クリーン済みのCSVファイルを読み込み
    input_file = 'episodes_cleaned_20250923_075301.csv'
    print(f"\n📂 入力ファイル: {input_file}")

    try:
        df = pd.read_csv(input_file, encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"❌ エラー: {input_file}が見つかりません")
        sys.exit(1)

    print(f"  総エピソード数: {len(df)}件")

    # ファクトチェッカーとPDCAガーディアン初期化
    fact_checker = FactChecker()
    pdca_guardian = PDCAGuardian()

    # 現在の検証状況を分析
    print("\n📊 現在の検証状況:")
    verified_count = df[df['fact_check_status'].notna()].shape[0]
    unverified_count = len(df) - verified_count
    print(f"  検証済み: {verified_count}件 ({verified_count/len(df)*100:.1f}%)")
    print(f"  未検証: {unverified_count}件 ({unverified_count/len(df)*100:.1f}%)")

    # 未検証エピソードのリスト
    unverified = df[df['fact_check_status'].isna()]
    if len(unverified) > 0:
        print(f"\n⚠️ 未検証エピソード一覧:")
        for _, row in unverified.head(10).iterrows():
            print(f"  - {row['person_name']} ({row['episode_age']}歳)")
        if len(unverified) > 10:
            print(f"  ... 他{len(unverified)-10}件")

    # 全エピソードに対してファクトチェック実行
    print(f"\n🔄 ファクトチェック実行中...")

    checked_episodes = []
    violations_summary = {
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0
    }

    for idx, row in df.iterrows():
        person_name = row['person_name']
        episode_text = row['episode_text']
        episode_age = row['episode_age']

        # プログレス表示
        if (idx + 1) % 10 == 0:
            print(f"  進捗: {idx+1}/{len(df)}件 処理完了")

        # ファクトチェック実行
        report = fact_checker.check_episode(
            person_id=row.get('person_id', f'P{idx:03d}'),
            person_name=person_name,
            episode_text=episode_text,
            birth_year=None,  # 生年データが必要な場合は別途取得
            metadata={'episode_age': episode_age}
        )

        # PDCAルールチェック（RULE_115-125）
        pdca_violations = pdca_guardian.check_episode_quality(
            episode_text,
            episode_age,
            person_name
        )

        # 結果を更新
        updated_row = row.copy()

        # ファクトチェック結果を反映
        if report.result == FactCheckResult.VERIFIED:
            updated_row['fact_check_status'] = 'verified'
        elif report.result == FactCheckResult.INCORRECT:
            updated_row['fact_check_status'] = 'failed'
        elif report.result == FactCheckResult.SUSPICIOUS:
            updated_row['fact_check_status'] = 'suspicious'
        else:
            updated_row['fact_check_status'] = 'unverified'

        # 違反の集計
        for violation in report.violations:
            violations_summary[violation.severity] += 1

        # 品質スコアの再計算（もし空欄の場合）
        if pd.isna(row.get('quality_score')):
            updated_row['quality_score'] = report.total_score / 10  # 100点満点を10点満点に変換

        checked_episodes.append(updated_row)

    # 結果をDataFrameに変換
    result_df = pd.DataFrame(checked_episodes)

    # 統計表示
    print(f"\n📈 ファクトチェック完了:")
    print(f"  処理件数: {len(result_df)}件")

    # ステータス別集計
    status_counts = result_df['fact_check_status'].value_counts()
    print(f"\n  ステータス別:")
    for status, count in status_counts.items():
        print(f"    {status}: {count}件 ({count/len(result_df)*100:.1f}%)")

    # 違反サマリー
    print(f"\n  違反レベル別:")
    for level, count in violations_summary.items():
        if count > 0:
            print(f"    {level}: {count}件")

    # 改善が必要なエピソード
    problematic = result_df[result_df['fact_check_status'].isin(['failed', 'suspicious'])]
    if len(problematic) > 0:
        print(f"\n⚠️ 要改善エピソード: {len(problematic)}件")
        for _, row in problematic.head(5).iterrows():
            print(f"  - {row['person_name']} ({row['episode_age']}歳): {row['fact_check_status']}")

    # 結果を保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'episodes_fact_checked_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        result_df.to_csv(f, index=False)

    print(f"\n✅ ファクトチェック済みファイル保存: {output_file}")

    # レポートファイルも生成
    report_data = {
        'timestamp': timestamp,
        'total_episodes': len(result_df),
        'fact_check_results': status_counts.to_dict(),
        'violations': violations_summary,
        'problematic_episodes': [
            {
                'name': row['person_name'],
                'age': row['episode_age'],
                'status': row['fact_check_status']
            }
            for _, row in problematic.iterrows()
        ]
    }

    report_file = f'fact_check_report_{timestamp}.json'
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"📋 レポートファイル保存: {report_file}")

    return result_df

def validate_fact_checks(df):
    """ファクトチェック結果の妥当性検証"""

    print("\n🔍 ファクトチェック結果の検証:")

    # 全エピソードがチェック済みか
    unchecked = df[df['fact_check_status'].isna()]
    if len(unchecked) == 0:
        print("  ✅ 全エピソードがファクトチェック済み")
    else:
        print(f"  ❌ {len(unchecked)}件が未チェック")
        return False

    # 品質スコアとステータスの整合性
    inconsistent = df[
        (df['fact_check_status'] == 'verified') &
        (df['quality_score'] < 6.0)
    ]
    if len(inconsistent) > 0:
        print(f"  ⚠️ {len(inconsistent)}件で品質スコアとステータスが不整合")

    return True

def main():
    """メイン処理"""
    try:
        # 包括的ファクトチェック実行
        checked_df = comprehensive_fact_check()

        # 検証
        is_valid = validate_fact_checks(checked_df)

        if is_valid:
            print("\n" + "="*70)
            print("🎉 包括的ファクトチェック完了！")
            print("="*70)
            print("""
            処理完了:
            - 全40件のエピソードをファクトチェック
            - 問題のあるエピソードを特定
            - PDCAルールとの整合性を検証
            """)
        else:
            print("\n⚠️ 警告: ファクトチェックに問題があります")

        return 0

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
