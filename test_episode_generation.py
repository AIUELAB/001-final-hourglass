#!/usr/bin/env python3
"""
エピソード生成システムのテストスクリプト
API無しでシステムの動作を確認
"""

import os
import sys
import sqlite3
import json
from datetime import datetime

# 環境変数を設定（ダミーモード）
os.environ['EPISODE_GENERATION_TEST_MODE'] = 'true'

# ローカルインポート
from episode_database_integration import EpisodeDatabaseIntegration
from episode_quality_evaluator import EpisodeQualityEvaluator

def test_system_integration():
    """システム統合テスト"""
    print("=" * 60)
    print("エピソード生成システム統合テスト")
    print("=" * 60)

    # 1. データベース初期化とCSV読み込み
    print("\n[1] データベース初期化")
    integration = EpisodeDatabaseIntegration()

    # 最新のCSVファイルを読み込み
    csv_path = "ultra_think_WITH_FIRECRAWL_FIXED_20250917_200409.csv"
    if os.path.exists(csv_path):
        df = integration.load_ultra_think_csv(csv_path)
        print(f"✅ CSVファイル読み込み成功: {len(df)}件")

        # データベース同期
        integration.sync_persons_to_database(df)
        print("✅ データベース同期完了")
    else:
        print(f"❌ CSVファイルが見つかりません: {csv_path}")
        return

    # 2. データベース統計確認
    print("\n[2] データベース統計")
    conn = sqlite3.connect("episode_database.db")
    cursor = conn.cursor()

    # 人物数の確認
    cursor.execute("SELECT COUNT(*) FROM persons")
    total_persons = cursor.fetchone()[0]
    print(f"総人物数: {total_persons}")

    # 生年がある人物数
    cursor.execute("SELECT COUNT(*) FROM persons WHERE birth_year IS NOT NULL")
    with_birth_year = cursor.fetchone()[0]
    print(f"生年設定済み: {with_birth_year}人")

    # カテゴリ分布
    print("\nカテゴリ別人物数:")
    cursor.execute("""
        SELECT category, COUNT(*) as count
        FROM persons
        GROUP BY category
        ORDER BY count DESC
        LIMIT 10
    """)
    for category, count in cursor.fetchall():
        print(f"  - {category}: {count}人")

    # 認識スコア分布
    cursor.execute("""
        SELECT
            MIN(recognition_score) as min_score,
            MAX(recognition_score) as max_score,
            AVG(recognition_score) as avg_score
        FROM persons
        WHERE recognition_score IS NOT NULL
    """)
    min_score, max_score, avg_score = cursor.fetchone()
    print(f"\n認識スコア:")
    print(f"  最小: {min_score:.2f}")
    print(f"  最大: {max_score:.2f}")
    print(f"  平均: {avg_score:.2f}")

    # 3. テスト用エピソード生成（ダミーデータ）
    print("\n[3] テスト用エピソード生成")

    # 高スコアの人物を3人選択
    cursor.execute("""
        SELECT person_id, person_name_ja, birth_year, category, recognition_score
        FROM persons
        WHERE birth_year IS NOT NULL
        ORDER BY recognition_score DESC
        LIMIT 3
    """)

    test_persons = cursor.fetchall()

    for person_id, name, birth_year, category, score in test_persons:
        print(f"\n{name} (ID: {person_id})")
        print(f"  生年: {int(birth_year)}, カテゴリ: {category}, スコア: {score:.2f}")

        # ダミーエピソード生成
        test_episodes = [
            {
                'age': 20,
                'episode_text': f"あなたと同じ20歳のとき、{name}は新しい挑戦を始めました。",
                'quality_score': 75.0,
                'grade': 'B'
            },
            {
                'age': 30,
                'episode_text': f"あなたと同じ30歳のとき、{name}は大きな成果を収めました。",
                'quality_score': 80.0,
                'grade': 'A'
            }
        ]

        # エピソードをデータベースに保存（既存があれば更新）
        for episode in test_episodes:
            episode_id = f"E{person_id}_{episode['age']:03d}"
            cursor.execute("""
                INSERT OR REPLACE INTO episodes (
                    episode_id, person_id, age, episode_text, quality_score, grade,
                    source, is_active, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                episode_id,
                person_id,
                episode['age'],
                episode['episode_text'],
                episode['quality_score'],
                episode['grade'],
                'test',
                True,
                datetime.now().isoformat()
            ))

        print(f"  → {len(test_episodes)}件のテストエピソード生成")

    conn.commit()

    # 4. エピソード品質評価テスト
    print("\n[4] エピソード品質評価")
    evaluator = EpisodeQualityEvaluator()

    # サンプルエピソードの評価
    sample_episode = {
        'episode_text': "あなたと同じ25歳のとき、大谷翔平はメジャーリーグで二刀流として初めてシーズンを通して活躍し、新人王を獲得しました。",
        'person_data': {
            'person_name_ja': '大谷翔平',
            'birth_year': 1994,
            'category': 'スポーツ'
        }
    }

    score = evaluator.evaluate_episode(
        sample_episode['episode_text'],
        sample_episode['person_data']
    )

    print(f"サンプルエピソード評価:")
    print(f"  総合スコア: {score.total_score:.2f}")
    print(f"  グレード: {score.grade.value if hasattr(score.grade, 'value') else score.grade}")

    # dimension_scores の有無を確認
    if hasattr(score, 'dimension_scores'):
        print(f"  詳細スコア:")
        for dim, val in score.dimension_scores.items():
            print(f"    - {dim}: {val:.2f}")
    elif hasattr(score, '__dict__'):
        print(f"  詳細スコア:")
        for key, val in score.__dict__.items():
            if key not in ['total_score', 'grade'] and isinstance(val, (int, float)):
                print(f"    - {key}: {val:.2f}")

    # 5. 最終統計
    print("\n[5] 最終統計")
    cursor.execute("SELECT COUNT(*) FROM episodes")
    total_episodes = cursor.fetchone()[0]
    print(f"生成されたエピソード総数: {total_episodes}")

    cursor.execute("""
        SELECT grade, COUNT(*) as count
        FROM episodes
        GROUP BY grade
        ORDER BY grade
    """)

    print("グレード分布:")
    for grade, count in cursor.fetchall():
        if grade:
            print(f"  - {grade}グレード: {count}件")

    conn.close()

    print("\n" + "=" * 60)
    print("✅ テスト完了")
    print("=" * 60)

if __name__ == "__main__":
    test_system_integration()