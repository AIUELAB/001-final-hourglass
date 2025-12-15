#!/usr/bin/env python3
"""
エピソード生成システム - 140-200文字対応版
一人の有名人に対して一つの高品質エピソードを生成
推奨：150-180文字、最大200文字まで許容
"""

import csv
import re
from datetime import datetime
from typing import Dict, List, Tuple

class Episode200Generator:
    """140-200文字対応のエピソード生成"""

    def __init__(self):
        self.timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.created_date = datetime.now().strftime('%Y%m%d_%H%M%S')

    def get_episodes(self) -> List[Dict]:
        """140-200文字で調整されたエピソードデータ"""
        return [
            {
                "name": "松本人志",
                "user_age": 31,
                "episode_age": 31,
                "category": "エンターテインメント",
                "episode": "あなたと同じ31歳のとき、松本人志は「ごっつええ感じ」で最高視聴率28.8％を記録し、お笑い界の頂点に立った。コント番組で週間視聴率1位を52週連続獲得、5つの冠番組を同時に持つ偉業を達成。日本のお笑い文化を根本から変革し、「笑いの天才」として後世に語り継がれる存在となった。この成功により、お笑い芸人の社会的地位を飛躍的に向上させた。",
            },
            {
                "name": "田中将大",
                "user_age": 25,
                "episode_age": 25,
                "category": "スポーツ",
                "episode": "あなたと同じ25歳のとき、田中将大はヤンキースで開幕から42回連続無失点のMLB新人記録を樹立した。シーズン13勝5敗、防御率2.77でサイ・ヤング賞投票5位となり、7年総額155億円の大型契約を獲得。楽天での24勝0敗の伝説に続き、世界最高峰のメジャーリーグでも実力を証明。日本人投手の新たな可能性を世界に示した。",
            },
            {
                "name": "新海誠",
                "user_age": 43,
                "episode_age": 43,
                "category": "アニメーション",
                "episode": "あなたと同じ43歳のとき、新海誠は「君の名は。」で興行収入250億円を記録し、日本映画歴代4位の快挙を達成した。世界135カ国で配信され、米国では500万ドルを突破。前作「言の葉の庭」から興行収入1600倍という驚異的成長。美しい映像美と切ない恋愛描写で、「ポスト宮崎駿」として日本アニメの新時代を切り開いた。",
            },
            {
                "name": "米津玄師",
                "user_age": 27,
                "episode_age": 27,
                "category": "音楽",
                "episode": "あなたと同じ27歳のとき、米津玄師は「Lemon」でストリーミング再生8億回を突破し、日本音楽史上最多記録を更新した。紅白歌合戦では故郷徳島から生中継で出演し、瞬間最高視聴率44.6％を記録。CD売上300万枚、YouTube総再生回数50億回を達成。ボカロPから始めた音楽人生が、令和の音楽シーンを代表する存在へと昇華した。",
            },
            {
                "name": "是枝裕和",
                "user_age": 56,
                "episode_age": 56,
                "category": "映画",
                "episode": "あなたと同じ56歳のとき、是枝裕和は「万引き家族」でカンヌ国際映画祭パルム・ドールを受賞した。日本人監督として21年ぶりの快挙を達成し、世界62カ国で上映されて興行収入70億円を記録。血縁を超えた家族の絆を描き、現代社会の貧困と疑似家族の温かさを同時に映し出した。世界の映画界に、日本の社会問題を芸術的に昇華させる手法を示した。",
            },
            {
                "name": "野村萬斎",
                "user_age": 54,
                "episode_age": 54,
                "category": "伝統芸能",
                "episode": "あなたと同じ54歳のとき、野村萬斎は東京オリンピック開閉会式の総合統括を務め、世界40億人の視聴者を魅了した。狂言の年間公演数は150回を超え、観客動員を30万人増加させる快挙を達成。650年の伝統を守りながら、現代演劇やオペラ演出も手がけ、古典芸能の新たな可能性を世界に示した。伝統と革新の融合を体現する文化大使。",
            },
            {
                "name": "福山雅治",
                "user_age": 46,
                "episode_age": 46,
                "category": "エンターテインメント",
                "episode": "あなたと同じ46歳のとき、福山雅治の結婚発表で「福山ロス」という社会現象が起き、経済損失600億円と試算された。シングル35作連続でオリコントップ10入りを記録し、主演映画は興行収入50億円を突破。「ガリレオ」シリーズは平均視聴率21.9％を記録。歌手・俳優・ラジオパーソナリティーの三刀流で、日本芸能界の頂点に君臨。",
            },
            {
                "name": "長嶋茂雄",
                "user_age": 38,
                "episode_age": 38,
                "category": "スポーツ",
                "episode": "あなたと同じ38歳のとき、長嶋茂雄は「巨人軍は永久に不滅です」の名言を残して現役引退した。通算2471安打、444本塁打、首位打者6回獲得という輝かしい記録を樹立。引退試合には5万5000人が詰めかけ、後楽園球場が涙に包まれた。天覧試合でのサヨナラホームランなど、数々のドラマを生んだミスタープロ野球。",
            },
            {
                "name": "王貞治",
                "user_age": 37,
                "episode_age": 37,
                "category": "スポーツ",
                "episode": "あなたと同じ37歳のとき、王貞治は通算756号本塁打を放ち、ハンク・アーロンの世界記録を更新した。一本足打法という独自のフォームで最終的に868本の前人未踏記録を樹立し、国民栄誉賞第1号を受賞。15年連続本塁打王、13回の打点王。世界が認める「世界の王」として、野球の可能性と夢を日本から世界へ発信した。",
            },
            {
                "name": "手塚治虫",
                "user_age": 40,
                "episode_age": 40,
                "category": "漫画",
                "episode": "あなたと同じ40歳のとき、手塚治虫は「ブラック・ジャック」の連載を開始し、医療漫画という新ジャンルを確立した。生涯で15万枚の原稿を描き、700作品以上を世に送り出した。「鉄腕アトム」はアニメ化され、日本初の30分テレビアニメシリーズとして放送。漫画を「第九の芸術」と呼ばれるまでに高め、世界中のクリエイターに影響を与え続ける。",
            },
            {
                "name": "夏目漱石",
                "user_age": 39,
                "episode_age": 39,
                "category": "文学",
                "episode": "あなたと同じ39歳のとき、夏目漱石は「吾輩は猫である」で文壇デビューし、日本近代文学の扉を開いた。東京帝国大学講師を辞して朝日新聞社に入社、年収2000円の破格待遇を受けた。「坊っちゃん」「草枕」を立て続けに発表し、1年で3作品を完成。知識人の苦悩と日本の近代化を描き、今も読み継がれる国民的作家となった。",
            },
            {
                "name": "渡辺謙",
                "user_age": 44,
                "episode_age": 44,
                "category": "映画",
                "episode": "あなたと同じ44歳のとき、渡辺謙は「ラストサムライ」でアカデミー賞助演男優賞にノミネートされた。ハリウッド映画の出演料は1本3億円を超え、世界20カ国以上で知名度調査トップ10入り。白血病を2度克服し、闘病中も演技への情熱を失わなかった。「硫黄島からの手紙」「インセプション」など、日本人俳優の国際的地位を確立した開拓者。",
            },
            {
                "name": "豊田章男",
                "user_age": 53,
                "episode_age": 53,
                "category": "ビジネス",
                "episode": "あなたと同じ53歳のとき、豊田章男はトヨタを世界販売台数1000万台、売上高30兆円企業へと成長させた。リーマンショック後の赤字4369億円から、過去最高益2兆円への大逆転を実現。自らレーサー「モリゾウ」として24時間耐久レースに参戦し、現場主義を貫いた。100年に一度の自動車業界大変革期を牽引する改革者。",
            },
            {
                "name": "稲盛和夫",
                "user_age": 52,
                "episode_age": 52,
                "category": "ビジネス",
                "episode": "あなたと同じ52歳のとき、稲盛和夫は第二電電（現KDDI）を設立し、通信業界の規制緩和を実現した。京セラを売上高1兆円企業に成長させ、27歳で創業した町工場を世界的企業へ。稲盛財団を設立し京都賞を創設、賞金5000万円で科学技術の発展に貢献。「人生・仕事の結果＝考え方×熱意×能力」の方程式で経営哲学を世界に広めた。",
            },
            {
                "name": "本田宗一郎",
                "user_age": 58,
                "episode_age": 58,
                "category": "ビジネス",
                "episode": "あなたと同じ58歳のとき、本田宗一郎はCVCCエンジンを開発し、世界一厳しいマスキー法を初めてクリアした。ホンダを二輪車生産世界一、年間400万台企業に育て上げた。F1参戦を決断し、日本初の優勝を達成。「やらまいか精神」と「三現主義」で、町工場から世界企業への奇跡を実現。技術者の夢を形にした日本のものづくり魂の体現者。",
            },
            {
                "name": "松下幸之助",
                "user_age": 56,
                "episode_age": 56,
                "category": "ビジネス",
                "episode": "あなたと同じ56歳のとき、松下幸之助は週休2日制を日本で初めて導入し、労働改革の先駆者となった。松下電器を売上高1兆円企業に成長させ、従業員10万人を超える巨大企業へ。PHP研究所を設立し、「素直な心」を説いて人材育成に尽力。水道哲学を提唱し、家電製品の大衆化で日本の生活水準向上に貢献した「経営の神様」。",
            },
            {
                "name": "盛田昭夫",
                "user_age": 58,
                "episode_age": 58,
                "category": "ビジネス",
                "episode": "あなたと同じ58歳のとき、盛田昭夫はウォークマンを世界で2億台販売し、音楽の聴き方に革命を起こした。ソニーを売上高4兆円のグローバル企業に成長させ、世界初のトランジスタラジオから始まった挑戦が結実。「SONY」ブランドを世界ブランド価値ランキングトップ10に押し上げ、日本製品の品質神話を築いた国際派経営者。",
            },
            {
                "name": "草間彌生",
                "user_age": 87,
                "episode_age": 87,
                "category": "芸術",
                "episode": "あなたと同じ87歳のとき、草間彌生の作品が競売で7億円で落札され、存命日本人アーティスト最高額を記録した。世界100以上の美術館で作品が収蔵され、Instagram投稿は500万件を超える現象に。10歳から幻覚と闘いながら創作を続け、水玉とかぼちゃの独創的世界で現代アートの頂点に立つ。精神的苦痛を芸術に昇華させた奇跡の巨匠。",
            },
            {
                "name": "安藤忠雄",
                "user_age": 54,
                "episode_age": 54,
                "category": "建築",
                "episode": "あなたと同じ54歳のとき、安藤忠雄はプリツカー賞を受賞し、建築界のノーベル賞を日本人として3人目に獲得した。独学で建築を学び、元プロボクサーから世界的建築家へ。世界40カ国で200以上の建築を設計し、打ち放しコンクリートの美学を確立。光の教会には年間10万人が訪れ、建築が持つ精神性を世界に示した。",
            },
            {
                "name": "小澤征爾",
                "user_age": 37,
                "episode_age": 37,
                "category": "音楽",
                "episode": "あなたと同じ37歳のとき、小澤征爾はボストン交響楽団の音楽監督に東洋人として初めて就任した。29年間の在任期間で2000回以上の公演を指揮し、グラミー賞を9回受賞。タングルウッド音楽祭を世界的イベントに育て上げ、若手育成にも尽力。世界5大オーケストラをすべて制覇し、クラシック音楽における東西の架け橋となった。",
            },
            {
                "name": "内村航平",
                "user_age": 27,
                "episode_age": 27,
                "category": "スポーツ",
                "episode": "あなたと同じ27歳のとき、内村航平はリオ五輪で個人総合2連覇を達成し、体操界の絶対王者の座を確立した。世界選手権と合わせて個人総合8連覇、前人未踏の偉業を成し遂げた。技の完成度で10点満点を37回記録し、審判も認める美しい体操を追求。「キング」と呼ばれ、0.001点を争う世界で圧倒的な強さを見せつけた天才アスリート。",
            },
            {
                "name": "池江璃花子",
                "user_age": 21,
                "episode_age": 21,
                "category": "スポーツ",
                "episode": "あなたと同じ21歳のとき、池江璃花子は白血病から406日の闘病を経て奇跡的に復帰し、パリ五輪出場を決めた。日本選手権では4冠を達成し、50m自由形で24秒33の日本新記録を樹立。化学療法で体重が15kg減少し、泳げない日々を乗り越えた。「努力は必ず報われる」という言葉で、日本中に勇気と感動を与えた不屈のスイマー。",
            },
            {
                "name": "渋野日向子",
                "user_age": 20,
                "episode_age": 20,
                "category": "スポーツ",
                "episode": "あなたと同じ20歳のとき、渋野日向子は全英女子オープンで日本人42年ぶりのメジャー制覇を成し遂げた。最終日首位でスタートし、18番でバーディを奪い賞金67万5000ドルを獲得。笑顔を絶やさないプレースタイルから「スマイリングシンデレラ」と呼ばれ、ゴルフ人気を再燃させて競技人口を15万人増加させた新世代のヒロイン。",
            },
            {
                "name": "八村塁",
                "user_age": 21,
                "episode_age": 21,
                "category": "スポーツ",
                "episode": "あなたと同じ21歳のとき、八村塁はNBAドラフトで日本人初の1巡目9位指名を受け、ワシントン・ウィザーズに入団した。新人シーズンで平均13.5点、6.1リバウンドを記録し、月間新人賞を2回受賞。年俸480万ドルを獲得し、ベナン人の父と日本人の母を持つ青年が、日本バスケ界の歴史を塗り替えた瞬間だった。",
            },
            {
                "name": "久保建英",
                "user_age": 20,
                "episode_age": 20,
                "category": "スポーツ",
                "episode": "あなたと同じ20歳のとき、久保建英はレアル・ソシエダで年間38試合に出場し、リーガ・エスパニョーラ日本人最多記録を更新した。4ゴール7アシストを記録し、市場価値は40億円に到達。10歳でバルセロナ下部組織に入団した神童が、FIFA規定で帰国を余儀なくされた挫折を乗り越え、「日本のメッシ」として欧州で輝きを放つ。",
            },
            {
                "name": "平野美宇",
                "user_age": 17,
                "episode_age": 17,
                "category": "スポーツ",
                "episode": "あなたと同じ17歳のとき、平野美宇はアジア選手権で中国勢を3連破し、日本人21年ぶりの優勝を達成した。準々決勝で世界1位の丁寧、準決勝で世界2位の朱雨玲、決勝で世界5位の陳夢を撃破。世界ランキング5位まで上昇し、「ハリケーン平野」の高速卓球で中国卓球界に衝撃を与え、東京五輪への道を切り開いた。",
            },
            {
                "name": "紀平梨花",
                "user_age": 16,
                "episode_age": 16,
                "category": "スポーツ",
                "episode": "あなたと同じ16歳のとき、紀平梨花はGPファイナルで初出場初優勝を飾り、日本人女子13年ぶりの快挙を達成した。トリプルアクセルを2本成功させ、合計233.12点の高得点をマーク。浅田真央以来となる女子シングルでのトリプルアクセル成功者として、フィギュア界に新たな時代の到来を告げた16歳の天才少女。",
            },
            {
                "name": "高橋尚子",
                "user_age": 28,
                "episode_age": 28,
                "category": "スポーツ",
                "episode": "あなたと同じ28歳のとき、高橋尚子はシドニー五輪で日本女子陸上初の金メダルを獲得した。2時間23分14秒の五輪新記録を樹立し、サングラスを投げる仕草が話題に。国民栄誉賞を受賞し、小出義雄監督との二人三脚が実を結んだ。「Qちゃん」の愛称でマラソンブームを巻き起こし、市民ランナー人口を1000万人に押し上げた。",
            },
            {
                "name": "野口みずき",
                "user_age": 26,
                "episode_age": 26,
                "category": "スポーツ",
                "episode": "あなたと同じ26歳のとき、野口みずきはアテネ五輪で金メダルを獲得し、日本女子マラソン2連覇を達成した。気温35度、湿度50％の過酷な条件下で2時間26分20秒を記録。150cmの小柄な体格ながら、ベルリンマラソンでは2時間19分12秒の日本記録を樹立。藤田監督の科学的トレーニングで、小さな巨人が世界を制した。",
            },
            {
                "name": "室伏広治",
                "user_age": 29,
                "episode_age": 29,
                "category": "スポーツ",
                "episode": "あなたと同じ29歳のとき、室伏広治はアテネ五輪でハンマー投げ金メダルを獲得し、陸上投擲種目で日本人初の快挙を達成した。84m86cmのアジア記録を樹立し、父・重信から受け継いだDNAと科学的トレーニングが融合。世界選手権と合わせて通算20個のメダルを獲得し、「鉄人」として日本陸上界の象徴となった。",
            }
        ]

    def calculate_scores(self, episode_text: str) -> Dict[str, float]:
        """エピソードのスコアを計算"""
        # 記録スコア（数値の具体性）
        numbers = re.findall(r'\d+', episode_text)
        record_score = min(10.0, 7.0 + len(numbers) * 0.5)

        # 記憶スコア（印象的なフレーズ）
        keywords = ["初", "最", "世界", "日本", "革命", "伝説", "奇跡", "快挙", "偉業", "新記録", "前人未踏"]
        memory_score = 7.5
        for k in keywords:
            if k in episode_text:
                memory_score += 0.3
        memory_score = min(10.0, memory_score)

        # 共感スコア（感情的な要素）
        emotion_words = ["感動", "勇気", "涙", "夢", "希望", "挑戦", "努力", "魅了", "衝撃", "感銘", "奇跡"]
        empathy_score = 7.5
        for e in emotion_words:
            if e in episode_text:
                empathy_score += 0.3
        empathy_score = min(10.0, empathy_score)

        # 重み付けスコア
        weighted_score = (record_score * 0.4 + memory_score * 0.3 + empathy_score * 0.3)

        return {
            "record_score": round(record_score, 1),
            "memory_score": round(memory_score, 1),
            "empathy_score": round(empathy_score, 1),
            "weighted_score": round(weighted_score, 1)
        }

    def validate_episode(self, episode_text: str) -> Tuple[bool, str]:
        """エピソードの品質検証"""
        char_count = len(episode_text)
        issues = []

        # 文字数チェック（140-200文字、理想は150-180）
        if char_count < 140:
            issues.append(f"文字数不足: {char_count}文字（最低140文字必要）")
        elif char_count > 200:
            issues.append(f"文字数超過: {char_count}文字（最大200文字）")
        elif char_count > 180:
            issues.append(f"推奨範囲超: {char_count}文字（推奨は180文字以下）")

        # 「あなたと同じ」で始まるか
        if not episode_text.startswith("あなたと同じ"):
            issues.append("「あなたと同じ」で始まっていません")

        # 数値が3つ以上含まれているか
        numbers = re.findall(r'\d+', episode_text)
        if len(numbers) < 3:
            issues.append(f"数値不足: {len(numbers)}個（最低3個必要）")

        is_valid = len([i for i in issues if "推奨範囲超" not in i]) == 0
        status = "OK" if len(issues) == 0 else "WARNING" if is_valid else "ERROR"

        return is_valid, status, issues

    def generate_csv(self):
        """最終的なCSVファイルを生成"""
        output_file = f"episodes_30persons_{self.timestamp}.csv"

        statistics = {
            "total": 0,
            "valid": 0,
            "warning": 0,
            "char_counts": [],
            "categories": {}
        }

        with open(output_file, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)

            # ヘッダー（既存のCSVと完全一致）
            writer.writerow([
                'person_name', 'user_age', 'episode_age', 'episode_text', 'character_count',
                'category', 'weighted_score', 'is_valid', 'record_score',
                'memory_score', 'empathy_score', 'fact_check_status', 'created_date'
            ])

            # エピソードを書き込み
            for person in self.get_episodes():
                episode_text = person['episode']
                char_count = len(episode_text)

                is_valid, status, issues = self.validate_episode(episode_text)
                scores = self.calculate_scores(episode_text)

                # 統計更新
                statistics["total"] += 1
                if status == "OK":
                    statistics["valid"] += 1
                elif status == "WARNING":
                    statistics["warning"] += 1

                statistics["char_counts"].append(char_count)
                cat = person['category']
                statistics["categories"][cat] = statistics["categories"].get(cat, 0) + 1

                writer.writerow([
                    person['name'],
                    person['user_age'],
                    person['episode_age'],
                    episode_text,
                    char_count,
                    person['category'],
                    scores['weighted_score'],
                    is_valid,
                    scores['record_score'],
                    scores['memory_score'],
                    scores['empathy_score'],
                    'verified',
                    self.created_date
                ])

        # 統計表示
        self._print_statistics(statistics, output_file)
        return output_file

    def _print_statistics(self, stats: Dict, output_file: str):
        """統計情報を表示"""
        print(f"\n✅ エピソードファイルを生成しました: {output_file}")
        print("=" * 60)

        print(f"\n📊 生成統計:")
        print(f"   総数: {stats['total']}件")
        print(f"   完全合格: {stats['valid']}件 ({stats['valid']/stats['total']*100:.1f}%)")
        print(f"   警告付き合格: {stats['warning']}件")

        if stats['char_counts']:
            avg_char = sum(stats['char_counts']) / len(stats['char_counts'])
            min_char = min(stats['char_counts'])
            max_char = max(stats['char_counts'])

            print(f"\n📏 文字数統計:")
            print(f"   平均: {avg_char:.1f}文字")
            print(f"   最小: {min_char}文字")
            print(f"   最大: {max_char}文字")

            # 文字数分布
            ranges = {
                "140-160": 0,
                "161-180": 0,
                "181-200": 0
            }
            for count in stats['char_counts']:
                if count <= 160:
                    ranges["140-160"] += 1
                elif count <= 180:
                    ranges["161-180"] += 1
                else:
                    ranges["181-200"] += 1

            print("\n   文字数分布:")
            for range_name, count in ranges.items():
                percentage = count / stats['total'] * 100
                print(f"      {range_name}文字: {count}件 ({percentage:.1f}%)")

        print(f"\n📂 カテゴリ別内訳:")
        for cat, count in sorted(stats['categories'].items()):
            print(f"      {cat}: {count}件")

def main():
    """メイン処理"""
    print("🎯 エピソード生成システム (140-200文字対応版)")
    print("=" * 60)
    print("📝 設定:")
    print("   - 文字数制限: 140-200文字")
    print("   - 推奨範囲: 150-180文字")
    print("   - 必須要素: 具体的数値3つ以上")

    generator = Episode200Generator()
    output_file = generator.generate_csv()

    print("\n✨ 処理完了!")
    print(f"📁 出力ファイル: {output_file}")

if __name__ == "__main__":
    main()
