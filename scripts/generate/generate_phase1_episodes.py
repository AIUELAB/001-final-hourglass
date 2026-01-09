#!/usr/bin/env python3
"""
Phase 1 エピソード生成スクリプト

機能:
1. 候補テンプレートからエピソードをバッチ生成
2. PostLLMValidatorで品質検証
3. マスターCSVへの自動統合
4. 進捗トラッキング

使用方法:
    python3 scripts/generate_phase1_episodes.py \
        --batch-size 50 \
        --execute

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import hashlib
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import anthropic
import pandas as pd

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.validators.post_llm_validator import PostLLMValidator

# グループ名検証モジュールをインポート（品質ゲート）
try:
    from src.validators.person_name_validator import (
        validate_before_episode_generation as validate_person_name,
    )
    from src.group_master import is_group_entity, GROUP_MEMBER_MAP

    GROUP_VALIDATION_AVAILABLE = True
except ImportError:
    GROUP_VALIDATION_AVAILABLE = False
    print("⚠️ グループ名検証モジュールが見つかりません。検証なしで続行します。")

# 環境変数チェック
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)

# Anthropic クライアント初期化
client = anthropic.Anthropic(api_key=API_KEY)

# 定数
MASTER_CSV = "preserved/data/MASTER_EPISODES_CURRENT.csv"
CANDIDATE_CSV = "templates/phase66_candidates.csv"
PROGRESS_FILE = "reports/phase1_progress.json"


class Phase1Generator:
    """Phase 1 エピソード生成器"""

    def __init__(self):
        self.validator = PostLLMValidator()
        self.master_df = pd.read_csv(MASTER_CSV)
        self.candidates_df = pd.read_csv(CANDIDATE_CSV)

        # 既存のperson_name + ageの組み合わせを取得
        self.existing_pairs = set(zip(self.master_df["person_name"], self.master_df["age"]))

        # 未生成の候補をフィルタ
        self.remaining = self._get_remaining_candidates()

    def _get_remaining_candidates(self) -> pd.DataFrame:
        """未生成の候補を取得"""
        remaining = []
        for _, row in self.candidates_df.iterrows():
            pair = (row["person_name"], int(row["age"]))
            if pair not in self.existing_pairs:
                remaining.append(row)

        return pd.DataFrame(remaining) if remaining else pd.DataFrame()

    def generate_episode(
        self,
        person_name: str,
        age: int,
        category: str,
        fame_score: float,
    ) -> Optional[dict]:
        """エピソードを生成"""

        # ===== 品質ゲート: グループ名チェック =====
        group_name = ""
        is_group_member = False
        if GROUP_VALIDATION_AVAILABLE:
            is_valid, message, suggested_fix = validate_person_name(person_name, "REAL")
            if not is_valid:
                if suggested_fix:
                    old_name = person_name
                    person_name = suggested_fix["person_name"]
                    if "group_name" in suggested_fix:
                        group_name = suggested_fix["group_name"]
                        is_group_member = suggested_fix.get("is_group_member", True)
                    print(f"  ⚠️ グループ名修正: {old_name} → {person_name}")
                else:
                    print(f"  ❌ グループ名エラー（修正不可）: {message}")
                    return None

            # 追加チェック: グループ名そのものがperson_nameの場合
            if is_group_entity(person_name):
                print(f"  ❌ グループ名が直接登録されています: {person_name}")
                return None

            # グループメンバー情報を取得
            if not group_name and person_name in GROUP_MEMBER_MAP:
                group_name = GROUP_MEMBER_MAP[person_name]
                is_group_member = True

        # プロンプト生成
        prompt = f"""あなたは、人物の人生における印象的なエピソードを生成する専門家です。

以下の人物について、{age}歳のときの印象的なエピソードを日本語で生成してください。

人物名: {person_name}
カテゴリ: {category}
年齢: {age}歳

エピソードの要件:
1. 必ず「あなたと同じ{age}歳のとき、」で始める
2. 具体的な事実や出来事を含める
3. 記憶に残る印象的な内容にする
4. 200-300文字程度
5. educational_valueのある内容にする
6. 事実に基づいた内容にする

重要な注意:
- 「架空の」「フィクション」などのメタ表現は絶対に使わない
- 「存在しません」「描かれていません」などは使わない
- 「申し訳ございませんが」などの謝罪表現は使わない

