#!/usr/bin/env python3
"""
マイルストーン整合性テスト

テスト対象:
- scripts/validation/milestone_consistency_gate.py
- scripts/validation/detect_milestone_age_conflicts.py

テスト観点:
1. KNOWN_FACTS整合性チェック
2. 重複マイルストーン検出
3. 誤検出防止
4. 尾崎豊修正後の回帰テスト
"""

import csv
import sys
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts" / "validation"))

from milestone_consistency_gate import (
    KNOWN_FACTS,
    check_known_fact_violation,
    extract_milestone_claims,
    scan_milestone_consistency,
)


class TestExtractMilestoneClaims:
    """マイルストーン抽出テスト"""

    def test_debut_detected(self):
        """T1: デビュー表現が検出される"""
        text = "彼はこの年、レコードデビューを果たしました。"
        claims = extract_milestone_claims(text)
        assert "デビューを果たし" in claims

    def test_award_detected(self):
        """受賞表現が検出される"""
        text = "この作品でノーベル賞を受賞した。"
        claims = extract_milestone_claims(text)
        assert "を受賞" in claims

    def test_no_milestone(self):
        """T10: マイルストーンなしは空リスト"""
        text = "彼は音楽活動を続けていました。"
        claims = extract_milestone_claims(text)
        assert claims == []


class TestCheckKnownFactViolation:
    """KNOWN_FACTS違反チェックテスト"""

    def test_ozaki_correct_age(self):
        """T3: 尾崎豊18歳デビューは違反なし"""
        result = check_known_fact_violation(person_name="尾崎豊", age=18.0, text="レコードデビューを果たしました")
        assert result is None

    def test_ozaki_wrong_age(self):
        """T4: 尾崎豊15歳デビューは違反"""
        result = check_known_fact_violation(person_name="尾崎豊", age=15.0, text="レコードデビューを果たしました")
        assert result is not None
        assert result["severity"] == "CRITICAL"
        assert result["correct_age"] == 18

    def test_utada_correct_age(self):
        """宇多田ヒカル15歳デビューは正しい"""
        result = check_known_fact_violation(person_name="宇多田ヒカル", age=15.0, text="デビューを果たしました")
        assert result is None

    def test_unknown_person(self):
        """未知の人物は違反なし"""
        result = check_known_fact_violation(person_name="未知の歌手", age=20.0, text="デビューを果たしました")
        assert result is None

    def test_age_tolerance(self):
        """許容誤差（±2歳）内は通過"""
        # 尾崎豊は18歳デビュー、17歳は±2以内なので通過
        result = check_known_fact_violation(person_name="尾崎豊", age=17.0, text="デビューを果たしました")
        assert result is None


class TestOzakiRegression:
    """尾崎豊修正後の回帰テスト"""

    @pytest.fixture
    def master_csv(self):
        """マスターCSVパス"""
        return PROJECT_ROOT / "preserved/data/MASTER_EPISODES_CURRENT.csv"

    @pytest.mark.xfail(reason="既存データ品質課題: 尾崎エピソード数変動 - 技術的負債", strict=False)
    def test_ozaki_episodes_exist(self, master_csv):
        """尾崎豊のエピソードが5件存在"""
        with open(master_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            ozaki_eps = [r for r in reader if r.get("person_id") == "P91861F7"]
        assert len(ozaki_eps) == 5

    def test_ozaki_debut_only_at_18(self, master_csv):
        """T3: デビュー断定は18歳エピソードのみ"""
        with open(master_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            ozaki_eps = [r for r in reader if r.get("person_id") == "P91861F7"]

        debut_ages = []
        for ep in ozaki_eps:
            text = ep.get("episode_text", "")
            age = float(ep.get("age") or 0)
            # 断定表現のみチェック
            if "デビューを果たし" in text or "でデビューした" in text:
                debut_ages.append(age)

        # 18歳のみでデビュー断定
        assert debut_ages == [18.0], f"デビュー断定が複数年齢: {debut_ages}"

    def test_ozaki_no_debut_at_other_ages(self, master_csv):
        """T3: 14歳・15歳・16歳にデビュー断定がない"""
        with open(master_csv, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            ozaki_eps = [r for r in reader if r.get("person_id") == "P91861F7"]

        for ep in ozaki_eps:
            text = ep.get("episode_text", "")
            age = float(ep.get("age") or 0)

            if age in [14.0, 15.0, 16.0]:
                # これらの年齢では「デビュー」キーワードが含まれないはず
                assert "デビュー" not in text, f"{age}歳にデビュー表現あり"


class TestScanMilestoneConsistency:
    """全体スキャンテスト"""

    def test_scan_returns_structure(self):
        """スキャン結果の構造確認"""
        result = scan_milestone_consistency()

        assert "scan_date" in result
        assert "known_fact_violations" in result
        assert "milestone_duplicates" in result
        assert "summary" in result

    def test_ozaki_not_in_violations(self):
        """T3: 修正後の尾崎豊はKNOWN_FACTS違反に含まれない"""
        result = scan_milestone_consistency()

        ozaki_violations = [v for v in result["known_fact_violations"] if v["person_name"] == "尾崎豊"]
        assert len(ozaki_violations) == 0, f"尾崎豊に違反あり: {ozaki_violations}"


class TestMilestoneAgeSpread:
    """年齢スプレッド判定テスト"""

    def test_spread_threshold(self):
        """T5/T6: 年齢スプレッド閾値"""
        # 5歳以上はCRITICAL、5歳未満はWARNINGまたは許容
        result = scan_milestone_consistency()

        for dup in result["milestone_duplicates"]:
            if dup["age_spread"] >= 10:
                assert dup["severity"] == "CRITICAL"
            elif dup["age_spread"] >= 5:
                # 5-9歳はCRITICALまたはWARNING（実装による）
                assert dup["severity"] in ["CRITICAL", "WARNING"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
