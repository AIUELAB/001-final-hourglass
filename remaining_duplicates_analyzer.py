#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
残り重複候補の詳細分析システム - 要検証の6件を詳しく調査

P000130, P000867, P002680, P003511, P015985, P015986
の詳細分析と削除の妥当性を判断
"""

import pandas as pd
import json
from datetime import datetime
from difflib import SequenceMatcher
from typing import Dict, List

class RemainingDuplicatesAnalyzer:
    def __init__(self, original_csv: str, cleaned_csv: str):
        """残り重複分析器の初期化"""
        self.original_csv = original_csv
        self.cleaned_csv = cleaned_csv
        self.original_df = pd.read_csv(original_csv)
        self.cleaned_df = pd.read_csv(cleaned_csv)

        # 要検証の削除候補
        self.validation_candidates = [
            'P000130', 'P000867', 'P002680',
            'P003511', 'P015985', 'P015986'
        ]

        print(f"🔍 残り重複分析器初期化完了")
        print(f"📊 要検証候補: {len(self.validation_candidates)} 件")

    def analyze_specific_candidate(self, person_id: str) -> Dict:
        """特定の候補を詳細分析"""
        # 元データから該当レコードを取得
        target_record = self.original_df[self.original_df['person_id'] == person_id]

        if target_record.empty:
            return {"error": f"Record {person_id} not found"}

        record = target_record.iloc[0]

        # 類似レコードを検索
        similar_records = []
        target_name = str(record['person_name'])

        for idx, row in self.original_df.iterrows():
            if row['person_id'] != person_id:
                # 名前の類似度をチェック
                other_name = str(row['person_name'])
                similarity = SequenceMatcher(None, target_name, other_name).ratio()

                if similarity > 0.8:  # 80%以上の類似度
                    similar_records.append({
                        'person_id': row['person_id'],
                        'person_name': other_name,
                        'person_name_display': str(row['person_name_display']),
                        'person_name_ja': str(row['person_name_ja']),
                        'nationality': str(row['nationality']),
                        'occupation': str(row['occupation']),
                        'category': str(row['category']),
                        'name_recognition': row['name_recognition'],
                        'similarity_score': similarity
                    })

        # 類似度でソート
        similar_records.sort(key=lambda x: x['similarity_score'], reverse=True)

        analysis = {
            'target_record': {
                'person_id': record['person_id'],
                'person_name': target_name,
                'person_name_display': str(record['person_name_display']),
                'person_name_ja': str(record['person_name_ja']),
                'nationality': str(record['nationality']),
                'occupation': str(record['occupation']),
                'category': str(record['category']),
                'name_recognition': record['name_recognition']
            },
            'similar_records': similar_records[:10],  # 上位10件
            'similarity_analysis': {
                'highest_similarity': max([r['similarity_score'] for r in similar_records], default=0),
                'potential_duplicates': len([r for r in similar_records if r['similarity_score'] > 0.95]),
                'likely_duplicates': len([r for r in similar_records if r['similarity_score'] > 0.90])
            },
            'deletion_recommendation': self.get_deletion_recommendation(record, similar_records)
        }

        return analysis

    def get_deletion_recommendation(self, target_record, similar_records) -> Dict:
        """削除推奨を判定"""
        # 最も類似度の高いレコードを分析
        if not similar_records:
            return {
                'recommendation': 'KEEP',
                'reason': '類似レコードが見つからない',
                'confidence': 'HIGH'
            }

        highest_sim_record = similar_records[0]
        similarity = highest_sim_record['similarity_score']

        # 削除判定ロジック
        if similarity >= 0.98:
            # 非常に高い類似度 - どちらを保持するか判定
            target_recognition = target_record['name_recognition']
            similar_recognition = highest_sim_record['name_recognition']

            if target_recognition > similar_recognition:
                return {
                    'recommendation': 'KEEP',
                    'reason': f'より高い認知度 ({target_recognition} > {similar_recognition})',
                    'confidence': 'HIGH',
                    'alternative_action': f'削除対象: {highest_sim_record["person_id"]}'
                }
            elif target_recognition < similar_recognition:
                return {
                    'recommendation': 'DELETE',
                    'reason': f'より低い認知度 ({target_recognition} < {similar_recognition})',
                    'confidence': 'HIGH',
                    'keep_alternative': highest_sim_record["person_id"]
                }
            else:
                # 認知度が同じ場合、person_idが小さい方を保持
                target_id_num = int(target_record['person_id'].replace('P', ''))
                similar_id_num = int(highest_sim_record['person_id'].replace('P', ''))

                if target_id_num < similar_id_num:
                    return {
                        'recommendation': 'KEEP',
                        'reason': f'より古いID ({target_record["person_id"]} < {highest_sim_record["person_id"]})',
                        'confidence': 'MEDIUM'
                    }
                else:
                    return {
                        'recommendation': 'DELETE',
                        'reason': f'より新しいID ({target_record["person_id"]} > {highest_sim_record["person_id"]})',
                        'confidence': 'MEDIUM'
                    }

        elif similarity >= 0.90:
            return {
                'recommendation': 'REVIEW',
                'reason': f'中程度の類似度 ({similarity:.3f}) - 手動確認推奨',
                'confidence': 'LOW'
            }

        else:
            return {
                'recommendation': 'KEEP',
                'reason': f'類似度が低い ({similarity:.3f}) - 異なる人物の可能性',
                'confidence': 'HIGH'
            }

    def analyze_all_validation_candidates(self) -> Dict:
        """すべての要検証候補を分析"""
        print("🔍 要検証候補の詳細分析開始...")

        analysis_results = {
            "analysis_timestamp": datetime.now().isoformat(),
            "total_candidates": len(self.validation_candidates),
            "candidate_analyses": {},
            "recommendations_summary": {
                "KEEP": [],
                "DELETE": [],
                "REVIEW": []
            }
        }

        for person_id in self.validation_candidates:
            print(f"📋 分析中: {person_id}")

            candidate_analysis = self.analyze_specific_candidate(person_id)
            analysis_results["candidate_analyses"][person_id] = candidate_analysis

            # 推奨に基づいて分類
            recommendation = candidate_analysis.get('deletion_recommendation', {}).get('recommendation', 'REVIEW')
            analysis_results["recommendations_summary"][recommendation].append(person_id)

        return analysis_results

    def generate_validation_report(self) -> str:
        """検証レポートを生成"""
        print("📊 検証レポート生成中...")

        # 詳細分析実行
        analysis_results = self.analyze_all_validation_candidates()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"VALIDATION_CANDIDATES_ANALYSIS_{timestamp}.json"

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(analysis_results, f, ensure_ascii=False, indent=2)

        # サマリー表示
        print("\n📊 検証結果サマリー")
        print("="*50)

        summary = analysis_results["recommendations_summary"]
        print(f"保持推奨: {len(summary['KEEP'])} 件")
        print(f"削除推奨: {len(summary['DELETE'])} 件")
        print(f"要確認: {len(summary['REVIEW'])} 件")

        # 各候補の詳細
        print("\n📋 各候補の推奨アクション:")
        for person_id in self.validation_candidates:
            analysis = analysis_results["candidate_analyses"].get(person_id, {})
            if 'target_record' in analysis:
                target = analysis['target_record']
                recommendation = analysis.get('deletion_recommendation', {})

                action = recommendation.get('recommendation', 'UNKNOWN')
                reason = recommendation.get('reason', '')
                confidence = recommendation.get('confidence', '')

                print(f"\n{person_id}: {target['person_name']}")
                print(f"  アクション: {action} ({confidence})")
                print(f"  理由: {reason}")

                if analysis['similar_records']:
                    top_similar = analysis['similar_records'][0]
                    print(f"  最類似: {top_similar['person_id']} - {top_similar['person_name']} (類似度: {top_similar['similarity_score']:.3f})")

        print(f"\n📝 詳細レポート保存: {report_file}")
        return report_file

def main():
    """メイン実行関数"""
    original_csv = "ultra_think_GROUP_FIXED_20250831_185100.csv"
    cleaned_csv = "ultra_think_DUPLICATES_REMOVED_20250831_191147.csv"

    print("🚀 残り重複候補詳細分析開始")
    print("="*60)

    # 分析器の初期化
    analyzer = RemainingDuplicatesAnalyzer(original_csv, cleaned_csv)

    # 検証レポート生成
    report_file = analyzer.generate_validation_report()

    print(f"\n✅ 分析完了")
    print(f"📝 検証レポート: {report_file}")

    return report_file

if __name__ == "__main__":
    main()
