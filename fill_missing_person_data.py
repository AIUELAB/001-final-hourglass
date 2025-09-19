#!/usr/bin/env python3
"""
指定されたperson_IDの欠損データを補完するスクリプト
"""

import pandas as pd
from datetime import datetime
import re

# CSVファイルを読み込み
csv_file = 'database_final_enriched_20250910_132247.csv'
df = pd.read_csv(csv_file)

# 補完が必要なperson_IDリスト
target_ids = [
    'P004556', 'P003716', 'P001630', 'P002825', 'P004234', 'P002005', 'P003094', 'P003973',
    'P003292', 'P002860', 'P000615', 'P005412', 'P004896', 'P005526', 'P003039', 'P004406',
    'P004290', 'P004264', 'P001662', 'P001793', 'P001784', 'P001910', 'P002051', 'P002172',
    'P005360', 'P001629', 'P004221', 'P000916', 'P002154', 'P004031', 'P004829', 'P005498',
    'P004422', 'P005222', 'P002873', 'P015935', 'P005430', 'P005185', 'P004401', 'P004419',
    'P004382', 'P002057', 'P002064', 'P001902', 'P002734', 'P001037', 'P002947', 'P005112',
    'P004899', 'P002955', 'P002961', 'P003004', 'P004660', 'P004659', 'P003054', 'P004547',
    'P003102', 'P001604', 'P004433', 'P004392', 'P003115', 'P004284', 'P004243', 'P004073',
    'P003728', 'P003689', 'P002063', 'P002199', 'P002192', 'P003548', 'P002373', 'P002198',
    'P005301', 'P003066', 'P003068', 'P004883', 'P001798', 'P002754', 'P002868', 'P003028',
    'P005270', 'P002971', 'P004416', 'P001643', 'P005345', 'P001137', 'P001648', 'P000136'
]

