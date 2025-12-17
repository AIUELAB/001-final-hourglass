"""
データモデルのデモンストレーション

エピソード収集パイプラインのデータモデルの基本的な使用例を示します。
"""

from pathlib import Path
from src.models import EpisodeSource, VerifiedSource, CuratedEpisode


def demo_episode_source():
    """EpisodeSourceのデモ"""
    print("=" * 60)
    print("1. EpisodeSource - 情報源管理")
    print("=" * 60)

    # インスタンス生成
    source = EpisodeSource(
        person_name="イチロー",
        person_id="P001ABC12",
        person_type="REAL",
        source_url="https://ja.wikipedia.org/wiki/イチロー",
        source_type="wikipedia",
        raw_text="2004年シーズン262安打記録",
        context="年齢31歳時の業績",
    )

    print(f"\n作成された情報源:")
    print(f"  - ソースID: {source.source_id}")
    print(f"  - 人物名: {source.person_name}")
    print(f"  - 根拠品質: {source.evidence_quality}")
    print(f"  - 検証ステータス: {source.verification_status}")
    print(f"  - 収集日時: {source.collected_at.isoformat()}")

    # 辞書変換
    data = source.to_dict()
    print(f"\n辞書形式のフィールド数: {len(data)}")

    # 冪等性テスト
    source_id1 = EpisodeSource.generate_source_id("イチロー", "https://ja.wikipedia.org/wiki/イチロー")
    source_id2 = EpisodeSource.generate_source_id("イチロー", "https://ja.wikipedia.org/wiki/イチロー")
    print(f"\n冪等性テスト:")
    print(f"  - source_id1: {source_id1}")
    print(f"  - source_id2: {source_id2}")
    print(f"  - 一致: {source_id1 == source_id2}")

    return source


def demo_verified_source():
    """VerifiedSourceのデモ"""
    print("\n" + "=" * 60)
    print("2. VerifiedSource - 検証済み情報源")
    print("=" * 60)

    # A品質（政府公式サイト）
    source_a = VerifiedSource(
        person_name="テスト太郎",
        person_id="P002ABC12",
        person_type="REAL",
        source_url="https://www.mext.go.jp/test",  # .go.jp
        source_type="manual",
        raw_text="テストテキストA",
    )

    # B品質（Wikipedia）
    source_b = VerifiedSource(
        person_name="テスト次郎",
        person_id="P003ABC12",
        person_type="REAL",
        source_url="https://ja.wikipedia.org/wiki/test",
        source_type="wikipedia",
        raw_text="テストテキストB",
    )

    # C品質（その他）
    source_c = VerifiedSource(
        person_name="テスト三郎",
        person_id="P004ABC12",
        person_type="REAL",
        source_url="https://example.com/test",
        source_type="manual",
        raw_text="テストテキストC",
    )

    print(f"\n自動品質判定:")
    print(f"  - .go.jp ドメイン: {source_a.evidence_quality} (期待: A)")
    print(f"  - Wikipedia: {source_b.evidence_quality} (期待: B)")
    print(f"  - その他ドメイン: {source_c.evidence_quality} (期待: C)")

    # 検証マーク
    source_a.mark_verified("政府公式サイト確認済み")
    print(f"\n検証マーク後:")
    print(f"  - 検証ステータス: {source_a.verification_status}")
    print(f"  - 検証者ノート: {source_a.verifier_notes}")

    # フィルタリング
    sources = [source_a, source_b, source_c]
    high_quality = VerifiedSource.filter_by_quality(sources, min_quality="B")
    print(f"\nフィルタリング結果:")
    print(f"  - 全件数: {len(sources)}")
    print(f"  - B品質以上: {len(high_quality)}")

    return source_a


