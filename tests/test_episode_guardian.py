#!/usr/bin/env python3
"""
EpisodeGuardianテストスイート

EP010グループ混入問題の再発防止テストを含む

著者: Claude Code
日付: 2025-10-01
バージョン: 1.0.0
"""

import sys
import unittest
from pathlib import Path

# プロジェクトルートをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from episode_guardian import (
    EpisodeGuardian,
    EntityTypeValidator,
    Severity,
    ValidationResult,
    create_episode_guardian
)
from episode_guardian_rules import (
    ENTITY_TYPE_RULES,
    FORMAT_RULES,
    CONTENT_RULES,
    ALL_RULES,
    get_rule,
    get_critical_rules
)


class TestEntityTypeValidator(unittest.TestCase):
    """Entity Type検証のテスト"""

    def setUp(self):
        """各テストの前処理"""
        self.known_groups = {
            'サカナクション', 'X JAPAN', 'SEKAI NO OWARI',
            'BTS', 'GLAY', "B'z", 'Mr.Children', '嵐'
        }
        self.validator = EntityTypeValidator(self.known_groups)

    def test_entity_type_001_group_blacklist_fail(self):
        """ENTITY_TYPE_001: グループ名ブラックリスト（失格）"""
        episode = {
            'person_name': 'サカナクション',
            'episode_age': 5,
            'episode_text': 'あなたと同じ5歳のとき、サカナクションは結成5年目を迎えた。',
            'category': '音楽'
        }

        result = self.validator.validate(episode)

        self.assertFalse(result.is_valid)
        self.assertEqual(result.severity, Severity.CRITICAL)
        self.assertIn('ENTITY_TYPE_001', result.failed_rules)
        self.assertIn('グループです', result.message)

    def test_entity_type_001_person_pass(self):
        """ENTITY_TYPE_001: 個人名（合格）"""
        episode = {
            'person_name': '羽生結弦',
            'episode_age': 19,
            'episode_text': 'あなたと同じ19歳のとき、羽生結弦はソチ五輪で金メダルを獲得した。',
            'category': 'スポーツ'
        }

        result = self.validator.validate(episode)

        self.assertTrue(result.is_valid)

    def test_all_known_groups_fail(self):
        """すべての既知グループが失格することを確認"""
        test_groups = [
            'サカナクション', 'X JAPAN', 'SEKAI NO OWARI',
            'BTS', 'GLAY', "B'z", 'Mr.Children', '嵐'
        ]

        for group_name in test_groups:
            with self.subTest(group=group_name):
                episode = {
                    'person_name': group_name,
                    'episode_age': 5,
                    'episode_text': f'あなたと同じ5歳のとき、{group_name}は活動を開始した。',
                    'category': '音楽'
                }

                result = self.validator.validate(episode)

                self.assertFalse(result.is_valid, f"{group_name} should fail validation")
                self.assertEqual(result.severity, Severity.CRITICAL)
                self.assertIn('ENTITY_TYPE_001', result.failed_rules)

    def test_entity_type_002_group_keywords_warning(self):
        """ENTITY_TYPE_002: グループ特有表現検出（警告）"""
        episode = {
            'person_name': '不明なアーティスト',
            'episode_age': 5,
            'episode_text': 'あなたと同じ5歳のとき、4人組のバンドとしてメジャーデビューした。',
            'category': '音楽'
        }

        result = self.validator.validate(episode)

        # グループ関連表現が2つ以上ある場合は警告
        if not result.is_valid:
            self.assertEqual(result.severity, Severity.WARNING)
            self.assertIn('ENTITY_TYPE_002', result.failed_rules)

    def test_entity_type_003_person_name_pattern_japanese(self):
        """ENTITY_TYPE_003: 日本人名パターン（合格）"""
        valid_names = ['羽生結弦', '大谷翔平', '錦織圭', '石川佳純']

        for name in valid_names:
            with self.subTest(name=name):
                episode = {
                    'person_name': name,
                    'episode_age': 20,
                    'episode_text': f'あなたと同じ20歳のとき、{name}は活躍した。',
                    'category': 'スポーツ'
                }

                result = self.validator.validate(episode)
                self.assertTrue(result.is_valid)

    def test_entity_type_003_person_name_pattern_western(self):
        """ENTITY_TYPE_003: 海外人名パターン（合格）"""
        valid_names = ['Ichiro Suzuki', 'Naomi Osaka', 'Shohei Ohtani']

        for name in valid_names:
            with self.subTest(name=name):
                episode = {
                    'person_name': name,
                    'episode_age': 20,
                    'episode_text': f'あなたと同じ20歳のとき、{name}は活躍した。',
                    'category': 'スポーツ'
                }

                result = self.validator.validate(episode)
                self.assertTrue(result.is_valid)


