#!/usr/bin/env python3
"""
統合データベースファクトチェックシステム
全102エピソードの事実確認を実施
"""

import csv
import re
from typing import Dict, List, Tuple
from pathlib import Path
from datetime import datetime
import pandas as pd

class FactChecker:
    """ファクトチェッカー"""

    def __init__(self):
        """初期化"""
        self.known_facts = self._load_known_facts()
        self.check_results = {
            "verified": [],
            "needs_verification": [],
            "contains_placeholder": [],
            "factual_errors": []
        }

    def _load_known_facts(self) -> Dict:
        """既知の事実データベース"""
        return {
            "大谷翔平": {
                "wbc_year": 2023,
                "wbc_age": 29,
                "mvp_year": 2021,
                "mvp_age": 26,
                "facts": ["二刀流", "WBC", "MVP", "46本塁打", "トラウト"]
            },
            "イチロー": {
                "retirement_year": 2019,
                "retirement_age": 45,
                "262_hits_year": 2004,
                "262_hits_age": 30,
                "facts": ["4367安打", "262安打", "200本安打", "28年間", "引退"]
            },
            "宮崎駿": {
                "spirited_away_year": 2001,
                "spirited_away_age": 60,
                "facts": ["千と千尋の神隠し", "アカデミー賞", "316億円", "ジブリ"]
            },
            "羽生結弦": {
                "pyeongchang_year": 2018,
                "pyeongchang_age": 23,
                "facts": ["66年ぶり", "連覇", "SEIMEI", "317.85点", "右足首"]
            },
            "藤井聡太": {
                "youngest_title_year": 2020,
                "youngest_title_age": 17,
                "five_crowns_year": 2021,
                "five_crowns_age": 19,
                "facts": ["29連勝", "最年少", "五冠", "竜王", "棋聖"]
            },
            "村上春樹": {
                "norwegian_wood_year": 1987,
                "norwegian_wood_age": 38,
                "facts": ["ノルウェイの森", "430万部", "40か国", "ジャズ喫茶"]
            },
            "山中伸弥": {
                "nobel_year": 2012,
                "nobel_age": 50,
                "ips_year": 2006,
                "ips_age": 44,
                "facts": ["iPS細胞", "ノーベル賞", "再生医療", "6年"]
            },
            "浅田真央": {
                "sochi_year": 2014,
                "sochi_age": 24,
                "facts": ["ソチ五輪", "142.71点", "トリプルアクセル", "16位から6位"]
            },
            "スティーブ・ジョブズ": {
                "iphone_year": 2007,
                "iphone_age": 52,
                "facts": ["iPhone", "Macworld", "875倍", "3500億ドル"]
            },
            "ヘレン・ケラー": {
                "water_year": 1887,
                "water_age": 7,
                "facts": ["water", "30の単語", "14カ国語", "ハーバード", "三重苦"]
            },
            "さくらももこ": {
                "chibi_maruko_year": 1986,
                "chibi_maruko_age": 21,
                "facts": ["ちびまる子ちゃん", "りぼん", "39.9％", "2か月で退職"]
            },
            "HIKAKIN": {
                "youtube_milestone_year": 2019,
                "youtube_milestone_age": 30,
                "facts": ["800万人", "100億回", "YouTuber", "アルバイト", "10億円"]
            }
        }

    def check_episode(self, person_name: str, age: int, episode: str) -> Dict:
        """エピソードをファクトチェック"""
        result = {
            "person": person_name,
            "age": age,
            "status": "unknown",
            "issues": [],
            "verified_facts": [],
            "confidence": 0.0
        }

        # プレースホルダーチェック
        placeholder_patterns = [
            r"重要な成果を残していた",
            r"その功績は今も語り継がれている",
            r"キャリアの重要な局面で",
            r"歴史に残る挑戦として",
            r"それまでの記録を塗り替える挑戦"
        ]

        for pattern in placeholder_patterns:
            if re.search(pattern, episode):
                result["status"] = "placeholder"
                result["issues"].append(f"テンプレート文検出: {pattern}")
                result["confidence"] = 0.0
                return result

        # 既知の事実との照合
        if person_name in self.known_facts:
            person_facts = self.known_facts[person_name]
            verified_count = 0

            # 事実確認
            for fact in person_facts.get("facts", []):
                if fact in episode:
                    result["verified_facts"].append(fact)
                    verified_count += 1

            # 年齢・年度チェック
            for key, expected_age in person_facts.items():
                if key.endswith("_age") and age == expected_age:
                    event_name = key.replace("_age", "")
                    result["verified_facts"].append(f"{event_name}の年齢が正確")
                    verified_count += 1

            # 評価
            if verified_count >= 3:
                result["status"] = "verified"
                result["confidence"] = min(1.0, verified_count / 5.0)
            elif verified_count >= 1:
                result["status"] = "partially_verified"
                result["confidence"] = verified_count / 5.0
            else:
                result["status"] = "needs_verification"
                result["confidence"] = 0.2

        else:
            # データベースにない人物
            result["status"] = "needs_verification"
            result["confidence"] = 0.1

        # 明らかな誤りチェック
        error_patterns = [
            (r"2007年.*ジョブズ.*30歳", "ジョブズは2007年に52歳"),
            (r"1887年.*ヘレン・ケラー.*30歳", "ヘレン・ケラーは1887年に7歳"),
            (r"WBC.*28歳", "大谷翔平のWBC制覇は29歳")
        ]

        for pattern, error_msg in error_patterns:
            if re.search(pattern, episode):
                result["status"] = "factual_error"
                result["issues"].append(error_msg)
                result["confidence"] = 0.0

        return result

    def check_database(self, csv_path: str) -> Tuple[Dict, List]:
        """データベース全体をチェック"""
        df = pd.read_csv(csv_path, encoding='utf-8-sig')
        all_results = []

        print("\nファクトチェック実行中...")
        print("="*60)

        for idx, row in df.iterrows():
            person_name = row['person_name']
            age = row['age']
            episode = row['episode']

            result = self.check_episode(person_name, age, episode)
            all_results.append(result)

            # 分類
            if result["status"] == "verified":
                self.check_results["verified"].append(person_name)
            elif result["status"] == "placeholder":
                self.check_results["contains_placeholder"].append(person_name)
            elif result["status"] == "factual_error":
                self.check_results["factual_errors"].append(person_name)
            else:
                self.check_results["needs_verification"].append(person_name)

            # 進捗表示
            if (idx + 1) % 20 == 0:
                print(f"  進捗: {idx + 1}/{len(df)}")

        return self.check_results, all_results

    def generate_report(self, check_results: Dict, all_results: List) -> str:
        """レポート生成"""
        report = []
        report.append("\n" + "="*60)
        report.append("ファクトチェックレポート")
        report.append("="*60)

        total = len(all_results)
        report.append(f"\n総エピソード数: {total}")
        report.append(f"  ✓ 検証済み: {len(check_results['verified'])} ({len(check_results['verified'])/total*100:.1f}%)")
        report.append(f"  ⚠ 要検証: {len(check_results['needs_verification'])} ({len(check_results['needs_verification'])/total*100:.1f}%)")
        report.append(f"  ✗ プレースホルダー: {len(check_results['contains_placeholder'])} ({len(check_results['contains_placeholder'])/total*100:.1f}%)")
        report.append(f"  ✗ 事実誤り: {len(check_results['factual_errors'])} ({len(check_results['factual_errors'])/total*100:.1f}%)")

        # 検証済みエピソード
        if check_results["verified"]:
            report.append("\n【検証済みエピソード】")
            for person in check_results["verified"][:10]:
                report.append(f"  ✓ {person}")

        # プレースホルダー含有
        if check_results["contains_placeholder"]:
            report.append(f"\n【プレースホルダー検出】({len(check_results['contains_placeholder'])}件)")
            for person in check_results["contains_placeholder"][:10]:
                report.append(f"  ✗ {person}")
            if len(check_results["contains_placeholder"]) > 10:
                report.append(f"  ... 他{len(check_results['contains_placeholder'])-10}件")

        # 事実誤り
        if check_results["factual_errors"]:
            report.append(f"\n【事実誤り検出】")
            for person in check_results["factual_errors"]:
                report.append(f"  ✗ {person}")

        # 改善提案
        report.append("\n【改善提案】")
        placeholder_count = len(check_results['contains_placeholder'])
        if placeholder_count > 50:
            report.append(f"  1. {placeholder_count}件のプレースホルダーエピソードを具体的内容に置換")
            report.append(f"  2. historical_moments_database.jsonの拡充（現在15人→102人）")
            report.append(f"  3. 各エピソードの年代・数値データの検証")

        return "\n".join(report)

    def save_fact_check_report(self, check_results: Dict, all_results: List,
                               filename: str = None) -> str:
        """ファクトチェック結果を保存"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"fact_check_report_{timestamp}.csv"

        filepath = Path(__file__).parent / filename

        # CSV保存
        with open(filepath, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = ['person', 'age', 'status', 'confidence',
                         'verified_facts', 'issues']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()

            for result in all_results:
                writer.writerow({
                    'person': result['person'],
                    'age': result['age'],
                    'status': result['status'],
                    'confidence': result['confidence'],
                    'verified_facts': '|'.join(result['verified_facts']),
                    'issues': '|'.join(result['issues'])
                })

        print(f"\nファクトチェック結果保存: {filepath}")
        return str(filepath)


def main():
    """メイン実行"""
    print("統合データベース ファクトチェックシステム")
    print("="*60)

    checker = FactChecker()

    # データベースチェック
    db_path = "unified_episode_database_20250923_175555.csv"
    check_results, all_results = checker.check_database(db_path)

    # レポート生成
    report = checker.generate_report(check_results, all_results)
    print(report)

    # 結果保存
    csv_path = checker.save_fact_check_report(check_results, all_results)

    print("\n" + "="*60)
    print("ファクトチェック完了")
    print(f"詳細レポート: {csv_path}")


if __name__ == "__main__":
    main()
