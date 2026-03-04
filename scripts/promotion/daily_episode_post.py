#!/usr/bin/env python3
"""最期の砂時計 - エピソード自動投稿テキスト生成スクリプト

マスターCSVからランダムにエピソードを選択し、
X(Twitter)向けの投稿テキストを生成します。

Usage:
    python scripts/promotion/daily_episode_post.py
    python scripts/promotion/daily_episode_post.py --template question
    python scripts/promotion/daily_episode_post.py --min-score 800 --category 芸術
    python scripts/promotion/daily_episode_post.py --output src/reports/promotion/today_post.txt
"""

import argparse
import csv
import random
import sys
from datetime import datetime
from pathlib import Path

# プロジェクトルート（このスクリプトから2階層上）
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
MASTER_CSV = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"

HASHTAGS = "#最期の砂時計 #偉人 #名言"
APP_STORE_LINK = ""  # App Store URL を設定してください

MAX_TWEET_LENGTH = 280


def load_episodes(
    csv_path: Path,
    min_score: float = 500.0,
    category: str | None = None,
) -> list[dict]:
    """マスターCSVからエピソードを読み込み、フィルタリングする。"""
    episodes = []
    with open(csv_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # スコアフィルタ
            try:
                score = float(row.get("composite_score", 0) or 0)
            except (ValueError, TypeError):
                continue
            if score < min_score:
                continue

            # カテゴリフィルタ
            if category and row.get("category", "") != category:
                continue

            # エピソードテキストが空のものをスキップ
            if not row.get("episode_text", "").strip():
                continue

            episodes.append(row)

    return episodes


def format_person_name(episode: dict) -> str:
    """人物名をフォーマットする。架空キャラの場合は作品名を付記。"""
    name = episode.get("person_name", "不明")
    person_type = episode.get("person_type", "")
    work_title = episode.get("work_title", "")

    if "FICTIONAL" in person_type and work_title:
        return f"{name}『{work_title}』"
    return name


def truncate_text(text: str, max_length: int) -> str:
    """テキストを指定長で切り詰め、末尾に「…」を付ける。"""
    if len(text) <= max_length:
        return text
    return text[: max_length - 1] + "…"


def generate_episode_post(episode: dict) -> str:
    """テンプレート: エピソード紹介型"""
    name = format_person_name(episode)
    age = episode.get("age", "?")
    text = episode.get("episode_text", "")

    # エピソードテキストを短縮（ハッシュタグ分を考慮）
    header = f"📖 今日の偉人エピソード\n\n【{name}・{age}歳】\n"
    footer = f"\n\n53,000件以上のエピソードから、あなたの年齢に合ったものを。\n\n{HASHTAGS}"
    available = MAX_TWEET_LENGTH - len(header) - len(footer)
    body = truncate_text(text, max(available, 50))

    return f"{header}{body}{footer}"


def generate_question_post(episode: dict) -> str:
    """テンプレート: 問いかけ型"""
    name = format_person_name(episode)
    age = episode.get("age", "?")
    text = episode.get("episode_text", "")

    header = f"🤔 {name}が{age}歳のとき、何をしていたか知っていますか？\n\n"
    footer = f"\n\nあなたと同じ年齢の偉人が何をしていたか、知ってみませんか？\n\n{HASHTAGS}"
    available = MAX_TWEET_LENGTH - len(header) - len(footer)
    body = truncate_text(text, max(available, 50))

    return f"{header}{body}{footer}"


def generate_comparison_post(episodes: list[dict], target_age: int | None = None) -> str:
    """テンプレート: 比較型（同年齢の偉人3人）"""
    if target_age is None:
        # ランダムに年齢を選択
        ages = [int(e.get("age", 0)) for e in episodes if e.get("age", "").isdigit()]
        if not ages:
            return "エラー: 年齢データが見つかりません"
        target_age = random.choice(ages)

    # 同年齢のエピソードを抽出
    same_age = [e for e in episodes if str(e.get("age", "")) == str(target_age)]
    if len(same_age) < 3:
        # 足りない場合は前後1歳も含める
        same_age = [
            e for e in episodes
            if abs(int(e.get("age", 0) or 0) - target_age) <= 1
        ]

    if len(same_age) < 3:
        return "エラー: 同年齢のエピソードが不足しています"

    selected = random.sample(same_age, min(3, len(same_age)))

    lines = [f"⏳ {target_age}歳のとき、偉人たちは…\n"]
    for ep in selected:
        name = format_person_name(ep)
        text = truncate_text(ep.get("episode_text", ""), 40)
        lines.append(f"・{name}: {text}")

    lines.append(f"\n年齢は言い訳にならない。\n\n{HASHTAGS}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="最期の砂時計 - エピソード自動投稿テキスト生成"
    )
    parser.add_argument(
        "--template",
        choices=["episode", "question", "comparison"],
        default="episode",
        help="投稿テンプレート (default: episode)",
    )
    parser.add_argument(
        "--min-score",
        type=float,
        default=500.0,
        help="composite_scoreの下限 (default: 500)",
    )
    parser.add_argument(
        "--category",
        type=str,
        default=None,
        help="カテゴリでフィルタ（例: 芸術, 科学, スポーツ）",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="出力ファイルパス（指定しない場合は標準出力）",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="乱数シード（再現性のため）",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="出力のみ（デフォルト）",
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)
    else:
        random.seed()

    if not MASTER_CSV.exists():
        print(f"エラー: マスターCSVが見つかりません: {MASTER_CSV}", file=sys.stderr)
        sys.exit(1)

    episodes = load_episodes(MASTER_CSV, args.min_score, args.category)
    if not episodes:
        print("エラー: 条件に合うエピソードが見つかりません", file=sys.stderr)
        sys.exit(1)

    # テンプレートに応じて投稿テキスト生成
    if args.template == "comparison":
        post_text = generate_comparison_post(episodes)
    else:
        episode = random.choice(episodes)
        if args.template == "question":
            post_text = generate_question_post(episode)
        else:
            post_text = generate_episode_post(episode)

    # 文字数チェック
    char_count = len(post_text)
    if char_count > MAX_TWEET_LENGTH:
        print(
            f"⚠️  警告: {char_count}文字（{MAX_TWEET_LENGTH}文字制限超過）",
            file=sys.stderr,
        )

    # 出力
    output_header = f"--- 生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---"
    output_footer = f"--- 文字数: {char_count}/{MAX_TWEET_LENGTH} ---"

    result = f"{output_header}\n\n{post_text}\n\n{output_footer}\n"

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result, encoding="utf-8")
        print(f"✅ 保存しました: {output_path}")
    else:
        print(result)


if __name__ == "__main__":
    main()
