#!/usr/bin/env python3
"""
同一人物×同一年齢 重複解決スクリプト

EPUP再発防止: 同一person_id×ageのエピソードを1件に絞る。

勝者選定ルール（優先順位）:
1. ファクトチェック合格（fact_check_result="確認済み"）を優先
2. 両方合格 or 両方未実施 → super_total_score が高い方
3. 同点 → 事実密度 > 生成品質スコア > ストーリー品質
4. それでも同点 → generation_timestamp が新しい方

Usage:
    # ドライラン（削除対象を確認）
    python scripts/validation/same_age_duplicate_resolver.py

    # 実行（削除）
    python scripts/validation/same_age_duplicate_resolver.py --execute

    # 検証（重複0件確認）
    python scripts/validation/same_age_duplicate_resolver.py --verify

Exit codes:
    0: 成功
    1: エラー
    2: 重複が残っている（--verify時）
"""

import argparse
import csv
import json
import sys
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data_guardian import DataGuardian

MASTER_CSV = PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"
REPORT_DIR = PROJECT_ROOT / "src/reports/logs"


@dataclass
class DuplicatePair:
    """重複ペア"""

    person_id: str
    person_name: str
    age: float
    winner_id: str
    loser_id: str
    winner_reason: str
    winner_score: float
    loser_score: float
    text_similarity: float


@dataclass
class ResolutionResult:
    """解決結果"""

    resolved_at: str
    dry_run: bool
    total_duplicate_groups: int
    total_losers: int
    pairs: list[DuplicatePair]


def normalize_name(name: str) -> str:
    """人物名を正規化（比較用）"""
    if not name:
        return ""
    # NFKC正規化
    name = unicodedata.normalize("NFKC", name)
    # 全角スペースを半角に
    name = name.replace("\u3000", " ")
    # 前後の空白を除去
    name = name.strip()
    return name


def text_similarity(text1: str, text2: str) -> float:
    """テキスト類似度を計算（0-1）"""
    if not text1 or not text2:
        return 0.0
    return SequenceMatcher(None, text1, text2).ratio()


