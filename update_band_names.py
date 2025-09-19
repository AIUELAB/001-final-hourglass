from src.secure_config import config
#!/usr/bin/env python3
"""
バンドメンバーのperson_name_displayにバンド名を括弧付きで追記
"""

import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import re

SPREADSHEET_ID = "1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps"

# 主要なバンド/グループとそのメンバー
BAND_MEMBERS = {
    "BTS": [
        "RM", "Jin", "SUGA", "J-Hope", "Jimin", "V", "Jungkook",
        "金南俊", "金碩珍", "閔玧其", "鄭號錫", "朴智旻", "金泰亨", "田柾國"
    ],
    "YOASOBI": ["Ayase", "ikura", "幾田りら"],
    "Official髭男dism": ["藤原聡", "小笹大輔", "楢崎誠", "松浦匡希"],
    "King Gnu": ["常田大希", "勢喜遊", "新井和輝", "井口理"],
    "RADWIMPS": ["野田洋次郎", "桑原彰", "武田祐介"],
    "ONE OK ROCK": ["Taka", "Toru", "Ryota", "Tomoya", "森内貴寛", "山下亨", "小浜良太", "神吉智也"],
    "SEKAI NO OWARI": ["Fukase", "Nakajin", "Saori", "DJ LOVE", "深瀬慧", "中島真一", "藤崎彩織"],
    "back number": ["清水依与吏", "小島和也", "栗原寿"],
    "Mrs. GREEN APPLE": ["大森元貴", "若井滉斗", "藤澤涼架"],
    "サカナクション": ["山口一郎", "岩寺基晴", "草刈愛美", "岡崎英美", "江島啓一"],
    "BUMP OF CHICKEN": ["藤原基央", "増川弘明", "直井由文", "升秀夫"],
    "Mr.Children": ["桜井和寿", "田原健一", "中川敬輔", "鈴木英哉"],
    "B'z": ["稲葉浩志", "松本孝弘"],
    "GLAY": ["TERU", "TAKURO", "HISASHI", "JIRO"],
    "L'Arc~en~Ciel": ["hyde", "tetsuya", "ken", "yukihiro"],
    "X JAPAN": ["YOSHIKI", "Toshl", "hide", "PATA", "HEATH"],
    "The Beatles": ["John Lennon", "Paul McCartney", "George Harrison", "Ringo Starr"],
    "Queen": ["Freddie Mercury", "Brian May", "Roger Taylor", "John Deacon"],
    "Led Zeppelin": ["Robert Plant", "Jimmy Page", "John Paul Jones", "John Bonham"],
    "The Rolling Stones": ["Mick Jagger", "Keith Richards", "Charlie Watts", "Ronnie Wood"],
    "Metallica": ["James Hetfield", "Lars Ulrich", "Kirk Hammett", "Robert Trujillo"],
    "Nirvana": ["Kurt Cobain", "Krist Novoselic", "Dave Grohl"],
    "Oasis": ["Liam Gallagher", "Noel Gallagher"],
    "Coldplay": ["Chris Martin", "Jonny Buckland", "Guy Berryman", "Will Champion"],
    "Maroon 5": ["Adam Levine", "James Valentine", "Jesse Carmichael", "Mickey Madden", "Matt Flynn"],
    "BLACKPINK": ["Jisoo", "Jennie", "Rosé", "Lisa", "ジス", "ジェニー", "ロゼ", "リサ"],
    "TWICE": ["Nayeon", "Jeongyeon", "Momo", "Sana", "Jihyo", "Mina", "Dahyun", "Chaeyoung", "Tzuyu"],
    "Stray Kids": ["Bang Chan", "Lee Know", "Changbin", "Hyunjin", "Han", "Felix", "Seungmin", "I.N"],
    "ENHYPEN": ["Jungwon", "Heeseung", "Jay", "Jake", "Sunghoon", "Sunoo", "Ni-ki"],
    "乃木坂46": ["秋元真夏", "生田絵梨花", "齋藤飛鳥", "白石麻衣", "西野七瀬", "橋本奈々未"],
    "櫻坂46": ["菅井友香", "土生瑞穂", "渡邉理佐"],
    "日向坂46": ["佐々木久美", "金村美玖", "河田陽菜"],
    "AKB48": ["前田敦子", "大島優子", "渡辺麻友", "指原莉乃", "柏木由紀"],
    "嵐": ["相葉雅紀", "松本潤", "二宮和也", "大野智", "櫻井翔"],
    "関ジャニ∞": ["横山裕", "村上信五", "丸山隆平", "安田章大", "大倉忠義"],
    "Hey! Say! JUMP": ["山田涼介", "中島裕翔", "知念侑李", "有岡大貴", "高木雄也"],
    "King & Prince": ["平野紫耀", "永瀬廉", "髙橋海人", "岸優太", "神宮寺勇太"],
    "Snow Man": ["深澤辰哉", "佐久間大介", "渡辺翔太", "宮舘涼太", "岩本照", "阿部亮平", "向井康二", "目黒蓮", "ラウール"],
    "SixTONES": ["ジェシー", "京本大我", "松村北斗", "髙地優吾", "森本慎太郎", "田中樹"],
    "EXILE": ["HIRO", "ATSUSHI", "TAKAHIRO", "AKIRA", "MAKIDAI"],
    "三代目 J Soul Brothers": ["今市隆二", "登坂広臣", "NAOTO", "小林直己", "ELLY", "山下健二郎", "岩田剛典"],
    "GENERATIONS": ["白濱亜嵐", "片寄涼太", "数原龍友", "小森隼", "佐野玲於", "関口メンディー", "中務裕太"],
    "THE RAMPAGE": ["川村壱馬", "吉野北人", "LIKIYA", "陣", "RIKU"],
    "DREAMS COME TRUE": ["吉田美和", "中村正人"],
    "サザンオールスターズ": ["桑田佳祐", "原由子", "関口和之", "松田弘", "野沢秀行"],
    "ゆず": ["北川悠仁", "岩沢厚治"],
    "コブクロ": ["黒田俊介", "小渕健太郎"],
    "いきものがかり": ["水野良樹", "山下穂尊", "吉岡聖恵"],
    "GReeeeN": ["HIDE", "navi", "92", "SOH"],
    "ORANGE RANGE": ["HIROKI", "NAOTO", "YAMATO", "YOH", "RYO"],
    "flumpool": ["山村隆太", "阪井一生", "尼川元気", "小倉誠司"],
    "UVERworld": ["TAKUYA∞", "克哉", "信人", "彰", "誠果", "真太郎"],
    "MAN WITH A MISSION": ["Tokyo Tanaka", "Jean-Ken Johnny", "Kamikaze Boy", "DJ Santa Monica", "Spear Rib"],
    "AAA": ["西島隆弘", "宇野実彩子", "浦田直也", "日高光啓", "與真司郎", "末吉秀太"],
    "Da-iCE": ["花村想太", "工藤大輝", "岩岡徹", "大野雄大", "和田颯"],
    "Perfume": ["あ～ちゃん", "かしゆか", "のっち", "西脇綾香", "樫野有香", "大本彩乃"],
    "BABYMETAL": ["SU-METAL", "MOAMETAL", "中元すず香", "菊地最愛"],
    "モーニング娘。": ["譜久村聖", "生田衣梨奈", "石田亜佑美", "小田さくら", "牧野真莉愛"],
    "Juice=Juice": ["金澤朋子", "高木紗友希", "宮本佳林", "植村あかり", "段原瑠々"],
    "アンジュルム": ["竹内朱莉", "川村文乃", "上國料萌衣"],
    "Little Glee Monster": ["芹奈", "アサヒ", "MAYU", "かれん", "ミサキ"],
    "E-girls": ["藤井夏恋", "楓", "佐藤晴美", "鷲尾伶菜"],
    "SPEED": ["島袋寛子", "今井絵理子", "上原多香子", "新垣仁絵"],
    "MAX": ["NANA", "LINA", "MINA", "REINA"],
    "CHEMISTRY": ["堂珍嘉邦", "川畑要"],
    "EXILE THE SECOND": ["橘ケンチ", "黒木啓司", "TETSUYA", "NESMITH", "SHOKICHI"],
    "w-inds.": ["千葉涼平", "橘慶太", "緒方龍一"],
    "FLOW": ["KEIGO", "KOHSHI", "TAKE", "GOT'S", "IWASAKI"],
    "Do As Infinity": ["伴都美子", "大渡亮"],
    "Every Little Thing": ["持田香織", "伊藤一朗"],
    "globe": ["KEIKO", "MARC", "TK"],
    "TRF": ["DJ KOO", "SAM", "ETSU", "CHIHARU", "YU-KI"],
    "安室奈美恵": [],  # ソロアーティストだがバックダンサー含む場合
    "SMAP": ["中居正広", "木村拓哉", "稲垣吾郎", "草彅剛", "香取慎吾"],
    "TOKIO": ["城島茂", "国分太一", "松岡昌宏", "長瀬智也"],
    "V6": ["坂本昌行", "長野博", "井ノ原快彦", "森田剛", "三宅健", "岡田准一"],
    "KinKi Kids": ["堂本光一", "堂本剛"],
    "タッキー&翼": ["滝沢秀明", "今井翼"],
    "NEWS": ["小山慶一郎", "加藤シゲアキ", "増田貴久"],
    "KAT-TUN": ["亀梨和也", "上田竜也", "中丸雄一"],
    "Sexy Zone": ["中島健人", "菊池風磨", "佐藤勝利", "松島聡"],
    "A.B.C-Z": ["橋本良亮", "戸塚祥太", "河合郁人", "五関晃一", "塚田僚一"],
    "ジャニーズWEST": ["重岡大毅", "桐山照史", "中間淳太", "神山智洋", "藤井流星", "濵田崇裕", "小瀧望"],
    "なにわ男子": ["西畑大吾", "大西流星", "道枝駿佑", "高橋恭平", "長尾謙杜", "大橋和也", "藤原丈一郎"],
    "THE YELLOW MONKEY": ["吉井和哉", "菊地英昭", "廣瀬洋一", "菊地英二"],
    "BOØWY": ["氷室京介", "布袋寅泰", "松井恒松", "高橋まこと"],
    "LUNA SEA": ["RYUICHI", "SUGIZO", "INORAN", "J", "真矢"],
    "GLAY": ["TERU", "TAKURO", "HISASHI", "JIRO"],
    "DIR EN GREY": ["京", "薫", "Die", "Toshiya", "Shinya"],
    "the GazettE": ["RUKI", "URUHA", "AOI", "REITA", "KAI"],
    "ASIAN KUNG-FU GENERATION": ["後藤正文", "喜多建介", "山田貴洋", "伊地知潔"],
    "ELLEGARDEN": ["細美武士", "生形真一", "高橋宏貴", "高田雄一"],
    "10-FEET": ["TAKUMA", "NAOKI", "KOUICHI"],
    "Hi-STANDARD": ["難波章浩", "横山健", "恒岡章"],
    "BRAHMAN": ["TOSHI-LOW", "KOHKI", "MAKOTO", "RONZI"],
    "Dragon Ash": ["降谷建志", "HIROKI", "IKÜZÖNE", "馬場育三", "櫻井誠"],
    "RIP SLYME": ["RYO-Z", "ILMARI", "PES", "SU", "DJ FUMIYA"],
    "KICK THE CAN CREW": ["KREVA", "MCU", "LITTLE"],
    "RHYMESTER": ["宇多丸", "Mummy-D", "DJ JIN"],
    "m-flo": ["VERBAL", "☆Taku Takahashi"],
    "SOUL'd OUT": ["Diggy-MO'", "Bro.Hi", "Shinnosuke"],
    "TERIYAKI BOYZ": ["ILMARI", "RYO-Z", "VERBAL", "WISE", "NIGO"],
    "湘南乃風": ["若旦那", "HAN-KUN", "SHOCK EYE", "RED RICE"],
    "HOME MADE 家族": ["MICRO", "KURO", "DJ U-ICHI"],
    "Aqua Timez": ["太志", "大介", "OKP-STAR", "mayuko", "TASSHI"],
    "FUNKY MONKEY BABYS": ["ファンキー加藤", "モン吉", "DJケミカル"],
    "C&K": ["CLIEVY", "KEEN"],
    "DISH//": ["北村匠海", "矢部昌暉", "橘柊生", "泉大智"],
    "THE ORAL CIGARETTES": ["山中拓也", "鈴木重伸", "あきらかにあきら", "中西雅哉"],
    "MY FIRST STORY": ["Hiro", "Nob", "Teru", "Kid'z", "Sho"],
    "SiM": ["MAH", "SHOW-HATE", "SiN", "GODRi"],
    "coldrain": ["Masato", "Y.K.C", "Sugi", "RxYxO"],
    "Crossfaith": ["Kenta Koie", "Terufumi Tamano", "Kazuki Takemura", "Hiroki Ikegawa", "Tatsuya Amano"],
    "Crystal Lake": ["Ryo Kinoshita", "Yusuke Kobayashi", "Shinya Hori", "Gaku Taura"],
    "Fear, and Loathing in Las Vegas": ["So", "Minami", "Taiki", "Tomonori", "Tetsuya", "Keisuke"],
    "ROTTENGRAFFTY": ["N∀OKI", "KAZUOMI", "侑威地", "HIROSHI"],
    "04 Limited Sazabys": ["GEN", "RYU-TA", "HIROKAZ", "KOUHEI"],
    "BLUE ENCOUNT": ["田邊駿一", "江口雄也", "辻村勇太", "高村佳秀"],
    "[Alexandros]": ["川上洋平", "磯部寛之", "白井眞輝", "庄村聡泰"],
    "KANA-BOON": ["谷口鮪", "小泉貴裕", "古賀隼斗", "飯田祐馬"],
    "KEYTALK": ["寺中友将", "首藤義勝", "小野武正", "八木優樹"],
    "フレデリック": ["三原健司", "三原康司", "高橋武"],
    "SHISHAMO": ["宮崎朝子", "松岡彩", "吉川美冴貴"],
    "SCANDAL": ["HARUNA", "MAMI", "TOMOMI", "RINA"],
    "BAND-MAID": ["小鳩ミク", "SAIKI", "KANAMI", "MISA", "AKANE"],
    "CHAI": ["マナ", "カナ", "ユウキ", "ユナ"],
    "tricot": ["中嶋イッキュウ", "キダ モティフォ", "ヒロミ・ヒロヒロ"],
    "Hump Back": ["林萌々子", "美咲", "ぴか"],
    "ネクライトーキー": ["もっさ", "朝日", "カズマ・タケイ", "藤田"],
    "ヤバイTシャツ屋さん": ["しばたありぼぼ", "こやまたくや", "もりもりもと"],
    "打首獄門同好会": ["大澤敦史", "河本あす香", "junko"],
    "マキシマム ザ ホルモン": ["マキシマムザ亮君", "ダイスケはん", "上ちゃん", "ナヲ"],
    "BiSH": ["アイナ・ジ・エンド", "セントチヒロ・チッチ", "モモコグミカンパニー", "ハシヤスメ・アツコ", "リンリン", "アユニ・D"],
    "でんぱ組.inc": ["相沢梨紗", "成瀬瑛美", "最上もが", "夢眠ねむ", "藤咲彩音", "古川未鈴"],
    "PassCode": ["大上陽奈子", "高嶋楓", "有馬えみり", "南菜生"],
    "ももいろクローバーZ": ["百田夏菜子", "玉井詩織", "佐々木彩夏", "高城れに"],
    "私立恵比寿中学": ["安本彩花", "星名美怜", "小林歌穂", "中山莉子", "柏木ひなた", "仲村悠菜"],
    "TEAM SHACHI": ["秋本帆華", "咲良菜緒", "大黒柚姫", "坂本遥奈"],
    "たこやきレインボー": ["清井咲希", "彩木咲良", "堀くるみ", "根岸可蓮", "春名真依"],
    "SUPER☆GiRLS": ["荒井玲良", "石丸千賀", "井上真由子", "内村莉彩", "金澤有希", "坂林佳奈", "田中美麗", "樋口なづな", "増本綺良", "溝手るか", "宮﨑理奈", "山口綺羅"],
    "X21": ["泉川実穂", "小澤奈々花", "吉本実憂", "末永真唯"],
    "Cheeky Parade": ["関根優那", "永井日菜", "島崎莉乃", "渡辺亜紗美", "山本真凛", "鈴木真梨耶", "鈴木友梨耶", "溝呂木世蘭", "小島夕佳"],
    "9nine": ["西脇彩華", "村田寛奈", "吉井香奈恵", "佐武宇綺"],
    "東京女子流": ["山邊未夢", "新井ひとみ", "中江友梨", "庄司芽生", "小西彩乃"],
    "SUPER BEAVER": ["渋谷龍太", "上杉研太", "柳沢亮太", "藤原広明"],
    "THE BACK HORN": ["山田将司", "菅波栄純", "松田晋二", "岸田研二"],
    "androp": ["内澤崇仁", "佐藤拓也", "前田恭介", "伊藤彬彦"],
    "NICO Touches the Walls": ["光村龍哉", "古村大介", "坂倉心悟", "対馬祥太郎"],
    "凛として時雨": ["TK", "345", "ピエール中野"],
    "9mm Parabellum Bullet": ["菅原卓郎", "滝善充", "中村和彦", "かみじょうちひろ"],
    "the telephones": ["石毛輝", "松本誠治", "長島涼平", "岡本伸明"],
    "THE BAWDIES": ["ROY", "TAXMAN", "JIM", "MARCY"],
    "OKAMOTO'S": ["オカモトショウ", "オカモトコウキ", "ハマ・オカモト", "オカモトレイジ"],
    "andymori": ["小山田壮平", "藤原寛", "後藤大樹"],
    "THE NOVEMBERS": ["小林祐介", "高松浩史", "玉置真吾", "吉木諒祐"],
    "LITE": ["武田信幸", "井澤惇", "山本晃紀", "青山譲二"],
    "toe": ["山嵜廣和", "山根敏史", "美濃隆章", "柏倉隆史"],
    "MONO": ["Takaakira 'Taka' Goto", "Hideki 'Yoda' Suematsu", "Tamaki Kunishi", "Yasunori Takada"],
    "Boris": ["Takeshi", "Wata", "Atsuo"],
    "envy": ["Tetsuya Fukagawa", "Nobukata Kawai", "Masahiro Tobita", "Manabu Nakagawa", "Dairoku Seki"],
    "downy": ["青木ロビン", "青木裕", "秋嶋良", "中尾憲太郎", "タブゾンビ"],
    "Suchmos": ["HSU", "YONCE", "TAIHEI", "OK", "KCEE", "TAIKING"],
    "WONK": ["荒田洸", "江﨑文武", "井上幹", "長塚健斗"],
    "Nulbarich": ["JQ", "Ryan", "Shingo", "Takuma", "Tomoya"],
    "SIRUP": ["KYOtaro"],
    "iri": [],  # ソロアーティスト
    "ROTH BART BARON": ["三船雅也", "豊田健弘"],
    "Yogee New Waves": ["角舘健悟", "粕谷哲司", "藤本隆行", "上野真吾"],
    "never young beach": ["安部勇磨", "巽啓伍", "松島皓", "鈴木健人", "阿南智史"],
    "DYGL": ["秋山信樹", "下中洋介", "加地洋太朗", "嘉本康平"],
    "Tempalay": ["小原綾斗", "AAAMYYY", "成田大致", "藤本夏樹"],
    "LUCKY TAPES": ["高橋海", "高橋健介", "田口恵人"],
    "Awesome City Club": ["atagi", "PORIN", "モリシー"],
    "cero": ["髙城晶平", "荒内佑", "橋本翼"],
    "OGRE YOU ASSHOLE": ["出戸学", "馬渕啓", "勝浦隆嗣", "高橋広", "清水隆史"],
    "skillkills": ["近藤大彗", "福山颯", "伊達大樹"],
    "AAAMYYY": [],  # Tempalayも参加
    "羊文学": ["塩塚モエカ", "ゆりか", "フクダヒロア"],
    "ずっと真夜中でいいのに。": ["ACAね"],
    "ヨルシカ": ["n-buna", "suis"],
    "神はサイコロを振らない": ["柳田周作", "吉田喜一", "桐木岳貢", "黒川亮介"],
    "Vaundy": [],  # ソロアーティスト
    "藤井風": [],  # ソロアーティスト
    "優里": [],  # ソロアーティスト
    "imase": [],  # ソロアーティスト
    "Ado": [],  # ソロアーティスト
    "Eve": [],  # ソロアーティスト
    "Aimer": [],  # ソロアーティスト
    "LiSA": [],  # ソロアーティスト
    "milet": [],  # ソロアーティスト
    "YOASOBI": ["Ayase", "ikura"],
    "After the Rain": ["そらる", "まふまふ"]
}

