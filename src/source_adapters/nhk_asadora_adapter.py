"""
NHK Asadora Adapter - NHK朝ドラモデル人物からの候補取得

このアダプタは NHK朝ドラのモデルとなった実在人物の情報を
CSVファイルから取得します。

CSV形式:
    person_name,drama_title,role_description,birth_year,death_year,category,tier,source_url

Example:
    >>> adapter = NHKAsadoraAdapter()
    >>> candidates = adapter.fetch_candidates()
    >>> print(f"取得: {len(candidates)}件")
"""

from pathlib import Path
from typing import List, Optional

import pandas as pd

from src.csv_path_resolver import get_person_sources_dir
from src.source_adapters.base import PersonCandidate, SourceAdapter


class NHKAsadoraAdapter(SourceAdapter):
    """NHK朝ドラモデル人物からの候補取得"""

    def __init__(
        self,
        csv_path: Optional[str] = None,
    ):
        """
        Args:
            csv_path: CSVファイルのパス（省略時はデフォルトパス）
        """
        if csv_path:
            self.csv_path = Path(csv_path)
            if not self.csv_path.is_absolute():
                # 相対パスの場合、プロジェクトルートからの相対として解釈
                from src.csv_path_resolver import get_project_root

                self.csv_path = get_project_root() / csv_path
        else:
            # デフォルトパス
            self.csv_path = get_person_sources_dir() / "nhk_asadora_models.csv"

        if not self.csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

    def fetch_candidates(self, limit: Optional[int] = None) -> List[PersonCandidate]:
        """
        CSVファイルから候補人物を取得

        Args:
            limit: 取得する候補数の上限（Noneの場合は全件）

        Returns:
            PersonCandidateのリスト

        Raises:
            FileNotFoundError: CSVファイルが存在しない
            ValueError: CSV形式が不正
        """
        try:
            df = pd.read_csv(self.csv_path, encoding="utf-8-sig")
        except Exception as e:
            raise ValueError(f"Failed to read CSV: {e}")

        # 必須カラムの確認
        required_columns = ["person_name"]
        missing_columns = set(required_columns) - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        candidates = []
        for idx, row in df.iterrows():
            # limitチェック
            if limit and idx >= limit:
                break

            # person_nameが空の行はスキップ
            if pd.isna(row.get("person_name")) or not str(row.get("person_name")).strip():
                continue

            try:
                # drama_titleとrole_descriptionから説明を生成
                description_parts = []
                if pd.notna(row.get("drama_title")):
                    description_parts.append(f"朝ドラ『{row['drama_title']}』モデル")
                if pd.notna(row.get("role_description")):
                    description_parts.append(str(row["role_description"]).strip())
                description = "・".join(description_parts) if description_parts else None

                candidate = PersonCandidate(
                    person_name=str(row["person_name"]).strip(),
                    category=(str(row["category"]).strip() if pd.notna(row.get("category")) else None),
                    sub_category=None,  # NHK朝ドラソースにはsub_categoryなし
                    person_type="REAL",  # 朝ドラモデルは必ず実在人物
                    description=description,
                    birth_year=(int(row["birth_year"]) if pd.notna(row.get("birth_year")) else None),
                    death_year=(int(row["death_year"]) if pd.notna(row.get("death_year")) else None),
                    tier=(
                        str(row["tier"]).strip()
                        if pd.notna(row.get("tier"))
                        else "S"  # 朝ドラモデルはデフォルトSランク
                    ),
                    source_name=self.get_source_name(),
                    source_url=(str(row["source_url"]).strip() if pd.notna(row.get("source_url")) else None),
                    status="pending",
                )

                # 基本検証
                if self.validate_candidate(candidate):
                    candidates.append(candidate)
                else:
                    # 検証エラーがある場合もリストに含める（レポート生成のため）
                    candidate.skip_reason = "validation_error"
                    candidates.append(candidate)

            except Exception as e:
                # 個別行のエラーはスキップ（ログ出力）
                print(f"⚠️  Warning: Failed to parse row {idx}: {row['person_name']} - {e}")
                continue

        return candidates

    def get_source_name(self) -> str:
        """
        ソース名を返す

        Returns:
            "nhk_asadora"
        """
        return "nhk_asadora"


if __name__ == "__main__":
    # 動作確認用
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).parent.parent.parent))

    try:
        adapter = NHKAsadoraAdapter()
        print(f"ソース名: {adapter.get_source_name()}")
        print(f"CSVパス: {adapter.csv_path}")

        candidates = adapter.fetch_candidates(limit=5)
        print(f"\n取得件数: {len(candidates)}")

        for candidate in candidates:
            print(f"- {candidate.person_name} ({candidate.category})")
            if candidate.description:
                print(f"  {candidate.description}")
            if candidate.validation_errors:
                print(f"  エラー: {candidate.validation_errors}")

    except FileNotFoundError as e:
        print(f"⚠️  {e}")
        print("NHK朝ドラモデルCSVを作成してください:")
        print("  config/person_sources/nhk_asadora_models.csv")