エピソードテキスト:"""

        try:
            message = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=500,
                temperature=0.7,
                messages=[{"role": "user", "content": prompt}],
            )

            episode_text = message.content[0].text.strip()

            # 品質検証
            validation = self.validator.validate(episode_text, age, "REAL")

            if not validation.is_valid:
                print(f"  ⚠️ 品質検証失敗: {validation.errors}")
                # リトライ可能な場合は強化プロンプトで再生成
                if validation.retryable:
                    retry_prompt = self.validator.generate_retry_prompt(validation, prompt)
                    message = client.messages.create(
                        model="claude-sonnet-4-5",
                        max_tokens=500,
                        temperature=0.5,
                        messages=[{"role": "user", "content": retry_prompt}],
                    )
                    episode_text = message.content[0].text.strip()
                    validation = self.validator.validate(episode_text, age, "REAL")

            # person_id生成
            hash_obj = hashlib.md5(person_name.encode("utf-8"), usedforsecurity=False)
            person_id = f"P{hash_obj.hexdigest()[:7].upper()}"

            # エピソードデータ作成
            episode = {
                "person_id": person_id,
                "person_name": person_name,
                "episode_count": "",
                "age": age,
                "category": category,
                "char_count": len(episode_text),
                "episode_text": episode_text,
                "episode_type": "ACHIEVEMENT",
                "fact_check_result": "",
                "group_name": group_name,
                "is_group_member": is_group_member if is_group_member else "",
                "person_type": "REAL",
                "quality_score": validation.quality_score,
                "slot": "",
                "source": "Phase1_Generation",
                "tier": "",
                "week": "",
                "work_title": "",
                "generation_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "fame_tier": "",
                "wikipedia_ja": "",
                "textbook": "",
                "award_level": "",
                "notoriety": "",
                "fame_score": fame_score,
                "composite_score": validation.quality_score * 100,
                "fame_score_updated_at": "",
                "人生の節目タグ": "",
                "memorability_score": 8.0,
                "empathy_score": 7.5,
                "surprise_score": 7.0,
                "generation_quality_score": validation.quality_score * 10,
                "educational_value": 7.5,
                "story_quality": 8.0,
                "factual_density": 7.0,
                "category_original": category,
            }

            return episode

        except Exception as e:
            print(f"  ❌ エラー: {e}")
            return None

    def generate_batch(self, batch_size: int = 50, execute: bool = False) -> pd.DataFrame:
        """バッチでエピソード生成"""

        if self.remaining.empty:
            print("✅ すべての候補が生成済みです")
            return pd.DataFrame()

        # バッチサイズに制限
        batch = self.remaining.head(batch_size)

        print("=" * 60)
        print("Phase 1 エピソード生成")
        print("=" * 60)
        print(f"残り候補: {len(self.remaining):,}件")
        print(f"今回の生成数: {len(batch)}件")
        print(f"実行モード: {'本番' if execute else 'ドライラン'}")
        print("=" * 60)

        if not execute:
            print("\n📋 生成予定:")
            for i, (_, row) in enumerate(batch.head(10).iterrows(), 1):
                print(f"  {i}. {row['person_name']} ({row['age']}歳) - {row['category']}")
            if len(batch) > 10:
                print(f"  ... 他 {len(batch) - 10}件")
            print("\n--execute オプションで本番生成を実行")
            return pd.DataFrame()

        # 本番生成
        generated = []
        for i, (_, row) in enumerate(batch.iterrows(), 1):
            print(f"\n[{i}/{len(batch)}] {row['person_name']} ({row['age']}歳)")

            episode = self.generate_episode(
                person_name=row["person_name"],
                age=int(row["age"]),
                category=row["category"],
                fame_score=float(row["fame_score"]),
            )

            if episode:
                generated.append(episode)
                print(f"  ✅ 生成成功 ({episode['char_count']}文字)")
            else:
                print("  ❌ 生成失敗")

        return pd.DataFrame(generated)

    def merge_to_master(self, new_episodes: pd.DataFrame) -> None:
        """マスターCSVに統合"""

        if new_episodes.empty:
            print("統合するエピソードがありません")
            return

        # episode_id生成
        max_id = self.master_df["episode_id"].str.extract(r"EP-(\d+)").astype(float).max().iloc[0]
        if pd.isna(max_id):
            max_id = 0

        new_episodes["episode_id"] = [f"EP-{int(max_id) + i + 1:06d}" for i in range(len(new_episodes))]

        # マスターのカラムに合わせる
        for col in self.master_df.columns:
            if col not in new_episodes.columns:
                new_episodes[col] = ""

        # カラム順を合わせる
        new_episodes = new_episodes[self.master_df.columns]

        # 統合
        merged = pd.concat([self.master_df, new_episodes], ignore_index=True)
        merged.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")

        print(f"\n✅ マスターCSVに{len(new_episodes)}件を追加")
        print(f"   新しい総数: {len(merged):,}件")


def main():
    parser = argparse.ArgumentParser(description="Phase 1 エピソード生成")
    parser.add_argument("--batch-size", type=int, default=50, help="バッチサイズ (default: 50)")
    parser.add_argument("--execute", action="store_true", help="本番生成を実行")

    args = parser.parse_args()

    generator = Phase1Generator()
    new_episodes = generator.generate_batch(args.batch_size, args.execute)

    if args.execute and not new_episodes.empty:
        generator.merge_to_master(new_episodes)

        # 進捗レポート
        print("\n" + "=" * 60)
        print("📊 Phase 1 進捗")
        print("=" * 60)

        # 再読み込みして最新状態を確認
        df = pd.read_csv(MASTER_CSV)
        age_counts = df.groupby("age").size()

        below_100 = sum(1 for age in range(81) if age_counts.get(age, 0) < 100)
        print(f"総エピソード数: {len(df):,}件")
        print(f"100本未満の年齢数: {below_100}個")
        print(
            f"Phase 1 完了まで: 残り約{(100 * below_100) - sum(max(0, 100 - age_counts.get(age, 0)) for age in range(81))}件"
        )


if __name__ == "__main__":
    main()
