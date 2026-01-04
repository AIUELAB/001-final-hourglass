#!/usr/bin/env python3
"""
celebrity_score_v2 同期検証の回帰テスト

テスト観点:
1. mutable使い回し検出
2. 部分更新検出（一部だけ更新されて残りが古いまま）
3. CSV-DB不整合検出
4. テンプレートコピー検出
"""

import sqlite3
import sys
import tempfile
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.validation.verify_celebrity_score_v2_sync import (
    detect_mismatches,
    detect_template_copy,
)


class TestDetectMismatches:
    """CSV-DB不整合検出のテスト"""

    def test_no_mismatch(self):
        """不整合がない場合は空リストを返す"""
        csv_scores = {
            "P001": (100.0, "テスト太郎"),
            "P002": (200.0, "テスト花子"),
        }
        db_scores = {
            "P001": 100.0,
            "P002": 200.0,
        }

        mismatches = detect_mismatches(csv_scores, db_scores)

        assert len(mismatches) == 0

    def test_detect_single_mismatch(self):
        """単一の不整合を検出"""
        csv_scores = {
            "P001": (100.0, "テスト太郎"),
            "P002": (200.0, "テスト花子"),  # 不整合
        }
        db_scores = {
            "P001": 100.0,
            "P002": 300.0,  # CSVと異なる
        }

        mismatches = detect_mismatches(csv_scores, db_scores)

        assert len(mismatches) == 1
        assert mismatches[0]["person_id"] == "P002"
        assert mismatches[0]["csv_score"] == 200.0
        assert mismatches[0]["db_score"] == 300.0

    def test_detect_multiple_mismatches(self):
        """複数の不整合を検出"""
        csv_scores = {
            "P001": (100.0, "A"),
            "P002": (200.0, "B"),
            "P003": (300.0, "C"),
        }
        db_scores = {
            "P001": 150.0,  # 不整合
            "P002": 200.0,  # 一致
            "P003": 350.0,  # 不整合
        }

        mismatches = detect_mismatches(csv_scores, db_scores)

        assert len(mismatches) == 2
        person_ids = {m["person_id"] for m in mismatches}
        assert person_ids == {"P001", "P003"}

    def test_sorted_by_difference(self):
        """差が大きい順にソートされる"""
        csv_scores = {
            "P001": (100.0, "A"),  # 差: 10
            "P002": (200.0, "B"),  # 差: 100
            "P003": (300.0, "C"),  # 差: 50
        }
        db_scores = {
            "P001": 110.0,
            "P002": 300.0,
            "P003": 350.0,
        }

        mismatches = detect_mismatches(csv_scores, db_scores)

        assert len(mismatches) == 3
        assert mismatches[0]["person_id"] == "P002"  # 差100
        assert mismatches[1]["person_id"] == "P003"  # 差50
        assert mismatches[2]["person_id"] == "P001"  # 差10

    def test_skip_db_missing(self):
        """DBに存在しない人物はスキップ"""
        csv_scores = {
            "P001": (100.0, "A"),
            "P002": (200.0, "B"),  # DBにない
        }
        db_scores = {
            "P001": 100.0,
            # P002はDBにない
        }

        mismatches = detect_mismatches(csv_scores, db_scores)

        assert len(mismatches) == 0

    def test_tolerance_within_limit(self):
        """許容差以内は不整合としない"""
        csv_scores = {
            "P001": (100.0, "A"),
        }
        db_scores = {
            "P001": 100.005,  # 差0.005 < 許容差0.01
        }

        mismatches = detect_mismatches(csv_scores, db_scores)

        assert len(mismatches) == 0


