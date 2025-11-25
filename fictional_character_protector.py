#!/usr/bin/env python3
"""
架空キャラクター保護システム
Fictional Character Protection System

文化的影響力を持つ架空キャラクターを削除から保護する
ユーザー指示：「架空キャラクターは知名度があれば削除対象ではありません」
"""

import os
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
import re

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class FictionalCharacter:
    """架空キャラクターデータクラス"""
    id: str
    name: str
    name_en: Optional[str]
    source_work: str  # 作品名
    media_type: str  # アニメ、マンガ、ゲーム等
    cultural_impact_score: float  # 文化的影響力スコア (0-10)
    is_protected: bool  # 保護対象かどうか
    protection_reason: str  # 保護理由


class FictionalCharacterProtector:
    """
    架空キャラクター保護システム

    ユーザー明確指示：
    - 竈門炭治郎（鬼滅の刃）を保護
    - 孫悟空（ドラゴンボール）を保護
    - 知名度がある架空キャラクターは削除しない
    """

    def __init__(self):
        """初期化"""
        # 保護対象キャラクターデータベース
        self.protected_characters = self._load_protected_database()

        # 作品名パターン
        self.work_patterns = self._load_work_patterns()

        # 文化的影響力の閾値
        self.protection_threshold = 3.0  # 3.0以上は保護

        # 統計情報
        self.stats = {
            'total_checked': 0,
            'protected_count': 0,
            'fictional_found': 0,
            'famous_fictional': 0
        }

    def _load_protected_database(self) -> Dict[str, FictionalCharacter]:
        """
        保護対象キャラクターデータベース
        ユーザーが明示的に指定したキャラクター＋有名キャラクター
        """
        database = {}

        # ユーザー明示指定キャラクター（絶対保護）
        mandatory_protections = [
            FictionalCharacter(
                id='FC001',
                name='竈門炭治郎',
                name_en='Kamado Tanjiro',
                source_work='鬼滅の刃',
                media_type='アニメ/マンガ',
                cultural_impact_score=10.0,
                is_protected=True,
                protection_reason='ユーザー明示指定・社会現象級作品主人公'
            ),
            FictionalCharacter(
                id='FC002',
                name='孫悟空',
                name_en='Son Goku',
                source_work='ドラゴンボール',
                media_type='アニメ/マンガ',
                cultural_impact_score=10.0,
                is_protected=True,
                protection_reason='ユーザー明示指定・世界的認知度'
            )
        ]

        # その他の有名架空キャラクター
        famous_characters = [
            # 鬼滅の刃
            ('竈門禰豆子', 'Kamado Nezuko', '鬼滅の刃', 9.5),
            ('我妻善逸', 'Agatsuma Zenitsu', '鬼滅の刃', 9.0),
            ('嘴平伊之助', 'Hashibira Inosuke', '鬼滅の刃', 9.0),
            ('冨岡義勇', 'Tomioka Giyuu', '鬼滅の刃', 8.5),
            ('煉獄杏寿郎', 'Rengoku Kyojuro', '鬼滅の刃', 9.0),

            # ドラゴンボール
            ('ベジータ', 'Vegeta', 'ドラゴンボール', 9.5),
            ('ピッコロ', 'Piccolo', 'ドラゴンボール', 8.5),
            ('フリーザ', 'Frieza', 'ドラゴンボール', 9.0),
            ('トランクス', 'Trunks', 'ドラゴンボール', 8.0),

            # ワンピース
            ('モンキー・D・ルフィ', 'Monkey D. Luffy', 'ONE PIECE', 10.0),
            ('ロロノア・ゾロ', 'Roronoa Zoro', 'ONE PIECE', 9.0),
            ('ナミ', 'Nami', 'ONE PIECE', 8.5),
            ('サンジ', 'Sanji', 'ONE PIECE', 8.5),
            ('ニコ・ロビン', 'Nico Robin', 'ONE PIECE', 8.0),

            # NARUTO
            ('うずまきナルト', 'Uzumaki Naruto', 'NARUTO', 10.0),
            ('うちはサスケ', 'Uchiha Sasuke', 'NARUTO', 9.5),
            ('春野サクラ', 'Haruno Sakura', 'NARUTO', 8.0),
            ('はたけカカシ', 'Hatake Kakashi', 'NARUTO', 9.0),

            # 新世紀エヴァンゲリオン
            ('碇シンジ', 'Ikari Shinji', '新世紀エヴァンゲリオン', 9.0),
            ('綾波レイ', 'Ayanami Rei', '新世紀エヴァンゲリオン', 9.5),
            ('惣流・アスカ・ラングレー', 'Soryu Asuka Langley', '新世紀エヴァンゲリオン', 9.0),

            # 進撃の巨人
            ('エレン・イェーガー', 'Eren Yeager', '進撃の巨人', 9.5),
            ('ミカサ・アッカーマン', 'Mikasa Ackerman', '進撃の巨人', 9.0),
            ('リヴァイ', 'Levi', '進撃の巨人', 9.5),

            # 呪術廻戦
            ('虎杖悠仁', 'Itadori Yuji', '呪術廻戦', 8.5),
            ('伏黒恵', 'Fushiguro Megumi', '呪術廻戦', 8.0),
            ('釘崎野薔薇', 'Kugisaki Nobara', '呪術廻戦', 8.0),
            ('五条悟', 'Gojo Satoru', '呪術廻戦', 9.5),

            # スタジオジブリ作品
            ('となりのトトロ', 'Totoro', 'となりのトトロ', 10.0),
            ('千尋', 'Chihiro', '千と千尋の神隠し', 9.0),
            ('ハク', 'Haku', '千と千尋の神隠し', 8.5),
            ('もののけ姫', 'Princess Mononoke', 'もののけ姫', 9.0),
            ('ナウシカ', 'Nausicaa', '風の谷のナウシカ', 9.0),

            # ポケモン
            ('ピカチュウ', 'Pikachu', 'ポケットモンスター', 10.0),
            ('ミュウツー', 'Mewtwo', 'ポケットモンスター', 8.5),
            ('イーブイ', 'Eevee', 'ポケットモンスター', 8.0),

            # 名探偵コナン
            ('江戸川コナン', 'Edogawa Conan', '名探偵コナン', 9.5),
            ('工藤新一', 'Kudo Shinichi', '名探偵コナン', 9.0),
            ('毛利蘭', 'Mouri Ran', '名探偵コナン', 8.0),
            ('怪盗キッド', 'Kaito Kid', '名探偵コナン', 9.0),

            # ドラえもん
            ('ドラえもん', 'Doraemon', 'ドラえもん', 10.0),
            ('野比のび太', 'Nobi Nobita', 'ドラえもん', 9.0),
            ('源静香', 'Minamoto Shizuka', 'ドラえもん', 8.0),
            ('ジャイアン', 'Gian', 'ドラえもん', 8.5),
            ('スネ夫', 'Suneo', 'ドラえもん', 8.0),

            # クレヨンしんちゃん
            ('野原しんのすけ', 'Nohara Shinnosuke', 'クレヨンしんちゃん', 9.5),
            ('野原みさえ', 'Nohara Misae', 'クレヨンしんちゃん', 8.0),
            ('野原ひろし', 'Nohara Hiroshi', 'クレヨンしんちゃん', 8.0),

            # サンリオ
            ('ハローキティ', 'Hello Kitty', 'サンリオ', 10.0),
            ('マイメロディ', 'My Melody', 'サンリオ', 8.5),
            ('ポムポムプリン', 'Pompompurin', 'サンリオ', 8.0),
            ('シナモロール', 'Cinnamoroll', 'サンリオ', 8.5),

            # ディズニー（日本で人気）
            ('ミッキーマウス', 'Mickey Mouse', 'ディズニー', 10.0),
            ('ミニーマウス', 'Minnie Mouse', 'ディズニー', 9.0),
            ('ドナルドダック', 'Donald Duck', 'ディズニー', 9.0),
            ('プーさん', 'Winnie the Pooh', 'ディズニー', 9.5),

            # ゲームキャラクター
            ('マリオ', 'Mario', 'スーパーマリオ', 10.0),
            ('ルイージ', 'Luigi', 'スーパーマリオ', 8.5),
            ('ピーチ姫', 'Princess Peach', 'スーパーマリオ', 8.5),
            ('リンク', 'Link', 'ゼルダの伝説', 9.5),
            ('ゼルダ姫', 'Princess Zelda', 'ゼルダの伝説', 8.5),
            ('ソニック', 'Sonic', 'ソニック・ザ・ヘッジホッグ', 9.0),
            ('パックマン', 'Pac-Man', 'パックマン', 9.0),
            ('リュウ', 'Ryu', 'ストリートファイター', 8.5),
            ('春麗', 'Chun-Li', 'ストリートファイター', 8.5),
            ('クラウド', 'Cloud Strife', 'ファイナルファンタジーVII', 9.0),
            ('セフィロス', 'Sephiroth', 'ファイナルファンタジーVII', 8.5),

            # 美少女戦士セーラームーン
            ('月野うさぎ', 'Tsukino Usagi', '美少女戦士セーラームーン', 9.5),
            ('セーラームーン', 'Sailor Moon', '美少女戦士セーラームーン', 9.5),

            # 鋼の錬金術師
            ('エドワード・エルリック', 'Edward Elric', '鋼の錬金術師', 9.0),
            ('アルフォンス・エルリック', 'Alphonse Elric', '鋼の錬金術師', 8.5),

            # DEATH NOTE
            ('夜神月', 'Yagami Light', 'DEATH NOTE', 9.0),
            ('L', 'L', 'DEATH NOTE', 9.5),
            ('リューク', 'Ryuk', 'DEATH NOTE', 8.5),
        ]

        # データベースに追加
        for char in mandatory_protections:
            database[char.name] = char

        # 有名キャラクターを追加
        for i, (name, name_en, work, score) in enumerate(famous_characters, start=3):
            media_type = self._determine_media_type(work)
            char = FictionalCharacter(
                id=f'FC{i:03d}',
                name=name,
                name_en=name_en,
                source_work=work,
                media_type=media_type,
                cultural_impact_score=score,
                is_protected=(score >= self.protection_threshold),
                protection_reason=f'文化的影響力スコア: {score}/10'
            )
            database[name] = char

        logger.info(f"✅ {len(database)}体の架空キャラクターをデータベースに登録")
        return database

    def _load_work_patterns(self) -> List[Tuple[str, float]]:
        """
        作品名パターンと影響力スコア
        キャラクター名に作品名が含まれる場合の判定用
        """
        return [
            # 社会現象級作品 (10.0)
            (r'鬼滅の刃', 10.0),
            (r'ドラゴンボール', 10.0),
            (r'ONE PIECE|ワンピース', 10.0),
            (r'ポケ(ット)?モンスター|ポケモン', 10.0),
            (r'ドラえもん', 10.0),

            # 国民的作品 (9.0以上)
            (r'NARUTO|ナルト', 9.5),
            (r'名探偵コナン', 9.5),
            (r'クレヨンしんちゃん', 9.5),
            (r'新世紀エヴァンゲリオン|エヴァ', 9.5),
            (r'進撃の巨人', 9.5),
            (r'美少女戦士セーラームーン', 9.5),

            # 大ヒット作品 (8.0以上)
            (r'呪術廻戦', 8.5),
            (r'東京リベンジャーズ', 8.5),
            (r'SPY×FAMILY|スパイファミリー', 8.5),
            (r'チェンソーマン', 8.5),
            (r'僕のヒーローアカデミア|ヒロアカ', 8.5),
            (r'DEATH NOTE|デスノート', 9.0),
            (r'鋼の錬金術師|ハガレン', 9.0),
            (r'BLEACH|ブリーチ', 8.5),

            # ジブリ作品 (9.0以上)
            (r'となりのトトロ', 10.0),
            (r'千と千尋の神隠し', 9.5),
            (r'もののけ姫', 9.0),
            (r'風の谷のナウシカ', 9.0),
            (r'天空の城ラピュタ', 9.0),
            (r'魔女の宅急便', 9.0),

            # ゲーム作品 (8.0以上)
            (r'スーパーマリオ|マリオ', 10.0),
            (r'ゼルダの伝説', 9.5),
            (r'ファイナルファンタジー|FF', 9.0),
            (r'ドラゴンクエスト|ドラクエ|DQ', 9.0),
            (r'モンスターハンター|モンハン', 8.5),
            (r'ストリートファイター|スト', 8.5),
            (r'バイオハザード', 8.5),

            # その他有名作品
            (r'サンリオ', 9.0),
            (r'ディズニー', 10.0),
            (r'ガンダム', 9.0),
            (r'仮面ライダー', 9.0),
            (r'ウルトラマン', 9.0),
            (r'プリキュア', 8.5),
        ]

    def _determine_media_type(self, work: str) -> str:
        """作品名からメディアタイプを判定"""
        game_works = ['スーパーマリオ', 'ゼルダの伝説', 'ファイナルファンタジー',
                     'ドラゴンクエスト', 'ストリートファイター', 'ポケットモンスター']

        if any(game in work for game in game_works):
            return 'ゲーム'
        elif 'サンリオ' in work:
            return 'キャラクターグッズ'
        elif 'ディズニー' in work:
            return 'アニメーション'
        elif work in ['となりのトトロ', '千と千尋の神隠し', 'もののけ姫']:
            return 'アニメ映画'
        else:
            return 'アニメ/マンガ'

    def is_fictional_character(self, name: str, context: Optional[str] = None) -> bool:
        """
        架空キャラクター判定

        Args:
            name: 判定対象の名前
            context: 追加コンテキスト（説明文等）

        Returns:
            架空キャラクターかどうか
        """
        self.stats['total_checked'] += 1

        # 1. データベースに存在するか確認
        if name in self.protected_characters:
            self.stats['fictional_found'] += 1
            return True

        # 2. コンテキストから作品名を検出
        if context:
            for pattern, _ in self.work_patterns:
                if re.search(pattern, context, re.IGNORECASE):
                    self.stats['fictional_found'] += 1
                    logger.info(f"🎭 架空キャラクター検出（作品名）: {name}")
                    return True

        # 3. 名前パターンで判定
        fictional_indicators = [
            r'仮面ライダー',
            r'ウルトラマン',
            r'プリキュア',
            r'戦隊',
            r'セーラー[ムマヴジ]',  # セーラームーン等
            r'ゴジラ',
            r'ガンダム',
            r'エヴァ(ンゲリオン)?',
            r'ポケモン',
            r'デジモン',
            r'たまごっち',
            r'妖怪ウォッチ',
        ]

        for pattern in fictional_indicators:
            if re.search(pattern, name):
                self.stats['fictional_found'] += 1
                logger.info(f"🎭 架空キャラクター検出（パターン）: {name}")
                return True

        return False

    def should_protect(self, name: str,
                       context: Optional[str] = None,
                       current_score: float = 0.0) -> Tuple[bool, str]:
        """
        保護判定

        Args:
            name: 対象の名前
            context: 追加コンテキスト
            current_score: 現在のスコア

        Returns:
            (保護すべきか, 理由)
        """
        # 1. データベースの保護対象確認
        if name in self.protected_characters:
            char = self.protected_characters[name]
            if char.is_protected:
                self.stats['protected_count'] += 1
                self.stats['famous_fictional'] += 1
                return True, char.protection_reason

        # 2. 架空キャラクターかつスコアが閾値以上
        if self.is_fictional_character(name, context):
            if current_score >= self.protection_threshold:
                self.stats['protected_count'] += 1
                self.stats['famous_fictional'] += 1
                reason = f"架空キャラクター（スコア: {current_score:.2f} >= {self.protection_threshold}）"
                logger.info(f"🛡️ 保護対象: {name} - {reason}")
                return True, reason
            else:
                logger.info(f"⚠️ 架空だが知名度不足: {name} (スコア: {current_score:.2f})")
                return False, "架空キャラクターだが知名度不足"

        return False, "非架空または保護対象外"

    def calculate_cultural_impact(self, name: str,
                                 context: Optional[str] = None) -> float:
        """
        文化的影響力スコア計算

        Args:
            name: キャラクター名
            context: コンテキスト

        Returns:
            文化的影響力スコア (0-10)
        """
        # データベースに存在する場合
        if name in self.protected_characters:
            return self.protected_characters[name].cultural_impact_score

        # 作品名から推定
        if context:
            for pattern, base_score in self.work_patterns:
                if re.search(pattern, context, re.IGNORECASE):
                    # 主人公や主要キャラは+1点
                    if any(keyword in context for keyword in ['主人公', '主役', 'ヒーロー', 'ヒロイン']):
                        return min(10.0, base_score + 1.0)
                    return base_score

        # デフォルトスコア
        if self.is_fictional_character(name, context):
            return 5.0  # 架空キャラクターのデフォルト

        return 0.0

    def batch_protect(self, persons: List[Dict]) -> List[Dict]:
        """
        バッチ保護処理

        Args:
            persons: 人物リスト

        Returns:
            保護情報が追加された人物リスト
        """
        protected_persons = []

        for person in persons:
            name = person.get('name', '')
            context = person.get('description', '')
            current_score = person.get('integrated_score', 0.0)

            # 保護判定
            should_protect, reason = self.should_protect(name, context, current_score)

            # 文化的影響力計算
            cultural_impact = self.calculate_cultural_impact(name, context)

            # 結果を追加
            person_with_protection = person.copy()
            person_with_protection.update({
                'is_fictional': self.is_fictional_character(name, context),
                'is_protected': should_protect,
                'protection_reason': reason,
                'cultural_impact_score': cultural_impact
            })

            protected_persons.append(person_with_protection)

        return protected_persons

    def export_protection_report(self, output_path: str):
        """保護レポート出力"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        report = {
            'timestamp': timestamp,
            'statistics': self.stats,
            'protected_characters': [
                {
                    'name': char.name,
                    'name_en': char.name_en,
                    'source_work': char.source_work,
                    'cultural_impact_score': char.cultural_impact_score,
                    'protection_reason': char.protection_reason
                }
                for char in self.protected_characters.values()
                if char.is_protected
            ],
            'protection_rules': {
                'threshold': self.protection_threshold,
                'total_in_database': len(self.protected_characters),
                'total_protected': sum(1 for c in self.protected_characters.values() if c.is_protected)
            }
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"✅ 保護レポート出力: {output_path}")

        # サマリー表示
        print("\n" + "="*60)
        print("架空キャラクター保護システム - 実行結果")
        print("="*60)
        print(f"チェック総数: {self.stats['total_checked']}")
        print(f"架空キャラクター検出数: {self.stats['fictional_found']}")
        print(f"保護対象数: {self.stats['protected_count']}")
        print(f"有名架空キャラクター: {self.stats['famous_fictional']}")
        print("="*60)


def main():
    """メイン実行"""
    protector = FictionalCharacterProtector()

    # テストデータ
    test_persons = [
        {'name': '竈門炭治郎', 'description': '鬼滅の刃の主人公', 'integrated_score': 8.0},
        {'name': '孫悟空', 'description': 'ドラゴンボールの主人公', 'integrated_score': 9.0},
        {'name': 'ピカチュウ', 'description': 'ポケットモンスターのキャラクター', 'integrated_score': 10.0},
        {'name': 'ドラえもん', 'description': '未来から来た猫型ロボット', 'integrated_score': 10.0},
        {'name': '架空太郎', 'description': '無名の架空キャラクター', 'integrated_score': 1.0},
        {'name': 'HIKAKIN', 'description': '日本のYouTuber', 'integrated_score': 7.5},
    ]

    # バッチ保護処理
    protected_persons = protector.batch_protect(test_persons)

    # 結果表示
    print("\n保護判定結果:")
    print("-" * 60)
    for person in protected_persons:
        print(f"\n名前: {person['name']}")
        print(f"  架空キャラクター: {'はい' if person['is_fictional'] else 'いいえ'}")
        print(f"  保護対象: {'はい' if person['is_protected'] else 'いいえ'}")
        print(f"  保護理由: {person['protection_reason']}")
        print(f"  文化的影響力: {person['cultural_impact_score']:.1f}/10")

    # レポート出力
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"fictional_protection_report_{timestamp}.json"
    protector.export_protection_report(output_path)

    print(f"\n✅ 完了！レポートは {output_path} に保存されました")


if __name__ == "__main__":
    main()
