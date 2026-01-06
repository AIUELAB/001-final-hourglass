#!/usr/bin/env python3
"""
同一人物×同一年齢 重複解決スクリプトのテスト

テストケース:
- 勝者選定ロジック（ファクトチェック、超総合スコア、タイブレーク）
- 重複検出
- dry-run / execute モード
"""

import csv
import tempfile
from pathlib import Path

import pytest

# テスト対象をインポート
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validation.same_age_duplicate_resolver import (
    DuplicatePair,
    SameAgeDuplicateResolver,
    normalize_name,
    text_similarity,
)


class TestNormalizeName:
    """人物名正規化のテスト"""

    def test_basic_normalize(self):
        assert normalize_name("田中 太郎") == "田中 太郎"

    def test_full_width_space(self):
        assert normalize_name("田中　太郎") == "田中 太郎"

    def test_nfkc(self):
        # 全角数字→半角
        assert normalize_name("テスト１２３") == "テスト123"

    def test_empty(self):
        assert normalize_name("") == ""
        assert normalize_name(None) == ""

    def test_strip(self):
        assert normalize_name("  田中  ") == "田中"


class TestTextSimilarity:
    """テキスト類似度計算のテスト"""

    def test_identical(self):
        assert text_similarity("hello", "hello") == 1.0

    def test_completely_different(self):
        sim = text_similarity("abc", "xyz")
        assert sim < 0.5

    def test_empty(self):
        assert text_similarity("", "hello") == 0.0
        assert text_similarity("hello", "") == 0.0


