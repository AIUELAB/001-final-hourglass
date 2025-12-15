#!/usr/bin/env python3
"""
Group Entity Processor - Phase 3
グループ名（バンド、お笑いコンビ等）を個人に分割する処理
"""

import json
import re
from typing import Dict, List, Tuple, Optional
import logging
from pathlib import Path

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GroupEntityProcessor:
    """グループエンティティを個人に分割するプロセッサー"""

    def __init__(self):
        """初期化"""
        # 既知のグループと個人のマッピング
        self.known_groups = self._load_known_groups()

        # グループ判定パターン
        self.group_patterns = [
            r'.*コンビ$',
            r'.*トリオ$',
            r'.*バンド$',
            r'.*ユニット$',
            r'.*グループ$',
            r'.*兄弟$',
            r'.*姉妹$',
            r'.*ブラザーズ$',
            r'.*シスターズ$',
            r'.*ファミリー$',
            r'.*オーケストラ$',
            r'.*楽団$',
            r'.*合唱団$',
            r'.*劇団$',
            r'.*一座$',
            r'.*カルテット$',
            r'.*クインテット$',
            r'.*デュオ$',
            r'.*ズ$',  # 〜ズ（複数形）
            r'THE.*',  # THE で始まるバンド名
            r'.*&.*',  # & が含まれる（デュオ等）
            r'.*×.*',  # × が含まれる（コラボ等）
            r'.*with.*',  # with が含まれる
            r'.*feat\..*',  # feat. が含まれる
            r'.*vs.*',  # vs が含まれる
        ]

        # 統計情報
        self.stats = {
            'total_processed': 0,
            'groups_found': 0,
            'individuals_extracted': 0,
            'groups_unknown': 0
        }

    def _load_known_groups(self) -> Dict[str, List[str]]:
        """既知のグループとメンバーのマッピングをロード"""
        known_groups = {
            # お笑いコンビ・トリオ
            'ダウンタウン': ['松本人志', '浜田雅功'],
            'ナインティナイン': ['岡村隆史', '矢部浩之'],
            'さまぁ～ず': ['三村マサカズ', '大竹一樹'],
            'くりぃむしちゅー': ['上田晋也', '有田哲平'],
            'オードリー': ['若林正恭', '春日俊彰'],
            'サンドウィッチマン': ['伊達みきお', '富澤たけし'],
            '千鳥': ['大悟', 'ノブ'],
            'かまいたち': ['山内健司', '濱家隆一'],
            '霜降り明星': ['せいや', '粗品'],
            'EXIT': ['りんたろー。', '兼近大樹'],
            'ミルクボーイ': ['駒場孝', '内海崇'],
            '見取り図': ['盛山晋太郎', 'リリー'],
            'ニューヨーク': ['嶋佐和也', '屋敷裕政'],
            '空気階段': ['水川かたまり', '鈴木もぐら'],
            'ランジャタイ': ['伊藤幸司', '国崎和也'],
            '錦鯉': ['長谷川雅紀', '渡辺隆'],
            'マヂカルラブリー': ['野田クリスタル', '村上'],
            'ウエストランド': ['井口浩之', '河本太'],
            '男性ブランコ': ['浦井のりひろ', '平井まさあき'],
            'ロングコートダディ': ['堂前透', '兎'],

            # 音楽グループ・バンド
            'YOASOBI': ['Ayase', 'ikura'],
            'Official髭男dism': ['藤原聡', '小笹大輔', '楢崎誠', '松浦匡希'],
            'King Gnu': ['常田大希', '勢喜遊', '新井和輝', '井口理'],
            'Mrs. GREEN APPLE': ['大森元貴', '若井滉斗', '藤澤涼架'],
            'back number': ['清水依与吏', '小島和也', '栗原寿'],
            'ONE OK ROCK': ['Taka', 'Toru', 'Ryota', 'Tomoya'],
            'RADWIMPS': ['野田洋次郎', '桑原彰', '武田祐介'],
            'BUMP OF CHICKEN': ['藤原基央', '増川弘明', '直井由文', '升秀夫'],
            'Mr.Children': ['桜井和寿', '田原健一', '中川敬輔', '鈴木英哉'],
            'サザンオールスターズ': ['桑田佳祐', '関口和之', '松田弘', '原由子', '野沢秀行'],
            'B\'z': ['稲葉浩志', '松本孝弘'],
            'GLAY': ['TAKURO', 'TERU', 'HISASHI', 'JIRO'],
            'L\'Arc~en~Ciel': ['hyde', 'tetsuya', 'ken', 'yukihiro'],
            'X JAPAN': ['YOSHIKI', 'TOSHI', 'PATA', 'HEATH', 'SUGIZO'],
            'LUNA SEA': ['RYUICHI', 'SUGIZO', 'INORAN', 'J', '真矢'],
            '嵐': ['大野智', '櫻井翔', '相葉雅紀', '二宮和也', '松本潤'],
            'SMAP': ['中居正広', '木村拓哉', '稲垣吾郎', '草彅剛', '香取慎吾'],
            'TOKIO': ['城島茂', '山口達也', '国分太一', '松岡昌宏', '長瀬智也'],
            'V6': ['坂本昌行', '長野博', '井ノ原快彦', '森田剛', '三宅健', '岡田准一'],
            'KinKi Kids': ['堂本光一', '堂本剛'],
            'Kis-My-Ft2': ['北山宏光', '千賀健永', '宮田俊哉', '横尾渉', '藤ヶ谷太輔', '玉森裕太', '二階堂高嗣'],
            'Hey! Say! JUMP': ['山田涼介', '知念侑李', '中島裕翔', '岡本圭人', '有岡大貴', '伊野尾慧', '髙木雄也', '八乙女光', '薮宏太'],
            'Snow Man': ['深澤辰哉', '佐久間大介', '渡辺翔太', '宮舘涼太', '岩本照', '阿部亮平', '向井康二', 'ラウール', '目黒蓮'],
            'SixTONES': ['ジェシー', '京本大我', '松村北斗', '髙地優吾', '森本慎太郎', '田中樹'],
            'なにわ男子': ['西畑大吾', '大西流星', '道枝駿佑', '高橋恭平', '長尾謙杜', '藤原丈一郎', '大橋和也'],

            # K-POPグループ
            'BTS': ['RM', 'Jin', 'SUGA', 'j-hope', 'Jimin', 'V', 'Jung Kook'],
            'BLACKPINK': ['ジス', 'ジェニー', 'ロゼ', 'リサ'],
            'TWICE': ['ナヨン', 'ジョンヨン', 'モモ', 'サナ', 'ジヒョ', 'ミナ', 'ダヒョン', 'チェヨン', 'ツウィ'],
            'Stray Kids': ['バンチャン', 'リノ', 'チャンビン', 'ヒョンジン', 'ハン', 'フィリックス', 'スンミン', 'アイエン'],
            'SEVENTEEN': ['エスクプス', 'ジョンハン', 'ジョシュア', 'ジュン', 'ホシ', 'ウォヌ', 'ウジ', 'ドギョム', 'ミンギュ', 'ディエイト', 'スングァン', 'バーノン', 'ディノ'],
            'ENHYPEN': ['ヒスン', 'ジェイ', 'ジェイク', 'ソンフン', 'ソヌ', 'ジョンウォン', 'ニキ'],
            'NCT': ['テヨン', 'ジャニー', 'テン', 'ジェヒョン', 'ウィンウィン', 'ジョンウ', 'ルーカス', 'マーク', 'シャオジュン', 'ヘンドリー', 'ロンジュン', 'ジェノ', 'ヘチャン', 'ジェミン', 'ヤンヤン', 'ショウタロウ', 'ソンチャン', 'チョンロ', 'チソン'],

            # YouTuberグループ
            'フィッシャーズ': ['シルクロード', 'マサイ', 'ンダホ', 'ぺけたん', 'ダーマ', 'ザカオ', 'モトキ'],
            '東海オンエア': ['てつや', 'しばゆー', 'りょう', 'としみつ', 'ゆめまる', '虫眼鏡'],
            'コムドット': ['やまと', 'ゆうた', 'ゆうま', 'ひゅうが', 'あむぎり'],
            'スカイピース': ['テオ', 'じん'],
            '水溜りボンド': ['カンタ', 'トミー'],
            'QuizKnock': ['伊沢拓司', '川上拓朗', '河村拓哉', '須貝駿貴', 'こうちゃん', '山本祥彰', 'ふくらP', '鶴崎修功'],

            # スポーツチーム（代表的な選手のみ）
            '侍ジャパン': ['大谷翔平', 'ダルビッシュ有', '山田哲人', '村上宗隆'],  # 代表選手のみ
            'なでしこジャパン': ['澤穂希', '宮間あや', '川澄奈穂美'],  # 代表選手のみ

            # バラエティ番組グループ
            'ロンドンブーツ1号2号': ['田村淳', '田村亮'],
            'くずコンビ': ['木梨憲武', '石橋貴明'],
            'ウッチャンナンチャン': ['内村光良', '南原清隆'],
            'とんねるず': ['石橋貴明', '木梨憲武'],
            '爆笑問題': ['太田光', '田中裕二'],
            'ネプチューン': ['名倉潤', '原田泰造', '堀内健'],
            'ココリコ': ['遠藤章造', '田中直樹'],
            'ロバート': ['秋山竜次', '馬場裕之', '山本博'],
            'ジャルジャル': ['後藤淳平', '福徳秀介'],
            'ハライチ': ['岩井勇気', '澤部佑'],
            'バナナマン': ['設楽統', '日村勇紀'],
            'おぎやはぎ': ['小木博明', '矢作兼'],
            'チュートリアル': ['徳井義実', '福田充徳'],
            'ブラックマヨネーズ': ['小杉竜一', '吉田敬'],
            'フットボールアワー': ['岩尾望', '後藤輝基'],
            'NON STYLE': ['石田明', '井上裕介'],
            'パンクブーブー': ['佐藤哲夫', '黒瀬純'],
            'トレンディエンジェル': ['斎藤司', 'たかし'],
            'ピース': ['綾部祐二', '又吉直樹'],
            'アンジャッシュ': ['児嶋一哉', '渡部建'],
            'インパルス': ['板倉俊之', '堤下敦'],
            'ナイツ': ['塙宣之', '土屋伸之'],
            '南海キャンディーズ': ['山里亮太', 'しずちゃん'],
            'オリエンタルラジオ': ['中田敦彦', '藤森慎吾'],
            'ハリセンボン': ['近藤春菜', '箕輪はるか'],
            '北陽': ['虻川美穂子', '伊藤さおり'],
            'TKO': ['木下隆行', '木本武宏'],
            'ライセンス': ['藤原一裕', '井本貴史'],
            'スピードワゴン': ['井戸田潤', '小沢一敬'],
            'キングコング': ['西野亮廣', '梶原雄太'],
            '雨上がり決死隊': ['宮迫博之', '蛍原徹'],
            'よゐこ': ['有野晋哉', '濱口優'],
            'ガレッジセール': ['川田広樹', 'ゴリ'],
            '極楽とんぼ': ['加藤浩次', '山本圭壱'],
            '次長課長': ['河本準一', '井上聡'],
            '品川庄司': ['品川祐', '庄司智春'],
            'タカアンドトシ': ['タカ', 'トシ'],
            '博多華丸・大吉': ['博多華丸', '博多大吉'],
            '東京03': ['飯塚悟志', '豊本明長', '角田晃広'],
            'パンサー': ['向井慧', '尾形貴弘', '菅良太郎'],
            'ハナコ': ['岡部大', '秋山寛貴', '菊田竜大'],
            '四千頭身': ['後藤拓実', '都築拓紀', '石橋遼大'],
            '３時のヒロイン': ['福田麻貴', 'ゆめっち', 'かなで'],
            'ぺこぱ': ['松陰寺太勇', 'シュウペイ'],
            'ゆにばーす': ['はら', '川瀬名人'],

            # 女性アイドルグループ
            'AKB48': ['渡辺麻友', '指原莉乃', '柏木由紀'],  # 代表的メンバーのみ
            '乃木坂46': ['白石麻衣', '西野七瀬', '生田絵梨花'],  # 代表的メンバーのみ
            '櫻坂46': ['菅井友香', '土生瑞穂', '渡邉理佐'],  # 代表的メンバーのみ
            '日向坂46': ['佐々木久美', '加藤史帆', '小坂菜緒'],  # 代表的メンバーのみ
            'モーニング娘。': ['新垣里沙', '道重さゆみ', '田中れいな'],  # 代表的メンバーのみ
            'Perfume': ['のっち', 'かしゆか', 'あ～ちゃん'],
            'BABYMETAL': ['SU-METAL', 'MOAMETAL'],
            'NiziU': ['マコ', 'リオ', 'マヤ', 'リク', 'アヤカ', 'マユカ', 'リマ', 'ミイヒ', 'ニナ'],
            'BiSH': ['アイナ・ジ・エンド', 'セントチヒロ・チッチ', 'モモコグミカンパニー', 'ハシヤスメ・アツコ', 'リンリン', 'アユニ・D'],

            # 声優ユニット
            'μ\'s': ['新田恵海', '内田彩', '三森すずこ', '南條愛乃', 'Pile', '楠田亜衣奈', '飯田里穂', '徳井青空', '久保ユリカ'],
            'Aqours': ['伊波杏樹', '逢田梨香子', '諏訪ななか', '小宮有紗', '斉藤朱夏', '小林愛香', '高槻かなこ', '鈴木愛奈', '降幡愛'],
        }

        return known_groups

    def is_group_entity(self, name: str) -> bool:
        """
        名前がグループエンティティかどうかを判定

        Args:
            name: 判定する名前

        Returns:
            グループならTrue
        """
        # 既知のグループに含まれるか
        if name in self.known_groups:
            return True

        # パターンマッチング
        for pattern in self.group_patterns:
            if re.match(pattern, name):
                return True

        # occupationフィールドでの判定も可能（別途実装）

        return False

    def extract_individuals(self, group_name: str) -> List[str]:
        """
        グループから個人を抽出

        Args:
            group_name: グループ名

        Returns:
            個人名のリスト
        """
        # 既知のグループから取得
        if group_name in self.known_groups:
            return self.known_groups[group_name]

        # 不明なグループ
        logger.warning(f"未知のグループ: {group_name}")
        self.stats['groups_unknown'] += 1

        # グループ名自体を返す（削除候補として）
        return []

    def process_entity(self, person_data: Dict) -> List[Dict]:
        """
        エンティティを処理（グループなら個人に分割）

        Args:
            person_data: 人物データ

        Returns:
            処理後の人物データのリスト
        """
        self.stats['total_processed'] += 1

        name = person_data.get('person_name_display', person_data.get('person_name', ''))

        if not name:
            return [person_data]

        # グループ判定
        if self.is_group_entity(name):
            self.stats['groups_found'] += 1
            individuals = self.extract_individuals(name)

            if individuals:
                # 個人データを生成
                result = []
                for individual_name in individuals:
                    individual_data = person_data.copy()
                    individual_data['person_name'] = individual_name
                    individual_data['person_name_display'] = individual_name
                    individual_data['original_group'] = name
                    individual_data['is_group_member'] = True
                    result.append(individual_data)
                    self.stats['individuals_extracted'] += 1

                logger.info(f"グループ '{name}' から {len(individuals)}人を抽出")
                return result
            else:
                # 未知のグループは削除候補としてマーク
                person_data['is_unknown_group'] = True
                person_data['should_delete'] = True
                person_data['deletion_reason'] = '未知のグループエンティティ'
                return [person_data]

        # 個人の場合はそのまま返す
        return [person_data]

    def process_batch(self, persons: List[Dict]) -> Tuple[List[Dict], Dict]:
        """
        バッチ処理

        Args:
            persons: 人物データのリスト

        Returns:
            (処理後の人物データリスト, 統計情報)
        """
        result = []

        for person in persons:
            processed = self.process_entity(person)
            result.extend(processed)

        # 統計情報
        stats = {
            'input_count': len(persons),
            'output_count': len(result),
            'groups_found': self.stats['groups_found'],
            'individuals_extracted': self.stats['individuals_extracted'],
            'groups_unknown': self.stats['groups_unknown'],
            'expansion_rate': len(result) / max(len(persons), 1)
        }

        return result, stats

    def add_known_group(self, group_name: str, members: List[str]) -> None:
        """
        新しいグループを追加

        Args:
            group_name: グループ名
            members: メンバーリスト
        """
        self.known_groups[group_name] = members
        logger.info(f"グループ '{group_name}' を追加（メンバー: {len(members)}人）")

    def save_known_groups(self, filepath: str = "known_groups.json") -> None:
        """
        既知のグループをファイルに保存

        Args:
            filepath: 保存先ファイルパス
        """
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.known_groups, f, ensure_ascii=False, indent=2)
        logger.info(f"既知のグループを保存: {filepath}")

    def load_additional_groups(self, filepath: str) -> None:
        """
        追加のグループデータをロード

        Args:
            filepath: グループデータファイルパス
        """
        if Path(filepath).exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                additional_groups = json.load(f)
                self.known_groups.update(additional_groups)
                logger.info(f"追加グループをロード: {len(additional_groups)}グループ")


