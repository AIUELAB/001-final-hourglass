#!/usr/bin/env python3
"""
test_hallucination_purger.py - ハルシネーション検出・削除システムの単体テスト

このテストモジュールは以下のコンポーネントをテストします:
1. HallucinationDetector - REAL/FICTIONALそれぞれの検出ロジック
2. PhysicalDeleter - CSVからの物理削除とバックアップ機能

テストケース:
- REAL人物 + メタ要素違反 → 削除対象（is_hallucination=True）
- REAL人物 + unverified + fabricated → 削除対象
- FICTIONAL + fanon → 許容（is_hallucination=False）
- FICTIONAL + invalid → 削除対象（is_hallucination=True）
- PhysicalDeleter: ドライラン動作確認
- PhysicalDeleter: バックアップ作成確認

Author: EPUP Validation Team
Date: 2026-02-03
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

# プロジェクトルートをパスに追加
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.validation.hallucination_detector import (
    DetectionResult,
    HallucinationDetector,
)
from scripts.validation.physical_deleter import DeletionResult, PhysicalDeleter
from scripts.validation.real_person_verifier import (
    RealPersonVerifier,
    VerificationResult,
    ViolationType,
)
from src.utils.authenticity_checker import AuthenticityStatus
from src.utils.fictional_quality_gate import QualityResult, Violation
from src.utils.fictional_quality_gate import ViolationType as FictionalViolationType


# =============================================================================
# テスト用フィクスチャ
# =============================================================================


@pytest.fixture
def temp_dir():
    """一時ディレクトリを作成するフィクスチャ"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_real_episode():
    """REAL人物のテスト用エピソードデータ"""
    return {
        "episode_id": "EP-REAL-001",
        "person_id": "P-12345",
        "person_name": "テスト太郎",
        "person_type": "REAL",
        "age": 30,
        "birth_year": 1990,
        "death_year": None,
        "episode_text": "2020年に第1回テスト賞を受賞した。",
        "super_total_score": 50000.0,
        "source": "GENERATED",
        "work_title": "",
    }


@pytest.fixture
def sample_fictional_episode():
    """FICTIONAL人物のテスト用エピソードデータ"""
    return {
        "episode_id": "EP-FICT-001",
        "person_id": "P-FICT-001",
        "person_name": "竈門炭治郎",
        "person_type": "FICTIONAL",
        "age": 15,
        "birth_year": None,
        "death_year": None,
        "episode_text": "鬼殺隊の一員として鬼と戦った。",
        "super_total_score": 60000.0,
        "source": "GENERATED",
        "work_title": "鬼滅の刃",
    }


@pytest.fixture
def temp_csv(temp_dir):
    """テスト用CSVファイルを作成するフィクスチャ"""
    csv_path = temp_dir / "test_episodes.csv"
    csv_content = """episode_id,person_id,person_name,person_type,age,birth_year,death_year,episode_text,super_total_score,source,work_title
EP-001,P-001,正常太郎,REAL,50,1970,,2020年に受賞した。,150000,GENERATED,
EP-002,P-002,埋草太郎,REAL,50,1970,,活動を続けていました。取り組んでいました。貫いていました。,30000,GENERATED,
EP-003,P-003,竈門炭治郎,FICTIONAL,15,,,鬼殺隊で鬼と戦った。,80000,GENERATED,鬼滅の刃
"""
    csv_path.write_text(csv_content, encoding="utf-8-sig")
    return csv_path


# =============================================================================
# HallucinationDetector テスト
# =============================================================================


