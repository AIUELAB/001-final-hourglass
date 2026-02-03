"""
Person Discoverer

Wikidataから新規有名人を発見・マスターCSVに追加する機能。
"""

import csv
import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class PersonInfo:
    """Wikidataから取得した人物情報"""

    name: str
    wikidata_id: Optional[str]
    sitelinks: int
    description: str
    category: str
    birth_year: Optional[int] = None
    death_year: Optional[int] = None


@dataclass
class AddPersonResult:
    """人物追加結果"""

    success: bool
    person_id: str
    person_name: str
    message: str
    wikidata_info: Optional[dict] = None


class PersonDiscoverer:
    """Wikidataから新規有名人を発見・追加"""

    DEFAULT_CSV = Path("preserved/data/MASTER_EPISODES_CURRENT.csv")

    def __init__(self, master_csv: Optional[Path] = None):
        self.master_csv = master_csv or self.DEFAULT_CSV
        self._existing_names: set[str] = set()
        self._existing_ids: set[str] = set()
        self._load_existing_persons()

    def _load_existing_persons(self) -> None:
        """既存人物リストを読み込み"""
        if not self.master_csv.exists():
            logger.warning(f"Master CSV not found: {self.master_csv}")
            return

        with open(self.master_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                name = row.get("person_name", "")
                pid = row.get("person_id", "")
                if name:
                    self._existing_names.add(name)
                if pid:
                    self._existing_ids.add(pid)

        logger.info(f"Loaded {len(self._existing_names)} existing persons")

    def get_existing_names(self) -> set[str]:
        """既存人物名のセットを取得"""
        return self._existing_names.copy()

    def _generate_person_id(self, name: str) -> str:
        """person_nameからperson_idを生成"""
        hash_obj = hashlib.md5(name.encode("utf-8"), usedforsecurity=False)
        return "P" + hash_obj.hexdigest()[:7].upper()

    def search_person(self, name: str) -> Optional[dict]:
        """
        人物名からWikidata情報を取得

        Args:
            name: 人物名

        Returns:
            Wikidata情報（見つからない場合はNone）
        """
        try:
            from scripts.fame_score_v3.wikidata import get_wikidata_info

            result = get_wikidata_info(name, include_inlinks=False)
            if result and result.get("wikidata_id"):
                logger.info(f"Found Wikidata: {name} -> {result['wikidata_id']}")
                return result
            else:
                logger.warning(f"Wikidata not found for: {name}")
                return None
        except Exception as e:
            logger.error(f"Wikidata search error for {name}: {e}")
            return None

    def check_duplicate(self, name: str) -> tuple[bool, str]:
        """
        重複チェック

        Args:
            name: 人物名

        Returns:
            (is_duplicate, message)
        """
        if name in self._existing_names:
            return True, f"Person already exists: {name}"

        person_id = self._generate_person_id(name)
        if person_id in self._existing_ids:
            return True, f"Person ID collision: {person_id}"

        return False, "OK"

    def add_person(
        self,
        name: str,
        category: str,
        dry_run: bool = True,
    ) -> AddPersonResult:
        """
        新規人物をマスターCSVに追加

        Args:
            name: 人物名
            category: カテゴリ（政治/ビジネス/科学/芸術/スポーツ等）
            dry_run: True=追加しない（確認のみ）

        Returns:
            AddPersonResult
        """
        # 重複チェック
        is_dup, dup_msg = self.check_duplicate(name)
        if is_dup:
            return AddPersonResult(
                success=False,
                person_id="",
                person_name=name,
                message=dup_msg,
            )

        # Wikidata検索
        wikidata_info = self.search_person(name)

        # person_id生成
        person_id = self._generate_person_id(name)

        if dry_run:
            return AddPersonResult(
                success=True,
                person_id=person_id,
                person_name=name,
                message=f"[DRY-RUN] Would add: {name} ({person_id})",
                wikidata_info=wikidata_info,
            )

        # CSVに追加
        try:
            self._append_to_csv(name, person_id, category, wikidata_info)
            self._existing_names.add(name)
            self._existing_ids.add(person_id)

            return AddPersonResult(
                success=True,
                person_id=person_id,
                person_name=name,
                message=f"Added: {name} ({person_id})",
                wikidata_info=wikidata_info,
            )
        except Exception as e:
            logger.error(f"Failed to add {name}: {e}")
            return AddPersonResult(
                success=False,
                person_id=person_id,
                person_name=name,
                message=f"Failed to add: {e}",
            )

    def _append_to_csv(
        self,
        name: str,
        person_id: str,
        category: str,
        wikidata_info: Optional[dict],
    ) -> None:
        """CSVに新規行を追加"""
        # 既存フィールド名を取得
        with open(self.master_csv, "r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fieldnames = reader.fieldnames
            if not fieldnames:
                raise ValueError("CSV has no fieldnames")

        # 新規行データを作成
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        episode_id = f"EP-{datetime.now().strftime('%y%m%d%H%M%S')}{hash(name) % 10000:04d}"

        new_row = {field: "" for field in fieldnames}
        new_row.update(
            {
                "episode_id": episode_id,
                "person_id": person_id,
                "person_name": name,
                "category": category,
                "person_type": "REAL",
                "episode_type": "placeholder",
                "source": "wikidata_discoverer",
                "generation_timestamp": timestamp,
                "episode_text": f"「{name}」のエピソードは後で生成されます。",
                "age": "30",  # プレースホルダー年齢
            }
        )

        # Wikidata情報があれば追加
        if wikidata_info:
            if "sitelinks" in wikidata_info and "sitelinks_count" in fieldnames:
                new_row["sitelinks_count"] = str(wikidata_info.get("sitelinks", 0))

        # 追記
        with open(self.master_csv, "a", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writerow(new_row)

        logger.info(f"Appended to CSV: {name} ({person_id})")


def add_person_from_wikidata(
    name: str,
    category: str,
    master_csv: Optional[Path] = None,
    dry_run: bool = True,
) -> AddPersonResult:
    """
    Wikidataから人物を追加するユーティリティ関数

    Args:
        name: 人物名
        category: カテゴリ
        master_csv: マスターCSVパス（省略時はデフォルト）
        dry_run: ドライラン

    Returns:
        AddPersonResult
    """
    discoverer = PersonDiscoverer(master_csv)
    return discoverer.add_person(name, category, dry_run)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 3:
        print("Usage: python person_discoverer.py <name> <category> [--execute]")
        sys.exit(1)

    name = sys.argv[1]
    category = sys.argv[2]
    dry_run = "--execute" not in sys.argv

    result = add_person_from_wikidata(name, category, dry_run=dry_run)
    print(f"Result: {result}")
