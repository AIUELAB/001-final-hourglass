#!/usr/bin/env python3
"""
品質ゲート付きエピソード生成スクリプト

LLM自己評価 + 品質ゲート + 改稿ループを実装した新世代生成システム

使用方法:
    # テスト実行（10件）
    python scripts/generate_with_quality_gate.py --count 10 --dry-run

    # 本番実行
    python scripts/generate_with_quality_gate.py --count 50 --execute

    # 特定年齢で生成
    python scripts/generate_with_quality_gate.py --count 20 --ages 25,30,35 --execute

環境変数:
    ANTHROPIC_API_KEY: Anthropic APIキー
"""

import argparse
import csv
import hashlib
import json
import os
import random
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import anthropic

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 埋め草検出モジュール
from scripts.validation.filler_detector import is_filler, FillerAnalysis, is_refusal_message

# 現在年（未来エピソード検出用）
CURRENT_YEAR = 2026

# 既知の人物データ（生年・没年）- 未来/死亡後エピソード検出用
KNOWN_PEOPLE_TEMPORAL = {
    # スポーツ
    "大谷翔平": {"birth": 1994},
    "羽生結弦": {"birth": 1994},
    "藤井聡太": {"birth": 2002},
    "イチロー": {"birth": 1973},
    "浅田真央": {"birth": 1990},
    "錦織圭": {"birth": 1989},
    # 芸能人・死亡済み
    "志村けん": {"birth": 1950, "death": 2020},
    "坂本龍一": {"birth": 1952, "death": 2023},
    "鳥山明": {"birth": 1955, "death": 2024},
    # 音楽・芸術
    "久石譲": {"birth": 1950},
    "エルトン・ジョン": {"birth": 1947},
    # 文化人
    "村上春樹": {"birth": 1949},
    "養老孟司": {"birth": 1937},
    # 歴史上の人物
    "湯川秀樹": {"birth": 1907, "death": 1981},
    "川端康成": {"birth": 1899, "death": 1972},
}


def validate_temporal_accuracy(person_name: str, age: int, person_type: str) -> tuple[bool, str]:
    """時間的妥当性を検証（未来/死亡後エピソードを検出）"""
    if person_type != "REAL":
        return True, ""

    if person_name not in KNOWN_PEOPLE_TEMPORAL:
        return True, ""  # 未知の人物は許可

    data = KNOWN_PEOPLE_TEMPORAL[person_name]
    birth = data["birth"]
    death = data.get("death")

    episode_year = birth + age

    # 死亡後のエピソード
    if death and episode_year > death:
        return False, f"死亡({death}年)後のエピソード({episode_year}年)は不可"

    # 未来のエピソード（現在年+2年以上先）
    if episode_year > CURRENT_YEAR + 2:
        current_age = CURRENT_YEAR - birth
        return False, f"未来({episode_year}年)のエピソード不可。現在{current_age}歳"

    return True, ""


# CSVパス
CSV_PATH = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "reports"

# 環境変数チェック
API_KEY = os.getenv("ANTHROPIC_API_KEY")
if not API_KEY:
    print("❌ ANTHROPIC_API_KEY環境変数が設定されていません")
    sys.exit(1)

# Anthropic クライアント
client = anthropic.Anthropic(api_key=API_KEY)

# =============================================================================
# 品質ゲート設定
# =============================================================================

QUALITY_GATES = {
    "minimum_composite": 380,  # これ以下は即棄却（緩和: 400→380）
    "target_composite": 550,  # 目標ライン（これ以上で即採用）
    "retry_threshold": 470,  # リトライ後この値以上で採用（緩和: 480→470）
    "max_retries": 2,  # 最大リトライ回数（強化: 1→2）
    # 軸別の最低ライン（これ以下の軸は改善対象）
    "axis_minimums": {
        "共感性スコア": 4.5,
        "意外性スコア": 5.0,  # 強化: 4.5→5.0（最弱軸なので優先改善）
        "教育的価値": 4.5,
        "事実密度": 5.0,  # 強化: 4.0→5.0（最弱軸なので優先改善）
    },
}

