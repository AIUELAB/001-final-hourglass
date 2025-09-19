#!/usr/bin/env python3
"""
name_recognition（知名度）スコアリングシステム
日本人（10代後半〜60代）における認知度を0-100で数値化
アプリで優先表示すべき人物を選定するための指標
"""

import pandas as pd
from datetime import datetime
import json
from typing import Dict, Optional

# 特定有名人の個別スコア（最優先）
SPECIFIC_RECOGNITION_SCORES = {
    # 100点：日本人なら誰でも知っている
    '天皇陛下': 100,
    'ドラえもん': 100,
    'サザエさん': 99,
    'ピカチュウ': 98,
    
    # 歴史上の超有名人物（95-98）
    '織田信長': 98,
    '豊臣秀吉': 97,
    '徳川家康': 98,
    '坂本龍馬': 94,
    '西郷隆盛': 92,
    '聖徳太子': 95,
    '源頼朝': 90,
    '平清盛': 88,
    '武田信玄': 90,
    '上杉謙信': 89,
    '伊達政宗': 91,
    
    # 現代の超有名人（90-98）
    '大谷翔平': 98,
    'イチロー': 96,
    '安倍晋三': 95,
    '小泉純一郎': 90,
    '田中角栄': 85,
    
    # エンタメ界のレジェンド（85-95）
    'タモリ': 95,
    '明石家さんま': 96,
    'ビートたけし': 95,
    '所ジョージ': 88,
    'みのもんた': 82,
    '黒柳徹子': 90,
    'タモリ': 94,
    '松本人志': 92,
    '浜田雅功': 91,
    '志村けん': 93,
    '加藤茶': 85,
    
    # スポーツ界のスター（80-95）
    '長嶋茂雄': 92,
    '王貞治': 93,
    '野村克也': 85,
    '松井秀喜': 88,
    '野茂英雄': 85,
    '中田英寿': 83,
    '本田圭佑': 82,
    '香川真司': 78,
    '錦織圭': 85,
    '羽生結弦': 92,
    '浅田真央': 90,
    '福原愛': 85,
    '吉田沙保里': 82,
    '内村航平': 78,
    '北島康介': 82,
    
    # 音楽界（70-90）
    '米津玄師': 85,
    'YOASOBI': 82,
    'あいみょん': 78,
    '藤井風': 72,
    'Ado': 75,
    '宇多田ヒカル': 88,
    '安室奈美恵': 90,
    '浜崎あゆみ': 85,
    'SMAP': 94,
    '嵐': 92,
    'AKB48': 88,
    '乃木坂46': 75,
    'B\'z': 85,
    'Mr.Children': 86,
    'サザンオールスターズ': 88,
    'YOSHIKI': 82,
    'GACKT': 75,
    '西川貴教': 72,
    '福山雅治': 88,
    '星野源': 82,
    
    # 俳優・女優（70-90）
    '木村拓哉': 94,
    '福山雅治': 88,
    '山田孝之': 78,
    '綾瀬はるか': 85,
    '新垣結衣': 88,
    '石原さとみ': 85,
    '北川景子': 82,
    '広瀬すず': 80,
    '橋本環奈': 78,
    '渡辺謙': 85,
    '役所広司': 82,
    '西田敏行': 85,
    
    # YouTuber/インフルエンサー（50-85）
    'HIKAKIN': 82,
    'はじめしゃちょー': 75,
    'ヒカル': 70,
    'コムドット': 65,
    'フィッシャーズ': 72,
    '東海オンエア': 70,
    'QuizKnock': 68,
    '水溜りボンド': 65,
    
    # VTuber（30-70）※若年層では高いが全体では低め
    'キズナアイ': 55,
    '兎田ぺこら': 45,
    '宝鐘マリン': 42,
    'ホロライブ': 48,
    'にじさんじ': 45,
    
    # 文化人（60-85）
    '村上春樹': 82,
    '東野圭吾': 78,
    '宮崎駿': 95,
    '新海誠': 85,
    '庵野秀明': 75,
    '鳥山明': 90,
    '尾田栄一郎': 85,
    '岸本斉史': 78,
    
    # 実業家（60-90）
    '孫正義': 85,
    '柳井正': 75,
    '三木谷浩史': 72,
    '堀江貴文': 78,
    '前澤友作': 75,
    '松下幸之助': 82,
    '本田宗一郎': 80,
    '稲盛和夫': 72,
}

