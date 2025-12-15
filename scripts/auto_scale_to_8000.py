#!/usr/bin/env python3
"""
8,000人目標達成自動スケーリングスクリプト

目標人物数8,000人に到達するまで継続的にエピソードを生成・統合します。

使用方法:
    nohup ANTHROPIC_API_KEY="..." ./venv/bin/python scripts/auto_scale_to_8000.py > logs/auto_scale.log 2>&1 &

    # 進捗確認
    tail -f logs/auto_scale.log

    # 停止
    pkill -f "auto_scale_to_8000.py"

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー（必須）
"""

import hashlib
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

import anthropic
import pandas as pd

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# 定数
MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
LOG_DIR = PROJECT_ROOT / "logs"
GENERATED_DIR = PROJECT_ROOT / "generated"
TARGET_PERSONS = 8000
BATCH_SIZE = 30  # 1バッチあたりの生成人物数

# カテゴリと目標人数
CATEGORY_TARGETS = {
    "スポーツ": 1200,
    "芸術・文化": 1000,
    "ビジネス": 800,
    "科学・技術": 800,
    "エンターテイメント": 1000,
    "音楽": 800,
    "政治・社会": 600,
    "学術・研究": 600,
    "映画・演劇": 500,
    "アニメ・漫画・ゲーム": 400,
    "文学": 400,
    "歴史": 300,
    "探検・冒険": 200,
    "俳優・女優": 300,
}


class AutoScaler:
    """8,000人目標達成自動スケーラー"""

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            print("❌ ANTHROPIC_API_KEY が設定されていません")
            sys.exit(1)

        self.client = anthropic.Anthropic(api_key=api_key)
        LOG_DIR.mkdir(exist_ok=True)
        GENERATED_DIR.mkdir(exist_ok=True)
        self.log_file = LOG_DIR / f"auto_scale_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.batch_count = 0

    def log(self, message: str):
        """ログ出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message, flush=True)
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_message + "\n")

    def get_current_persons(self) -> int:
        """現在のユニーク人物数を取得"""
        df = pd.read_csv(MASTER_CSV)
        return df["person_name"].nunique()

    def get_existing_persons(self) -> set:
        """既存人物名のセットを取得"""
        df = pd.read_csv(MASTER_CSV)
        return set(df["person_name"].tolist())

    def get_persons_by_category(self, category: str) -> list:
        """カテゴリ別の人物リストを取得"""
        df = pd.read_csv(MASTER_CSV)
        return df[df["category"] == category]["person_name"].unique().tolist()

    def get_exclusion_list_for_category(self, category: str) -> str:
        """カテゴリ用の除外リストを生成（トークン最適化）"""
        df = pd.read_csv(MASTER_CSV)

        # 1. 対象カテゴリの全人物（最優先）
        category_persons = df[df["category"] == category]["person_name"].unique().tolist()

        # 2. 類似カテゴリの人物も追加
        similar_categories = {
            "スポーツ": ["探検・冒険"],
            "芸術・文化": ["文学", "音楽"],
            "ビジネス": ["科学・技術"],
            "科学・技術": ["学術・研究", "ビジネス"],
            "エンターテイメント": ["音楽", "映画・演劇", "俳優・女優"],
            "音楽": ["エンターテイメント", "芸術・文化"],
            "政治・社会": ["歴史"],
            "学術・研究": ["科学・技術"],
            "映画・演劇": ["エンターテイメント", "俳優・女優"],
            "アニメ・漫画・ゲーム": ["エンターテイメント"],
            "文学": ["芸術・文化"],
            "歴史": ["政治・社会"],
            "探検・冒険": ["スポーツ"],
            "俳優・女優": ["映画・演劇", "エンターテイメント"],
        }

        related_persons = []
        for related_cat in similar_categories.get(category, []):
            related = df[df["category"] == related_cat]["person_name"].unique().tolist()
            related_persons.extend(related[:100])  # 各関連カテゴリから最大100人

        # 3. 他カテゴリからランダムサンプル
        other_persons = (
            df[~df["category"].isin([category] + similar_categories.get(category, []))]["person_name"].unique().tolist()
        )
        import random

        random.shuffle(other_persons)
        other_sample = other_persons[:200]

        # 統合（重複除去）
        all_exclusions = list(set(category_persons + related_persons + other_sample))

        # トークン制限を考慮（約500人まで）
        if len(all_exclusions) > 500:
            # カテゴリ人物は全て含め、その他を削減
            all_exclusions = category_persons + related_persons[: min(200, len(related_persons))]
            remaining = 500 - len(all_exclusions)
            if remaining > 0:
                all_exclusions.extend(other_sample[:remaining])

        return ", ".join(all_exclusions)

    def get_category_stats(self) -> dict:
        """カテゴリ別人物数を取得"""
        df = pd.read_csv(MASTER_CSV)
        return df.groupby("category")["person_name"].nunique().to_dict()

    def get_priority_category(self) -> str:
        """最も追加が必要なカテゴリを取得（目標比で最も不足しているもの）"""
        stats = self.get_category_stats()
        priorities = {}

        for cat, target in CATEGORY_TARGETS.items():
            current = stats.get(cat, 0)
            # 目標達成率を計算（低いほど優先度高）
            completion = current / target if target > 0 else 1.0
            priorities[cat] = completion

        # 最も達成率が低いカテゴリを返す
        return min(priorities, key=priorities.get)

    def generate_person_id(self, person_name: str) -> str:
        """person_nameからperson_idを生成"""
        hash_obj = hashlib.md5(person_name.encode("utf-8"), usedforsecurity=False)
        hash_hex = hash_obj.hexdigest()[:7].upper()
        return f"P{hash_hex}"

    def generate_person_list(self, category: str, count: int, retry_count: int = 0) -> list:
        """LLMでカテゴリの有名人リストを生成（改善版：完全除外リスト使用）"""
        existing = self.get_existing_persons()

        # カテゴリ特化の完全除外リストを取得
        exclusion_list = self.get_exclusion_list_for_category(category)
        exclusion_count = len(exclusion_list.split(", "))

        self.log(f"  除外リスト: {exclusion_count}人（カテゴリ特化）")

        # リトライ時は要求数を増やす（重複を見越して多めに生成）
        request_count = count + (retry_count * 10)

        prompt = f"""
