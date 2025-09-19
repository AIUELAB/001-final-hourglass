#!/usr/bin/env python3
"""
すべての架空キャラクターのdisplay名を修正するスクリプト
RULE_077: 架空キャラクターには必ず作品名を括弧付きで表示
"""

import pandas as pd
import logging
from datetime import datetime
from pathlib import Path

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 完全な作品名マッピング
CHARACTER_WORK_MAPPING = {
    # アンパンマンシリーズ
    'アンパンマン': 'それいけ！アンパンマン',
    'しょくぱんまん': 'それいけ！アンパンマン',
    'カレーパンマン': 'それいけ！アンパンマン',
    'ばいきんまん': 'それいけ！アンパンマン',
    'ドキンちゃん': 'それいけ！アンパンマン',
    'メロンパンナ': 'それいけ！アンパンマン',
    'ロールパンナ': 'それいけ！アンパンマン',
    
    # クレヨンしんちゃん
    '野原しんのすけ': 'クレヨンしんちゃん',
    '野原ひろし': 'クレヨンしんちゃん',
    '野原みさえ': 'クレヨンしんちゃん',
    '野原ひまわり': 'クレヨンしんちゃん',
    'シロ': 'クレヨンしんちゃん',
    
    # ドラえもん
    'ドラえもん': 'ドラえもん',
    '野比のび太': 'ドラえもん',
    '源静香': 'ドラえもん',
    'しずか': 'ドラえもん',
    '剛田武': 'ドラえもん',
    'ジャイアン': 'ドラえもん',
    '骨川スネ夫': 'ドラえもん',
    'スネ夫': 'ドラえもん',
    
    # サザエさん
    'フグ田サザエ': 'サザエさん',
    'フグ田マスオ': 'サザエさん',
    'フグ田タラオ': 'サザエさん',
    '磯野カツオ': 'サザエさん',
    '磯野ワカメ': 'サザエさん',
    '磯野波平': 'サザエさん',
    '磯野フネ': 'サザエさん',
    
    # ちびまる子ちゃん
    'さくらももこ': 'ちびまる子ちゃん',
    'まる子': 'ちびまる子ちゃん',
    '花輪くん': 'ちびまる子ちゃん',
    'たまちゃん': 'ちびまる子ちゃん',
    
    # ドラゴンボール
    '孫悟空': 'ドラゴンボール',
    'ベジータ': 'ドラゴンボール',
    'ピッコロ': 'ドラゴンボール',
    'フリーザ': 'ドラゴンボール',
    'トランクス': 'ドラゴンボール',
    '孫悟飯': 'ドラゴンボール',
    'クリリン': 'ドラゴンボール',
    'ブルマ': 'ドラゴンボール',
    '亀仙人': 'ドラゴンボール',
    
    # ONE PIECE
    'モンキー・D・ルフィ': 'ONE PIECE',
    'ルフィ': 'ONE PIECE',
    'ロロノア・ゾロ': 'ONE PIECE',
    'ゾロ': 'ONE PIECE',
    'ナミ': 'ONE PIECE',
    'サンジ': 'ONE PIECE',
    'トニートニー・チョッパー': 'ONE PIECE',
    'チョッパー': 'ONE PIECE',
    'ニコ・ロビン': 'ONE PIECE',
    'フランキー': 'ONE PIECE',
    'ブルック': 'ONE PIECE',
    'ジンベエ': 'ONE PIECE',
    'ポートガス・D・エース': 'ONE PIECE',
    
    # 鬼滅の刃
    '竈門炭治郎': '鬼滅の刃',
    '竈門禰豆子': '鬼滅の刃',
    '我妻善逸': '鬼滅の刃',
    '嘴平伊之助': '鬼滅の刃',
    '冨岡義勇': '鬼滅の刃',
    '煉獄杏寿郎': '鬼滅の刃',
    '胡蝶しのぶ': '鬼滅の刃',
    '鬼舞辻無惨': '鬼滅の刃',
    
    # 名探偵コナン
    '江戸川コナン': '名探偵コナン',
    '工藤新一': '名探偵コナン',
    '毛利蘭': '名探偵コナン',
    '毛利小五郎': '名探偵コナン',
    '灰原哀': '名探偵コナン',
    '怪盗キッド': '名探偵コナン',
    '服部平次': '名探偵コナン',
    
    # NARUTO
    'うずまきナルト': 'NARUTO',
    'ナルト': 'NARUTO',
    'うちはサスケ': 'NARUTO',
    'サスケ': 'NARUTO',
    '春野サクラ': 'NARUTO',
    'サクラ': 'NARUTO',
    'はたけカカシ': 'NARUTO',
    'カカシ': 'NARUTO',
    '我愛羅': 'NARUTO',
    'ガアラ': 'NARUTO',
    '自来也': 'NARUTO',
    '綱手': 'NARUTO',
    '大蛇丸': 'NARUTO',
    
    # ポケモン
    'ピカチュウ': 'ポケットモンスター',
    'サトシ': 'ポケットモンスター',
    'カスミ': 'ポケットモンスター',
    'タケシ': 'ポケットモンスター',
    'ムサシ': 'ポケットモンスター',
    'コジロウ': 'ポケットモンスター',
    'ニャース': 'ポケットモンスター',
    
    # 進撃の巨人
    'エレン・イェーガー': '進撃の巨人',
    'ミカサ・アッカーマン': '進撃の巨人',
    'アルミン・アルレルト': '進撃の巨人',
    'リヴァイ': '進撃の巨人',
    'エルヴィン・スミス': '進撃の巨人',
    
    # 呪術廻戦
    '虎杖悠仁': '呪術廻戦',
    '伏黒恵': '呪術廻戦',
    '釘崎野薔薇': '呪術廻戦',
    '五条悟': '呪術廻戦',
    '宿儺': '呪術廻戦',
    
    # その他
    'ウルトラマン': 'ウルトラマン',
    '仮面ライダー': '仮面ライダー',
    'ゴジラ': 'ゴジラ',
    'トトロ': 'となりのトトロ',
    '千と千尋': '千と千尋の神隠し',
}

