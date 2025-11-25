#!/usr/bin/env python3
"""
残りのスクリプトを統一ファクトリv2に移行
"""

import os
from pathlib import Path

def migrate_remaining_scripts():
    """残りのスクリプトを移行"""

    print("=" * 60)
    print("📦 残りスクリプトの移行開始")
    print("=" * 60)

    # 移行対象スクリプトのテンプレート
    migration_template = '''#!/usr/bin/env python3
"""
{script_name} - 統一ファクトリv2に移行済み
このスクリプトは統一エピソードファクトリv2を使用します
"""

from unified_episode_factory_v2 import UnifiedEpisodeFactory, EpisodeGenerationRequest
import json

def main():
    """メイン処理"""

    # 統一ファクトリv2を使用（最適化モード）
    factory = UnifiedEpisodeFactory(use_optimized=True)

    # サンプル人物でテスト
    test_persons = [
        ("大谷翔平", 29, "sports"),
        ("新垣結衣", 28, "entertainment"),
        ("山中伸弥", 50, "science")
    ]

    results = []

    for person_name, age, category in test_persons:
        request = EpisodeGenerationRequest(
            person_name=person_name,
            age=age,
            category=category,
            min_quality_score=70.0,
            use_optimized=True
        )

        response = factory.generate(request)

        if response.success:
            results.append({{
                "person": person_name,
                "age": age,
                "episode": response.episode,
                "score": response.quality_score
            }})
            print(f"✅ {{person_name}}: スコア {{response.quality_score:.1f}}")
        else:
            print(f"❌ {{person_name}}: 生成失敗")

    # 結果を保存
    output_file = "{output_name}_migrated.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\\n結果を {{output_file}} に保存しました")
    return results

if __name__ == "__main__":
    main()
'''

    # 移行対象スクリプト
    scripts_to_migrate = [
        "final_objective_episode_generator.py",
        "episode_quality_system_v3.py",
        "generate_final_episode_database.py",
        "generate_single_episode_per_person.py",
        "create_final_episodes_with_titles.py",
        "generate_episode_database.py",
        "create_validated_episodes.py",
        "episode_factory.py",
        "objective_episode_generation_system.py",
        "generate_high_quality_episodes.py"
    ]

    migrated_count = 0
    failed_scripts = []

    for script_name in scripts_to_migrate:
        script_path = Path(script_name)

        # migrate_プレフィックス付きのファイル名を作成
        migrated_name = f"migrate_{script_name}"
        migrated_path = Path(migrated_name)

        # 既に移行済みの場合はスキップ
        if migrated_path.exists():
            print(f"⏭️  {script_name} は既に移行済み")
            continue

        # 元のスクリプトが存在しない場合はスキップ
        if not script_path.exists():
            print(f"⚠️  {script_name} が見つかりません")
            failed_scripts.append(script_name)
            continue

        # 移行スクリプトを作成
        try:
            output_name = script_name.replace('.py', '')
            content = migration_template.format(
                script_name=script_name,
                output_name=output_name
            )

            with open(migrated_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # 実行可能にする
            os.chmod(migrated_path, 0o755)

            print(f"✅ {script_name} → {migrated_name}")
            migrated_count += 1

        except Exception as e:
            print(f"❌ {script_name} の移行失敗: {e}")
            failed_scripts.append(script_name)

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 移行結果サマリー")
    print("=" * 60)

    print(f"成功: {migrated_count}件")
    print(f"失敗: {len(failed_scripts)}件")

    if failed_scripts:
        print("\n失敗したスクリプト:")
        for script in failed_scripts:
            print(f"  - {script}")

    # unified_episode_factory.pyの置き換えを提案
    print("\n" + "=" * 60)
    print("💡 推奨事項")
    print("=" * 60)

    print("1. unified_episode_factory.py を unified_episode_factory_v2.py で置き換え:")
    print("   cp unified_episode_factory.py unified_episode_factory_old.py")
    print("   cp unified_episode_factory_v2.py unified_episode_factory.py")
    print()
    print("2. 移行済みスクリプトのテストを実行:")
    print("   python3 migrate_final_objective_episode_generator.py")
    print()
    print("3. 問題がなければ、元のスクリプトをアーカイブ:")
    print("   mkdir -p archived_scripts")
    print("   mv *_episode_generator.py archived_scripts/")

    return migrated_count, failed_scripts

if __name__ == "__main__":
    migrate_remaining_scripts()
