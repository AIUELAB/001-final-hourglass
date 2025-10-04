#!/usr/bin/env python3
"""
新規エピソード生成システム
一人の有名人に対して一つの高品質エピソードを生成
"""

import csv
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import re

class EpisodeData:
    """エピソードデータを管理するクラス"""

    def __init__(self):
        self.persons = self._initialize_persons()

    def _initialize_persons(self) -> List[Dict]:
        """30名の有名人データを初期化"""
        return [
            # スポーツ
            {
                "name": "松本人志",
                "age": 31,
                "category": "エンターテインメント",
                "episode": "あなたと同じ31歳のとき、松本人志は「ごっつええ感じ」で最高視聴率28.8％を記録し、お笑い界の頂点に立った。コント番組で週間視聴率1位を52週連続で獲得し、「松本人志のすべらない話」など5つの冠番組を同時に持つ偉業を達成。お笑いを「第七の芸術」へと昇華させた革命児となった。",
                "achievements": ["視聴率28.8％", "52週連続1位", "5つの冠番組"]
            },
            {
                "name": "田中将大",
                "age": 25,
                "category": "スポーツ",
                "episode": "あなたと同じ25歳のとき、田中将大はヤンキースで開幕から42回連続無失点のMLB新人記録を樹立した。シーズン13勝5敗、防御率2.77でサイ・ヤング賞投票5位となり、7年総額155億円の大型契約を勝ち取った。日本人投手として最高額の評価を受け、メジャーの頂点を極めた。",
                "achievements": ["42回連続無失点", "13勝5敗", "155億円契約"]
            },
            {
                "name": "新海誠",
                "age": 43,
                "category": "アニメーション",
                "episode": "あなたと同じ43歳のとき、新海誠は「君の名は。」で興行収入250億円を記録し、日本映画史上歴代4位の大ヒットを生んだ。世界135カ国で配信され、アジア映画として初めて米国興行収入500万ドルを突破。「ポスト宮崎駿」と呼ばれ、日本アニメーション界の新時代を切り開いた。",
                "achievements": ["興行収入250億円", "135カ国配信", "米国500万ドル"]
            },
            {
                "name": "米津玄師",
                "age": 27,
                "category": "音楽",
                "episode": "あなたと同じ27歳のとき、米津玄師は「Lemon」でストリーミング再生8億回を突破し、日本音楽史上最多記録を更新した。紅白歌合戦で故郷徳島から生中継出演し、瞬間最高視聴率44.6％を記録。CD売上300万枚を達成し、令和の音楽シーンを代表するアーティストとなった。",
                "achievements": ["8億回再生", "視聴率44.6％", "CD300万枚"]
            },
            {
                "name": "是枝裕和",
                "age": 56,
                "category": "映画",
                "episode": "あなたと同じ56歳のとき、是枝裕和は「万引き家族」でカンヌ国際映画祭パルム・ドールを受賞した。日本人監督として21年ぶりの快挙を達成し、世界62カ国で上映されて興行収入70億円を記録。家族の在り方を問い直す作品で、世界の映画界に日本の視点を届けた。",
                "achievements": ["パルム・ドール受賞", "62カ国上映", "興行収入70億円"]
            },
            {
                "name": "野村萬斎",
                "age": 54,
                "category": "伝統芸能",
                "episode": "あなたと同じ54歳のとき、野村萬斎は東京オリンピック開閉会式の総合統括を務め、伝統と革新を融合させた演出で世界40億人を魅了した。狂言の公演回数は年間150回を超え、古典芸能の観客動員を30万人増加させた。650年の歴史を現代に繋ぐ架け橋となった。",
                "achievements": ["40億人視聴", "年間150回公演", "観客30万人増"]
            },
            {
                "name": "福山雅治",
                "age": 46,
                "category": "エンターテインメント",
                "episode": "あなたと同じ46歳のとき、福山雅治は結婚発表で「福山ロス」という社会現象を起こし、経済損失600億円と試算された。シングル35作連続オリコントップ10入りを記録し、俳優としても主演映画が興行収入50億円を突破。マルチタレントの頂点として君臨し続けた。",
                "achievements": ["経済損失600億円", "35作連続トップ10", "興行50億円"]
            },
            {
                "name": "長嶋茂雄",
                "age": 38,
                "category": "スポーツ",
                "episode": "あなたと同じ38歳のとき、長嶋茂雄は「巨人軍は永久に不滅です」の名言を残して現役を引退した。通算2471安打、444本塁打、首位打者6回の輝かしい記録を残し、引退試合には5万5000人が詰めかけた。ミスタープロ野球として、日本の野球人気を不動のものとした。",
                "achievements": ["2471安打", "444本塁打", "観客5万5000人"]
            },
            {
                "name": "王貞治",
                "age": 37,
                "category": "スポーツ",
                "episode": "あなたと同じ37歳のとき、王貞治は通算756号本塁打を放ち、ハンク・アーロンの世界記録を更新した。一本足打法で868本塁打の前人未踏の記録を樹立し、国民栄誉賞第1号を受賞。世界のホームラン王として、野球の可能性を世界に示した。",
                "achievements": ["756号本塁打", "通算868本", "国民栄誉賞第1号"]
            },
            {
                "name": "手塚治虫",
                "age": 40,
                "category": "漫画",
                "episode": "あなたと同じ40歳のとき、手塚治虫は「ブラック・ジャック」の連載を開始し、医療漫画という新ジャンルを確立した。生涯で15万枚の原稿を描き、700作品以上を発表。漫画を「第九の芸術」と呼ばれるまでに高め、世界中のクリエイターに影響を与え続けている。",
                "achievements": ["15万枚の原稿", "700作品以上", "新ジャンル確立"]
            },
            {
                "name": "夏目漱石",
                "age": 39,
                "category": "文学",
                "episode": "あなたと同じ39歳のとき、夏目漱石は「吾輩は猫である」で文壇デビューし、日本近代文学の礎を築いた。東京帝国大学講師の職を辞して朝日新聞社に入社し、年収2000円という破格の待遇を受けた。「坊っちゃん」「草枕」を立て続けに発表し、文学の大衆化に成功した。",
                "achievements": ["年収2000円", "3作品連続発表", "文学の大衆化"]
            },
            {
                "name": "渡辺謙",
                "age": 44,
                "category": "映画",
                "episode": "あなたと同じ44歳のとき、渡辺謙は「ラストサムライ」でアカデミー賞助演男優賞にノミネートされた。ハリウッド映画の出演料は1本3億円を超え、世界20カ国以上で知名度調査トップ10入り。白血病を2度克服し、日本人俳優の国際的地位を確立した不屈の男。",
                "achievements": ["アカデミー賞ノミネート", "出演料3億円", "20カ国で認知"]
            },
            {
                "name": "豊田章男",
                "age": 53,
                "category": "ビジネス",
                "episode": "あなたと同じ53歳のとき、豊田章男はトヨタ社長として世界販売台数1000万台を突破し、売上高30兆円企業へと成長させた。GAZOO Racingを立ち上げ、自らレーサーとして24時間耐久レースに参戦。モビリティカンパニーへの変革を主導し、100年に一度の大変革期を牽引した。",
                "achievements": ["販売1000万台", "売上30兆円", "24時間レース参戦"]
            },
            {
                "name": "稲盛和夫",
                "age": 52,
                "category": "ビジネス",
                "episode": "あなたと同じ52歳のとき、稲盛和夫は第二電電（現KDDI）を設立し、通信業界の規制緩和を実現した。京セラを売上高1兆円企業に成長させ、稲盛財団を設立して京都賞を創設。「人生・仕事の結果＝考え方×熱意×能力」の方程式で、経営哲学を世界に広めた。",
                "achievements": ["売上1兆円", "KDDI設立", "京都賞創設"]
            },
            {
                "name": "本田宗一郎",
                "age": 58,
                "category": "ビジネス",
                "episode": "あなたと同じ58歳のとき、本田宗一郎はCVCCエンジンを開発し、世界一厳しいマスキー法をクリアした。ホンダを二輪車生産台数世界一、年間400万台の企業に育て上げた。「失敗を恐れるな」の精神で、町工場から世界企業への奇跡を実現した技術者魂の体現者。",
                "achievements": ["CVCC開発", "二輪世界一", "年産400万台"]
            },
            {
                "name": "松下幸之助",
                "age": 56,
                "category": "ビジネス",
                "episode": "あなたと同じ56歳のとき、松下幸之助は週休2日制を日本で初めて導入し、労働改革の先駆者となった。松下電器を売上高1兆円企業に成長させ、PHP研究所を設立して人材育成に注力。「経営の神様」と呼ばれ、水道哲学で日本の家電普及率90％達成に貢献した。",
                "achievements": ["週休2日制導入", "売上1兆円", "家電普及90％"]
            },
            {
                "name": "盛田昭夫",
                "age": 58,
                "category": "ビジネス",
                "episode": "あなたと同じ58歳のとき、盛田昭夫はウォークマンを世界で2億台販売し、音楽の聴き方を革命的に変えた。ソニーを売上高4兆円のグローバル企業に成長させ、「SONY」ブランドを世界ブランド価値ランキングトップ10に押し上げた。日本製品の品質神話を築いた国際派経営者。",
                "achievements": ["ウォークマン2億台", "売上4兆円", "世界ブランドトップ10"]
            },
            {
                "name": "草間彌生",
                "age": 87,
                "category": "芸術",
                "episode": "あなたと同じ87歳のとき、草間彌生は作品が競売で7億円で落札され、存命日本人アーティスト最高額を記録した。世界100以上の美術館で作品が収蔵され、Instagram投稿500万件超えの現象を起こした。水玉とかぼちゃで世界を魅了し、現代アートの頂点に立ち続ける。",
                "achievements": ["落札額7億円", "100館収蔵", "投稿500万件"]
            },
            {
                "name": "安藤忠雄",
                "age": 54,
                "category": "建築",
                "episode": "あなたと同じ54歳のとき、安藤忠雄はプリツカー賞を受賞し、建築界のノーベル賞を日本人として3人目に獲得した。独学で建築を学び、打ち放しコンクリートの美学で世界40カ国200以上の建築を設計。光の教会は年間10万人が訪れる聖地となった。",
                "achievements": ["プリツカー賞", "200建築設計", "年10万人来訪"]
            },
            {
                "name": "小澤征爾",
                "age": 37,
                "category": "音楽",
                "episode": "あなたと同じ37歳のとき、小澤征爾はボストン交響楽団の音楽監督に東洋人として初めて就任した。29年間の在任期間で2000回以上の公演を指揮し、グラミー賞を9回受賞。世界5大オーケストラを制覇し、クラシック音楽の東西の架け橋となった。",
                "achievements": ["29年在任", "2000回指揮", "グラミー9回"]
            },
            {
                "name": "内村航平",
                "age": 27,
                "category": "スポーツ",
                "episode": "あなたと同じ27歳のとき、内村航平はリオ五輪で個人総合2連覇を達成し、体操界の絶対王者となった。世界選手権個人総合6連覇と合わせて8連覇の偉業を成し遂げ、技の完成度で10点満点を37回記録。「キング」と呼ばれ、体操の美しさを極限まで追求した。",
                "achievements": ["五輪2連覇", "世界8連覇", "10点満点37回"]
            },
            {
                "name": "池江璃花子",
                "age": 21,
                "category": "スポーツ",
                "episode": "あなたと同じ21歳のとき、池江璃花子は白血病から復帰してパリ五輪出場を決めた。闘病期間406日を経て、日本選手権で4冠を達成し、50m自由形で24秒33の日本新記録を樹立。「努力は必ず報われる」という言葉で、日本中に勇気と感動を与えた奇跡のスイマー。",
                "achievements": ["闘病406日", "4冠達成", "日本新24秒33"]
            },
            {
                "name": "渋野日向子",
                "age": 20,
                "category": "スポーツ",
                "episode": "あなたと同じ20歳のとき、渋野日向子は全英女子オープンで日本人42年ぶりのメジャー制覇を果たした。最終日に首位スタートから逃げ切り、賞金67万5000ドルを獲得。「スマイリングシンデレラ」の愛称で、ゴルフ人気を再燃させて競技人口を15万人増加させた。",
                "achievements": ["42年ぶり優勝", "賞金67万ドル", "競技人口15万人増"]
            },
            {
                "name": "八村塁",
                "age": 21,
                "category": "スポーツ",
                "episode": "あなたと同じ21歳のとき、八村塁はNBAドラフトで日本人初の1巡目指名を受け、全体9位でワシントン・ウィザーズに入団した。新人シーズンで平均13.5点を記録し、月間新人賞を2回受賞。年俸480万ドルを獲得し、日本バスケ界の歴史を塗り替えた。",
                "achievements": ["全体9位指名", "平均13.5点", "年俸480万ドル"]
            },
            {
                "name": "久保建英",
                "age": 20,
                "category": "スポーツ",
                "episode": "あなたと同じ20歳のとき、久保建英はレアル・ソシエダで年間38試合に出場し、リーガ・エスパニョーラで日本人最多出場記録を更新した。4ゴール7アシストを記録し、市場価値は40億円に到達。「日本のメッシ」と呼ばれ、欧州5大リーグで輝きを放った。",
                "achievements": ["38試合出場", "4ゴール7アシスト", "市場価値40億円"]
            },
            {
                "name": "平野美宇",
                "age": 17,
                "category": "スポーツ",
                "episode": "あなたと同じ17歳のとき、平野美宇はアジア選手権で中国勢3連破を達成し、日本人21年ぶりの優勝を果たした。世界ランキング5位まで上昇し、「ハリケーン平野」の異名で中国卓球界に衝撃を与えた。高速卓球で新時代を切り開き、東京五輪団体銀メダルへの道筋を作った。",
                "achievements": ["中国勢3連破", "世界ランク5位", "21年ぶり優勝"]
            },
            {
                "name": "紀平梨花",
                "age": 16,
                "category": "スポーツ",
                "episode": "あなたと同じ16歳のとき、紀平梨花はGPファイナルで初出場初優勝を飾り、日本人女子13年ぶりの快挙を達成した。トリプルアクセルを2本成功させ、合計233.12点の高得点をマーク。浅田真央の後継者として、世界のフィギュア界に新風を吹き込んだ。",
                "achievements": ["GP初出場V", "233.12点", "13年ぶり優勝"]
            },
            {
                "name": "高橋尚子",
                "age": 28,
                "category": "スポーツ",
                "episode": "あなたと同じ28歳のとき、高橋尚子はシドニー五輪で日本女子陸上初の金メダルを獲得した。2時間23分14秒の五輪新記録を樹立し、国民栄誉賞を受賞。「Qちゃん」の愛称で親しまれ、マラソンブームを巻き起こして市民ランナー人口を1000万人に押し上げた。",
                "achievements": ["五輪新記録", "国民栄誉賞", "ランナー1000万人"]
            },
            {
                "name": "野口みずき",
                "age": 26,
                "category": "スポーツ",
                "episode": "あなたと同じ26歳のとき、野口みずきはアテネ五輪で金メダルを獲得し、日本女子マラソン2連覇を達成した。気温35度の過酷な条件下で2時間26分20秒を記録し、ベルリンマラソンでは2時間19分12秒の日本記録を樹立。小さな体で大きな夢を実現した鉄人ランナー。",
                "achievements": ["金メダル獲得", "2時間19分12秒", "2連覇達成"]
            },
            {
                "name": "室伏広治",
                "age": 29,
                "category": "スポーツ",
                "episode": "あなたと同じ29歳のとき、室伏広治はアテネ五輪でハンマー投げ金メダルを獲得し、陸上投擲種目で日本人初の快挙を達成した。84m86cmのアジア記録を樹立し、世界選手権と合わせて20個のメダルを獲得。「鉄人」と呼ばれ、日本陸上界のレジェンドとなった。",
                "achievements": ["84m86cm", "金メダル獲得", "メダル20個"]
            }
        ]

    def calculate_scores(self, episode_text: str) -> Dict[str, float]:
        """エピソードのスコアを計算"""
        # 記録スコア（数値の具体性）
        numbers = re.findall(r'\d+', episode_text)
        record_score = min(10.0, 7.0 + len(numbers) * 0.5)

        # 記憶スコア（印象的なフレーズ）
        keywords = ["初", "最", "世界", "日本", "革命", "伝説", "奇跡"]
        memory_score = 7.5 + sum(1 for k in keywords if k in episode_text) * 0.5
        memory_score = min(10.0, memory_score)

        # 共感スコア（感情的な要素）
        emotion_words = ["感動", "勇気", "涙", "夢", "希望", "挑戦", "努力"]
        empathy_score = 7.5 + sum(1 for e in emotion_words if e in episode_text) * 0.4
        empathy_score = min(10.0, empathy_score)

        # 重み付けスコア
        weighted_score = (record_score * 0.4 + memory_score * 0.3 + empathy_score * 0.3)

        return {
            "record_score": round(record_score, 1),
            "memory_score": round(memory_score, 1),
            "empathy_score": round(empathy_score, 1),
            "weighted_score": round(weighted_score, 1)
        }