# =============================================================================
# 重要転機キーワード（5件制限を緩和）
# =============================================================================
TURNING_POINT_KEYWORDS = [
    # 政治的転機
    "大統領",
    "首相",
    "総理",
    "主席",
    "書記長",
    "総統",
    "国王",
    "女王",
    "皇帝",
    "当選",
    "就任",
    "選挙",
    "政権",
    # 科学的マイルストーン
    "ノーベル賞",
    "ノーベル",
    "発見",
    "発明",
    "理論",
    "証明",
    "相対性理論",
    "量子力学",
    "DNA",
    # スポーツ達成
    "金メダル",
    "オリンピック",
    "世界記録",
    "世界選手権",
    "優勝",
    "制覇",
    "MVP",
    "チャンピオン",
    # 芸術的達成
    "アカデミー賞",
    "グラミー賞",
    "カンヌ",
    "パルム・ドール",
    "ベルリン",
    "芥川賞",
    "直木賞",
    "ノーベル文学賞",
    # ビジネス転機
    "創業",
    "設立",
    "上場",
    "IPO",
]

# 転機優先: この件数までは転機キーワードを含むエピソードを優先
TURNING_POINT_EXTRA_SLOTS = 2  # 5件制限を超えて2件まで転機を許可


def is_critical_turning_point(episode_text: str) -> bool:
    """エピソードが重要転機かどうか判定"""
    if not episode_text:
        return False
    return any(kw in episode_text for kw in TURNING_POINT_KEYWORDS)


# 7軸フィールド
SEVEN_AXIS_FIELDS = [
    "記憶性スコア",
    "共感性スコア",
    "意外性スコア",
    "生成品質スコア",
    "教育的価値",
    "ストーリー品質",
    "事実密度",
]

# 軸別改善プロンプト
AXIS_IMPROVEMENT_PROMPTS = {
    "共感性スコア": """
【共感性を高めてください】
- 人物の感情や内面の葛藤をより具体的に描写
- 読者が「自分だったら」と思える普遍的な状況を追加
- 感情的なクライマックスを明確に
""",
    "意外性スコア": """
【意外性を劇的に高めてください】

必ず以下のいずれかを含めてください:
1. 一般的なイメージと正反対の側面（例: 厳格な人物の意外な趣味、成功者の大失敗）
2. 逆転のエピソード（例: 絶望的状況からの復活、予想外の転機）
3. 時代を先取りした先見性（例: 当時は理解されなかったが後に評価された行動）
4. 意外な人物との関わり（例: 全く異なる分野の人物からの影響）

避けるべき表現:
- 「〜したと言われている」（曖昧で意外性なし）
- 「〜は有名である」（周知の事実は意外性なし）
- 淡々とした業績の羅列

目指す表現:
- 「誰もが驚いたことに」「実は〜」「〜とは対照的に」
- 「周囲の予想に反して」「意外にも」
""",
    "教育的価値": """
【教育的価値を高めてください】
- この経験から得られる具体的な教訓や学びを追加
- 他の人が参考にできる普遍的な知恵を含める
- 「なるほど」と思わせる洞察を追加
""",
    "事実密度": """
【具体的な事実・数値を必ず追加してください】

以下の要素を最低2つ以上含めてください:
1. 具体的な年号（例: 1985年、2003年）
2. 数値データ（例: 100万部突破、3時間、世界2位、10回目の挑戦）
3. 固有名詞（例: 作品名『〇〇』、場所名、共演者・関係者の名前）
4. 検証可能な記録（例: 史上初、ギネス記録、〇〇賞受賞）

避けるべき表現:
- 「多くの」「いくつかの」（曖昧）
- 「長年にわたり」（具体性なし）
- 「成功を収めた」だけで終わる（詳細なし）

目指す表現:
- 「1997年、32歳のとき」
- 「累計500万部を突破した」
- 「〇〇賞を受賞し、日本人として3人目となった」
""",
    "記憶性スコア": """
【記憶に残る要素を追加してください】
- 印象的なエピソードや名言を追加
- 視覚的に想像できる具体的なシーンを描写
- 読後も思い出したくなる印象的な結末を
""",
    "ストーリー品質": """
【ストーリー構成を改善してください】
- 起承転結をより明確に
- 導入で興味を引き、展開で引き込む構成に
- クライマックスと余韻を意識した構成に
""",
}