# 職業カテゴリ別の基本スコア
OCCUPATION_BASE_SCORES = {
    # 政治・皇室（80-100）
    '天皇': 100,
    '皇族': 90,
    '首相': 85,
    '政治家': 60,
    
    # 歴史（60-90）
    '武将': 75,
    '将軍': 75,
    '大名': 70,
    '志士': 70,
    '新選組': 72,
    '忍者': 68,
    '剣豪': 65,
    '歴史上の人物': 65,
    
    # スポーツ（50-80）
    '野球選手': 65,
    'サッカー選手': 62,
    'オリンピック選手': 60,
    'プロゴルファー': 55,
    'テニス選手': 58,
    'ボクサー': 55,
    '力士': 52,
    'プロレスラー': 50,
    '格闘家': 48,
    'フィギュアスケート選手': 65,
    '水泳選手': 55,
    '陸上選手': 52,
    'マラソン選手': 50,
    '柔道家': 52,
    'レスリング選手': 50,
    '卓球選手': 48,
    'バドミントン選手': 45,
    'バスケットボール選手': 48,
    'バレーボール選手': 45,
    'ラグビー選手': 48,
    'スピードスケート選手': 45,
    '体操選手': 50,
    'ウィンタースポーツ選手': 45,
    '騎手': 45,
    'レーシングドライバー': 48,
    
    # エンタメ（40-80）
    'お笑い芸人': 65,
    'タレント': 60,
    '俳優': 58,
    '女優': 58,
    '歌手': 55,
    'ミュージシャン': 52,
    'アイドル': 50,
    '声優': 42,
    'モデル': 45,
    'アナウンサー': 48,
    'キャスター': 50,
    '司会者': 55,
    
    # 文化・芸術（40-70）
    '作家': 55,
    '小説家': 55,
    '漫画家': 58,
    '映画監督': 52,
    'アニメ監督': 50,
    '画家': 45,
    '芸術家': 45,
    '音楽家': 48,
    '作曲家': 48,
    '指揮者': 42,
    'ピアニスト': 42,
    'バイオリニスト': 40,
    '建築家': 42,
    'デザイナー': 42,
    '写真家': 40,
    
    # インターネット（20-70）
    'YouTuber': 45,
    'VTuber': 35,
    'TikToker': 38,
    'インフルエンサー': 40,
    'ブロガー': 30,
    
    # 学術・専門職（30-60）
    '医師': 35,
    '医学者': 40,
    '科学者': 42,
    '物理学者': 40,
    '化学者': 38,
    '生物学者': 38,
    '数学者': 35,
    '哲学者': 38,
    '経済学者': 35,
    '教育者': 32,
    '宗教家': 38,
    '僧侶': 35,
    
    # ビジネス（30-60）
    '実業家': 48,
    '起業家': 45,
    '経営者': 42,
    'CEO': 42,
    
    # 伝統芸能（35-60）
    '歌舞伎役者': 48,
    '落語家': 45,
    '狂言師': 42,
    '能楽師': 40,
    '茶人': 38,
    '華道家': 35,
    
    # その他専門職（30-50）
    '棋士': 42,
    '囲碁棋士': 40,
    '料理人': 42,
    '冒険家': 45,
    '宇宙飛行士': 55,
    '登山家': 40,
    
    # 一般職（5-20）
    '会社員': 5,
    '教師': 8,
    'エンジニア': 6,
    '公務員': 5,
    '自営業': 5,
    '看護師': 5,
    '営業': 5,
    '事務員': 5,
    '主婦': 5,
    '学生': 5,
    
    # 架空・その他
    '架空のキャラクター': 60,
    '犯罪者': 45,
    '宗教指導者': 40,
}

