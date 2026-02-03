#!/usr/bin/env python3
"""
HallucinationDetector - LLMハルシネーション（虚偽・捏造エピソード）検出モジュール

## 目的
LLMが生成したエピソードの中から、虚偽や捏造が疑われるものを検出する。
REAL人物とFICTIONAL人物で異なるルールを適用。

## 検出ルール

### REAL人物
削除対象 = unverified + (メタ要素違反 OR 年齢矛盾 OR fabricated OR 年号違反)
- RealPersonVerifier の結果で passed=False の場合

### FICTIONAL人物
- FictionalQualityGate で passed=False かつ authenticity_status=INVALID の場合のみ削除
- canon と fanon は許容（削除対象外）

## 使用方法
    from scripts.validation.hallucination_detector import HallucinationDetector

    detector = HallucinationDetector()
    result = detector.detect(episode)

    if result.is_hallucination:
        print(f"ハルシネーション検出: {result.reason}")

    # 全スキャン
    results = detector.scan_all(csv_path, limit=100)
    deletion_candidates = detector.get_deletion_candidates(results)

Author: EPUP Validation Team
Date: 2026-02-03
"""

from __future__ import annotations

import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from scripts.validation.real_person_verifier import RealPersonVerifier, ViolationType as RealViolationType
from src.utils.fictional_quality_gate import FictionalQualityGate
from src.utils.authenticity_checker import AuthenticityStatus
from src.utils.fictional_characters import is_fictional_character

# =============================================================================
# パス設定
# =============================================================================

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

# =============================================================================
# ロギング設定
# =============================================================================

logger = logging.getLogger(__name__)


# =============================================================================
# メタ要素パターン（detect_meta_element_violations.pyから流用）
# =============================================================================

META_PATTERNS: dict[str, list[str]] = {
    "販売本数": [
        r"(?:\d+万?本|累計\d+部)(?:を|が)(?:突破|達成|記録|売上)",
        r"(?:販売|売上)[が高]?(?:\d+|記録)",
        r"(?:売れ行き|販売実績|売上高)",
        r"(?:\d+(?:万|億)?部)(?:以上)?(?:を|が)?(?:突破|達成|記録|売上|販売)",
    ],
    "興行成績": [
        r"(?:興行収入|興行成績|観客動員)(?:が)?(?:\d+|〜|が|は)",
        r"(?:動員数|観客数)(?:\d+万人|が)",
        r"(?:歴代|過去)(?:\d+位|最高)",
        r"(?:大ヒット|メガヒット)(?:を記録|作品)",
    ],
    "開発・製作": [
        r"(?:\d+年間?の)?(?:開発|製作|撮影)(?:期間|準備|開始|が始)",
        r"(?:映画化|アニメ化|実写化|ドラマ化|ゲーム化)(?:され|が決定|の発表|が発表)",
        r"(?:スタッフ|キャスト|声優)(?:が発表|が決定|陣)",
        r"(?:制作|製作)(?:委員会|チーム|スタッフ)",
    ],
    "ゲーム的表現": [
        r"(?:魔力|攻撃力|防御力|判断力|耐久力|HP|MP|レベル)(?:\d+%?|\d+ポイント|が\d+)",
        r"(?:ステータス|パラメータ|能力値)(?:が|は|の)",
    ],
    "現実イベント": [
        r"(?:東京ゲームショウ|E3|コミケ|コミックマーケット|映画祭)",
        r"(?:アカデミー賞|グラミー賞|エミー賞|カンヌ|ベネチア)",
    ],
    "作品メタ言及": [
        r"この(?:作品|アニメ|漫画|マンガ|ゲーム)(?:では|において|の中で|は)",
        r"(?:原作|漫画版|アニメ版|映画版|実写版|ゲーム版)(?:では|において|の中で|と(?:は|の)違い)",
        r"(?:連載|放送|配信)(?:当時|開始時|終了時|中)",
        r"(?:作者|原作者|監督)(?:が描いた|の意図|によると|が)",
    ],
    "年号+作品名": [
        r"(?:19[0-9]{2}|20[0-2][0-9])年の[『「].+?[』」]",
        r"[『「].+?[』」](?:が|は|を)?(?:19[0-9]{2}|20[0-2][0-9])年",
    ],
    "現実企業名": [
        r"任天堂|スクウェア・エニックス|バンダイナムコ|カプコン|コナミ|セガ",
        r"集英社|講談社|小学館|角川|KADOKAWA",
        r"週刊少年ジャンプ|少年マガジン|少年サンデー|Vジャンプ",
    ],
    "現実人物名_作者": [
        r"鳥山明|尾田栄一郎|岸本斉史|荒川弘|手塚治虫|藤子不二雄|藤子・F・不二雄",
        r"宮崎駿|庵野秀明|新海誠|高橋留美子|冨樫義博|久保帯人|諫山創",
    ],
}