@dataclass
class GenerationStats:
    """生成統計"""

    total_attempts: int = 0
    success: int = 0
    rejected: int = 0
    retried: int = 0
    composite_scores: List[float] = field(default_factory=list)
    axis_scores: Dict[str, List[float]] = field(default_factory=dict)
    rejection_reasons: List[str] = field(default_factory=list)

    def __post_init__(self):
        for axis in SEVEN_AXIS_FIELDS:
            self.axis_scores[axis] = []

    def add_success(self, scores: Dict[str, float]):
        self.success += 1
        composite = self._calc_composite(scores)
        self.composite_scores.append(composite)
        for axis in SEVEN_AXIS_FIELDS:
            if axis in scores:
                self.axis_scores[axis].append(scores[axis])

    def add_rejection(self, reason: str):
        self.rejected += 1
        self.rejection_reasons.append(reason)

    def _calc_composite(self, scores: Dict) -> float:
        vals = [scores.get(a, 0) for a in SEVEN_AXIS_FIELDS if a in scores]
        if not vals:
            return 0
        # 0-1000スケールに変換
        avg = sum(vals) / len(vals)
        normalized = (avg - 1.0) / 9.0
        transformed = normalized**0.85
        return transformed * 1000

    def get_summary(self) -> Dict:
        avg_composite = sum(self.composite_scores) / len(self.composite_scores) if self.composite_scores else 0

        axis_avgs = {}
        for axis, scores in self.axis_scores.items():
            axis_avgs[axis] = sum(scores) / len(scores) if scores else 0

        return {
            "total_attempts": self.total_attempts,
            "success": self.success,
            "rejected": self.rejected,
            "retried": self.retried,
            "success_rate": self.success / self.total_attempts if self.total_attempts > 0 else 0,
            "avg_composite_score": round(avg_composite, 1),
            "axis_averages": {k: round(v, 2) for k, v in axis_avgs.items()},
            "top_rejection_reasons": self._count_reasons(),
        }

    def _count_reasons(self) -> Dict[str, int]:
        counts = {}
        for r in self.rejection_reasons:
            counts[r] = counts.get(r, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: -x[1])[:5])


def generate_person_id(person_name: str) -> str:
    """person_nameからperson_idを生成"""
    hash_obj = hashlib.md5(person_name.encode("utf-8"), usedforsecurity=False)
    hash_hex = hash_obj.hexdigest()[:7].upper()
    return f"P{hash_hex}"


def generate_episode_id() -> str:
    """ユニークなepisode_idを生成"""
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    random_suffix = random.randint(100, 999)
    return f"EP-{timestamp}{random_suffix}"


def llm_generate_draft(
    person_name: str,
    category: str,
    age: int,
    person_type: str = "REAL",
    work_title: Optional[str] = None,
) -> Optional[str]:
    """エピソードの初稿を生成"""

    if person_type == "FICTIONAL" and work_title:
        prompt = f"""あなたは、架空キャラクターの作品世界内での印象的なエピソードを創作する専門家です。

以下の架空キャラクターについて、{age}歳のときの印象的なエピソードを日本語で生成してください。

【重要ルール】
- 作品『{work_title}』の世界観・設定を尊重する
- 「架空のキャラクターなので〜」「実在しないため〜」といったメタ的な説明は絶対に書かない
- キャラクターらしい具体的なエピソードを創作する

キャラクター名: {person_name}
作品名: {work_title}
カテゴリ: {category}
年齢: {age}歳

【品質要件（重要）】
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で必ず始める
2. 読者が感情移入できる具体的なシーンを描写する
3. 予想外の展開や意外な事実を含める
4. 250-320文字程度
5. 印象に残る結末にする

エピソードテキスト:"""
    else:
        prompt = f"""あなたは、人物の人生における印象的なエピソードを生成する専門家です。

以下の人物について、{age}歳のときの印象的なエピソードを日本語で生成してください。

人物名: {person_name}
カテゴリ: {category}
年齢: {age}歳

【品質要件（重要）】
1. 「あなたと同じ{age}歳のとき、{person_name}は〜」という形式で必ず始める
2. 具体的な年号、数値、事実を含める（事実密度を高く）
3. 読者が感情移入できる感情描写を入れる（共感性を高く）
4. 予想外の展開や意外な事実を含める（意外性を高く）
5. 学びや教訓が得られる内容にする（教育的価値を高く）
6. 250-320文字程度
7. 印象に残る結末にする

エピソードテキスト:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  ❌ 生成エラー: {e}")
        return None


def llm_self_evaluate(episode_text: str) -> Optional[Dict[str, float]]:
    """LLMに7軸評価させる"""

    prompt = f"""以下のエピソードを7軸で評価してください。各軸1.0〜10.0点で採点してください。