def find_band_for_member(name):
    """メンバー名からバンド名を特定"""
    for band, members in BAND_MEMBERS.items():
        if name in members:
            return band
    return None

def update_band_names():
    """バンドメンバーのdisplay nameを更新"""
    try:
        print("🎵 バンドメンバー名更新処理開始")
        print("=" * 60)
        
        # 認証
        print("\n1️⃣ Google Sheets認証中...")
        credentials = Credentials.from_service_account_file(
            config.google_credentials_path,
            scopes=[
                'https://www.googleapis.com/auth/spreadsheets',
                'https://www.googleapis.com/auth/drive.file'
            ]
        )
        client = gspread.authorize(credentials)
        
        # スプレッドシートを開く
        print("2️⃣ データ取得中...")
        sheet = client.open_by_key(SPREADSHEET_ID)
        worksheet = sheet.sheet1
        
        # 全データを取得
        all_values = worksheet.get_all_values()
        headers = all_values[0]
        data = all_values[1:]
        
        # DataFrameに変換
        df = pd.DataFrame(data, columns=headers)
        print(f"   ✅ {len(df)}件のデータを取得")
        
        # 必要な列のインデックスを取得
        name_idx = headers.index('person_name')
        display_idx = headers.index('person_name_display')
        occupation_idx = headers.index('occupation')
        
        # 更新対象を特定
        print("\n3️⃣ バンドメンバー検出中...")
        updates = []
        update_cells = []
        
        for i, row in enumerate(df.values):
            person_name = row[name_idx]
            current_display = row[display_idx]
            occupation = row[occupation_idx] if occupation_idx < len(row) else ""
            
            # バンド名を検索
            band_name = find_band_for_member(person_name)
            
            if band_name:
                # 新しいdisplay nameを作成
                new_display = f"{person_name} ({band_name})"
                
                # 既に括弧がある場合はスキップ
                if "(" not in current_display or current_display != new_display:
                    updates.append({
                        'row': i + 2,  # ヘッダー行を考慮
                        'person_name': person_name,
                        'band': band_name,
                        'old_display': current_display,
                        'new_display': new_display
                    })
                    
                    # セル位置を計算（A=1, B=2, ...）
                    col_letter = chr(65 + display_idx)  # A, B, C, ...
                    if display_idx >= 26:
                        col_letter = chr(65 + display_idx // 26 - 1) + chr(65 + display_idx % 26)
                    
                    cell_ref = f"{col_letter}{i + 2}"
                    update_cells.append({'range': cell_ref, 'values': [[new_display]]})
        
        print(f"   ✅ {len(updates)}件のバンドメンバーを検出")
        
        if updates:
            # 更新内容を表示
            print("\n4️⃣ 更新対象:")
            print("-" * 60)
            for update in updates[:10]:  # 最初の10件を表示
                print(f"   {update['person_name']} → {update['new_display']}")
            
            if len(updates) > 10:
                print(f"   ... 他 {len(updates) - 10}件")
            
            # Google Sheetsを更新
            print("\n5️⃣ Google Sheets更新中...")
            
            # バッチ更新（高速化）
            batch_size = 100
            for i in range(0, len(update_cells), batch_size):
                batch = update_cells[i:i+batch_size]
                worksheet.batch_update(batch)
                print(f"   📤 {min(i + batch_size, len(update_cells))}/{len(update_cells)} 件完了")
            
            # CSVファイルも更新
            print("\n6️⃣ ローカルCSV更新中...")
            csv_file = "ultra_think_NO_FAKE_RESEARCHERS_20250827_143418.csv"
            local_df = pd.read_csv(csv_file, encoding='utf-8')
            
            for update in updates:
                row_idx = update['row'] - 2  # ヘッダー分を調整
                if row_idx < len(local_df):
                    local_df.at[row_idx, 'person_name_display'] = update['new_display']
            
            # バックアップを作成
            backup_file = f"{csv_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            pd.read_csv(csv_file, encoding='utf-8').to_csv(backup_file, index=False, encoding='utf-8')
            
            # 更新したCSVを保存
            local_df.to_csv(csv_file, index=False, encoding='utf-8')
            print(f"   ✅ CSVファイル更新完了")
            
            # レポート作成
            report = f"""
# バンドメンバー名更新レポート
更新日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 統計
- 総データ数: {len(df)}件
- 更新件数: {len(updates)}件
- 検出バンド数: {len(set([u['band'] for u in updates]))}組

## 更新例
"""
            for update in updates[:20]:
                report += f"- {update['person_name']} → {update['new_display']}\n"
            
            with open("BAND_NAME_UPDATE_REPORT.md", "w", encoding='utf-8') as f:
                f.write(report)
            
            print("\n" + "=" * 60)
            print("✨ 更新完了！")
            print(f"   📊 {len(updates)}件のバンドメンバー名を更新しました")
            print(f"   📝 詳細は BAND_NAME_UPDATE_REPORT.md を確認してください")
            print(f"   🔗 {sheet.url}")
            
        else:
            print("\n✅ 更新対象なし（既に全て更新済み）")
        
    except Exception as e:
        print(f"\n❌ エラー: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    update_band_names()