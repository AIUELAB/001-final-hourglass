#!/usr/bin/env python3
"""
重複エピソード削除スクリプト
各人物について1つのエピソードのみを保持し、品質の高い方を選択
"""

import pandas as pd
from datetime import datetime
import sys
from src.fact_checker import FactChecker, FactCheckResult

def fix_duplicate_episodes():
    """重複エピソードを削除して各人物1エピソードに修正"""

    print("="*70)
    print("🔧 重複エピソード修正処理")
    print("="*70)

    # 1. 現在のCSVファイルを読み込み
    input_file = 'episodes_58_complete_20250923_000952.csv'
    print(f"\n📂 入力ファイル: {input_file}")

    try:
        df = pd.read_csv(input_file, encoding='utf-8-sig')
    except FileNotFoundError:
        print(f"❌ エラー: {input_file}が見つかりません")
        sys.exit(1)

    print(f"  読み込み行数: {len(df)}行（ヘッダー除く）")

    # 2. 重複分析
    print("\n📊 重複分析:")
    duplicates = df[df.duplicated(['person_name'], keep=False)]
    duplicate_names = duplicates['person_name'].unique()
    print(f"  重複している人物数: {len(duplicate_names)}人")

    if len(duplicate_names) > 0:
        print(f"  重複人物リスト: {', '.join(sorted(duplicate_names[:5]))}...")

    # 3. 各人物について最良のエピソードを選択
    print("\n🎯 最良エピソード選択処理:")

    cleaned_episodes = []
    fact_checker = FactChecker()

    for person_name in df['person_name'].unique():
        person_episodes = df[df['person_name'] == person_name]

        if len(person_episodes) == 1:
            # 重複なし
            cleaned_episodes.append(person_episodes.iloc[0].to_dict())
        else:
            # 重複あり - 最良のエピソードを選択
            best_episode = None
            best_score = -1

            for _, episode in person_episodes.iterrows():
                # スコア計算の優先順位
                # 1. fact_check_statusが'verified'
                # 2. quality_scoreが高い
                # 3. episode_id=1（既存の検証済みエピソード）

                score = 0

                # ファクトチェックステータス
                if episode.get('fact_check_status') == 'verified':
                    score += 100
                elif episode.get('fact_check_status') == 'verified_corrected':
                    score += 90

                # 品質スコア（欠損値は0として扱う）
                quality = episode.get('quality_score', 0)
                if pd.notna(quality):
                    score += float(quality) * 10

                # episode_idの優先度
                if episode.get('episode_id') == 1:
                    score += 50  # 既存の検証済みエピソードを優先

                # 文字数（適切な長さを評価）
                text_len = len(str(episode.get('episode_text', '')))
                if 132 <= text_len <= 250:
                    score += 20

                if score > best_score:
                    best_score = score
                    best_episode = episode

            if best_episode is not None:
                cleaned_episodes.append(best_episode.to_dict())

                # 削除されるエピソードの情報を表示
                removed_count = len(person_episodes) - 1
                if removed_count > 0:
                    print(f"  {person_name}: {len(person_episodes)}件→1件 (スコア: {best_score:.1f})")

    # 4. クリーンなDataFrameを作成
    cleaned_df = pd.DataFrame(cleaned_episodes)

    # 5. ソート（人物名順）
    cleaned_df = cleaned_df.sort_values('person_name')

    # 6. 結果の統計
    print(f"\n📈 処理結果:")
    print(f"  処理前: {len(df)}件")
    print(f"  処理後: {len(cleaned_df)}件")
    print(f"  削除数: {len(df) - len(cleaned_df)}件")

    # 重複チェック
    remaining_duplicates = cleaned_df[cleaned_df.duplicated(['person_name'], keep=False)]
    if len(remaining_duplicates) > 0:
        print(f"  ⚠️ 警告: まだ{len(remaining_duplicates)}件の重複が残っています")
    else:
        print(f"  ✅ すべての重複が解消されました")

    # 7. 品質統計
    print(f"\n🎖️ 品質統計:")
    verified_count = cleaned_df[cleaned_df['fact_check_status'].notna()].shape[0]
    print(f"  ファクトチェック済み: {verified_count}/{len(cleaned_df)}件")

    avg_quality = cleaned_df['quality_score'].mean()
    if pd.notna(avg_quality):
        print(f"  平均品質スコア: {avg_quality:.1f}")

    # 8. 新しいCSVファイルを保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'episodes_cleaned_{timestamp}.csv'

    with open(output_file, 'w', encoding='utf-8-sig') as f:
        cleaned_df.to_csv(f, index=False)

    print(f"\n✅ 修正済みファイル保存: {output_file}")

    # 9. 削除されたエピソードの詳細レポート
    print(f"\n📋 削除されたエピソード詳細:")
    removed_episodes = []
    for person_name in duplicate_names:
        original = df[df['person_name'] == person_name]
        if len(original) > 1:
            kept = cleaned_df[cleaned_df['person_name'] == person_name]
            if len(kept) == 1:
                kept_age = kept.iloc[0]['episode_age']
                for _, episode in original.iterrows():
                    if episode['episode_age'] != kept_age:
                        print(f"  - {person_name} ({episode['episode_age']}歳): episode_id={episode.get('episode_id', 'N/A')}")

    return cleaned_df

def validate_cleaned_data(df):
    """クリーニング後のデータを検証"""
    print("\n🔍 データ検証:")

    # 1. 重複チェック
    duplicates = df[df.duplicated(['person_name'], keep=False)]
    if len(duplicates) == 0:
        print("  ✅ 重複なし")
    else:
        print(f"  ❌ {len(duplicates)}件の重複が残存")
        return False

    # 2. 必須フィールドチェック
    required_fields = ['person_name', 'episode_age', 'episode_text']
    for field in required_fields:
        missing = df[field].isna().sum()
        if missing > 0:
            print(f"  ⚠️ {field}に{missing}件の欠損値")

    # 3. 文字数チェック
    text_lengths = df['episode_text'].str.len()
    short_episodes = (text_lengths < 132).sum()
    long_episodes = (text_lengths > 250).sum()

    if short_episodes > 0:
        print(f"  ⚠️ {short_episodes}件のエピソードが132文字未満")
    if long_episodes > 0:
        print(f"  ⚠️ {long_episodes}件のエピソードが250文字超過")

    return True

def main():
    """メイン処理"""
    try:
        # 重複削除実行
        cleaned_df = fix_duplicate_episodes()

        # データ検証
        is_valid = validate_cleaned_data(cleaned_df)

        if is_valid:
            print("\n" + "="*70)
            print("🎉 重複エピソード修正完了！")
            print("="*70)
            print("""
            処理完了:
            - すべての重複が削除されました
            - 各人物1エピソードの原則が守られています
            - 品質の高いエピソードが選択されました
            """)
        else:
            print("\n⚠️ 警告: データに問題が残っています。手動確認が必要です。")

        return 0

    except Exception as e:
        print(f"\n❌ エラーが発生しました: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