class TestEpisodeGuardian(unittest.TestCase):
    """EpisodeGuardian統合テスト"""

    def setUp(self):
        """各テストの前処理"""
        self.guardian = create_episode_guardian()

    def test_ep010_regression_sakanaction_fail(self):
        """
        EP010リグレッションテスト: サカナクション（グループ）が失格することを確認

        これはEP010グループ混入問題の再発を防ぐための重要なテストです。
        """
        episode = {
            'episode_id': 'EP010',
            'person_name': 'サカナクション',
            'episode_age': 5,
            'episode_text': 'あなたと同じ5歳のとき、サカナクションは結成から5年でじ活動5年目のとき、アルクアラウンドをリリースした。',
            'category': '音楽',
            'user_age': 5
        }

        result = self.guardian.validate_episode(episode)

        # 絶対に失格しなければならない
        self.assertFalse(result.is_valid, "サカナクション（グループ）は必ず失格すべき")
        self.assertEqual(result.severity, Severity.CRITICAL)
        self.assertIn('ENTITY_TYPE_001', result.failed_rules)
        self.assertIn('グループです', result.message)

    def test_ep010_new_yuzuru_hanyu_pass(self):
        """EP010新エピソード: 羽生結弦（個人）が合格することを確認"""
        episode = {
            'episode_id': 'EP010',
            'person_name': '羽生結弦',
            'episode_age': 19,
            'episode_text': 'あなたと同じ19歳のとき、羽生結弦はソチ五輪でフィギュアスケート男子シングル金メダルを獲得した。ショートプログラム101.45点、フリー178.64点の合計280.09点で世界最高得点を更新。日本男子66年ぶりの五輪金メダリストとなり、4回転ジャンプ3本を完璧に成功させた。',
            'category': 'スポーツ',
            'user_age': 19
        }

        result = self.guardian.validate_episode(episode)

        # 個人なので合格すべき
        self.assertTrue(result.is_valid, "羽生結弦（個人）は合格すべき")

    def test_multiple_groups_all_fail(self):
        """複数のグループがすべて失格することを確認"""
        test_cases = [
            ('サカナクション', 'EP010の元データ'),
            ('X JAPAN', 'ロックバンド'),
            ('嵐', 'アイドルグループ'),
            ('BTS', 'K-POPグループ'),
            ('Mr.Children', 'ロックバンド')
        ]

        for group_name, description in test_cases:
            with self.subTest(group=group_name, description=description):
                episode = {
                    'person_name': group_name,
                    'episode_age': 5,
                    'episode_text': f'あなたと同じ5歳のとき、{group_name}は活動を始めた。',
                    'category': '音楽',
                    'user_age': 5
                }

                result = self.guardian.validate_episode(episode)

                self.assertFalse(result.is_valid, f"{group_name}（{description}）は失格すべき")
                self.assertEqual(result.severity, Severity.CRITICAL)

    def test_validation_order_entity_type_first(self):
        """検証順序: Entity Typeが最優先で実行されることを確認"""
        # グループ名 + 形式エラー（文字数不足）のエピソード
        episode = {
            'person_name': 'サカナクション',
            'episode_age': 5,
            'episode_text': '短すぎるテキスト',  # 130文字未満
            'category': '音楽',
            'user_age': 5
        }

        result = self.guardian.validate_episode(episode)

        # Entity Typeエラーが最優先で検出されるべき
        self.assertFalse(result.is_valid)
        self.assertEqual(result.severity, Severity.CRITICAL)
        self.assertIn('ENTITY_TYPE_001', result.failed_rules)
        # 形式エラーは検出されない（Entity Typeで即座に失格）

    def test_metrics_tracking(self):
        """メトリクス追跡機能の確認"""
        # メトリクスをリセット
        self.guardian.reset_metrics()

        # 失格エピソード（グループ）
        fail_episode = {
            'person_name': 'サカナクション',
            'episode_age': 5,
            'episode_text': 'あなたと同じ5歳のとき、サカナクションは結成5年目を迎えた。メジャーデビュー後、数々のヒット曲を生み出し、音楽シーンに大きな影響を与えた。',
            'category': '音楽',
            'user_age': 5
        }

        result = self.guardian.validate_episode(fail_episode)

        # グループは必ず失格
        self.assertFalse(result.is_valid)

        metrics = self.guardian.get_metrics()

        # 最低限の検証: グループが検出されたこと
        self.assertGreaterEqual(metrics['total_validations'], 1)
        self.assertGreaterEqual(metrics['failed_validations'], 1)
        self.assertGreaterEqual(metrics['entity_type_failures'], 1)
        self.assertGreaterEqual(len(metrics['group_detections']), 1)
        self.assertEqual(metrics['group_detections'][0]['name'], 'サカナクション')


