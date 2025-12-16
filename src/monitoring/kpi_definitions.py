#!/usr/bin/env python3
"""
EPUP KPI Definitions - 品質指標定義

KPI一覧:
1. グループ名混入率 (target: 0%)
2. フォーマット準拠率 (target: 100%)
3. メタ表現クリーン率 (target: 100%)
4. 表記ゆれ率 (target: 0%)
5. 重複ID率 (target: 0%)
6. nan ID率 (target: 0%)
7. 削除済みID混入率 (target: 0%) - 再発防止用
8. 組織名・肩書き混入率 (target: 0%) - 人物名汚染防止用
9. 英字別名検出率 (target: 0%) - 英字別名誤登録防止用
10. 後置詞型パターン検出率 (target: 0%) - 役職語・関係語混入防止用（ERR-006）
"""

import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from collections import defaultdict

import pandas as pd

# Tombstoneファイルパス
TOMBSTONE_PATH = Path(__file__).parent.parent.parent / "preserved" / "data" / "DELETED_IDS_TOMBSTONE.json"

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.group_master import GROUP_ENTITIES


@dataclass
class KPIResult:
    """KPI計算結果"""

    name: str
    value: float
    target: float
    status: str  # "OK", "WARNING", "CRITICAL"
    details: Optional[dict] = None


@dataclass
class HealthReport:
    """ヘルスチェックレポート"""

    timestamp: str
    total_records: int
    kpis: list[KPIResult]
    overall_status: str
    overall_score: float