def calculate_era_modifier(birth_year: Optional[int], occupation: str) -> float:
    """時代性による補正係数を計算"""
    if not birth_year:
        return 1.0
    
    current_year = 2025
    
    # 歴史上の人物で教科書に載るレベル
    if birth_year < 1900:
        if occupation in ['武将', '将軍', '天皇', '志士', '大名']:
            return 1.15  # 教育で必ず学ぶ
        elif occupation in ['作家', '画家', '僧侶', '茶人']:
            return 1.1
        else:
            return 0.9
    
    # 昭和の有名人
    elif 1900 <= birth_year < 1960:
        if occupation in ['俳優', '歌手', 'タレント', 'お笑い芸人']:
            return 1.05  # まだ記憶に残る
        else:
            return 1.0
    
    # 現役世代
    elif 1960 <= birth_year <= 2000:
        return 1.1  # 現在活躍中
    
    # 若すぎる
    elif birth_year > 2000:
        if occupation in ['YouTuber', 'TikToker', 'VTuber']:
            return 1.0  # デジタルネイティブ
        else:
            return 0.85
    
    return 1.0

def calculate_group_bonus(person_data: Dict) -> int:
    """グループ・所属による知名度ボーナス"""
    # person_name_displayから（）内のグループ名を抽出
    display_name = person_data.get('person_name_display', '')
    
    if '（' in display_name and '）' in display_name:
        group = display_name[display_name.find('（')+1:display_name.find('）')]
        
        # 有名グループのボーナス
        GROUP_BONUSES = {
            'SMAP': 15,
            '嵐': 15,
            'AKB48': 12,
            '乃木坂46': 10,
            'ジャニーズ': 10,
            'お笑いコンビ': 8,
            'フィッシャーズ': 10,
            '東海オンエア': 8,
            'コムドット': 8,
            'ホロライブ': 5,
            'にじさんじ': 5,
        }
        
        for group_key, bonus in GROUP_BONUSES.items():
            if group_key in group:
                return bonus
    
    return 0

def calculate_cultural_bonus(cultural_significance: int) -> int:
    """文化的重要度によるボーナス"""
    if cultural_significance >= 9:
        return 10
    elif cultural_significance >= 8:
        return 7
    elif cultural_significance >= 7:
        return 5
    elif cultural_significance >= 6:
        return 3
    else:
        return 0

def calculate_name_recognition(person_data: Dict) -> int:
    """
    知名度スコアを計算（0-100）
    アプリで優先表示すべき人物を選定
    """
    
    # 1. 個別設定された有名人チェック
    name_ja = person_data.get('person_name_ja', '')
    if name_ja in SPECIFIC_RECOGNITION_SCORES:
        return SPECIFIC_RECOGNITION_SCORES[name_ja]
    
    # 名前の別表記もチェック
    display_name = person_data.get('person_name_display', '')
    if display_name in SPECIFIC_RECOGNITION_SCORES:
        return SPECIFIC_RECOGNITION_SCORES[display_name]
    
    # 2. 職業ベースの基本スコア
    occupation = person_data.get('occupation', '')
    base_score = OCCUPATION_BASE_SCORES.get(occupation, 25)
    
    # 3. 時代性補正
    birth_year = person_data.get('birth_year')
    if birth_year and birth_year != '':
        try:
            birth_year = int(birth_year)
            era_modifier = calculate_era_modifier(birth_year, occupation)
            base_score = int(base_score * era_modifier)
        except:
            pass
    
    # 4. グループボーナス
    group_bonus = calculate_group_bonus(person_data)
    base_score += group_bonus
    
    # 5. 文化的重要度ボーナス
    cultural_significance = person_data.get('cultural_significance', 5)
    if cultural_significance:
        try:
            cultural_bonus = calculate_cultural_bonus(int(cultural_significance))
            base_score += cultural_bonus
        except:
            pass
    
    # 6. 特殊ケース調整
    # アメリカ大統領など
    if person_data.get('nationality') == 'アメリカ' and occupation == '大統領':
        base_score = max(base_score, 75)
    
    # 世界的有名人
    if person_data.get('global_recognition'):
        try:
            global_rec = int(person_data.get('global_recognition', 5))
            if global_rec >= 9:
                base_score = max(base_score, 70)
        except:
            pass
    
    # スコアを0-100に正規化
    final_score = min(100, max(0, base_score))
    
    return final_score