# コンパイル済みパターン（遅延初期化用）
_compiled_meta_patterns_cache: list[re.Pattern[str]] = []


def get_compiled_meta_patterns() -> list[re.Pattern[str]]:
    """コンパイル済みメタ要素パターンを取得（遅延初期化）"""
    global _compiled_meta_patterns_cache
    if not _compiled_meta_patterns_cache:
        for patterns in META_PATTERNS.values():
            for pattern in patterns:
                _compiled_meta_patterns_cache.append(re.compile(pattern))
    return _compiled_meta_patterns_cache


# =============================================================================
# データクラス
# =============================================================================


@dataclass
class DetectionResult:
    """ハルシネーション検出結果"""

    episode_id: str
    person_name: str
    person_type: str  # REAL or FICTIONAL
    age: int
    is_hallucination: bool
    reason: str  # 検出理由
    violation_type: str  # fabrication, meta_element, year_violation, invalid等
    confidence: float  # 0.0-1.0
    super_total_score: float

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "episode_id": self.episode_id,
            "person_name": self.person_name,
            "person_type": self.person_type,
            "age": self.age,
            "is_hallucination": self.is_hallucination,
            "reason": self.reason,
            "violation_type": self.violation_type,
            "confidence": self.confidence,
            "super_total_score": self.super_total_score,
        }


# =============================================================================
# HallucinationDetector クラス
# =============================================================================


