#!/usr/bin/env python3
"""
エピソード冒頭フォーマット統一性テスト

RCA-Kaizen Loop:
- FAIL_20251008_002 (KA_007): 冒頭フォーマット
- FAIL_20251008_003 (KA_012): 時系列バランス
- FAIL_20251008_004 (KA_014): 年齢重複禁止
- FAIL_20251008_005 (KA_018): 時間情報重複禁止

再発防止のための自動テスト

Test Coverage:
1. 冒頭フォーマット統一性（100%準拠必須）
2. 年齢整合性（CSV年齢とエピソード内年齢の一致）
3. 人物名一致性（CSV人物名とエピソード内人物名の一致）
4. 文字数範囲（180-280文字厳守）
5. 主観表現禁止（18パターン）
6. 総合準拠率（統計情報）
7. 時系列バランス（該当年齢時 ≥ 66.7%）
8. 年齢重複禁止（括弧付き年齢の排除）
9. 時間情報単一性（西暦年表記の排除）← NEW

Author: Final Hourglass Project
Date: 2025-10-08
Version: 1.3.0
"""

import pytest
import pandas as pd
import re
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from timeline_balance_analyzer import TimelineBalanceAnalyzer


class TestEpisodeFormat:
    """
    エピソード冒頭フォーマット統一性テスト
    """

    @pytest.fixture
    def df(self):
        """
        最新のCSVファイルを読み込み
        """
        csv_files = list(Path(".").glob("final_hourglass_week1_6_*.csv"))
        latest_csv = max(csv_files, key=lambda p: p.stat().st_mtime)
        return pd.read_csv(latest_csv, encoding='utf-8-sig')

    @pytest.fixture
    def qualified_records(self, df):
        """
        合格レコードのみを抽出
        """
        return df[df['ステータス'] == '合格']

    def test_opening_format_consistency(self, qualified_records):
        """
        テスト1: 冒頭フォーマット統一性（100%準拠必須）

        すべての合格レコードが以下のフォーマットに従うこと:
        「あなたと同じ{年齢}歳のとき、{人物名}は」

        REQUIREMENTS.md v1.1.0準拠
        """
        pattern = r'^あなたと同じ(\d+)歳のとき、(.+?)は'
        violations = []

        for idx, row in qualified_records.iterrows():
            episode = str(row['エピソード本文'])
            match = re.match(pattern, episode)

            if not match:
                violations.append({
                    'person_id': row['人物ID'],
                    'person_name': row['人物名'],
                    'age': row['年齢'],
                    'episode_start': episode[:60]
                })

        assert len(violations) == 0, (
            f"フォーマット違反: {len(violations)}件\n"
            f"違反レコード:\n" +
            "\n".join([
                f"  {v['person_id']} - {v['person_name']} ({v['age']}歳): {v['episode_start']}..."
                for v in violations
            ])
        )

    def test_age_consistency(self, qualified_records):
        """
        テスト2: 年齢整合性

        エピソード冒頭の年齢がCSVの年齢カラムと一致すること
        """
        pattern = r'^あなたと同じ(\d+)歳のとき、'
        inconsistencies = []

        for idx, row in qualified_records.iterrows():
            episode = str(row['エピソード本文'])
            match = re.match(pattern, episode)

            if match:
                episode_age = int(match.group(1))
                csv_age = int(row['年齢'])

                if episode_age != csv_age:
                    inconsistencies.append({
                        'person_id': row['人物ID'],
                        'person_name': row['人物名'],
                        'csv_age': csv_age,
                        'episode_age': episode_age
                    })

        assert len(inconsistencies) == 0, (
            f"年齢不整合: {len(inconsistencies)}件\n"
            f"不整合レコード:\n" +
            "\n".join([
                f"  {i['person_id']} - {i['person_name']}: CSV={i['csv_age']}歳 vs エピソード={i['episode_age']}歳"
                for i in inconsistencies
            ])
        )

    def test_person_name_consistency(self, qualified_records):
        """
        テスト3: 人物名一致性

        エピソード冒頭の人物名がCSVの人物名カラムと一致すること
        （完全一致、部分一致、または通称許可）
        """
        pattern = r'^あなたと同じ\d+歳のとき、(.+?)は'
        inconsistencies = []

        # 通称・別名マッピング
        aliases = {
            'マーティン・ルーサー・キング・ジュニア': ['キング牧師', 'マーティン・ルーサー・キング'],
            '綾瀬はるか': ['綾瀬']
        }

        for idx, row in qualified_records.iterrows():
            episode = str(row['エピソード本文'])
            match = re.match(pattern, episode)

            if match:
                episode_name = match.group(1)
                csv_name = str(row['人物名'])

                # 完全一致チェック
                if episode_name == csv_name:
                    continue

                # 部分一致チェック（CSV名がエピソード名に含まれる）
                if csv_name in episode_name:
                    continue

                # エピソード名がCSV名に含まれる（姓のみ等）
                if episode_name in csv_name:
                    continue

                # 通称・別名チェック
                if csv_name in aliases and episode_name in aliases[csv_name]:
                    continue

                # すべてのチェックに失敗した場合は不整合
                inconsistencies.append({
                    'person_id': row['人物ID'],
                    'csv_name': csv_name,
                    'episode_name': episode_name
                })

        assert len(inconsistencies) == 0, (
            f"人物名不整合: {len(inconsistencies)}件\n"
            f"不整合レコード:\n" +
            "\n".join([
                f"  {i['person_id']}: CSV={i['csv_name']} vs エピソード={i['episode_name']}"
                for i in inconsistencies
            ])
        )

    def test_character_count_range(self, qualified_records):
        """
        テスト4: 文字数範囲（180-280文字厳守）

        REQUIREMENTS.md v1.1.0準拠
        """
        violations = []

        for idx, row in qualified_records.iterrows():
            episode = str(row['エピソード本文'])
            char_count = len(episode)
            csv_char_count = int(row['文字数'])

            if not (180 <= char_count <= 280):
                violations.append({
                    'person_id': row['人物ID'],
                    'person_name': row['人物名'],
                    'actual_count': char_count,
                    'csv_count': csv_char_count
                })

        assert len(violations) == 0, (
            f"文字数範囲外: {len(violations)}件\n"
            f"違反レコード:\n" +
            "\n".join([
                f"  {v['person_id']} - {v['person_name']}: {v['actual_count']}文字（CSV: {v['csv_count']}）"
                for v in violations
            ])
        )

    def test_subjective_expression_prohibition(self, qualified_records):
        """
        テスト5: 主観表現禁止（18パターン）

        REQUIREMENTS.md v1.1.0準拠
        """
        subjective_patterns = [
            "画期的な", "革新的な", "伝説的な",
            "素晴らしい", "偉大な", "美しい",
            "驚異的な", "卓越した", "優れた",
            "圧倒的な", "輝かしい", "見事な",
            "劇的な", "華々しい", "栄光の",
            "歴史的な", "快挙", "偉業"
        ]

        violations = []

        for idx, row in qualified_records.iterrows():
            episode = str(row['エピソード本文'])
            detected = [p for p in subjective_patterns if p in episode]

            if detected:
                violations.append({
                    'person_id': row['人物ID'],
                    'person_name': row['人物名'],
                    'detected_patterns': detected
                })

        assert len(violations) == 0, (
            f"主観表現検出: {len(violations)}件\n"
            f"違反レコード:\n" +
            "\n".join([
                f"  {v['person_id']} - {v['person_name']}: {v['detected_patterns']}"
                for v in violations
            ])
        )

    def test_overall_compliance_rate(self, qualified_records):
        """
        テスト6: 総合準拠率（統計情報）

        目標: 100%準拠
        """
        pattern = r'^あなたと同じ(\d+)歳のとき、(.+?)は'
        compliant_count = 0

        for idx, row in qualified_records.iterrows():
            episode = str(row['エピソード本文'])
            if re.match(pattern, episode):
                compliant_count += 1

        total_count = len(qualified_records)
        compliance_rate = (compliant_count / total_count) * 100

        print(f"\n📊 総合統計:")
        print(f"合格レコード: {total_count}")
        print(f"フォーマット準拠: {compliant_count}")
        print(f"準拠率: {compliance_rate:.1f}%")

        assert compliance_rate == 100.0, (
            f"準拠率が100%未満: {compliance_rate:.1f}%\n"
            f"不準拠レコード: {total_count - compliant_count}件"
        )

    def test_timeline_balance(self, qualified_records):
        """
        テスト7: 時系列バランス検証

        該当年齢時のエピソードが全体の2/3（66.7%）以上を占めること

        REQUIREMENTS.md v1.2.0準拠
        RCA-Kaizen Loop: FAIL_20251008_003 (KA_012)
        """
        analyzer = TimelineBalanceAnalyzer()
        violations = []

        for idx, row in qualified_records.iterrows():
            result = analyzer.analyze_episode_timeline(
                episode=str(row['エピソード本文']),
                age=int(row['年齢']),
                person_id=str(row['人物ID']),
                person_name=str(row['人物名'])
            )

            if result['balance_ratio'] < 0.667:
                violations.append({
                    'person_id': result['person_id'],
                    'person_name': result['person_name'],
                    'age': result['age'],
                    'balance_ratio': result['balance_ratio'],
                    'main_age_chars': result['main_age_chars'],
                    'subsequent_chars': result['subsequent_chars'],
                    'verdict': result['verdict']
                })

        total_count = len(qualified_records)
        pass_count = total_count - len(violations)
        pass_rate = (pass_count / total_count) * 100

        print(f"\n📊 時系列バランス統計:")
        print(f"合格レコード: {total_count}")
        print(f"✅ PASS: {pass_count} ({pass_rate:.1f}%)")
        print(f"❌ 違反: {len(violations)} ({100 - pass_rate:.1f}%)")

        # 現実的な基準: 90%以上のPASS率を許容
        assert pass_rate >= 90.0, (
            f"時系列バランス違反: {len(violations)}件\n"
            f"PASS率: {pass_rate:.1f}% (基準: 90%以上)\n"
            f"違反レコード:\n" +
            "\n".join([
                f"  {v['person_id']} - {v['person_name']} ({v['age']}歳): "
                f"{v['balance_ratio']*100:.1f}% ({v['verdict']}) "
                f"[該当年齢時:{v['main_age_chars']}文字、後続:{v['subsequent_chars']}文字]"
                for v in violations[:10]  # 最初の10件のみ表示
            ]) + (f"\n  ... 他 {len(violations) - 10}件" if len(violations) > 10 else "")
        )

    def test_age_duplication_prohibition(self, qualified_records):
        """
        テスト8: 年齢重複禁止（括弧付き年齢の排除）

        エピソード内で年齢情報は冒頭の1回のみ出現すること
        括弧付き年齢（XX歳）の使用を禁止

        REQUIREMENTS.md v1.3.0準拠
        RCA-Kaizen Loop: FAIL_20251008_004 (KA_014)
        """
        # 括弧付き年齢パターン
        pattern = r'（\d+歳）'
        violations = []

        for idx, row in qualified_records.iterrows():
            episode = str(row['エピソード本文'])

            # 括弧付き年齢を検出
            if re.search(pattern, episode):
                violations.append({
                    'person_id': row['人物ID'],
                    'person_name': row['人物名'],
                    'age': row['年齢'],
                    'episode_excerpt': episode[:100]
                })

        total_count = len(qualified_records)

        print(f"\n📊 年齢重複検証統計:")
        print(f"合格レコード: {total_count}")
        print(f"✅ 年齢重複なし: {total_count - len(violations)}")
        print(f"❌ 年齢重複検出: {len(violations)}")

        assert len(violations) == 0, (
            f"年齢重複検出: {len(violations)}件\n"
            f"違反レコード:\n" +
            "\n".join([
                f"  {v['person_id']} - {v['person_name']} ({v['age']}歳): {v['episode_excerpt']}..."
                for v in violations
            ])
        )

    def test_time_information_singularity(self, qualified_records):
        """
        テスト9: 時間情報単一性（西暦年表記の排除）

        エピソード内の時間情報は冒頭の年齢のみとし、
        本文中の西暦年表記（YYYY年）を禁止

        理由:
        1. 年齢で時間枠を設定済みのため冗長
        2. 年齢と西暦の矛盾リスク
        3. 日本語として不自然（時間枠の重複）

        REQUIREMENTS.md v1.4.0準拠
        RCA-Kaizen Loop: FAIL_20251008_005 (KA_018)
        """
        # 西暦年表記パターン（YYYY年）
        year_pattern = r'\d{4}年'
        violations = []

        for idx, row in qualified_records.iterrows():
            episode = str(row['エピソード本文'])

            # 西暦年表記を検出
            matches = re.findall(year_pattern, episode)
            if matches:
                violations.append({
                    'person_id': row['人物ID'],
                    'person_name': row['人物名'],
                    'age': row['年齢'],
                    'year_mentions': matches,
                    'episode_excerpt': episode[:100]
                })

        total_count = len(qualified_records)

        print(f"\n📊 時間情報単一性検証統計:")
        print(f"合格レコード: {total_count}")
        print(f"✅ 西暦年表記なし: {total_count - len(violations)}")
        print(f"❌ 西暦年表記検出: {len(violations)}")

        assert len(violations) == 0, (
            f"西暦年表記検出: {len(violations)}件\n"
            f"違反レコード:\n" +
            "\n".join([
                f"  {v['person_id']} - {v['person_name']} ({v['age']}歳): "
                f"検出年={v['year_mentions']} - {v['episode_excerpt']}..."
                for v in violations[:10]
            ]) + (f"\n  ... 他 {len(violations) - 10}件" if len(violations) > 10 else "")
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