class TestRuleDefinitions(unittest.TestCase):
    """ルール定義のテスト"""

    def test_all_rules_exist(self):
        """すべてのルールが定義されていることを確認"""
        expected_rules = [
            'ENTITY_TYPE_001', 'ENTITY_TYPE_002', 'ENTITY_TYPE_003',
            'FORMAT_001', 'FORMAT_002', 'FORMAT_003', 'FORMAT_004',
            'CONTENT_001', 'CONTENT_002', 'CONTENT_003'
        ]

        for rule_id in expected_rules:
            with self.subTest(rule=rule_id):
                rule = get_rule(rule_id)
                self.assertIsNotNone(rule, f"{rule_id} should be defined")
                self.assertIn('name', rule)
                self.assertIn('severity', rule)
                self.assertIn('description', rule)

    def test_critical_rules(self):
        """CRITICALルールが正しく定義されていることを確認"""
        critical_rules = get_critical_rules()

        # ENTITY_TYPE_001はCRITICAL
        self.assertIn('ENTITY_TYPE_001', critical_rules)

        # FORMAT_001-004はCRITICAL
        self.assertIn('FORMAT_001', critical_rules)

        # CONTENT_001-003はCRITICAL
        self.assertIn('CONTENT_001', critical_rules)


class TestIntegration(unittest.TestCase):
    """統合テスト"""

    def setUp(self):
        """各テストの前処理"""
        self.guardian = create_episode_guardian()

    def test_ep025_regression_future_achievement_contamination(self):
        """
        EP025リグレッションテスト: 未来の成果混入を検出
        "後にファッション通販ZOZOTOWNへと展開"のような未来の成果を検出
        """
        # 修正前のEP025（未来の成果混入）
        old_ep025 = {
            'episode_id': 'EP025',
            'person_name': '前澤友作',
            'episode_age': 23,
            'episode_text': 'あなたと同じ23歳のとき、前澤友作は有限会社スタートトゥデイを設立。音楽CDのオンライン販売から始め、後にファッション通販ZOZOTOWNへと展開。時価総額1兆円企業に成長させ、日本のEC市場に革命をもたらした。ZOZO前澤ファンド設立で100億円規模の起業家支援も開始した。',
            'category': 'ビジネス'
        }

        result = self.guardian.validate_episode(old_ep025)

        # 未来の成果混入は失格（CONTENT_005違反）
        self.assertFalse(result.is_valid)
        self.assertEqual(result.severity, Severity.CRITICAL)
        self.assertIn('CONTENT_005', result.failed_rules)

    def test_ep025_corrected_passes_validation(self):
        """
        EP025修正版: 定番エピソード（ZOZOTOWN開設）で合格
        """
        # 修正後のEP025（ZOZOTOWN開設、29歳）
        new_ep025 = {
            'episode_id': 'EP025',
            'person_name': '前澤友作',
            'episode_age': 29,
            'episode_text': 'あなたと同じ29歳のとき、前澤友作はZOZOTOWNを開設した。17のインターネットセレクトショップを集積した日本初のファッション通販モールとして、彼がこだわった「ファッションの街」をイメージしたサイト設計を実現。アパレルEC市場に革命をもたらし、スタートトゥデイの事業転換の成功例となった。',
            'category': 'ビジネス'
        }

        result = self.guardian.validate_episode(new_ep025)

        # 修正版は合格
        self.assertTrue(result.is_valid)

    def test_ep028_regression_future_achievement_contamination(self):
        """
        EP028リグレッションテスト: 未来の成果混入を検出
        "その後、『火花』で芥川賞を受賞し累計300万部"のような未来の成果を検出
        """
        # 修正前のEP028（未来の成果混入）
        old_ep028 = {
            'episode_id': 'EP028',
            'person_name': '又吉直樹',
            'episode_age': 23,
            'episode_text': 'お笑いコンビ「ピース」を綾部祐二と結成し、M-1グランプリで準優勝を果たし賞金500万円を獲得。当時から文学への傾倒が深く、小説の習作を重ねながら芸人活動を続けた。その後、お笑い芸人の世界を描いた『火花』で第153回芥川龍之介賞を受賞し累計300万部を突破する大ヒット。続く『劇場』も50万部のベストセラーとなり、芸人と作家の二足のわらじを履く稀有な存在として文芸界に新風を吹き込んだ。',
            'category': 'エンターテインメント'
        }

        result = self.guardian.validate_episode(old_ep028)

        # 未来の成果混入は失格（CONTENT_005違反）
        self.assertFalse(result.is_valid)
        self.assertEqual(result.severity, Severity.CRITICAL)
        self.assertIn('CONTENT_005', result.failed_rules)

    def test_ep028_corrected_passes_validation(self):
        """
        EP028修正版: 定番エピソード（芥川賞受賞）で合格
        """
        # 修正後のEP028（芥川賞受賞、35歳）
        new_ep028 = {
            'episode_id': 'EP028',
            'person_name': '又吉直樹',
            'episode_age': 35,
            'episode_text': 'あなたと同じ35歳のとき、又吉直樹は『火花』で第153回芥川龍之介賞を受賞した。お笑い芸人として活動しながら10年以上書き続けた小説が、文芸界最高峰の賞を獲得。芸人が芥川賞作家となった史上初の快挙として文学界に衝撃を与え、純文学作品としては異例の発行部数を記録。お笑いと文学の境界を打ち破った。',
            'category': 'エンターテインメント'
        }

        result = self.guardian.validate_episode(new_ep028)

        # 修正版は合格
        self.assertTrue(result.is_valid)

    def test_ep054_regression_old_version_fail(self):
        """
        EP054リグレッションテスト: 旧版（未来の成果混入）は失格

        問題:
        1. 年齢19歳だがエピソードは35歳のもの（逃げ恥・恋）
        2. 累積成果混入: 「配信200万ダウンロード、YouTube再生2億回」
        3. 累積成果混入: 「紅白歌合戦3回出場」
        4. 累積成果混入: 「俳優として映画20本出演」
        5. 文法エラー: 「活動この楽曲は」
        """
        old_ep054 = {
            'episode_id': 'EP054',
            'person_name': '星野源',
            'episode_age': 19,
            'episode_text': 'あなたと同じ19歳のとき、星野源はSAKEROCK結成、インストバンドとして活動この楽曲は時代の象徴となり、多くのリスナーの心に深く刻まれた。音楽と演技の二刀流で新境地を開拓。『恋』は配信200万ダウンロード、YouTube再生2億回。紅白歌合戦3回出場。俳優として映画20本出演。',
            'category': '音楽'
        }

        result = self.guardian.validate_episode(old_ep054)

        # CONTENT_005（未来の成果）で失格すべき
        self.assertFalse(result.is_valid)
        self.assertEqual(result.severity, Severity.CRITICAL)
        self.assertIn('CONTENT_005', result.failed_rules)

        # 検出された違反パターンを確認
        self.assertIn('200万', result.message)  # 配信200万

    def test_ep054_new_version_pass(self):
        """
        EP054リグレッションテスト: 新版（35歳、逃げ恥エピソード）は合格

        修正内容:
        1. 年齢: 19歳 → 35歳
        2. エピソード: SAKEROCK → 逃げ恥主演 + 恋発売
        3. すべての未来の成果を削除
        4. 2016年時点の具体的事実のみを記述
        """
        new_ep054 = {
            'episode_id': 'EP054',
            'person_name': '星野源',
            'episode_age': 35,
            'episode_text': 'あなたと同じ35歳のとき、星野源は大ヒットドラマ『逃げるは恥だが役に立つ』で主演を務め、自身が作曲した主題歌『恋』を発売した。シングル『恋』は同ドラマの主題歌として社会現象となり、オリコンチャート最高2位を記録。ドラマは平均視聴率14.2%、最終回は20.8%を記録し、「恋ダンス」が大ブームとなった。音楽家・俳優として二刀流で活躍し、ドラマと楽曲の相乗効果で国民的スターの地位を確立した。',
            'category': '音楽'
        }

        result = self.guardian.validate_episode(new_ep054)

        # 修正版は合格
        self.assertTrue(result.is_valid)

    def test_complete_validation_flow(self):
        """完全な検証フローのテスト"""
        # 理想的なエピソード
        perfect_episode = {
            'episode_id': 'EP999',
            'person_name': '羽生結弦',
            'episode_age': 19,
            'episode_text': 'あなたと同じ19歳のとき、羽生結弦はソチ五輪でフィギュアスケート男子シングル金メダルを獲得した。ショートプログラム101.45点、フリー178.64点の合計280.09点で世界最高得点を更新。日本男子66年ぶりの五輪金メダリストとなり、4回転ジャンプ3本を完璧に成功させた。',
            'category': 'スポーツ',
            'user_age': 19
        }

        result = self.guardian.validate_episode(perfect_episode)

        # すべての検証を通過すべき
        self.assertTrue(result.is_valid)
        self.assertEqual(result.message, 'すべての検証を通過')


def run_regression_tests():
    """リグレッションテストのみを実行"""
    suite = unittest.TestSuite()
    suite.addTest(TestEpisodeGuardian('test_ep010_regression_sakanaction_fail'))
    suite.addTest(TestEpisodeGuardian('test_ep010_new_yuzuru_hanyu_pass'))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    return result.wasSuccessful()


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='EpisodeGuardianテストスイート')
    parser.add_argument(
        '--regression-only',
        action='store_true',
        help='EP010リグレッションテストのみを実行'
    )
    args = parser.parse_args()

    if args.regression_only:
        print("=" * 80)
        print("EP010リグレッションテスト実行")
        print("=" * 80)
        success = run_regression_tests()
        sys.exit(0 if success else 1)
    else:
        unittest.main()
