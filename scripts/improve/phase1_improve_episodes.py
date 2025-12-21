#!/usr/bin/env python3
"""
Phase 1エピソード品質改善スクリプト

生成済みの20件のエピソードを既存の高品質CSVフォーマットに合わせて
吟味・修正し、詳細化します。

改善ポイント:
1. 具体的な数値・データの追加
2. 逆境・困難の明示
3. 感情的インパクトの強化
4. 歴史的意義の明確化
5. 150-250文字への最適化
"""

import os
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# OpenAI API
import openai

# APIキー設定
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ OPENAI_API_KEYが設定されていません")
openai.api_key = api_key


class EpisodeImprover:
    """エピソード品質改善クラス"""

    def __init__(self, db_path: str = "episode_database.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

    def get_all_phase1_episodes(self) -> List[Dict[str, Any]]:
        """Phase 1の全エピソードを取得"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT
                e.episode_id,
                e.person_id,
                e.age,
                e.episode_text,
                p.person_name_ja,
                p.person_name_en,
                p.birth_year,
                p.category,
                p.entity_type
            FROM episodes e
            JOIN persons p ON e.person_id = p.person_id
            WHERE e.grade = 'phase1_pilot'
            ORDER BY e.person_id
        """)

        episodes = []
        for row in cursor.fetchall():
            episodes.append(
                {
                    "episode_id": row["episode_id"],
                    "person_id": row["person_id"],
                    "person_name_ja": row["person_name_ja"],
                    "person_name_en": row["person_name_en"],
                    "age": row["age"],
                    "episode_text": row["episode_text"],
                    "birth_year": row["birth_year"],
                    "category": row["category"],
                    "entity_type": row["entity_type"],
                }
            )

        return episodes

    def create_improvement_prompt(self, episode: Dict[str, Any]) -> str:
        """改善プロンプト生成"""
        name = episode["person_name_ja"]
        age = episode["age"]
        current_text = episode["episode_text"]
        category = episode["category"]

        prompt = f"""
あなたは優秀なエピソードライターです。以下のエピソードを、より感動的で具体的な内容に改善してください。

【対象人物】
名前: {name}
年齢: {age}歳
カテゴリ: {category}

【現在のエピソード】
{current_text}

【改善指示】
1. **逆境・困難の明示**: 「〜という反対があった」「〜という批判」など具体的な障害を追加
2. **具体的数値**: 興行収入、視聴率、売上、参加人数、記録などの数値を追加
3. **感情的インパクト**: 「涙を流した」「震える声で」など感情表現を追加
4. **歴史的意義**: 「〜初」「〜以来」「〜を変えた」など歴史的文脈を追加
5. **文字数**: 180-230文字が理想的

【禁止事項】
❌ 推測や憶測を含めない（事実ベースのみ）
❌ 「〜と言われている」などの曖昧表現
❌ 敬語や敬称（さん、様等）
❌ 年齢言及を忘れない（「〇〇歳の時」必須）

【参考例】
良い例: 「この年、製作側から『無名の新人に大作主演は無理』という強い反対があった。オーディションで何度も落選し、沖縄出身というハンデを乗り越えて勝ち取った役だった。」

悪い例: 「この作品は評価された。」

【出力形式】
改善されたエピソード文のみを出力してください（説明不要）。
必ず「{age}歳の時」を含め、180-230文字で記述してください。
"""
        return prompt

    def improve_episode(self, episode: Dict[str, Any]) -> str:
        """エピソードを改善"""
        prompt = self.create_improvement_prompt(episode)

        try:
            response = openai.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "あなたは歴史的事実に基づいた感動的なエピソードを書く専門家です。"},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.8,
                max_tokens=600,
            )

            improved_text = response.choices[0].message.content.strip()

            # 改行や余計な記号を除去
            improved_text = improved_text.replace("\n", "").replace("\r", "")

            return improved_text

        except Exception as e:
            print(f"❌ 改善API呼び出し失敗: {e}")
            return episode["episode_text"]

    def update_episode(self, episode_id: str, new_text: str):
        """エピソードをデータベースに更新"""
        cursor = self.conn.cursor()
        cursor.execute(
            """
            UPDATE episodes
            SET episode_text = ?,
                updated_at = ?
            WHERE episode_id = ?
        """,
            (new_text, datetime.now().isoformat(), episode_id),
        )
        self.conn.commit()

    def improve_all_episodes(self):
        """全エピソードを改善"""
        episodes = self.get_all_phase1_episodes()

        if not episodes:
            print("⚠️ Phase 1のエピソードが見つかりません")
            return

        total = len(episodes)
        print(f"\n{'=' * 70}")
        print("  Phase 1エピソード品質改善")
        print(f"{'=' * 70}")
        print(f"\n対象エピソード数: {total}件\n")

        improved_count = 0

        for idx, episode in enumerate(episodes, 1):
            print(f"\n{'─' * 70}")
            print(f"[{idx}/{total}] {episode['person_name_ja']}（{episode['age']}歳）")
            print(f"{'─' * 70}")

            # 現在のエピソード表示
            print(f"\n📄 現在のエピソード（{len(episode['episode_text'])}文字）:")
            print(f"   {episode['episode_text'][:100]}...")

            # 改善
            print("\n🔄 改善中...")
            improved_text = self.improve_episode(episode)

            # 改善後表示
            print(f"\n✨ 改善後のエピソード（{len(improved_text)}文字）:")
            print(f"   {improved_text}")

            # 確認
            if improved_text != episode["episode_text"]:
                # 更新
                self.update_episode(episode["episode_id"], improved_text)
                improved_count += 1
                print("\n✅ エピソードを更新しました")
            else:
                print("\n⚠️ 変更なし")

            # API レート制限対策
            if idx < total:
                import time

                time.sleep(2)

        print(f"\n{'=' * 70}")
        print("  改善完了")
        print(f"{'=' * 70}")
        print(f"\n改善件数: {improved_count}/{total}件")
        print(f"成功率: {improved_count/total*100:.1f}%")
        print(f"\n{'=' * 70}")

    def close(self):
        """クリーンアップ"""
        self.conn.close()


def main():
    """メイン処理"""
    print("=" * 70)
    print("  Phase 1: エピソード品質改善")
    print("=" * 70)

    improver = EpisodeImprover()

    try:
        improver.improve_all_episodes()
        return 0
    finally:
        improver.close()


if __name__ == "__main__":
    sys.exit(main())