class HallucinationDetector:
    """
    ハルシネーション検出クラス

    REAL人物とFICTIONAL人物で異なるルールを適用し、
    LLMによる虚偽・捏造エピソードを検出する。
    """

    def __init__(self, enable_web_verification: bool = False):
        """
        初期化

        Args:
            enable_web_verification: Web検証を有効化するか（将来拡張用）
        """
        # 既存ツールを再利用
        self._real_verifier = RealPersonVerifier()
        self._fictional_gate = FictionalQualityGate(enable_authenticity_check=True)
        self._enable_web = enable_web_verification
        self._meta_patterns = get_compiled_meta_patterns()

    def _detect_meta_elements(self, text: str) -> list[str]:
        """
        メタ要素パターンを検出

        Args:
            text: エピソードテキスト

        Returns:
            検出されたメタ要素のリスト
        """
        detected: list[str] = []
        if not text:
            return detected

        for pattern in self._meta_patterns:
            matches = pattern.findall(text)
            detected.extend(matches)

        return detected

    def _is_fictional(self, person_type: str, person_name: str) -> bool:
        """
        架空キャラクターかどうかを判定

        Args:
            person_type: 人物タイプ
            person_name: 人物名

        Returns:
            架空キャラクターならTrue
        """
        if "FICTIONAL" in str(person_type).upper():
            return True
        return is_fictional_character(person_name)

    def _detect_real_person(self, episode: dict) -> DetectionResult:
        """
        REAL人物のハルシネーション検出

        Args:
            episode: エピソードデータ

        Returns:
            DetectionResult
        """
        episode_id = str(episode.get("episode_id", ""))
        person_name = str(episode.get("person_name", ""))
        person_type = "REAL"
        episode_text = str(episode.get("episode_text", ""))
        super_total_score = float(episode.get("super_total_score", 0) or 0)

        # age を数値に変換
        raw_age = episode.get("age", 0)
        try:
            age = int(raw_age) if raw_age and str(raw_age).replace(".", "").isdigit() else 0
        except (ValueError, TypeError):
            age = 0

        # birth_year, death_year を取得
        birth_year = episode.get("birth_year")
        death_year = episode.get("death_year")
        source = episode.get("source")

        # source が NaN や float の場合は None に変換
        if source is not None:
            try:
                source = str(source) if not pd.isna(source) else None
            except (ValueError, TypeError):
                source = None

        # 数値変換
        if birth_year:
            try:
                birth_year = int(birth_year)
            except (ValueError, TypeError):
                birth_year = None

        if death_year:
            try:
                death_year = int(death_year)
            except (ValueError, TypeError):
                death_year = None

        # 1. RealPersonVerifier で検証
        verification = self._real_verifier.verify(
            person_name=person_name,
            episode_text=episode_text,
            age=float(age),
            birth_year=birth_year,
            death_year=death_year,
            source=source,
        )

        if not verification.passed:
            # 違反タイプをマッピング
            violation_type = verification.violation_type.value if verification.violation_type else "unknown"

            # 確信度を計算（違反の重大さに応じて）
            confidence = 0.8
            if verification.violation_type == RealViolationType.FABRICATION:
                confidence = 0.9
            elif verification.violation_type == RealViolationType.FILLER:
                confidence = 0.6
            elif verification.violation_type == RealViolationType.FUTURE_EPISODE:
                confidence = 0.95
            elif verification.violation_type == RealViolationType.POST_DEATH:
                confidence = 0.95

            return DetectionResult(
                episode_id=episode_id,
                person_name=person_name,
                person_type=person_type,
                age=age,
                is_hallucination=True,
                reason=verification.violation_detail,
                violation_type=violation_type,
                confidence=confidence,
                super_total_score=super_total_score,
            )

        # 2. メタ要素チェックはREAL人物には適用しない
        # REAL人物の受賞歴（アカデミー賞、グラミー賞等）は正当なエピソードであり、
        # メタ要素検出はFICTIONAL人物専用（RCA-20260203）

        # 検証通過
        return DetectionResult(
            episode_id=episode_id,
            person_name=person_name,
            person_type=person_type,
            age=age,
            is_hallucination=False,
            reason="",
            violation_type="",
            confidence=0.0,
            super_total_score=super_total_score,
        )

    def _detect_fictional_character(self, episode: dict) -> DetectionResult:
        """
        FICTIONAL人物のハルシネーション検出

        Args:
            episode: エピソードデータ

        Returns:
            DetectionResult
        """
        episode_id = str(episode.get("episode_id", ""))
        person_name = str(episode.get("person_name", ""))
        person_type = "FICTIONAL"
        super_total_score = float(episode.get("super_total_score", 0) or 0)

        # age を数値に変換
        raw_age = episode.get("age", 0)
        try:
            age = int(raw_age) if raw_age and str(raw_age).replace(".", "").isdigit() else 0
        except (ValueError, TypeError):
            age = 0

        # FictionalQualityGate で検証
        gate_result = self._fictional_gate.check(episode)

        if not gate_result.passed:
            # authenticity_status が INVALID の場合のみ削除対象
            # canon と fanon は許容
            if gate_result.authenticity_status == AuthenticityStatus.INVALID:
                violations_str = "; ".join([v.detail for v in gate_result.violations[:3]])
                return DetectionResult(
                    episode_id=episode_id,
                    person_name=person_name,
                    person_type=person_type,
                    age=age,
                    is_hallucination=True,
                    reason=f"真正性検証失敗 (INVALID): {violations_str}",
                    violation_type="invalid",
                    confidence=0.85,
                    super_total_score=super_total_score,
                )

            # その他の違反（年号違反、メタ表現等）も検出するが、
            # authenticity_status が CANON/NO_MATCH の場合は警告のみ（削除対象外）
            # ただし、メタ表現違反は重大なので削除対象とする
            for v in gate_result.violations:
                if v.type.value == "meta_expression":
                    return DetectionResult(
                        episode_id=episode_id,
                        person_name=person_name,
                        person_type=person_type,
                        age=age,
                        is_hallucination=True,
                        reason=f"メタ表現検出: {v.detail}",
                        violation_type="meta_element",
                        confidence=0.8,
                        super_total_score=super_total_score,
                    )

        # 検証通過（またはcanon/fanon）
        return DetectionResult(
            episode_id=episode_id,
            person_name=person_name,
            person_type=person_type,
            age=age,
            is_hallucination=False,
            reason="",
            violation_type="",
            confidence=0.0,
            super_total_score=super_total_score,
        )

    def detect(self, episode: dict) -> DetectionResult:
        """
        単一エピソードのハルシネーション検出

        Args:
            episode: エピソードデータ（dict）
                必須キー: episode_id, person_name, person_type, episode_text, age
                オプションキー: birth_year, death_year, source, work_title, super_total_score

        Returns:
            DetectionResult
        """
        person_type = str(episode.get("person_type", "")).upper()
        person_name = str(episode.get("person_name", ""))

        # 架空キャラクターかどうかを判定
        is_fictional = self._is_fictional(person_type, person_name)

        if is_fictional:
            return self._detect_fictional_character(episode)
        else:
            return self._detect_real_person(episode)

    def scan_all(
        self,
        csv_path: Optional[Path] = None,
        limit: int = 0,
        person_type_filter: Optional[str] = None,
    ) -> list[DetectionResult]:
        """
        全エピソードをスキャン

        Args:
            csv_path: CSVファイルパス（省略時はMASTER_CSV）
            limit: 処理件数上限（0=無制限）
            person_type_filter: 対象の人物タイプ（REAL/FICTIONAL/None=ALL）

        Returns:
            DetectionResultのリスト
        """
        csv_path = csv_path or MASTER_CSV
        results: list[DetectionResult] = []

        if not csv_path.exists():
            logger.error(f"CSVファイルが見つかりません: {csv_path}")
            return results

        logger.info(f"CSVファイル読み込み: {csv_path}")
        df = pd.read_csv(csv_path, encoding="utf-8-sig", low_memory=False)

        # person_type でフィルター（スキャン前）
        if person_type_filter and person_type_filter.upper() != "ALL":
            df = df[df["person_type"].str.upper() == person_type_filter.upper()]
            logger.info(f"person_type={person_type_filter}でフィルター: {len(df)}件")

        total = len(df) if limit == 0 else min(limit, len(df))

        logger.info(f"スキャン開始: {total}件")

        processed = 0
        for _, row in df.iterrows():
            if limit > 0 and processed >= limit:
                break

            episode = row.to_dict()
            result = self.detect(episode)
            results.append(result)

            processed += 1

            # 進捗表示（50件ごと）
            if processed % 50 == 0:
                hallucinations = sum(1 for r in results if r.is_hallucination)
                pct = (processed / total) * 100
                logger.info(f"進捗: {processed}/{total} ({pct:.1f}%) - ハルシネーション: {hallucinations}件")

        # 最終結果
        hallucinations = sum(1 for r in results if r.is_hallucination)
        logger.info(f"スキャン完了: {processed}件処理, ハルシネーション: {hallucinations}件検出")

        return results

    def get_deletion_candidates(self, results: list[DetectionResult]) -> list[dict]:
        """
        削除候補を抽出

        Args:
            results: DetectionResultのリスト

        Returns:
            削除候補エピソードの情報リスト
        """
        candidates: list[dict] = []

        for r in results:
            if r.is_hallucination:
                candidates.append(r.to_dict())

        # confidence降順でソート
        candidates.sort(key=lambda x: x["confidence"], reverse=True)

        return candidates

    def get_summary(self, results: list[DetectionResult]) -> dict:
        """
        検出結果のサマリーを取得

        Args:
            results: DetectionResultのリスト

        Returns:
            サマリー情報
        """
        total = len(results)
        hallucinations = [r for r in results if r.is_hallucination]
        passed = [r for r in results if not r.is_hallucination]

        # violation_type 別集計
        by_violation_type: dict[str, int] = {}
        for r in hallucinations:
            vt = r.violation_type or "unknown"
            by_violation_type[vt] = by_violation_type.get(vt, 0) + 1

        # person_type 別集計
        by_person_type: dict[str, dict[str, int]] = {
            "REAL": {"total": 0, "hallucination": 0},
            "FICTIONAL": {"total": 0, "hallucination": 0},
        }
        for r in results:
            pt = r.person_type if r.person_type in by_person_type else "REAL"
            by_person_type[pt]["total"] += 1
            if r.is_hallucination:
                by_person_type[pt]["hallucination"] += 1

        return {
            "total": total,
            "hallucinations": len(hallucinations),
            "passed": len(passed),
            "by_violation_type": by_violation_type,
            "by_person_type": by_person_type,
        }


