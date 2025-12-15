#!/usr/bin/env python3
"""
最終品質検証
すべての修正が完了したエピソードの品質を総合的に確認
"""

import csv
import re
from datetime import datetime
from pathlib import Path

class FinalQualityValidator:
    """最終品質検証システム"""

    def __init__(self):
        """初期化"""
        # PDCAガーディアン RULE_164準拠
        self.date_noise_patterns = [
            r'\d{4}年\d{1,2}月\d{1,2}日',  # 年月日
            r'\d{1,2}月\d{1,2}日',          # 月日
            r'\d{4}年\d{1,2}月(?!\d)',      # 年月
            r'午前\d+時',                    # 時刻
            r'午後\d+時',                    # 時刻
            r'\d+時\d+分'                    # 時分
        ]

        # 定型文パターン（絶対に使用禁止）
        self.template_patterns = [
            r'その後も.*続け',
            r'この偉業は.*記憶され',
            r'後世.*道標',
            r'多くの.*影響を与え',
            r'今も.*語り継が',
            r'永遠に.*残',
            r'この活躍が.*新風を吹き込み',
            r'新たな可能性を切り開いた',
            r'時代を.*象徴'
        ]

        # 名詞終了チェック
        self.noun_endings = [
            '革命児', '先駆者', '開拓者', '巨人', '天才',
            'レジェンド', 'カリスマ', '英雄', '巨匠'
        ]

    def validate_episode(self, episode_text: str, person_name: str) -> dict:
        """
        エピソードを総合的に検証

        Returns:
            検証結果の辞書
        """
        violations = []
        warnings = []

        # 1. 文字数チェック（132-250文字）
        char_count = len(episode_text)
        if char_count < 132:
            violations.append(f"文字数不足: {char_count}文字（最低132文字必要）")
        elif char_count > 250:
            violations.append(f"文字数超過: {char_count}文字（最大250文字）")

        # 2. RULE_164: 日付ノイズチェック
        for pattern in self.date_noise_patterns:
            if re.search(pattern, episode_text):
                match = re.search(pattern, episode_text)
                violations.append(f"日付ノイズ検出（RULE_164違反）: '{match.group()}'")

        # 3. 定型文チェック
        for pattern in self.template_patterns:
            if re.search(pattern, episode_text):
                match = re.search(pattern, episode_text)
                violations.append(f"定型文検出: '{match.group()}'")

        # 4. 名詞終了チェック
        text_without_period = episode_text.rstrip('。')
        for noun in self.noun_endings:
            if text_without_period.endswith(noun):
                violations.append(f"文末が名詞: '{noun}。'")

        # 5. 具体的数値の有無（警告レベル）
        numbers = re.findall(r'\d+', episode_text)
        if len(numbers) < 2:
            warnings.append("具体的な数値が不足（2つ以上推奨）")

        # 6. 年齢対比の明確性
        if not re.search(r'あなたと同じ\d+歳のとき', episode_text):
            violations.append("年齢対比のフレーズがありません")

        return {
            'person_name': person_name,
            'character_count': char_count,
            'violations': violations,
            'warnings': warnings,
            'is_valid': len(violations) == 0,
            'quality_score': self.calculate_quality_score(violations, warnings)
        }

    def calculate_quality_score(self, violations: list, warnings: list) -> float:
        """品質スコアを計算（100点満点）"""
        score = 100.0

        # 違反は各-10点
        score -= len(violations) * 10

        # 警告は各-3点
        score -= len(warnings) * 3

        return max(0, score)

    def validate_all_episodes(self, csv_file: str) -> dict:
        """全エピソードを検証"""
        print("=" * 60)
        print("最終品質検証")
        print("=" * 60)
        print(f"検証ファイル: {csv_file}\n")

        results = []
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            episodes = list(reader)

        print(f"検証対象: {len(episodes)}件のエピソード\n")

        # 各エピソードを検証
        for episode in episodes:
            person_name = episode['person_name']
            episode_text = episode['episode_text']

            result = self.validate_episode(episode_text, person_name)
            results.append(result)

        # 統計を集計
        valid_count = sum(1 for r in results if r['is_valid'])
        avg_score = sum(r['quality_score'] for r in results) / len(results)

        # 違反のあるエピソードを表示
        print("【違反検出エピソード】")
        violation_count = 0
        for result in results:
            if result['violations']:
                violation_count += 1
                print(f"\n{result['person_name']}:")
                for violation in result['violations']:
                    print(f"  ❌ {violation}")

        if violation_count == 0:
            print("✅ 違反はありませんでした")

        # 警告のあるエピソードを表示
        print("\n【警告検出エピソード】")
        warning_count = 0
        for result in results:
            if result['warnings'] and not result['violations']:  # 違反がないものだけ
                warning_count += 1
                if warning_count <= 5:  # 最初の5件のみ表示
                    print(f"\n{result['person_name']}:")
                    for warning in result['warnings']:
                        print(f"  ⚠️ {warning}")

        if warning_count > 5:
            print(f"\n... 他{warning_count - 5}件の警告")

        # サマリー
        print("\n" + "=" * 60)
        print("検証結果サマリー")
        print("=" * 60)
        print(f"総エピソード数: {len(results)}")
        print(f"✅ 合格: {valid_count}件 ({valid_count/len(results)*100:.1f}%)")
        print(f"❌ 違反あり: {violation_count}件")
        print(f"⚠️ 警告のみ: {warning_count}件")
        print(f"平均品質スコア: {avg_score:.1f}/100")

        # 文字数分布
        char_counts = [r['character_count'] for r in results]
        print(f"\n文字数統計:")
        print(f"  最小: {min(char_counts)}文字")
        print(f"  最大: {max(char_counts)}文字")
        print(f"  平均: {sum(char_counts)/len(char_counts):.1f}文字")

        return {
            'total': len(results),
            'valid': valid_count,
            'violations': violation_count,
            'warnings': warning_count,
            'average_score': avg_score,
            'results': results
        }

if __name__ == "__main__":
    validator = FinalQualityValidator()

    # 最新の修正済みファイルを検証
    csv_file = 'episodes_absolute_final_20250923_142200.csv'

    validation_results = validator.validate_all_episodes(csv_file)

    # 最終判定
    print("\n" + "=" * 60)
    print("最終判定")
    print("=" * 60)

    if validation_results['violations'] == 0:
        print("🎉 すべてのエピソードが品質基準を満たしています！")
        print(f"✅ 100件のエピソードが完成しました")
        print(f"📊 平均品質スコア: {validation_results['average_score']:.1f}/100")

        # 最終版として保存
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        final_file = f'episodes_final_complete_{timestamp}.csv'

        import shutil
        shutil.copy(csv_file, final_file)
        print(f"\n📁 最終版を保存: {final_file}")
    else:
        print(f"⚠️ {validation_results['violations']}件のエピソードに違反があります")
        print("追加の修正が必要です")
