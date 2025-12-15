#!/usr/bin/env python3
"""
Ultra Think 段階的データベース拡張システム
高品質を維持しながら段階的に人数を増やす戦略的アプローチ
"""

import json
import csv
import time
import os
from datetime import datetime
from typing import Dict, List, Set
from dataclasses import dataclass, asdict
import logging
import hashlib

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 定数定義
COMPUTER_SCIENTIST = "計算機科学者"

@dataclass
class ProgressivePerson:
    """段階的拡張用の人物データ"""
    person_name: str
    person_name_ja: str
    person_name_display: str
    birth_year: int

    # 基本情報
    nationality: str = ""
    occupation: str = ""
    main_category: str = ""
    subcategory: str = ""
    description: str = ""

    # スコア
    historical_impact: int = 0
    educational_value: int = 0
    cultural_significance: int = 0
    global_recognition: int = 0

    # メタ情報
    grade: str = ""
    era: str = ""
    phase: int = 0  # 収集フェーズ

    def to_dict(self) -> Dict:
        return asdict(self)

    def generate_id(self) -> str:
        """一意のIDを生成"""
        unique_str = f"{self.person_name}_{self.birth_year}"
        return hashlib.md5(unique_str.encode()).hexdigest()[:8]


class UltraThinkProgressiveExpansion:
    """Ultra Think段階的拡張システム"""

    def __init__(self):
        """初期化"""
        self.collected_people: List[ProgressivePerson] = []
        self.existing_ids: Set[str] = set()
        self.checkpoint_file = "progressive_expansion_checkpoint.json"
        self.phase_data = {}

        # フェーズ定義
        self.phases = {
            1: {"name": "基礎構築", "target": 25, "completed": True},
            2: {"name": "第一次拡張", "target": 50, "completed": False},
            3: {"name": "第二次拡張", "target": 100, "completed": False},
            4: {"name": "第三次拡張", "target": 200, "completed": False},
            5: {"name": "第四次拡張", "target": 400, "completed": False},
        }

        # 既存データを読み込み
        self.load_existing_data()

    def load_existing_data(self):
        """既存データを読み込む"""
        try:
            # 既に収集済みの25人を読み込み
            if os.path.exists("ultra_think_load_balanced_20250825_124337.csv"):
                with open("ultra_think_load_balanced_20250825_124337.csv", 'r', encoding='utf-8-sig') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        person_id = hashlib.md5(f"{row['person_name']}_{row['birth_year']}".encode()).hexdigest()[:8]
                        self.existing_ids.add(person_id)
                logger.info(f"既存データ読み込み: {len(self.existing_ids)}人")
        except Exception as e:
            logger.warning(f"既存データ読み込みエラー: {e}")

    def get_phase_2_people(self) -> List[ProgressivePerson]:
        """フェーズ2: ノーベル賞受賞者と思想家（50人）"""
        people = []

        # ノーベル物理学賞
        nobel_physics = [
            ("Wilhelm Röntgen", "ヴィルヘルム・レントゲン", "レントゲン", 1845, "ドイツ", "物理学者"),
            ("Max Planck", "マックス・プランク", "プランク", 1858, "ドイツ", "物理学者"),
            ("Niels Bohr", "ニールス・ボーア", "ボーア", 1885, "デンマーク", "物理学者"),
            ("Werner Heisenberg", "ヴェルナー・ハイゼンベルク", "ハイゼンベルク", 1901, "ドイツ", "物理学者"),
            ("Erwin Schrödinger", "エルヴィン・シュレーディンガー", "シュレーディンガー", 1887, "オーストリア", "物理学者"),
        ]

        # ノーベル化学賞
        nobel_chemistry = [
            ("Jacobus van 't Hoff", "ヤコブス・ファント・ホッフ", "ファント・ホッフ", 1852, "オランダ", "化学者"),
            ("Emil Fischer", "エミール・フィッシャー", "フィッシャー", 1852, "ドイツ", "化学者"),
            ("Svante Arrhenius", "スヴァンテ・アレニウス", "アレニウス", 1859, "スウェーデン", "化学者"),
            ("Ernest Rutherford", "アーネスト・ラザフォード", "ラザフォード", 1871, "ニュージーランド", "物理学者"),
            ("Otto Hahn", "オットー・ハーン", "ハーン", 1879, "ドイツ", "化学者"),
        ]

        # ノーベル医学・生理学賞
        nobel_medicine = [
            ("Emil von Behring", "エミール・フォン・ベーリング", "ベーリング", 1854, "ドイツ", "医学者"),
            ("Robert Koch", "ロベルト・コッホ", "コッホ", 1843, "ドイツ", "細菌学者"),
            ("Ivan Pavlov", "イワン・パブロフ", "パブロフ", 1849, "ロシア", "生理学者"),
            ("Alexander Fleming", "アレクサンダー・フレミング", "フレミング", 1881, "イギリス", "細菌学者"),
            ("Jonas Salk", "ジョナス・ソーク", "ソーク", 1914, "アメリカ", "医学者"),
        ]

        # 哲学者・思想家
        philosophers = [
            ("Socrates", "ソクラテス", "ソクラテス", -469, "ギリシャ", "哲学者"),
            ("Plato", "プラトン", "プラトン", -428, "ギリシャ", "哲学者"),
            ("Aristotle", "アリストテレス", "アリストテレス", -384, "ギリシャ", "哲学者"),
            ("René Descartes", "ルネ・デカルト", "デカルト", 1596, "フランス", "哲学者"),
            ("Immanuel Kant", "イマニュエル・カント", "カント", 1724, "ドイツ", "哲学者"),
            ("Georg Wilhelm Friedrich Hegel", "ゲオルク・ヴィルヘルム・フリードリヒ・ヘーゲル", "ヘーゲル", 1770, "ドイツ", "哲学者"),
            ("Friedrich Nietzsche", "フリードリヒ・ニーチェ", "ニーチェ", 1844, "ドイツ", "哲学者"),
            ("Jean-Paul Sartre", "ジャン＝ポール・サルトル", "サルトル", 1905, "フランス", "哲学者"),
        ]

        # 経済学者
        economists = [
            ("Adam Smith", "アダム・スミス", "アダム・スミス", 1723, "イギリス", "経済学者"),
            ("Karl Marx", "カール・マルクス", "マルクス", 1818, "ドイツ", "経済学者"),
            ("John Maynard Keynes", "ジョン・メイナード・ケインズ", "ケインズ", 1883, "イギリス", "経済学者"),
            ("Milton Friedman", "ミルトン・フリードマン", "フリードマン", 1912, "アメリカ", "経済学者"),
            ("Joseph Schumpeter", "ヨーゼフ・シュンペーター", "シュンペーター", 1883, "オーストリア", "経済学者"),
        ]

        # 探検家・冒険家
        explorers = [
            ("Christopher Columbus", "クリストファー・コロンブス", "コロンブス", 1451, "イタリア", "探検家"),
            ("Vasco da Gama", "ヴァスコ・ダ・ガマ", "ダ・ガマ", 1469, "ポルトガル", "探検家"),
            ("Ferdinand Magellan", "フェルディナンド・マゼラン", "マゼラン", 1480, "ポルトガル", "探検家"),
            ("James Cook", "ジェームズ・クック", "クック", 1728, "イギリス", "探検家"),
            ("David Livingstone", "デイヴィッド・リヴィングストン", "リヴィングストン", 1813, "イギリス", "探検家"),
        ]

        # 作家・文学者
        writers = [
            ("William Shakespeare", "ウィリアム・シェイクスピア", "シェイクスピア", 1564, "イギリス", "劇作家"),
            ("Johann Wolfgang von Goethe", "ヨハン・ヴォルフガング・フォン・ゲーテ", "ゲーテ", 1749, "ドイツ", "作家"),
            ("Victor Hugo", "ヴィクトル・ユーゴー", "ユーゴー", 1802, "フランス", "作家"),
            ("Leo Tolstoy", "レフ・トルストイ", "トルストイ", 1828, "ロシア", "作家"),
            ("Mark Twain", "マーク・トウェイン", "マーク・トウェイン", 1835, "アメリカ", "作家"),
            ("Oscar Wilde", "オスカー・ワイルド", "ワイルド", 1854, "アイルランド", "作家"),
            ("Ernest Hemingway", "アーネスト・ヘミングウェイ", "ヘミングウェイ", 1899, "アメリカ", "作家"),
        ]

        # 発明家・起業家
        inventors = [
            ("James Watt", "ジェームズ・ワット", "ワット", 1736, "イギリス", "発明家"),
            ("Alexander Graham Bell", "アレクサンダー・グラハム・ベル", "ベル", 1847, "イギリス", "発明家"),
            ("Henry Ford", "ヘンリー・フォード", "フォード", 1863, "アメリカ", "実業家"),
            ("Thomas Watson", "トーマス・ワトソン", "ワトソン", 1874, "アメリカ", "実業家"),
        ]

        # すべてを結合
        all_people = (nobel_physics + nobel_chemistry + nobel_medicine +
                     philosophers + economists + explorers + writers + inventors)

        for data in all_people[:50]:  # 50人に制限
            person = ProgressivePerson(
                person_name=data[0],
                person_name_ja=data[1],
                person_name_display=data[2],
                birth_year=data[3],
                nationality=data[4],
                occupation=data[5],
                main_category="歴史的偉人",
                subcategory="フェーズ2",
                historical_impact=8,
                educational_value=9,
                cultural_significance=8,
                global_recognition=8,
                grade="S",
                phase=2
            )

            # 重複チェック
            if person.generate_id() not in self.existing_ids:
                people.append(person)
                self.existing_ids.add(person.generate_id())

        return people

    def get_phase_3_people(self) -> List[ProgressivePerson]:
        """フェーズ3: 日本の偉人と世界の科学者（100人）"""
        people = []

        # 日本の歴史人物（追加分）
        japanese_historical = [
            ("Minamoto no Yoritomo", "源頼朝", "源頼朝", 1147, "日本", "武将"),
            ("Minamoto no Yoshitsune", "源義経", "源義経", 1159, "日本", "武将"),
            ("Ashikaga Takauji", "足利尊氏", "足利尊氏", 1305, "日本", "武将"),
            ("Takeda Shingen", "武田信玄", "武田信玄", 1521, "日本", "武将"),
            ("Uesugi Kenshin", "上杉謙信", "上杉謙信", 1530, "日本", "武将"),
            ("Date Masamune", "伊達政宗", "伊達政宗", 1567, "日本", "武将"),
            ("Miyamoto Musashi", "宮本武蔵", "宮本武蔵", 1584, "日本", "剣豪"),
            ("Ito Hirobumi", "伊藤博文", "伊藤博文", 1841, "日本", "政治家"),
            ("Okuma Shigenobu", "大隈重信", "大隈重信", 1838, "日本", "政治家"),
            ("Yamagata Aritomo", "山縣有朋", "山縣有朋", 1838, "日本", "政治家"),
        ]

        # 日本の文化人
        japanese_cultural = [
            ("Murasaki Shikibu", "紫式部", "紫式部", 973, "日本", "作家"),
            ("Sei Shonagon", "清少納言", "清少納言", 966, "日本", "作家"),
            ("Matsuo Basho", "松尾芭蕉", "芭蕉", 1644, "日本", "俳人"),
            ("Hokusai", "葛飾北斎", "北斎", 1760, "日本", "浮世絵師"),
            ("Hiroshige", "歌川広重", "広重", 1797, "日本", "浮世絵師"),
            ("Natsume Soseki", "夏目漱石", "漱石", 1867, "日本", "作家"),
            ("Mori Ogai", "森鴎外", "鴎外", 1862, "日本", "作家"),
            ("Akutagawa Ryunosuke", "芥川龍之介", "芥川龍之介", 1892, "日本", "作家"),
            ("Kawabata Yasunari", "川端康成", "川端康成", 1899, "日本", "作家"),
            ("Mishima Yukio", "三島由紀夫", "三島由紀夫", 1925, "日本", "作家"),
        ]

        # アジアの偉人
        asian_leaders = [
            ("Confucius", "孔子", "孔子", -551, "中国", "思想家"),
            ("Laozi", "老子", "老子", -604, "中国", "思想家"),
            ("Sun Tzu", "孫子", "孫子", -544, "中国", "軍事思想家"),
            ("Qin Shi Huang", "秦始皇", "始皇帝", -259, "中国", "皇帝"),
            ("Genghis Khan", "チンギス・ハン", "チンギス・ハン", 1162, "モンゴル", "征服者"),
            ("Kublai Khan", "フビライ・ハン", "フビライ", 1215, "モンゴル", "皇帝"),
            ("Buddha", "ブッダ", "ブッダ", -563, "インド", "宗教家"),
            ("Ashoka", "アショーカ王", "アショーカ", -304, "インド", "皇帝"),
        ]

        # 古代の偉人
        ancient_leaders = [
            ("Alexander the Great", "アレクサンドロス大王", "アレクサンドロス", -356, "マケドニア", "征服者"),
            ("Julius Caesar", "ユリウス・カエサル", "カエサル", -100, "ローマ", "政治家"),
            ("Augustus", "アウグストゥス", "アウグストゥス", -63, "ローマ", "皇帝"),
            ("Cleopatra", "クレオパトラ", "クレオパトラ", -69, "エジプト", "女王"),
            ("Hannibal", "ハンニバル", "ハンニバル", -247, "カルタゴ", "将軍"),
            ("Archimedes", "アルキメデス", "アルキメデス", -287, "ギリシャ", "数学者"),
            ("Pythagoras", "ピタゴラス", "ピタゴラス", -570, "ギリシャ", "数学者"),
            ("Euclid", "ユークリッド", "ユークリッド", -330, "ギリシャ", "数学者"),
        ]

        # 20世紀の科学者
        modern_scientists = [
            ("Stephen Hawking", "スティーヴン・ホーキング", "ホーキング", 1942, "イギリス", "物理学者"),
            ("Richard Feynman", "リチャード・ファインマン", "ファインマン", 1918, "アメリカ", "物理学者"),
            ("Carl Sagan", "カール・セーガン", "セーガン", 1934, "アメリカ", "天文学者"),
            ("Linus Pauling", "ライナス・ポーリング", "ポーリング", 1901, "アメリカ", "化学者"),
            ("Watson and Crick", "ワトソン", "ワトソン", 1928, "アメリカ", "生物学者"),
            ("Francis Crick", "フランシス・クリック", "クリック", 1916, "イギリス", "生物学者"),
            ("Rosalind Franklin", "ロザリンド・フランクリン", "フランクリン", 1920, "イギリス", "化学者"),
            ("Barbara McClintock", "バーバラ・マクリントック", "マクリントック", 1902, "アメリカ", "遺伝学者"),
        ]

        # コンピュータサイエンスの先駆者
        computer_pioneers = [
            ("Alan Turing", "アラン・チューリング", "チューリング", 1912, "イギリス", COMPUTER_SCIENTIST),
            ("John von Neumann", "フォン・ノイマン", "フォン・ノイマン", 1903, "ハンガリー", "数学者"),
            ("Grace Hopper", "グレース・ホッパー", "ホッパー", 1906, "アメリカ", COMPUTER_SCIENTIST),
            ("Dennis Ritchie", "デニス・リッチー", "リッチー", 1941, "アメリカ", COMPUTER_SCIENTIST),
            ("Ken Thompson", "ケン・トンプソン", "トンプソン", 1943, "アメリカ", COMPUTER_SCIENTIST),
            ("Bjarne Stroustrup", "ビャーネ・ストロヴストルップ", "ストロヴストルップ", 1950, "デンマーク", COMPUTER_SCIENTIST),
            ("Tim Berners-Lee", "ティム・バーナーズ＝リー", "バーナーズ＝リー", 1955, "イギリス", COMPUTER_SCIENTIST),
        ]

        # すべてを結合（重複チェック付き）
        all_people = (japanese_historical + japanese_cultural + asian_leaders +
                     ancient_leaders + modern_scientists + computer_pioneers)

        for data in all_people:
            person = ProgressivePerson(
                person_name=data[0],
                person_name_ja=data[1],
                person_name_display=data[2],
                birth_year=data[3],
                nationality=data[4],
                occupation=data[5],
                main_category="歴史的偉人",
                subcategory="フェーズ3",
                historical_impact=8,
                educational_value=9,
                cultural_significance=8,
                global_recognition=7,
                grade="A",
                phase=3
            )

            # 重複チェック
            if person.generate_id() not in self.existing_ids:
                people.append(person)
                self.existing_ids.add(person.generate_id())

        return people[:100]  # 100人に制限

    def process_phase(self, phase: int, batch_size: int = 10) -> bool:
        """特定のフェーズを処理"""

        if phase not in self.phases:
            logger.error(f"無効なフェーズ: {phase}")
            return False

        phase_info = self.phases[phase]

        if phase_info["completed"]:
            logger.info(f"フェーズ {phase} は既に完了しています")
            return True

        logger.info(f"フェーズ {phase}: {phase_info['name']} を開始")
        logger.info(f"目標人数: {phase_info['target']}")

        try:
            # フェーズごとのデータを取得
            if phase == 2:
                phase_people = self.get_phase_2_people()
            elif phase == 3:
                phase_people = self.get_phase_3_people()
            else:
                logger.warning(f"フェーズ {phase} のデータ取得関数が未実装")
                return False

            # バッチ処理
            total_added = 0
            for i in range(0, len(phase_people), batch_size):
                batch = phase_people[i:i+batch_size]

                logger.info(f"バッチ処理中: {i//batch_size + 1}/{(len(phase_people)-1)//batch_size + 1}")

                for person in batch:
                    self.collected_people.append(person)
                    total_added += 1
                    time.sleep(0.05)  # API負荷対策

                # バッチ間の休憩
                if i + batch_size < len(phase_people):
                    time.sleep(1)

            # フェーズ完了
            self.phases[phase]["completed"] = True

            # 中間結果を保存
            self.save_phase_results(phase)

            logger.info(f"フェーズ {phase} 完了: {total_added}人追加")
            return True

        except Exception as e:
            logger.error(f"フェーズ {phase} 処理エラー: {e}")
            return False

    def save_phase_results(self, phase: int):
        """フェーズ結果を保存"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # フェーズのデータのみ抽出
        phase_data = [p for p in self.collected_people if p.phase == phase]

        # JSON形式
        json_file = f"ultra_think_phase_{phase}_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(
                [p.to_dict() for p in phase_data],
                f,
                ensure_ascii=False,
                indent=2
            )

        # CSV形式
        csv_file = f"ultra_think_phase_{phase}_{timestamp}.csv"
        with open(csv_file, 'w', encoding='utf-8-sig', newline='') as f:
            if phase_data:
                fieldnames = list(phase_data[0].to_dict().keys())
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                for person in phase_data:
                    writer.writerow(person.to_dict())

        logger.info(f"フェーズ {phase} 結果保存: {json_file}, {csv_file}")

    def run_progressive_expansion(self, target_phase: int = 2):
        """段階的拡張を実行"""

        logger.info("=" * 60)
        logger.info("Ultra Think 段階的拡張システム起動")
        logger.info(f"目標フェーズ: {target_phase}")
        logger.info("=" * 60)

        # 指定されたフェーズまで順次実行
        for phase in range(2, target_phase + 1):
            if phase not in self.phases:
                break

            logger.info(f"\n--- フェーズ {phase} ---")

            if not self.process_phase(phase):
                logger.error(f"フェーズ {phase} で停止")
                break

            # フェーズ間の休憩
            if phase < target_phase:
                logger.info("次のフェーズまで5秒待機...")
                time.sleep(5)

        # 最終統計
        self.generate_final_report()

        return True

    def generate_final_report(self):
        """最終レポートを生成"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"PROGRESSIVE_EXPANSION_REPORT_{timestamp}.md"

        # カテゴリ別統計
        categories: Dict[str, int] = {}
        phases_count: Dict[int, int] = {}

        for person in self.collected_people:
            # カテゴリ
            cat = person.subcategory or "未分類"
            categories[cat] = categories.get(cat, 0) + 1

            # フェーズ
            phase = person.phase
            phases_count[phase] = phases_count.get(phase, 0) + 1

        report = f"""# Ultra Think 段階的拡張レポート

## 実行日時
{datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}

## 拡張統計
- 総追加人数: {len(self.collected_people)}
- 既存データ: {len(self.existing_ids)}人

## フェーズ別進捗
"""
        for phase, info in self.phases.items():
            status = "✅ 完了" if info["completed"] else "⏳ 未実施"
            count = phases_count.get(phase, 0)
            report += f"- フェーズ {phase} ({info['name']}): {count}/{info['target']}人 {status}\n"

        report += f"""
## カテゴリ別内訳
"""
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            report += f"- {cat}: {count}人\n"

        report += f"""
## 品質指標
- 平均歴史的影響力: {sum(p.historical_impact for p in self.collected_people) / max(len(self.collected_people), 1):.1f}
- 平均教育的価値: {sum(p.educational_value for p in self.collected_people) / max(len(self.collected_people), 1):.1f}
- 平均文化的重要性: {sum(p.cultural_significance for p in self.collected_people) / max(len(self.collected_people), 1):.1f}

## 次のステップ
1. 既存データベースとの統合
2. 重複チェックと整合性確認
3. Firebase Episodesへの反映
"""

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"最終レポート生成: {report_file}")


def main():
    """メイン実行関数"""
    expansion = UltraThinkProgressiveExpansion()

    # フェーズ3（100人追加）まで実行
    success = expansion.run_progressive_expansion(target_phase=3)

    if success:
        logger.info("✅ 段階的拡張が正常に完了しました")
        logger.info(f"総収集人数: {len(expansion.collected_people)}人")
    else:
        logger.error("❌ 拡張中にエラーが発生しました")

    return success


if __name__ == "__main__":
    main()
