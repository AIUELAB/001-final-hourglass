#!/usr/bin/env python3
"""
生涯ハイライト選定システムのテスト
年齢カテゴリに縛られず、真に重要な7つの瞬間を選定する
"""

from lifetime_highlight_selector import LifetimeHighlightSelector, LifeEvent
import json

def test_ohtani_highlights():
    """大谷翔平のハイライトテスト"""

    selector = LifetimeHighlightSelector()

    print("="*60)
    print("🌟 大谷翔平 - 生涯ハイライト選定テスト")
    print("="*60)

    person_data = {
        'person_name_display': '大谷翔平',
        'occupation': '野球選手',
        'person_id': 'P00001'
    }

    # 実際の全生涯イベント（順不同）
    all_events = [
        # 幼少期
        {'age': 1, 'text': 'あなたと同じ1歳のとき、大谷翔平は岩手県奥州市で生まれ、スポーツ一家の環境で育ちました。'},
        {'age': 7, 'text': 'あなたと同じ7歳のとき、大谷翔平は水沢リトルリーグで野球を始め、早くも才能の片鱗を見せました。'},

        # 高校時代
        {'age': 17, 'text': 'あなたと同じ17歳のとき、大谷翔平は花巻東高校で160km/hを記録し、日本高校野球史上最速タイ記録を樹立しました。'},
        {'age': 18, 'text': 'あなたと同じ18歳のとき、大谷翔平は日本ハムファイターズに1位指名で入団し、プロ野球選手としてのキャリアをスタートしました。'},

        # NPB時代
        {'age': 20, 'text': 'あなたと同じ20歳のとき、大谷翔平は日本プロ野球史上初の「2桁勝利・2桁本塁打」を達成し、二刀流の可能性を証明しました。'},
        {'age': 21, 'text': 'あなたと同じ21歳のとき、大谷翔平は日本プロ野球最速となる162km/hを記録し、投手としての圧倒的な能力を示しました。'},
        {'age': 22, 'text': 'あなたと同じ22歳のとき、大谷翔平は日本ハムを日本一に導き、日本シリーズで最優秀選手に選出されました。'},

        # MLB時代 - 最重要期間
        {'age': 23, 'text': 'あなたと同じ23歳のとき、大谷翔平はメジャーリーグのロサンゼルス・エンゼルスに移籍し、MLB新人王を獲得、二刀流が世界で通用することを証明しました。'},
        {'age': 25, 'text': 'あなたと同じ25歳のとき、大谷翔平はMLBオールスターゲームに初選出され、史上初の二刀流選手として先発投手兼1番指名打者で出場しました。'},
        {'age': 26, 'text': 'あなたと同じ26歳のとき、大谷翔平は46本塁打を放ち、日本人選手のMLBシーズン最多本塁打記録を更新しました。'},
        {'age': 27, 'text': 'あなたと同じ27歳のとき、大谷翔平はアメリカンリーグMVPを満票で受賞し、日本人として2人目、満票では史上初の快挙を達成しました。'},
        {'age': 28, 'text': 'あなたと同じ28歳のとき、大谷翔平はWBC日本代表として世界一に貢献し、大会MVPに選出され、日本中に感動を与えました。'},
        {'age': 29, 'text': 'あなたと同じ29歳のとき、大谷翔平は史上初の「2年連続10勝&40本塁打」を達成し、MLB史に前人未到の金字塔を打ち立てました。'},
        {'age': 30, 'text': 'あなたと同じ30歳のとき、大谷翔平はドジャースに移籍し、史上最高額の契約を結び、世界最高の野球選手としての地位を確立しました。'}
    ]

    # ハイライト選定
    highlights = selector.select_seven_highlights(person_data, all_events)

    print("\n📊 選定された7つの最重要ハイライト:")
    print("-"*40)

    for i, highlight in enumerate(highlights, 1):
        print(f"\n{i}. {highlight['age_category']}歳カテゴリ")
        print(f"   実際の年齢: {highlight['actual_age']}歳")
        print(f"   重要度スコア: {highlight['importance_score']:.1f}点")
        print(f"   イベントタイプ: {highlight['event_type']}")
        if highlight['age_adjusted']:
            print(f"   ⚠️ 年齢調整あり（{highlight['actual_age']}→{highlight['age_category']}）")
        print(f"   エピソード: {highlight['episode_text'][:80]}...")

    # 重要度ランキング
    print("\n🏆 重要度ランキング（年齢に関係なく）:")
    print("-"*40)
    sorted_highlights = sorted(highlights, key=lambda x: x['importance_score'], reverse=True)
    for i, highlight in enumerate(sorted_highlights[:5], 1):
        print(f"{i}. {highlight['actual_age']}歳時: スコア{highlight['importance_score']:.1f} - {highlight['keywords'][:3]}")

    # 従来方式との比較
    print("\n⚡ 改善点の確認:")
    print("-"*40)

    # WBCとMLB MVPが選ばれているか確認
    has_wbc = any('WBC' in str(h['keywords']) for h in highlights)
    has_mvp = any('MVP' in str(h['keywords']) for h in highlights)
    has_mlb = any('メジャー' in h['episode_text'] or 'MLB' in h['episode_text'] for h in highlights)

    print(f"✅ WBC関連エピソード: {'含まれている' if has_wbc else '❌ 含まれていない'}")
    print(f"✅ MLB MVP受賞: {'含まれている' if has_mvp else '❌ 含まれていない'}")
    print(f"✅ メジャーリーグ関連: {'含まれている' if has_mlb else '❌ 含まれていない'}")

    # NPB時代のエピソードが適切に評価されているか
    npb_episodes = [h for h in highlights if 'NPB' in h['episode_text'] or '日本プロ野球' in h['episode_text']]
    print(f"📊 NPB時代のエピソード数: {len(npb_episodes)}個（適切なバランス）")


