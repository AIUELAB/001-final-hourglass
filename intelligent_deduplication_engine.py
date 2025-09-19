#!/usr/bin/env python3
"""
Intelligent Deduplication Engine for Ultra Think Database

高度な重複検出・削除エンジン：
- 品質スコアベースの選択アルゴリズム
- セマンティック重複検出（名前の類似性分析）
- 安全なバックアップ・削除プロセス
- 詳細なログ記録と統計レポート
"""

import pandas as pd
import json
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
from datetime import datetime
from pathlib import Path
import hashlib
import difflib
import re
from dataclasses import dataclass
from collections import defaultdict
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class PersonRecord:
    """個人レコードの詳細情報"""
    person_id: str
    person_name: str
    person_name_display: str
    person_name_ja: str
    name_recognition: float
    occupation: str
    category: str
    accuracy_score: float
    impact_score: float
    extended_data: str
    recognition_metadata: str
    row_index: int

@dataclass
class DuplicateGroup:
    """重複グループの情報"""
    canonical_record: PersonRecord
    duplicate_records: List[PersonRecord]
    similarity_score: float
    merge_strategy: str
    quality_reasons: List[str]

class IntelligentDeduplicationEngine:
    """高度な重複削除エンジン"""
    
    def __init__(self, csv_path: str):
        self.csv_path = Path(csv_path)
        self.df = pd.read_csv(csv_path)
        self.original_count = len(self.df)
        self.duplicate_groups: List[DuplicateGroup] = []
        self.processing_stats = {
            'total_records': self.original_count,
            'duplicate_groups_found': 0,
            'records_to_remove': 0,
            'quality_improvements': 0,
            'processing_time': 0
        }
        
        # バックアップディレクトリ作成
        self.backup_dir = Path('emergency_backups')
        self.backup_dir.mkdir(exist_ok=True)
        
        logger.info(f"データベース読み込み完了: {self.original_count}件のレコード")
    def normalize_name(self, name: str) -> str:
        """名前の正規化（重複検出用）"""
        if pd.isna(name) or not name:
            return ""
        
        # 基本的な正規化
        normalized = str(name).strip()
        
        # 括弧内容の削除 (例: "りんたろー。(EXIT)" → "りんたろー。")
        normalized = re.sub(r'\s*\([^)]*\)\s*', '', normalized)
        
        # 全角・半角の統一
        normalized = normalized.replace('。', '.').replace('（', '(').replace('）', ')')
        
        # スペースの統一
        normalized = re.sub(r'\s+', ' ', normalized)
        
        return normalized.lower()

    def calculate_name_similarity(self, name1: str, name2: str) -> float:
        """名前の類似度を計算（0-1の範囲）"""
        if not name1 or not name2:
            return 0.0
        
        norm1 = self.normalize_name(name1)
        norm2 = self.normalize_name(name2)
        
        # 完全一致
        if norm1 == norm2:
            return 1.0
        
        # Levenshtein距離ベースの類似度
        ratio = difflib.SequenceMatcher(None, norm1, norm2).ratio()
        
        # 日本語名の特別処理
        if self._is_japanese_name(name1) and self._is_japanese_name(name2):
            # カタカナ・ひらがな変換後の比較
            kana1 = self._to_katakana(norm1)
            kana2 = self._to_katakana(norm2)
            kana_ratio = difflib.SequenceMatcher(None, kana1, kana2).ratio()
            ratio = max(ratio, kana_ratio)
        
        return ratio

    def _is_japanese_name(self, name: str) -> bool:
        """日本語名かどうかを判定"""
        japanese_chars = re.compile(r'[ひらがなカタカナ漢字ー]')
        return bool(japanese_chars.search(name))

    def _to_katakana(self, text: str) -> str:
        """ひらがなをカタカナに変換（簡易版）"""
        hiragana = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
        katakana = "アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン"
        
        result = text
        for h, k in zip(hiragana, katakana):
            result = result.replace(h, k)
        return result

    def calculate_quality_score(self, record: PersonRecord) -> float:
        """レコードの品質スコアを計算"""
        score = 0.0
        
        # 名前認識スコア（最重要: 40%）
        if record.name_recognition:
            score += float(record.name_recognition) * 0.4
        
        # 精度スコア（30%）
        if record.accuracy_score:
            score += float(record.accuracy_score) * 0.3
        
        # インパクトスコア（20%）
        if record.impact_score:
            score += float(record.impact_score) * 0.2
        
        # データ完全性（10%）
        completeness = 0
        fields = [record.person_name, record.person_name_display, 
                 record.person_name_ja, record.occupation, record.category]
        completeness = sum(1 for field in fields if field and str(field).strip()) / len(fields)
        score += completeness * 10
        
        return score

    def detect_duplicates(self) -> List[DuplicateGroup]:
        """重複を検出してグループ化"""
        logger.info("重複検出を開始...")
        
        processed_indices = set()
        duplicate_groups = []
        
        for i, row in self.df.iterrows():
            if i in processed_indices:
                continue
            
            record = self._row_to_record(row, i)
            similar_records = []
            
            # 同じ人物の可能性があるレコードを検索
            for j, other_row in self.df.iterrows():
                if i >= j or j in processed_indices:
                    continue
                
                other_record = self._row_to_record(other_row, j)
                
                # 名前の類似度チェック
                name_similarities = [
                    self.calculate_name_similarity(record.person_name, other_record.person_name),
                    self.calculate_name_similarity(record.person_name_display, other_record.person_name_display),
                    self.calculate_name_similarity(record.person_name_ja, other_record.person_name_ja)
                ]
                
                max_similarity = max(name_similarities)
                
                # 高い類似度（0.85以上）または完全一致を重複と判定
                if max_similarity >= 0.85:
                    similar_records.append((other_record, max_similarity))
                    processed_indices.add(j)
            
            # 重複グループの作成
            if similar_records:
                all_records = [record] + [r[0] for r in similar_records]
                
                # 品質スコアで最適なレコードを選択
                quality_scores = [(r, self.calculate_quality_score(r)) for r in all_records]
                quality_scores.sort(key=lambda x: x[1], reverse=True)
                
                canonical_record = quality_scores[0][0]
                duplicate_records = [r[0] for r in quality_scores[1:]]
                
                # 品質選択理由の生成
                quality_reasons = self._generate_quality_reasons(canonical_record, duplicate_records)
                
                duplicate_group = DuplicateGroup(
                    canonical_record=canonical_record,
                    duplicate_records=duplicate_records,
                    similarity_score=max([s[1] for s in similar_records]),
                    merge_strategy="quality_based",
                    quality_reasons=quality_reasons
                )
                
                duplicate_groups.append(duplicate_group)
                processed_indices.add(i)
        
        self.duplicate_groups = duplicate_groups
        self.processing_stats['duplicate_groups_found'] = len(duplicate_groups)
        self.processing_stats['records_to_remove'] = sum(len(g.duplicate_records) for g in duplicate_groups)
        
        logger.info(f"重複検出完了: {len(duplicate_groups)}グループ、"
                   f"{self.processing_stats['records_to_remove']}件の重複レコード")
        
        return duplicate_groups

    def _row_to_record(self, row: pd.Series, index: int) -> PersonRecord:
        """DataFrameの行をPersonRecordに変換"""
        return PersonRecord(
            person_id=row.get('person_id', ''),
            person_name=row.get('person_name', ''),
            person_name_display=row.get('person_name_display', ''),
            person_name_ja=row.get('person_name_ja', ''),
            name_recognition=row.get('name_recognition', 0),
            occupation=row.get('occupation', ''),
            category=row.get('category', ''),
            accuracy_score=row.get('accuracy_score', 0),
            impact_score=row.get('impact_score', 0),
            extended_data=row.get('extended_data', ''),
            recognition_metadata=row.get('recognition_metadata', ''),
            row_index=index
        )

    def _generate_quality_reasons(self, canonical: PersonRecord, duplicates: List[PersonRecord]) -> List[str]:
        """品質選択の理由を生成"""
        reasons = []
        
        canonical_score = self.calculate_quality_score(canonical)
        
        for duplicate in duplicates:
            duplicate_score = self.calculate_quality_score(duplicate)
            
            if canonical.name_recognition > duplicate.name_recognition:
                reasons.append(f"名前認識スコア: {canonical.name_recognition} > {duplicate.name_recognition}")
            
            if canonical.accuracy_score > duplicate.accuracy_score:
                reasons.append(f"精度スコア: {canonical.accuracy_score} > {duplicate.accuracy_score}")
            
            if len(canonical.person_name_display) > len(duplicate.person_name_display):
                reasons.append("表示名がより詳細")
            
            reasons.append(f"総合品質スコア: {canonical_score:.2f} > {duplicate_score:.2f}")
        
        return reasons

    def create_backup(self) -> str:
        """安全なバックアップを作成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_filename = f"backup_before_deduplication_{timestamp}.csv"
        backup_path = self.backup_dir / backup_filename
        
        self.df.to_csv(backup_path, index=False)
        logger.info(f"バックアップ作成完了: {backup_path}")
        
        return str(backup_path)

    def remove_duplicates(self, confirm_removal: bool = True) -> pd.DataFrame:
        """重複レコードを安全に削除"""
        if not self.duplicate_groups:
            logger.warning("重複グループが検出されていません。detect_duplicates()を先に実行してください。")
            return self.df
        
        if confirm_removal:
            logger.info(f"重複削除の確認: {self.processing_stats['records_to_remove']}件のレコードを削除します")
            
            # 重要な重複を表示
            for i, group in enumerate(self.duplicate_groups[:5]):  # 最初の5件を表示
                logger.info(f"重複グループ {i+1}: {group.canonical_record.person_name} "
                           f"(保持) vs {[d.person_name for d in group.duplicate_records]} (削除)")
        
        # バックアップ作成
        backup_path = self.create_backup()
        
        # 削除対象のインデックスを収集
        indices_to_remove = []
        for group in self.duplicate_groups:
            for duplicate in group.duplicate_records:
                indices_to_remove.append(duplicate.row_index)
        
        # 削除実行
        cleaned_df = self.df.drop(indices_to_remove).reset_index(drop=True)
        
        # 統計更新
        self.processing_stats['records_removed'] = len(indices_to_remove)
        self.processing_stats['final_count'] = len(cleaned_df)
        
        logger.info(f"重複削除完了: {len(indices_to_remove)}件削除、{len(cleaned_df)}件残存")
        
        return cleaned_df

    def generate_deduplication_report(self) -> Dict:
        """重複削除レポートを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        report = {
            "deduplication_summary": {
                "timestamp": timestamp,
                "original_records": self.processing_stats['total_records'],
                "duplicate_groups_found": self.processing_stats['duplicate_groups_found'],
                "records_removed": self.processing_stats.get('records_removed', 0),
                "final_records": self.processing_stats.get('final_count', self.original_count),
                "deduplication_rate": round((self.processing_stats.get('records_removed', 0) / self.original_count) * 100, 2)
            },
            "duplicate_groups_detail": []
        }
        
        for i, group in enumerate(self.duplicate_groups):
            group_detail = {
                "group_id": i + 1,
                "canonical_record": {
                    "person_id": group.canonical_record.person_id,
                    "person_name": group.canonical_record.person_name,
                    "name_recognition": group.canonical_record.name_recognition,
                    "quality_score": self.calculate_quality_score(group.canonical_record)
                },
                "removed_duplicates": [
                    {
                        "person_id": dup.person_id,
                        "person_name": dup.person_name,
                        "name_recognition": dup.name_recognition,
                        "quality_score": self.calculate_quality_score(dup)
                    }
                    for dup in group.duplicate_records
                ],
                "similarity_score": group.similarity_score,
                "quality_reasons": group.quality_reasons
            }
            report["duplicate_groups_detail"].append(group_detail)
        
        return report

    def save_report(self, report: Dict, output_path: Optional[str] = None) -> str:
        """レポートをファイルに保存"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"DEDUPLICATION_REPORT_{timestamp}.json"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        logger.info(f"重複削除レポート保存完了: {output_path}")
        return output_path

    def save_cleaned_data(self, cleaned_df: pd.DataFrame, output_path: Optional[str] = None) -> str:
        """クリーンなデータを保存"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            original_name = self.csv_path.stem
            output_path = f"{original_name}_DEDUPLICATED_{timestamp}.csv"
        
        cleaned_df.to_csv(output_path, index=False)
        logger.info(f"クリーンなデータベース保存完了: {output_path}")
        return output_path