【エピソード】
{episode_text}

【評価軸と基準】
1. 記憶性スコア: 読後も印象に残るか（具体的なシーン、名言、意外な事実）
2. 共感性スコア: 感情移入できるか（感情描写、普遍的な状況、内面の葛藤）
3. 意外性スコア: 予想外の展開があるか（意外な事実、常識を覆す視点）
4. 生成品質スコア: 文章として完成度が高いか（文法、構成、読みやすさ）
5. 教育的価値: 学びや教訓があるか（普遍的な知恵、参考になる経験）
6. ストーリー品質: 構成が良いか（起承転結、引き込む力、余韻）
7. 事実密度: 具体的なデータ・事実があるか（年号、数値、固有名詞）

【採点基準】
- 9-10点: 非常に優れている（上位5%レベル）
- 7-8点: 良い（平均以上）
- 5-6点: 普通（改善の余地あり）
- 3-4点: 不足している
- 1-2点: 大きく不足している

必ず以下のJSON形式のみで回答してください（説明不要）:
{{"記憶性スコア": X.X, "共感性スコア": X.X, "意外性スコア": X.X, "生成品質スコア": X.X, "教育的価値": X.X, "ストーリー品質": X.X, "事実密度": X.X}}"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=200, messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text.strip()

        # JSON部分を抽出
        json_match = re.search(r"\{[^}]+\}", text)
        if json_match:
            return json.loads(json_match.group())
        return None
    except Exception as e:
        print(f"  ❌ 評価エラー: {e}")
        return None


def calculate_composite_score(scores: Dict[str, float]) -> float:
    """7軸スコアから超総合スコア(0-1000)を計算"""
    vals = [scores.get(axis, 0) for axis in SEVEN_AXIS_FIELDS if axis in scores]
    if not vals:
        return 0

    avg = sum(vals) / len(vals)
    # 正規化 (1-10 → 0-1) → 非線形変換 (k=0.85) → 0-1000スケール
    normalized = max(0, (avg - 1.0) / 9.0)
    transformed = normalized**0.85
    return round(transformed * 1000, 1)


def find_weak_axes(scores: Dict[str, float]) -> List[str]:
    """改善が必要な軸を特定"""
    weak = []
    for axis, min_score in QUALITY_GATES["axis_minimums"].items():
        if axis in scores and scores[axis] < min_score:
            weak.append(axis)
    return weak


def build_improvement_prompt(weak_axes: List[str]) -> str:
    """弱い軸に対する改善指示を構築"""
    prompts = []
    for axis in weak_axes:
        if axis in AXIS_IMPROVEMENT_PROMPTS:
            prompts.append(AXIS_IMPROVEMENT_PROMPTS[axis])
    return "\n".join(prompts)


def llm_improve_draft(original_text: str, improvement_prompt: str) -> Optional[str]:
    """弱点を改善した改稿版を生成"""

    prompt = f"""以下のエピソードを改善してください。

【元のエピソード】
{original_text}

【改善指示】
{improvement_prompt}

【重要】
- 「あなたと同じN歳のとき、」で始まる形式は維持
- 250-320文字程度を維持
- 改善指示に従いつつ、元のエピソードの良い部分は残す

改善後のエピソード:"""

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514", max_tokens=500, messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip()
    except Exception as e:
        print(f"  ❌ 改稿エラー: {e}")
        return None


