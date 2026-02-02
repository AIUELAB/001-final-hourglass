#!/usr/bin/env python3
"""
test_fabrication_guardian.py - 捏造検出システムの単体・統合テスト

テスト対象:
1. QuarantineManager - エピソード隔離システム
2. WikipediaClient - Wikipedia検証クライアント
3. RealPersonVerifier - 実在人物検証
4. FabricationGuardian - 統合オーケストレーター

Author: EPUP Validation Team
Date: 2026-02-01
"""

import sys
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.quarantine_manager import (
    QuarantineManager,
    QuarantineRecord,
    QuarantineStatus,
)
from scripts.validation.real_person_verifier import (
    RealPersonVerifier,
    VerificationResult,
    ViolationType,
)
from src.utils.wikipedia_client import PersonInfo, WikipediaClient


# =============================================================================
# テスト用フィクスチャ
# =============================================================================


@pytest.fixture
def temp_dir():
    """一時ディレクトリを作成するフィクスチャ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def quarantine_manager(temp_dir):
    """テスト用QuarantineManagerを作成"""
    return QuarantineManager(quarantine_dir=temp_dir)


@pytest.fixture
def wikipedia_client(temp_dir):
    """テスト用WikipediaClientを作成"""
    cache_file = temp_dir / "test_cache.json"
    return WikipediaClient(cache_file=cache_file)


@pytest.fixture
def real_person_verifier():
    """テスト用RealPersonVerifierを作成"""
    return RealPersonVerifier()


@pytest.fixture
def sample_episode():
    """テスト用エピソードデータ"""
    return {
        "episode_id": "EP-TEST-001",
        "person_id": "P-12345",
        "person_name": "テスト太郎",
        "person_type": "REAL",
        "age": 30.0,
        "birth_year": 1990,
        "episode_text": "2020年に第1回テスト賞を受賞した。",
        "super_total_score": 50000.0,
        "source": "GENERATED",
    }


@pytest.fixture
def sample_filler_episode():
    """埋草エピソードのテストデータ"""
    return {
        "episode_id": "EP-FILLER-001",
        "person_id": "P-FILLER",
        "person_name": "埋草太郎",
        "person_type": "REAL",
        "age": 50.0,
        "birth_year": 1970,
        "episode_text": "精力的に活動を続けていました。創作活動を行い、次世代の育成にも取り組んでいました。信念を貫いていました。",
        "super_total_score": 30000.0,
        "source": "GENERATED",
    }


@pytest.fixture
def sample_future_episode():
    """未来エピソードのテストデータ"""
    return {
        "episode_id": "EP-FUTURE-001",
        "person_id": "P-FUTURE",
        "person_name": "大谷翔平",
        "person_type": "REAL",
        "age": 59.0,
        "birth_year": 1994,
        "episode_text": "2053年に通算1000本塁打を達成した。",
        "super_total_score": 80000.0,
        "source": "GENERATED",
    }


# =============================================================================
# QuarantineManager テスト
# =============================================================================


class TestQuarantineManager:
    """QuarantineManagerのテスト"""

    def test_quarantine_episode(self, quarantine_manager, sample_episode):
        """エピソード隔離のテスト"""
        # 隔離実行
        record = quarantine_manager.quarantine(
            episode_id=sample_episode["episode_id"],
            person_name=sample_episode["person_name"],
            reason="テスト用隔離",
            violation_type="TEST_VIOLATION",
            super_total_score=sample_episode["super_total_score"],
            episode_data=sample_episode,
        )

        # 検証
        assert record is not None
        assert record.episode_id == sample_episode["episode_id"]
        assert record.person_name == sample_episode["person_name"]
        assert record.status == QuarantineStatus.QUARANTINED
        assert record.violation_type == "TEST_VIOLATION"
        assert record.reason == "テスト用隔離"

        # 統計も更新されることを確認
        quarantined = quarantine_manager.get_quarantined(status=QuarantineStatus.QUARANTINED)
        assert len(quarantined) == 1

    def test_quarantine_duplicate_episode(self, quarantine_manager, sample_episode):
        """重複隔離の動作テスト"""
        # 最初の隔離
        record1 = quarantine_manager.quarantine(
            episode_id=sample_episode["episode_id"],
            person_name=sample_episode["person_name"],
            reason="最初の隔離",
            violation_type="TEST_VIOLATION",
            super_total_score=sample_episode["super_total_score"],
            episode_data=sample_episode,
        )

        # 重複隔離（同じIDで再度隔離）
        record2 = quarantine_manager.quarantine(
            episode_id=sample_episode["episode_id"],
            person_name=sample_episode["person_name"],
            reason="重複隔離",
            violation_type="TEST_VIOLATION_2",
            super_total_score=sample_episode["super_total_score"],
            episode_data=sample_episode,
        )

        # 既存レコードが返されることを確認
        assert record2.episode_id == record1.episode_id
        assert record2.status == QuarantineStatus.QUARANTINED

    def test_release_episode(self, quarantine_manager, sample_episode):
        """隔離解除のテスト"""
        # 先に隔離
        quarantine_manager.quarantine(
            episode_id=sample_episode["episode_id"],
            person_name=sample_episode["person_name"],
            reason="テスト用隔離",
            violation_type="TEST_VIOLATION",
            super_total_score=sample_episode["super_total_score"],
            episode_data=sample_episode,
        )

        # 解除実行
        released = quarantine_manager.release(
            episode_id=sample_episode["episode_id"],
            release_reason="テスト解除",
        )

        # 検証
        assert released is not None
        assert released.status == QuarantineStatus.RELEASED
        assert released.release_reason == "テスト解除"
        assert released.release_timestamp is not None

    def test_release_nonexistent_episode(self, quarantine_manager):
        """存在しないエピソードの解除テスト"""
        result = quarantine_manager.release(
            episode_id="EP-NONEXISTENT",
            release_reason="テスト",
        )
        assert result is None

    def test_purge_episode(self, quarantine_manager, sample_episode):
        """完全削除のテスト"""
        # 先に隔離
        quarantine_manager.quarantine(
            episode_id=sample_episode["episode_id"],
            person_name=sample_episode["person_name"],
            reason="テスト用隔離",
            violation_type="TEST_VIOLATION",
            super_total_score=sample_episode["super_total_score"],
            episode_data=sample_episode,
        )

        # 完全削除
        success = quarantine_manager.purge(sample_episode["episode_id"])

        # 検証
        assert success is True

        # ステータス確認
        record = quarantine_manager.get_record(sample_episode["episode_id"])
        assert record is not None
        assert record.status == QuarantineStatus.PURGED

    def test_purge_nonexistent_episode(self, quarantine_manager):
        """存在しないエピソードの完全削除テスト"""
        success = quarantine_manager.purge("EP-NONEXISTENT")
        assert success is False

    def test_get_quarantined_by_status(self, quarantine_manager):
        """ステータス別取得のテスト"""
        # 複数エピソードを隔離
        for i in range(3):
            quarantine_manager.quarantine(
                episode_id=f"EP-TEST-{i:03d}",
                person_name=f"テスト人物{i}",
                reason=f"理由{i}",
                violation_type="TEST",
                super_total_score=10000.0,
                episode_data={"episode_id": f"EP-TEST-{i:03d}"},
            )

        # 1つを解除
        quarantine_manager.release("EP-TEST-001", "解除理由")

        # 1つを完全削除
        quarantine_manager.purge("EP-TEST-002")

        # ステータス別取得
        quarantined = quarantine_manager.get_quarantined(status=QuarantineStatus.QUARANTINED)
        released = quarantine_manager.get_quarantined(status=QuarantineStatus.RELEASED)
        purged = quarantine_manager.get_quarantined(status=QuarantineStatus.PURGED)

        assert len(quarantined) == 1
        assert len(released) == 1
        assert len(purged) == 1

    def test_generate_report(self, quarantine_manager, sample_episode):
        """レポート生成のテスト"""
        # 隔離
        quarantine_manager.quarantine(
            episode_id=sample_episode["episode_id"],
            person_name=sample_episode["person_name"],
            reason="レポートテスト",
            violation_type="FABRICATION",
            super_total_score=sample_episode["super_total_score"],
            episode_data=sample_episode,
        )

        # レポート生成
        report = quarantine_manager.generate_report()

        # 検証
        assert "generated_at" in report
        assert "statistics" in report
        assert "violation_type_breakdown" in report
        assert "recent_quarantined" in report

        # 統計確認
        stats = report["statistics"]
        assert stats["total_quarantined"] == 1
        assert stats["total_released"] == 0
        assert stats["total_purged"] == 0

        # 違反タイプ別集計
        breakdown = report["violation_type_breakdown"]
        assert breakdown.get("FABRICATION", 0) == 1

    def test_get_restorable_data(self, quarantine_manager, sample_episode):
        """復元用データ取得のテスト"""
        # 隔離
        quarantine_manager.quarantine(
            episode_id=sample_episode["episode_id"],
            person_name=sample_episode["person_name"],
            reason="復元テスト",
            violation_type="TEST",
            super_total_score=sample_episode["super_total_score"],
            episode_data=sample_episode,
        )

        # 復元用データ取得
        data = quarantine_manager.get_restorable_data(sample_episode["episode_id"])

        # 検証
        assert data is not None
        assert data["episode_id"] == sample_episode["episode_id"]
        assert data["person_name"] == sample_episode["person_name"]


# =============================================================================
# WikipediaClient テスト
# =============================================================================


class TestWikipediaClient:
    """WikipediaClientのテスト"""

    def test_parse_birth_year_standard_format(self, wikipedia_client):
        """生年パース: 標準形式のテスト"""
        text = "織田信長（1534年6月23日 - 1582年6月21日）は、日本の戦国武将。"
        result = wikipedia_client.parse_wikipedia_result("織田信長", text)

        assert result.exists is True
        assert result.birth_year == 1534

    def test_parse_birth_year_year_only(self, wikipedia_client):
        """生年パース: 年のみ形式のテスト"""
        text = "アインシュタイン（1879年 - 1955年）は、理論物理学者。"
        result = wikipedia_client.parse_wikipedia_result("アインシュタイン", text)

        assert result.birth_year == 1879

    def test_parse_birth_year_born_suffix(self, wikipedia_client):
        """生年パース: 「生まれ」形式のテスト"""
        text = "田中太郎は1980年生まれの作家である。"
        result = wikipedia_client.parse_wikipedia_result("田中太郎", text)

        assert result.birth_year == 1980

    def test_parse_death_year_standard_format(self, wikipedia_client):
        """没年パース: 標準形式のテスト"""
        text = "織田信長（1534年6月23日 - 1582年6月21日）は、日本の戦国武将。"
        result = wikipedia_client.parse_wikipedia_result("織田信長", text)

        assert result.death_year == 1582

    def test_parse_death_year_death_suffix(self, wikipedia_client):
        """没年パース: 「没」形式のテスト"""
        text = "夏目漱石（1867年 - 1916年没）は日本の小説家。"
        result = wikipedia_client.parse_wikipedia_result("夏目漱石", text)

        assert result.death_year == 1916

    def test_parse_occupation(self, wikipedia_client):
        """職業パースのテスト"""
        text = "織田信長は日本の武将で戦国大名。"
        result = wikipedia_client.parse_wikipedia_result("織田信長", text)

        assert result.occupation == "武将"

    def test_parse_nationality(self, wikipedia_client):
        """国籍パースのテスト"""
        text = "アインシュタインはドイツ生まれの理論物理学者。"
        result = wikipedia_client.parse_wikipedia_result("アインシュタイン", text)

        assert result.nationality == "ドイツ"

    def test_cache_save_and_load(self, wikipedia_client):
        """キャッシュ保存・読み込みのテスト"""
        # データをパースしてキャッシュに保存
        text = "織田信長（1534年 - 1582年）は日本の武将。"
        wikipedia_client.parse_wikipedia_result("織田信長", text)

        # キャッシュから取得
        cached = wikipedia_client.verify_person("織田信長")

        assert cached.exists is True
        assert cached.birth_year == 1534
        assert cached.death_year == 1582

    def test_cache_validity(self, wikipedia_client):
        """キャッシュ有効期限のテスト"""
        # 有効なキャッシュエントリ
        valid_entry = {
            "name": "テスト人物",
            "exists": True,
            "birth_year": 1990,
            "death_year": None,
            "occupation": "テスト",
            "nationality": "日本",
            "source_url": "https://example.com",
            "confidence": 0.8,
            "cache_timestamp": datetime.now().isoformat(),
        }

        # 期限切れのキャッシュエントリ
        expired_entry = {
            "name": "期限切れ人物",
            "exists": True,
            "birth_year": 1980,
            "death_year": None,
            "occupation": "テスト",
            "nationality": "日本",
            "source_url": "https://example.com",
            "confidence": 0.8,
            "cache_timestamp": (datetime.now() - timedelta(days=10)).isoformat(),
        }

        # 有効性チェック
        assert wikipedia_client._is_cache_valid(valid_entry) is True
        assert wikipedia_client._is_cache_valid(expired_entry) is False

    def test_confidence_calculation(self, wikipedia_client):
        """信頼度計算のテスト"""
        # 全情報あり
        full_confidence = wikipedia_client._calculate_confidence(
            exists=True,
            birth_year=1990,
            death_year=2020,
            occupation="科学者",
            nationality="日本",
        )
        assert full_confidence == 1.0

        # 存在しない場合
        no_confidence = wikipedia_client._calculate_confidence(
            exists=False,
            birth_year=None,
            death_year=None,
            occupation=None,
            nationality=None,
        )
        assert no_confidence == 0.0

        # 部分的な情報
        partial_confidence = wikipedia_client._calculate_confidence(
            exists=True,
            birth_year=1990,
            death_year=None,
            occupation=None,
            nationality=None,
        )
        assert 0.0 < partial_confidence < 1.0

    def test_cache_clear(self, wikipedia_client):
        """キャッシュクリアのテスト"""
        # データをパース
        wikipedia_client.parse_wikipedia_result("テスト人物", "テスト人物（1990年生まれ）")

        # クリア前確認
        before = wikipedia_client.verify_person("テスト人物")
        assert before.exists is True

        # クリア
        wikipedia_client.clear_cache("テスト人物")

        # クリア後確認
        after = wikipedia_client.verify_person("テスト人物")
        assert after.exists is False

    def test_cache_stats(self, wikipedia_client):
        """キャッシュ統計のテスト"""
        # データをパース
        wikipedia_client.parse_wikipedia_result("人物1", "人物1（1990年生まれ）は作家。")
        wikipedia_client.parse_wikipedia_result("人物2", "人物2（1980年生まれ）は科学者。")

        # 統計取得
        stats = wikipedia_client.get_cache_stats()

        assert stats["total_entries"] == 2
        assert stats["valid_entries"] == 2
        assert stats["exists_count"] == 2


# =============================================================================
# RealPersonVerifier テスト
# =============================================================================


class TestRealPersonVerifier:
    """RealPersonVerifierのテスト"""

    def test_detect_future_episode(self, real_person_verifier):
        """未来エピソード検出のテスト"""
        result = real_person_verifier.verify(
            person_name="大谷翔平",
            episode_text="2060年に史上初の通算2000本塁打を達成した。",
            age=59.0,
            birth_year=1994,
        )

        assert result.passed is False
        assert result.violation_type == ViolationType.FUTURE_EPISODE
        assert "未来" in result.violation_detail

    def test_detect_future_episode_threshold(self, real_person_verifier):
        """未来エピソード閾値のテスト（CURRENT_YEAR + 2年まで許容）"""
        # 現在年 + 2年は許容
        result_ok = real_person_verifier.verify(
            person_name="テスト人物",
            episode_text="テストエピソード",
            age=36.0,  # 1994 + 36 = 2030 > 2026 + 2
            birth_year=1994,
        )
        # 2030年 > 2028年（閾値）なので未来エピソード
        assert result_ok.passed is False
        assert result_ok.violation_type == ViolationType.FUTURE_EPISODE

    def test_detect_post_death(self, real_person_verifier):
        """死亡後エピソード検出のテスト"""
        result = real_person_verifier.verify(
            person_name="手塚治虫",
            episode_text="死後もなお影響力を持ち続けた。",
            age=70.0,
            birth_year=1928,
            death_year=1989,
        )

        assert result.passed is False
        assert result.violation_type == ViolationType.POST_DEATH
        assert "死亡後" in result.violation_detail

    def test_detect_filler(self, real_person_verifier, sample_filler_episode):
        """埋草エピソード検出のテスト"""
        result = real_person_verifier.verify(
            person_name=sample_filler_episode["person_name"],
            episode_text=sample_filler_episode["episode_text"],
            age=sample_filler_episode["age"],
            birth_year=sample_filler_episode["birth_year"],
        )

        assert result.passed is False
        assert result.violation_type == ViolationType.FILLER
        assert result.filler_score >= 3
        assert result.concrete_score < 2

    def test_detect_fabrication(self, real_person_verifier):
        """捏造パターン検出のテスト"""
        result = real_person_verifier.verify(
            person_name="テスト人物",
            episode_text="突然現役引退を表明し、養蜂業を始めた。周囲の猛反対を押し切って決断。",
            age=50.0,
            birth_year=1970,
            source="SURPRISE_IMPROVED",  # 捏造チェックが有効になるソース
        )

        assert result.passed is False
        assert result.violation_type == ViolationType.FABRICATION
        assert len(result.fabrication_patterns) > 0
        assert "養蜂業" in result.fabrication_patterns

    def test_pass_valid_episode(self, real_person_verifier):
        """正常エピソードの通過テスト"""
        result = real_person_verifier.verify(
            person_name="田中太郎",
            episode_text="2020年に第1回テスト大賞を受賞した。この業績により、学会でも高く評価された。",
            age=50.0,
            birth_year=1970,
        )

        assert result.passed is True
        assert result.violation_type is None
        assert result.concrete_score >= 2

    def test_batch_verify(self, real_person_verifier):
        """バッチ検証のテスト"""
        episodes = [
            {
                "person_name": "正常人物",
                "episode_text": "2020年に受賞した。",
                "age": 50,
                "birth_year": 1970,
            },
            {
                "person_name": "埋草人物",
                "episode_text": "活動を続けていました。取り組んでいました。貫いていました。",
                "age": 50,
                "birth_year": 1970,
            },
        ]

        results = real_person_verifier.batch_verify(episodes)

        assert len(results) == 2
        assert results[0][1].passed is True
        assert results[1][1].passed is False

    def test_violation_summary(self, real_person_verifier):
        """違反サマリーのテスト"""
        episodes = [
            {
                "person_name": "正常人物",
                "episode_text": "2020年に受賞した。",
                "age": 50,
                "birth_year": 1970,
            },
            {
                "person_name": "埋草人物",
                "episode_text": "活動を続けていました。取り組んでいました。貫いていました。",
                "age": 50,
                "birth_year": 1970,
            },
        ]

        results = real_person_verifier.batch_verify(episodes)
        summary = real_person_verifier.get_violation_summary(results)

        assert summary["total"] == 2
        assert summary["passed"] == 1
        assert summary["failed"] == 1
        assert "by_violation_type" in summary


# =============================================================================
# FabricationGuardian 統合テスト
# =============================================================================


class TestFabricationGuardianIntegration:
    """FabricationGuardianの統合テスト"""

    @pytest.fixture
    def temp_csv(self, temp_dir):
        """テスト用CSVファイルを作成"""
        csv_path = temp_dir / "test_episodes.csv"
        csv_content = """episode_id,person_id,person_name,person_type,age,birth_year,death_year,episode_text,super_total_score,source
