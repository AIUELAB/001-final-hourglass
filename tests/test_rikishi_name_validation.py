"""
力士名バリデーション回帰テスト

目的:
- 力士名の正規化が正しく動作することを保証
- マスターCSVに本名混入がないことを検証

実行:
    pytest tests/test_rikishi_name_validation.py -v
"""

import sys
from pathlib import Path

import pandas as pd
import pytest

# プロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.data.normalize_person_names import RIKISHI_SHIKONA, PersonNameNormalizer


class TestRikishiNameNormalization:
    """力士名正規化のテスト"""

    def test_known_rikishi_normalization(self):
        """既知力士の正規化（千代の富士貢 → 千代の富士）"""
        normalizer = PersonNameNormalizer()
        result = normalizer.normalize("千代の富士貢")

        assert result is not None
        assert result.normalized_name == "千代の富士"
        assert result.confidence >= 0.95
        assert result.pattern_type == "RIKISHI_SHIKONA"

    @pytest.mark.parametrize(
        "original,expected",
        [
            ("舞の海秀平", "舞の海"),
            ("土佐ノ海敏生", "土佐ノ海"),
            ("千代の富士貢", "千代の富士"),
        ],
    )
    def test_new_rikishi_normalization(self, original, expected):
        """Phase 4で追加した力士が正しく正規化されるか"""
        normalizer = PersonNameNormalizer()
        result = normalizer.normalize(original)

        assert result is not None, f"{original} が正規化されませんでした"
        assert result.normalized_name == expected
        assert result.confidence >= 0.85

    def test_correct_shikona_not_normalized(self):
        """正しい四股名は正規化されない"""
        normalizer = PersonNameNormalizer()

        correct_shikonas = ["千代の富士", "舞の海", "土佐ノ海", "稀勢の里"]

        for shikona in correct_shikonas:
            result = normalizer.normalize(shikona)
            assert result is None, f"{shikona} が誤って正規化されました"


class TestMasterCSVRikishiConsistency:
    """マスターCSVの力士名整合性テスト"""

    def test_no_rikishi_contamination_in_master_csv(self):
        """マスターCSVに本名混入がないことを確認"""
        csv_path = PROJECT_ROOT / "preserved" / "data" / "MASTER_EPISODES_CURRENT.csv"
        df = pd.read_csv(csv_path, encoding="utf-8-sig")

        # 力士候補を抽出（「の」を含む人物名）
        # ただし、これは厳密な力士判定ではない（野原しのすけ等も含まれる）
        # 実際の力士はエピソード本文で判定済み（17名）

        # RIKISHI_SHIKONAリストに登録されている力士をチェック
        for shikona in RIKISHI_SHIKONA:
            # この四股名で始まり、余分な文字がある場合は本名混入
            for _, row in df.iterrows():
                name = row["person_name"]
                if name.startswith(shikona) and len(name) > len(shikona):
                    suffix = name[len(shikona) :]
                    # 末尾1-2文字の漢字の場合、本名混入の疑い
                    if 1 <= len(suffix) <= 2 and all("\u4e00" <= char <= "\u9fff" for char in suffix):
                        pytest.fail(
                            f"本名混入検出: person_id={row['person_id']}, person_name={name}, expected={shikona}"
                        )

    def test_rikishi_shikona_list_updated(self):
        """RIKISHI_SHIKONAリストが更新されていることを確認"""
        # Phase 4で追加した力士が含まれていることを確認
        assert "舞の海" in RIKISHI_SHIKONA, "舞の海が RIKISHI_SHIKONAリストに含まれていません"
        assert "土佐ノ海" in RIKISHI_SHIKONA, "土佐ノ海が RIKISHI_SHIKONAリストに含まれていません"


class TestRikishiValidationScript:
    """力士名バリデーションスクリプトのテスト"""

    def test_validate_rikishi_names_script_exists(self):
        """validate_rikishi_names.py が存在することを確認"""
        script_path = PROJECT_ROOT / "scripts" / "validation" / "validate_rikishi_names.py"
        assert script_path.exists(), "validate_rikishi_names.py が見つかりません"

    def test_fix_rikishi_display_names_script_exists(self):
        """fix_rikishi_display_names.py が存在することを確認"""
        script_path = PROJECT_ROOT / "scripts" / "fix" / "fix_rikishi_display_names.py"
        assert script_path.exists(), "fix_rikishi_display_names.py が見つかりません"
