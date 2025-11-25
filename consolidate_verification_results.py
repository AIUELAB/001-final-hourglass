#!/usr/bin/env python3
"""
全100人のグループ検証結果統合スクリプト
Consolidate 100 Person Group Verification Results

全10バッチ＋5人サンプルの検証結果を統合し、
包括的なレポートとエンリッチCSVを生成します。

Created: 2025-10-02
"""

import pandas as pd
import json
from typing import Dict, List
from datetime import datetime
from pathlib import Path
from collections import Counter


class VerificationResultConsolidator:
    """検証結果統合クラス"""

    def __init__(self, csv_path: str, verification_results_dir: str = "verification_results"):
        self.csv_path = csv_path
        self.results_dir = Path(verification_results_dir)
        self.df = pd.read_csv(csv_path)

        # 統合結果
        self.all_results: Dict[str, Dict] = {}

    def load_sample_results(self):
        """5人サンプル結果をロード"""
        sample_path = self.results_dir / "sample_5_verification_results.json"

        if sample_path.exists():
            with open(sample_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for result in data['results']:
                    self.all_results[result['person_name']] = result
            print(f"✅ サンプル5人の結果をロード: {len(data['results'])}件")
        else:
            print("⚠️ サンプル結果ファイルが見つかりません")

    def load_batch_results(self):
        """全10バッチの結果をロード"""

        # バッチ結果の手動統合（サブエージェントの報告から）
        batch_results = {
            # Batch 1 (People 6-15)
            "サカナクション": {
                "person_name": "サカナクション",
                "entity_type": "group",
                "group_name": None,
                "group_type": "band",
                "confidence_score": 95.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/サカナクション",
                "reasoning": "バンドそのものとして確認（山口一郎、岩寺基晴、草刈愛美、岡崎英美、江島啓一）",
                "notes": "5人組ロックバンド、2005年結成"
            },
            "マザー・テレサ": {
                "person_name": "マザー・テレサ",
                "entity_type": "person",
                "group_name": "神の愛の宣教者会",
                "group_type": "religious_order",
                "confidence_score": 90.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/マザー・テレサ",
                "reasoning": "Wikipedia確認: カトリック修道女、神の愛の宣教者会創設者",
                "notes": "ノーベル平和賞受賞者"
            },

            # Batch 2 (People 16-25)
            "前澤友作": {
                "person_name": "前澤友作",
                "entity_type": "person",
                "group_name": "SWITCH STYLE",
                "group_type": "band",
                "confidence_score": 85.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/前澤友作",
                "reasoning": "元バンドメンバー（SWITCH STYLE、2000年解散）",
                "notes": "ZOZO創業者、現在は起業家として活動"
            },

            # Batch 3 (People 26-35)
            "北野武": {
                "person_name": "北野武",
                "entity_type": "person",
                "group_name": "ツービート",
                "group_type": "comedy_duo",
                "confidence_score": 95.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/北野武",
                "reasoning": "Wikipedia＋Brave確認: ビートたけしとして漫才コンビ「ツービート」",
                "notes": "映画監督、芸人、俳優"
            },
            "又吉直樹": {
                "person_name": "又吉直樹",
                "entity_type": "person",
                "group_name": "ピース",
                "group_type": "comedy_duo",
                "confidence_score": 95.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/又吉直樹",
                "reasoning": "Wikipedia確認: お笑いコンビ「ピース」、芥川賞作家",
                "notes": "『火花』著者"
            },
            "坂本龍一": {
                "person_name": "坂本龍一",
                "entity_type": "person",
                "group_name": "YMO",
                "group_type": "band",
                "confidence_score": 95.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/坂本龍一",
                "reasoning": "Wikipedia確認: Yellow Magic Orchestra（YMO）メンバー",
                "notes": "音楽家、作曲家、プロデューサー"
            },
            "堀江貴文": {
                "person_name": "堀江貴文",
                "entity_type": "person",
                "group_name": "ハッカーズ",
                "group_type": "band",
                "confidence_score": 70.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/堀江貴文",
                "reasoning": "Brave Search確認: バンド「ハッカーズ」（2014年結成）",
                "notes": "実業家、ライブドア元社長、趣味でバンド活動"
            },

            # Batch 5 (People 46-55)
            "岡田准一": {
                "person_name": "岡田准一",
                "entity_type": "person",
                "group_name": "V6",
                "group_type": "idol_group",
                "confidence_score": 95.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/岡田准一",
                "reasoning": "Wikipedia確認: V6元メンバー（2021年解散）",
                "notes": "ジャニーズ事務所、俳優"
            },
            "星野源": {
                "person_name": "星野源",
                "entity_type": "person",
                "group_name": "SAKEROCK",
                "group_type": "band",
                "confidence_score": 90.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/星野源",
                "reasoning": "Wikipedia確認: SAKEROCK元リーダー（2015年解散）",
                "notes": "現在はソロシンガーソングライター、俳優"
            },

            # Batch 6 (People 56-65)
            "松本人志": {
                "person_name": "松本人志",
                "entity_type": "person",
                "group_name": "ダウンタウン",
                "group_type": "comedy_duo",
                "confidence_score": 95.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/松本人志",
                "reasoning": "Wikipedia確認: お笑いコンビ「ダウンタウン」",
                "notes": "吉本興業所属、映画監督"
            },

            # Batch 7 (People 66-75)
            "櫻井翔": {
                "person_name": "櫻井翔",
                "entity_type": "person",
                "group_name": "嵐",
                "group_type": "idol_group",
                "confidence_score": 95.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/櫻井翔",
                "reasoning": "Wikipedia確認: 嵐メンバー（1999年結成）",
                "notes": "ジャニーズ事務所、キャスター"
            },

            # Batch 9 (People 86-95)
            "西野亮廣": {
                "person_name": "西野亮廣",
                "entity_type": "person",
                "group_name": "キングコング",
                "group_type": "comedy_duo",
                "confidence_score": 95.0,
                "verification_status": "verified",
                "wikipedia_url": "https://ja.wikipedia.org/wiki/西野亮廣",
                "reasoning": "Wikipedia確認: お笑いコンビ「キングコング」",
                "notes": "吉本興業所属、絵本作家"
            },
        }

        # 統合結果に追加
        for person_name, result in batch_results.items():
            self.all_results[person_name] = result

        print(f"✅ バッチ結果をロード: {len(batch_results)}件のグループメンバー")

    def enrich_dataframe(self) -> pd.DataFrame:
        """CSVデータフレームをエンリッチ"""

        enriched_df = self.df.copy()

        # 新規カラムを追加
        enriched_df['entity_type'] = 'person'  # デフォルト
        enriched_df['group_name'] = None
        enriched_df['group_type'] = None
        enriched_df['verification_confidence'] = 0.0
        enriched_df['verification_status'] = 'unknown'
        enriched_df['wikipedia_url'] = None

        # 検証結果をマージ
        for idx, row in enriched_df.iterrows():
            person_name = row['person_name']

            if person_name in self.all_results:
                result = self.all_results[person_name]
                enriched_df.at[idx, 'entity_type'] = result.get('entity_type', 'person')
                enriched_df.at[idx, 'group_name'] = result.get('group_name')
                enriched_df.at[idx, 'group_type'] = result.get('group_type')
                enriched_df.at[idx, 'verification_confidence'] = result.get('confidence_score', 0.0)
                enriched_df.at[idx, 'verification_status'] = result.get('verification_status', 'unknown')
                enriched_df.at[idx, 'wikipedia_url'] = result.get('wikipedia_url')

        return enriched_df

    def generate_comprehensive_report(self) -> Dict:
        """包括的レポート生成"""

        # 統計計算
        group_members = [r for r in self.all_results.values() if r.get('group_name')]
        entity_types = Counter([r.get('entity_type', 'person') for r in self.all_results.values()])
        group_types = Counter([r.get('group_type') for r in group_members if r.get('group_type')])
        confidence_scores = [r.get('confidence_score', 0) for r in self.all_results.values()]

        report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "csv_source": self.csv_path,
                "total_persons": len(self.df),
                "verified_persons": len(self.all_results)
            },
            "statistics": {
                "total_verified": len(self.all_results),
                "group_members_found": len(group_members),
                "solo_artists": len(self.all_results) - len(group_members),
                "entity_type_distribution": dict(entity_types),
                "group_type_distribution": dict(group_types),
                "average_confidence": sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0,
                "high_confidence_count": sum(1 for s in confidence_scores if s >= 90),
                "medium_confidence_count": sum(1 for s in confidence_scores if 70 <= s < 90),
                "low_confidence_count": sum(1 for s in confidence_scores if s < 70)
            },
            "group_members": [
                {
                    "person_name": r['person_name'],
                    "group_name": r['group_name'],
                    "group_type": r['group_type'],
                    "confidence": r.get('confidence_score', 0),
                    "reasoning": r.get('reasoning', ''),
                    "notes": r.get('notes', '')
                }
                for r in group_members
            ],
            "mcp_usage": {
                "brave_search_detections": sum(1 for r in self.all_results.values() if r.get('brave_group_detected', False)),
                "wikipedia_detections": sum(1 for r in self.all_results.values() if r.get('wikipedia_group_detected', False) or r.get('wikipedia_url')),
                "mcp_tools_used": ["mcp__brave-search__brave_web_search", "WebFetch (Wikipedia)", "mcp__firecrawl__firecrawl_search"]
            },
            "detailed_results": list(self.all_results.values())
        }

        return report

    def export_results(self, output_dir: str = "verification_results"):
        """結果をエクスポート"""

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. 包括的レポート（JSON）
        report = self.generate_comprehensive_report()
        report_path = output_path / f"complete_100_person_verification_{timestamp}.json"
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"✅ 包括的レポート保存: {report_path}")

        # 2. エンリッチCSV
        enriched_df = self.enrich_dataframe()
        csv_path = output_path / f"episodes_enriched_with_groups_{timestamp}.csv"
        enriched_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✅ エンリッチCSV保存: {csv_path}")

        # 3. 統計サマリー表示
        print("\n" + "="*70)
        print("📊 100人グループ検証 - 最終統計")
        print("="*70)
        print(f"総検証人数: {report['metadata']['total_persons']}")
        print(f"検証済み: {report['statistics']['total_verified']}")
        print(f"\n🎭 グループメンバー発見: {report['statistics']['group_members_found']}人")
        print(f"🎤 ソロアーティスト: {report['statistics']['solo_artists']}人")

        print(f"\n📈 信頼度分布:")
        print(f"  高信頼度(≥90%): {report['statistics']['high_confidence_count']}人")
        print(f"  中信頼度(70-90%): {report['statistics']['medium_confidence_count']}人")
        print(f"  低信頼度(<70%): {report['statistics']['low_confidence_count']}人")
        print(f"  平均信頼度: {report['statistics']['average_confidence']:.1f}%")

        print(f"\n🎸 グループタイプ分布:")
        for group_type, count in report['statistics']['group_type_distribution'].items():
            print(f"  {group_type}: {count}件")

        print(f"\n🌐 MCP活用状況:")
        print(f"  Brave Search検出: {report['mcp_usage']['brave_search_detections']}件")
        print(f"  Wikipedia検出: {report['mcp_usage']['wikipedia_detections']}件")

        print("\n" + "="*70)
        print("🎯 発見されたグループメンバー一覧:")
        print("="*70)
        for member in sorted(report['group_members'], key=lambda x: x['person_name']):
            print(f"  {member['person_name']}: {member['group_name']} ({member['group_type']}) - {member['confidence']:.0f}%")

        print("\n" + "="*70)

        return report, enriched_df


def main():
    """メイン実行"""
    print("="*70)
    print("🌐 100人グループ検証結果統合システム")
    print("="*70)

    csv_path = "episodes_final_fixed_20250923_141648.csv"

    consolidator = VerificationResultConsolidator(csv_path)

    # サンプル結果をロード
    consolidator.load_sample_results()

    # バッチ結果をロード
    consolidator.load_batch_results()

    # 結果をエクスポート
    report, enriched_df = consolidator.export_results()

    print("\n✅ 全100人のグループ検証が完了しました")
    print(f"📊 詳細レポート: verification_results/")
    print(f"📁 エンリッチCSV: verification_results/")


if __name__ == "__main__":
    main()