def main():
    """メイン処理（テスト用）"""
    print("=" * 60)
    print("Group Entity Processor")
    print("グループエンティティの個人分割処理")
    print("=" * 60)
    print()

    # プロセッサー初期化
    processor = GroupEntityProcessor()

    # テストデータ
    test_data = [
        {'person_name': 'ダウンタウン', 'person_name_display': 'ダウンタウン', 'occupation': 'お笑いコンビ'},
        {'person_name': 'BTS', 'person_name_display': 'BTS', 'occupation': 'K-POPグループ'},
        {'person_name': 'YOASOBI', 'person_name_display': 'YOASOBI', 'occupation': '音楽ユニット'},
        {'person_name': '大谷翔平', 'person_name_display': '大谷翔平', 'occupation': '野球選手'},
        {'person_name': 'HIKAKIN', 'person_name_display': 'HIKAKIN', 'occupation': 'YouTuber'},
        {'person_name': '千鳥', 'person_name_display': '千鳥', 'occupation': 'お笑いコンビ'},
        {'person_name': '謎のグループ', 'person_name_display': '謎のグループ', 'occupation': 'グループ'},
    ]

    # 処理実行
    result, stats = processor.process_batch(test_data)

    # 結果表示
    print("=== 処理結果 ===")
    print(f"入力: {stats['input_count']}件")
    print(f"出力: {stats['output_count']}件")
    print(f"グループ発見: {stats['groups_found']}件")
    print(f"個人抽出: {stats['individuals_extracted']}人")
    print(f"未知のグループ: {stats['groups_unknown']}件")
    print(f"拡張率: {stats['expansion_rate']:.2f}倍")
    print()

    print("=== 詳細 ===")
    for item in result:
        if item.get('is_group_member'):
            print(f"✅ {item['person_name']} (元: {item['original_group']})")
        elif item.get('is_unknown_group'):
            print(f"❌ {item['person_name']} -> 削除候補（未知のグループ）")
        else:
            print(f"👤 {item['person_name']} (個人)")

    # 既知のグループを保存
    processor.save_known_groups()
    print()
    print("✅ 処理完了")


if __name__ == "__main__":
    main()
