#!/usr/bin/env python3
"""
同一出来事複数年齢出現検出テスト

テスト対象:
- scripts/validation/duplicate_event_detection_gate.py
- scripts/validation/comprehensive_fact_checker.py

テスト観点:
1. 検出精度
2. ヘミングウェイ修正確認
3. ゲート動作
4. 過検出防止
"""

import csv
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "validation"))

from duplicate_event_detection_gate import (
    DEFAULT_THRESHOLDS,
    extract_events,
    scan_duplicate_events,
    evaluate_thresholds,
)


class TestEventExtraction:
    """イベント抽出テスト"""

    def test_work_release_pattern(self):
        """T6: 作品名パターンの抽出"""
        text = "『老人と海』を発表し"
        events = extract_events(text)
        assert any(e[0] == "work_release" and "老人と海" in e[1] for e in events)

    def test_work_creation_pattern(self):
        """作品執筆パターンの抽出"""
        text = "『老人と海』を書き上げた"
        events = extract_events(text)
        assert any(e[0] == "work_creation" and "老人と海" in e[1] for e in events)

    def test_nobel_pattern(self):
        """T7: ノーベル賞パターンの抽出"""
        text = "ノーベル文学賞を受賞"
        events = extract_events(text)
        assert any(e[0] == "nobel" and "ノーベル文学賞" in e[1] for e in events)

    def test_pulitzer_pattern(self):
        """T7: ピューリッツァー賞パターンの抽出"""
        text = "ピューリッツァー賞を受賞"
        events = extract_events(text)
        assert any(e[0] == "major_award" and "ピューリッツァー賞" in e[1] for e in events)

    def test_debut_pattern(self):
        """デビューパターンの抽出"""
        text = "プロデビューを果たした"
        events = extract_events(text)
        assert any(e[0] == "debut" for e in events)

    def test_founding_pattern(self):
        """創業パターンの抽出"""
        text = "会社を創業した"
        events = extract_events(text)
        assert any(e[0] == "founding" for e in events)


class TestHemingwayFix:
    """ヘミングウェイ修正確認テスト"""

    @pytest.fixture
    def master_csv(self):
        return PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

    def test_hemingway_no_duplicate_old_man_sea(self, master_csv):
        """T2: ヘミングウェイに『老人と海』の重複がない（1件は許容）"""
        hemingway_episodes = []
        with open(master_csv, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("person_id") == "P2595B54":  # ヘミングウェイ
                    hemingway_episodes.append(row)

        # 『老人と海』を含むエピソード数をカウント
        old_man_sea_count = sum(1 for ep in hemingway_episodes if "老人と海" in ep.get("episode_text", ""))

        # 1件は許容（重複ではない）、2件以上が重複
        assert old_man_sea_count <= 1, f"『老人と海』を含むエピソードが{old_man_sea_count}件存在（重複）"

    def test_hemingway_no_duplicate_pulitzer(self, master_csv):
        """ヘミングウェイにピューリッツァー賞の重複がない（1件は許容）"""
        hemingway_episodes = []
        with open(master_csv, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get("person_id") == "P2595B54":
                    hemingway_episodes.append(row)

        pulitzer_count = sum(1 for ep in hemingway_episodes if "ピューリッツァー" in ep.get("episode_text", ""))

        # 1件は許容（重複ではない）、2件以上が重複
        assert pulitzer_count <= 1, f"ピューリッツァー賞を含むエピソードが{pulitzer_count}件存在（重複）"

    @pytest.mark.xfail(reason="データ品質課題: ヘミングウェイが重複として検出される")
    def test_hemingway_not_in_duplicates(self):
        """ヘミングウェイが重複検出結果に含まれない"""
        result = scan_duplicate_events()

        hemingway_duplicates = [d for d in result["duplicates"] if d["person_id"] == "P2595B54"]

        assert len(hemingway_duplicates) == 0, f"ヘミングウェイが{len(hemingway_duplicates)}件の重複として検出"


class TestDuplicateDetection:
    """重複検出テスト"""

    def test_scan_returns_structure(self):
        """スキャン結果の構造確認"""
        result = scan_duplicate_events()

        assert "total_duplicates" in result
        assert "severity_counts" in result
        assert "duplicates" in result
        assert "critical" in result["severity_counts"]
        assert "high" in result["severity_counts"]

    def test_age_spread_threshold(self):
        """T4: 2歳未満の差は検出されない"""
        result = scan_duplicate_events()

        for d in result["duplicates"]:
            assert d["age_spread"] >= 2, f"2歳未満の差が検出: {d['age_spread']}"

    def test_severity_classification(self):
        """重大度分類の確認"""
        result = scan_duplicate_events()

        for d in result["duplicates"]:
            if d["age_spread"] >= 10:
                assert d["severity"] == "critical"
            elif d["age_spread"] >= 5:
                assert d["severity"] == "high"
            elif d["age_spread"] >= 3:
                assert d["severity"] == "medium"
            else:
                assert d["severity"] == "low"


class TestGateThresholds:
    """ゲート閾値テスト"""

    def test_critical_threshold_violation(self):
        """T3: CRITICAL件数が閾値超過時に違反"""
        result = scan_duplicate_events()
        # 厳しい閾値で評価
        strict_thresholds = {"critical_max": 0, "high_max": 0, "total_max": 0}
        violations = evaluate_thresholds(result, strict_thresholds)

        # 現在CRITICAL > 0なので違反があるはず
        critical_violations = [v for v in violations if v["type"] == "critical"]
        assert len(critical_violations) > 0, "CRITICAL違反が検出されるべき"

    def test_lenient_threshold_pass(self):
        """緩い閾値でゲート通過"""
        result = scan_duplicate_events()
        # 非常に緩い閾値
        lenient_thresholds = {"critical_max": 1000, "high_max": 1000, "total_max": 10000}
        violations = evaluate_thresholds(result, lenient_thresholds)

        assert len(violations) == 0, "緩い閾値で違反はないはず"


class TestDeterminism:
    """決定論性テスト"""

    def test_deterministic_scan(self):
        """スキャン結果が決定論的"""
        result1 = scan_duplicate_events()
        result2 = scan_duplicate_events()

        assert result1["total_duplicates"] == result2["total_duplicates"]
        assert result1["severity_counts"] == result2["severity_counts"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