def fix_fictional_characters(csv_file: str):
    """架空キャラクターのdisplay名を修正"""
    
    logger.info(f"CSVファイル読み込み中: {csv_file}")
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    
    # バックアップ作成
    backup_file = csv_file.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
    df.to_csv(backup_file, index=False, encoding='utf-8-sig')
    logger.info(f"バックアップ作成: {backup_file}")
    
    # 架空キャラクターのフィルタリング
    fictional_mask = (df['category'] == '架空の存在') | (df['category'] == 'fictional_character')
    
    fixed_count = 0
    not_fixed = []
    
    for idx in df[fictional_mask].index:
        person_id = df.at[idx, 'person_id']
        display_name = df.at[idx, 'person_name_display']
        person_name = df.at[idx, 'person_name']
        person_name_ja = df.at[idx, 'person_name_ja']
        
        # 既に括弧がある場合はスキップ
        if pd.notna(display_name) and ('(' in str(display_name) or '（' in str(display_name)):
            continue
        
        # キャラクター名の候補を取得
        char_names = []
        if pd.notna(display_name):
            char_names.append(str(display_name).strip())
        if pd.notna(person_name_ja):
            char_names.append(str(person_name_ja).strip())
        if pd.notna(person_name):
            char_names.append(str(person_name).strip())
        
        # 作品名を検索
        work_found = False
        for char_name in char_names:
            if char_name in CHARACTER_WORK_MAPPING:
                work_title = CHARACTER_WORK_MAPPING[char_name]
                new_display = f"{char_name} ({work_title})"
                df.at[idx, 'person_name_display'] = new_display
                fixed_count += 1
                logger.info(f"✅ {person_id}: {char_name} → {new_display}")
                work_found = True
                break
        
        if not work_found:
            # 部分一致でも試す
            for char_name in char_names:
                for known_char, work_title in CHARACTER_WORK_MAPPING.items():
                    if known_char in char_name or char_name in known_char:
                        new_display = f"{char_name} ({work_title})"
                        df.at[idx, 'person_name_display'] = new_display
                        fixed_count += 1
                        logger.info(f"✅ {person_id}: {char_name} → {new_display}")
                        work_found = True
                        break
                if work_found:
                    break
        
        if not work_found:
            not_fixed.append({
                'person_id': person_id,
                'display_name': display_name,
                'person_name': person_name,
                'person_name_ja': person_name_ja
            })
    
    # 結果保存
    output_file = csv_file.replace('.csv', '_FICTIONAL_COMPLETE.csv')
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    
    # レポート
    logger.info("\n" + "="*60)
    logger.info("架空キャラクター修正完了")
    logger.info("="*60)
    logger.info(f"✅ 修正済み: {fixed_count}件")
    logger.info(f"❓ 未修正: {len(not_fixed)}件")
    
    if not_fixed:
        logger.info("\n未修正のキャラクター:")
        for item in not_fixed:
            logger.info(f"  - {item['person_id']}: {item['person_name_ja'] or item['person_name'] or item['display_name']}")
    
    logger.info(f"\n✅ 修正済みファイル: {output_file}")
    
    return output_file

def main():
    """メイン処理"""
    # 最新の修正ファイルを使用
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_FINAL_CLEAN_20250912_042742_FICTIONAL_FIXED.csv"
    
    if not Path(csv_file).exists():
        # オリジナルファイルを使用
        csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_FINAL_CLEAN_20250912_042742.csv"
    
    if not Path(csv_file).exists():
        logger.error(f"ファイルが見つかりません: {csv_file}")
        return
    
    # 修正実行
    output_file = fix_fictional_characters(csv_file)
    
    # PDCAガーディアンで最終確認
    from pdca_guardian import PDCAGuardian
    guardian = PDCAGuardian()
    
    violations = guardian.check_fictional_character_display(output_file)
    
    if violations:
        logger.warning(f"⚠️ まだ{len(violations)}件の違反があります")
    else:
        logger.info("✅ すべての架空キャラクターがRULE_077に準拠しています！")

if __name__ == "__main__":
    main()