#!/usr/bin/env python3
"""
データベースに必須追加すべき重要人物リスト
日本人ユーザーにとって有益なエピソードを持つ人物を体系的に定義
"""

from typing import Dict, List, Tuple
from datetime import datetime

class MustAddPersons:
    """必須追加人物リスト管理クラス"""
    
    def __init__(self):
        """初期化"""
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.must_add_list = []
        self._initialize_lists()
    
    def _initialize_lists(self):
        """必須追加人物リストの初期化"""
        
        # 国民栄誉賞受賞者（不足分）
        self.national_honor_recipients = [
            # 音楽・芸能
            ('美空ひばり', '歌手', '昭和の歌姫、国民栄誉賞第7号', 9.0),
            ('藤山一郎', '歌手', '国民栄誉賞第12号、戦後歌謡界の巨匠', 8.0),
            ('古賀政男', '作曲家', '国民栄誉賞第2号、日本歌謡界の父', 8.0),
            ('服部良一', '作曲家', '国民栄誉賞第11号、戦後音楽の礎', 8.0),
            
            # 俳優
            ('長谷川一夫', '俳優', '国民栄誉賞第3号、日本映画界の至宝', 8.0),
            ('渥美清', '俳優', '国民栄誉賞第13号、寅さん', 8.5),
            ('森繁久彌', '俳優', '国民栄誉賞第21号、昭和の名優', 8.0),
            ('森光子', '女優', '国民栄誉賞第20号、放浪記の主演', 8.0),
            
            # スポーツ
            ('千代の富士貢', '大相撲力士', '国民栄誉賞第8号、昭和の大横綱', 8.5),
            
            # 特別枠（チーム）
            ('澤穂希', 'サッカー選手', 'なでしこジャパン主将、W杯優勝', 8.0),
            ('宮間あや', 'サッカー選手', 'なでしこジャパン司令塔', 7.5),
            ('川澄奈穂美', 'サッカー選手', 'なでしこジャパンエース', 7.5),
        ]
        
        # 歴代総理大臣（不足分）
        self.prime_ministers = [
            ('菅義偉', '政治家', '第99代内閣総理大臣、令和初期', 7.5),
            ('野田佳彦', '政治家', '第95代内閣総理大臣、民主党政権', 7.0),
            ('福田康夫', '政治家', '第91代内閣総理大臣', 7.0),
            ('麻生太郎', '政治家', '第92代内閣総理大臣、現財務大臣', 7.5),
            ('橋本龍太郎', '政治家', '第82・83代内閣総理大臣、行政改革', 7.0),
            ('海部俊樹', '政治家', '第76・77代内閣総理大臣', 6.5),
            ('竹下登', '政治家', '第74代内閣総理大臣、消費税導入', 7.0),
            ('大平正芳', '政治家', '第68・69代内閣総理大臣', 6.5),
            ('福田赳夫', '政治家', '第67代内閣総理大臣', 6.5),
            ('三木武夫', '政治家', '第66代内閣総理大臣、クリーン三木', 6.5),
        ]
        
        # 漫画家（世界的影響力）
        self.manga_artists = [
            ('尾田栄一郎', '漫画家', 'ONE PIECE作者、世界最高発行部数', 8.0),
            ('岸本斉史', '漫画家', 'NARUTO作者、世界的忍者ブーム', 7.5),
            ('冨樫義博', '漫画家', 'HUNTER×HUNTER、幽遊白書作者', 7.5),
            ('荒木飛呂彦', '漫画家', 'ジョジョの奇妙な冒険作者', 7.5),
            ('青山剛昌', '漫画家', '名探偵コナン作者、国民的作品', 7.5),
            ('高橋留美子', '漫画家', 'うる星やつら、らんま1/2作者', 7.5),
            ('井上雄彦', '漫画家', 'SLAM DUNK、バガボンド作者', 7.5),
            ('諫山創', '漫画家', '進撃の巨人作者、世界的ヒット', 7.0),
            ('吾峠呼世晴', '漫画家', '鬼滅の刃作者、社会現象', 7.5),
            ('堀越耕平', '漫画家', '僕のヒーローアカデミア作者', 6.5),
        ]
        
        # 社会貢献者・活動家
        self.social_contributors = [
            ('緒方貞子', '国際公務員', '元国連難民高等弁務官、人道支援', 8.0),
            ('中村哲', '医師', 'ペシャワール会、アフガニスタン支援', 7.5),
            ('日野原重明', '医師', '聖路加国際病院、生涯現役', 7.0),
            ('瀬戸内寂聴', '作家・僧侶', '天台宗僧侶、作家', 7.0),
            ('黒柳徹子', 'タレント・活動家', 'ユニセフ親善大使、徹子の部屋', 8.0),
            ('坂田明', 'ミュージシャン・活動家', '環境保護活動家', 6.0),
            ('田中正造', '政治家・活動家', '足尾銅山鉱毒事件', 7.0),
            ('杉原千畝', '外交官', '命のビザ、ユダヤ人救済', 8.0),
        ]
        
        # 現代のイノベーター・起業家
        self.modern_innovators = [
            ('藤井聡太', '将棋棋士', '最年少八冠、将棋界の革命児', 8.0),
            ('前澤友作', '実業家', 'ZOZO創業者、宇宙旅行者', 7.0),
            ('山田進太郎', '実業家', 'メルカリ創業者、シェアエコノミー', 6.5),
            ('南場智子', '実業家', 'DeNA創業者、女性起業家の先駆者', 6.5),
            ('笠原健治', '実業家', 'ミクシィ創業者、SNSの先駆者', 6.0),
            ('堀江貴文', '実業家', 'ライブドア創業者、ホリエモン', 7.0),
            ('西村博之', '実業家', '2ちゃんねる創設者、ひろゆき', 7.0),
            ('川上量生', '実業家', 'ドワンゴ創業者、ニコニコ動画', 6.5),
            ('岩田聡', '経営者', '任天堂元社長、ゲーム業界の巨人', 7.5),
            ('宮本茂', 'ゲームクリエイター', 'マリオ・ゼルダの生みの親', 8.0),
        ]
        
        # お笑い・エンタメのレジェンド（不足分）
        self.entertainment_legends = [
            ('横山やすし', '漫才師', 'やすしきよし、伝説の漫才師', 7.5),
            ('西川きよし', '漫才師・政治家', 'やすしきよし、参議院議員', 7.0),
            ('島田紳助', 'タレント', '司会者、プロデューサー', 7.0),
            ('上岡龍太郎', 'タレント', '関西の重鎮、評論家', 6.5),
            ('山口百恵', '歌手・女優', '昭和のトップアイドル、引退伝説', 8.0),
            ('沢田研二', '歌手', 'ジュリー、昭和のスーパースター', 7.0),
            ('矢沢永吉', '歌手', '日本ロックの先駆者、永ちゃん', 7.5),
            ('桑田佳祐', '歌手', 'サザンオールスターズ、国民的バンド', 8.0),
            ('忌野清志郎', '歌手', 'RCサクセション、日本ロックの神様', 7.0),
            ('美輪明宏', '歌手・俳優', '芸術家、文化人', 7.0),
        ]
        
        # スポーツ界の新世代
        self.new_sports_stars = [
            ('久保建英', 'サッカー選手', 'レアル・ソシエダ、日本の至宝', 7.0),
            ('三笘薫', 'サッカー選手', 'ブライトン、ドリブラー', 6.5),
            ('堂安律', 'サッカー選手', 'フライブルク、攻撃的MF', 6.5),
            ('冨安健洋', 'サッカー選手', 'アーセナル、守備の要', 6.5),
            ('南野拓実', 'サッカー選手', 'モナコ、日本代表FW', 6.0),
            ('鎌田大地', 'サッカー選手', 'ラツィオ、攻撃的MF', 6.0),
            ('板倉滉', 'サッカー選手', 'ボルシアMG、センターバック', 6.0),
            ('佐々木朗希', '野球選手', 'ロッテ、完全試合達成投手', 7.0),
            ('村上宗隆', '野球選手', 'ヤクルト、三冠王', 7.0),
            ('山本由伸', '野球選手', 'ドジャース、エース投手', 7.0),
        ]
        
        # 文化人・学者（不足分）
        self.cultural_figures = [
            ('司馬遼太郎', '作家', '歴史小説の巨匠、竜馬がゆく', 8.0),
            ('遠藤周作', '作家', '沈黙、海と毒薬の作者', 7.0),
            ('井上靖', '作家', '敦煌、天平の甍の作者', 7.0),
            ('水木しげる', '漫画家', 'ゲゲゲの鬼太郎作者、妖怪研究', 7.5),
            ('石ノ森章太郎', '漫画家', '仮面ライダー、サイボーグ009', 7.5),
            ('永井豪', '漫画家', 'デビルマン、マジンガーZ作者', 7.0),
            ('松本零士', '漫画家', '銀河鉄道999、宇宙戦艦ヤマト', 7.5),
            ('梅原猛', '哲学者', '日本文化研究、仏教哲学', 6.5),
            ('河合隼雄', '心理学者', '臨床心理学、ユング派分析', 6.5),
            ('養老孟司', '解剖学者', 'バカの壁著者、脳科学', 7.0),
        ]
        
        # 世界的日本人（追加分）
        self.global_japanese = [
            ('小澤征爾', '指揮者', '世界的マエストロ、ボストン響', 8.0),
            ('内田光子', 'ピアニスト', '世界的ピアニスト、モーツァルト', 7.0),
            ('五嶋みどり', 'バイオリニスト', '世界的バイオリニスト', 7.0),
            ('辻井伸行', 'ピアニスト', '盲目のピアニスト、国際コンクール優勝', 7.0),
            ('是枝裕和', '映画監督', 'カンヌ映画祭パルムドール', 7.5),
            ('北野武', '映画監督・タレント', '世界的映画監督、ビートたけし', 8.5),
            ('新海誠', 'アニメ監督', '君の名は。天気の子監督', 7.5),
            ('細田守', 'アニメ監督', 'サマーウォーズ、時をかける少女', 7.0),
            ('庵野秀明', 'アニメ監督', 'エヴァンゲリオン監督', 7.5),
            ('押井守', 'アニメ監督', '攻殻機動隊、パトレイバー監督', 7.0),
        ]
    
    def get_all_persons(self) -> List[Tuple[str, str, str, float]]:
        """全必須追加人物リストを取得"""
        all_persons = []
        
        # 各カテゴリから人物を収集
        all_persons.extend(self.national_honor_recipients)
        all_persons.extend(self.prime_ministers)
        all_persons.extend(self.manga_artists)
        all_persons.extend(self.social_contributors)
        all_persons.extend(self.modern_innovators)
        all_persons.extend(self.entertainment_legends)
        all_persons.extend(self.new_sports_stars)
        all_persons.extend(self.cultural_figures)
        all_persons.extend(self.global_japanese)
        
        return all_persons
    
    def get_category_stats(self) -> Dict[str, int]:
        """カテゴリ別統計を取得"""
        return {
            '国民栄誉賞受賞者': len(self.national_honor_recipients),
            '歴代総理大臣': len(self.prime_ministers),
            '漫画家': len(self.manga_artists),
            '社会貢献者': len(self.social_contributors),
            '起業家・イノベーター': len(self.modern_innovators),
            'エンタメレジェンド': len(self.entertainment_legends),
            'スポーツ新世代': len(self.new_sports_stars),
            '文化人・学者': len(self.cultural_figures),
            '世界的日本人': len(self.global_japanese),
        }
    
    def generate_person_id(self, index: int, base: int = 100000) -> str:
        """人物IDを生成"""
        return f"P{base + index:06d}"
    
    def export_to_csv(self, filename: str = None):
        """CSVファイルとして出力"""
        import csv
        
        if not filename:
            filename = f"must_add_persons_{self.timestamp}.csv"
        
        all_persons = self.get_all_persons()
        
        with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['person_id', 'name', 'occupation', 'description', 'min_score', 'category'])
            
            for idx, (name, occupation, description, min_score) in enumerate(all_persons):
                person_id = self.generate_person_id(idx)
                
                # カテゴリを判定
                if name in [p[0] for p in self.national_honor_recipients]:
                    category = '国民栄誉賞'
                elif name in [p[0] for p in self.prime_ministers]:
                    category = '歴代総理'
                elif name in [p[0] for p in self.manga_artists]:
                    category = '漫画家'
                elif name in [p[0] for p in self.social_contributors]:
                    category = '社会貢献者'
                elif name in [p[0] for p in self.modern_innovators]:
                    category = '起業家'
                elif name in [p[0] for p in self.entertainment_legends]:
                    category = 'エンタメ'
                elif name in [p[0] for p in self.new_sports_stars]:
                    category = 'スポーツ'
                elif name in [p[0] for p in self.cultural_figures]:
                    category = '文化人'
                elif name in [p[0] for p in self.global_japanese]:
                    category = '世界的日本人'
                else:
                    category = 'その他'
                
                writer.writerow([person_id, name, occupation, description, min_score, category])
        
        print(f"✅ 必須追加人物リスト出力完了: {filename}")
        return filename
    
    def show_summary(self):
        """サマリーを表示"""
        all_persons = self.get_all_persons()
        stats = self.get_category_stats()
        
        print("=" * 60)
        print("📊 必須追加人物リスト サマリー")
        print("=" * 60)
        print(f"総人数: {len(all_persons)}名")
        print("\nカテゴリ別内訳:")
        for category, count in stats.items():
            print(f"  {category}: {count}名")
        
        print("\n主要人物（スコア8.0以上）:")
        high_score_persons = [p for p in all_persons if p[3] >= 8.0]
        for name, occupation, _, score in high_score_persons[:10]:
            print(f"  - {name} ({occupation}): {score}")
        
        print(f"\n高スコア人物数: {len(high_score_persons)}名")

def main():
    """メイン処理"""
    print("🎯 必須追加人物リスト作成開始")
    
    # リスト作成
    must_add = MustAddPersons()
    
    # サマリー表示
    must_add.show_summary()
    
    # CSV出力
    output_file = must_add.export_to_csv()
    
    print(f"\n✅ 処理完了")
    print(f"出力ファイル: {output_file}")

if __name__ == "__main__":
    main()