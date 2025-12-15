#!/usr/bin/env python3
"""
エピソード自動修正システム
統合検証システムの違反を自動的に修正

Author: Claude Code
Date: 2025-10-01
Version: 1.0.0
"""

import re
import csv
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
from unified_validation_system import UnifiedValidationSystem, ValidationResult, SeverityLevel


class EpisodeAutoCorrection:
    """エピソード自動修正システム"""

    def __init__(self):
        self.validator = UnifiedValidationSystem()
        self.corrections_log = []

    def remove_temporal_noise(self, text: str) -> Tuple[str, List[str]]:
        """年号・日付を削除"""
        removed = []
        patterns = [
            (r'\d{4}年', ''),
            (r'令和\d+年', ''),
            (r'平成\d+年', ''),
            (r'\d+月\d+日', ''),
            (r'\d{4}/\d{2}/\d{2}', '')
        ]

        modified_text = text
        for pattern, replacement in patterns:
            matches = re.findall(pattern, modified_text)
            if matches:
                removed.extend(matches)
                modified_text = re.sub(pattern, replacement, modified_text)

        # 余分なスペースを削除
        modified_text = re.sub(r'\s+', '', modified_text)
        modified_text = re.sub(r'、+', '、', modified_text)

        return modified_text, removed

    def remove_subjective_keywords(self, text: str) -> Tuple[str, List[str]]:
        """主観的キーワードを削除"""
        subjective_keywords = [
            "素晴らしい", "すごい", "驚異的", "圧倒的",
            "感動的", "劇的", "衝撃的", "奇跡的",
            "伝説的", "壮大な"
        ]

        removed = []
        modified_text = text

        for keyword in subjective_keywords:
            if keyword in modified_text:
                removed.append(keyword)
                # キーワードとその後の「成績」「活躍」などもセットで削除
                modified_text = modified_text.replace(f"{keyword}な", "")
                modified_text = modified_text.replace(keyword, "")

        return modified_text, removed

    def fix_duplicate_age(self, text: str) -> Tuple[str, bool]:
        """年齢の重複を修正"""
        age_pattern = r'(\d+)[歳才]'
        ages = re.findall(age_pattern, text)

        if len(ages) != len(set(ages)):
            # 重複がある場合、最初の出現のみ残す
            seen = set()
            modified_text = text
            for age in ages:
                if age in seen:
                    # 2回目以降の出現を削除
                    modified_text = re.sub(f'{age}[歳才]', '', modified_text, count=1)
                else:
                    seen.add(age)

            # 余分なスペースを削除
            modified_text = re.sub(r'\s+', '', modified_text)
            return modified_text, True

        return text, False

    def enhance_specificity(self, text: str, category: str) -> str:
        """具体性を向上（必要に応じて）"""
        # 文字数が130未満の場合、カテゴリに応じた補足を追加
        if len(text) < 130:
            # 既に適切な記述がある場合はそのまま返す
            return text

        return text

    def auto_correct_episode(self, episode: Dict) -> Tuple[Dict, List[str]]:
        """エピソードの自動修正"""
        original_text = episode['episode_text']
        modified_text = original_text
        corrections = []

        # 1. 時間的ノイズの削除
        modified_text, removed_temporal = self.remove_temporal_noise(modified_text)
        if removed_temporal:
            corrections.append(f"年号・日付削除: {', '.join(removed_temporal)}")

        # 2. 主観的キーワードの削除
        modified_text, removed_subjective = self.remove_subjective_keywords(modified_text)
        if removed_subjective:
            corrections.append(f"主観表現削除: {', '.join(removed_subjective)}")

        # 3. 年齢重複の修正
        modified_text, age_fixed = self.fix_duplicate_age(modified_text)
        if age_fixed:
            corrections.append("年齢重複を修正")

        # 4. テキストのクリーンアップ
        modified_text = re.sub(r'。+', '。', modified_text)
        modified_text = re.sub(r'、+', '、', modified_text)
        modified_text = modified_text.strip()

        # 修正されたエピソードを返す
        corrected_episode = episode.copy()
        corrected_episode['episode_text'] = modified_text
        corrected_episode['character_count'] = len(modified_text)
        corrected_episode['corrections_applied'] = corrections

        return corrected_episode, corrections

    def validate_and_correct(self, episode: Dict, max_iterations: int = 3) -> Tuple[Dict, ValidationResult, List[str]]:
        """検証と修正を反復"""
        all_corrections = []
        current_episode = episode.copy()

        for iteration in range(max_iterations):
            # 検証
            result = self.validator.validate_episode(current_episode)

            if result.is_valid:
                return current_episode, result, all_corrections

            # クリティカルな違反がある場合のみ修正
            has_critical = len(result.get_critical_violations()) > 0

            if has_critical:
                # 自動修正を実行
                corrected, corrections = self.auto_correct_episode(current_episode)

                if corrections:
                    all_corrections.extend([f"Iter{iteration+1}: {c}" for c in corrections])
                    current_episode = corrected
                else:
                    # 修正できない場合は終了
                    break
            else:
                break

        # 最終検証
        final_result = self.validator.validate_episode(current_episode)
        return current_episode, final_result, all_corrections