def get_person_episode_count(person_name: str) -> int:
    """指定人物の既存エピソード数を取得"""
    if not CSV_PATH.exists():
        return 0
    try:
        with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            return sum(1 for row in reader if row.get("person_name") == person_name)
    except Exception:
        return 0


EPISODE_LIMIT = 5  # 1人あたりのエピソード上限


def generate_episode_with_quality_gate(
    person_name: str,
    category: str,
    age: int,
    person_type: str = "REAL",
    work_title: Optional[str] = None,
    stats: Optional[GenerationStats] = None,
    skip_limit_check: bool = False,
    is_turning_point: bool = False,  # 重要転機フラグ
) -> Optional[Dict]:
    """品質ゲート付きエピソード生成

    Args:
        is_turning_point: Trueの場合、5件制限を緩和（+2件まで許可）
    """

    # Step 0: 5件制限チェック（転機優先対応）
    if not skip_limit_check:
        existing_count = get_person_episode_count(person_name)
        # 転機フラグがある場合は拡張制限を適用
        effective_limit = EPISODE_LIMIT + TURNING_POINT_EXTRA_SLOTS if is_turning_point else EPISODE_LIMIT
        if existing_count >= effective_limit:
            limit_type = f"転機拡張: {effective_limit}" if is_turning_point else str(EPISODE_LIMIT)
            print(f"\n⚠️ スキップ: {person_name} は既に{existing_count}件（制限: {limit_type}件）")
            if stats:
                stats.add_rejection("episode_limit_reached")
            return None
        elif existing_count >= EPISODE_LIMIT and is_turning_point:
            print(f"\n🌟 転機優先: {person_name} ({existing_count}件目→転機枠で許可)")

    # Step 0.5: 時間的妥当性チェック（未来/死亡後エピソード防止）
    is_valid, reason = validate_temporal_accuracy(person_name, age, person_type)
    if not is_valid:
        print(f"\n🚫 時間的妥当性エラー: {person_name} ({age}歳)")
        print(f"   理由: {reason}")
        if stats:
            stats.add_rejection("temporal_invalid")
        return None

    if stats:
        stats.total_attempts += 1

    print(f"\n{'='*60}")
    print(f"生成中: {person_name} ({age}歳, {category})")
    print(f"{'='*60}")

    for attempt in range(QUALITY_GATES["max_retries"] + 1):
        attempt_label = "初稿" if attempt == 0 else f"改稿{attempt}"
        print(f"\n  [{attempt_label}] 生成中...")

        # Step 1: 生成
        if attempt == 0:
            draft = llm_generate_draft(person_name, category, age, person_type, work_title)
        else:
            # 改稿
            weak_axes = find_weak_axes(evaluation)
            if not weak_axes:
                weak_axes = ["意外性スコア", "共感性スコア"]  # デフォルト改善軸
            improvement_prompt = build_improvement_prompt(weak_axes)
            print(f"  改善対象軸: {', '.join(weak_axes)}")
            draft = llm_improve_draft(draft, improvement_prompt)
            if stats:
                stats.retried += 1

        if not draft:
            if stats:
                stats.add_rejection("generation_failed")
            return None

        # Step 1.5: LLM拒否メッセージチェック（即棄却、リトライ不可）
        if is_refusal_message(draft):
            print("  🚫 LLM拒否メッセージ検出: このエピソードは生成不可")
            print(f"     テキスト: {draft[:100]}...")
            if stats:
                stats.add_rejection("refusal_message")
            return None

        # Step 1.6: 埋め草チェック（即棄却、リトライ不可）
        if is_filler(draft):
            filler_analysis = FillerAnalysis(draft)
            print(f"  ❌ 埋め草検出: 具体性={filler_analysis.specificity_score}, 抽象度={filler_analysis.filler_count}")
            print(f"     抽象フレーズ: {filler_analysis.matched_filler_phrases[:3]}")
            if stats:
                stats.add_rejection("filler_detected")
            return None

        print(f"  テキスト: {draft[:60]}...")

        # Step 2: 自己評価
        print("  自己評価中...")
        evaluation = llm_self_evaluate(draft)

        if not evaluation:
            if stats:
                stats.add_rejection("evaluation_failed")
            return None

        composite = calculate_composite_score(evaluation)
        print(f"  超総合スコア: {composite:.1f}")

        # 軸別スコア表示
        for axis in SEVEN_AXIS_FIELDS:
            score = evaluation.get(axis, 0)
            indicator = "✓" if score >= 5.0 else "△" if score >= 4.0 else "✗"
            print(f"    {indicator} {axis}: {score:.1f}")

        # Step 3: 品質ゲートチェック
        if composite >= QUALITY_GATES["target_composite"]:
            print(f"  ✅ 目標達成！ ({composite:.1f} >= {QUALITY_GATES['target_composite']})")
            if stats:
                stats.add_success(evaluation)
            return _create_episode_dict(
                person_name, category, age, person_type, draft, evaluation, composite, work_title
            )

        if composite < QUALITY_GATES["minimum_composite"]:
            print(f"  ❌ 最低ライン未達 ({composite:.1f} < {QUALITY_GATES['minimum_composite']})")
            if stats:
                stats.add_rejection(f"below_minimum_{composite:.0f}")
            return None

        # リトライ可能かチェック
        if attempt < QUALITY_GATES["max_retries"]:
            print(f"  → リトライ判定: {composite:.1f} < {QUALITY_GATES['target_composite']}")
        else:
            # 最終判定
            if composite >= QUALITY_GATES["retry_threshold"]:
                print(f"  ⚠️ リトライ後採用 ({composite:.1f} >= {QUALITY_GATES['retry_threshold']})")
                if stats:
                    stats.add_success(evaluation)
                return _create_episode_dict(
                    person_name, category, age, person_type, draft, evaluation, composite, work_title
                )
            else:
                print(f"  ❌ リトライ上限・基準未達 ({composite:.1f} < {QUALITY_GATES['retry_threshold']})")
                if stats:
                    stats.add_rejection(f"retry_exhausted_{composite:.0f}")
                return None

    return None


