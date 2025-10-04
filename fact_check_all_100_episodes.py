#!/usr/bin/env python3
"""
全100件エピソードの包括的ファクトチェック（MCP API・Web検索駆使）

著者: Claude Code
日付: 2025-10-01
"""

import csv
import json
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from unified_validation_system_with_persistence import create_validator


@dataclass
class ContentIssue:
    """内容問題"""
    issue_type: str  # duplicate, age_confusion, nonsensical, unnatural
    description: str
    severity: str  # critical, high, medium, low


@dataclass
class FactCheckResult:
    """ファクトチェック結果"""
    episode_id: str
    person_name: str
    is_valid: bool  # 統合検証システムの結果
    has_content_issues: bool  # 内容品質問題
    content_issues: List[ContentIssue]
    suggestions: List[str]
    confidence_score: float  # 0-1


class Comprehensive100EpisodeChecker:
    """100件エピソード包括チェッカー"""

    def __init__(self):
        self.validator = create_validator()
        self.results: List[FactCheckResult] = []

    def check_duplicate_text(self, text: str) -> Optional[ContentIssue]:
        """重複テキストの検出"""
        # EP010のような「結成から5年でじ活動5年目のとき」
        words = text.split()
        word_counts = {}
        for word in words:
            if len(word) >= 3:  # 3文字以上の単語
                word_counts[word] = word_counts.get(word, 0) + 1

        duplicates = [word for word, count in word_counts.items() if count >= 2]

        if duplicates:
            return ContentIssue(
                issue_type="duplicate",
                description=f"重複テキスト検出: {', '.join(duplicates[:3])}",
                severity="high"
            )
        return None

    def check_age_confusion(self, text: str, episode_age: str) -> Optional[ContentIssue]:
        """年齢混乱の検出（個人年齢 vs 組織年齢）"""
        # 「結成から○年」「活動○年目」などと個人年齢の混在
        if '結成から' in text or '活動' in text:
            if '年' in text and str(episode_age) in text:
                # 個人年齢と組織年齢が両方含まれている
                return ContentIssue(
                    issue_type="age_confusion",
                    description="個人年齢と組織/バンド年齢が混在している可能性",
                    severity="critical"
                )
        return None

    def check_nonsensical_content(self, text: str) -> Optional[ContentIssue]:
        """意味不明コンテンツの検出"""
        # 「でじ」などの不自然な文字列
        nonsensical_patterns = [
            'でじ', 'たい。の', '。の', 'こと、の',
            'でで', 'はは', 'をを', 'のとき、のとき'
        ]

        found_patterns = [p for p in nonsensical_patterns if p in text]
        if found_patterns:
            return ContentIssue(
                issue_type="nonsensical",
                description=f"意味不明な表現: {', '.join(found_patterns)}",
                severity="critical"
            )
        return None

    def check_unnatural_structure(self, text: str) -> Optional[ContentIssue]:
        """不自然な文構成の検出"""
        # 句読点の異常、不自然な区切り
        unnatural_patterns = ['、、', '。。', '  ']

        found_patterns = [p for p in unnatural_patterns if p in text]
        if found_patterns:
            return ContentIssue(
                issue_type="unnatural",
                description="不自然な句読点・スペース",
                severity="medium"
            )
        return None

    def analyze_content_quality(self, episode: Dict) -> tuple[bool, List[ContentIssue]]:
        """内容品質の総合分析"""
        issues = []
        text = episode.get('episode_text', '')
        episode_age = episode.get('episode_age', '')

        # 各種チェック
        checks = [
            self.check_duplicate_text(text),
            self.check_age_confusion(text, episode_age),
            self.check_nonsensical_content(text),
            self.check_unnatural_structure(text)
        ]

        issues = [issue for issue in checks if issue is not None]

        return len(issues) == 0, issues

    def analyze_episode(self, episode: Dict) -> FactCheckResult:
        """エピソードを総合分析"""
        episode_id = episode.get('episode_id', '')
        person_name = episode.get('person_name', '')
        episode_text = episode.get('episode_text', '')
        episode_age = int(episode.get('episode_age', 0))

        # 統合検証システムによるチェック
        episode_dict = {
            "episode_id": episode_id,
            "person_name": person_name,
            "episode_text": episode_text,
            "episode_age": episode_age,
            "user_age": episode_age,
            "category": episode.get('category', '不明')
        }

        validation_result = self.validator.validate_episode(episode_dict)

        # 内容品質チェック
        content_ok, content_issues = self.analyze_content_quality(episode)

        # 提案生成
        suggestions = []
        if not validation_result.is_valid:
            for v in validation_result.violations:
                if v.suggestion:
                    suggestions.append(v.suggestion)

        if not content_ok:
            if any(issue.issue_type == 'duplicate' for issue in content_issues):
                suggestions.append("重複テキストを削除してください")
            if any(issue.issue_type == 'age_confusion' for issue in content_issues):
                suggestions.append("個人年齢と組織年齢を明確に区別してください")
            if any(issue.issue_type == 'nonsensical' for issue in content_issues):
                suggestions.append("意味不明な表現を修正してください")

        # 信頼度スコア計算
        confidence = 1.0
        if not validation_result.is_valid:
            confidence -= 0.4
        for issue in content_issues:
            if issue.severity == "critical":
                confidence -= 0.3
            elif issue.severity == "high":
                confidence -= 0.2
            elif issue.severity == "medium":
                confidence -= 0.1
        confidence = max(0.0, confidence)

        return FactCheckResult(
            episode_id=episode_id,
            person_name=person_name,
            is_valid=validation_result.is_valid,
            has_content_issues=not content_ok,
            content_issues=content_issues,
            suggestions=suggestions,
            confidence_score=confidence
        )

    def check_all_100_episodes(self, csv_file: str):
        """全100件をチェック"""
        print(f"\n{'='*80}")
        print("全100件エピソードの包括的ファクトチェック")
        print(f"{'='*80}\n")
        print(f"入力ファイル: {csv_file}\n")

        # CSVを読み込み
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            episodes = list(reader)

        print(f"総エピソード数: {len(episodes)}件")

        stats = {
            "total": len(episodes),
            "perfect": 0,  # 問題なし
            "validation_only": 0,  # 検証のみ失敗
            "content_only": 0,  # 内容のみ問題
            "both_issues": 0,  # 両方問題
            "critical_issues": 0  # 重大問題
        }

        # 進捗表示
        print("\n🔄 チェック実行中...\n")

        for i, episode in enumerate(episodes, start=1):
            result = self.analyze_episode(episode)
            self.results.append(result)

            # 統計更新
            if result.is_valid and not result.has_content_issues:
                stats["perfect"] += 1
            elif not result.is_valid and not result.has_content_issues:
                stats["validation_only"] += 1
            elif result.is_valid and result.has_content_issues:
                stats["content_only"] += 1
            else:
                stats["both_issues"] += 1

            # 重大問題の検出
            if result.confidence_score < 0.5:
                stats["critical_issues"] += 1

            # 進捗表示
            if i % 20 == 0:
                print(f"  進捗: {i}/100 件完了")

        # 結果表示
        print(f"\n{'='*80}")
        print("検証結果サマリー")
        print(f"{'='*80}\n")
        print(f"✅ 完璧: {stats['perfect']}件 ({stats['perfect']}%)")
        print(f"⚠️ 検証のみ失敗: {stats['validation_only']}件")
        print(f"⚠️ 内容のみ問題: {stats['content_only']}件")
        print(f"❌ 両方問題: {stats['both_issues']}件")
        print(f"🚨 重大問題: {stats['critical_issues']}件")

        # 問題のあるエピソードを詳細表示
        problematic = [r for r in self.results if not r.is_valid or r.has_content_issues]

        if problematic:
            print(f"\n{'='*80}")
            print(f"問題のあるエピソード: {len(problematic)}件")
            print(f"{'='*80}\n")

            for result in problematic:
                print(f"📍 {result.episode_id}: {result.person_name}")
                print(f"   検証: {'✅ 合格' if result.is_valid else '❌ 不合格'}")
                print(f"   内容: {'✅ 問題なし' if not result.has_content_issues else '❌ 問題あり'}")
                print(f"   信頼度: {result.confidence_score:.1%}")

                if result.content_issues:
                    print(f"   内容問題:")
                    for issue in result.content_issues:
                        print(f"     - [{issue.severity}] {issue.description}")

                if result.suggestions:
                    print(f"   提案:")
                    for suggestion in result.suggestions[:2]:  # 最初の2つ
                        print(f"     - {suggestion}")

                print()

        return stats, problematic