class BatchEpisodeCorrection:
    """バッチエピソード修正システム"""

    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self.corrector = EpisodeAutoCorrection()
        self.validator = UnifiedValidationSystem()

    def load_episodes(self) -> List[Dict]:
        """CSVからエピソードを読み込む"""
        episodes = []

        with open(self.csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, 1):
                episode = {
                    'episode_id': f"EP{idx:03d}",
                    'person_name': row.get('person_name', ''),
                    'user_age': row.get('user_age', ''),
                    'episode_age': row.get('episode_age', ''),
                    'episode_text': row.get('episode_text', ''),
                    'category': row.get('category', ''),
                    'weighted_score': float(row.get('weighted_score', 0)),
                    'original_validation': row.get('is_valid', '')
                }
                episodes.append(episode)

        print(f"✅ {len(episodes)}件のエピソードを読み込みました")
        return episodes

    def correct_all(self, episodes: List[Dict]) -> List[Tuple[Dict, ValidationResult, List[str]]]:
        """全エピソードの修正"""
        print("\n" + "=" * 80)
        print("自動修正システム実行開始")
        print("=" * 80)

        results = []

        for idx, episode in enumerate(episodes, 1):
            print(f"\n【{idx}/{len(episodes)}】{episode['person_name']}")

            # 初期検証
            initial_result = self.validator.validate_episode(episode)
            initial_status = "✅ 合格" if initial_result.is_valid else "❌ 不合格"
            print(f"  初期状態: {initial_status}")

            if not initial_result.is_valid:
                # 自動修正を実行
                corrected, final_result, corrections = self.corrector.validate_and_correct(episode)

                final_status = "✅ 合格" if final_result.is_valid else "❌ 不合格"
                print(f"  修正後: {final_status}")

                if corrections:
                    print(f"  適用された修正:")
                    for correction in corrections:
                        print(f"    - {correction}")

                results.append((corrected, final_result, corrections))
            else:
                # 合格の場合はそのまま
                results.append((episode, initial_result, []))

        return results

    def export_corrected_csv(self, results: List[Tuple[Dict, ValidationResult, List[str]]], output_path: str):
        """修正済みエピソードをCSV出力"""
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = [
                'person_name',
                'user_age',
                'episode_age',
                'episode_text',
                'character_count',
                'category',
                'weighted_score',
                'is_valid',
                'emotional_impact_score',
                'specificity_score',
                'corrections_applied',
                'created_date'
            ]

            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for episode, result, corrections in results:
                writer.writerow({
                    'person_name': episode['person_name'],
                    'user_age': episode['user_age'],
                    'episode_age': episode['episode_age'],
                    'episode_text': episode['episode_text'],
                    'character_count': len(episode['episode_text']),
                    'category': episode['category'],
                    'weighted_score': episode['weighted_score'],
                    'is_valid': 'True' if result.is_valid else 'False',
                    'emotional_impact_score': f"{result.emotional_impact_score:.2f}",
                    'specificity_score': f"{result.specificity_score:.2f}",
                    'corrections_applied': ' | '.join(corrections) if corrections else 'None',
                    'created_date': datetime.now().strftime("%Y%m%d_%H%M%S")
                })

        print(f"\n✅ 修正済みCSV出力: {output_path}")

    def print_summary(self, results: List[Tuple[Dict, ValidationResult, List[str]]]):
        """サマリー表示"""
        total = len(results)
        valid_count = sum(1 for _, result, _ in results if result.is_valid)
        corrected_count = sum(1 for _, _, corrections in results if corrections)

        print("\n" + "=" * 80)
        print("📊 修正結果サマリー")
        print("=" * 80)
        print(f"総エピソード数: {total}件")
        print(f"修正後合格: {valid_count}件 ({valid_count/total*100:.1f}%)")
        print(f"修正を実行: {corrected_count}件")
        print(f"修正後も不合格: {total - valid_count}件")

        # 平均スコア
        avg_emotional = sum(result.emotional_impact_score for _, result, _ in results) / total
        avg_specificity = sum(result.specificity_score for _, result, _ in results) / total
        print(f"\n平均感銘スコア: {avg_emotional:.2f}")
        print(f"平均具体性スコア: {avg_specificity:.2f}")

        print("=" * 80)


def main():
    """メイン実行"""
    csv_path = "/Users/admin/Documents/AIUELAB/001-final-hourglass/master/episodes_master_current.csv"

    # バッチ修正システムのインスタンス化
    batch_corrector = BatchEpisodeCorrection(csv_path)

    # エピソードの読み込み
    episodes = batch_corrector.load_episodes()

    # 全エピソードの修正
    results = batch_corrector.correct_all(episodes)

    # サマリー表示
    batch_corrector.print_summary(results)

    # 修正済みCSVの出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"episodes_auto_corrected_{timestamp}.csv"
    batch_corrector.export_corrected_csv(results, output_path)

    print("\n✅ 自動修正完了")


if __name__ == "__main__":
    main()