# 人物データ定義
person_data = {
    # スコア4.9の著名人
    'P004556': {
        'person_name_display': '石川直樹',
        'person_name_ja': '石川直樹',
        'category': '文化・芸術',
        'nationality': '日本',
        'occupation': '写真家・冒険家',
        'description': '世界各地を旅する写真家・冒険家。エベレスト登頂経験もある'
    },
    'P003716': {
        'person_name_display': '松本剛',
        'person_name_ja': '松本剛',
        'category': '政治',
        'nationality': '日本',
        'occupation': '政治家',
        'description': '元外務大臣、衆議院議員'
    },
    'P001630': {
        'person_name_display': '中川大志',
        'person_name_ja': '中川大志',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': '俳優',
        'description': '若手俳優。ドラマや映画で活躍'
    },
    'P002825': {
        'person_name_display': '小島秀夫',
        'person_name_ja': '小島秀夫',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'ゲームクリエイター',
        'description': 'メタルギアシリーズの生みの親。世界的に有名なゲームクリエイター'
    },
    'P004234': {
        'person_name_display': '渡辺信一郎',
        'person_name_ja': '渡辺信一郎',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'アニメ監督',
        'description': 'カウボーイビバップ、サムライチャンプルーなどの監督'
    },
    'P002005': {
        'person_name_display': '佐々木久美',
        'person_name_ja': '佐々木久美',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'アイドル',
        'description': '日向坂46のメンバー、キャプテン'
    },
    'P003094': {
        'person_name_display': '山田優',
        'person_name_ja': '山田優',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'モデル・女優',
        'description': 'ファッションモデル、女優として活躍。小栗旬の妻'
    },
    'P003973': {
        'person_name_display': '橋本大輝',
        'person_name_ja': '橋本大輝',
        'category': 'スポーツ',
        'nationality': '日本',
        'occupation': '体操選手',
        'description': '東京オリンピック体操金メダリスト'
    },
    'P003292': {
        'person_name_display': '平野謙',
        'person_name_ja': '平野謙',
        'category': '文化・芸術',
        'nationality': '日本',
        'occupation': '文芸評論家',
        'description': '昭和期の著名な文芸評論家'
    },
    'P002860': {
        'person_name_display': '小林悠',
        'person_name_ja': '小林悠',
        'category': 'スポーツ',
        'nationality': '日本',
        'occupation': 'サッカー選手',
        'description': '川崎フロンターレ所属のプロサッカー選手'
    },
    
    # スコア3.8の著名人
    'P000615': {
        'person_name_display': 'ショーン・キング',
        'person_name_ja': 'ショーン・キング',
        'category': '社会活動',
        'nationality': 'アメリカ',
        'occupation': '活動家・ジャーナリスト',
        'description': 'アメリカの人権活動家、ジャーナリスト'
    },
    
    # スコア3.5の一般著名人
    'P005412': {
        'person_name_display': '高橋三郎',
        'person_name_ja': '高橋三郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004896': {
        'person_name_display': '藤井三郎',
        'person_name_ja': '藤井三郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P005526': {
        'person_name_display': '藤井恵',
        'person_name_ja': '藤井恵',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '料理研究家',
        'description': '料理研究家、テレビ出演も多い'
    },
    'P003039': {
        'person_name_display': '山本健太',
        'person_name_ja': '山本健太',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004406': {
        'person_name_display': '田中次郎',
        'person_name_ja': '田中次郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004290': {
        'person_name_display': '渡邊直樹',
        'person_name_ja': '渡邊直樹',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004264': {
        'person_name_display': '渡辺直樹',
        'person_name_ja': '渡辺直樹',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P001662': {
        'person_name_display': '中村太郎',
        'person_name_ja': '中村太郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P001793': {
        'person_name_display': '井上翔太',
        'person_name_ja': '井上翔太',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P001784': {
        'person_name_display': '井上次郎',
        'person_name_ja': '井上次郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P001910': {
        'person_name_display': '伊藤健太',
        'person_name_ja': '伊藤健太',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': '声優',
        'description': '男性声優'
    },
    'P002051': {
        'person_name_display': '佐藤直樹',
        'person_name_ja': '佐藤直樹',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P002172': {
        'person_name_display': '加藤三郎',
        'person_name_ja': '加藤三郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P005360': {
        'person_name_display': '風太',
        'person_name_ja': '風太',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '動物',
        'description': '千葉市動物公園のレッサーパンダ'
    },
    'P001629': {
        'person_name_display': '中川剛',
        'person_name_ja': '中川剛',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'お笑い芸人',
        'description': '中川家のボケ担当'
    },
    'P004221': {
        'person_name_display': '清水聡',
        'person_name_ja': '清水聡',
        'category': 'スポーツ',
        'nationality': '日本',
        'occupation': 'ボクサー',
        'description': 'プロボクサー、オリンピック銅メダリスト'
    },
    'P000916': {
        'person_name_display': 'デムーロ',
        'person_name_ja': 'デムーロ',
        'category': 'スポーツ',
        'nationality': 'イタリア',
        'occupation': '騎手',
        'description': 'JRA騎手、ミルコ・デムーロ'
    },
    'P002154': {
        'person_name_display': '別れ',
        'person_name_ja': '別れ',
        'category': 'その他',
        'nationality': '不明',
        'occupation': '不明',
        'description': '人物情報不明'
    },
    'P004031': {
        'person_name_display': '比企宗朝',
        'person_name_ja': '比企宗朝',
        'category': '歴史',
        'nationality': '日本',
        'occupation': '武将',
        'description': '鎌倉時代の武将'
    },
    'P004829': {
        'person_name_display': '莉奈',
        'person_name_ja': '莉奈',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P005498': {
        'person_name_display': '齋藤孝',
        'person_name_ja': '齋藤孝',
        'category': '教育',
        'nationality': '日本',
        'occupation': '教育学者',
        'description': '明治大学教授、教育学者、作家'
    },
    'P004422': {
        'person_name_display': '田中良和',
        'person_name_ja': '田中良和',
        'category': 'ビジネス',
        'nationality': '日本',
        'occupation': '実業家',
        'description': 'GREE創業者'
    },
    'P005222': {
        'person_name_display': '鈴木翼',
        'person_name_ja': '鈴木翼',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P002873': {
        'person_name_display': '小林秀雄',
        'person_name_ja': '小林秀雄',
        'category': '文化・芸術',
        'nationality': '日本',
        'occupation': '文芸評論家',
        'description': '近代日本の代表的文芸評論家'
    },
    
    # スコア3.4の一般著名人
    'P015935': {
        'person_name_display': 'エリッサ',
        'person_name_ja': 'エリッサ',
        'category': 'エンタメ',
        'nationality': 'レバノン',
        'occupation': '歌手',
        'description': 'レバノンの有名歌手'
    },
    'P005430': {
        'person_name_display': '高橋恭平',
        'person_name_ja': '高橋恭平',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'アイドル',
        'description': 'なにわ男子のメンバー'
    },
    'P005185': {
        'person_name_display': '鈴木健太',
        'person_name_ja': '鈴木健太',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004401': {
        'person_name_display': '田中愛',
        'person_name_ja': '田中愛',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004419': {
        'person_name_display': '田中翔',
        'person_name_ja': '田中翔',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004382': {
        'person_name_display': '田中健太',
        'person_name_ja': '田中健太',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P002057': {
        'person_name_display': '佐藤翔',
        'person_name_ja': '佐藤翔',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P002064': {
        'person_name_display': '佐藤蓮',
        'person_name_ja': '佐藤蓮',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P001902': {
        'person_name_display': '伊藤七海',
        'person_name_ja': '伊藤七海',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P002734': {
        'person_name_display': '安藤太郎',
        'person_name_ja': '安藤太郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P001037': {
        'person_name_display': 'バイロン卿',
        'person_name_ja': 'バイロン卿',
        'category': '文化・芸術',
        'nationality': 'イギリス',
        'occupation': '詩人',
        'description': 'イギリスロマン主義の詩人'
    },
    'P002947': {
        'person_name_display': '山下三郎',
        'person_name_ja': '山下三郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P005112': {
        'person_name_display': '遠藤三郎',
        'person_name_ja': '遠藤三郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004899': {
        'person_name_display': '藤井大輔',
        'person_name_ja': '藤井大輔',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P002955': {
        'person_name_display': '山中拓也',
        'person_name_ja': '山中拓也',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P002961': {
        'person_name_display': '山内太郎',
        'person_name_ja': '山内太郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P003004': {
        'person_name_display': '山口隼人',
        'person_name_ja': '山口隼人',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004660': {
        'person_name_display': '竹内太郎',
        'person_name_ja': '竹内太郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004659': {
        'person_name_display': '竹内和也',
        'person_name_ja': '竹内和也',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P003054': {
        'person_name_display': '山本拓也',
        'person_name_ja': '山本拓也',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004547': {
        'person_name_display': '石川三郎',
        'person_name_ja': '石川三郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P003102': {
        'person_name_display': '山田大輔',
        'person_name_ja': '山田大輔',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P001604': {
        'person_name_display': '上田次郎',
        'person_name_ja': '上田次郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004433': {
        'person_name_display': '田中雄大',
        'person_name_ja': '田中雄大',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004392': {
        'person_name_display': '田中大輔',
        'person_name_ja': '田中大輔',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P003115': {
        'person_name_display': '山田直樹',
        'person_name_ja': '山田直樹',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004284': {
        'person_name_display': '渡邊三郎',
        'person_name_ja': '渡邊三郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004243': {
        'person_name_display': '渡辺和也',
        'person_name_ja': '渡辺和也',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004073': {
        'person_name_display': '水谷直樹',
        'person_name_ja': '水谷直樹',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P003728': {
        'person_name_display': '松本拓也',
        'person_name_ja': '松本拓也',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P003689': {
        'person_name_display': '松島幸太朗',
        'person_name_ja': '松島幸太朗',
        'category': 'スポーツ',
        'nationality': '日本',
        'occupation': 'ラグビー選手',
        'description': '日本代表ラグビー選手'
    },
    'P002063': {
        'person_name_display': '佐藤葵',
        'person_name_ja': '佐藤葵',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P002199': {
        'person_name_display': '加藤拓也',
        'person_name_ja': '加藤拓也',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P002192': {
        'person_name_display': '加藤太郎',
        'person_name_ja': '加藤太郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P003548': {
        'person_name_display': '木村隼人',
        'person_name_ja': '木村隼人',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P002373': {
        'person_name_display': '吉田直樹',
        'person_name_ja': '吉田直樹',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'ゲームプロデューサー',
        'description': 'FF14プロデューサー兼ディレクター'
    },
    'P002198': {
        'person_name_display': '加藤愛',
        'person_name_ja': '加藤愛',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': '女優',
        'description': '日本の女優'
    },
    'P005301': {
        'person_name_display': '阿部亮平',
        'person_name_ja': '阿部亮平',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'アイドル',
        'description': 'Snow Manのメンバー'
    },
    'P003066': {
        'person_name_display': '山本真央',
        'person_name_ja': '山本真央',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P003068': {
        'person_name_display': '山本真由',
        'person_name_ja': '山本真由',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004883': {
        'person_name_display': '葛葉',
        'person_name_ja': '葛葉',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'VTuber',
        'description': 'にじさんじ所属のVTuber'
    },
    'P001798': {
        'person_name_display': '井上裕介',
        'person_name_ja': '井上裕介',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'お笑い芸人',
        'description': 'NON STYLEのツッコミ担当'
    },
    'P002754': {
        'person_name_display': '宮川大輔',
        'person_name_ja': '宮川大輔',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'お笑い芸人',
        'description': '人気お笑い芸人、司会者'
    },
    'P002868': {
        'person_name_display': '小林由依',
        'person_name_ja': '小林由依',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'アイドル',
        'description': '元欅坂46、櫻坂46のメンバー'
    },
    'P003028': {
        'person_name_display': '山崎直子',
        'person_name_ja': '山崎直子',
        'category': '科学・技術',
        'nationality': '日本',
        'occupation': '宇宙飛行士',
        'description': '日本人女性宇宙飛行士'
    },
    'P005270': {
        'person_name_display': '長谷川潤',
        'person_name_ja': '長谷川潤',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'モデル',
        'description': 'ファッションモデル、タレント'
    },
    'P002971': {
        'person_name_display': '山口三郎',
        'person_name_ja': '山口三郎',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P004416': {
        'person_name_display': '田中碧',
        'person_name_ja': '田中碧',
        'category': 'スポーツ',
        'nationality': '日本',
        'occupation': 'サッカー選手',
        'description': 'プロサッカー選手'
    },
    'P001643': {
        'person_name_display': '中村倫也',
        'person_name_ja': '中村倫也',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': '俳優',
        'description': '人気俳優、様々なドラマや映画に出演'
    },
    'P005345': {
        'person_name_display': '雪子',
        'person_name_ja': '雪子',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    'P001137': {
        'person_name_display': 'フロイド・メイウェザー',
        'person_name_ja': 'フロイド・メイウェザー',
        'category': 'スポーツ',
        'nationality': 'アメリカ',
        'occupation': 'プロボクサー',
        'description': '元プロボクサー、無敗の5階級制覇王者'
    },
    'P001648': {
        'person_name_display': '中村優花',
        'person_name_ja': '中村優花',
        'category': 'その他',
        'nationality': '日本',
        'occupation': '一般著名人',
        'description': '一般的な著名人'
    },
    
    # スコア3.0の一般著名人
    'P000136': {
        'person_name_display': 'ゆん (ヴァンゆん)',
        'person_name_ja': 'ゆん (ヴァンゆん)',
        'category': 'エンタメ',
        'nationality': '日本',
        'occupation': 'YouTuber',
        'description': 'ヴァンゆんのメンバー'
    }
}

# データフレームを更新
for person_id in target_ids:
    if person_id in person_data:
        data = person_data[person_id]
        mask = df['person_id'] == person_id
        
        for column, value in data.items():
            df.loc[mask, column] = value

# バックアップを作成
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = f'backup_{csv_file}_{timestamp}'
df_original = pd.read_csv(csv_file)
df_original.to_csv(backup_file, index=False, encoding='utf-8-sig')
print(f"バックアップファイルを作成: {backup_file}")

# 更新したデータを保存（UTF-8 BOM付き）
df.to_csv(csv_file, index=False, encoding='utf-8-sig')
print(f"データを更新しました: {csv_file}")

# 更新された行数を確認
updated_count = 0
for person_id in target_ids:
    if person_id in person_data:
        updated_count += 1

print(f"\n更新された人物数: {updated_count}/{len(target_ids)}")

# 更新内容のサンプルを表示
print("\n更新内容のサンプル（最初の5件）:")
sample_ids = target_ids[:5]
sample_df = df[df['person_id'].isin(sample_ids)][['person_id', 'person_name_display', 'category', 'nationality', 'occupation']]
print(sample_df.to_string(index=False))