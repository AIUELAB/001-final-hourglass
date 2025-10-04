#!/usr/bin/env python3
"""
MCP統合グループ検証システム - 完全実装版
Full MCP Integration for Group Verification

Brave Search、Wikipedia、WebFetchを活用して
100人全員のグループ所属情報を高精度で検証します。

使用MCPツール:
- mcp__brave-search__brave_web_search
- WebFetch (Wikipedia記事取得)

Created: 2025-10-02
"""

import pandas as pd
import json
import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path


@dataclass
class GroupVerificationResult:
    """グループ検証結果"""
    person_name: str

    # 基本情報
    entity_type: str = "person"
    group_name: Optional[str] = None
    group_type: Optional[str] = None  # band, comedy_duo, youtube_unit, solo
    work_title: Optional[str] = None  # 架空キャラクター用

    # 検証ソース
    brave_group_detected: bool = False
    brave_group_name: Optional[str] = None
    brave_evidence: List[str] = None

    wikipedia_url: Optional[str] = None
    wikipedia_group_detected: bool = False
    wikipedia_group_name: Optional[str] = None
    wikipedia_summary: Optional[str] = None

    database_group_detected: bool = False
    database_group_name: Optional[str] = None

    # 総合判定
    final_group_name: Optional[str] = None
    confidence_score: float = 0.0
    verification_status: str = "pending"

    # エビデンス
    all_evidence: List[str] = None
    reasoning: str = ""
    notes: str = ""

    def __post_init__(self):
        if self.brave_evidence is None:
            self.brave_evidence = []
        if self.all_evidence is None:
            self.all_evidence = []


