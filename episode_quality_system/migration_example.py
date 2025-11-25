#!/usr/bin/env python3
"""
既存スクリプトの統合システムへの移行例
既存の生成スクリプトを統合バリデーションシステムに移行する方法を示す
"""

import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import Dict, List

# 統合システムをインポート
from unified_episode_factory import UnifiedEpisodeFactory, EpisodeGenerationRequest


class MigrationExample:
    """移行例クラス"""

    def __init__(self):
        """初期化"""
        # 統合ファクトリを使用（これが唯一の生成方法）
        self.factory = UnifiedEpisodeFactory()
        self.results = []

    def migrate_old_style(self):
        """
        【旧方式】バリデーションなしの直接生成
        このような直接生成は禁止
        """
        print("=" * 60)
        print("❌ 旧方式（禁止）: バリデーションなしの直接生成")
        print("=" * 60)

        # このような直接生成は絶対に行わない
        old_episode = {
            'person_name': '大谷翔平',
            'age': 29,
            'episode': 'あなたと同じ29歳のとき、大谷翔平は素晴らしい活躍をした。'  # テンプレート文章
        }

        print(f"旧エピソード: {old_episode['episode']}")
        print("⚠️ 問題: テンプレート文章、固有名詞なし、文字数不足")
        print()

    def migrate_new_style(self):
        """
        【新方式】統合システムを使用した生成
        必ずこの方式を使用する
        """
        print("=" * 60)
        print("✅ 新方式（推奨）: 統合システム経由の生成")
        print("=" * 60)

        # テストデータ
        test_persons = [
            {'name': '大谷翔平', 'age': 29, 'category': 'sports'},
            {'name': '村上春樹', 'age': 38, 'category': 'literature'},
            {'name': '新海誠', 'age': 43, 'category': 'entertainment'}
        ]

        for person in test_persons:
            print(f"\n■ {person['name']} ({person['age']}歳)")

            # 統合システムでリクエスト作成
            request = EpisodeGenerationRequest(
                person_name=person['name'],
                age=person['age'],
                category=person['category'],
                min_quality_score=70.0,  # 最低品質スコア
                max_attempts=5,           # 最大試行回数
                strict_mode=True          # 厳格モード
            )

            # エピソード生成（自動でバリデーション実行）
            response = self.factory.generate(request)

            if response.success:
                print(f"✅ 生成成功")
                print(f"  エピソード: {response.episode[:80]}...")
                print(f"  品質スコア: {response.quality_score:.1f}/100")
                print(f"  バリデーション: すべてパス")

                self.results.append({
                    'person_name': person['name'],
                    'age': person['age'],
                    'episode': response.episode,
                    'quality_score': response.quality_score,
                    'validation_passed': True
                })
            else:
                print(f"❌ 生成失敗")
                print(f"  エラー: {response.error_message}")
                print(f"  試行回数: {response.attempts}")

                # 改善履歴を表示
                if response.improvement_history:
                    print(f"  改善試行:")
                    for history in response.improvement_history[-3:]:
                        print(f"    - {history['action']}: {history.get('reason', '')}")

    def save_results(self, output_path: str = None):
        """
        結果をCSVに保存（BOM付きでExcel対応）

        Args:
            output_path: 出力パス
        """
        if not self.results:
            print("保存するデータがありません")
            return

        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"migrated_episodes_{timestamp}.csv"

        df = pd.DataFrame(self.results)

        # UTF-8 BOM付きで保存（Excel対応）
        with open(output_path, 'w', encoding='utf-8-sig') as f:
            df.to_csv(f, index=False)

        print(f"\n✅ 結果をCSVに保存: {output_path}")
        print(f"  総エピソード数: {len(self.results)}")
        print(f"  バリデーション合格率: 100%（統合システム使用）")

    def show_migration_guide(self):
        """移行ガイドを表示"""
        print("\n" + "=" * 60)
        print("📋 既存スクリプトの移行ガイド")
        print("=" * 60)

        guide = """
        1. 【インポート変更】
           旧: 独自の生成ロジック
           新: from unified_episode_factory import UnifiedEpisodeFactory

        2. 【初期化】
           factory = UnifiedEpisodeFactory()

        3. 【リクエスト作成】
           request = EpisodeGenerationRequest(
               person_name="人物名",
               age=年齢,
               category="カテゴリ",  # sports, entertainment, literature等
               min_quality_score=70.0
           )

        4. 【生成実行】
           response = factory.generate(request)

        5. 【結果確認】
           if response.success:
               episode = response.episode
               score = response.quality_score

        ⚠️ 重要な注意事項:
        - 直接エピソードを作成しない
        - ハードコードされたエピソードを削除
        - 必ず統合システムを経由する
        - バリデーションをスキップしない
        """

        print(guide)

        print("\n✅ 移行のメリット:")
        print("  1. テンプレート文章の自動排除")
        print("  2. 固有名詞（作品名・大会名）の必須化")
        print("  3. 品質スコアの保証")
        print("  4. 自動改善機能")
        print("  5. 監査ログによる追跡可能性")


def demonstrate_migration():
    """移行デモンストレーション"""
    print("\n" + "🔄" * 30)
    print("統合バリデーションシステムへの移行デモ")
    print("🔄" * 30 + "\n")

    migrator = MigrationExample()

    # 旧方式の問題を示す
    migrator.migrate_old_style()

    # 新方式の実演
    migrator.migrate_new_style()

    # 結果を保存
    migrator.save_results()

    # 移行ガイド表示
    migrator.show_migration_guide()

    # 統計表示
    print("\n" + "=" * 60)
    print("📊 ファクトリ統計:")
    stats = migrator.factory.get_stats()
    for key, value in stats.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.1f}")
        else:
            print(f"  {key}: {value}")


def migrate_specific_script(script_path: str):
    """
    特定のスクリプトを移行

    Args:
        script_path: 移行対象のスクリプトパス
    """
    print(f"\n📝 スクリプト移行: {script_path}")
    print("=" * 60)

    # ファイル読み込み
    with open(script_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 移行が必要な箇所を検出
    issues = []

    # ハードコードされたエピソード
    if 'episode = "' in content or "episode = '" in content:
        issues.append("ハードコードされたエピソードを検出")

    # 直接辞書作成
    if "'episode':" in content and "unified_episode_factory" not in content:
        issues.append("統合システムを使わない直接生成を検出")

    # バリデーションのインポートなし
    if "validation" not in content.lower() and "unified" not in content:
        issues.append("バリデーションシステムの未使用")

    if issues:
        print("⚠️ 移行が必要な問題:")
        for issue in issues:
            print(f"  - {issue}")

        print("\n✅ 推奨される修正:")
        print("  1. unified_episode_factory をインポート")
        print("  2. UnifiedEpisodeFactory() で初期化")
        print("  3. EpisodeGenerationRequest でリクエスト作成")
        print("  4. factory.generate() で生成")
    else:
        print("✅ このスクリプトは既に統合システムを使用しています")


if __name__ == "__main__":
    # 移行デモを実行
    demonstrate_migration()

    # 特定のスクリプトの移行チェック例
    # migrate_specific_script("create_final_episodes_with_titles.py")
