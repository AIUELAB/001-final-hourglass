#!/usr/bin/env python3
"""
架空キャラクターのperson_name_display形式をチェックし、
RULE_077の遵守状況を確認・修正するスクリプト
"""

import pandas as pd
import re
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, List, Tuple

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 既知の作品名マッピング（キャラクター名から作品名を推定）
KNOWN_CHARACTER_WORKS = {
    # ドラゴンボール
    '孫悟空': 'ドラゴンボール',
    'ベジータ': 'ドラゴンボール',
    'ピッコロ': 'ドラゴンボール',
    'フリーザ': 'ドラゴンボール',
    'トランクス': 'ドラゴンボール',
    '孫悟飯': 'ドラゴンボール',
    'クリリン': 'ドラゴンボール',
    
    # ONE PIECE
    'ルフィ': 'ONE PIECE',
    'ゾロ': 'ONE PIECE',
    'ナミ': 'ONE PIECE',
    'サンジ': 'ONE PIECE',
    'チョッパー': 'ONE PIECE',
    'ニコ・ロビン': 'ONE PIECE',
    'フランキー': 'ONE PIECE',
    'ブルック': 'ONE PIECE',
    'ジンベエ': 'ONE PIECE',
    
    # 鬼滅の刃
    '竈門炭治郎': '鬼滅の刃',
    '竈門禰豆子': '鬼滅の刃',
    '我妻善逸': '鬼滅の刃',
    '嘴平伊之助': '鬼滅の刃',
    '冨岡義勇': '鬼滅の刃',
    '煉獄杏寿郎': '鬼滅の刃',
    '胡蝶しのぶ': '鬼滅の刃',
    
    # ドラえもん
    'ドラえもん': 'ドラえもん',
    'のび太': 'ドラえもん',
    'しずか': 'ドラえもん',
    'ジャイアン': 'ドラえもん',
    'スネ夫': 'ドラえもん',
    
    # 名探偵コナン
    '江戸川コナン': '名探偵コナン',
    '工藤新一': '名探偵コナン',
    '毛利蘭': '名探偵コナン',
    '毛利小五郎': '名探偵コナン',
    '灰原哀': '名探偵コナン',
    '怪盗キッド': '名探偵コナン',
    
    # NARUTO
    'ナルト': 'NARUTO',
    'サスケ': 'NARUTO',
    'サクラ': 'NARUTO',
    'カカシ': 'NARUTO',
    'ガアラ': 'NARUTO',
    '自来也': 'NARUTO',
    '綱手': 'NARUTO',
    
    # ポケモン
    'ピカチュウ': 'ポケットモンスター',
    'サトシ': 'ポケットモンスター',
    'カスミ': 'ポケットモンスター',
    'タケシ': 'ポケットモンスター',
    
    # エヴァンゲリオン
    '碇シンジ': '新世紀エヴァンゲリオン',
    '綾波レイ': '新世紀エヴァンゲリオン',
    '惣流・アスカ・ラングレー': '新世紀エヴァンゲリオン',
    'エヴァンゲリオン初号機': '新世紀エヴァンゲリオン',
    
    # セーラームーン
    'セーラームーン': '美少女戦士セーラームーン',
    '月野うさぎ': '美少女戦士セーラームーン',
    'セーラーマーキュリー': '美少女戦士セーラームーン',
    'セーラーマーズ': '美少女戦士セーラームーン',
    'セーラージュピター': '美少女戦士セーラームーン',
    'セーラーヴィーナス': '美少女戦士セーラームーン',
    
    # 進撃の巨人
    'エレン・イェーガー': '進撃の巨人',
    'ミカサ・アッカーマン': '進撃の巨人',
    'アルミン・アルレルト': '進撃の巨人',
    'リヴァイ': '進撃の巨人',
    
    # 呪術廻戦
    '虎杖悠仁': '呪術廻戦',
    '伏黒恵': '呪術廻戦',
    '釘崎野薔薇': '呪術廻戦',
    '五条悟': '呪術廻戦',
    
    # その他有名作品
    'アンパンマン': 'それいけ！アンパンマン',
    'サザエさん': 'サザエさん',
    'ちびまる子ちゃん': 'ちびまる子ちゃん',
    'クレヨンしんちゃん': 'クレヨンしんちゃん',
    '野原しんのすけ': 'クレヨンしんちゃん',
    'ガンダム': '機動戦士ガンダム',
    'アムロ・レイ': '機動戦士ガンダム',
    'シャア・アズナブル': '機動戦士ガンダム',
}

def extract_work_from_display(display_name: str) -> str:
    """既存のdisplay_nameから作品名を抽出"""
    if pd.isna(display_name):
        return None
    
    display_name = str(display_name)
    
    # 括弧内の文字を抽出
    match_half = re.search(r'\(([^)]+)\)', display_name)
    if match_half:
        return match_half.group(1)
    
    match_full = re.search(r'（([^）]+）', display_name)
    if match_full:
        return match_full.group(1)
    
    return None

def get_character_name(display_name: str) -> str:
    """display_nameからキャラクター名のみを抽出"""
    if pd.isna(display_name):
        return None
    
    display_name = str(display_name)
    
    # 括弧とその中身を削除
    name = re.sub(r'\([^)]*\)', '', display_name)
    name = re.sub(r'（[^）]*）', '', name)
    
    return name.strip()