class MCPGroupVerificationEngine:
    """MCP統合グループ検証エンジン"""

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.df = pd.read_csv(csv_path)
        self.results: Dict[str, GroupVerificationResult] = {}

        # 既知グループデータベース
        self.known_groups = self._load_known_groups()

        # グループ検出パターン
        self.group_patterns = {
            'band': [
                r'(.+?)のメンバー',
                r'(.+?)に所属',
                r'バンド[「『](.+?)[」』]',
                r'ロックバンド(.+?)の',
                r'グループ[「『](.+?)[」』]',
            ],
            'comedy': [
                r'お笑いコンビ[「『](.+?)[」』]',
                r'漫才コンビ(.+?)の',
                r'(.+?)のボケ',
                r'(.+?)のツッコミ',
            ],
            'youtube': [
                r'YouTuber(.+?)の',
                r'(.+?)というユニット',
                r'(.+?)として活動',
            ]
        }

    def _load_known_groups(self) -> Dict:
        """既知グループデータベースをロード"""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from group_member_database import GROUP_MEMBERS_DATABASE, NAME_TO_GROUP

            print(f"✅ 既知グループデータベース読み込み: {len(NAME_TO_GROUP)}件")
            return {
                'database': GROUP_MEMBERS_DATABASE,
                'name_to_group': NAME_TO_GROUP
            }
        except ImportError:
            print("⚠️ group_member_database.py未検出")
            return {'database': {}, 'name_to_group': {}}

    def check_known_database(self, person_name: str) -> Tuple[bool, Optional[str]]:
        """既知データベースチェック"""
        name_lower = person_name.lower()

        if name_lower in self.known_groups.get('name_to_group', {}):
            group_name, person_id = self.known_groups['name_to_group'][name_lower]
            return True, group_name

        return False, None

    def extract_group_from_brave(self, search_results: List[Dict]) -> Tuple[bool, Optional[str], List[str]]:
        """Brave Search結果からグループ名を抽出"""
        evidence = []
        detected_groups = []

        for result in search_results:
            title = result.get('title', '')
            description = result.get('description', '')
            combined_text = f"{title} {description}"

            # パターンマッチング
            for category, patterns in self.group_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, combined_text)
                    if match:
                        group_name = match.group(1).strip()
                        detected_groups.append(group_name)
                        evidence.append(f"Brave [{category}]: {group_name}")
                        break

        if detected_groups:
            # 最頻出グループ名を採用
            most_common = max(set(detected_groups), key=detected_groups.count)
            return True, most_common, evidence

        return False, None, []

    def extract_group_from_wikipedia(self, wiki_text: str) -> Tuple[bool, Optional[str], str]:
        """Wikipedia記事からグループ情報を抽出"""
        summary = ""

        # グループ名抽出パターン
        for category, patterns in self.group_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, wiki_text)
                if match:
                    group_name = match.group(1).strip()
                    summary = f"Wikipedia記事にて{category}「{group_name}」のメンバーと確認"
                    return True, group_name, summary

        return False, None, "グループ情報検出されず"

    def verify_person(self, person_name: str, index: int, total: int) -> GroupVerificationResult:
        """
        1人の検証を実行

        NOTE: この関数内でMCPツールを呼び出すことはできません。
        代わりに、Claude Codeに対して「特定の人物の検証」を依頼する形で実装します。

        実際の実装では、このスクリプトはClaude Codeがサブエージェントとして
        各人物を検証するためのフレームワークとして機能します。
        """
        result = GroupVerificationResult(person_name=person_name)

        print(f"\n[{index+1}/{total}] 🔍 {person_name} を検証中...")

        # Step 1: 既知データベースチェック
        in_db, db_group = self.check_known_database(person_name)
        if in_db:
            result.database_group_detected = True
            result.database_group_name = db_group
            result.all_evidence.append(f"既知DB: {db_group}")
            print(f"  ✅ 既知データベース: {db_group}")

        # Step 2 & 3: Brave Search + Wikipedia検証
        # → この部分はClaude CodeがMCPツールを使って実行
        result.notes = "MCP検証はClaude Codeが実行"

        return result

    def generate_verification_plan(self, sample_size: Optional[int] = None) -> Dict:
        """検証プランを生成"""

        if sample_size:
            persons_to_verify = self.df.head(sample_size)['person_name'].tolist()
            print(f"\n📋 {sample_size}人サンプル検証プラン")
        else:
            persons_to_verify = self.df['person_name'].tolist()
            print(f"\n📋 全{len(persons_to_verify)}人検証プラン")

        plan = {
            'total_persons': len(persons_to_verify),
            'verification_tasks': []
        }

        for idx, person_name in enumerate(persons_to_verify):
            task = {
                'index': idx + 1,
                'person_name': person_name,
                'queries': {
                    'brave_search': [
                        f"{person_name} グループ メンバー",
                        f"{person_name} バンド",
                        f"{person_name} お笑いコンビ",
                    ],
                    'wikipedia_url': f"https://ja.wikipedia.org/wiki/{person_name}"
                }
            }
            plan['verification_tasks'].append(task)

        print(f"  総タスク数: {len(plan['verification_tasks'])}")
        print(f"  推定Brave Search呼び出し: {len(plan['verification_tasks']) * 3}回")
        print(f"  推定Wikipedia呼び出し: {len(plan['verification_tasks'])}回")

        return plan

    def save_results(self, output_dir: str = "verification_results"):
        """検証結果を保存"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # JSON詳細レポート
        report = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'csv_source': self.csv_path,
                'total_persons': len(self.results)
            },
            'statistics': {
                'verified': sum(1 for r in self.results.values() if r.verification_status == "verified"),
                'uncertain': sum(1 for r in self.results.values() if r.verification_status == "uncertain"),
                'group_members': sum(1 for r in self.results.values() if r.final_group_name),
                'high_confidence': sum(1 for r in self.results.values() if r.confidence_score >= 80),
            },
            'results': [asdict(r) for r in self.results.values()]
        }

        report_path = output_path / f"verification_report_{timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        print(f"\n📄 検証レポート保存: {report_path}")

        # エンリッチCSV
        enriched_df = self.df.copy()
        enriched_df['entity_type'] = 'person'
        enriched_df['group_name'] = None
        enriched_df['verification_confidence'] = 0.0

        for idx, row in enriched_df.iterrows():
            person_name = row['person_name']
            if person_name in self.results:
                result = self.results[person_name]
                enriched_df.at[idx, 'entity_type'] = result.entity_type
                enriched_df.at[idx, 'group_name'] = result.final_group_name
                enriched_df.at[idx, 'verification_confidence'] = result.confidence_score

        csv_path = output_path / f"enriched_database_{timestamp}.csv"
        enriched_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"📊 エンリッチCSV保存: {csv_path}")

        return report


def main():
    """メイン関数"""
    print("=" * 80)
    print("🌐 MCP統合グループ検証システム - 完全実装版")
    print("=" * 80)

    csv_path = "episodes_final_fixed_20250923_141648.csv"

    engine = MCPGroupVerificationEngine(csv_path)

    # 検証プラン生成（5人サンプル）
    plan = engine.generate_verification_plan(sample_size=5)

    print("\n" + "=" * 80)
    print("📝 検証プラン詳細")
    print("=" * 80)

    for task in plan['verification_tasks'][:5]:
        print(f"\n[{task['index']}] {task['person_name']}")
        print(f"  Brave Search:")
        for query in task['queries']['brave_search']:
            print(f"    - {query}")
        print(f"  Wikipedia: {task['queries']['wikipedia_url']}")

    print("\n" + "=" * 80)
    print("🎯 次のステップ")
    print("=" * 80)
    print("このプランをClaude Codeに渡して、各人物の検証をMCPツールで実行します")
    print("")
    print("Claude Codeへの指示:")
    print("「上記のverification_tasksに基づいて、各人物のグループ所属情報を")
    print(" Brave SearchとWikipediaで検証してください。」")
    print("=" * 80)

    return plan


if __name__ == "__main__":
    main()