EP-PASS-001,P-001,正常太郎,REAL,50,1970,,2020年に受賞した。,150000,GENERATED
EP-FILLER-001,P-002,埋草太郎,REAL,50,1970,,活動を続けていました。取り組んでいました。貫いていました。,30000,GENERATED
EP-FUTURE-001,P-003,未来太郎,REAL,70,1994,,2064年に達成した。,80000,GENERATED
EP-SKIP-001,P-004,不明太郎,UNKNOWN,50,1970,,テスト,50000,GENERATED
"""
        csv_path.write_text(csv_content, encoding="utf-8-sig")
        return csv_path

    @pytest.fixture
    def guardian(self, temp_csv, temp_dir):
        """テスト用FabricationGuardianを作成"""
        from scripts.validation.fabrication_guardian import FabricationGuardian

        guardian = FabricationGuardian(csv_path=temp_csv, dry_run=True)
        guardian.quarantine_manager = QuarantineManager(quarantine_dir=temp_dir)
        return guardian

    def test_scan_dry_run(self, guardian):
        """ドライランスキャンのテスト"""
        results = guardian.scan()

        # 4件スキャンされることを確認
        assert len(results) == 4

        # 各結果の確認
        pass_count = sum(1 for r in results if r.action.value == "pass")
        skip_count = sum(1 for r in results if r.action.value == "skipped")

        # 正常エピソード（super_total_score >= 100000）は通過
        # 埋草・未来エピソード（super_total_score < 100000）は隔離対象
        # UNKNOWN person_typeはスキップ
        assert pass_count >= 1  # EP-PASS-001は通過
        assert skip_count == 1  # EP-SKIP-001はスキップ

    def test_quarantine_threshold(self, guardian):
        """隔離閾値判定のテスト"""
        # 閾値以上のエピソード
        high_score_episode = {"super_total_score": 150000}
        assert guardian._should_quarantine(high_score_episode) is False

        # 閾値未満のエピソード
        low_score_episode = {"super_total_score": 50000}
        assert guardian._should_quarantine(low_score_episode) is True

        # 境界値
        boundary_episode = {"super_total_score": 100000}
        assert guardian._should_quarantine(boundary_episode) is False

    def test_generate_report(self, guardian):
        """レポート生成のテスト"""
        # 先にスキャン
        guardian.scan()

        # レポート生成
        report = guardian.generate_report()

        # 検証
        assert "scan_timestamp" in report
        assert "total_scanned" in report
        assert "passed" in report
        assert "violations_detected" in report
        assert "quarantine_threshold" in report
        assert "dry_run" in report
        assert report["dry_run"] is True

    def test_execute_summary(self, guardian):
        """実行サマリーのテスト"""
        # 先にスキャン
        guardian.scan()

        # 実行サマリー取得
        summary = guardian.execute()

        # 検証
        assert "executed_at" in summary
        assert "dry_run" in summary
        assert "total_scanned" in summary
        assert summary["dry_run"] is True

    def test_release_episode(self, guardian, temp_dir):
        """隔離解除機能のテスト"""
        # 先に手動で隔離
        qm = QuarantineManager(quarantine_dir=temp_dir)
        qm.quarantine(
            episode_id="EP-TEST-RELEASE",
            person_name="解除テスト",
            reason="テスト理由",
            violation_type="TEST",
            super_total_score=50000,
            episode_data={"episode_id": "EP-TEST-RELEASE"},
        )

        # QuarantineManagerを共有
        guardian.quarantine_manager = qm

        # 解除
        success = guardian.release("EP-TEST-RELEASE")

        # 検証
        assert success is True

        # ステータス確認
        record = qm.get_record("EP-TEST-RELEASE")
        assert record.status == QuarantineStatus.RELEASED

    def test_scan_with_person_id_filter(self, guardian):
        """person_idフィルタでのスキャンテスト"""
        results = guardian.scan(person_id="P-001")

        # P-001のエピソードのみ
        assert len(results) == 1
        assert results[0].person_name == "正常太郎"

    def test_scan_with_limit(self, guardian):
        """件数上限でのスキャンテスト"""
        results = guardian.scan(limit=2)

        assert len(results) == 2


# =============================================================================
# QuarantineRecord データクラステスト
# =============================================================================


class TestQuarantineRecord:
    """QuarantineRecordデータクラスのテスト"""

    def test_to_dict(self):
        """辞書変換のテスト"""
        record = QuarantineRecord(
            episode_id="EP-001",
            person_name="テスト人物",
            quarantine_timestamp="2026-02-01T12:00:00",
            reason="テスト理由",
            violation_type="TEST",
            super_total_score=50000.0,
            original_data={"key": "value"},
            status=QuarantineStatus.QUARANTINED,
        )

        data = record.to_dict()

        assert data["episode_id"] == "EP-001"
        assert data["status"] == "quarantined"
        assert data["original_data"] == {"key": "value"}

    def test_from_dict(self):
        """辞書からの生成テスト"""
        data = {
            "episode_id": "EP-001",
            "person_name": "テスト人物",
            "quarantine_timestamp": "2026-02-01T12:00:00",
            "reason": "テスト理由",
            "violation_type": "TEST",
            "super_total_score": 50000.0,
            "original_data": {"key": "value"},
            "status": "released",
            "release_timestamp": "2026-02-02T12:00:00",
            "release_reason": "解除理由",
        }

        record = QuarantineRecord.from_dict(data)

        assert record.episode_id == "EP-001"
        assert record.status == QuarantineStatus.RELEASED
        assert record.release_reason == "解除理由"


# =============================================================================
# PersonInfo データクラステスト
# =============================================================================


class TestPersonInfo:
    """PersonInfoデータクラスのテスト"""

    def test_to_dict(self):
        """辞書変換のテスト"""
        info = PersonInfo(
            name="テスト人物",
            exists=True,
            birth_year=1990,
            death_year=None,
            occupation="科学者",
            nationality="日本",
            source_url="https://example.com",
            confidence=0.8,
            cache_timestamp="2026-02-01T12:00:00",
        )

        data = info.to_dict()

        assert data["name"] == "テスト人物"
        assert data["exists"] is True
        assert data["confidence"] == 0.8

    def test_from_dict(self):
        """辞書からの生成テスト"""
        data = {
            "name": "テスト人物",
            "exists": True,
            "birth_year": 1990,
            "death_year": 2020,
            "occupation": "科学者",
            "nationality": "日本",
            "source_url": "https://example.com",
            "confidence": 0.9,
            "cache_timestamp": "2026-02-01T12:00:00",
        }

        info = PersonInfo.from_dict(data)

        assert info.name == "テスト人物"
        assert info.death_year == 2020
        assert info.confidence == 0.9

    def test_not_found(self):
        """存在しない人物のテスト"""
        info = PersonInfo.not_found("不明人物")

        assert info.name == "不明人物"
        assert info.exists is False
        assert info.confidence == 0.0
        assert info.cache_timestamp is not None


# =============================================================================
# VerificationResult データクラステスト
# =============================================================================


class TestVerificationResult:
    """VerificationResultデータクラスのテスト"""

    def test_to_dict(self):
        """辞書変換のテスト"""
        result = VerificationResult(
            passed=False,
            violation_type=ViolationType.FILLER,
            violation_detail="埋草スコア: 5",
            filler_score=5,
            concrete_score=1,
            fabrication_patterns=["活動を続け"],
            suggestion="具体的な内容に修正してください",
            wikipedia_verified=False,
        )

        data = result.to_dict()

        assert data["passed"] is False
        assert data["violation_type"] == "filler"
        assert data["filler_score"] == 5
        assert "活動を続け" in data["fabrication_patterns"]

    def test_passed_result(self):
        """通過結果のテスト"""
        result = VerificationResult(
            passed=True,
            violation_type=None,
            violation_detail="",
            filler_score=0,
            concrete_score=5,
        )

        data = result.to_dict()

        assert data["passed"] is True
        assert data["violation_type"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