def _create_episode_dict(
    person_name: str,
    category: str,
    age: int,
    person_type: str,
    episode_text: str,
    scores: Dict[str, float],
    composite: float,
    work_title: Optional[str] = None,
) -> Dict:
    """エピソード辞書を作成"""
    return {
        "episode_id": generate_episode_id(),
        "person_id": generate_person_id(person_name),
        "person_name": person_name,
        "category": category,
        "age": age,
        "person_type": person_type,
        "work_title": work_title or "",
        "episode_text": episode_text,
        "episode_type": "TURNING_POINT",  # デフォルト
        "記憶性スコア": scores.get("記憶性スコア", 0),
        "共感性スコア": scores.get("共感性スコア", 0),
        "意外性スコア": scores.get("意外性スコア", 0),
        "生成品質スコア": scores.get("生成品質スコア", 0),
        "教育的価値": scores.get("教育的価値", 0),
        "ストーリー品質": scores.get("ストーリー品質", 0),
        "事実密度": scores.get("事実密度", 0),
        "composite_score": composite,
        "generation_method": "quality_gate_v1",
        "generated_at": datetime.now().isoformat(),
    }


def get_candidate_persons(count: int, ages: Optional[List[int]] = None) -> List[Dict]:
    """生成候補の人物リストを取得"""
    import pandas as pd

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    # ユニークな人物を取得
    persons = df.drop_duplicates(subset=["person_name"])[["person_name", "category", "person_type"]].to_dict("records")

    # ランダムにサンプル
    if len(persons) > count * 2:
        persons = random.sample(persons, count * 2)

    # 年齢を割り当て
    if ages is None:
        ages = list(range(20, 60))

    candidates = []
    for p in persons[:count]:
        p["age"] = random.choice(ages)
        candidates.append(p)

    return candidates