class SameAgeDuplicateResolver:
    """同一人物×同一年齢の重複を解決するクラス"""

    def __init__(self, master_csv: Path = MASTER_CSV):
        self.master_csv = master_csv
        self._guardian = DataGuardian()
        self._rows: list[dict] = []
        self._fieldnames: list[str] = []

    def _load_data(self) -> None:
        """CSVデータを読み込み"""
        with open(self.master_csv, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            self._fieldnames = reader.fieldnames or []
            self._rows = list(reader)

    def _get_person_key(self, row: dict) -> tuple[str, float] | None:
        """
        人物キーを取得（person_id優先、なければperson_name）

        Returns:
            (person_id or normalized_name, age) のタプル、または無効ならNone
        """
        person_id = row.get("person_id", "").strip()
        person_name = row.get("person_name", "").strip()
        age_str = row.get("age", "").strip()

        if not age_str:
            return None

        try:
            age = float(age_str)
        except (ValueError, TypeError):
            return None

        # person_idが有効ならそれを使う、なければ正規化したperson_name
        if person_id:
            return (person_id, age)
        elif person_name:
            return (f"name:{normalize_name(person_name)}", age)
        else:
            return None

    def _determine_winner(self, ep1: dict, ep2: dict) -> tuple[str, str, str]:
        """
        勝者を決定

        Returns:
            (winner_id, loser_id, reason) のタプル
        """
        # ルール1: ファクトチェック合格を優先
        fc1 = ep1.get("fact_check_result", "").strip() == "確認済み"
        fc2 = ep2.get("fact_check_result", "").strip() == "確認済み"

        if fc1 and not fc2:
            return ep1["episode_id"], ep2["episode_id"], "fact_check(合格vs未実施)"
        if fc2 and not fc1:
            return ep2["episode_id"], ep1["episode_id"], "fact_check(合格vs未実施)"

        # ルール2: 超総合スコア
        st1 = float(ep1.get("super_total_score") or 0)
        st2 = float(ep2.get("super_total_score") or 0)

        if st1 > st2:
            return ep1["episode_id"], ep2["episode_id"], f"super_total({st1:.0f}>{st2:.0f})"
        if st2 > st1:
            return ep2["episode_id"], ep1["episode_id"], f"super_total({st2:.0f}>{st1:.0f})"

        # ルール3: タイブレーク（事実密度→生成品質→ストーリー品質）
        tiebreak_cols = ["事実密度", "生成品質スコア", "ストーリー品質"]
        for col in tiebreak_cols:
            v1 = float(ep1.get(col) or 0)
            v2 = float(ep2.get(col) or 0)
            if v1 > v2:
                return ep1["episode_id"], ep2["episode_id"], f"{col}({v1}>{v2})"
            if v2 > v1:
                return ep2["episode_id"], ep1["episode_id"], f"{col}({v2}>{v1})"

        # ルール4: タイムスタンプ（新しい方を優先）
        ts1 = ep1.get("generation_timestamp", "") or ""
        ts2 = ep2.get("generation_timestamp", "") or ""

        if ts1 > ts2:
            return ep1["episode_id"], ep2["episode_id"], f"timestamp({ts1}>{ts2})"
        if ts2 > ts1:
            return ep2["episode_id"], ep1["episode_id"], f"timestamp({ts2}>{ts1})"

        # 全て同じ場合は最初のエピソードを残す
        return ep1["episode_id"], ep2["episode_id"], "tiebreak(先頭を優先)"

    def scan(self) -> list[DuplicatePair]:
        """
        同一person_id×ageの重複ペアを検出

        Returns:
            DuplicatePairのリスト
        """
        self._load_data()

        # 人物・年齢ごとにグループ化
        groups: dict[tuple, list[dict]] = defaultdict(list)

        for row in self._rows:
            key = self._get_person_key(row)
            if key:
                groups[key].append(row)

        # 重複を検出
        pairs: list[DuplicatePair] = []

        for (person_key, age), episodes in groups.items():
            if len(episodes) < 2:
                continue

            # 3件以上ある場合はトーナメント方式で勝者を決定
            # まず全てのエピソードをスコア順にソート
            sorted_eps = sorted(
                episodes,
                key=lambda x: (
                    1 if x.get("fact_check_result", "").strip() == "確認済み" else 0,
                    float(x.get("super_total_score") or 0),
                    float(x.get("事実密度") or 0),
                    float(x.get("生成品質スコア") or 0),
                    float(x.get("ストーリー品質") or 0),
                    x.get("generation_timestamp", "") or "",
                ),
                reverse=True,
            )

            # 最初の1件が勝者、残りは敗者
            winner = sorted_eps[0]
            losers = sorted_eps[1:]

            for loser in losers:
                winner_id, loser_id, reason = self._determine_winner(winner, loser)

                # person_idから表示用のperson_nameを取得
                person_name = winner.get("person_name", "")

                # テキスト類似度を計算
                sim = text_similarity(
                    winner.get("episode_text", ""),
                    loser.get("episode_text", ""),
                )

                pairs.append(
                    DuplicatePair(
                        person_id=person_key if not person_key.startswith("name:") else "",
                        person_name=person_name,
                        age=age,
                        winner_id=winner_id,
                        loser_id=loser_id,
                        winner_reason=reason,
                        winner_score=float(winner.get("super_total_score") or 0),
                        loser_score=float(loser.get("super_total_score") or 0),
                        text_similarity=sim,
                    )
                )

        return pairs

    def resolve(self, dry_run: bool = True) -> ResolutionResult:
        """
        重複を解決（敗者を削除）

        Args:
            dry_run: Trueの場合は削除せず確認のみ

        Returns:
            ResolutionResult
        """
        pairs = self.scan()
        loser_ids = [p.loser_id for p in pairs]

        # 重複グループ数をカウント
        groups = set((p.person_id or p.person_name, p.age) for p in pairs)

        result = ResolutionResult(
            resolved_at=datetime.now().isoformat(),
            dry_run=dry_run,
            total_duplicate_groups=len(groups),
            total_losers=len(loser_ids),
            pairs=pairs,
        )

        if dry_run:
            print(f"[DRY RUN] {len(loser_ids)}件の削除予定")
        else:
            if loser_ids:
                delete_result = self._guardian.safe_delete_episodes(
                    episode_ids=loser_ids,
                    reason=f"同一人物×同一年齢重複解決: {len(loser_ids)}件",
                )
                print(f"削除完了: {delete_result['deleted_count']}件")
            else:
                print("削除対象なし")

        return result

    def verify(self) -> tuple[bool, int]:
        """
        重複が0件であることを検証

        Returns:
            (成功フラグ, 残っている重複数)
        """
        pairs = self.scan()
        return len(pairs) == 0, len(pairs)


def generate_report(result: ResolutionResult) -> str:
    """レポートを生成"""
    lines = [
        "=" * 60,
        "同一人物×同一年齢 重複解決レポート",
        "=" * 60,
        f"実行日時: {result.resolved_at}",
        f"モード: {'ドライラン' if result.dry_run else '実行'}",
        f"重複グループ数: {result.total_duplicate_groups}",
        f"削除{'予定' if result.dry_run else '済み'}: {result.total_losers}件",
        "",
        "-" * 60,
        "詳細:",
        "-" * 60,
    ]

    for i, pair in enumerate(result.pairs, 1):
        lines.extend(
            [
                f"[{i}] {pair.person_name} ({pair.person_id}) 年齢{pair.age}",
                f"    勝者: {pair.winner_id} (score: {pair.winner_score:.0f})",
                f"    敗者: {pair.loser_id} (score: {pair.loser_score:.0f})",
                f"    選定理由: {pair.winner_reason}",
                f"    テキスト類似度: {pair.text_similarity:.1%}",
                "",
            ]
        )

    return "\n".join(lines)


def save_report(result: ResolutionResult, report_dir: Path = REPORT_DIR) -> Path:
    """レポートをJSONとして保存"""
    report_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"same_age_duplicate_resolved_{timestamp}.json"

    # dataclassをdict化
    data = asdict(result)

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return report_path


def main():
    parser = argparse.ArgumentParser(description="同一人物×同一年齢 重複解決")
    parser.add_argument("--execute", action="store_true", help="実際に削除を実行")
    parser.add_argument("--verify", action="store_true", help="重複が0件であることを検証")
    parser.add_argument("--report", type=str, help="レポート出力先（デフォルト: 自動生成）")
    args = parser.parse_args()

    resolver = SameAgeDuplicateResolver()

    if args.verify:
        print("=" * 60)
        print("重複検証モード")
        print("=" * 60)
        success, count = resolver.verify()
        if success:
            print("✅ 重複は0件です")
            return 0
        else:
            print(f"❌ {count}件の重複が残っています")
            return 2

    # 解決モード（dry-run or execute）
    dry_run = not args.execute
    result = resolver.resolve(dry_run=dry_run)

    # コンソール出力
    print(generate_report(result))

    # JSONレポート保存
    report_path = save_report(result)
    print(f"\nレポート保存: {report_path}")

    if dry_run and result.total_losers > 0:
        print("\n--execute オプションで実際に削除を実行できます")

    return 0


if __name__ == "__main__":
    sys.exit(main())
