#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
エピソード検証システムのテスト
検証システムが正しく動作することを確認
"""

from episode_validator import EpisodeValidator


def test_valid_episodes():
    """正しいエピソードのテスト"""
    print("=" * 60)
    print("✅ 正しいエピソードのテスト")
    print("=" * 60)

    valid_episodes = [
        "あなたと同じ41歳のとき、黒澤明は『羅生門』で1951年にヴェネツィア国際映画祭金獅子賞を受賞した。日本映画として初めて国際的評価を獲得し、世界に日本映画の存在を知らしめた。複数の視点から真実を描く斬新な構成は、世界の映画界に衝撃を与えた。",
        "あなたと同じ52歳のとき、稲盛和夫は第二電電（現KDDI）を創業し、通信業界の規制緩和に挑戦した。京セラでの成功に続く第二の起業で、NTTの独占体制を打破した。携帯電話料金を3分の1に引き下げ、通信の民主化を実現した。利他の心を経営哲学とし、27年間赤字なしの経営で日本の通信革命を主導した。",
    ]

    for i, episode in enumerate(valid_episodes, 1):
        print(f"\n例 {i}: {episode[:50]}...")
        print(f"文字数: {len(episode)}")

        validation = EpisodeValidator.validate_episode(episode)
        all_valid = all(result[0] for result in validation.values())

        for check_name, (is_valid, reason) in validation.items():
            status = "✅" if is_valid else "❌"
            print(f"  {status} {check_name}: {reason}")

        if all_valid:
            print(f"  ✅ 総合判定: 合格")
        else:
            print(f"  ❌ 総合判定: 不合格")


def test_invalid_episodes():
    """問題のあるエピソードのテスト"""
    print("\n" + "=" * 60)
    print("❌ 問題のあるエピソードのテスト")
    print("=" * 60)

    invalid_episodes = [
        # 名詞で終わる（元のWeek 4の問題）
        "あなたと同じ47歳のとき、久石譲は『もののけ姫』で日本アカデミー賞最優秀音楽賞を受賞した。宮崎駿作品の音楽を30年以上手がけ、世界中のファンを魅了。年間100回以上のコンサートで指揮を執り、クラシックと映画音楽の垣根を超えた。日本音楽を世界に広めた現代最高の作曲家。",
        # 文字数不足
        "あなたと同じ44歳のとき、孫正義はボーダフォン日本法人を1兆7500億円で買収した。",
        # 開始文なし
        "44歳のとき、三島由紀夫は『豊饒の海』四部作を完成させた。20年構想の集大成として、輪廻転生を通じて日本の精神性を描いた。",
        # 数字不足
        "あなたと同じ五十二歳のとき、中山啓子は細胞老化メカニズムの解明で日本医学会賞を受賞した。",
    ]

    for i, episode in enumerate(invalid_episodes, 1):
        print(f"\n例 {i}: {episode[:50]}...")
        print(f"文字数: {len(episode)}")

        validation = EpisodeValidator.validate_episode(episode)
        all_valid = all(result[0] for result in validation.values())

        for check_name, (is_valid, reason) in validation.items():
            status = "✅" if is_valid else "❌"
            print(f"  {status} {check_name}: {reason}")

        if all_valid:
            print(f"  ✅ 総合判定: 合格")
        else:
            print(f"  ❌ 総合判定: 不合格")


def test_auto_fix():
    """自動修正機能のテスト"""
    print("\n" + "=" * 60)
    print("🔧 自動修正機能のテスト")
    print("=" * 60)

    test_cases = [
        {
            "original": "あなたと同じ47歳のとき、久石譲は『もののけ姫』で日本アカデミー賞最優秀音楽賞を受賞した。日本音楽を世界に広めた現代最高の作曲家。",
            "issue": "名詞で終わる"
        },
        {
            "original": "あなたと同じ44歳のとき、孫正義はボーダフォン日本法人を買収した。世界のIT業界をリードする起業家。",
            "issue": "名詞で終わる"
        },
        {
            "original": "あなたと同じ61歳のとき、明石康は国連カンボジア暫定統治機構代表として活躍した。国際平和構築の第一人者として世界に貢献した外交官。",
            "issue": "名詞で終わる"
        }
    ]

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n例 {i}: {test_case['issue']}")
        original = test_case["original"]
        print(f"元の文末: ...{original[-30:]}")

        # 文末検証
        is_valid, reason = EpisodeValidator.validate_sentence_ending(original)
        print(f"  検証結果: {'✅' if is_valid else '❌'} {reason}")

        if not is_valid:
            # 修正
            fixed = EpisodeValidator.fix_sentence_ending(original)
            print(f"修正後: ...{fixed[-40:]}")

            # 再検証
            is_valid, reason = EpisodeValidator.validate_sentence_ending(fixed)
            print(f"  再検証: {'✅' if is_valid else '❌'} {reason}")


def test_batch_validation():
    """バッチ検証のテスト"""
    print("\n" + "=" * 60)
    print("📊 バッチ検証のテスト")
    print("=" * 60)

    from batch_week4_validated import create_week4_batch_validated

    # Week 4のエピソードを生成
    episodes = create_week4_batch_validated()

    # 統計
    total = len(episodes)
    valid = sum(1 for ep in episodes if ep["is_valid"])
    invalid = total - valid

    print(f"\n検証結果:")
    print(f"  総数: {total}件")
    print(f"  有効: {valid}件 ({(valid/total)*100:.1f}%)")
    print(f"  無効: {invalid}件")

    # 個別チェック
    if invalid > 0:
        print(f"\n❌ 無効なエピソード:")
        for ep in episodes:
            if not ep["is_valid"]:
                print(f"  - {ep['person_name']}: {ep['character_count']}文字")
                validation = EpisodeValidator.validate_episode(ep["episode_text"])
                for check_name, (is_valid, reason) in validation.items():
                    if not is_valid:
                        print(f"    ❌ {check_name}: {reason}")
    else:
        print(f"\n✅ すべてのエピソードが検証を通過しました！")


def main():
    """テストメイン関数"""
    print("エピソード検証システム - 総合テスト")
    print("=" * 80)

    # 各テストを実行
    test_valid_episodes()
    test_invalid_episodes()
    test_auto_fix()
    test_batch_validation()

    print("\n" + "=" * 80)
    print("✅ テスト完了")


if __name__ == "__main__":
    main()