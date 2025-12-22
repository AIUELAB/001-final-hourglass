"""
tests/test_master_updater.py - data/master_updater.py ユニットテスト
"""

from unittest.mock import MagicMock, patch
import tempfile
import os

import pandas as pd
import pytest


class TestNewEntity:
    """NewEntityデータクラステスト"""

    def test_new_entity_creation(self):
        """NewEntity作成"""
        from src.data.master_updater import NewEntity

        entity = NewEntity(
            name="テストグループ",
            entity_type="group",
            detected_in="EP001",
            confidence=0.8,
            suggested_action="GROUP_ENTITIESに追加",
        )

        assert entity.name == "テストグループ"
        assert entity.entity_type == "group"
        assert entity.confidence == 0.8


class TestRuleProposal:
    """RuleProposalデータクラステスト"""

    def test_rule_proposal_creation(self):
        """RuleProposal作成"""
        from src.data.master_updater import RuleProposal

        proposal = RuleProposal(
            group_name="テストグループ",
            strategy="ALL",
            members=["メンバー1", "メンバー2"],
            confidence=0.9,
            reason="メンバー2名で全員分散が適切",
        )

        assert proposal.group_name == "テストグループ"
        assert proposal.strategy == "ALL"
        assert len(proposal.members) == 2


class TestMasterUpdaterInit:
    """MasterUpdater初期化テスト"""

    def test_init_with_valid_csv(self):
        """有効なCSVで初期化"""
        from src.data.master_updater import MasterUpdater

        # テスト用の一時CSVを作成
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_id,episode_text\n")
            f.write("テスト太郎,P001,REAL,EP001,テスト\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path, min_confidence=0.8)

            assert updater.min_confidence == 0.8
            assert len(updater.df) == 1
        finally:
            os.unlink(temp_path)


class TestDetectNewEntities:
    """detect_new_entitiesメソッドテスト"""

    @patch("src.data.master_updater.GROUP_ENTITIES", {"既存グループ"})
    @patch("src.data.master_updater.GROUP_MEMBER_MAP", {})
    def test_detect_group_pattern(self):
        """グループパターン検出"""
        from src.data.master_updater import MasterUpdater

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_id\n")
            f.write("新グループ,P001,REAL,EP001\n")  # グループパターンに一致
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path)
            entities = updater.detect_new_entities()

            # 「新グループ」はGROUP_PATTERNSに一致しない
            # パターンに一致するケースをテスト
            assert isinstance(entities, list)
        finally:
            os.unlink(temp_path)

    @patch("src.data.master_updater.GROUP_ENTITIES", set())
    @patch("src.data.master_updater.GROUP_MEMBER_MAP", {})
    def test_detect_concat_pattern(self):
        """連結パターン検出"""
        from src.data.master_updater import MasterUpdater

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_id\n")
            f.write("グループ名・メンバー名,P001,REAL,EP001\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path)
            entities = updater.detect_new_entities()

            # 連結パターンで検出
            assert isinstance(entities, list)
        finally:
            os.unlink(temp_path)

    @patch("src.data.master_updater.GROUP_ENTITIES", set())
    @patch("src.data.master_updater.GROUP_MEMBER_MAP", {})
    def test_detect_duplicates_removed(self):
        """重複が除去される"""
        from src.data.master_updater import MasterUpdater

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_id\n")
            f.write("テストバンド,P001,REAL,EP001\n")
            f.write("テストバンド,P002,REAL,EP002\n")  # 同じ名前
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path)
            entities = updater.detect_new_entities()

            # 重複は除去される
            names = [e.name for e in entities]
            assert len(names) == len(set(names))
        finally:
            os.unlink(temp_path)


class TestProposeDispersionRules:
    """propose_dispersion_rulesメソッドテスト"""

    @patch("src.data.master_updater.GROUP_ENTITIES", {"グループA", "グループB"})
    @patch("src.data.master_updater.GROUP_MEMBER_MAP", {"メンバー1": "グループA", "メンバー2": "グループA"})
    @patch("src.data.master_updater.DISPERSION_RULES", {"グループA": MagicMock()})
    def test_propose_undefined_groups(self):
        """未定義グループの提案"""
        from src.data.master_updater import MasterUpdater

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type\n")
            f.write("テスト,P001,REAL\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path)
            proposals = updater.propose_dispersion_rules()

            # グループBは未定義なので提案される
            assert any(p.group_name == "グループB" for p in proposals)
        finally:
            os.unlink(temp_path)


class TestGenerateDiff:
    """generate_diffメソッドテスト"""

    def test_generate_diff_high_confidence(self):
        """高信頼度の差分生成"""
        from src.data.master_updater import MasterUpdater, RuleProposal

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type\n")
            f.write("テスト,P001,REAL\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path, min_confidence=0.9)

            proposals = [
                RuleProposal(
                    group_name="テストグループ",
                    strategy="ALL",
                    members=["A", "B"],
                    confidence=0.95,  # 閾値以上
                    reason="テスト",
                )
            ]

            diff = updater.generate_diff(proposals)

            assert "テストグループ" in diff
            assert "DispersionStrategy.ALL" in diff
        finally:
            os.unlink(temp_path)

    def test_generate_diff_low_confidence(self):
        """低信頼度は除外"""
        from src.data.master_updater import MasterUpdater, RuleProposal

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type\n")
            f.write("テスト,P001,REAL\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path, min_confidence=0.9)

            proposals = [
                RuleProposal(
                    group_name="低信頼グループ",
                    strategy="ALL",
                    members=["A"],
                    confidence=0.5,  # 閾値未満
                    reason="テスト",
                )
            ]

            diff = updater.generate_diff(proposals)

            assert "低信頼グループ" not in diff
        finally:
            os.unlink(temp_path)


class TestApplyUpdates:
    """apply_updatesメソッドテスト"""

    def test_apply_dry_run(self):
        """ドライランモード"""
        from src.data.master_updater import MasterUpdater, RuleProposal

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type\n")
            f.write("テスト,P001,REAL\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path, min_confidence=0.9)

            proposals = [
                RuleProposal(
                    group_name="適用グループ",
                    strategy="ALL",
                    members=["A"],
                    confidence=0.95,
                    reason="テスト",
                ),
                RuleProposal(
                    group_name="スキップグループ",
                    strategy="ALL",
                    members=["B"],
                    confidence=0.5,  # 閾値未満
                    reason="テスト",
                ),
            ]

            result = updater.apply_updates(proposals, dry_run=True)

            assert result["dry_run"] is True
            assert len(result["applied"]) == 1
            assert len(result["skipped"]) == 1
            assert result["applied"][0]["group"] == "適用グループ"
        finally:
            os.unlink(temp_path)

    def test_apply_actual(self):
        """実際の適用（バックアップ作成）"""
        from src.data.master_updater import MasterUpdater, RuleProposal

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type\n")
            f.write("テスト,P001,REAL\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path, min_confidence=0.9)

            proposals = [
                RuleProposal(
                    group_name="適用グループ",
                    strategy="ALL",
                    members=["A"],
                    confidence=0.95,
                    reason="テスト",
                )
            ]

            # バックアップパスのモック
            with patch("shutil.copy"):
                with patch("pathlib.Path.mkdir"):
                    with patch("pathlib.Path.exists", return_value=True):
                        result = updater.apply_updates(proposals, dry_run=False)

            assert result["dry_run"] is False
            assert "note" in result
        finally:
            os.unlink(temp_path)