class TestDetermineWinner:
    """勝者選定ロジックのテスト"""

    @pytest.fixture
    def resolver(self, tmp_path):
        """空のCSVでResolverを初期化"""
        csv_path = tmp_path / "test.csv"
        csv_path.write_text("episode_id,person_id,person_name,age\n", encoding="utf-8")
        return SameAgeDuplicateResolver(master_csv=csv_path)

    def test_fact_check_wins(self, resolver):
        """ファクトチェック合格が勝つ"""
        ep1 = {
            "episode_id": "EP-001",
            "fact_check_result": "確認済み",
            "super_total_score": "100000",
            "事実密度": "5",
            "生成品質スコア": "5",
            "ストーリー品質": "5",
            "generation_timestamp": "20260101_000000",
        }
        ep2 = {
            "episode_id": "EP-002",
            "fact_check_result": "",
            "super_total_score": "200000",  # スコアは高いが未実施
            "事実密度": "8",
            "生成品質スコア": "8",
            "ストーリー品質": "8",
            "generation_timestamp": "20260102_000000",
        }

        winner_id, loser_id, reason = resolver._determine_winner(ep1, ep2)

        assert winner_id == "EP-001"
        assert loser_id == "EP-002"
        assert "fact_check" in reason

    def test_super_total_wins(self, resolver):
        """両方未実施なら超総合スコアが高い方が勝つ"""
        ep1 = {
            "episode_id": "EP-001",
            "fact_check_result": "",
            "super_total_score": "100000",
            "事実密度": "5",
            "生成品質スコア": "5",
            "ストーリー品質": "5",
            "generation_timestamp": "20260101_000000",
        }
        ep2 = {
            "episode_id": "EP-002",
            "fact_check_result": "",
            "super_total_score": "200000",
            "事実密度": "5",
            "生成品質スコア": "5",
            "ストーリー品質": "5",
            "generation_timestamp": "20260101_000000",
        }

        winner_id, loser_id, reason = resolver._determine_winner(ep1, ep2)

        assert winner_id == "EP-002"
        assert loser_id == "EP-001"
        assert "super_total" in reason

    def test_fact_density_tiebreak(self, resolver):
        """超総合が同点なら事実密度でタイブレーク"""
        ep1 = {
            "episode_id": "EP-001",
            "fact_check_result": "",
            "super_total_score": "100000",
            "事実密度": "8",
            "生成品質スコア": "5",
            "ストーリー品質": "5",
            "generation_timestamp": "20260101_000000",
        }
        ep2 = {
            "episode_id": "EP-002",
            "fact_check_result": "",
            "super_total_score": "100000",
            "事実密度": "5",
            "生成品質スコア": "5",
            "ストーリー品質": "5",
            "generation_timestamp": "20260101_000000",
        }

        winner_id, loser_id, reason = resolver._determine_winner(ep1, ep2)

        assert winner_id == "EP-001"
        assert loser_id == "EP-002"
        assert "事実密度" in reason

    def test_generation_quality_tiebreak(self, resolver):
        """事実密度も同点なら生成品質でタイブレーク"""
        ep1 = {
            "episode_id": "EP-001",
            "fact_check_result": "",
            "super_total_score": "100000",
            "事実密度": "5",
            "生成品質スコア": "8",
            "ストーリー品質": "5",
            "generation_timestamp": "20260101_000000",
        }
        ep2 = {
            "episode_id": "EP-002",
            "fact_check_result": "",
            "super_total_score": "100000",
            "事実密度": "5",
            "生成品質スコア": "5",
            "ストーリー品質": "5",
            "generation_timestamp": "20260101_000000",
        }

        winner_id, loser_id, reason = resolver._determine_winner(ep1, ep2)

        assert winner_id == "EP-001"
        assert loser_id == "EP-002"
        assert "生成品質" in reason

    def test_story_quality_tiebreak(self, resolver):
        """生成品質も同点ならストーリー品質でタイブレーク"""
        ep1 = {
            "episode_id": "EP-001",
            "fact_check_result": "",
            "super_total_score": "100000",
            "事実密度": "5",
            "生成品質スコア": "5",
            "ストーリー品質": "8",
            "generation_timestamp": "20260101_000000",
        }
        ep2 = {
            "episode_id": "EP-002",
            "fact_check_result": "",
            "super_total_score": "100000",
            "事実密度": "5",
            "生成品質スコア": "5",
            "ストーリー品質": "5",
            "generation_timestamp": "20260101_000000",
        }

        winner_id, loser_id, reason = resolver._determine_winner(ep1, ep2)

        assert winner_id == "EP-001"
        assert loser_id == "EP-002"
        assert "ストーリー品質" in reason

    def test_timestamp_tiebreak(self, resolver):
        """全て同点ならタイムスタンプが新しい方が勝つ"""
        ep1 = {
            "episode_id": "EP-001",
            "fact_check_result": "",
            "super_total_score": "100000",
            "事実密度": "5",
            "生成品質スコア": "5",
            "ストーリー品質": "5",
            "generation_timestamp": "20260101_000000",
        }
        ep2 = {
            "episode_id": "EP-002",
            "fact_check_result": "",
            "super_total_score": "100000",
            "事実密度": "5",
            "生成品質スコア": "5",
            "ストーリー品質": "5",
            "generation_timestamp": "20260102_000000",  # 新しい
        }

        winner_id, loser_id, reason = resolver._determine_winner(ep1, ep2)

        assert winner_id == "EP-002"
        assert loser_id == "EP-001"
        assert "timestamp" in reason