def demo_curated_episode():
    """CuratedEpisodeのデモ"""
    print("\n" + "=" * 60)
    print("3. CuratedEpisode - 生成済みエピソード")
    print("=" * 60)

    # インスタンス生成
    episode = CuratedEpisode(
        person_id="P001ABC12",
        person_name="イチロー",
        age=31,
        episode_text="あなたと同じ31歳のとき、イチローは2004年シーズンに262安打を記録し、84年ぶりにメジャーリーグの最多安打記録を更新した。",
        source_id="SRC-abc123def456",
        source_url="https://ja.wikipedia.org/wiki/イチロー",
        evidence_quality="B",
        person_type="REAL",
        category="スポーツ",
        episode_type="転機",
    )

    print(f"\n作成されたエピソード:")
    print(f"  - エピソードID: {episode.episode_id if episode.episode_id else '（未採番）'}")
    print(f"  - 人物名: {episode.person_name}")
    print(f"  - 年齢: {episode.age}")
    print(f"  - 根拠品質: {episode.evidence_quality}")
    print(f"  - バリデーションステータス: {episode.validation_status}")
    print(f"  - エピソード本文（抜粋）: {episode.episode_text[:50]}...")

    # バリデーション結果マーク
    episode.mark_passed()
    print(f"\nバリデーション合格後:")
    print(f"  - ステータス: {episode.validation_status}")

    # マスター形式変換
    master_data = episode.to_master_format()
    print(f"\nマスター形式変換:")
    print(f"  - source: {master_data['source']}")
    print(f"  - fact_check_result: {master_data['fact_check_result']}")
    print(f"  - verification_status: {master_data['verification_status']}")
    print(f"  - 全フィールド数: {len(master_data)}")

    return episode


def demo_csv_operations():
    """CSV操作のデモ"""
    print("\n" + "=" * 60)
    print("4. CSV操作 - 保存・読み込み")
    print("=" * 60)

    # テスト用ディレクトリ
    test_dir = Path("examples/demo_output")
    test_dir.mkdir(parents=True, exist_ok=True)

    # EpisodeSource保存
    source = EpisodeSource(
        person_name="テスト",
        person_id="P999ABC12",
        person_type="REAL",
        source_url="https://example.com/test",
        source_type="manual",
        raw_text="テストテキスト",
    )
    source_csv = test_dir / "episode_sources.csv"
    EpisodeSource.save_to_csv([source], source_csv)
    print(f"\nEpisodeSource保存:")
    print(f"  - ファイル: {source_csv}")
    print(f"  - 存在: {source_csv.exists()}")

    # EpisodeSource読み込み
    loaded_sources = EpisodeSource.load_from_csv(source_csv)
    print(f"\nEpisodeSource読み込み:")
    print(f"  - 件数: {len(loaded_sources)}")
    print(f"  - 最初の人物名: {loaded_sources[0].person_name if loaded_sources else '（なし）'}")

    # CuratedEpisode保存
    episode = CuratedEpisode(
        person_id="P999ABC12",
        person_name="テスト",
        age=30,
        episode_text="あなたと同じ30歳のとき、テストは...",
        source_id="SRC-test123",
        source_url="https://example.com/test",
        evidence_quality="C",
    )
    episode_csv = test_dir / "curated_episodes.csv"
    CuratedEpisode.save_to_csv([episode], episode_csv)
    print(f"\nCuratedEpisode保存:")
    print(f"  - ファイル: {episode_csv}")
    print(f"  - 存在: {episode_csv.exists()}")

    # CuratedEpisode読み込み
    loaded_episodes = CuratedEpisode.load_from_csv(episode_csv)
    print(f"\nCuratedEpisode読み込み:")
    print(f"  - 件数: {len(loaded_episodes)}")
    print(f"  - 最初の人物名: {loaded_episodes[0].person_name if loaded_episodes else '（なし）'}")

    print(f"\n作成されたファイル:")
    for csv_file in test_dir.glob("*.csv"):
        print(f"  - {csv_file}")


def main():
    """メイン処理"""
    print("\n" + "=" * 60)
    print("エピソード収集パイプライン - データモデルデモ")
    print("=" * 60)

    # 各モデルのデモ
    demo_episode_source()
    demo_verified_source()
    demo_curated_episode()
    demo_csv_operations()

    print("\n" + "=" * 60)
    print("デモ完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