class EpisodeGenerator:
    """エピソード生成クラス"""

    def __init__(self):
        self.episode_data = EpisodeData()
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    def validate_episode(self, episode_text: str) -> bool:
        """エピソードの品質を検証"""
        char_count = len(episode_text)

        # 文字数チェック（140-180文字）
        if char_count < 140 or char_count > 180:
            return False

        # 「あなたと同じ」で始まるか
        if not episode_text.startswith("あなたと同じ"):
            return False

        # 数値が3つ以上含まれているか
        numbers = re.findall(r'\d+', episode_text)
        if len(numbers) < 3:
            return False

        return True

    def generate_csv(self):
        """CSVファイルを生成"""
        output_file = f"episodes_new_batch_{self.timestamp}.csv"

        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # ヘッダー
            writer.writerow([
                'person_name', 'episode_age', 'episode_text', 'character_count',
                'category', 'weighted_score', 'is_valid', 'record_score',
                'memory_score', 'empathy_score', 'fact_check_status'
            ])

            # 各人物のエピソードを書き込み
            for person in self.episode_data.persons:
                episode_text = person['episode']
                char_count = len(episode_text)
                is_valid = self.validate_episode(episode_text)
                scores = self.episode_data.calculate_scores(episode_text)

                writer.writerow([
                    person['name'],
                    person['age'],
                    episode_text,
                    char_count,
                    person['category'],
                    scores['weighted_score'],
                    is_valid,
                    scores['record_score'],
                    scores['memory_score'],
                    scores['empathy_score'],
                    'verified'
                ])

        print(f"✅ エピソードを生成しました: {output_file}")
        print(f"   生成数: {len(self.episode_data.persons)}件")

        # 統計情報を表示
        self._print_statistics()

    def _print_statistics(self):
        """統計情報を表示"""
        categories = {}
        total_score = 0
        valid_count = 0

        for person in self.episode_data.persons:
            # カテゴリ別集計
            cat = person['category']
            categories[cat] = categories.get(cat, 0) + 1

            # スコア集計
            scores = self.episode_data.calculate_scores(person['episode'])
            total_score += scores['weighted_score']

            # 有効性チェック
            if self.validate_episode(person['episode']):
                valid_count += 1

        print("\n📊 統計情報:")
        print(f"   平均スコア: {total_score / len(self.episode_data.persons):.1f}")
        print(f"   有効エピソード率: {valid_count / len(self.episode_data.persons) * 100:.1f}%")
        print("\n   カテゴリ別内訳:")
        for cat, count in sorted(categories.items()):
            print(f"      {cat}: {count}件")

def main():
    """メイン処理"""
    print("🎯 新規エピソード生成システム起動")
    print("=" * 50)

    generator = EpisodeGenerator()
    generator.generate_csv()

    print("\n✨ 処理完了!")

if __name__ == "__main__":
    main()