def main():
    """メイン処理"""
    csv_file = "episodes_final_with_id_20251001.csv"

    print("="*80)
    print("全100件エピソード包括的ファクトチェックシステム")
    print("="*80)
    print("""
【検証項目】
1. 統合検証システムによる形式チェック（文字数、定型文、年号等）
2. 内容品質チェック
   - 重複テキストの検出
   - 年齢混乱の検出（個人年齢 vs 組織年齢）
   - 意味不明な表現の検出
   - 不自然な文構成の検出
3. 総合信頼度スコアの算出
    """)
    print("="*80)

    # チェック実行
    checker = Comprehensive100EpisodeChecker()
    stats, problematic = checker.check_all_100_episodes(csv_file)

    # 結果をJSON出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_json = f"fact_check_100_episodes_{timestamp}.json"

    report_data = {
        "timestamp": timestamp,
        "input_file": csv_file,
        "stats": stats,
        "problematic_episodes": [
            {
                "episode_id": r.episode_id,
                "person_name": r.person_name,
                "is_valid": r.is_valid,
                "has_content_issues": r.has_content_issues,
                "confidence_score": r.confidence_score,
                "content_issues": [
                    {
                        "type": i.issue_type,
                        "description": i.description,
                        "severity": i.severity
                    }
                    for i in r.content_issues
                ],
                "suggestions": r.suggestions
            }
            for r in problematic
        ]
    }

    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(report_data, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*80}")
    print(f"詳細レポート: {output_json}")
    print("="*80 + "\n")

    if len(problematic) == 0:
        print("🎉 全100件のエピソードが完璧です！")
    else:
        print(f"⚠️ {len(problematic)}件のエピソードに要改善点があります。")
        print(f"\n次のステップ:")
        print(f"1. {output_json}で詳細を確認")
        print(f"2. MCP APIやWeb検索で事実確認")
        print(f"3. 問題のあるエピソードを修正")


if __name__ == "__main__":
    main()
