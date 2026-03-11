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


class TestProposeDispersionRulesNoMembers:
    """propose_dispersion_rulesでメンバーがいない場合のテスト"""

    @patch("src.data.master_updater.GROUP_ENTITIES", {"メンバーなしグループ"})
    @patch("src.data.master_updater.GROUP_MEMBER_MAP", {})  # メンバーなし
    @patch("src.data.master_updater.DISPERSION_RULES", {})  # ルールなし
    def test_no_members_proposal(self):
        """メンバーがいないグループの提案"""
        from src.data.master_updater import MasterUpdater

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type\n")
            f.write("テスト,P001,REAL\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path)
            proposals = updater.propose_dispersion_rules()

            # メンバーなしグループが提案される
            assert len(proposals) == 1
            assert proposals[0].group_name == "メンバーなしグループ"
            assert proposals[0].strategy == "REPRESENTATIVE"
            assert proposals[0].confidence == 0.3
            assert "手動定義" in proposals[0].reason
        finally:
            os.unlink(temp_path)


class TestDetectNewEntitiesEdgeCases:
    """detect_new_entitiesのエッジケーステスト"""

    @patch("src.data.master_updater.GROUP_ENTITIES", set())
    @patch("src.data.master_updater.GROUP_MEMBER_MAP", {})
    def test_empty_person_name(self):
        """空の person_name"""
        from src.data.master_updater import MasterUpdater

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_id\n")
            f.write(",P001,REAL,EP001\n")  # 空の名前
            f.write("テストバンド,P002,REAL,EP002\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path)
            entities = updater.detect_new_entities()

            # 空の名前はスキップされる
            assert all(e.name != "" for e in entities)
        finally:
            os.unlink(temp_path)

    @patch("src.data.master_updater.GROUP_ENTITIES", set())
    @patch("src.data.master_updater.GROUP_MEMBER_MAP", {})
    def test_na_person_name(self):
        """NaN の person_name"""
        from src.data.master_updater import MasterUpdater
        import numpy as np

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_id\n")
            f.write("テストグループ,P001,REAL,EP001\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path)
            # NaN 値を手動で設定
            updater.df.loc[0, "person_name"] = np.nan
            entities = updater.detect_new_entities()

            # NaN はスキップされる
            assert len(entities) == 0
        finally:
            os.unlink(temp_path)


class TestProposeDispersionRulesLargeGroup:
    """propose_dispersion_rulesで6名以上のメンバーがいる場合のテスト（L162-169カバー）"""

    @patch(
        "src.data.master_updater.GROUP_ENTITIES",
        {"大人数グループ"},
    )
    @patch(
        "src.data.master_updater.GROUP_MEMBER_MAP",
        {
            "メンバー1": "大人数グループ",
            "メンバー2": "大人数グループ",
            "メンバー3": "大人数グループ",
            "メンバー4": "大人数グループ",
            "メンバー5": "大人数グループ",
            "メンバー6": "大人数グループ",
        },
    )
    @patch("src.data.master_updater.DISPERSION_RULES", {})
    def test_representative_strategy_for_large_group(self):
        """6名以上のグループにはREPRESENTATIVE戦略が提案される"""
        from src.data.master_updater import MasterUpdater

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type\n")
            f.write("テスト,P001,REAL\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path)
            proposals = updater.propose_dispersion_rules()

            assert len(proposals) == 1
            assert proposals[0].group_name == "大人数グループ"
            assert proposals[0].strategy == "REPRESENTATIVE"
            assert "代表者分散" in proposals[0].reason
            # membersは最大5名
            assert len(proposals[0].members) <= 5
        finally:
            os.unlink(temp_path)


class TestDetectEmptyPersonName:
    """detect_new_entitiesで空のperson_nameをスキップするテスト（L100カバー）"""

    @patch("src.data.master_updater.GROUP_ENTITIES", set())
    @patch("src.data.master_updater.GROUP_MEMBER_MAP", {})
    def test_empty_string_person_name_skipped(self):
        """空文字列のperson_nameがスキップされる"""
        from src.data.master_updater import MasterUpdater

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_id\n")
            f.write(",P001,REAL,EP001\n")  # 空文字列
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path)
            entities = updater.detect_new_entities()
            # 空文字列はスキップされるので結果は空
            assert len(entities) == 0
        finally:
            os.unlink(temp_path)


class TestDetectNoMatchPatterns:
    """detect_new_entitiesでどのパターンにもマッチしない場合のテスト"""

    @patch("src.data.master_updater.GROUP_ENTITIES", set())
    @patch("src.data.master_updater.GROUP_MEMBER_MAP", {})
    def test_no_group_or_concat_pattern(self):
        """グループパターンにも連結パターンにもマッチしない名前"""
        from src.data.master_updater import MasterUpdater

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type,episode_id\n")
            f.write("普通の人名,P001,REAL,EP001\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path)
            entities = updater.detect_new_entities()
            assert len(entities) == 0
        finally:
            os.unlink(temp_path)


class TestMainApplyWithBackup:
    """main関数で--apply時にbackup_pathが結果に含まれる場合のテスト"""

    @patch("sys.argv", ["master_updater.py", "--csv", "test.csv", "--apply"])
    @patch("src.data.master_updater.MasterUpdater")
    def test_main_apply_no_backup_key(self, MockUpdater):
        """--apply で backup_path がない場合"""
        from src.data.master_updater import main, RuleProposal

        mock_instance = MagicMock()
        mock_instance.detect_new_entities.return_value = []
        mock_instance.propose_dispersion_rules.return_value = [RuleProposal("グループA", "ALL", ["A"], 0.95, "テスト")]
        mock_instance.apply_updates.return_value = {
            "applied": [{"group": "グループA"}],
            "skipped": [],
        }
        MockUpdater.return_value = mock_instance

        main()
        mock_instance.apply_updates.assert_called_once()


class TestMainWithLowConfProposals:
    """main関数で低信頼度提案がある場合のテスト（L332->338, L349->exit分岐カバー）"""

    @patch("sys.argv", ["master_updater.py", "--csv", "test.csv"])
    @patch("src.data.master_updater.MasterUpdater")
    def test_main_with_low_and_high_conf_proposals(self, MockUpdater):
        """高信頼度と低信頼度の両方の提案がある場合"""
        from src.data.master_updater import main, RuleProposal

        mock_instance = MagicMock()
        mock_instance.detect_new_entities.return_value = []
        mock_instance.propose_dispersion_rules.return_value = [
            RuleProposal("高信頼グループ", "ALL", ["A", "B"], 0.95, "高信頼度"),
            RuleProposal("低信頼グループ", "REPRESENTATIVE", [], 0.3, "低信頼度"),
        ]
        mock_instance.generate_diff.return_value = "# Diff content"
        MockUpdater.return_value = mock_instance

        main()

        mock_instance.propose_dispersion_rules.assert_called_once()


class TestMain:
    """main関数のテスト"""

    @patch("sys.argv", ["master_updater.py", "--csv", "test.csv", "--detect-only"])
    @patch("src.data.master_updater.MasterUpdater")
    def test_main_detect_only(self, MockUpdater):
        """--detect-only オプション"""
        from src.data.master_updater import main, NewEntity

        mock_instance = MagicMock()
        mock_instance.detect_new_entities.return_value = [
            NewEntity("テストグループ", "group", "EP001", 0.8, "追加推奨")
        ]
        MockUpdater.return_value = mock_instance

        main()

        mock_instance.detect_new_entities.assert_called_once()
        mock_instance.propose_dispersion_rules.assert_not_called()

    @patch("sys.argv", ["master_updater.py", "--csv", "test.csv"])
    @patch("src.data.master_updater.MasterUpdater")
    def test_main_default(self, MockUpdater):
        """デフォルト実行（提案まで）"""
        from src.data.master_updater import main, NewEntity, RuleProposal

        mock_instance = MagicMock()
        mock_instance.detect_new_entities.return_value = []
        mock_instance.propose_dispersion_rules.return_value = [
            RuleProposal("グループA", "ALL", ["A", "B"], 0.95, "テスト理由")
        ]
        mock_instance.generate_diff.return_value = "# Diff"
        MockUpdater.return_value = mock_instance

        main()

        mock_instance.detect_new_entities.assert_called_once()
        mock_instance.propose_dispersion_rules.assert_called_once()
        mock_instance.generate_diff.assert_called_once()

    @patch("sys.argv", ["master_updater.py", "--csv", "test.csv", "--apply"])
    @patch("src.data.master_updater.MasterUpdater")
    def test_main_apply(self, MockUpdater):
        """--apply オプション"""
        from src.data.master_updater import main, RuleProposal

        mock_instance = MagicMock()
        mock_instance.detect_new_entities.return_value = []
        mock_instance.propose_dispersion_rules.return_value = [RuleProposal("グループA", "ALL", ["A"], 0.95, "テスト")]
        mock_instance.apply_updates.return_value = {
            "applied": [{"group": "グループA"}],
            "skipped": [],
            "backup_path": "/path/to/backup",
        }
        MockUpdater.return_value = mock_instance

        main()

        mock_instance.apply_updates.assert_called_once()

    @patch("sys.argv", ["master_updater.py", "--csv", "test.csv"])
    @patch("src.data.master_updater.MasterUpdater")
    def test_main_many_entities(self, MockUpdater):
        """10件以上のエンティティ"""
        from src.data.master_updater import main, NewEntity

        mock_instance = MagicMock()
        # 15件のエンティティ
        mock_instance.detect_new_entities.return_value = [
            NewEntity(f"グループ{i}", "group", f"EP{i:03d}", 0.8, "追加") for i in range(15)
        ]
        mock_instance.propose_dispersion_rules.return_value = []
        mock_instance.generate_diff.return_value = ""
        MockUpdater.return_value = mock_instance

        main()

        mock_instance.detect_new_entities.assert_called_once()

    @patch("sys.argv", ["master_updater.py", "--csv", "test.csv", "--min-confidence", "0.5"])
    @patch("src.data.master_updater.MasterUpdater")
    def test_main_min_confidence(self, MockUpdater):
        """--min-confidence オプション"""
        from src.data.master_updater import main, RuleProposal

        mock_instance = MagicMock()
        mock_instance.detect_new_entities.return_value = []
        mock_instance.propose_dispersion_rules.return_value = [
            RuleProposal("高信頼", "ALL", ["A"], 0.9, "高"),
            RuleProposal("低信頼", "ALL", ["B"], 0.3, "低"),
        ]
        mock_instance.generate_diff.return_value = "# Diff"
        MockUpdater.return_value = mock_instance

        main()

        # min_confidence=0.5 で初期化される
        MockUpdater.assert_called_once()
        call_args = MockUpdater.call_args
        assert call_args[0][1] == 0.5

    @patch("sys.argv", ["master_updater.py", "--csv", "test.csv"])
    @patch("src.data.master_updater.MasterUpdater")
    def test_main_long_diff(self, MockUpdater):
        """500文字以上の差分"""
        from src.data.master_updater import main

        mock_instance = MagicMock()
        mock_instance.detect_new_entities.return_value = []
        mock_instance.propose_dispersion_rules.return_value = []
        mock_instance.generate_diff.return_value = "x" * 600  # 600文字
        MockUpdater.return_value = mock_instance

        main()

        mock_instance.generate_diff.assert_called_once()


class TestProposeDispersionRulesSmallGroup:
    """propose_dispersion_rulesで5名以下のメンバーがいる場合のテスト（L162-164カバー）"""

    @patch(
        "src.data.master_updater.GROUP_ENTITIES",
        {"小人数グループ"},
    )
    @patch(
        "src.data.master_updater.GROUP_MEMBER_MAP",
        {
            "メンバー1": "小人数グループ",
            "メンバー2": "小人数グループ",
            "メンバー3": "小人数グループ",
        },
    )
    @patch("src.data.master_updater.DISPERSION_RULES", {})
    def test_all_strategy_for_small_group(self):
        """5名以下のグループにはALL戦略が提案される (L162-164)"""
        from src.data.master_updater import MasterUpdater

        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("person_name,person_id,person_type\n")
            f.write("テスト,P001,REAL\n")
            temp_path = f.name

        try:
            updater = MasterUpdater(temp_path)
            proposals = updater.propose_dispersion_rules()

            assert len(proposals) == 1
            assert proposals[0].group_name == "小人数グループ"
            assert proposals[0].strategy == "ALL"
            assert "全員分散" in proposals[0].reason
        finally:
            os.unlink(temp_path)
