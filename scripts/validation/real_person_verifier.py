#!/usr/bin/env python3
"""
RealPersonVerifier - 実在人物エピソード検証クラス

既存のpurge_fabricated_episodes.pyから活用するパターン:
- FILLER_PATTERNS (20個): 埋草表現
- CONCRETE_PATTERNS (25個): 具体的事実
- FABRICATION_PATTERNS (10個): LLM捏造パターン

判定ロジック:
- 埋草判定: 埋草スコア >= 3 AND 具体性スコア < 2
- 未来エピソード: 現在年 + FUTURE_THRESHOLD年を超える
- 死亡後エピソード: death_year を超える年のエピソード
- 捏造判定: SURPRISE_IMPROVED源 + 捏造パターン検出
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ViolationType(Enum):
    """違反タイプの列挙型"""

    FABRICATION = "fabrication"  # LLMによる捏造
    FILLER = "filler"  # 埋草・抽象的すぎる内容
    FUTURE_EPISODE = "future_episode"  # 未来の架空エピソード
    POST_DEATH = "post_death"  # 死亡後のエピソード
    TIMELINE_ERROR = "timeline_error"  # タイムライン整合性エラー
    NO_WIKIPEDIA = "no_wikipedia"  # Wikipedia検証失敗


@dataclass
class VerificationResult:
    """検証結果を格納するデータクラス"""

    passed: bool
    violation_type: Optional[ViolationType]
    violation_detail: str
    filler_score: int
    concrete_score: int
    fabrication_patterns: list[str] = field(default_factory=list)
    suggestion: Optional[str] = None
    wikipedia_verified: bool = False

    def to_dict(self) -> dict:
        """辞書形式に変換"""
        return {
            "passed": self.passed,
            "violation_type": self.violation_type.value if self.violation_type else None,
            "violation_detail": self.violation_detail,
            "filler_score": self.filler_score,
            "concrete_score": self.concrete_score,
            "fabrication_patterns": self.fabrication_patterns,
            "suggestion": self.suggestion,
            "wikipedia_verified": self.wikipedia_verified,
        }


class RealPersonVerifier:
    """
    実在人物エピソード検証クラス

    以下の観点で実在人物のエピソードを検証:
    1. 未来エピソード検出（現在年 + 閾値を超える）
    2. 死亡後エピソード検出
    3. 埋草パターン検出（抽象的すぎる内容）
    4. 捏造パターン検出（LLMが創作した可能性の高い内容）
    5. Wikipedia検証（オプション）
    """

    CURRENT_YEAR = 2026
    FUTURE_THRESHOLD = 2  # 現在年 + 2年を超えると未来エピソード

    # 埋め草パターン（抽象的・継続的な表現）
    FILLER_PATTERNS = [
        "続けていました",
        "行っていました",
        "取り組んでいました",
        "貫いていました",
        "示していました",
        "教えてくれます",
        "体現し",
        "創作活動を行",
        "活動を続けて",
        "挑戦を続けて",
        "ペースで",
        "姿勢を",
        "信念を",
        "次世代の育成",
        "助言者として",
        "還元する",
        "境地にあり",
        "円熟の",
        "精力的に",
        "なお現役",
    ]

    # 具体的事実パターン（検証可能な事実を示す表現）
    CONCRETE_PATTERNS = [
        "発表",
        "発売",
        "受賞",
        "優勝",
        "記録",
        "達成",
        "完成",
        "出版",
        "公開",
        "デビュー",
        "初",
        "金メダル",
        "銀メダル",
        "銅メダル",
        "賞を",
        "に選ばれ",
        "に就任",
        "を設立",
        "を創業",
        "億円",
        "億部",
        "万部",
        "万枚",
        "万人",
    ]

    # 捏造パターン（LLMが創作しがちな表現）
    FABRICATION_PATTERNS = [
        "養蜂業",
        "農業を始め",
        "突然現役引退",
        "周囲の猛反対を押し切",
        "意外にも",
        "予想外",
        "衝撃的な告白",
        "コラボレーション",
        "AIと",
        "過疎地域で",
    ]

    def __init__(self, wikipedia_client=None):
        """
        初期化

        Args:
            wikipedia_client: Wikipedia検証用クライアント（オプション）
        """
        self.wikipedia_client = wikipedia_client

    def verify(
        self,
        person_name: str,
        episode_text: str,
        age: float,
        birth_year: Optional[int] = None,
        death_year: Optional[int] = None,
        source: Optional[str] = None,
    ) -> VerificationResult:
        """
        実在人物エピソードを検証

        Args:
            person_name: 人物名
            episode_text: エピソードテキスト
            age: エピソード時の年齢
            birth_year: 生年（オプション）
            death_year: 没年（オプション）
            source: エピソードソース（オプション）

        Returns:
            VerificationResult: 検証結果
        """
        # デフォルト値
        filler_score = 0
        concrete_score = 0
        fabrication_patterns_found: list[str] = []
        wikipedia_verified = False

        # 1. 未来エピソードチェック
        if birth_year:
            is_future, future_detail = self._check_future_episode(birth_year, age)
            if is_future:
                filler_score, concrete_score = self._count_patterns(episode_text)
                return VerificationResult(
                    passed=False,
                    violation_type=ViolationType.FUTURE_EPISODE,
                    violation_detail=future_detail,
                    filler_score=filler_score,
                    concrete_score=concrete_score,
                    fabrication_patterns=fabrication_patterns_found,
                    suggestion=f"{person_name}の現在年齢({self.CURRENT_YEAR - birth_year}歳)以下のエピソードに修正してください",
                    wikipedia_verified=wikipedia_verified,
                )

        # 2. 死亡後エピソードチェック
        if birth_year and death_year:
            is_post_death, post_death_detail = self._check_post_death(birth_year, age, death_year)
            if is_post_death:
                filler_score, concrete_score = self._count_patterns(episode_text)
                return VerificationResult(
                    passed=False,
                    violation_type=ViolationType.POST_DEATH,
                    violation_detail=post_death_detail,
                    filler_score=filler_score,
                    concrete_score=concrete_score,
                    fabrication_patterns=fabrication_patterns_found,
                    suggestion=f"{person_name}は{death_year}年に死亡。{death_year - birth_year}歳以下のエピソードに修正してください",
                    wikipedia_verified=wikipedia_verified,
                )

        # 3. 埋草チェック
        is_filler, filler_score, concrete_score = self._check_filler(episode_text)
        if is_filler:
            return VerificationResult(
                passed=False,
                violation_type=ViolationType.FILLER,
                violation_detail=f"埋草スコア: {filler_score}, 具体性スコア: {concrete_score}",
                filler_score=filler_score,
                concrete_score=concrete_score,
                fabrication_patterns=fabrication_patterns_found,
                suggestion="具体的な事実・出来事を含むエピソードに書き換えてください",
                wikipedia_verified=wikipedia_verified,
            )

        # 4. 捏造チェック
        is_fabricated, fabrication_patterns_found = self._check_fabrication(episode_text, source)
        if is_fabricated:
            return VerificationResult(
                passed=False,
                violation_type=ViolationType.FABRICATION,
                violation_detail=f"捏造パターン検出: {', '.join(fabrication_patterns_found)}",
                filler_score=filler_score,
                concrete_score=concrete_score,
                fabrication_patterns=fabrication_patterns_found,
                suggestion="検証可能な事実に基づくエピソードに修正してください",
                wikipedia_verified=wikipedia_verified,
            )

        # 5. Wikipedia検証（クライアントが設定されている場合）
        if self.wikipedia_client:
            wikipedia_verified = self._verify_with_wikipedia(person_name, episode_text)
            if not wikipedia_verified:
                return VerificationResult(
                    passed=False,
                    violation_type=ViolationType.NO_WIKIPEDIA,
                    violation_detail="Wikipediaで検証できませんでした",
                    filler_score=filler_score,
                    concrete_score=concrete_score,
                    fabrication_patterns=fabrication_patterns_found,
                    suggestion="Wikipedia等の信頼できるソースで確認可能な内容に修正してください",
                    wikipedia_verified=False,
                )

        # 全チェック通過
        return VerificationResult(
            passed=True,
            violation_type=None,
            violation_detail="",
            filler_score=filler_score,
            concrete_score=concrete_score,
            fabrication_patterns=fabrication_patterns_found,
            suggestion=None,
            wikipedia_verified=wikipedia_verified,
        )

    def _check_future_episode(self, birth_year: int, age: float) -> tuple[bool, str]:
        """
        未来のエピソードかどうか判定

        Args:
            birth_year: 生年
            age: エピソード時の年齢

        Returns:
            tuple[bool, str]: (違反有無, 詳細メッセージ)
        """
        episode_year = birth_year + int(age)
        threshold_year = self.CURRENT_YEAR + self.FUTURE_THRESHOLD

        if episode_year > threshold_year:
            current_age = self.CURRENT_YEAR - birth_year
            years_ahead = episode_year - self.CURRENT_YEAR
            return (
                True,
                f"未来のエピソード: {episode_year}年（現在より{years_ahead}年先）、現在{current_age}歳",
            )

        return False, ""

    def _check_post_death(self, birth_year: int, age: float, death_year: int) -> tuple[bool, str]:
        """
        死亡後のエピソードかどうか判定

        Args:
            birth_year: 生年
            age: エピソード時の年齢
            death_year: 没年

        Returns:
            tuple[bool, str]: (違反有無, 詳細メッセージ)
        """
        episode_year = birth_year + int(age)

        if episode_year > death_year:
            death_age = death_year - birth_year
            years_after = episode_year - death_year
            return (
                True,
                f"死亡後のエピソード: {death_year}年に{death_age}歳で死亡、エピソードは{episode_year}年（死後{years_after}年）",
            )

        return False, ""

    def _check_filler(self, text: str) -> tuple[bool, int, int]:
        """
        埋草エピソードかどうか判定

        Args:
            text: エピソードテキスト

        Returns:
            tuple[bool, int, int]: (違反有無, 埋草スコア, 具体性スコア)
        """
        filler_score, concrete_score = self._count_patterns(text)

        # 埋草スコア >= 3 AND 具体性スコア < 2
        is_filler = filler_score >= 3 and concrete_score < 2
        return is_filler, filler_score, concrete_score

    def _count_patterns(self, text: str) -> tuple[int, int]:
        """
        パターンをカウント

        Args:
            text: エピソードテキスト

        Returns:
            tuple[int, int]: (埋草スコア, 具体性スコア)
        """
        filler_score = sum(1 for p in self.FILLER_PATTERNS if p in text)
        concrete_score = sum(1 for p in self.CONCRETE_PATTERNS if p in text)
        return filler_score, concrete_score

    def _check_fabrication(self, text: str, source: Optional[str]) -> tuple[bool, list[str]]:
        """
        捏造エピソードかどうか判定

        Args:
            text: エピソードテキスト
            source: エピソードソース

        Returns:
            tuple[bool, list[str]]: (違反有無, 検出された捏造パターンのリスト)
        """
        # SURPRISE_IMPROVED源の場合のみ厳格チェック
        if source and "SURPRISE_IMPROVED" not in source:
            return False, []

        patterns_found = [p for p in self.FABRICATION_PATTERNS if p in text]

        if patterns_found:
            return True, patterns_found

        return False, []

    def _verify_with_wikipedia(self, person_name: str, episode_text: str) -> bool:
        """
        Wikipediaで検証

        Args:
            person_name: 人物名
            episode_text: エピソードテキスト

        Returns:
            bool: Wikipedia検証成功かどうか
        """
        if not self.wikipedia_client:
            return False

        try:
            # Wikipedia APIを呼び出して検証
            # 実装はwikipedia_clientのインターフェースに依存
            return self.wikipedia_client.verify(person_name, episode_text)
        except Exception:
            return False

    def batch_verify(self, episodes: list[dict]) -> list[tuple[dict, VerificationResult]]:
        """
        複数エピソードを一括検証

        Args:
            episodes: エピソード辞書のリスト
                必須キー: person_name, episode_text, age
                オプションキー: birth_year, death_year, source

        Returns:
            list[tuple[dict, VerificationResult]]: (エピソード, 検証結果)のタプルリスト
        """
        results = []

        for episode in episodes:
            person_name = episode.get("person_name", "")
            episode_text = episode.get("episode_text", "")
            age = episode.get("age", 0)

            # 年齢を数値に変換
            try:
                age = float(age)
            except (ValueError, TypeError):
                age = 0

            birth_year = episode.get("birth_year")
            death_year = episode.get("death_year")
            source = episode.get("source")

            # birth_yearを数値に変換
            if birth_year is not None:
                try:
                    birth_year = int(birth_year)
                except (ValueError, TypeError):
                    birth_year = None

            # death_yearを数値に変換
            if death_year is not None:
                try:
                    death_year = int(death_year)
                except (ValueError, TypeError):
                    death_year = None

            result = self.verify(
                person_name=person_name,
                episode_text=episode_text,
                age=age,
                birth_year=birth_year,
                death_year=death_year,
                source=source,
            )

            results.append((episode, result))

        return results

    def get_violation_summary(self, results: list[tuple[dict, VerificationResult]]) -> dict:
        """
        検証結果のサマリーを取得

        Args:
            results: batch_verifyの結果

        Returns:
            dict: 違反タイプ別の集計
        """
        by_violation_type: dict[str, int] = {
            ViolationType.FABRICATION.value: 0,
            ViolationType.FILLER.value: 0,
            ViolationType.FUTURE_EPISODE.value: 0,
            ViolationType.POST_DEATH.value: 0,
            ViolationType.TIMELINE_ERROR.value: 0,
            ViolationType.NO_WIKIPEDIA.value: 0,
        }
        passed = 0
        failed = 0

        for _, result in results:
            if result.passed:
                passed += 1
            else:
                failed += 1
                if result.violation_type:
                    by_violation_type[result.violation_type.value] += 1

        summary: dict[str, int | dict[str, int]] = {
            "total": len(results),
            "passed": passed,
            "failed": failed,
            "by_violation_type": by_violation_type,
        }

        return summary


def main():
    """CLIエントリーポイント"""
    import argparse
    import csv
    import json
    from pathlib import Path

    parser = argparse.ArgumentParser(description="実在人物エピソード検証ツール")
    parser.add_argument("--csv", type=str, help="検証対象のCSVファイルパス")
    parser.add_argument("--limit", type=int, default=100, help="検証するエピソード数の上限")
    parser.add_argument("--output", type=str, help="結果出力先JSONファイルパス")
    parser.add_argument("--failed-only", action="store_true", help="失敗したエピソードのみ表示")
    args = parser.parse_args()

    # デフォルトCSVパス
    project_root = Path(__file__).parent.parent.parent
    csv_path = Path(args.csv) if args.csv else project_root / "preserved/data/MASTER_EPISODES_CURRENT.csv"

    if not csv_path.exists():
        print(f"エラー: ファイルが見つかりません: {csv_path}")
        return

    # CSVを読み込み
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        episodes = []
        for i, row in enumerate(reader):
            if i >= args.limit:
                break
            # REALタイプのみ
            if row.get("person_type") == "REAL":
                episodes.append(row)

    print(f"検証対象: {len(episodes)}件の実在人物エピソード")

    # 検証実行
    verifier = RealPersonVerifier()
    results = verifier.batch_verify(episodes)

    # サマリー表示
    summary = verifier.get_violation_summary(results)
    print("\n=== 検証結果サマリー ===")
    print(f"総数: {summary['total']}")
    print(f"合格: {summary['passed']}")
    print(f"不合格: {summary['failed']}")
    print("\n【違反タイプ別】")
    for vtype, count in summary["by_violation_type"].items():
        if count > 0:
            print(f"  {vtype}: {count}件")

    # 詳細表示
    failed_results = [(ep, res) for ep, res in results if not res.passed]
    if failed_results:
        print("\n=== 不合格エピソード（上位10件） ===")
        for episode, result in failed_results[:10]:
            print(
                f"\n[{episode.get('episode_id', 'N/A')}] {episode.get('person_name', 'N/A')} ({episode.get('age', 'N/A')}歳)"
            )
            print(f"  違反タイプ: {result.violation_type.value if result.violation_type else 'N/A'}")
            print(f"  詳細: {result.violation_detail}")
            print(f"  埋草/具体性スコア: {result.filler_score}/{result.concrete_score}")
            if result.suggestion:
                print(f"  修正提案: {result.suggestion}")

    # JSON出力
    if args.output:
        output_path = Path(args.output)
        output_data = {
            "summary": summary,
            "results": [
                {
                    "episode_id": ep.get("episode_id", ""),
                    "person_name": ep.get("person_name", ""),
                    "age": ep.get("age", ""),
                    "verification": res.to_dict(),
                }
                for ep, res in results
                if not args.failed_only or not res.passed
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=2)
        print(f"\n結果を保存: {output_path}")


if __name__ == "__main__":
    main()