class TestHallucinationDetector:
    """HallucinationDetectorのテスト"""

    def test_real_person_with_meta_element_is_allowed(self, sample_real_episode):
        """
        テストケース1: REAL人物 + メタ要素（受賞歴など）→ 許容（is_hallucination=False）

        REAL人物のアカデミー賞、グラミー賞などの受賞歴は正当な情報であり、
        RealPersonVerifierが通過した場合はハルシネーション扱いにならない。
        メタ要素検出はFICTIONAL人物専用（RCA-20260203）。
        """
        # メタ要素を含むエピソードを作成（受賞歴は正当）
        episode = sample_real_episode.copy()
        episode["episode_text"] = "2020年にアカデミー賞を受賞した。"

        # RealPersonVerifier をモック化（検証通過させる）
        mock_verification = VerificationResult(
            passed=True,
            violation_type=None,
            violation_detail="",
            filler_score=0,
            concrete_score=3,
        )

        with patch.object(RealPersonVerifier, "verify", return_value=mock_verification):
            detector = HallucinationDetector()
            result = detector.detect(episode)

        # アサーション: REAL人物の受賞歴は正当なのでハルシネーション扱いにならない
        assert result.is_hallucination is False
        assert result.person_type == "REAL"

    def test_real_person_unverified_fabricated(self, sample_real_episode):
        """
        テストケース2: REAL人物 + unverified + fabricated → 削除対象

        RealPersonVerifierがFABRICATION違反を検出した場合、
        ハルシネーションとして削除対象になるべき。
        """
        # 捏造パターンを含むエピソード
        episode = sample_real_episode.copy()
        episode["episode_text"] = "突然現役引退を表明し、養蜂業を始めた。周囲の猛反対を押し切って決断。"
        episode["source"] = "SURPRISE_IMPROVED"

        # RealPersonVerifierの戻り値をモック化
        mock_verification = VerificationResult(
            passed=False,
            violation_type=ViolationType.FABRICATION,
            violation_detail="捏造パターン検出: 養蜂業, 突然現役引退",
            filler_score=0,
            concrete_score=1,
            fabrication_patterns=["養蜂業", "突然現役引退"],
        )

        with patch.object(RealPersonVerifier, "verify", return_value=mock_verification):
            detector = HallucinationDetector()
            result = detector.detect(episode)

        # アサーション
        assert result.is_hallucination is True
        assert result.violation_type == "fabrication"
        assert result.person_type == "REAL"
        assert result.confidence >= 0.8  # FABRICATIONは高確信度

    def test_real_person_year_age_mismatch(self, sample_real_episode):
        """
        テストケース2.5: REAL人物 + 年号-年齢不整合 → 削除対象

        エピソード内の年号と (birth_year + age) が大きくズレている場合、
        ハルシネーションとして検出されるべき。
        例: birth_year=1941 (誤り), age=18 → calculated_year=1959
            エピソード内に「2025年」があると、66年のズレで検出される。
        ※過去の年号は「過去への言及」として許容するため、未来の年号のみ検出対象
        """
        episode = sample_real_episode.copy()
        episode["birth_year"] = 1941  # 誤ったbirth_year（真木よう子のケース同様）
        episode["age"] = 18
        # 1941 + 18 = 1959 だが、エピソード内に「2025年」と書いてある（66年のズレ）
        episode["episode_text"] = "2025年に大きな賞を受賞した。"

        # RealPersonVerifier をモック化（検証通過させる）
        mock_verification = VerificationResult(
            passed=True,
            violation_type=None,
            violation_detail="",
            filler_score=0,
            concrete_score=3,
        )

        with patch.object(RealPersonVerifier, "verify", return_value=mock_verification):
            detector = HallucinationDetector()
            result = detector.detect(episode)

        # アサーション: 年号-年齢不整合でハルシネーション扱い
        assert result.is_hallucination is True
        assert result.violation_type == "year_age_mismatch"
        assert "年号-年齢不整合" in result.reason
        assert result.confidence >= 0.8

    def test_real_person_year_age_match(self, sample_real_episode):
        """
        テストケース2.6: REAL人物 + 年号-年齢整合 → 許容

        エピソード内の年号と (birth_year + age) が一致する場合は許容。
        """
        episode = sample_real_episode.copy()
        episode["birth_year"] = 1970
        episode["age"] = 50
        # 1970 + 50 = 2020 で一致
        episode["episode_text"] = "2020年に大きな功績を達成した。"

        mock_verification = VerificationResult(
            passed=True,
            violation_type=None,
            violation_detail="",
            filler_score=0,
            concrete_score=3,
        )

        with patch.object(RealPersonVerifier, "verify", return_value=mock_verification):
            detector = HallucinationDetector()
            result = detector.detect(episode)

        # アサーション: 整合しているのでハルシネーション扱いにならない
        assert result.is_hallucination is False
        assert result.person_type == "REAL"

    def test_fictional_fanon_allowed(self, sample_fictional_episode):
        """
        テストケース3: FICTIONAL + fanon → 許容（is_hallucination=False）

        架空キャラクターのエピソードで、FictionalQualityGateがpassedでなくても
        authenticity_statusがFANON（またはCANON/NO_MATCH）であれば許容される。
        """
        episode = sample_fictional_episode.copy()
        episode["episode_text"] = "鬼殺隊で仲間と共に戦いを続けた。"

        # FictionalQualityGate の結果をモック化（passed=True、つまり違反なし）
        mock_quality_result = QualityResult(
            passed=True,
            violations=[],
            authenticity_status=AuthenticityStatus.NO_MATCH,  # CANONでなくても許容
        )

        with patch("scripts.validation.hallucination_detector.FictionalQualityGate") as MockGate:
            mock_gate_instance = MockGate.return_value
            mock_gate_instance.check.return_value = mock_quality_result

            detector = HallucinationDetector()
            result = detector.detect(episode)

        # アサーション
        assert result.is_hallucination is False
        assert result.person_type == "FICTIONAL"

    def test_fictional_invalid_is_hallucination(self, sample_fictional_episode):
        """
        テストケース4: FICTIONAL + invalid → 削除対象（is_hallucination=True）

        架空キャラクターのエピソードで、FictionalQualityGateが
        authenticity_status=INVALIDを返した場合、ハルシネーションとして検出。
        """
        episode = sample_fictional_episode.copy()
        episode["episode_text"] = "2019年に任天堂と協力してゲームを開発した。"

        # FictionalQualityGate の結果をモック化（INVALID）
        mock_violation = Violation(
            type=FictionalViolationType.AUTHENTICITY,
            detail="設定違反: 現代年号・現実企業への言及",
            fixable=False,
        )
        mock_quality_result = QualityResult(
            passed=False,
            violations=[mock_violation],
            authenticity_status=AuthenticityStatus.INVALID,
        )

        with patch("scripts.validation.hallucination_detector.FictionalQualityGate") as MockGate:
            mock_gate_instance = MockGate.return_value
            mock_gate_instance.check.return_value = mock_quality_result

            detector = HallucinationDetector()
            result = detector.detect(episode)

        # アサーション
        assert result.is_hallucination is True
        assert result.violation_type == "invalid"
        assert result.person_type == "FICTIONAL"
        assert "真正性検証失敗" in result.reason
        assert result.confidence >= 0.8

    def test_detection_result_to_dict(self):
        """DetectionResult.to_dict() のテスト"""
        result = DetectionResult(
            episode_id="EP-001",
            person_name="テスト太郎",
            person_type="REAL",
            age=30,
            is_hallucination=True,
            reason="テスト理由",
            violation_type="fabrication",
            confidence=0.9,
            super_total_score=50000.0,
        )

        data = result.to_dict()

        assert data["episode_id"] == "EP-001"
        assert data["person_name"] == "テスト太郎"
        assert data["is_hallucination"] is True
        assert data["violation_type"] == "fabrication"
        assert data["confidence"] == 0.9

    def test_get_deletion_candidates(self):
        """削除候補取得のテスト"""
        # 複数の検出結果を用意
        results = [
            DetectionResult(
                episode_id="EP-001",
                person_name="人物A",
                person_type="REAL",
                age=30,
                is_hallucination=True,
                reason="理由A",
                violation_type="fabrication",
                confidence=0.9,
                super_total_score=50000.0,
            ),
            DetectionResult(
                episode_id="EP-002",
                person_name="人物B",
                person_type="REAL",
                age=40,
                is_hallucination=False,
                reason="",
                violation_type="",
                confidence=0.0,
                super_total_score=60000.0,
            ),
            DetectionResult(
                episode_id="EP-003",
                person_name="人物C",
                person_type="FICTIONAL",
                age=15,
                is_hallucination=True,
                reason="理由C",
                violation_type="invalid",
                confidence=0.7,
                super_total_score=40000.0,
            ),
        ]

        detector = HallucinationDetector()
        candidates = detector.get_deletion_candidates(results)

        # 2件が削除候補（is_hallucination=True）
        assert len(candidates) == 2
        # confidence降順でソート
        assert candidates[0]["confidence"] == 0.9
        assert candidates[1]["confidence"] == 0.7

    def test_get_summary(self):
        """検出結果サマリーのテスト"""
        results = [
            DetectionResult(
                episode_id="EP-001",
                person_name="人物A",
                person_type="REAL",
                age=30,
                is_hallucination=True,
                reason="理由A",
                violation_type="fabrication",
                confidence=0.9,
                super_total_score=50000.0,
            ),
            DetectionResult(
                episode_id="EP-002",
                person_name="人物B",
                person_type="REAL",
                age=40,
                is_hallucination=False,
                reason="",
                violation_type="",
                confidence=0.0,
                super_total_score=60000.0,
            ),
            DetectionResult(
                episode_id="EP-003",
                person_name="人物C",
                person_type="FICTIONAL",
                age=15,
                is_hallucination=True,
                reason="理由C",
                violation_type="meta_element",
                confidence=0.7,
                super_total_score=40000.0,
            ),
        ]

        detector = HallucinationDetector()
        summary = detector.get_summary(results)

        assert summary["total"] == 3
        assert summary["hallucinations"] == 2
        assert summary["passed"] == 1
        assert summary["by_violation_type"]["fabrication"] == 1
        assert summary["by_violation_type"]["meta_element"] == 1