class EPUPKPICalculator:
    """EPUP KPI計算クラス"""

    # リード文パターン
    LEAD_PATTERN = re.compile(r"^あなたと同じ(\d+)歳のとき、")

    # メタ表現パターン
    META_PATTERNS = [
        "架空の",
        "フィクション",
        "設定上",
        "作品内では",
        "公式な描写は存在しません",
        "実在しない",
        "申し訳ございませんが",
        "キャラクターです",
        "存在しません",
        "描かれていません",
        "物語の中で",
        "作品世界",
        "著作権の関係",
    ]

    def __init__(self, csv_path: str):
        """
        初期化

        Args:
            csv_path: MASTER CSVパス
        """
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)

    def calculate_all(self) -> HealthReport:
        """
        全KPIを計算

        Returns:
            HealthReport
        """
        from datetime import datetime

        kpis = [
            self._calc_group_name_rate(),
            self._calc_format_compliance_rate(),
            self._calc_meta_expression_rate(),
            self._calc_variant_rate(),
            self._calc_duplicate_id_rate(),
            self._calc_nan_id_rate(),
            self._calc_deleted_id_contamination_rate(),
            self._calc_org_title_contamination_rate(),
            self._calc_english_alias_rate(),  # KPI 9: 英字別名検出率
            self._calc_suffix_pattern_rate(),  # KPI 10: 後置詞型パターン検出率（ERR-006）
        ]

        # 総合ステータス判定
        critical_count = len([k for k in kpis if k.status == "CRITICAL"])
        warning_count = len([k for k in kpis if k.status == "WARNING"])

        if critical_count > 0:
            overall_status = "CRITICAL"
        elif warning_count > 0:
            overall_status = "WARNING"
        else:
            overall_status = "OK"

        # 総合スコア計算
        scores = []
        for kpi in kpis:
            if kpi.target == 0:
                # ターゲットが0%の場合、値が低いほど良い
                scores.append(1.0 - min(kpi.value, 1.0))
            else:
                # ターゲットが100%の場合、値が高いほど良い
                scores.append(min(kpi.value / kpi.target, 1.0))

        overall_score = sum(scores) / len(scores) if scores else 0.0

        return HealthReport(
            timestamp=datetime.now().isoformat(),
            total_records=len(self.df),
            kpis=kpis,
            overall_status=overall_status,
            overall_score=overall_score,
        )

    def _calc_group_name_rate(self) -> KPIResult:
        """
        グループ名混入率を計算

        person_typeがGROUP以外でperson_nameがGROUP_ENTITIESに含まれる人物名を検出
        """
        group_as_person = 0

        # person_type != 'GROUP' のレコードのみを対象
        non_group_df = self.df[self.df["person_type"] != "GROUP"]

        for name in non_group_df["person_name"].dropna().unique():
            if name in GROUP_ENTITIES:
                group_as_person += 1

        # 全体のユニーク人物名数（person_type不問）
        total = self.df["person_name"].dropna().nunique()
        rate = group_as_person / total if total > 0 else 0.0

        return KPIResult(
            name="グループ名混入率",
            value=rate,
            target=0.0,
            status=self._get_status(rate, 0.0, 0.001, 0.01),
            details={"group_as_person": group_as_person, "total_unique": total},
        )

    def _calc_format_compliance_rate(self) -> KPIResult:
        """フォーマット準拠率を計算"""
        compliant = 0
        total = 0

        for text in self.df["episode_text"].dropna():
            total += 1
            if self.LEAD_PATTERN.match(str(text)):
                compliant += 1

        rate = compliant / total if total > 0 else 0.0

        return KPIResult(
            name="フォーマット準拠率",
            value=rate,
            target=1.0,
            status=self._get_status(1 - rate, 0.0, 0.01, 0.05),
            details={"compliant": compliant, "total": total},
        )

    def _calc_meta_expression_rate(self) -> KPIResult:
        """メタ表現混入率を計算（FICTIONALのみ）"""
        fictional_df = self.df[self.df["person_type"].str.upper() == "FICTIONAL"]
        meta_count = 0
        total = 0

        for text in fictional_df["episode_text"].dropna():
            total += 1
            text_str = str(text)
            for pattern in self.META_PATTERNS:
                if pattern in text_str:
                    meta_count += 1
                    break

        rate = meta_count / total if total > 0 else 0.0

        return KPIResult(
            name="メタ表現混入率",
            value=rate,
            target=0.0,
            status=self._get_status(rate, 0.0, 0.005, 0.02),
            details={"meta_count": meta_count, "fictional_total": total},
        )

    def _calc_variant_rate(self) -> KPIResult:
        """表記ゆれ率を計算（同一IDで複数表記）"""
        id_to_names = defaultdict(set)

        for _, row in self.df.iterrows():
            if pd.notna(row["person_id"]):
                id_to_names[str(row["person_id"])].add(str(row["person_name"]))

        variant_ids = [k for k, v in id_to_names.items() if len(v) > 1]
        total_ids = len(id_to_names)
        rate = len(variant_ids) / total_ids if total_ids > 0 else 0.0

        return KPIResult(
            name="表記ゆれ率",
            value=rate,
            target=0.0,
            status=self._get_status(rate, 0.0, 0.001, 0.005),
            details={"variant_ids": len(variant_ids), "total_ids": total_ids},
        )

    def _calc_duplicate_id_rate(self) -> KPIResult:
        """重複ID率を計算（同一人物が複数ID）"""
        # 正規化名でグループ化
        name_to_ids = defaultdict(set)

        for _, row in self.df.iterrows():
            if pd.notna(row["person_name"]) and pd.notna(row["person_id"]):
                # 簡易正規化
                norm_name = str(row["person_name"]).lower().replace("・", "").replace(" ", "")
                name_to_ids[norm_name].add(str(row["person_id"]))

        duplicate_names = [k for k, v in name_to_ids.items() if len(v) > 1]
        total_names = len(name_to_ids)
        rate = len(duplicate_names) / total_names if total_names > 0 else 0.0

        return KPIResult(
            name="重複ID率",
            value=rate,
            target=0.0,
            status=self._get_status(rate, 0.0, 0.001, 0.005),
            details={"duplicate_names": len(duplicate_names), "total_names": total_names},
        )

    def _calc_nan_id_rate(self) -> KPIResult:
        """nan ID率を計算"""
        nan_count = self.df["person_id"].isna().sum()
        total = len(self.df)
        rate = nan_count / total if total > 0 else 0.0

        return KPIResult(
            name="nan ID率",
            value=rate,
            target=0.0,
            status=self._get_status(rate, 0.0, 0.0, 0.001),
            details={"nan_count": nan_count, "total": total},
        )

    def _load_deleted_ids(self) -> tuple[set, set]:
        """
        Tombstoneファイルから削除済みID・名前を読み込む

        Returns:
            (削除済みperson_idのセット, 削除済みperson_nameのセット)
        """
        if not TOMBSTONE_PATH.exists():
            return set(), set()

        try:
            with open(TOMBSTONE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            deleted_ids = {item["person_id"] for item in data.get("deleted_ids", [])}
            deleted_names = {item["person_name"] for item in data.get("deleted_ids", []) if "person_name" in item}
            return deleted_ids, deleted_names
        except (json.JSONDecodeError, KeyError):
            return set(), set()

    def _calc_deleted_id_contamination_rate(self) -> KPIResult:
        """
        削除済みID/名前混入率を計算

        Tombstoneに登録された削除済みID・名前がCSVに存在するかチェック
        ※ person_idだけでなくperson_nameでもチェック（新IDでの再投入を防止）
        """
        deleted_ids, deleted_names = self._load_deleted_ids()

        if not deleted_ids and not deleted_names:
            return KPIResult(
                name="削除済みID混入率",
                value=0.0,
                target=0.0,
                status="OK",
                details={
                    "contaminated": 0,
                    "deleted_ids_count": 0,
                    "deleted_names_count": 0,
                    "note": "Tombstone未設定",
                },
            )

        contaminated = 0
        contaminated_entries: list[str] = []

        for _, row in self.df.iterrows():
            person_id = str(row["person_id"]) if pd.notna(row["person_id"]) else ""
            person_name = str(row["person_name"]) if pd.notna(row["person_name"]) else ""

            # IDまたは名前で検出
            matched_by_id = person_id in deleted_ids
            matched_by_name = person_name in deleted_names

            if matched_by_id or matched_by_name:
                contaminated += 1
                if len(contaminated_entries) < 5:  # 最大5件まで記録
                    match_type = "ID" if matched_by_id else "名前"
                    contaminated_entries.append(f"{person_id}:{person_name}({match_type})")

        total = len(self.df)
        rate = contaminated / total if total > 0 else 0.0

        return KPIResult(
            name="削除済みID混入率",
            value=rate,
            target=0.0,
            status=self._get_status(rate, 0.0, 0.0, 0.001),  # 1件でもあればCRITICAL
            details={
                "contaminated": contaminated,
                "deleted_ids_count": len(deleted_ids),
                "deleted_names_count": len(deleted_names),
                "contaminated_entries": contaminated_entries,
            },
        )

    def _calc_org_title_contamination_rate(self) -> KPIResult:
        """
        組織名・肩書き混入率を計算（KPI 8）

        PersonNameNormalizerを使用して、person_nameフィールドに
        組織名・肩書き・説明文が混入している人物名を検出する。

        Returns:
            KPIResult
        """
        # PersonNameNormalizerを遅延インポート（循環インポート回避）
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from scripts.normalize_person_names import PersonNameNormalizer

        normalizer = PersonNameNormalizer(min_confidence=0.85)
        contaminated = 0
        contaminated_names: list[str] = []

        # ユニークな人物名ごとにチェック
        for person_name in self.df["person_name"].dropna().unique():
            result = normalizer.normalize(str(person_name))
            if result:
                # 正規化が必要 = 組織名・肩書き混入あり
                contaminated += 1
                if len(contaminated_names) < 10:  # 最大10件まで例を記録
                    contaminated_names.append(f"{person_name} → {result.normalized_name}")

        total = self.df["person_name"].dropna().nunique()
        rate = contaminated / total if total > 0 else 0.0

        return KPIResult(
            name="組織名・肩書き混入率",
            value=rate,
            target=0.0,
            status=self._get_status(rate, 0.0, 0.005, 0.01),  # 0.5%超でWARNING, 1%超でCRITICAL
            details={
                "contaminated_count": contaminated,
                "total_unique_names": total,
                "contaminated_examples": contaminated_names,
            },
        )

    def _calc_english_alias_rate(self) -> KPIResult:
        """
        英字別名検出率を計算（KPI 9）

        detect_english_names.pyのEnglishNameDetectorを使用して、
        review_required（要確認）の人物名数をKPI化する。

        芸名・表記名として正当な英字人物名（YOSHIKI, HIKAKIN等）は維持しつつ、
        誤った英字別名（"Mackenyu"等）を検出する。

        Returns:
            KPIResult
        """
        # EnglishNameDetectorを遅延インポート（循環インポート回避）
        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from scripts.detect_english_names import EnglishNameDetector

        # detectorを実行
        detector = EnglishNameDetector(self.csv_path)
        detector.detect_all()

        review_required_count = len(detector.review_required)
        total_unique_persons = self.df["person_name"].dropna().nunique()
        rate = review_required_count / total_unique_persons if total_unique_persons > 0 else 0.0

        # 要確認人物名の例を記録（最大10件）
        review_examples = [
            f"{item['person_name']} ({item.get('name_type', 'unknown')})" for item in detector.review_required[:10]
        ]

        return KPIResult(
            name="英字別名検出率",
            value=rate,
            target=0.0,
            status=self._get_status(rate, 0.0, 0.01, 0.03),  # 1%超でWARNING, 3%超でCRITICAL
            details={
                "review_required_count": review_required_count,
                "total_unique_persons": total_unique_persons,
                "review_examples": review_examples,
            },
        )

    def _calc_suffix_pattern_rate(self) -> KPIResult:
        """
        後置詞型パターン検出率を計算（KPI 10: ERR-006）

        PersonNameValidator._check_suffix_patterns()を使用して、
        関係語（夫人等）で個人名が不明確なケースを検出

        Returns:
            KPIResult
        """
        from pathlib import Path
        import sys

        sys.path.insert(0, str(Path(__file__).parent.parent.parent))
        from src.validators.person_name_validator import get_validator, IssueType, Severity

        validator = get_validator()
        error_count = 0
        error_examples: list[str] = []

        # ユニークな人物名をチェック
        unique_names = self.df["person_name"].dropna().unique()
        for person_name in unique_names:
            issues = validator.validate(str(person_name))
            # 後置詞型パターンのERRORのみカウント（関係語で個人名不明確）
            suffix_errors = [
                i for i in issues if i.issue_type == IssueType.ORG_TITLE_CONTAMINATION and i.severity == Severity.ERROR
            ]
            if suffix_errors:
                error_count += 1
                if len(error_examples) < 10:
                    error_examples.append(person_name)

        total = len(unique_names)
        rate = error_count / total if total > 0 else 0.0

        return KPIResult(
            name="後置詞型パターン検出率",
            value=rate,
            target=0.0,
            status=self._get_status(rate, 0.0, 0.005, 0.01),  # 0.5%超でWARNING, 1%超でCRITICAL
            details={
                "error_count": error_count,
                "total_unique_names": total,
                "error_examples": error_examples,
            },
        )

    def _get_status(self, value: float, ok_max: float, warn_max: float, crit_max: float) -> str:
        """
        ステータスを判定

        Args:
            value: 現在値
            ok_max: OK閾値
            warn_max: WARNING閾値
            crit_max: CRITICAL閾値

        Returns:
            ステータス文字列
        """
        if value <= ok_max:
            return "OK"
        elif value <= warn_max:
            return "WARNING"
        else:
            return "CRITICAL"


def main():
    """テスト実行"""
    import sys

    csv_path = sys.argv[1] if len(sys.argv) > 1 else "preserved/data/MASTER_EPISODES_CURRENT.csv"

    calculator = EPUPKPICalculator(csv_path)
    report = calculator.calculate_all()

    print("=" * 60)
    print("EPUP Health Report")
    print("=" * 60)
    print(f"Timestamp: {report.timestamp}")
    print(f"Total Records: {report.total_records:,}")
    print(f"Overall Status: {report.overall_status}")
    print(f"Overall Score: {report.overall_score:.1%}")
    print()

    print("KPI Results:")
    print("-" * 60)
    for kpi in report.kpis:
        status_icon = {"OK": "✅", "WARNING": "⚠️", "CRITICAL": "❌"}.get(kpi.status, "?")
        if kpi.target == 0:
            value_str = f"{kpi.value:.2%}"
        else:
            value_str = f"{kpi.value:.2%} / {kpi.target:.0%}"
        print(f"{status_icon} {kpi.name}: {value_str}")
        if kpi.details:
            for k, v in kpi.details.items():
                print(f"   {k}: {v}")


if __name__ == "__main__":
    main()