def check_and_fix_fictional_characters(csv_file: str):
    """
    架空キャラクターのdisplay名をチェックして修正
    """
    logger.info(f"CSVファイル読み込み中: {csv_file}")
    
    # CSVファイル読み込み
    df = pd.read_csv(csv_file, encoding='utf-8-sig')
    logger.info(f"総レコード数: {len(df)}")
    
    # categoryフィールドの確認
    if 'category' not in df.columns:
        logger.error("categoryフィールドが見つかりません")
        return
    
    # 架空キャラクターのフィルタリング
    fictional_mask = (df['category'] == '架空の存在') | (df['category'] == 'fictional_character')
    fictional_chars = df[fictional_mask].copy()
    
    logger.info(f"架空キャラクター数: {len(fictional_chars)}")
    
    if len(fictional_chars) == 0:
        logger.info("架空キャラクターが見つかりませんでした")
        return
    
    # 統計情報
    stats = {
        'total': len(fictional_chars),
        'has_parentheses': 0,
        'missing_parentheses': 0,
        'empty_parentheses': 0,
        'fixed': 0,
        'unknown_work': 0
    }
    
    # 修正リスト
    fixes = []
    
    for idx, row in fictional_chars.iterrows():
        person_id = row.get('person_id', f'row_{idx}')
        display_name = row.get('person_name_display', '')
        person_name = row.get('person_name', '')
        person_name_ja = row.get('person_name_ja', '')
        
        if pd.isna(display_name):
            display_name = ''
        else:
            display_name = str(display_name)
        
        # 括弧のチェック
        has_half_paren = '(' in display_name and ')' in display_name
        has_full_paren = '（' in display_name and '）' in display_name
        
        if has_half_paren or has_full_paren:
            # 既に括弧がある
            stats['has_parentheses'] += 1
            
            # 空の括弧チェック
            if '()' in display_name or '（）' in display_name:
                stats['empty_parentheses'] += 1
                fixes.append({
                    'index': idx,
                    'person_id': person_id,
                    'old_display': display_name,
                    'issue': '空の括弧',
                    'action': 'need_work_title'
                })
        else:
            # 括弧がない
            stats['missing_parentheses'] += 1
            
            # キャラクター名から作品を推定
            char_name = get_character_name(display_name) or person_name_ja or person_name or ''
            work_title = None
            
            # 既知のキャラクターマッピングから検索
            for known_char, known_work in KNOWN_CHARACTER_WORKS.items():
                if known_char in char_name:
                    work_title = known_work
                    break
            
            if work_title:
                # 作品名が見つかった場合は修正
                new_display = f"{char_name} ({work_title})"
                df.at[idx, 'person_name_display'] = new_display
                stats['fixed'] += 1
                fixes.append({
                    'index': idx,
                    'person_id': person_id,
                    'old_display': display_name,
                    'new_display': new_display,
                    'issue': '作品名なし',
                    'action': 'fixed'
                })
            else:
                # 作品名が不明
                stats['unknown_work'] += 1
                fixes.append({
                    'index': idx,
                    'person_id': person_id,
                    'old_display': display_name,
                    'issue': '作品名不明',
                    'action': 'manual_review_needed'
                })
    
    # レポート出力
    logger.info("\n" + "="*60)
    logger.info("架空キャラクター display名 チェック結果")
    logger.info("="*60)
    logger.info(f"総架空キャラクター数: {stats['total']}")
    logger.info(f"✅ 括弧あり（正常）: {stats['has_parentheses']}")
    logger.info(f"❌ 括弧なし（要修正）: {stats['missing_parentheses']}")
    logger.info(f"⚠️ 空の括弧: {stats['empty_parentheses']}")
    logger.info(f"🔧 自動修正済み: {stats['fixed']}")
    logger.info(f"❓ 作品名不明（要手動確認）: {stats['unknown_work']}")
    
    # 問題のあるレコードの詳細表示
    if fixes:
        logger.info("\n" + "-"*60)
        logger.info("問題のあるレコード（上位20件）:")
        logger.info("-"*60)
        
        for fix in fixes[:20]:
            if fix['action'] == 'fixed':
                logger.info(f"✅ {fix['person_id']}: {fix['old_display']} → {fix['new_display']}")
            elif fix['action'] == 'manual_review_needed':
                logger.info(f"❓ {fix['person_id']}: {fix['old_display']} （作品名不明）")
            elif fix['action'] == 'need_work_title':
                logger.info(f"⚠️ {fix['person_id']}: {fix['old_display']} （空の括弧）")
    
    # 修正したデータを保存
    if stats['fixed'] > 0:
        output_file = csv_file.replace('.csv', '_FICTIONAL_FIXED.csv')
        df.to_csv(output_file, index=False, encoding='utf-8-sig')
        logger.info(f"\n✅ 修正済みファイル保存: {output_file}")
    
    # PDCAガーディアンによる検証
    logger.info("\n" + "="*60)
    logger.info("PDCAガーディアン検証")
    logger.info("="*60)
    
    from pdca_guardian import PDCAGuardian
    guardian = PDCAGuardian()
    
    # 架空キャラクターチェック実行
    violations = guardian.check_fictional_character_display(csv_file)
    
    if violations:
        logger.error(f"⚠️ {len(violations)}件の違反が検出されました")
        for v in violations[:10]:
            logger.error(f"  - {v.description}")
    else:
        logger.info("✅ すべての架空キャラクターがRULE_077に準拠しています")
    
    return df

def main():
    """メイン処理"""
    # 最新のCSVファイル取得
    csv_file = "/Users/admin/Documents/AIUELAB/001-final-hourglass/ultra_think_FINAL_CLEAN_20250912_042742.csv"
    
    if not Path(csv_file).exists():
        logger.error(f"ファイルが見つかりません: {csv_file}")
        return
    
    # チェックと修正実行
    check_and_fix_fictional_characters(csv_file)

if __name__ == "__main__":
    main()