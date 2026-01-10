"""
Episode Type 推定モジュール

エピソードテキストからepisode_typeを自動推定する。
推定不能な場合は None を返し、保留キューへ送る。

EPUP準拠: 欠損補完ミッション Phase 1
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# 有効なエピソードタイプ（completeness.pyと同期）
VALID_EPISODE_TYPES = {"転機", "達成", "死去", "挑戦", "キャリア", "革新", "創業", "失敗", "復帰"}


# キーワードによるタイプ推定（優先度順）
# 優先度高いものから順にチェックし、最初にマッチしたタイプを返す
EPISODE_TYPE_PATTERNS = [
    # 死去（最優先：一義的に決定可能）
    (
        "死去",
        [
            r"亡くなった",
            r"死去",
            r"逝去",
            r"他界",
            r"没した",
            r"息を引き取った",
            r"この世を去った",
            r"永眠",
        ],
    ),
    # 達成（偉業・受賞系）
    (
        "達成",
        [
            r"達成",
            r"成功",
            r"優勝",
            r"受賞",
            r"金メダル",
            r"銀メダル",
            r"銅メダル",
            r"ノーベル賞",
            r"アカデミー賞",
            r"グランプリ",
            r"チャンピオン",
            r"世界記録",
            r"日本記録",
            r"新記録",
            r"初優勝",
            r"連覇",
            r"制覇",
            r"栄冠",
            r"快挙",
            r"偉業",
            r"大ヒット",
            r"ベストセラー",
            r"完全試合",
            r"ノーヒットノーラン",
            r"三冠王",
            r"MVP",
        ],
    ),
    # 創業・設立
    (
        "創業",
        [
            r"創業",
            r"設立",
            r"起業",
            r"創設",
            r"立ち上げ",
            r"会社を興し",
            r"独立開業",
            r"事業を始め",
        ],
    ),
    # 革新・発明
    (
        "革新",
        [
            r"発明",
            r"発見",
            r"開発",
            r"革新",
            r"新技術",
            r"画期的",
            r"革命的",
            r"ブレークスルー",
            r"先駆者",
            r"パイオニア",
            r"イノベーション",
            r"世界初",
            r"日本初",
            r"業界初",
        ],
    ),
    # 失敗・挫折
    (
        "失敗",
        [
            r"失敗",
            r"挫折",
            r"敗北",
            r"落選",
            r"破産",
            r"倒産",
            r"失脚",
            r"解雇",
            r"追放",
            r"退場",
            r"引退を余儀なく",
            r"戦力外",
            r"契約解除",
        ],
    ),
    # 復帰
    (
        "復帰",
        [
            r"復帰",
            r"カムバック",
            r"再起",
            r"復活",
            r"再挑戦",
            r"再出発",
            r"返り咲き",
            r"復調",
        ],
    ),
    # キャリア・就任
    (
        "キャリア",
        [
            r"就任",
            r"入社",
            r"入団",
            r"デビュー",
            r"プロ入り",
            r"初登板",
            r"初出場",
            r"初主演",
            r"抜擢",
            r"監督就任",
            r"社長就任",
            r"代表取締役",
            r"芸能界入り",
            r"移籍",
        ],
    ),
    # 挑戦
    (
        "挑戦",
        [
            r"挑戦",
            r"チャレンジ",
            r"試み",
            r"挑む",
            r"立ち向かった",
            r"飛び込んだ",
            r"踏み出した",
            r"決断",
            r"決意",
            r"覚悟",
            r"賭けに出",
        ],
    ),
    # 転機（最後：汎用）
    (
        "転機",
        [
            r"転機",
            r"きっかけ",
            r"転換点",
            r"変わった",
            r"一変",
            r"変貌",
            r"方向転換",
            r"人生を変えた",
            r"運命の",
            r"出会い",
            r"契機",
        ],
    ),
]


@dataclass
class InferenceResult:
    """推定結果"""

    episode_type: Optional[str]  # 推定されたタイプ（推定不能ならNone）
    confidence: str  # "high", "medium", "low", "none"
    matched_keywords: list[str]  # マッチしたキーワード
    reason: str  # 推定理由


def infer_episode_type(episode_text: str) -> InferenceResult:
    """
    エピソードテキストからepisode_typeを推定

    Args:
        episode_text: エピソードテキスト

    Returns:
        InferenceResult: 推定結果
    """
    if not episode_text or len(episode_text) < 20:
        return InferenceResult(
            episode_type=None,
            confidence="none",
            matched_keywords=[],
            reason="テキストが短すぎる",
        )

    text = str(episode_text)
    matched_types: dict[str, list[str]] = {}

    # パターンマッチング
    for ep_type, patterns in EPISODE_TYPE_PATTERNS:
        matches = []
        for pattern in patterns:
            if re.search(pattern, text):
                matches.append(pattern)

        if matches:
            matched_types[ep_type] = matches

    # マッチなし
    if not matched_types:
        return InferenceResult(
            episode_type=None,
            confidence="none",
            matched_keywords=[],
            reason="マッチするキーワードなし",
        )

    # 最も多くマッチしたタイプを選択
    best_type = max(matched_types.keys(), key=lambda t: len(matched_types[t]))
    best_matches = matched_types[best_type]

    # 信頼度判定
    match_count = len(best_matches)
    if match_count >= 3:
        confidence = "high"
    elif match_count >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    return InferenceResult(
        episode_type=best_type,
        confidence=confidence,
        matched_keywords=best_matches[:5],  # 最大5件
        reason=f"{match_count}キーワードマッチ: {', '.join(best_matches[:3])}",
    )


def infer_episode_type_simple(episode_text: str) -> Optional[str]:
    """
    シンプル版: episode_typeのみを返す

    Args:
        episode_text: エピソードテキスト

    Returns:
        str | None: 推定されたepisode_type、推定不能ならNone
    """
    result = infer_episode_type(episode_text)
    return result.episode_type


def validate_episode_type(episode_type: str) -> bool:
    """episode_typeが有効かチェック"""
    return episode_type in VALID_EPISODE_TYPES


# CLI対応
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        text = sys.argv[1]
        result = infer_episode_type(text)
        print(f"Type: {result.episode_type}")
        print(f"Confidence: {result.confidence}")
        print(f"Keywords: {result.matched_keywords}")
        print(f"Reason: {result.reason}")
    else:
        # テスト実行
        test_cases = [
            "あなたと同じ25歳のとき、田中太郎は世界選手権で優勝を果たした。",
            "あなたと同じ30歳のとき、山田花子は会社を設立した。",
            "あなたと同じ45歳のとき、鈴木一郎はこの世を去った。",
            "あなたと同じ20歳のとき、佐藤次郎はプロ野球入りを果たした。",
            "あなたと同じ35歳のとき、高橋三郎は新技術を開発した。",
            "あなたと同じ40歳のとき、伊藤四郎は事業に失敗した。",
            "あなたと同じ50歳のとき、渡辺五郎は芸能界に復帰した。",
            "あなたと同じ22歳のとき、中村六郎は新しい挑戦に踏み出した。",
            "あなたと同じ28歳のとき、小林七郎は人生の転機を迎えた。",
        ]

        print("=== Episode Type Inference Test ===\n")
        for text in test_cases:
            result = infer_episode_type(text)
            print(f"Text: {text[:50]}...")
            print(f"  → Type: {result.episode_type} ({result.confidence})")
            print(f"     Keywords: {result.matched_keywords}")
            print()