def main():
    print("=== name_recognition スコアリングシステム ===\n")
    
    # 入力ファイル
    input_file = '/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_10000_ACHIEVED_20250825_223422edit.csv'
    
    # CSVファイル読み込み
    print(f"1. データ読み込み中: {input_file}")
    df = pd.read_csv(input_file)
    print(f"   読み込み完了: {len(df):,}人")
    
    # 知名度スコア計算
    print("\n2. 知名度スコア計算中...")
    recognition_scores = []
    
    for idx, row in df.iterrows():
        score = calculate_name_recognition(row.to_dict())
        recognition_scores.append(score)
        
        # 進捗表示
        if (idx + 1) % 1000 == 0:
            print(f"   処理中: {idx + 1:,}/{len(df):,}")
    
    # スコアをDataFrameに追加
    df['name_recognition'] = recognition_scores
    
    # 統計情報
    print("\n3. 統計情報")
    print(f"   平均スコア: {df['name_recognition'].mean():.1f}")
    print(f"   中央値: {df['name_recognition'].median():.1f}")
    print(f"   最大値: {df['name_recognition'].max()}")
    print(f"   最小値: {df['name_recognition'].min()}")
    
    # スコア分布
    print("\n4. スコア分布")
    score_ranges = [
        (90, 100, "超有名（誰でも知っている）"),
        (70, 89, "有名（ほとんどの人が知っている）"),
        (50, 69, "中程度（多くの人が知っている）"),
        (30, 49, "やや低い（一部の人が知っている）"),
        (0, 29, "低い（ほとんど知られていない）")
    ]
    
    for min_score, max_score, label in score_ranges:
        count = len(df[(df['name_recognition'] >= min_score) & (df['name_recognition'] <= max_score)])
        percentage = (count / len(df)) * 100
        print(f"   {min_score:3d}-{max_score:3d}: {count:5,}人 ({percentage:5.1f}%) - {label}")
    
    # アプリ表示推奨人数（閾値70以上）
    high_recognition = df[df['name_recognition'] >= 70]
    print(f"\n5. アプリ表示推奨人物（知名度70以上）: {len(high_recognition):,}人")
    
    # トップ20表示
    print("\n6. 知名度トップ20")
    top20 = df.nlargest(20, 'name_recognition')[['person_name_display', 'occupation', 'name_recognition']]
    for idx, row in top20.iterrows():
        print(f"   {row['name_recognition']:3d}点: {row['person_name_display']} ({row['occupation']})")
    
    # CSV保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_csv = f'ultra_think_with_recognition_{timestamp}.csv'
    df.to_csv(output_csv, index=False, encoding='utf-8-sig')
    print(f"\n7. CSV保存完了: {output_csv}")
    
    # 高知名度人物リスト（アプリ用）
    high_recognition_file = f'high_recognition_people_{timestamp}.csv'
    high_recognition.to_csv(high_recognition_file, index=False, encoding='utf-8-sig')
    print(f"   高知名度リスト: {high_recognition_file}")
    
    # JSON出力（アプリ用）
    app_data = []
    for _, row in high_recognition.iterrows():
        app_data.append({
            'id': f"{row['person_name']}_{row.get('birth_year', '')}",
            'name': row['person_name'],
            'name_ja': row['person_name_ja'],
            'display_name': row['person_name_display'],
            'occupation': row['occupation'],
            'recognition_score': int(row['name_recognition']),
            'birth_year': row.get('birth_year'),
            'nationality': row.get('nationality', '日本'),
            'category': row.get('main_category', ''),
        })
    
    # 知名度でソート
    app_data.sort(key=lambda x: x['recognition_score'], reverse=True)
    
    json_file = f'app_high_recognition_{timestamp}.json'
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(app_data, f, ensure_ascii=False, indent=2)
    print(f"   アプリ用JSON: {json_file}")
    
    # 最終レポート
    print("\n" + "="*50)
    print("✅ name_recognition スコアリング完了")
    print("="*50)
    print(f"総人数: {len(df):,}人")
    print(f"アプリ表示推奨（知名度70以上）: {len(high_recognition):,}人")
    print(f"表示率: {(len(high_recognition)/len(df)*100):.1f}%")
    print("\nこれにより、アプリはユーザーが知っている人物の")
    print("エピソードを優先的に表示できるようになりました。")
    
    return df

if __name__ == "__main__":
    main()