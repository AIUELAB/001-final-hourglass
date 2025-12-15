#!/usr/bin/env python3
"""
初心者向け：現実的な知名度評価システム
サンプリング戦略とハイブリッド方式を使用した効率的な実装
"""

import pandas as pd
import numpy as np
import random
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple

class SimpleRecognitionSystem:
    """初心者向けのシンプルな知名度評価システム"""

    def __init__(self):
        """システムの初期化"""
        print("="*60)
        print("🚀 シンプル知名度評価システム v2.0")
        print("="*60)
        print()

        self.results = []
        self.api_call_count = 0
        self.ml_call_count = 0
        self.start_time = datetime.now()

        # 有名人リスト（判定の基準として使用）
        self.known_celebrities = {
            # 超有名人（スコア9.0以上）
            "HIKAKIN": 9.5,
            "はじめしゃちょー": 9.2,
            "大谷翔平": 9.8,
            "新垣結衣": 9.0,
            "米津玄師": 9.1,

            # 有名人（スコア7.0-9.0）
            "フィッシャーズ": 8.5,
            "東海オンエア": 8.3,
            "水溜りボンド": 8.0,
            "ヒカル": 8.4,
            "ラファエル": 7.8,

            # 中堅（スコア5.0-7.0）
            "コムドット": 7.2,
            "平成フラミンゴ": 6.5,
            "スカイピース": 6.8,
        }

        print("✅ システム初期化完了")
        print(f"📅 開始時刻: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

    def load_data(self, filename: str) -> pd.DataFrame:
        """CSVファイルを読み込む"""
        print(f"📂 データ読み込み中: {filename}")

        try:
            # CSVを読み込む
            self.data = pd.read_csv(filename, encoding='utf-8')
            print(f"✅ {len(self.data):,}件のデータを読み込みました")

            # データの概要を表示
            print("\n📊 データ概要:")
            print(f"  - カラム数: {len(self.data.columns)}")
            print(f"  - 主要カラム: {', '.join(self.data.columns[:5])}")

            return self.data

        except FileNotFoundError:
            print(f"❌ エラー: ファイル '{filename}' が見つかりません")
            print("💡 ヒント: ファイル名とパスを確認してください")
            return pd.DataFrame()
        except Exception as e:
            print(f"❌ エラー: {e}")
            return pd.DataFrame()

    def categorize_by_priority(self) -> Dict[str, List]:
        """優先度別にデータを分類"""
        print("\n🎯 優先度別分類を開始...")

        categories = {
            "level_1_critical": [],    # 絶対調査（超有名人）
            "level_2_important": [],   # 重要調査（有名人）
            "level_3_standard": [],    # 標準調査（中堅）
            "level_4_simple": []       # 簡易調査（その他）
        }

        for idx, row in self.data.iterrows():
            person_name = row.get('person_name', '')

            # 既知の有名人チェック
            if person_name in self.known_celebrities:
                score = self.known_celebrities[person_name]
                if score >= 9.0:
                    categories["level_1_critical"].append(idx)
                elif score >= 7.0:
                    categories["level_2_important"].append(idx)
                elif score >= 5.0:
                    categories["level_3_standard"].append(idx)
                else:
                    categories["level_4_simple"].append(idx)
            else:
                # ランダムに振り分け（実際はより高度な判定を使用）
                rand = random.random()
                if rand < 0.01:  # 1%
                    categories["level_1_critical"].append(idx)
                elif rand < 0.05:  # 4%
                    categories["level_2_important"].append(idx)
                elif rand < 0.20:  # 15%
                    categories["level_3_standard"].append(idx)
                else:  # 80%
                    categories["level_4_simple"].append(idx)

        # 結果を表示
        print("\n📊 分類結果:")
        print(f"  🔴 Level 1 (最優先): {len(categories['level_1_critical']):,}人")
        print(f"  🟠 Level 2 (重要): {len(categories['level_2_important']):,}人")
        print(f"  🟡 Level 3 (標準): {len(categories['level_3_standard']):,}人")
        print(f"  🟢 Level 4 (簡易): {len(categories['level_4_simple']):,}人")

        self.categories = categories
        return categories

    def select_smart_sample(self, total_sample: int = 500) -> pd.DataFrame:
        """スマートサンプリング：各カテゴリから比例配分で選択"""
        print(f"\n🎲 スマートサンプリング開始（目標: {total_sample}人）")

        # 各レベルからの抽出比率
        sampling_ratios = {
            "level_1_critical": 1.0,    # 100%抽出
            "level_2_important": 0.5,    # 50%抽出
            "level_3_standard": 0.2,     # 20%抽出
            "level_4_simple": 0.05       # 5%抽出
        }

        sample_indices = []

        for level, indices in self.categories.items():
            ratio = sampling_ratios[level]

            # このレベルから選ぶ数を計算
            if level == "level_1_critical":
                # Level 1は全員選ぶ
                selected = indices
            else:
                # 他のレベルは比率に応じて選ぶ
                sample_size = min(int(len(indices) * ratio), len(indices))
                selected = random.sample(indices, sample_size) if sample_size > 0 else []

            sample_indices.extend(selected)
            print(f"  {level}: {len(selected):,}人を選択")

        # 目標数に調整
        if len(sample_indices) > total_sample:
            # 多すぎる場合は優先度の低いものから削る
            sample_indices = sample_indices[:total_sample]
        elif len(sample_indices) < total_sample:
            # 少ない場合は追加で選ぶ
            remaining = total_sample - len(sample_indices)
            all_indices = set(range(len(self.data)))
            available = list(all_indices - set(sample_indices))
            if available:
                additional = random.sample(available, min(remaining, len(available)))
                sample_indices.extend(additional)

        self.sample = self.data.iloc[sample_indices]
        print(f"\n✅ 最終サンプル数: {len(self.sample):,}人")

        return self.sample

    def calculate_ml_score(self, person_data: pd.Series) -> float:
        """機械学習による知名度スコア推定（簡易版）"""
        person_name = person_data.get('person_name', '')

        # 既知の有名人なら既定のスコアを返す
        if person_name in self.known_celebrities:
            base_score = self.known_celebrities[person_name]
        else:
            # 簡易的な推定ロジック
            features_score = 0.0

            # 名前の長さ（長い名前は団体名の可能性）
            if len(person_name) > 10:
                features_score += 0.5

            # カタカナ比率（外国人名の可能性）
            katakana_count = sum(1 for c in person_name if 'ァ' <= c <= 'ヶ')
            if katakana_count > len(person_name) * 0.5:
                features_score += 0.3

            # ひらがな比率（日本人の芸名の可能性）
            hiragana_count = sum(1 for c in person_name if 'ぁ' <= c <= 'ん')
            if hiragana_count == len(person_name):
                features_score += 0.4

            # 基本スコア（3.0〜6.0の範囲）
            base_score = 3.0 + features_score + random.uniform(0, 3.0)

        # ノイズを追加（より現実的に）
        noise = random.uniform(-0.2, 0.2)
        final_score = max(0.0, min(10.0, base_score + noise))

        self.ml_call_count += 1
        return round(final_score, 2)

    def simulate_api_call(self, person_data: pd.Series) -> float:
        """API呼び出しのシミュレーション（実際のAPIの代替）"""
        person_name = person_data.get('person_name', '')

        # API呼び出しの遅延をシミュレート（実際はもっと長い）
        time.sleep(0.1)  # 0.1秒の遅延

        # MLスコアをベースに、より詳細な調査結果を追加
        ml_score = self.calculate_ml_score(person_data)

        # API調査による追加情報（シミュレーション）
        search_results = random.randint(100, 1000000)  # 検索結果数
        wikipedia_exists = random.random() < (ml_score / 10)  # Wikipedia記事の有無
        news_mentions = random.randint(0, 100) if ml_score > 5 else 0  # ニュース言及数

        # 総合スコアを計算
        api_boost = 0.0
        if search_results > 100000:
            api_boost += 1.0
        if wikipedia_exists:
            api_boost += 0.5
        if news_mentions > 10:
            api_boost += 0.5

        final_score = min(10.0, ml_score + api_boost)

        self.api_call_count += 1
        return round(final_score, 2)

    def process_hybrid(self):
        """ハイブリッド処理：API＋ML組み合わせ"""
        print("\n" + "="*60)
        print("🔄 ハイブリッド処理を開始")
        print("="*60)

        # Phase 1: サンプルをAPI処理
        print("\n【Phase 1】サンプルのAPI処理（詳細調査）")
        print("-"*40)

        sample_ids = set(self.sample.index)
        processed_count = 0

        for idx in sample_ids:
            row = self.data.iloc[idx]
            person_name = row.get('person_name', f'Person_{idx}')

            # API処理
            score = self.simulate_api_call(row)

            self.results.append({
                'person_id': row.get('person_id', f'P{idx:06d}'),
                'person_name': person_name,
                'recognition_score': score,
                'processing_method': 'API',
                'confidence': 'HIGH'
            })

            processed_count += 1

            # 進捗表示
            if processed_count % 50 == 0 or processed_count == len(sample_ids):
                progress = (processed_count / len(sample_ids)) * 100
                print(f"  進捗: {processed_count:,}/{len(sample_ids):,} ({progress:.1f}%)")

        # Phase 2: 残りをML処理
        print("\n【Phase 2】残りのML処理（高速推定）")
        print("-"*40)

        ml_count = 0
        total_ml = len(self.data) - len(sample_ids)

        for idx, row in self.data.iterrows():
            if idx not in sample_ids:
                person_name = row.get('person_name', f'Person_{idx}')

                # ML処理
                score = self.calculate_ml_score(row)

                # 信頼度を判定
                if person_name in self.known_celebrities:
                    confidence = 'HIGH'
                elif score > 7.0 or score < 3.0:
                    confidence = 'MEDIUM'
                else:
                    confidence = 'LOW'

                self.results.append({
                    'person_id': row.get('person_id', f'P{idx:06d}'),
                    'person_name': person_name,
                    'recognition_score': score,
                    'processing_method': 'ML',
                    'confidence': confidence
                })

                ml_count += 1

                # 進捗表示
                if ml_count % 500 == 0 or ml_count == total_ml:
                    progress = (ml_count / total_ml) * 100
                    print(f"  進捗: {ml_count:,}/{total_ml:,} ({progress:.1f}%)")

        # 処理完了
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()

        print("\n" + "="*60)
        print("✅ 処理完了！")
        print("="*60)
        print(f"\n📊 処理統計:")
        print(f"  - 処理時間: {duration:.1f}秒")
        print(f"  - API処理: {self.api_call_count:,}件")
        print(f"  - ML処理: {self.ml_call_count:,}件")
        print(f"  - 合計: {len(self.results):,}件")
        print(f"  - 処理速度: {len(self.results)/duration:.1f}件/秒")

    def quality_check(self) -> bool:
        """品質チェック"""
        print("\n🔍 品質チェックを実行中...")

        df = pd.DataFrame(self.results)
        issues = []

        # 1. 有名人のスコアチェック
        for celebrity, expected_score in self.known_celebrities.items():
            celebrity_data = df[df['person_name'] == celebrity]
            if not celebrity_data.empty:
                actual_score = celebrity_data['recognition_score'].values[0]
                if abs(actual_score - expected_score) > 2.0:
                    issues.append(f"{celebrity}: 期待値{expected_score} vs 実際{actual_score}")

        # 2. スコア分布チェック
        high_score = (df['recognition_score'] > 7.0).sum()
        low_score = (df['recognition_score'] < 3.0).sum()
        high_ratio = high_score / len(df)
        low_ratio = low_score / len(df)

        print(f"\n📊 スコア分布:")
        print(f"  - 高スコア(>7.0): {high_score:,}人 ({high_ratio*100:.1f}%)")
        print(f"  - 中スコア(3-7): {len(df) - high_score - low_score:,}人")
        print(f"  - 低スコア(<3.0): {low_score:,}人 ({low_ratio*100:.1f}%)")

        # 3. 信頼度分布
        confidence_dist = df['confidence'].value_counts()
        print(f"\n🎯 信頼度分布:")
        for conf, count in confidence_dist.items():
            print(f"  - {conf}: {count:,}件 ({count/len(df)*100:.1f}%)")

        # 4. 問題点の報告
        if issues:
            print(f"\n⚠️ 検出された問題:")
            for issue in issues[:5]:  # 最初の5件のみ表示
                print(f"  - {issue}")
        else:
            print("\n✅ 重大な問題は検出されませんでした")

        # 妥当性判定
        if high_ratio > 0.5:
            print("\n⚠️ 注意: 高スコアが多すぎる可能性があります")
            return False
        elif low_ratio > 0.7:
            print("\n⚠️ 注意: 低スコアが多すぎる可能性があります")
            return False
        else:
            print("\n✅ スコア分布は妥当な範囲内です")
            return True

    def save_results(self) -> str:
        """結果を保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"simple_recognition_results_{timestamp}.csv"

        print(f"\n💾 結果を保存中: {filename}")

        # DataFrameに変換
        df = pd.DataFrame(self.results)

        # スコアでソート（降順）
        df = df.sort_values('recognition_score', ascending=False)

        # UTF-8 BOM付きで保存（Excel対応）
        df.to_csv(filename, index=False, encoding='utf-8-sig')

        print(f"✅ 保存完了！")

        # トップ10を表示
        print("\n🏆 トップ10の知名度スコア:")
        print("-"*50)
        for i, row in df.head(10).iterrows():
            print(f"{row['person_name'][:20]:20} | スコア: {row['recognition_score']:.2f} | {row['processing_method']}")

        return filename

    def generate_report(self):
        """最終レポートを生成"""
        print("\n" + "="*60)
        print("📋 最終レポート")
        print("="*60)

        df = pd.DataFrame(self.results)

        print(f"\n【処理サマリー】")
        print(f"  処理日時: {self.start_time.strftime('%Y年%m月%d日 %H:%M')}")
        print(f"  総処理数: {len(df):,}件")
        print(f"  API処理: {self.api_call_count:,}件")
        print(f"  ML処理: {self.ml_call_count:,}件")

        print(f"\n【スコア統計】")
        print(f"  平均スコア: {df['recognition_score'].mean():.2f}")
        print(f"  中央値: {df['recognition_score'].median():.2f}")
        print(f"  標準偏差: {df['recognition_score'].std():.2f}")
        print(f"  最高スコア: {df['recognition_score'].max():.2f}")
        print(f"  最低スコア: {df['recognition_score'].min():.2f}")

        print(f"\n【処理方法別統計】")
        method_stats = df.groupby('processing_method')['recognition_score'].agg(['count', 'mean'])
        for method, stats in method_stats.iterrows():
            print(f"  {method}: {int(stats['count']):,}件（平均: {stats['mean']:.2f}）")

        print("\n" + "="*60)
        print("🎉 すべての処理が完了しました！")
        print("="*60)


def main():
    """メイン実行関数"""
    print("\n" + "🌟"*30)
    print(" "*10 + "知名度評価システム（簡易版）")
    print("🌟"*30 + "\n")

    # システム初期化
    system = SimpleRecognitionSystem()

    # データ読み込み
    data_file = "ultra_think_EPISODE_FINAL_20250901_020106_fixed.csv"
    data = system.load_data(data_file)

    if data.empty:
        print("❌ データの読み込みに失敗しました。終了します。")
        return

    # 優先度別分類
    system.categorize_by_priority()

    # スマートサンプリング
    system.select_smart_sample(500)

    # ハイブリッド処理実行
    system.process_hybrid()

    # 品質チェック
    system.quality_check()

    # 結果保存
    output_file = system.save_results()

    # 最終レポート
    system.generate_report()

    print(f"\n📁 出力ファイル: {output_file}")
    print("👉 ExcelやGoogle Sheetsで開いて確認してください")


if __name__ == "__main__":
    main()