class TestScan:
    """重複スキャンのテスト"""

    def _create_csv(self, tmp_path, rows):
        """テスト用CSVを作成"""
        csv_path = tmp_path / "test.csv"
        fieldnames = [
            "episode_id",
            "person_id",
            "person_name",
            "age",
            "episode_text",
            "fact_check_result",
            "super_total_score",
            "事実密度",
            "生成品質スコア",
            "ストーリー品質",
            "generation_timestamp",
        ]

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                # デフォルト値を設定
                full_row = {k: "" for k in fieldnames}
                full_row.update(row)
                writer.writerow(full_row)

        return csv_path

    def test_no_duplicates(self, tmp_path):
        """重複なしの場合は空リストを返す"""
        csv_path = self._create_csv(
            tmp_path,
            [
                {"episode_id": "EP-001", "person_id": "P1", "person_name": "A", "age": "30"},
                {"episode_id": "EP-002", "person_id": "P1", "person_name": "A", "age": "31"},
                {"episode_id": "EP-003", "person_id": "P2", "person_name": "B", "age": "30"},
            ],
        )

        resolver = SameAgeDuplicateResolver(master_csv=csv_path)
        pairs = resolver.scan()

        assert len(pairs) == 0

    def test_single_duplicate(self, tmp_path):
        """1ペアの重複を検出"""
        csv_path = self._create_csv(
            tmp_path,
            [
                {
                    "episode_id": "EP-001",
                    "person_id": "P1",
                    "person_name": "A",
                    "age": "30",
                    "super_total_score": "100000",
                },
                {
                    "episode_id": "EP-002",
                    "person_id": "P1",
                    "person_name": "A",
                    "age": "30",
                    "super_total_score": "200000",
                },
            ],
        )

        resolver = SameAgeDuplicateResolver(master_csv=csv_path)
        pairs = resolver.scan()

        assert len(pairs) == 1
        assert pairs[0].winner_id == "EP-002"
        assert pairs[0].loser_id == "EP-001"

    def test_multiple_duplicates(self, tmp_path):
        """複数の重複を検出"""
        csv_path = self._create_csv(
            tmp_path,
            [
                # グループ1: P1の30歳
                {
                    "episode_id": "EP-001",
                    "person_id": "P1",
                    "person_name": "A",
                    "age": "30",
                    "super_total_score": "100000",
                },
                {
                    "episode_id": "EP-002",
                    "person_id": "P1",
                    "person_name": "A",
                    "age": "30",
                    "super_total_score": "200000",
                },
                # グループ2: P2の40歳
                {
                    "episode_id": "EP-003",
                    "person_id": "P2",
                    "person_name": "B",
                    "age": "40",
                    "super_total_score": "150000",
                },
                {
                    "episode_id": "EP-004",
                    "person_id": "P2",
                    "person_name": "B",
                    "age": "40",
                    "super_total_score": "180000",
                },
            ],
        )

        resolver = SameAgeDuplicateResolver(master_csv=csv_path)
        pairs = resolver.scan()

        assert len(pairs) == 2

    def test_three_duplicates_in_group(self, tmp_path):
        """3件以上の重複（トーナメント方式）"""
        csv_path = self._create_csv(
            tmp_path,
            [
                {
                    "episode_id": "EP-001",
                    "person_id": "P1",
                    "person_name": "A",
                    "age": "30",
                    "super_total_score": "100000",
                },
                {
                    "episode_id": "EP-002",
                    "person_id": "P1",
                    "person_name": "A",
                    "age": "30",
                    "super_total_score": "200000",
                },
                {
                    "episode_id": "EP-003",
                    "person_id": "P1",
                    "person_name": "A",
                    "age": "30",
                    "super_total_score": "150000",
                },
            ],
        )

        resolver = SameAgeDuplicateResolver(master_csv=csv_path)
        pairs = resolver.scan()

        # 最高スコアのEP-002が勝者、他2件が敗者
        assert len(pairs) == 2
        assert all(p.winner_id == "EP-002" for p in pairs)
        loser_ids = {p.loser_id for p in pairs}
        assert loser_ids == {"EP-001", "EP-003"}


