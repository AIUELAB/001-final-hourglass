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
        """グループ名混入率を計算"""
        group_as_person = 0

        for name in self.df["person_name"].dropna().unique():
            if name in GROUP_ENTITIES:
                group_as_person += 1

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

    def _load_deleted_ids(self) -> set:
        """
        Tombstoneファイルから削除済みIDを読み込む

        Returns:
            削除済みperson_idのセット
        """
        if not TOMBSTONE_PATH.exists():
            return set()

        try:
            with open(TOMBSTONE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return {item["person_id"] for item in data.get("deleted_ids", [])}
        except (json.JSONDecodeError, KeyError):
            return set()

    def _calc_deleted_id_contamination_rate(self) -> KPIResult:
        """
        削除済みID混入率を計算

        Tombstoneに登録された削除済みIDがCSVに存在するかチェック
        """
        deleted_ids = self._load_deleted_ids()

        if not deleted_ids:
            return KPIResult(
                name="削除済みID混入率",
                value=0.0,
                target=0.0,
                status="OK",
                details={"contaminated": 0, "deleted_ids_count": 0, "note": "Tombstone未設定"},
            )

        contaminated = 0
        contaminated_ids: list[str] = []

        for _, row in self.df.iterrows():
            if pd.notna(row["person_id"]) and str(row["person_id"]) in deleted_ids:
                contaminated += 1
                if len(contaminated_ids) < 5:  # 最大5件まで記録
                    contaminated_ids.append(str(row["person_id"]))

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
                "contaminated_ids": contaminated_ids,
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
