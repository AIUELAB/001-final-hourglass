#!/usr/bin/env python3
"""
包括的グループ・作品情報ファクトチェッカー
Comprehensive Group & Work Fact Checker with MCP Integration

このスクリプトはMCPサーバー（Brave Search、Wikipedia）を活用して、
100人全員のグループ所属情報と架空キャラクターの作品情報を検証・収集します。

機能:
1. Brave Search APIで最新のグループ情報を検索
2. Wikipedia APIで公式情報を検証
3. 既存のgroup_member_database.pyとクロスチェック
4. 信頼度スコアリング（0-100%）
5. 詳細なファクトチェックレポート生成

Created: 2025-10-02
"""

import pandas as pd
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class GroupVerificationResult:
    """グループ検証結果"""
    person_name: str
    entity_type: str  # "person", "group", "fictional_character"
    group_name: Optional[str] = None
    group_type: Optional[str] = None  # "band", "comedy_duo", "youtube_group"
    work_title: Optional[str] = None  # 架空キャラクター用

    # 検証ソース
    verified_by_brave: bool = False
    verified_by_wikipedia: bool = False
    verified_by_database: bool = False

    # 信頼度（0-100%）
    confidence_score: float = 0.0

    # エビデンス
    evidence: List[str] = None

    # 検証メモ
    notes: str = ""

    def __post_init__(self):
        if self.evidence is None:
            self.evidence = []

    def calculate_confidence(self):
        """信頼度スコアを計算"""
        score = 0.0

        # 複数ソースで検証されているほど高スコア
        if self.verified_by_brave:
            score += 30.0
        if self.verified_by_wikipedia:
            score += 50.0  # Wikipedia最重視
        if self.verified_by_database:
            score += 20.0

        # エビデンス数でボーナス
        evidence_bonus = min(len(self.evidence) * 5, 20)
        score += evidence_bonus

        self.confidence_score = min(score, 100.0)
        return self.confidence_score


class ComprehensiveGroupFactChecker:
    """包括的グループ・作品ファクトチェッカー"""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self.results: List[GroupVerificationResult] = []

        # 既存グループデータベースをロード
        self.known_groups = self._load_known_groups()

        # バンド・音楽グループのキーワード
        self.band_keywords = [
            'バンド', 'band', 'グループ', 'group', 'メンバー', 'member',
            'ボーカル', 'vocal', 'ギター', 'guitar', 'ドラム', 'drum',
            'ベース', 'bass', 'アーティスト', 'artist'
        ]

        # お笑いコンビ・グループのキーワード
        self.comedy_keywords = [
            'コンビ', '漫才', 'お笑い', 'コント', '芸人',
            'comedy', 'comedian', 'manzai'
        ]

        # YouTuberグループのキーワード
        self.youtube_keywords = [
            'YouTuber', 'YouTube', 'チャンネル', 'channel',
            '動画', 'video', '配信', 'streamer'
        ]

        # 架空キャラクターのキーワード
        self.fictional_keywords = [
            'キャラクター', 'character', '主人公', 'protagonist',
            '漫画', 'manga', 'アニメ', 'anime', '小説', 'novel',
            'ゲーム', 'game', '作品', 'work'
        ]

    def _load_known_groups(self) -> Dict[str, List[str]]:
        """既存のグループデータベースをロード"""
        try:
            # group_member_database.pyから既知のグループを読み込み
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from group_member_database import GROUP_MEMBERS_DATABASE, NAME_TO_GROUP

            return {
                'database': GROUP_MEMBERS_DATABASE,
                'name_to_group': NAME_TO_GROUP
            }
        except ImportError:
            return {'database': {}, 'name_to_group': {}}

    def check_in_known_database(self, person_name: str) -> Tuple[bool, Optional[str]]:
        """既知のデータベースでチェック"""
        name_lower = person_name.lower()

        if name_lower in self.known_groups.get('name_to_group', {}):
            group_name, person_id = self.known_groups['name_to_group'][name_lower]
            return True, group_name

        return False, None

    def verify_person(self, person_name: str, category: str) -> GroupVerificationResult:
        """
        1人の人物情報を検証

        このメソッドは実際のMCP呼び出しプレースホルダー
        実装時にBrave Search、Wikipedia MCPを使用
        """
        result = GroupVerificationResult(
            person_name=person_name,
            entity_type="person"  # デフォルト
        )

        # Step 1: 既知のデータベースチェック
        in_db, group_name = self.check_in_known_database(person_name)
        if in_db:
            result.verified_by_database = True
            result.group_name = group_name
            result.evidence.append(f"既知のデータベースに登録: {group_name}")

        # Step 2: Brave Search検証（プレースホルダー）
        # 実際の実装では mcp__brave-search__brave_web_search を使用
        result.notes = "MCP検証: 実装予定"

        # Step 3: Wikipedia検証（プレースホルダー）
        # 実際の実装では WebFetch + Wikipedia を使用

        # 信頼度計算
        result.calculate_confidence()

        return result

    def run_comprehensive_check(self) -> pd.DataFrame:
        """全員の包括的チェックを実行"""
        print(f"🔍 {len(self.df)}人の包括的グループ・作品情報チェック開始...")

        for idx, row in self.df.iterrows():
            person_name = row['person_name']
            category = row.get('category', 'unknown')

            print(f"  [{idx+1}/{len(self.df)}] {person_name} を検証中...")

            result = self.verify_person(person_name, category)
            self.results.append(result)

        # 結果をDataFrameに変換
        results_df = pd.DataFrame([asdict(r) for r in self.results])

        return results_df

    def generate_report(self, output_path: str = "group_verification_report.json"):
        """詳細レポートを生成"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_persons": len(self.results),
            "statistics": {
                "verified_by_database": sum(1 for r in self.results if r.verified_by_database),
                "verified_by_brave": sum(1 for r in self.results if r.verified_by_brave),
                "verified_by_wikipedia": sum(1 for r in self.results if r.verified_by_wikipedia),
                "high_confidence": sum(1 for r in self.results if r.confidence_score >= 70),
                "medium_confidence": sum(1 for r in self.results if 40 <= r.confidence_score < 70),
                "low_confidence": sum(1 for r in self.results if r.confidence_score < 40),
            },
            "group_members_found": sum(1 for r in self.results if r.group_name),
            "fictional_characters_found": sum(1 for r in self.results if r.work_title),
            "results": [asdict(r) for r in self.results]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n✅ レポート保存: {output_path}")

        return report


def main():
    """メイン実行"""
    csv_path = "episodes_final_fixed_20250923_141648.csv"

    checker = ComprehensiveGroupFactChecker(csv_path)

    # 包括的チェック実行
    results_df = checker.run_comprehensive_check()

    # レポート生成
    report = checker.generate_report()

    # 統計表示
    print("\n" + "="*60)
    print("📊 グループ・作品情報検証結果")
    print("="*60)
    print(f"総人数: {report['total_persons']}")
    print(f"既知データベース検証済み: {report['statistics']['verified_by_database']}")
    print(f"グループメンバー発見: {report['group_members_found']}")
    print(f"高信頼度(≥70%): {report['statistics']['high_confidence']}")
    print(f"中信頼度(40-70%): {report['statistics']['medium_confidence']}")
    print(f"低信頼度(<40%): {report['statistics']['low_confidence']}")
    print("="*60)

    # 結果CSV保存
    results_df.to_csv('group_verification_results.csv', index=False, encoding='utf-8-sig')
    print(f"✅ 詳細結果CSV: group_verification_results.csv")


if __name__ == "__main__":
    main()