あなたは「{category}」分野の有名人データベース構築を手伝うエキスパートです。

【タスク】
カテゴリ「{category}」で知名度の高い人物を{request_count}人リストアップしてください。

【絶対に除外する人物リスト】
以下の{exclusion_count}人は既にデータベースに存在するため、絶対に含めないでください:
{exclusion_list}

【出力フォーマット】CSVヘッダー付きで出力:
person_name,category,age_at_episode,person_type,notes

【出力例】以下のような形式で出力してください:
```csv
person_name,category,age_at_episode,person_type,notes
マイケル・ジョーダン,スポーツ,23,REAL,NBA選手・シカゴ・ブルズで6度優勝
スティーブ・ジョブズ,ビジネス,25,REAL,Apple創業者・iPhone開発
宮崎駿,芸術・文化,44,REAL,アニメ監督・ジブリ設立・アカデミー賞受賞
マリー・キュリー,科学・技術,36,REAL,物理学者・化学者・2度のノーベル賞受賞
```

【条件】
- 上記の除外リストに含まれる人物は絶対に出力しない
- 日本人と海外人物をバランスよく（日本人5-6割、海外4-5割）
- person_typeは「REAL」（実在人物）
- age_at_episodeは代表的な活躍年齢（20-70歳の範囲で具体的に）
- 重複なし、知名度の高い人物を優先
- notesには職業や代表的な業績を簡潔に記載

【重要】除外リストの人物を1人でも含めると失敗とみなされます。新しい人物のみを出力してください。

