#!/usr/bin/env python3
"""
Phase 1再生成スクリプト（統合システム対応版）

既存システムを完全統合し、19人のエピソードを正しく生成します。
- entity_type検証（架空キャラクター除外）
- PDCAGuardian統合（90ルール）
- EpisodeGuardian統合（EntityTypeValidator）
"""

import csv
import json
import os
import sqlite3
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 統合システムのインポート
try:
    from episode_guardian import EntityTypeValidator, Severity
    from pdca_guardian import PDCAGuardian
except ImportError as e:
    print(f"❌ インポートエラー: {e}")
    sys.exit(1)

# OpenAI API
try:
    import openai
except ImportError:
    print("❌ OpenAIライブラリが見つかりません")
    print("   pip install openai を実行してください")
    sys.exit(1)


class IntegratedEpisodeGenerator:
    """統合システム対応エピソード生成クラス"""

    def __init__(self, db_path: str = "episode_database.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row

        # PDCAGuardian初期化
        self.pdca_guardian = PDCAGuardian(
            memory_file="phase1_regenerate_memory.json", use_unified_rules=True, relaxed_mode=False
        )

        # EntityTypeValidator初期化
        known_groups = set()
        self.entity_validator = EntityTypeValidator(known_groups)

        # OpenAI API設定
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("❌ OPENAI_API_KEYが設定されていません")
        openai.api_key = api_key

        print("✅ 統合エピソード生成エンジン初期化完了")
        print(f"   PDCAルール数: {len(self.pdca_guardian.unified_rule_loader.rules)}件")
        print("   EntityTypeValidator: 有効")

    def load_phase1_persons(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Phase 1対象人物を読み込み（統合検証付き）"""
        cursor = self.conn.cursor()

        # 実在人物のみを取得（4層防御の第1層）
        query = """
            SELECT
                person_id,
                person_name_ja,
                birth_year,
                category,
                entity_type,
                recognition_score
            FROM persons
            WHERE birth_year IS NOT NULL
              AND entity_type = 'real_person'
            ORDER BY recognition_score DESC
            LIMIT ?
        """

        cursor.execute(query, (limit,))
        rows = cursor.fetchall()

        persons = []
        for row in rows:
            person_data = {
                "person_id": row["person_id"],
                "person_name_ja": row["person_name_ja"],
                "birth_year": row["birth_year"],
                "category": row["category"],
                "entity_type": row["entity_type"],
                "recognition_score": row["recognition_score"],
            }

            # 第2層: entity_type二重チェック
            if person_data["entity_type"] != "real_person":
                print(f"⚠️ Skipping {person_data['person_name_ja']}: entity_type={person_data['entity_type']}")
                continue

            # 第3層: EntityTypeValidator事前検証
            validation_result = self.entity_validator.validate(
                {
                    "person_name": person_data["person_name_ja"],
                    "category": person_data["category"],
                    "episode_text": "",
                    "age": 30,  # ダミー年齢
                }
            )

            if not validation_result.is_valid and validation_result.severity == Severity.CRITICAL:
                print(f"❌ Pre-validation failed for {person_data['person_name_ja']}: {validation_result.message}")
                continue

            persons.append(person_data)

        return persons

    def generate_episode_prompt(self, person_info: Dict[str, Any], age: int) -> str:
        """エピソード生成プロンプト"""
        name = person_info["person_name_ja"]
        birth_year = person_info["birth_year"]
        category = person_info["category"]

        prompt = f"""
あなたは{name}の人生エピソードを生成する専門家です。

【対象人物】
- 名前: {name}
- 生年: {birth_year}年
- 年齢: {age}歳
- カテゴリ: {category}

【エピソード生成ルール】
1. **必須フォーマット**: 「あなたと同じ{age}歳のとき、{name}は」で必ず始める
2. **文字数（超重要）**:
   - プレフィックス（「あなたと同じ{age}歳のとき、{name}は」）を除いた本文が132文字以上必須
   - 全体で200-250文字を目標（プレフィックス込み）
3. 文末: 必ず動詞・形容詞で終わる（「〜した」「〜だった」等）
4. 事実性: Wikipediaや信頼できる情報源に基づく事実のみ（検証可能な固有名詞、数値、日付を含める）
5. 具体性: 数値、固有名詞、具体的な出来事を含める
6. 逆境・困難: 「〜という反対」「〜という批判」など障害を明示
7. 感情的インパクト: 印象的で記憶に残る描写
8. 歴史的意義: 「〜初」「〜以来」「〜を変えた」など文脈を追加
9. 教育的価値: 知識として価値のある情報を含める

【禁止事項】
❌ 推測や憶測を含めない
❌ 「〜と言われている」などの曖昧表現
❌ 一般論や抽象的な記述
❌ 敬語や敬称（さん、様等）
❌ フォーマット違反（必ず「あなたと同じ{age}歳のとき、{name}は」で始める）

【参考例】
良い例: 「あなたと同じ{age}歳のとき、{name}は製作側から『無名の新人に大作主演は無理』という強い反対があった。彼女は5年間演技の修行を積み、2015年のオーディションで100人のライバルを退け、沖縄出身初の大作主演女優として映画『海の向こう』で主役を獲得した。この映画は興行収入50億円を超え、彼女の演技は日本アカデミー賞新人賞を受賞するという快挙を成し遂げた。」

【出力形式】
あなたと同じ{age}歳のとき、{name}は（プレフィックス除いて132文字以上の具体的エピソード）

**重要**:
- プレフィックス除外後の本文が132文字以上必須
- 全体で200-250文字が理想的
- 必ず上記フォーマットで開始
"""
        return prompt

    def call_openai_api(self, prompt: str) -> Optional[str]:
        """OpenAI APIを呼び出し"""
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

            text = response.choices[0].message.content.strip()
            # 改行や余計な記号を除去
            text = text.replace("\n", "").replace("\r", "")
            return text

        except Exception as e:
            print(f"❌ API呼び出しエラー: {e}")
            return None

    def parse_episode(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """生成されたテキストからエピソードをパース"""
        import re

        # 年齢抽出
        age_match = re.search(r"(\d{1,3})歳", raw_text)
        if not age_match:
            print(f"⚠️ 年齢が見つかりません: {raw_text[:50]}...")
            return None

        age = int(age_match.group(1))

        # エピソード本文抽出
        episode_text = raw_text.strip()

        return {"age": age, "episode_text": episode_text}

    def validate_with_pdca(self, episode: Dict[str, Any]) -> bool:
        """PDCAGuardianで検証"""
        violations = self.pdca_guardian.check_episode_quality(
            episode_text=episode["episode_text"],
            age=episode["age"],
            person_name_display=episode["person_name"],
            person_data=episode,  # 全データを渡す
        )
        # 違反がなければ合格
        return len(violations) == 0

    def save_episode(self, person_id: str, age: int, episode_text: str) -> str:
        """エピソードをデータベースに保存"""
        episode_id = f"EP_{person_id}_{age:03d}"
        cursor = self.conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO episodes (
                episode_id, person_id, age, episode_text,
                grade, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
            (
                episode_id,
                person_id,
                age,
                episode_text,
                "phase1_regenerated",
                datetime.now().isoformat(),
                datetime.now().isoformat(),
            ),
        )

        self.conn.commit()
        return episode_id

    def generate_batch(self, count: int = 19) -> List[Dict[str, Any]]:
        """バッチ生成"""
        print(f"\n{'=' * 70}")
        print("  Phase 1再生成（統合システム版）")
        print(f"{'=' * 70}")

        persons = self.load_phase1_persons(limit=count)
        total = len(persons)

        print(f"\n対象人物数: {total}人")
        print(f"{'=' * 70}\n")

        results = []
        success_count = 0
        failed_count = 0

        for idx, person in enumerate(persons, 1):
            person_name = person["person_name_ja"]
            person_id = person["person_id"]

            print(f"\n{'─' * 70}")
            print(f"[{idx}/{total}] {person_name} ({person_id})")
            print(f"{'─' * 70}")

            # 年齢を選択（30歳をデフォルト）
            age = 30

            # プロンプト生成
            prompt = self.generate_episode_prompt(person, age)

            # API呼び出し
            print("🔄 エピソード生成中...")
            raw_text = self.call_openai_api(prompt)

            if not raw_text:
                print("❌ 生成失敗")
                failed_count += 1
                results.append(
                    {"person_id": person_id, "person_name": person_name, "success": False, "error": "API呼び出し失敗"}
                )
                continue

            # パース
            parsed = self.parse_episode(raw_text)
            if not parsed:
                print("❌ パース失敗")
                failed_count += 1
                results.append(
                    {"person_id": person_id, "person_name": person_name, "success": False, "error": "パース失敗"}
                )
                continue

            episode_text = parsed["episode_text"]
            age = parsed["age"]

            print(f"\n📝 生成されたエピソード（{len(episode_text)}文字）:")
            print(f"   {episode_text[:100]}...")

            # PDCA検証
            print("\n🔍 PDCAGuardian検証中...")
            episode_for_validation = {
                "person_id": person_id,
                "person_name": person_name,
                "age": age,
                "episode_text": episode_text,
                "category": person["category"],
            }

            is_valid = self.validate_with_pdca(episode_for_validation)

            if is_valid:
                print("✅ 検証合格")
                # 保存
                episode_id = self.save_episode(person_id, age, episode_text)
                success_count += 1
                results.append(
                    {
                        "person_id": person_id,
                        "person_name": person_name,
                        "age": age,
                        "episode_text": episode_text,
                        "episode_id": episode_id,
                        "success": True,
                        "character_count": len(episode_text),
                    }
                )
                print(f"💾 保存完了: {episode_id}")
            else:
                print("❌ 検証不合格")
                failed_count += 1
                results.append(
                    {"person_id": person_id, "person_name": person_name, "success": False, "error": "PDCA検証不合格"}
                )

            # API レート制限対策
            if idx < total:
                time.sleep(2)

        # サマリー
        print(f"\n{'=' * 70}")
        print("  生成完了サマリー")
        print(f"{'=' * 70}")
        print(f"\n対象: {total}人")
        print(f"✅ 成功: {success_count}人 ({success_count/total*100:.1f}%)")
        print(f"❌ 失敗: {failed_count}人 ({failed_count/total*100:.1f}%)")
        print(f"\n{'=' * 70}")

        return results

    def export_to_csv(self, results: List[Dict[str, Any]], output_path: str):
        """CSVエクスポート"""
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            fieldnames = ["person_id", "person_name", "age", "episode_text", "episode_id", "character_count", "success"]
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()

            for result in results:
                if result.get("success"):
                    writer.writerow(result)

        print(f"\n💾 CSV出力: {output_path}")

    def close(self):
        """クリーンアップ"""
        self.conn.close()


def main():
    """メイン処理"""
    print("=" * 70)
    print("  Phase 1: 統合システム再生成")
    print("=" * 70)

    generator = IntegratedEpisodeGenerator()

    try:
        results = generator.generate_batch(count=19)

        # CSV出力
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_csv = f"phase1_regenerated_{timestamp}.csv"
        generator.export_to_csv(results, output_csv)

        return 0

    finally:
        generator.close()


if __name__ == "__main__":
    sys.exit(main())
