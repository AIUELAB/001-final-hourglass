#!/usr/bin/env python3
"""
Ultra Think Phase 11-20 Expansion - 1000人規模への最終拡張
アジア・アフリカ・現代のビジネスリーダー強化
"""

import json
import csv
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class FinalPerson:
    person_name: str
    person_name_ja: str
    person_name_display: str
    birth_year: int
    nationality: str
    occupation: str
    main_category: str
    subcategory: str
    description: str = ""
    historical_impact: int = 8
    educational_value: int = 8
    cultural_significance: int = 9
    global_recognition: int = 7
    grade: str = "A"
    era: str = ""
    phase: int = 11

class UltraThinkFinalExpander:
    """フェーズ11〜20の最終拡張"""
    
    def __init__(self):
        self.collected_people: List[Dict[str, Any]] = []
        self.processed_phases = set()
        self.checkpoint_file = "ultra_think_phase_11_20_checkpoint.json"
        
    def get_phase_11_people(self) -> List[FinalPerson]:
        """フェーズ11: アジアの現代指導者と革命家（50人）"""
        return [
            # 東アジア現代指導者
            FinalPerson("Park Chung-hee", "朴正煕", "朴正煕", 1917, "韓国", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Kim Dae-jung", "金大中", "金大中", 1924, "韓国", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Chiang Ching-kuo", "蔣経国", "蔣経国", 1910, "台湾", "総統", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Lee Teng-hui", "李登輝", "李登輝", 1923, "台湾", "総統", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Mahathir Mohamad", "マハティール・モハマド", "マハティール", 1925, "マレーシア", "首相", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Suharto", "スハルト", "スハルト", 1921, "インドネシア", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Ferdinand Marcos", "フェルディナンド・マルコス", "マルコス", 1917, "フィリピン", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Corazon Aquino", "コラソン・アキノ", "アキノ", 1933, "フィリピン", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Pol Pot", "ポル・ポト", "ポル・ポト", 1925, "カンボジア", "首相", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Norodom Sihanouk", "ノロドム・シハヌーク", "シハヌーク", 1922, "カンボジア", "国王", "現代のイノベーター", "フェーズ11", phase=11),
            
            # 南アジア指導者
            FinalPerson("Sheikh Mujibur Rahman", "シェイク・ムジブル・ラフマン", "ムジブル", 1920, "バングラデシュ", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Zulfikar Ali Bhutto", "ズルフィカール・アリー・ブットー", "ブットー", 1928, "パキスタン", "首相", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Benazir Bhutto", "ベーナズィール・ブットー", "ベナジル", 1953, "パキスタン", "首相", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Rajiv Gandhi", "ラジーヴ・ガンディー", "ラジーヴ", 1944, "インド", "首相", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Atal Bihari Vajpayee", "アタル・ビハーリー・ヴァージペーイー", "ヴァージペーイー", 1924, "インド", "首相", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Manmohan Singh", "マンモハン・シン", "マンモハン・シン", 1932, "インド", "首相", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("J.R. Jayewardene", "J・R・ジャヤワルダナ", "ジャヤワルダナ", 1906, "スリランカ", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Solomon Bandaranaike", "ソロモン・バンダラナイケ", "バンダラナイケ", 1899, "スリランカ", "首相", "現代のイノベーター", "フェーズ11", phase=11),
            
            # 中央アジア・西アジア
            FinalPerson("Nursultan Nazarbayev", "ヌルスルタン・ナザルバエフ", "ナザルバエフ", 1940, "カザフスタン", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Islam Karimov", "イスラム・カリモフ", "カリモフ", 1938, "ウズベキスタン", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Mohammad Reza Pahlavi", "モハンマド・レザー・パフラヴィー", "パフラヴィー", 1919, "イラン", "皇帝", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Ruhollah Khomeini", "ルーホッラー・ホメイニー", "ホメイニー", 1902, "イラン", "最高指導者", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Saddam Hussein", "サダム・フセイン", "サダム", 1937, "イラク", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Hafez al-Assad", "ハーフィズ・アル＝アサド", "アサド", 1930, "シリア", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Yasser Arafat", "ヤーセル・アラファト", "アラファト", 1929, "パレスチナ", "議長", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Golda Meir", "ゴルダ・メイア", "メイア", 1898, "イスラエル", "首相", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Yitzhak Rabin", "イツハク・ラビン", "ラビン", 1922, "イスラエル", "首相", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Shimon Peres", "シモン・ペレス", "ペレス", 1923, "イスラエル", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("King Hussein", "フセイン国王", "フセイン", 1935, "ヨルダン", "国王", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Anwar Sadat", "アンワル・サダト", "サダト", 1918, "エジプト", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Hosni Mubarak", "ホスニー・ムバラク", "ムバラク", 1928, "エジプト", "大統領", "現代のイノベーター", "フェーズ11", phase=11),
            
            # アジアのビジネスリーダー
            FinalPerson("Masayoshi Son", "孫正義", "孫正義", 1957, "日本", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Tadashi Yanai", "柳井正", "柳井正", 1949, "日本", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Hiroshi Mikitani", "三木谷浩史", "三木谷浩史", 1965, "日本", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Soichiro Honda", "本田宗一郎", "本田宗一郎", 1906, "日本", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Konosuke Matsushita", "松下幸之助", "松下幸之助", 1894, "日本", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Akio Morita", "盛田昭夫", "盛田昭夫", 1921, "日本", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Kazuo Inamori", "稲盛和夫", "稲盛和夫", 1932, "日本", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Lee Byung-chul", "李秉喆", "李秉喆", 1910, "韓国", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Lee Kun-hee", "李健熙", "李健熙", 1942, "韓国", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Chung Ju-yung", "鄭周永", "鄭周永", 1915, "韓国", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Dhirubhai Ambani", "ディルバイ・アンバニ", "ディルバイ", 1932, "インド", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Azim Premji", "アジム・プレムジ", "プレムジ", 1945, "インド", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Ratan Tata", "ラタン・タタ", "タタ", 1937, "インド", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Wang Jianlin", "王健林", "王健林", 1954, "中国", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Ma Huateng", "馬化騰", "馬化騰", 1971, "中国", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Robin Li", "李彦宏", "李彦宏", 1968, "中国", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Lei Jun", "雷軍", "雷軍", 1969, "中国", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
            FinalPerson("Terry Gou", "郭台銘", "郭台銘", 1950, "台湾", "実業家", "現代のイノベーター", "フェーズ11", phase=11),
        ]
    
    def get_phase_12_people(self) -> List[FinalPerson]:
        """フェーズ12: アフリカの指導者と独立運動家（50人）"""
        return [
            # 北アフリカ
            FinalPerson("Ahmed Ben Bella", "アフメド・ベン・ベラ", "ベン・ベラ", 1916, "アルジェリア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Houari Boumediene", "ホアリ・ブーメディエン", "ブーメディエン", 1932, "アルジェリア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Habib Bourguiba", "ハビーブ・ブルギーバ", "ブルギーバ", 1903, "チュニジア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Muammar Gaddafi", "ムアンマル・アル＝カッザーフィー", "カダフィ", 1942, "リビア", "指導者", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Hassan II", "ハッサン2世", "ハッサン2世", 1929, "モロッコ", "国王", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Mohammed V", "ムハンマド5世", "ムハンマド5世", 1909, "モロッコ", "国王", "国民的英雄", "フェーズ12", phase=12),
            
            # 西アフリカ
            FinalPerson("Leopold Sedar Senghor", "レオポール・セダール・サンゴール", "サンゴール", 1906, "セネガル", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Felix Houphouet-Boigny", "フェリックス・ウフェ＝ボワニ", "ウフェ＝ボワニ", 1905, "コートジボワール", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Ahmed Sekou Toure", "アフメド・セク・トゥーレ", "セク・トゥーレ", 1922, "ギニア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Thomas Sankara", "トーマス・サンカラ", "サンカラ", 1949, "ブルキナファソ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Jerry Rawlings", "ジェリー・ローリングス", "ローリングス", 1947, "ガーナ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Nnamdi Azikiwe", "ナムディ・アジキウェ", "アジキウェ", 1904, "ナイジェリア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Obafemi Awolowo", "オバフェミ・アウォロウォ", "アウォロウォ", 1909, "ナイジェリア", "政治家", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Ahmadu Bello", "アフマドゥ・ベロ", "ベロ", 1910, "ナイジェリア", "政治家", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Samuel Doe", "サミュエル・ドウ", "ドウ", 1951, "リベリア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Charles Taylor", "チャールズ・テイラー", "テイラー", 1948, "リベリア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Ellen Johnson Sirleaf", "エレン・ジョンソン・サーリーフ", "サーリーフ", 1938, "リベリア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            
            # 東アフリカ
            FinalPerson("Meles Zenawi", "メレス・ゼナウィ", "メレス", 1955, "エチオピア", "首相", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Mengistu Haile Mariam", "メンギスツ・ハイレ・マリアム", "メンギスツ", 1937, "エチオピア", "議長", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Siad Barre", "モハメド・シアド・バーレ", "シアド・バーレ", 1919, "ソマリア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Daniel arap Moi", "ダニエル・アラップ・モイ", "モイ", 1924, "ケニア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Mwai Kibaki", "ムワイ・キバキ", "キバキ", 1931, "ケニア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Uhuru Kenyatta", "ウフル・ケニヤッタ", "ウフル", 1961, "ケニア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Yoweri Museveni", "ヨウェリ・ムセベニ", "ムセベニ", 1944, "ウガンダ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Idi Amin", "イディ・アミン", "アミン", 1925, "ウガンダ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Milton Obote", "ミルトン・オボテ", "オボテ", 1925, "ウガンダ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Paul Kagame", "ポール・カガメ", "カガメ", 1957, "ルワンダ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Pierre Nkurunziza", "ピエール・ンクルンジザ", "ンクルンジザ", 1964, "ブルンジ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            
            # 中央アフリカ
            FinalPerson("Mobutu Sese Seko", "モブツ・セセ・セコ", "モブツ", 1930, "ザイール", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Laurent-Desire Kabila", "ローラン＝デジレ・カビラ", "カビラ", 1939, "コンゴ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Joseph Kabila", "ジョゼフ・カビラ", "ジョゼフ・カビラ", 1971, "コンゴ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Denis Sassou Nguesso", "ドゥニ・サスヌゲソ", "サスヌゲソ", 1943, "コンゴ共和国", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Paul Biya", "ポール・ビヤ", "ビヤ", 1933, "カメルーン", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Omar Bongo", "オマル・ボンゴ", "ボンゴ", 1935, "ガボン", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Jean-Bedel Bokassa", "ジャン＝ベデル・ボカサ", "ボカサ", 1921, "中央アフリカ", "皇帝", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Idriss Deby", "イドリス・デビ", "デビ", 1952, "チャド", "大統領", "国民的英雄", "フェーズ12", phase=12),
            
            # 南部アフリカ
            FinalPerson("Samora Machel", "サモラ・マシェル", "マシェル", 1933, "モザンビーク", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Eduardo Mondlane", "エドゥアルド・モンドラーネ", "モンドラーネ", 1920, "モザンビーク", "独立運動家", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Agostinho Neto", "アゴスティニョ・ネト", "ネト", 1922, "アンゴラ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Jonas Savimbi", "ジョナス・サヴィンビ", "サヴィンビ", 1934, "アンゴラ", "反政府指導者", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Sam Nujoma", "サム・ヌジョマ", "ヌジョマ", 1929, "ナミビア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Kenneth Kaunda", "ケネス・カウンダ", "カウンダ", 1924, "ザンビア", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Robert Mugabe", "ロバート・ムガベ", "ムガベ", 1924, "ジンバブエ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Joshua Nkomo", "ジョシュア・ンコモ", "ンコモ", 1917, "ジンバブエ", "政治家", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Ian Smith", "イアン・スミス", "スミス", 1919, "ローデシア", "首相", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Seretse Khama", "セレツェ・カーマ", "カーマ", 1921, "ボツワナ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("Hastings Banda", "ヘイスティングス・バンダ", "バンダ", 1898, "マラウイ", "大統領", "国民的英雄", "フェーズ12", phase=12),
            FinalPerson("King Sobhuza II", "ソブーザ2世", "ソブーザ", 1899, "スワジランド", "国王", "国民的英雄", "フェーズ12", phase=12),
        ]
    
    def get_phase_13_people(self) -> List[FinalPerson]:
        """フェーズ13: ラテンアメリカの革命家と文化人（50人）"""
        return [
            # 革命家・独立運動家
            FinalPerson("Emiliano Zapata", "エミリアーノ・サパタ", "サパタ", 1879, "メキシコ", "革命家", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Pancho Villa", "パンチョ・ビリャ", "パンチョ・ビリャ", 1878, "メキシコ", "革命家", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Lazaro Cardenas", "ラサロ・カルデナス", "カルデナス", 1895, "メキシコ", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Miguel Hidalgo", "ミゲル・イダルゴ", "イダルゴ", 1753, "メキシコ", "独立運動家", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Jose Maria Morelos", "ホセ・マリア・モレロス", "モレロス", 1765, "メキシコ", "独立運動家", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Antonio Lopez de Santa Anna", "アントニオ・ロペス・デ・サンタ・アナ", "サンタ・アナ", 1794, "メキシコ", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Augusto Cesar Sandino", "アウグスト・セサル・サンディーノ", "サンディーノ", 1895, "ニカラグア", "革命家", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Daniel Ortega", "ダニエル・オルテガ", "オルテガ", 1945, "ニカラグア", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Omar Torrijos", "オマル・トリホス", "トリホス", 1929, "パナマ", "最高司令官", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Manuel Noriega", "マヌエル・ノリエガ", "ノリエガ", 1934, "パナマ", "最高司令官", "国民的英雄", "フェーズ13", phase=13),
            
            # 南米の政治指導者
            FinalPerson("Juan Peron", "フアン・ペロン", "ペロン", 1895, "アルゼンチン", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Carlos Menem", "カルロス・メネム", "メネム", 1930, "アルゼンチン", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Nestor Kirchner", "ネストル・キルチネル", "キルチネル", 1950, "アルゼンチン", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Cristina Fernandez", "クリスティーナ・フェルナンデス", "クリスティーナ", 1953, "アルゼンチン", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Getulio Vargas", "ジェトゥリオ・ヴァルガス", "ヴァルガス", 1882, "ブラジル", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Juscelino Kubitschek", "ジュセリーノ・クビシェッキ", "クビシェッキ", 1902, "ブラジル", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Fernando Henrique Cardoso", "フェルナンド・エンリケ・カルドーゾ", "カルドーゾ", 1931, "ブラジル", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Luiz Inacio Lula da Silva", "ルイス・イナシオ・ルーラ・ダ・シルヴァ", "ルーラ", 1945, "ブラジル", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Dilma Rousseff", "ジルマ・ルセフ", "ルセフ", 1947, "ブラジル", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Augusto Pinochet", "アウグスト・ピノチェト", "ピノチェト", 1915, "チリ", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Michelle Bachelet", "ミシェル・バチェレ", "バチェレ", 1951, "チリ", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Alberto Fujimori", "アルベルト・フジモリ", "フジモリ", 1938, "ペルー", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Alan Garcia", "アラン・ガルシア", "ガルシア", 1949, "ペルー", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Hugo Chavez", "ウゴ・チャベス", "チャベス", 1954, "ベネズエラ", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Nicolas Maduro", "ニコラス・マドゥロ", "マドゥロ", 1962, "ベネズエラ", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Rafael Correa", "ラファエル・コレア", "コレア", 1963, "エクアドル", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Evo Morales", "エボ・モラレス", "モラレス", 1959, "ボリビア", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Jose Mujica", "ホセ・ムヒカ", "ムヒカ", 1935, "ウルグアイ", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Alfredo Stroessner", "アルフレド・ストロエスネル", "ストロエスネル", 1912, "パラグアイ", "大統領", "国民的英雄", "フェーズ13", phase=13),
            FinalPerson("Alvaro Uribe", "アルバロ・ウリベ", "ウリベ", 1952, "コロンビア", "大統領", "国民的英雄", "フェーズ13", phase=13),
            
            # ラテンアメリカの文化人
            FinalPerson("Octavio Paz", "オクタビオ・パス", "パス", 1914, "メキシコ", "詩人", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Carlos Fuentes", "カルロス・フエンテス", "フエンテス", 1928, "メキシコ", "作家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Diego Rivera", "ディエゴ・リベラ", "リベラ", 1886, "メキシコ", "画家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Frida Kahlo", "フリーダ・カーロ", "フリーダ", 1907, "メキシコ", "画家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("David Alfaro Siqueiros", "ダビッド・アルファロ・シケイロス", "シケイロス", 1896, "メキシコ", "画家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Jose Clemente Orozco", "ホセ・クレメンテ・オロスコ", "オロスコ", 1883, "メキシコ", "画家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Pablo Neruda", "パブロ・ネルーダ", "ネルーダ", 1904, "チリ", "詩人", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Isabel Allende", "イサベル・アジェンデ", "イサベル・アジェンデ", 1942, "チリ", "作家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Mario Vargas Llosa", "マリオ・バルガス・リョサ", "バルガス・リョサ", 1936, "ペルー", "作家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Julio Cortazar", "フリオ・コルタサル", "コルタサル", 1914, "アルゼンチン", "作家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Ernesto Sabato", "エルネスト・サバト", "サバト", 1911, "アルゼンチン", "作家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Clarice Lispector", "クラリッセ・リスペクトール", "リスペクトール", 1920, "ブラジル", "作家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Jorge Amado", "ジョルジェ・アマード", "アマード", 1912, "ブラジル", "作家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Paulo Coelho", "パウロ・コエーリョ", "コエーリョ", 1947, "ブラジル", "作家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Carlos Gardel", "カルロス・ガルデル", "ガルデル", 1890, "アルゼンチン", "歌手", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Astor Piazzolla", "アストル・ピアソラ", "ピアソラ", 1921, "アルゼンチン", "作曲家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Villa-Lobos", "ヴィラ＝ロボス", "ヴィラ＝ロボス", 1887, "ブラジル", "作曲家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Tom Jobim", "トム・ジョビン", "ジョビン", 1927, "ブラジル", "作曲家", "歴史的偉人", "フェーズ13", phase=13),
            FinalPerson("Gilberto Gil", "ジルベルト・ジル", "ジル", 1942, "ブラジル", "音楽家", "歴史的偉人", "フェーズ13", phase=13),
        ]
    
    def get_phase_14_people(self) -> List[FinalPerson]:
        """フェーズ14: 現代のテクノロジー・メディア・金融界の巨人（60人）"""
        return [
            # テクノロジー界の新世代
            FinalPerson("Satya Nadella", "サティア・ナデラ", "ナデラ", 1967, "インド", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Sundar Pichai", "スンダー・ピチャイ", "ピチャイ", 1972, "インド", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Tim Cook", "ティム・クック", "クック", 1960, "アメリカ", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Sheryl Sandberg", "シェリル・サンドバーグ", "サンドバーグ", 1969, "アメリカ", "実業家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Reed Hastings", "リード・ヘイスティングス", "ヘイスティングス", 1960, "アメリカ", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Brian Chesky", "ブライアン・チェスキー", "チェスキー", 1981, "アメリカ", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Travis Kalanick", "トラビス・カラニック", "カラニック", 1976, "アメリカ", "起業家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Garrett Camp", "ギャレット・キャンプ", "キャンプ", 1978, "カナダ", "起業家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Jan Koum", "ヤン・クーム", "クーム", 1976, "ウクライナ", "起業家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Brian Acton", "ブライアン・アクトン", "アクトン", 1972, "アメリカ", "起業家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Kevin Systrom", "ケビン・シストロム", "シストロム", 1983, "アメリカ", "起業家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Evan Spiegel", "エヴァン・シュピーゲル", "シュピーゲル", 1990, "アメリカ", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Bobby Murphy", "ボビー・マーフィー", "マーフィー", 1988, "アメリカ", "CTO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Jack Dorsey", "ジャック・ドーシー", "ドーシー", 1976, "アメリカ", "起業家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Drew Houston", "ドリュー・ヒューストン", "ヒューストン", 1983, "アメリカ", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Daniel Ek", "ダニエル・エク", "エク", 1983, "スウェーデン", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Pavel Durov", "パヴェル・ドゥーロフ", "ドゥーロフ", 1984, "ロシア", "起業家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Brian Armstrong", "ブライアン・アームストロング", "アームストロング", 1983, "アメリカ", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Sam Altman", "サム・アルトマン", "アルトマン", 1985, "アメリカ", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Jensen Huang", "ジェンスン・ファン", "ファン", 1963, "台湾", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            
            # 金融・投資界
            FinalPerson("Jamie Dimon", "ジェイミー・ダイモン", "ダイモン", 1956, "アメリカ", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Lloyd Blankfein", "ロイド・ブランクファイン", "ブランクファイン", 1954, "アメリカ", "元CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Ray Dalio", "レイ・ダリオ", "ダリオ", 1949, "アメリカ", "投資家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Carl Icahn", "カール・アイカーン", "アイカーン", 1936, "アメリカ", "投資家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Peter Thiel", "ピーター・ティール", "ティール", 1967, "ドイツ", "投資家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Marc Andreessen", "マーク・アンドリーセン", "アンドリーセン", 1971, "アメリカ", "投資家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Reid Hoffman", "リード・ホフマン", "ホフマン", 1967, "アメリカ", "起業家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("John Doerr", "ジョン・ドーア", "ドーア", 1951, "アメリカ", "投資家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Mary Meeker", "メアリー・ミーカー", "ミーカー", 1959, "アメリカ", "投資家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Cathie Wood", "キャシー・ウッド", "ウッド", 1955, "アメリカ", "投資家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Christine Lagarde", "クリスティーヌ・ラガルド", "ラガルド", 1956, "フランス", "ECB総裁", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Janet Yellen", "ジャネット・イエレン", "イエレン", 1946, "アメリカ", "財務長官", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Jerome Powell", "ジェローム・パウエル", "パウエル", 1953, "アメリカ", "FRB議長", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Mario Draghi", "マリオ・ドラギ", "ドラギ", 1947, "イタリア", "元ECB総裁", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Mark Carney", "マーク・カーニー", "カーニー", 1965, "カナダ", "元英中銀総裁", "現代のイノベーター", "フェーズ14", phase=14),
            
            # メディア・エンタメ業界
            FinalPerson("Rupert Murdoch", "ルパート・マードック", "マードック", 1931, "オーストラリア", "メディア王", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Ted Turner", "テッド・ターナー", "ターナー", 1938, "アメリカ", "メディア王", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Oprah Winfrey", "オプラ・ウィンフリー", "オプラ", 1954, "アメリカ", "メディア王", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Bob Iger", "ボブ・アイガー", "アイガー", 1951, "アメリカ", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Jeff Zucker", "ジェフ・ザッカー", "ザッカー", 1965, "アメリカ", "メディア経営者", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Arianna Huffington", "アリアナ・ハフィントン", "ハフィントン", 1950, "ギリシャ", "起業家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Tyler Perry", "タイラー・ペリー", "ペリー", 1969, "アメリカ", "映画監督", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Shonda Rhimes", "ションダ・ライムズ", "ライムズ", 1970, "アメリカ", "プロデューサー", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Ryan Murphy", "ライアン・マーフィー", "マーフィー", 1965, "アメリカ", "プロデューサー", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("J.J. Abrams", "J・J・エイブラムス", "エイブラムス", 1966, "アメリカ", "映画監督", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Christopher Nolan", "クリストファー・ノーラン", "ノーラン", 1970, "イギリス", "映画監督", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Quentin Tarantino", "クエンティン・タランティーノ", "タランティーノ", 1963, "アメリカ", "映画監督", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Martin Scorsese", "マーティン・スコセッシ", "スコセッシ", 1942, "アメリカ", "映画監督", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("James Cameron", "ジェームズ・キャメロン", "キャメロン", 1954, "カナダ", "映画監督", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Peter Jackson", "ピーター・ジャクソン", "ジャクソン", 1961, "ニュージーランド", "映画監督", "現代のイノベーター", "フェーズ14", phase=14),
            
            # ゲーム業界
            FinalPerson("Shigeru Miyamoto", "宮本茂", "宮本茂", 1952, "日本", "ゲームデザイナー", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Hideo Kojima", "小島秀夫", "小島秀夫", 1963, "日本", "ゲームデザイナー", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Hironobu Sakaguchi", "坂口博信", "坂口博信", 1962, "日本", "ゲームデザイナー", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Yu Suzuki", "鈴木裕", "鈴木裕", 1958, "日本", "ゲームデザイナー", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Sid Meier", "シド・マイヤー", "マイヤー", 1954, "カナダ", "ゲームデザイナー", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Will Wright", "ウィル・ライト", "ライト", 1960, "アメリカ", "ゲームデザイナー", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("John Carmack", "ジョン・カーマック", "カーマック", 1970, "アメリカ", "プログラマー", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Gabe Newell", "ゲイブ・ニューウェル", "ニューウェル", 1962, "アメリカ", "起業家", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Tim Sweeney", "ティム・スウィーニー", "スウィーニー", 1970, "アメリカ", "CEO", "現代のイノベーター", "フェーズ14", phase=14),
            FinalPerson("Markus Persson", "マルクス・ペルソン", "Notch", 1979, "スウェーデン", "ゲーム開発者", "現代のイノベーター", "フェーズ14", phase=14),
        ]
    
    def get_phase_15_people(self) -> List[FinalPerson]:
        """フェーズ15: スポーツ界のレジェンドと現代のヒーロー（50人）"""
        return [
            # サッカー
            FinalPerson("Lionel Messi", "リオネル・メッシ", "メッシ", 1987, "アルゼンチン", "サッカー選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Cristiano Ronaldo", "クリスティアーノ・ロナウド", "ロナウド", 1985, "ポルトガル", "サッカー選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Neymar", "ネイマール", "ネイマール", 1992, "ブラジル", "サッカー選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Kylian Mbappe", "キリアン・エムバペ", "エムバペ", 1998, "フランス", "サッカー選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Zinedine Zidane", "ジネディーヌ・ジダン", "ジダン", 1972, "フランス", "サッカー選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Ronaldinho", "ロナウジーニョ", "ロナウジーニョ", 1980, "ブラジル", "サッカー選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Thierry Henry", "ティエリ・アンリ", "アンリ", 1977, "フランス", "サッカー選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Franz Beckenbauer", "フランツ・ベッケンバウアー", "ベッケンバウアー", 1945, "ドイツ", "サッカー選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Johan Cruyff", "ヨハン・クライフ", "クライフ", 1947, "オランダ", "サッカー選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Michel Platini", "ミシェル・プラティニ", "プラティニ", 1955, "フランス", "サッカー選手", "現代のイノベーター", "フェーズ15", phase=15),
            
            # バスケットボール
            FinalPerson("LeBron James", "レブロン・ジェームズ", "レブロン", 1984, "アメリカ", "バスケットボール選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Kobe Bryant", "コービー・ブライアント", "コービー", 1978, "アメリカ", "バスケットボール選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Stephen Curry", "ステフィン・カリー", "カリー", 1988, "アメリカ", "バスケットボール選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Kevin Durant", "ケビン・デュラント", "デュラント", 1988, "アメリカ", "バスケットボール選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Magic Johnson", "マジック・ジョンソン", "マジック", 1959, "アメリカ", "バスケットボール選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Larry Bird", "ラリー・バード", "バード", 1956, "アメリカ", "バスケットボール選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Shaquille O'Neal", "シャキール・オニール", "シャック", 1972, "アメリカ", "バスケットボール選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Tim Duncan", "ティム・ダンカン", "ダンカン", 1976, "アメリカ", "バスケットボール選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Dirk Nowitzki", "ダーク・ノヴィツキー", "ノヴィツキー", 1978, "ドイツ", "バスケットボール選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Yao Ming", "姚明", "姚明", 1980, "中国", "バスケットボール選手", "現代のイノベーター", "フェーズ15", phase=15),
            
            # テニス
            FinalPerson("Rafael Nadal", "ラファエル・ナダル", "ナダル", 1986, "スペイン", "テニス選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Novak Djokovic", "ノバク・ジョコビッチ", "ジョコビッチ", 1987, "セルビア", "テニス選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Andy Murray", "アンディ・マレー", "マレー", 1987, "イギリス", "テニス選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Pete Sampras", "ピート・サンプラス", "サンプラス", 1971, "アメリカ", "テニス選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Andre Agassi", "アンドレ・アガシ", "アガシ", 1970, "アメリカ", "テニス選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Boris Becker", "ボリス・ベッカー", "ベッカー", 1967, "ドイツ", "テニス選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Stefan Edberg", "ステファン・エドベリ", "エドベリ", 1966, "スウェーデン", "テニス選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Venus Williams", "ビーナス・ウィリアムズ", "ビーナス", 1980, "アメリカ", "テニス選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Maria Sharapova", "マリア・シャラポワ", "シャラポワ", 1987, "ロシア", "テニス選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Naomi Osaka", "大坂なおみ", "大坂なおみ", 1997, "日本", "テニス選手", "現代のイノベーター", "フェーズ15", phase=15),
            
            # オリンピック選手
            FinalPerson("Michael Phelps", "マイケル・フェルプス", "フェルプス", 1985, "アメリカ", "水泳選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Carl Lewis", "カール・ルイス", "ルイス", 1961, "アメリカ", "陸上選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Michael Johnson", "マイケル・ジョンソン", "ジョンソン", 1967, "アメリカ", "陸上選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Nadia Comaneci", "ナディア・コマネチ", "コマネチ", 1961, "ルーマニア", "体操選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Simone Biles", "シモーネ・バイルズ", "バイルズ", 1997, "アメリカ", "体操選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Katarina Witt", "カタリナ・ヴィット", "ヴィット", 1965, "ドイツ", "フィギュアスケート", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Yuzuru Hanyu", "羽生結弦", "羽生結弦", 1994, "日本", "フィギュアスケート", "現代のイノベーター", "フェーズ15", phase=15),
            
            # その他のスポーツ
            FinalPerson("Tom Brady", "トム・ブレイディ", "ブレイディ", 1977, "アメリカ", "アメフト選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Wayne Gretzky", "ウェイン・グレツキー", "グレツキー", 1961, "カナダ", "アイスホッケー選手", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Mike Tyson", "マイク・タイソン", "タイソン", 1966, "アメリカ", "ボクサー", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Floyd Mayweather", "フロイド・メイウェザー", "メイウェザー", 1977, "アメリカ", "ボクサー", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Manny Pacquiao", "マニー・パッキャオ", "パッキャオ", 1978, "フィリピン", "ボクサー", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Lewis Hamilton", "ルイス・ハミルトン", "ハミルトン", 1985, "イギリス", "F1ドライバー", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Michael Schumacher", "ミハエル・シューマッハ", "シューマッハ", 1969, "ドイツ", "F1ドライバー", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Ayrton Senna", "アイルトン・セナ", "セナ", 1960, "ブラジル", "F1ドライバー", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Valentino Rossi", "バレンティーノ・ロッシ", "ロッシ", 1979, "イタリア", "オートバイレーサー", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Tony Hawk", "トニー・ホーク", "ホーク", 1968, "アメリカ", "スケートボーダー", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Kelly Slater", "ケリー・スレーター", "スレーター", 1972, "アメリカ", "サーファー", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Shaun White", "ショーン・ホワイト", "ホワイト", 1986, "アメリカ", "スノーボーダー", "現代のイノベーター", "フェーズ15", phase=15),
            FinalPerson("Ichiro Suzuki", "イチロー", "イチロー", 1973, "日本", "野球選手", "現代のイノベーター", "フェーズ15", phase=15),
        ]
    
    def load_checkpoint(self):
        """チェックポイントの読み込み"""
        try:
            if Path(self.checkpoint_file).exists():
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.processed_phases = set(data.get('processed_phases', []))
                    self.collected_people = data.get('collected_people', [])
                    logger.info(f"チェックポイント読み込み完了: {len(self.processed_phases)}フェーズ処理済み")
        except Exception as e:
            logger.error(f"チェックポイント読み込み失敗: {e}")
    
    def save_checkpoint(self):
        """チェックポイントの保存"""
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'processed_phases': list(self.processed_phases),
                    'collected_people': self.collected_people
                }, f, ensure_ascii=False, indent=2)
            logger.info("チェックポイント保存完了")
        except Exception as e:
            logger.error(f"チェックポイント保存失敗: {e}")
    
    def process_phase(self, phase_num: int, people_getter):
        """フェーズの処理（負荷分散）"""
        if phase_num in self.processed_phases:
            logger.info(f"フェーズ{phase_num}は処理済みです")
            return
        
        logger.info(f"フェーズ{phase_num}の処理を開始...")
        people = people_getter()
        
        # 5人ずつのバッチで処理（さらに小さく）
        batch_size = 5
        for i in range(0, len(people), batch_size):
            batch = people[i:i+batch_size]
            logger.info(f"バッチ処理中: {i+1}-{min(i+batch_size, len(people))}/{len(people)}")
            
            for person in batch:
                person_dict = asdict(person)
                self.collected_people.append(person_dict)
            
            # API負荷対策
            time.sleep(0.5)
        
        self.processed_phases.add(phase_num)
        self.save_checkpoint()
        logger.info(f"フェーズ{phase_num}完了: {len(people)}人追加")
    
    def run_expansion(self):
        """フェーズ11〜15の拡張実行"""
        self.load_checkpoint()
        
        phases = [
            (11, self.get_phase_11_people),
            (12, self.get_phase_12_people),
            (13, self.get_phase_13_people),
            (14, self.get_phase_14_people),
            (15, self.get_phase_15_people),
        ]
        
        for phase_num, getter in phases:
            try:
                self.process_phase(phase_num, getter)
                # フェーズ間の休憩
                time.sleep(2)
            except Exception as e:
                logger.error(f"フェーズ{phase_num}でエラー: {e}")
                continue
        
        # 最終データ保存
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        final_csv = f"ultra_think_phase_11_15_complete_{timestamp}.csv"
        final_json = f"ultra_think_phase_11_15_complete_{timestamp}.json"
        
        # 全フィールドを収集
        all_fields = set()
        for person in self.collected_people:
            all_fields.update(person.keys())
        
        # CSV保存
        with open(final_csv, 'w', encoding='utf-8-sig', newline='') as f:
            fieldnames = sorted(list(all_fields))
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for person in self.collected_people:
                writer.writerow(person)
        
        # JSON保存
        with open(final_json, 'w', encoding='utf-8') as f:
            json.dump(self.collected_people, f, ensure_ascii=False, indent=2)
        
        logger.info(f"""
        ========================================
        フェーズ11〜15拡張完了！
        ========================================
        総人数: {len(self.collected_people)}人
        処理フェーズ: {sorted(list(self.processed_phases))}
        出力ファイル:
        - {final_csv}
        - {final_json}
        ========================================
        """)
        
        return self.collected_people

def main():
    """メイン実行"""
    logger.info("""
    ========================================
    Ultra Think Phase 11-15 Expansion
    1000人規模への最終拡張開始
    ========================================
    """)
    
    expander = UltraThinkFinalExpander()
    people = expander.run_expansion()
    
    logger.info(f"✅ 拡張完了: {len(people)}人のデータを収集")

if __name__ == "__main__":
    main()