class TestDetectTemplateCopy:
    """テンプレートコピー問題検出のテスト"""

    def test_no_duplicates(self):
        """重複がない場合は空辞書を返す"""
        csv_scores = {
            "P001": (100.0, "A"),
            "P002": (200.0, "B"),
            "P003": (300.0, "C"),
        }

        duplicates = detect_template_copy(csv_scores)

        assert len(duplicates) == 0

    def test_detect_large_duplicates(self):
        """10人以上の重複を検出"""
        csv_scores = {
            f"P{i:03d}": (610.06, f"Person{i}")  # 15人が同じ値
            for i in range(15)
        }
        csv_scores["P100"] = (500.0, "Different")  # 別の値

        duplicates = detect_template_copy(csv_scores)

        assert len(duplicates) == 1
        assert 610.06 in duplicates
        assert duplicates[610.06] == 15

    def test_ignore_small_duplicates(self):
        """9人以下の重複は無視"""
        csv_scores = {
            f"P{i:03d}": (610.06, f"Person{i}")  # 9人が同じ値
            for i in range(9)
        }

        duplicates = detect_template_copy(csv_scores)

        assert len(duplicates) == 0

    def test_multiple_duplicate_groups(self):
        """複数の重複グループを検出"""
        csv_scores = {}
        # グループ1: 12人
        for i in range(12):
            csv_scores[f"A{i:03d}"] = (100.0, f"A{i}")
        # グループ2: 15人
        for i in range(15):
            csv_scores[f"B{i:03d}"] = (200.0, f"B{i}")
        # グループ3: 5人（閾値以下）
        for i in range(5):
            csv_scores[f"C{i:03d}"] = (300.0, f"C{i}")

        duplicates = detect_template_copy(csv_scores)

        assert len(duplicates) == 2
        assert 100.0 in duplicates
        assert 200.0 in duplicates
        assert 300.0 not in duplicates


class TestMutableReuse:
    """mutable使い回し問題のテスト

    テンプレートコピー問題の典型パターン:
    - 同じdict/listをループ内で使い回して上書き
    - deepcopy不足
    """

    def test_mutable_dict_reuse_bug(self):
        """mutable dict使い回しバグのシミュレーション"""

        # バグのあるコード（修正前）
        def buggy_calculate_scores(persons: list) -> dict:
            result = {}
            template = {"score": 0, "rank": 0}  # ← 問題: 同じdictを使い回す

            for person in persons:
                template["score"] = person["raw_score"] * 1.5
                template["rank"] = person["id"]
                result[person["id"]] = template  # ← 全員同じdictを参照

            return result

        persons = [
            {"id": "P001", "raw_score": 100},
            {"id": "P002", "raw_score": 200},
            {"id": "P003", "raw_score": 300},
        ]

        result = buggy_calculate_scores(persons)

        # バグの証明: 全員が最後の人物のスコアを持つ
        assert result["P001"]["score"] == 450  # 本来は150であるべき
        assert result["P002"]["score"] == 450  # 本来は300であるべき
        assert result["P003"]["score"] == 450  # これが最後の値

    def test_mutable_dict_correct_implementation(self):
        """正しい実装: 毎回新しいdictを作成"""

        def correct_calculate_scores(persons: list) -> dict:
            result = {}

            for person in persons:
                result[person["id"]] = {  # ← 毎回新しいdictを作成
                    "score": person["raw_score"] * 1.5,
                    "rank": person["id"],
                }

            return result

        persons = [
            {"id": "P001", "raw_score": 100},
            {"id": "P002", "raw_score": 200},
            {"id": "P003", "raw_score": 300},
        ]

        result = correct_calculate_scores(persons)

        # 正しい結果
        assert result["P001"]["score"] == 150
        assert result["P002"]["score"] == 300
        assert result["P003"]["score"] == 450


class TestPartialUpdate:
    """部分更新問題のテスト

    一部の人物だけ更新されて残りが古いままになるパターン
    """

    def test_partial_update_detection(self):
        """部分更新を検出"""
        # 更新前の状態（全員同じデフォルト値）
        original_scores = {f"P{i:03d}": 0.0 for i in range(100)}

        # 部分更新後の状態（前半49人だけ更新、P000は0.0のまま）
        updated_scores = original_scores.copy()
        for i in range(1, 50):  # P001〜P049を更新（49人）
            updated_scores[f"P{i:03d}"] = float(i * 10)  # 更新

        # CSVとして扱う
        csv_scores = {pid: (score, f"Person{pid}") for pid, score in updated_scores.items()}

        # テンプレートコピー検出
        duplicates = detect_template_copy(csv_scores)

        # P000とP050〜P099の51人が0.0のままなので検出される
        assert 0.0 in duplicates
        assert duplicates[0.0] == 51


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
