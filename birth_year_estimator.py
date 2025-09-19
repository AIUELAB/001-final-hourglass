#!/usr/bin/env python3
"""
生年推定ロジックの実装
複数の推定手法を組み合わせて高精度な推定を実現
"""

import pandas as pd
import numpy as np
import re
from datetime import datetime
from typing import Optional, Tuple, Dict

class BirthYearEstimator:
    """生年推定クラス"""

    def __init__(self):
        """初期化"""
        # 職業別のデビュー年齢の平均値
        self.debut_ages = {
            '俳優': 22,
            '女優': 20,
            '歌手': 20,
            'アイドル': 16,
            'お笑い芸人': 24,
            'YouTuber': 25,
            '声優': 22,
            'プロレスラー': 23,
            '野球選手': 18,
            'サッカー選手': 18,
            'バスケットボール選手': 22,
            'ボクサー': 20,
            '政治家': 40,
            '作家': 30,
            '漫画家': 25,
            '映画監督': 35,
            '実業家': 35,
        }

        # 世代キーワードと推定生年
        self.generation_patterns = {
            '一世': 1900,
            '二世': 1930,
            '三世': 1960,
            'Jr': 1965,
            'ジュニア': 1965,
            '2世': 1960,
            '3世': 1990,
        }

        # 歴史的時代と推定年代
        self.historical_periods = {
            '明治': (1868, 1912),
            '大正': (1912, 1926),
            '昭和': (1926, 1989),
            '平成': (1989, 2019),
            '令和': (2019, 2025),
            '江戸': (1603, 1868),
            '戦国': (1467, 1615),
            '鎌倉': (1185, 1333),
            '平安': (794, 1185),
        }

    def estimate_from_debut(self, row: pd.Series) -> Optional[int]:
        """デビュー年から生年を推定"""
        if pd.notna(row.get('debut_year')):
            debut_year = int(row['debut_year'])
            occupation = row.get('occupation', '')

            # 職業別のデビュー年齢を使用
            debut_age = self.debut_ages.get(occupation, 25)  # デフォルト25歳

            # 特殊ケースの調整
            if '子役' in str(row.get('person_name_ja', '')):
                debut_age = 8
            elif 'ジュニア' in str(row.get('group_name', '')):
                debut_age = 15

            estimated_birth = debut_year - debut_age

            # 妥当性チェック
            if 1800 <= estimated_birth <= 2010:
                return estimated_birth

        return None

    def estimate_from_group_members(self, row: pd.Series, df: pd.DataFrame) -> Optional[int]:
        """同じグループメンバーから生年を推定"""
        if pd.notna(row.get('group_name')):
            group_name = row['group_name']

            # 同じグループの他のメンバーを検索
            group_members = df[df['group_name'] == group_name]

            # 生年データがあるメンバーの平均を計算
            birth_years = group_members['birth_year_int'].dropna()

            if len(birth_years) >= 2:  # 2人以上のデータがある場合
                # 中央値を使用（外れ値の影響を減らす）
                estimated = int(birth_years.median())

                # グループの特性による調整
                if 'ジャニーズ' in group_name or 'Jr' in group_name:
                    # アイドルグループは年齢差が小さい
                    std = birth_years.std()
                    if std <= 3:  # 標準偏差が3年以内
                        return estimated
                else:
                    return estimated

        return None

    def estimate_from_historical_context(self, row: pd.Series) -> Optional[int]:
        """歴史的文脈から生年を推定"""
        name = str(row.get('person_name_ja', ''))
        occupation = str(row.get('occupation', ''))
        category = str(row.get('category', ''))

        # 歴史上の人物の場合
        if category == '歴史的偉人' or '天皇' in occupation:
            for period, (start, end) in self.historical_periods.items():
                if period in name or period in str(row.get('wikipedia_url', '')):
                    # 時代の中央値を使用
                    return start + (end - start) // 3  # 活動期を前半に仮定

        # 世代情報から推定
        for keyword, base_year in self.generation_patterns.items():
            if keyword in name:
                # 親の生年が分かれば、それに基づいて調整
                return base_year

        return None

    def estimate_from_activity_period(self, row: pd.Series) -> Optional[int]:
        """活動期間から生年を推定"""

        # 引退年がある場合（スポーツ選手）
        if pd.notna(row.get('retirement_year')):
            retirement = int(row['retirement_year'])
            occupation = row.get('occupation', '')

            # スポーツ選手の平均引退年齢
            retirement_ages = {
                '野球選手': 35,
                'サッカー選手': 33,
                'プロレスラー': 45,
                'ボクサー': 35,
                'バスケットボール選手': 35,
                '力士': 33,
            }

            age = retirement_ages.get(occupation, 38)
            return retirement - age

        # 受賞年から推定
        if pd.notna(row.get('award_year')):
            award_year = int(row['award_year'])
            # 受賞時の平均年齢を仮定
            return award_year - 45

        return None

    def estimate_from_name_pattern(self, row: pd.Series) -> Optional[int]:
        """名前パターンから生年を推定"""
        name = str(row.get('person_name_ja', ''))

        # 年号を含む名前（例：昭和太郎）
        if '昭和' in name:
            return 1930
        elif '平成' in name:
            return 1990
        elif '令和' in name:
            return 2019

        # 数字を含む芸名パターン
        year_match = re.search(r'(19|20)\d{2}', name)
        if year_match:
            year = int(year_match.group())
            if 1900 <= year <= 2010:
                return year

        return None

    def estimate_with_confidence(self, row: pd.Series, df: pd.DataFrame) -> Tuple[Optional[int], float]:
        """
        複数の手法で推定し、信頼度スコアを返す

        Returns:
            (推定生年, 信頼度スコア 0-100)
        """
        estimates = []
        weights = []

        # 1. デビュー年からの推定（高信頼度）
        debut_est = self.estimate_from_debut(row)
        if debut_est:
            estimates.append(debut_est)
            weights.append(0.8)

        # 2. グループメンバーからの推定（高信頼度）
        group_est = self.estimate_from_group_members(row, df)
        if group_est:
            estimates.append(group_est)
            weights.append(0.9)

        # 3. 活動期間からの推定（中信頼度）
        activity_est = self.estimate_from_activity_period(row)
        if activity_est:
            estimates.append(activity_est)
            weights.append(0.6)

        # 4. 歴史的文脈からの推定（中信頼度）
        historical_est = self.estimate_from_historical_context(row)
        if historical_est:
            estimates.append(historical_est)
            weights.append(0.5)

        # 5. 名前パターンからの推定（低信頼度）
        name_est = self.estimate_from_name_pattern(row)
        if name_est:
            estimates.append(name_est)
            weights.append(0.3)

        if estimates:
            # 加重平均で最終推定値を計算
            weighted_sum = sum(e * w for e, w in zip(estimates, weights))
            total_weight = sum(weights)
            final_estimate = int(weighted_sum / total_weight)

            # 信頼度スコア（0-100）
            confidence = min(100, total_weight * 30)  # 複数の手法で一致すれば高スコア

            # 推定値のばらつきが小さければ信頼度を上げる
            if len(estimates) > 1:
                std = np.std(estimates)
                if std < 5:
                    confidence = min(100, confidence + 20)
                elif std > 20:
                    confidence = max(0, confidence - 30)

            return final_estimate, confidence

        return None, 0

