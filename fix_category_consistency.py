#!/usr/bin/env python3
"""
カテゴリ整合性修正スクリプト
occupation（職業）に基づいて正しいmain_category/subcategoryを割り当てる
"""

import json
import csv
from datetime import datetime
from typing import Dict, Tuple, List
from collections import defaultdict


class CategoryConsistencyFixer:
    """カテゴリ整合性修正クラス"""
    
    def __init__(self):
        # 包括的なoccupation → category マッピング
        self.category_mapping = {
            # 音楽関連
            '作曲家': ('音楽', '作曲家'),
            '歌手': ('音楽', '歌手'),
            '音楽家': ('音楽', '音楽家'),
            'ミュージシャン': ('音楽', 'ミュージシャン'),
            'ピアニスト': ('音楽', 'ピアニスト'),
            'バイオリニスト': ('音楽', 'バイオリニスト'),
            '指揮者': ('音楽', '指揮者'),
            'DJ': ('音楽', 'DJ'),
            
            # 科学・技術
            '科学者': ('科学・技術', '科学者'),
            '物理学者': ('科学・技術', '物理学者'),
            '化学者': ('科学・技術', '化学者'),
            '生物学者': ('科学・技術', '生物学者'),
            '数学者': ('科学・技術', '数学者'),
            '天文学者': ('科学・技術', '天文学者'),
            '医師': ('医学', '医師'),
            '研究者': ('科学・技術', '研究者'),
            '発明家': ('科学・技術', '発明家'),
            '技術者': ('科学・技術', '技術者'),
            
            # 政治・社会
            '政治家': ('政治・社会', '政治家'),
            '大統領': ('政治・社会', '大統領'),
            '首相': ('政治・社会', '首相'),
            '知事': ('政治・社会', '知事'),
            '市長': ('政治・社会', '市長'),
            '外交官': ('政治・社会', '外交官'),
            '活動家': ('政治・社会', '活動家'),
            
            # 文学
            '作家': ('文学', '作家'),
            '小説家': ('文学', '小説家'),
            '詩人': ('文学', '詩人'),
            '劇作家': ('文学', '劇作家'),
            'ライター': ('文学', 'ライター'),
            'ジャーナリスト': ('文学', 'ジャーナリスト'),
            
            # 芸能・エンターテインメント
            '俳優': ('芸能', '俳優'),
            '女優': ('芸能', '女優'),
            '映画俳優': ('芸能', '映画俳優'),
            '舞台俳優': ('芸能', '舞台俳優'),
            '子役': ('芸能', '子役'),
            '声優': ('芸能', '声優'),
            'お笑い芸人': ('芸能', 'お笑い芸人'),
            'お笑い芸人（R-1）': ('芸能', 'お笑い芸人'),
            'コメディアン': ('芸能', 'コメディアン'),
            'タレント': ('芸能', 'タレント'),
            'アイドル': ('芸能', 'アイドル'),
            
            # スポーツ
            '野球選手': ('スポーツ', '野球'),
            'サッカー選手': ('スポーツ', 'サッカー'),
            'テニス選手': ('スポーツ', 'テニス'),
            '陸上選手': ('スポーツ', '陸上'),
            '水泳選手': ('スポーツ', '水泳'),
            'ボクサー': ('スポーツ', 'ボクシング'),
            'プロレスラー': ('スポーツ', 'プロレス'),
            'ゴルファー': ('スポーツ', 'ゴルフ'),
            'フィギュアスケート選手': ('スポーツ', 'フィギュアスケート'),
            'バスケットボール選手': ('スポーツ', 'バスケットボール'),
            'バレーボール選手': ('スポーツ', 'バレーボール'),
            'スポーツ選手': ('スポーツ', 'その他'),
            'アスリート': ('スポーツ', 'その他'),
            'eスポーツ選手': ('スポーツ', 'eスポーツ'),
            
            # 芸術
            '画家': ('芸術', '画家'),
            '彫刻家': ('芸術', '彫刻家'),
            '建築家': ('芸術', '建築家'),
            'デザイナー': ('芸術', 'デザイナー'),
            '写真家': ('芸術', '写真家'),
            '芸術家': ('芸術', '芸術家'),
            
            # 映画・アニメ
            '映画監督': ('映画・アニメ', '映画監督'),
            'アニメ監督': ('映画・アニメ', 'アニメ監督'),
            '監督': ('映画・アニメ', '監督'),
            'プロデューサー': ('映画・アニメ', 'プロデューサー'),
            '脚本家': ('映画・アニメ', '脚本家'),
            '漫画家': ('映画・アニメ', '漫画家'),
            'アニメーター': ('映画・アニメ', 'アニメーター'),
            
            # ビジネス
            '実業家': ('ビジネス', '実業家'),
            '起業家': ('ビジネス', '起業家'),
            '経営者': ('ビジネス', '経営者'),
            'CEO': ('ビジネス', 'CEO'),
            '投資家': ('ビジネス', '投資家'),
            
            # デジタル・メディア
            'YouTuber': ('デジタルメディア', 'YouTuber'),
            'TikToker': ('デジタルメディア', 'TikToker'),
            'インフルエンサー': ('デジタルメディア', 'インフルエンサー'),
            'ブロガー': ('デジタルメディア', 'ブロガー'),
            
            # 軍事・歴史
            '軍人': ('軍事・歴史', '軍人'),
            '将軍': ('軍事・歴史', '将軍'),
            '提督': ('軍事・歴史', '提督'),
            '古代ローマ軍人': ('軍事・歴史', '古代ローマ軍人'),
            '古代ローマ政治家': ('軍事・歴史', '古代ローマ政治家'),
            '武将': ('軍事・歴史', '武将'),
            '軍事指導者': ('軍事・歴史', '軍事指導者'),
            
            # 王室・貴族
            '国王': ('王室・貴族', '国王'),
            '女王': ('王室・貴族', '女王'),
            '皇帝': ('王室・貴族', '皇帝'),
            '君主': ('王室・貴族', '君主'),
            '王子': ('王室・貴族', '王子'),
            '王女': ('王室・貴族', '王女'),
            '統治者': ('王室・貴族', '統治者'),
            
            # 宗教・哲学
            '哲学者': ('哲学・思想', '哲学者'),
            '宗教家': ('宗教', '宗教家'),
            '僧侶': ('宗教', '僧侶'),
            '牧師': ('宗教', '牧師'),
            '思想家': ('哲学・思想', '思想家'),
            
            # 教育
            '教師': ('教育', '教師'),
            '教授': ('教育', '教授'),
            '教育者': ('教育', '教育者'),
            
            # 法律
            '弁護士': ('法律', '弁護士'),
            '裁判官': ('法律', '裁判官'),
            '検察官': ('法律', '検察官'),
            
            # その他
            '探検家': ('その他', '探検家'),
            '冒険家': ('その他', '冒険家'),
            'パイロット': ('その他', 'パイロット'),
            '宇宙飛行士': ('その他', '宇宙飛行士'),
        }
        
        self.stats = {
            'total': 0,
            'fixed': 0,
            'already_correct': 0,
            'no_occupation': 0,
            'unknown_occupation': 0,
            'category_distribution': defaultdict(int)
        }
    
    def get_correct_category(self, occupation: str) -> Tuple[str, str]:
        """職業から正しいカテゴリを取得"""
        
        # 完全一致を試みる
        if occupation in self.category_mapping:
            return self.category_mapping[occupation]
        
        # 部分一致を試みる（例：「作曲家・編曲家」→「作曲家」）
        for key, value in self.category_mapping.items():
            if key in occupation:
                return value
        
        # マッピングが見つからない場合
        return None, None
    
    def fix_categories(self, input_file: str) -> str:
        """カテゴリを修正"""
        
        print("🔧 カテゴリ整合性修正開始")
        print(f"  入力: {input_file}")
        
        # データ読み込み
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.stats['total'] = len(data)
        
        # カテゴリ修正
        for key, value in data.items():
            if isinstance(value, dict):
                occupation = value.get('occupation', '')
                
                if not occupation:
                    self.stats['no_occupation'] += 1
                    continue
                
                # 正しいカテゴリを取得
                main_cat, sub_cat = self.get_correct_category(occupation)
                
                if main_cat and sub_cat:
                    # 既存のカテゴリと比較
                    old_main = value.get('main_category', '')
                    old_sub = value.get('subcategory', '')
                    
                    if old_main == main_cat and old_sub == sub_cat:
                        self.stats['already_correct'] += 1
                    else:
                        # カテゴリを更新
                        value['main_category'] = main_cat
                        value['subcategory'] = sub_cat
                        self.stats['fixed'] += 1
                    
                    self.stats['category_distribution'][main_cat] += 1
                else:
                    self.stats['unknown_occupation'] += 1
                    # 未知の職業は現状維持
        
        # 結果を保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"category_fixed_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"\n✅ 修正完了: {output_file}")
        
        # CSV出力
        csv_file = self.export_to_csv(data, timestamp)
        
        # 統計表示
        self.display_stats()
        
        return output_file, csv_file
    
    def export_to_csv(self, data: Dict, timestamp: str) -> str:
        """CSVファイルとして出力"""
        
        csv_file = f"category_fixed_{timestamp}.csv"
        
        # フィールド収集
        all_fields = set()
        for value in data.values():
            if isinstance(value, dict):
                all_fields.update(value.keys())
        
        # フィールド順序
        priority_fields = ['id', 'name', 'original_name', 'person_name_ja', 
                          'occupation', 'main_category', 'subcategory',
                          'birth_date', 'death_date', 'nationality']
        other_fields = sorted(all_fields - set(priority_fields))
        fieldnames = [f for f in priority_fields if f in all_fields] + other_fields
        
        # CSV書き込み
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for key, value in data.items():
                if isinstance(value, dict):
                    row = {field: value.get(field, '') for field in fieldnames}
                    if 'id' not in row or not row['id']:
                        row['id'] = key
                    writer.writerow(row)
        
        print(f"  CSV出力: {csv_file}")
        return csv_file
    
    def display_stats(self):
        """統計情報を表示"""
        
        print("\n📊 修正統計:")
        print(f"  総レコード数: {self.stats['total']:,}件")
        print(f"  修正済み: {self.stats['fixed']:,}件 ({self.stats['fixed']/self.stats['total']*100:.1f}%)")
        print(f"  既に正しい: {self.stats['already_correct']:,}件 ({self.stats['already_correct']/self.stats['total']*100:.1f}%)")
        print(f"  職業なし: {self.stats['no_occupation']:,}件")
        print(f"  未知の職業: {self.stats['unknown_occupation']:,}件")
        
        print("\n📈 カテゴリ分布（修正後）:")
        sorted_cats = sorted(self.stats['category_distribution'].items(), 
                           key=lambda x: x[1], reverse=True)
        for i, (cat, count) in enumerate(sorted_cats[:15], 1):
            percentage = count / self.stats['total'] * 100
            print(f"  {i:2}. {cat:20} {count:5,}件 ({percentage:5.1f}%)")


def main():
    """メイン実行"""
    fixer = CategoryConsistencyFixer()
    
    # 最新のデータファイルを使用
    input_file = 'final_translated_20250825_100424.json'
    
    json_file, csv_file = fixer.fix_categories(input_file)
    
    print("\n🎯 カテゴリ整合性修正完了！")
    print(f"  JSON: {json_file}")
    print(f"  CSV: {csv_file}")
    print("\n次のステップ: validate_categories.pyで検証を実行")


if __name__ == "__main__":
    main()