class TestResolve:
    """重複解決のテスト"""

    def _create_csv(self, tmp_path, rows):
        """テスト用CSVを作成"""
        csv_path = tmp_path / "test.csv"
        fieldnames = [
            "episode_id",
            "person_id",
            "person_name",
            "age",
            "episode_text",
            "fact_check_result",
            "super_total_score",
            "事実密度",
            "生成品質スコア",
            "ストーリー品質",
            "generation_timestamp",
        ]

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                full_row = {k: "" for k in fieldnames}
                full_row.update(row)
                writer.writerow(full_row)

        return csv_path

    def test_dry_run_no_deletion(self, tmp_path):
        """dry_runでは削除しない"""
        csv_path = self._create_csv(
            tmp_path,
            [
                {
                    "episode_id": "EP-001",
                    "person_id": "P1",
                    "person_name": "A",
                    "age": "30",
                    "super_total_score": "100000",
                },
                {
                    "episode_id": "EP-002",
                    "person_id": "P1",
                    "person_name": "A",
                    "age": "30",
                    "super_total_score": "200000",
                },
            ],
        )

        resolver = SameAgeDuplicateResolver(master_csv=csv_path)
        result = resolver.resolve(dry_run=True)

        assert result.dry_run is True
        assert result.total_losers == 1

        # CSVは変更されていない
        with open(csv_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 2


class TestVerify:
    """重複検証のテスト"""

    def _create_csv(self, tmp_path, rows):
        """テスト用CSVを作成"""
        csv_path = tmp_path / "test.csv"
        fieldnames = ["episode_id", "person_id", "person_name", "age"]

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)

        return csv_path

    def test_verify_success(self, tmp_path):
        """重複なしで成功"""
        csv_path = self._create_csv(
            tmp_path,
            [
                {"episode_id": "EP-001", "person_id": "P1", "person_name": "A", "age": "30"},
                {"episode_id": "EP-002", "person_id": "P1", "person_name": "A", "age": "31"},
            ],
        )

        resolver = SameAgeDuplicateResolver(master_csv=csv_path)
        success, count = resolver.verify()

        assert success is True
        assert count == 0

    def test_verify_failure(self, tmp_path):
        """重複ありで失敗"""
        csv_path = self._create_csv(
            tmp_path,
            [
                {"episode_id": "EP-001", "person_id": "P1", "person_name": "A", "age": "30"},
                {"episode_id": "EP-002", "person_id": "P1", "person_name": "A", "age": "30"},
            ],
        )

        resolver = SameAgeDuplicateResolver(master_csv=csv_path)
        success, count = resolver.verify()

        assert success is False
        assert count == 1


class TestASKAExample:
    """受け入れ条件: ASKAの39歳重複を正しく解決"""

    def _create_csv(self, tmp_path, rows):
        """テスト用CSVを作成"""
        csv_path = tmp_path / "test.csv"
        fieldnames = [
            "episode_id",
            "person_id",
            "person_name",
            "age",
            "episode_text",
            "fact_check_result",
            "super_total_score",
            "事実密度",
            "生成品質スコア",
            "ストーリー品質",
            "generation_timestamp",
        ]

        with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                full_row = {k: "" for k in fieldnames}
                full_row.update(row)
                writer.writerow(full_row)

        return csv_path

    def test_aska_39_resolution(self, tmp_path):
        """
        受け入れ条件:
        - EP-260105225818577127: super_total=108,354
        - EP-260105225818577129: super_total=111,108
        - 勝者: EP-260105225818577129（super_total高い方）
        """
        csv_path = self._create_csv(
            tmp_path,
            [
                {
                    "episode_id": "EP-260105225818577127",
                    "person_id": "PF960CF9",
                    "person_name": "ASKA",
                    "age": "39",
                    "episode_text": "ASKAは39歳で音楽活動を再開した。",
                    "fact_check_result": "",
                    "super_total_score": "108354",
                    "事実密度": "6.3",
                    "生成品質スコア": "8.0",
                    "ストーリー品質": "7.0",
                    "generation_timestamp": "20260106_082259",
                },
                {
                    "episode_id": "EP-260105225818577129",
                    "person_id": "PF960CF9",
                    "person_name": "ASKA",
                    "age": "39",
                    "episode_text": "ASKAは39歳でソロ活動を再スタートした。",
                    "fact_check_result": "",
                    "super_total_score": "111108",
                    "事実密度": "6.4",
                    "生成品質スコア": "8.0",
                    "ストーリー品質": "7.0",
                    "generation_timestamp": "20260106_082259",
                },
            ],
        )

        resolver = SameAgeDuplicateResolver(master_csv=csv_path)
        pairs = resolver.scan()

        assert len(pairs) == 1
        pair = pairs[0]
        assert pair.winner_id == "EP-260105225818577129"
        assert pair.loser_id == "EP-260105225818577127"
        assert pair.person_name == "ASKA"
        assert pair.age == 39.0
        assert "super_total" in pair.winner_reason


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