def save_results(episodes: List[Dict], stats: GenerationStats, output_path: Path):
    """結果を保存"""
    # CSV保存
    if episodes:
        with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=episodes[0].keys())
            writer.writeheader()
            writer.writerows(episodes)
        print(f"\n📁 結果保存: {output_path}")

    # レポート保存
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = REPORT_DIR / f"quality_gate_report_{timestamp}.json"

    report = {
        "timestamp": datetime.now().isoformat(),
        "quality_gates": QUALITY_GATES,
        "statistics": stats.get_summary(),
        "episodes_generated": len(episodes),
    }

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"📊 レポート保存: {report_path}")


def main():
    parser = argparse.ArgumentParser(description="品質ゲート付きエピソード生成")
    parser.add_argument("--count", type=int, default=10, help="生成数")
    parser.add_argument("--ages", type=str, help="対象年齢（カンマ区切り）例: 25,30,35")
    parser.add_argument("--output", type=str, help="出力CSVパス")
    parser.add_argument("--execute", action="store_true", help="本番実行")
    parser.add_argument("--dry-run", action="store_true", help="ドライラン（実際には保存しない）")

    args = parser.parse_args()

    print("=" * 80)
    print("🚀 品質ゲート付きエピソード生成システム v1.0")
    print("=" * 80)
    print()
    print("【品質ゲート設定】")
    print(f"  最低ライン: {QUALITY_GATES['minimum_composite']}")
    print(f"  目標ライン: {QUALITY_GATES['target_composite']}")
    print(f"  リトライ閾値: {QUALITY_GATES['retry_threshold']}")
    print(f"  最大リトライ: {QUALITY_GATES['max_retries']}回")
    print()

    # 年齢パース
    ages = None
    if args.ages:
        ages = [int(a.strip()) for a in args.ages.split(",")]
        print(f"対象年齢: {ages}")

    # 出力パス
    output_path = (
        Path(args.output)
        if args.output
        else PROJECT_ROOT / "generated" / f"quality_gate_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # 候補取得
    print(f"\n生成候補を取得中... (目標: {args.count}件)")
    candidates = get_candidate_persons(args.count, ages)
    print(f"  候補数: {len(candidates)}件")

    # 統計
    stats = GenerationStats()
    episodes = []

    # 生成ループ
    print(f"\n{'='*80}")
    print("生成開始")
    print(f"{'='*80}")

    for i, candidate in enumerate(candidates):
        print(f"\n[{i+1}/{len(candidates)}]")

        episode = generate_episode_with_quality_gate(
            person_name=candidate["person_name"],
            category=candidate["category"],
            age=candidate["age"],
            person_type=candidate.get("person_type", "REAL"),
            stats=stats,
        )

        if episode:
            episodes.append(episode)

        # レート制限対策
        time.sleep(0.5)

    # 結果サマリー
    print(f"\n{'='*80}")
    print("生成完了")
    print(f"{'='*80}")

    summary = stats.get_summary()
    print("\n【統計サマリー】")
    print(f"  試行数: {summary['total_attempts']}")
    print(f"  成功: {summary['success']} ({summary['success_rate']*100:.1f}%)")
    print(f"  棄却: {summary['rejected']}")
    print(f"  リトライ: {summary['retried']}")
    print(f"  超総合平均: {summary['avg_composite_score']:.1f}")
    print()
    print("【7軸平均】")
    for axis, avg in summary["axis_averages"].items():
        indicator = "✓" if avg >= 6.0 else "△" if avg >= 5.0 else "✗"
        print(f"  {indicator} {axis}: {avg:.2f}")

    if summary["top_rejection_reasons"]:
        print("\n【棄却理由TOP】")
        for reason, count in summary["top_rejection_reasons"].items():
            print(f"  {reason}: {count}件")

    # 保存
    if not args.dry_run and (args.execute or episodes):
        save_results(episodes, stats, output_path)
    else:
        print("\n⚠️ ドライランモード: 結果は保存されません")
        print("   --execute オプションで本番実行してください")


if __name__ == "__main__":
    main()