def apply_estimation(csv_file: str):
    """推定ロジックを適用"""

    print("=" * 80)
    print("🎯 生年推定ロジック適用")
    print("=" * 80)

    # データ読み込み
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    estimator = BirthYearEstimator()

    # 生年データがない記録に推定を適用
    no_birth_mask = df['birth_year_int'].isna()
    targets = df[no_birth_mask].copy()

    print(f"\n📊 処理対象: {len(targets):,}件")

    success_count = 0
    high_confidence = 0
    medium_confidence = 0
    low_confidence = 0

    # 推定結果を保存
    estimation_results = []

    for idx, row in targets.iterrows():
        estimated_year, confidence = estimator.estimate_with_confidence(row, df)

        if estimated_year:
            success_count += 1
            df.at[idx, 'birth_year_int'] = estimated_year
            df.at[idx, 'estimation_confidence'] = confidence
            df.at[idx, 'is_estimated'] = True

            # 信頼度別カウント
            if confidence >= 70:
                high_confidence += 1
                status = "高"
            elif confidence >= 40:
                medium_confidence += 1
                status = "中"
            else:
                low_confidence += 1
                status = "低"

            estimation_results.append({
                'person_name': row['person_name_ja'],
                'estimated_year': estimated_year,
                'confidence': confidence,
                'status': status
            })

            if success_count % 100 == 0:
                print(f"  処理済み: {success_count:,}件")

    # 結果サマリー
    print("\n" + "=" * 80)
    print("📊 推定結果サマリー")
    print("=" * 80)
    print(f"✅ 推定成功: {success_count:,}件 / {len(targets):,}件")
    print(f"  - 高信頼度（70%以上）: {high_confidence:,}件")
    print(f"  - 中信頼度（40-69%）: {medium_confidence:,}件")
    print(f"  - 低信頼度（40%未満）: {low_confidence:,}件")

    # 新しいカバー率
    total_with_birth = df['birth_year_int'].notna().sum()
    coverage = total_with_birth / len(df) * 100
    print(f"\n📈 新カバー率: {coverage:.1f}%")
    print(f"   （推定前: {(total_with_birth - success_count) / len(df) * 100:.1f}%）")

    # 結果を保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f"ultra_think_WITH_ESTIMATED_BIRTH_{timestamp}.csv"
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"\n💾 保存先: {output_file}")

    # 推定結果の詳細を別ファイルに保存
    if estimation_results:
        details_df = pd.DataFrame(estimation_results)
        details_file = f"estimation_details_{timestamp}.csv"
        details_df.to_csv(details_file, index=False, encoding='utf-8-sig')
        print(f"📝 推定詳細: {details_file}")

    return df

if __name__ == "__main__":
    # 最新のCSVファイルで実行
    csv_file = "ultra_think_WITH_BIRTH_DATES_BATCH5_20250917_094115.csv"
    result_df = apply_estimation(csv_file)