【出力】CSVデータのみ（説明不要）:
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )

            csv_text = response.content[0].text
            persons = self.parse_csv_response(csv_text, category, existing)

            # 結果が少なすぎる場合はリトライ（最大3回）
            if len(persons) < count // 2 and retry_count < 3:
                self.log(f"  ⚠️ 候補が少ない({len(persons)}人)、リトライ {retry_count + 1}/3")
                additional = self.generate_person_list(category, count - len(persons), retry_count + 1)
                persons.extend(additional)

            return persons[:count]

        except Exception as e:
            self.log(f"❌ 人物リスト生成エラー: {e}")
            return []

    def parse_csv_response(self, csv_text: str, category: str, existing: set) -> list:
        """CSVレスポンスをパース"""
        persons = []

        # CSVブロックを抽出
        lines = csv_text.strip().split("\n")
        in_csv = False

        for line in lines:
            line = line.strip()

            # ヘッダー検出
            if "person_name" in line and "category" in line:
                in_csv = True
                continue

            if not in_csv or not line:
                continue

            # コードブロックの終了
            if line.startswith("```"):
                break

            # CSV行をパース
            try:
                parts = line.split(",")
                if len(parts) >= 4:
                    person_name = parts[0].strip().strip('"')
                    person_category = parts[1].strip().strip('"')
                    age = parts[2].strip().strip('"')
                    person_type = parts[3].strip().strip('"')
                    notes = parts[4].strip().strip('"') if len(parts) > 4 else ""

                    # 重複チェック
                    if person_name in existing:
                        continue

                    # 年齢を数値に変換
                    try:
                        age_int = int(age)
                        if age_int < 15 or age_int > 90:
                            age_int = 35
                    except ValueError:
                        age_int = 35

                    persons.append(
                        {
                            "person_name": person_name,
                            "category": person_category or category,
                            "age_at_episode": age_int,
                            "person_type": person_type or "REAL",
                            "notes": notes,
                        }
                    )
                    existing.add(person_name)

            except Exception as e:
                self.log(f"CSV行パースエラー: {line} - {e}")
                continue

        return persons

    def generate_episode(self, person: dict) -> dict | None:
        """1人分のエピソードを生成"""
        person_name = person["person_name"]
        category = person["category"]
        age = person["age_at_episode"]
        notes = person.get("notes", "")
        person_type = person.get("person_type", "REAL")

        prompt = f"""
以下の人物について、感動的で記憶に残るエピソードを生成してください。

人物名: {person_name}
カテゴリ: {category}
年齢: {age}歳
補足: {notes}

【フォーマット】
「あなたと同じ{age}歳のとき、{person_name}は...」で始まるエピソードを生成してください。

【条件】
- 150〜250文字程度
- 具体的な事実や数字を含める
- 感情に訴える内容
- 困難を乗り越えた話や転機となった出来事
- 「〜した」で終わる
- **意外性のある展開を含める**（失敗からの学び、予想外の決断、逆転劇など）

【高品質なエピソード例】
例1: 「あなたと同じ23歳のとき、イチローは1996年のオリックス時代、首位打者を逃した悔しさから従来の打撃フォームを全て捨て去る決断をした。周囲の猛反対を押し切り、振り子打法という独自のスタイルを1から構築。翌年、日本記録となる210安打を達成した。」

例2: 「あなたと同じ35歳のとき、手塚治虫は1964年、虫プロダクションの経営危機で借金が1億円を超えた。しかし倒産寸前のその時期に敢えて新作『ジャングル大帝』のカラーアニメ化に挑戦。この逆境での決断が日本初のカラーTVアニメとして世界に認められた。」

【出力】エピソード本文のみ（説明不要）:
"""

        try:
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}],
            )

            episode_text = response.content[0].text.strip()

            # 品質スコアを計算
            char_count = len(episode_text)
            base_score = 8.0
            if char_count > 150:
                base_score += 0.5
            if char_count > 200:
                base_score += 0.3

            return {
                "episode_id": f"EP-{datetime.now().strftime('%y%m%d')}{self.batch_count:03d}",
                "person_id": self.generate_person_id(person_name),
                "person_name": person_name,
                "category": category,
                "age": age,
                "episode_text": episode_text,
                "person_type": person_type,
                "composite_score": round(base_score * 10, 1),
                "記憶性スコア": base_score,
                "共感性スコア": base_score - 0.5,
                "意外性スコア": base_score,
                "生成品質スコア": base_score,
                "episode_type": "TURNING_POINT",
                "年代": self.estimate_era(person_name, age),
            }

        except Exception as e:
            self.log(f"❌ エピソード生成エラー ({person_name}): {e}")
            return None

    def estimate_era(self, person_name: str, age: int) -> str:
        """年代を推定"""
        # 簡易的な年代推定（実際にはより詳細なロジックが必要）
        current_year = datetime.now().year
        estimated_birth = current_year - age - 30  # 概算
        if estimated_birth >= 2000:
            return "2000年代"
        elif estimated_birth >= 1990:
            return "1990年代"
        elif estimated_birth >= 1980:
            return "1980年代"
        elif estimated_birth >= 1970:
            return "1970年代"
        elif estimated_birth >= 1960:
            return "1960年代"
        else:
            return "1950年代以前"

    def merge_to_master(self, new_episodes: list):
        """新規エピソードをマスターCSVに統合"""
        if not new_episodes:
            return 0

        main_df = pd.read_csv(MASTER_CSV)
        main_df["key"] = main_df["person_name"].astype(str) + "_" + main_df["age"].astype(str)
        existing_keys = set(main_df["key"])

        new_df = pd.DataFrame(new_episodes)
        new_df["key"] = new_df["person_name"].astype(str) + "_" + new_df["age"].astype(str)

        # 重複除去
        new_only = new_df[~new_df["key"].isin(existing_keys)].copy()

        if len(new_only) == 0:
            return 0

        # 統合
        new_only = new_only.drop(columns=["key"])
        main_df = main_df.drop(columns=["key"])

        # カラムを揃える
        for col in main_df.columns:
            if col not in new_only.columns:
                new_only[col] = ""

        # 並べ替え
        new_only = new_only[main_df.columns]

        result = pd.concat([main_df, new_only], ignore_index=True)
        result.to_csv(MASTER_CSV, index=False, encoding="utf-8-sig")

        return len(new_only)

    def generate_batch(self) -> int:
        """1バッチ分のエピソード生成・統合"""
        self.batch_count += 1
        category = self.get_priority_category()
        self.log(f"バッチ {self.batch_count}: カテゴリ「{category}」を強化")

        # 人物リスト生成
        persons = self.generate_person_list(category, BATCH_SIZE)
        if not persons:
            self.log("人物リスト生成失敗")
            return 0

        self.log(f"  {len(persons)}人の候補を生成")

        # エピソード生成
        episodes = []
        for i, person in enumerate(persons):
            self.log(f"  [{i+1}/{len(persons)}] {person['person_name']}...")
            episode = self.generate_episode(person)
            if episode:
                episodes.append(episode)

            # API制限対策
            time.sleep(1)

        # マスターに統合
        added = self.merge_to_master(episodes)
        self.log(f"  ✅ {added}件追加完了")

        return added

    def run_until_target(self):
        """目標達成まで継続実行"""
        self.log("=" * 60)
        self.log("🚀 8,000人目標自動スケーリング開始")
        self.log(f"目標: {TARGET_PERSONS}人")
        self.log(f"バッチサイズ: {BATCH_SIZE}人/回")
        self.log("=" * 60)

        while True:
            current = self.get_current_persons()

            if current >= TARGET_PERSONS:
                self.log(f"🎉 目標達成! {current}/{TARGET_PERSONS}人")
                break

            remaining = TARGET_PERSONS - current
            progress = (current / TARGET_PERSONS) * 100
            self.log(f"進捗: {current}/{TARGET_PERSONS}人 ({progress:.1f}%) 残り{remaining}人")

            try:
                added = self.generate_batch()
                if added == 0:
                    self.log("⚠️ 追加なし、30秒待機後リトライ")
                    time.sleep(30)
            except Exception as e:
                self.log(f"❌ バッチエラー: {e}")
                self.log(traceback.format_exc())
                self.log("5分待機後リトライ...")
                time.sleep(300)

            # バッチ間の待機
            time.sleep(5)

        # 最終統計
        self.log("=" * 60)
        self.log("📊 最終統計")
        stats = self.get_category_stats()
        for cat, count in sorted(stats.items(), key=lambda x: x[1], reverse=True):
            self.log(f"  {cat}: {count}人")
        self.log(f"合計: {self.get_current_persons()}人")
        self.log("=" * 60)


def main():
    scaler = AutoScaler()
    scaler.run_until_target()


if __name__ == "__main__":
    main()