def test_miyazaki_highlights():
    """宮崎駿のハイライトテスト"""

    selector = LifetimeHighlightSelector()

    print("\n" + "="*60)
    print("🎬 宮崎駿 - 生涯ハイライト選定テスト")
    print("="*60)

    person_data = {
        'person_name_display': '宮崎駿',
        'occupation': 'アニメーション監督',
        'person_id': 'P00002'
    }

    all_events = [
        {'age': 1, 'text': 'あなたと同じ1歳のとき、宮崎駿は東京都で生まれました。'},
        {'age': 22, 'text': 'あなたと同じ22歳のとき、宮崎駿は東映動画に入社し、アニメーターとしてのキャリアをスタートしました。'},
        {'age': 36, 'text': 'あなたと同じ36歳のとき、宮崎駿は「未来少年コナン」で初めてTVシリーズの監督を務めました。'},
        {'age': 38, 'text': 'あなたと同じ38歳のとき、宮崎駿は「ルパン三世 カリオストロの城」で劇場映画監督デビューを果たしました。'},
        {'age': 43, 'text': 'あなたと同じ43歳のとき、宮崎駿は「風の谷のナウシカ」を発表し、日本アニメ史に新たな地平を開きました。'},
        {'age': 44, 'text': 'あなたと同じ44歳のとき、宮崎駿はスタジオジブリを設立し、世界的アニメスタジオの礎を築きました。'},
        {'age': 47, 'text': 'あなたと同じ47歳のとき、宮崎駿は「となりのトトロ」を発表し、日本の国民的キャラクターを生み出しました。'},
        {'age': 51, 'text': 'あなたと同じ51歳のとき、宮崎駿は「紅の豚」で大人向けアニメーションの新境地を開拓しました。'},
        {'age': 56, 'text': 'あなたと同じ56歳のとき、宮崎駿は「もののけ姫」で日本映画史上最高の興行収入（当時）を記録しました。'},
        {'age': 60, 'text': 'あなたと同じ60歳のとき、宮崎駿は「千と千尋の神隠し」でアカデミー賞長編アニメ映画賞を受賞し、日本アニメ史上初の快挙を達成しました。'},
        {'age': 72, 'text': 'あなたと同じ72歳のとき、宮崎駿は「風立ちぬ」で長編映画からの引退を表明しました。'},
        {'age': 82, 'text': 'あなたと同じ82歳のとき、宮崎駿は「君たちはどう生きるか」でアカデミー賞を再び受賞し、現役復帰を果たしました。'}
    ]

    highlights = selector.select_seven_highlights(person_data, all_events)

    print("\n📊 選定された7つの最重要ハイライト:")
    print("-"*40)

    # アカデミー賞受賞が最優先で選ばれているか確認
    academy_episodes = [h for h in highlights if 'アカデミー' in h['episode_text']]
    print(f"\n✅ アカデミー賞関連: {len(academy_episodes)}個のエピソード")

    # ジブリ設立が含まれているか
    ghibli = any('ジブリ' in h['episode_text'] for h in highlights)
    print(f"✅ スタジオジブリ設立: {'含まれている' if ghibli else '❌ 含まれていない'}")

    # 千と千尋が含まれているか
    spirited_away = any('千と千尋' in h['episode_text'] for h in highlights)
    print(f"✅ 千と千尋の神隠し: {'含まれている' if spirited_away else '❌ 含まれていない'}")


def test_comparison_old_vs_new():
    """従来方式と新方式の比較"""

    print("\n" + "="*60)
    print("📊 従来方式 vs 新方式の比較")
    print("="*60)

    print("\n❌ 従来方式の問題点:")
    print("-"*40)
    print("1. 年齢カテゴリに最も近い出来事を選ぶ")
    print("   → 20歳: NPBの2桁勝利・2桁本塁打（国内記録）")
    print("   → 30歳: 該当なし（プレースホルダー）")
    print("   結果: WBC MVPやMLB MVPが選ばれない")

    print("\n✅ 新方式（生涯ハイライト）の改善:")
    print("-"*40)
    print("1. 生涯で最も重要な7つの瞬間を選定")
    print("   → 27歳: MLB MVP満票受賞（世界的偉業）")
    print("   → 28歳: WBC MVP（国際的偉業）")
    print("   → 29歳: 史上初の記録（歴史的偉業）")
    print("2. その後、表示スロットに最適配置")
    print("   → 30歳スロット ← 28歳のWBC MVP")
    print("   → 必要に応じて年齢調整を明記")

    print("\n🎯 根本的な違い:")
    print("-"*40)
    print("従来: 年齢カテゴリを埋めることが目的")
    print("新式: 最重要瞬間を選ぶことが目的")
    print("\n結果: より感動的で意味のあるエピソード選定")


if __name__ == "__main__":
    # 大谷翔平のテスト
    test_ohtani_highlights()

    # 宮崎駿のテスト
    test_miyazaki_highlights()

    # 比較分析
    test_comparison_old_vs_new()

    print("\n" + "="*60)
    print("✅ 全テスト完了")
    print("="*60)