def main():
    """メイン実行関数"""
    # 設定
    input_csv = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_GROUP_FIXED_20250831_185100.csv"
    
    # エンジン初期化
    engine = IntelligentDeduplicationEngine(input_csv)
    
    # 重複検出
    duplicate_groups = engine.detect_duplicates()
    
    if duplicate_groups:
        logger.info(f"\n=== 重複検出結果 ===")
        logger.info(f"重複グループ数: {len(duplicate_groups)}")
        logger.info(f"削除対象レコード数: {sum(len(g.duplicate_records) for g in duplicate_groups)}")
        
        # 特に注目すべき重複（P000141/P000142等）
        important_groups = []
        for group in duplicate_groups:
            if any('P000141' in record.person_id or 'P000142' in record.person_id 
                   for record in [group.canonical_record] + group.duplicate_records):
                important_groups.append(group)
        
        if important_groups:
            logger.info(f"\n=== 重要な重複（P000141/P000142等） ===")
            for group in important_groups:
                logger.info(f"保持: {group.canonical_record.person_name} (ID: {group.canonical_record.person_id})")
                for dup in group.duplicate_records:
                    logger.info(f"削除: {dup.person_name} (ID: {dup.person_id})")
                logger.info(f"理由: {', '.join(group.quality_reasons)}")
        
        # 重複削除実行
        cleaned_df = engine.remove_duplicates(confirm_removal=True)
        
        # レポート生成・保存
        report = engine.generate_deduplication_report()
        report_path = engine.save_report(report)
        
        # クリーンデータ保存
        output_path = engine.save_cleaned_data(cleaned_df)
        
        # 最終統計
        logger.info(f"\n=== 重複削除完了 ===")
        logger.info(f"元レコード数: {engine.original_count}")
        logger.info(f"削除レコード数: {report['deduplication_summary']['records_removed']}")
        logger.info(f"最終レコード数: {report['deduplication_summary']['final_records']}")
        logger.info(f"重複削除率: {report['deduplication_summary']['deduplication_rate']}%")
        logger.info(f"クリーンファイル: {output_path}")
        logger.info(f"詳細レポート: {report_path}")
        
        return output_path, report_path
    else:
        logger.info("重複が検出されませんでした。")
        return None, None

if __name__ == "__main__":
    main()