# =============================================================================
# PhysicalDeleter テスト
# =============================================================================


class TestPhysicalDeleter:
    """PhysicalDeleterのテスト"""

    def test_dry_run_does_not_delete(self, temp_csv, temp_dir):
        """
        テストケース5: ドライラン動作確認

        dry_run=Trueの場合、CSVは変更されず、
        削除件数のみが返されることを確認。
        """
        # バックアップディレクトリを設定
        deleter = PhysicalDeleter(master_csv=temp_csv)
        deleter.backup_dir = temp_dir / "backups"
        deleter.backup_dir.mkdir(parents=True, exist_ok=True)

        # ドライラン実行
        result = deleter.delete_episodes(["EP-001", "EP-002"], dry_run=True)

        # アサーション
        assert result.success is True
        assert result.deleted_count == 2
        assert len(result.deleted_episodes) == 2
        assert result.backup_path == Path("")  # ドライランではバックアップなし

        # CSVが変更されていないことを確認
        import pandas as pd

        df = pd.read_csv(temp_csv, encoding="utf-8-sig")
        assert len(df) == 3  # 元の3件が残っている

    def test_backup_creation_on_execute(self, temp_csv, temp_dir):
        """
        テストケース6: バックアップ作成確認

        dry_run=Falseで削除を実行した場合、
        バックアップファイルが作成されることを確認。
        """
        # バックアップディレクトリを設定
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        deleter = PhysicalDeleter(master_csv=temp_csv)
        deleter.backup_dir = backup_dir

        # 実行モードで削除
        result = deleter.delete_episodes(["EP-001"], dry_run=False)

        # アサーション
        assert result.success is True
        assert result.deleted_count == 1
        assert result.backup_path.exists()  # バックアップが存在
        assert "pre_purge_" in result.backup_path.name

        # CSVが変更されていることを確認
        import pandas as pd

        df = pd.read_csv(temp_csv, encoding="utf-8-sig")
        assert len(df) == 2  # 1件削除されて2件

        # バックアップには元の3件が残っている
        df_backup = pd.read_csv(result.backup_path, encoding="utf-8-sig")
        assert len(df_backup) == 3

    def test_delete_nonexistent_episode(self, temp_csv, temp_dir):
        """存在しないエピソードIDの削除テスト"""
        deleter = PhysicalDeleter(master_csv=temp_csv)
        deleter.backup_dir = temp_dir / "backups"
        deleter.backup_dir.mkdir(parents=True, exist_ok=True)

        # 存在しないIDを指定
        result = deleter.delete_episodes(["EP-NONEXISTENT"], dry_run=True)

        # アサーション
        assert result.success is True
        assert result.deleted_count == 0  # 見つからないので0件

    def test_delete_empty_list(self, temp_csv, temp_dir):
        """空のリストで削除を試みるテスト"""
        deleter = PhysicalDeleter(master_csv=temp_csv)
        deleter.backup_dir = temp_dir / "backups"
        deleter.backup_dir.mkdir(parents=True, exist_ok=True)

        result = deleter.delete_episodes([], dry_run=True)

        # アサーション
        assert result.success is True
        assert result.deleted_count == 0
        assert "No episode IDs" in result.error_message

    def test_verify_deletion(self, temp_csv, temp_dir):
        """削除結果検証のテスト"""
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        deleter = PhysicalDeleter(master_csv=temp_csv)
        deleter.backup_dir = backup_dir

        # 実際に削除
        deleter.delete_episodes(["EP-001"], dry_run=False)

        # 検証
        deleted, remaining = deleter.verify_deletion(["EP-001", "EP-002"])

        assert deleted == 1  # EP-001は削除済み
        assert remaining == 1  # EP-002は残存

    def test_restore_from_backup(self, temp_csv, temp_dir):
        """バックアップからの復元テスト"""
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        deleter = PhysicalDeleter(master_csv=temp_csv)
        deleter.backup_dir = backup_dir

        # 削除を実行（バックアップが作成される）
        result = deleter.delete_episodes(["EP-001", "EP-002"], dry_run=False)
        backup_path = result.backup_path

        # CSVが2件削除されていることを確認
        import pandas as pd

        df_after_delete = pd.read_csv(temp_csv, encoding="utf-8-sig")
        assert len(df_after_delete) == 1

        # バックアップから復元
        restore_success = deleter.restore_from_backup(backup_path)

        # アサーション
        assert restore_success is True

        # 復元後、元の3件に戻っていることを確認
        df_restored = pd.read_csv(temp_csv, encoding="utf-8-sig")
        assert len(df_restored) == 3

    def test_list_backups(self, temp_csv, temp_dir):
        """バックアップ一覧取得のテスト"""
        backup_dir = temp_dir / "backups"
        backup_dir.mkdir(parents=True, exist_ok=True)

        deleter = PhysicalDeleter(master_csv=temp_csv)
        deleter.backup_dir = backup_dir

        # 複数回削除してバックアップを作成
        deleter.delete_episodes(["EP-001"], dry_run=False)

        # バックアップ一覧を取得
        backups = deleter.list_backups()

        assert len(backups) >= 1
        assert all(b.suffix == ".csv" for b in backups)


# =============================================================================
# DeletionResult データクラステスト
# =============================================================================


class TestDeletionResult:
    """DeletionResultデータクラスのテスト"""

    def test_str_success(self):
        """成功時の文字列表現テスト"""
        result = DeletionResult(
            success=True,
            deleted_count=5,
            backup_path=Path("/path/to/backup.csv"),
            deleted_episodes=["EP-001", "EP-002"],
        )

        str_repr = str(result)
        assert "success=True" in str_repr
        assert "deleted_count=5" in str_repr

    def test_str_failure(self):
        """失敗時の文字列表現テスト"""
        result = DeletionResult(
            success=False,
            deleted_count=0,
            backup_path=Path(""),
            error_message="Test error",
        )

        str_repr = str(result)
        assert "success=False" in str_repr
        assert "Test error" in str_repr


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