# =============================================================================
# CLI
# =============================================================================


def main() -> int:
    """CLI エントリーポイント"""
    import argparse
    import json
    from datetime import datetime

    parser = argparse.ArgumentParser(
        description="HallucinationDetector - LLMハルシネーション検出ツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用例:
  # 全エピソードをスキャン（上限100件）
  python scripts/validation/hallucination_detector.py --limit 100

  # 削除候補をJSON出力
  python scripts/validation/hallucination_detector.py --output candidates.json

  # REAL人物のみスキャン
  python scripts/validation/hallucination_detector.py --person-type REAL

  # FICTIONAL人物のみスキャン
  python scripts/validation/hallucination_detector.py --person-type FICTIONAL
        """,
    )
    parser.add_argument(
        "--csv",
        type=str,
        help="検証対象のCSVファイルパス（デフォルト: MASTER_EPISODES_CURRENT.csv）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="処理件数上限（0=無制限）",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="削除候補の出力先JSONファイルパス",
    )
    parser.add_argument(
        "--person-type",
        type=str,
        choices=["REAL", "FICTIONAL", "ALL"],
        default="ALL",
        help="対象の人物タイプ（デフォルト: ALL）",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="詳細ログ出力",
    )

    args = parser.parse_args()

    # ログ設定
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # ヘッダー表示
    print("=" * 70)
    print("HallucinationDetector - LLMハルシネーション検出ツール")
    print(f"実行日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    # 検出器初期化
    detector = HallucinationDetector()

    # CSV パス
    csv_path = Path(args.csv) if args.csv else MASTER_CSV

    if not csv_path.exists():
        logger.error(f"CSVファイルが見つかりません: {csv_path}")
        return 1

    # スキャン実行
    results = detector.scan_all(csv_path, limit=args.limit)

    # person_type でフィルタ
    if args.person_type != "ALL":
        results = [r for r in results if r.person_type == args.person_type]

    # サマリー表示
    summary = detector.get_summary(results)
    print("\n" + "=" * 70)
    print("検出結果サマリー")
    print("=" * 70)
    print(f"総エピソード数: {summary['total']}")
    print(f"ハルシネーション検出: {summary['hallucinations']}件")
    print(f"合格: {summary['passed']}件")

    print("\n【違反タイプ別】")
    for vt, count in sorted(summary["by_violation_type"].items(), key=lambda x: -x[1]):
        print(f"  {vt}: {count}件")

    print("\n【人物タイプ別】")
    for pt, stats in summary["by_person_type"].items():
        if stats["total"] > 0:
            rate = (stats["hallucination"] / stats["total"]) * 100
            print(f"  {pt}: {stats['hallucination']}/{stats['total']} ({rate:.1f}%)")

    # 削除候補を表示
    candidates = detector.get_deletion_candidates(results)
    if candidates:
        print("\n" + "=" * 70)
        print(f"削除候補（上位10件 / 全{len(candidates)}件）")
        print("=" * 70)
        for i, c in enumerate(candidates[:10], 1):
            print(
                f"[{i}] {c['episode_id']} | {c['person_name']} ({c['age']}歳) | "
                f"{c['person_type']} | {c['violation_type']} | conf={c['confidence']:.2f}"
            )
            print(f"    理由: {c['reason'][:80]}...")

    # JSON出力
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_data = {
            "summary": summary,
            "execution_time": datetime.now().isoformat(),
            "csv_path": str(csv_path),
            "limit": args.limit,
            "person_type_filter": args.person_type,
            "candidates": candidates,
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n削除候補を保存: {output_path}")

    print("\n" + "=" * 70)
    print("[完了]")

    # 終了コード（ハルシネーションがあれば1）
    return 1 if summary["hallucinations"] > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
