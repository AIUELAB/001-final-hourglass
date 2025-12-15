#!/usr/bin/env python3
"""
3件のエピソードをより適切な年齢・出来事に変更
"""

import pandas as pd
from datetime import datetime
from pdca_guardian import PDCAGuardian

def create_updated_episodes():
    """新しいエピソードを作成"""

    updated_episodes = {
        "村上春樹": {
            "old_age": 30,
            "new_age": 38,
            "new_episode": "あなたと同じ38歳のとき、村上春樹は「ノルウェイの森」を発表し、累計1000万部を超える大ベストセラーとなった。シチリア島とローマで執筆された本作は、喪失と再生を描いた恋愛小説として世代を超えて読み継がれた。50以上の言語に翻訳され、日本文学の世界的認知度を飛躍的に高めた。",
            "category": "文学"
        },
        "さくらももこ": {
            "old_age": 39,
            "new_age": 21,
            "new_episode": "あなたと同じ21歳のとき、さくらももこは「りぼん」8月号で「ちびまる子ちゃん」の連載を開始した。会社を2か月で退職し漫画家の道を選んだ決断が、後に視聴率39.9％の国民的アニメを生んだ。静岡の小学生時代を描いた作品は、3世代が共感できる普遍的な家族像を創り出し、日本の文化的財産となった。",
            "category": "漫画"
        },
        "YOSHIKI": {
            "old_age": 30,
            "new_age": 23,
            "new_episode": "あなたと同じ23歳のとき、YOSHIKIはX JAPANとして「BLUE BLOOD」でメジャーデビューを果たした。インディーズから這い上がり、ビジュアル系ロックという新ジャンルを確立。アルバムは100万枚を突破し、日本のロック史に新たな1ページを刻んだ。世界進出への第一歩となる歴史的瞬間だった。",
            "category": "音楽"
        }
    }

    return updated_episodes

def update_csv(updated_episodes):
    """CSVファイルを更新"""

    # 既存のCSVを読み込み
    df = pd.read_csv('trusted_episodes_latest.csv', encoding='utf-8-sig')
    print(f"元のエピソード数: {len(df)}件")

    # バックアップを作成
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f'trusted_episodes_backup_{timestamp}.csv'
    df.to_csv(backup_file, index=False, encoding='utf-8-sig')
    print(f"バックアップを作成: {backup_file}")

    # 各エピソードを更新
    for person_name, update_info in updated_episodes.items():
        old_age = update_info["old_age"]
        new_age = update_info["new_age"]
        new_episode = update_info["new_episode"]

        # 該当する行を見つける
        mask = (df['person_name'] == person_name) & (df['episode_age'] == old_age)

        if df[mask].empty:
            print(f"⚠️ {person_name}（{old_age}歳）のエピソードが見つかりません")
            continue

        # 更新
        df.loc[mask, 'episode_age'] = new_age
        df.loc[mask, 'user_age'] = new_age  # user_ageも同じ値に更新
        df.loc[mask, 'episode_text'] = new_episode
        df.loc[mask, 'character_count'] = len(new_episode)
        df.loc[mask, 'created_date'] = datetime.now().strftime("%Y%m%d_%H%M%S")

        print(f"✅ {person_name}: {old_age}歳 → {new_age}歳に変更")
        print(f"   文字数: {len(new_episode)}文字")

    # CSVファイルを保存
    df.to_csv('trusted_episodes_latest.csv', index=False, encoding='utf-8-sig')
    print("\n更新されたCSVを保存しました: trusted_episodes_latest.csv")

    return df

def check_violations(df, updated_episodes):
    """更新されたエピソードの違反をチェック"""

    print("\n" + "="*70)
    print("🔍 更新後の違反チェック")
    print("="*70)

    guardian = PDCAGuardian()

    for person_name in updated_episodes.keys():
        new_age = updated_episodes[person_name]["new_age"]

        # 該当エピソードを取得
        episode_row = df[(df['person_name'] == person_name) & (df['episode_age'] == new_age)]

        if episode_row.empty:
            continue

        episode_text = episode_row.iloc[0]['episode_text']
        person_name_display = f"{person_name}（{new_age}歳）"

        # 違反チェック
        violations = guardian.check_episode_quality(
            episode_text=episode_text,
            age=new_age,
            person_name_display=person_name_display
        )

        print(f"\n【{person_name_display}】")
        print(f"違反数: {len(violations)}件")

        if violations:
            for v in violations[:3]:  # 最初の3件を表示
                print(f"  - {v.get('rule_id', 'UNKNOWN')}: {v.get('type', '')}")
        else:
            print("  ✅ 違反なし")

def main():
    # 新しいエピソードを作成
    updated_episodes = create_updated_episodes()

    print("="*70)
    print("📝 3件のエピソード更新")
    print("="*70)

    # 新しいエピソードを表示
    for person_name, info in updated_episodes.items():
        print(f"\n【{person_name}】")
        print(f"  年齢: {info['old_age']}歳 → {info['new_age']}歳")
        print(f"  新エピソード（{len(info['new_episode'])}文字）:")
        print(f"  {info['new_episode']}")

    # CSVファイルを更新
    df = update_csv(updated_episodes)

    # 違反チェック
    check_violations(df, updated_episodes)

    print("\n" + "="*70)
    print("✅ 更新完了")
    print("="*70)

if __name__ == "__main__":
    main()
