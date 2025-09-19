#!/usr/bin/env python3
"""
グループメンバー表示名修正システム
グループ名が表示されていないメンバーを検出して修正
"""

import pandas as pd
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class GroupMemberDisplayFixer:
    """グループメンバー表示名修正クラス"""
    
    def __init__(self):
        """初期化"""
        self.group_members = {}
        self.fixes_applied = []
        self.issues_found = []
        
        # 既知のグループメンバーデータベース
        # 2025-09-14 修正: お笑い芸人の正しいコンビメンバーに更新
        self.known_groups = {
            # お笑いコンビ（修正済み）
            '真空ジェシカ': ['ガク', '川北茂澄'],
            'Aマッソ': ['加納', '村上'],
            'ロングコートダディ': ['堂前透', '兎'],
            'アインシュタイン': ['河井ゆずる', '稲田直樹'],
            'ぺこぱ': ['松陰寺太勇', 'シュウペイ'],
            'ビスケッティ': ['きん', 'やす'],
            '４ガロン': ['志田', '下町ミルク'],
            # 音楽グループ
            'YOASOBI': ['Ayase', 'ikura'],
            'SEKAI NO OWARI': ['Fukase', 'Nakajin', 'Saori', 'DJ LOVE'],
            'X JAPAN': ['YOSHIKI', 'Toshl', 'hide', 'PATA', 'HEATH', 'TAIJI'],
            'GLAY': ['TERU', 'TAKURO', 'HISASHI', 'JIRO'],
            'LUNA SEA': ['RYUICHI', 'SUGIZO', 'INORAN', 'J', '真矢'],
            'BTS': ['RM', 'Jin', 'SUGA', 'J-Hope', 'Jimin', 'V', 'Jung Kook'],
            'SEVENTEEN': ['S.Coups', 'Jeonghan', 'Joshua', 'Jun', 'Hoshi', 'Wonwoo', 'Woozi', 'DK', 'Mingyu', 'The8', 'Seungkwan', 'Vernon', 'Dino'],
            'Stray Kids': ['Bang Chan', 'Lee Know', 'Changbin', 'Hyunjin', 'Han', 'Felix', 'Seungmin', 'I.N'],
            'ENHYPEN': ['Heeseung', 'Jay', 'Jake', 'Sunghoon', 'Sunoo', 'Jungwon', 'Ni-ki'],
            'TXT': ['Yeonjun', 'Soobin', 'Beomgyu', 'Taehyun', 'Huening Kai'],
            'NCT': ['Taeyong', 'Taeil', 'Johnny', 'Yuta', 'Kun', 'Doyoung', 'Ten', 'Jaehyun', 'WinWin', 'Jungwoo', 'Lucas', 'Mark', 'Xiaojun', 'Hendery', 'Renjun', 'Jeno', 'Haechan', 'Jaemin', 'YangYang', 'Shotaro', 'Sungchan', 'Chenle', 'Jisung'],
            'L\'Arc〜en〜Ciel': ['hyde', 'ken', 'tetsuya', 'yukihiro'],
            'B\'z': ['稲葉浩志', '松本孝弘'],
            'Mr.Children': ['桜井和寿', '田原健一', '中川敬輔', '鈴木英哉'],
            'サザンオールスターズ': ['桑田佳祐', '原由子', '関口和之', '松田弘', '野沢秀行'],
            'BUMP OF CHICKEN': ['藤原基央', '増川弘明', '直井由文', '升秀夫'],
            'RADWIMPS': ['野田洋次郎', '桑原彰', '武田祐介'],
            'ONE OK ROCK': ['Taka', 'Toru', 'Ryota', 'Tomoya'],
            'MAN WITH A MISSION': ['Tokyo Tanaka', 'Jean-Ken Johnny', 'Kamikaze Boy', 'DJ Santa Monica', 'Spear Rib'],
            '嵐': ['大野智', '櫻井翔', '相葉雅紀', '松本潤', '二宮和也'],
            'SMAP': ['中居正広', '木村拓哉', '稲垣吾郎', '草なぎ剛', '香取慎吾'],
            'TOKIO': ['城島茂', '国分太一', '松岡昌宏', '長瀬智也'],
            'KinKi Kids': ['堂本光一', '堂本剛'],
            'V6': ['坂本昌行', '長野博', '井ノ原快彦', '森田剛', '三宅健', '岡田准一'],
            'Hey! Say! JUMP': ['山田涼介', '知念侑李', '中島裕翔', '岡本圭人', '有岡大貴', '髙木雄也', '伊野尾慧', '八乙女光', '薮宏太'],
            'Kis-My-Ft2': ['北山宏光', '横尾渉', '藤ヶ谷太輔', '玉森裕太', '千賀健永', '宮田俊哉', '二階堂高嗣'],
            'Snow Man': ['深澤辰哉', '佐久間大介', '渡辺翔太', '宮舘涼太', '岩本照', '阿部亮平', '向井康二', '目黒蓮', 'ラウール'],
            'SixTONES': ['ジェシー', '京本大我', '松村北斗', '髙地優吾', '森本慎太郎', '田中樹'],
            'King & Prince': ['平野紫耀', '永瀬廉', '髙橋海人', '岸優太', '神宮寺勇太'],
            'なにわ男子': ['西畑大吾', '大西流星', '道枝駿佑', '高橋恭平', '長尾謙杜', '藤原丈一郎', '大橋和也'],
            'AKB48': ['柏木由紀', '岡田奈々', '向井地美音'],  # 代表的なメンバーのみ
            '乃木坂46': ['秋元真夏', '与田祐希', '遠藤さくら'],  # 代表的なメンバーのみ
            '櫻坂46': ['森田ひかる', '藤吉夏鈴', '山﨑天'],  # 代表的なメンバーのみ
            '日向坂46': ['佐々木久美', '加藤史帆', '小坂菜緒'],  # 代表的なメンバーのみ
            'EXILE': ['ATSUSHI', 'TAKAHIRO', 'NESMITH', 'SHOKICHI', 'NAOTO', '小林直己'],
            '三代目 J SOUL BROTHERS': ['NAOTO', '小林直己', 'ELLY', '山下健二郎', '岩田剛典', '今市隆二', '登坂広臣'],
            'GENERATIONS': ['白濱亜嵐', '片寄涼太', '数原龍友', '小森隼', '佐野玲於', '関口メンディー', '中務裕太'],
            'THE RAMPAGE': ['川村壱馬', 'RIKU', '吉野北人'],  # 代表的なメンバー
            'BALLISTIK BOYZ': ['深堀未来', '海沼流星'],  # 代表的なメンバー
            'FANTASTICS': ['佐藤大樹', '瀬口黎弥'],  # 代表的なメンバー
            'THE ORAL CIGARETTES': ['山中拓也', '鈴木重伸', 'あきらかにあきら', '中西雅哉'],
            'ASIAN KUNG-FU GENERATION': ['後藤正文', '喜多建介', '山田貴洋', '伊地知潔'],
            'UVERworld': ['TAKUYA∞', '克哉', '誠果', '信人', '彰', '真太郎'],
            'ORANGE RANGE': ['HIROKI', 'NAOTO', 'YAMATO', 'YOH', 'RYO'],
            'ケツメイシ': ['Ryo', 'Ryoji', '大蔵', 'DJ KOHNO'],
            'FUNKY MONKEY BABYS': ['ファンキー加藤', 'モン吉', 'DJケミカル'],
            'GReeeeN': ['HIDE', 'navi', '92', 'SOH'],
            'AAA': ['西島隆弘', '宇野実彩子', '與真司郎', '日高光啓', 'SKY-HI', '末吉秀太', '浦田直也'],
            'Da-iCE': ['工藤大輝', '岩岡徹', '大野雄大', '花村想太', '和田颯'],
            'DISH//': ['北村匠海', '矢部昌暉', '橘柊生', '泉大智'],
            'w-inds.': ['千葉涼平', '橘慶太', '緒方龍一'],
            'CHEMISTRY': ['堂珍嘉邦', '川畑要'],
            'コブクロ': ['黒田俊介', '小渕健太郎'],
            'ゆず': ['北川悠仁', '岩沢厚治'],
            'スキマスイッチ': ['大橋卓弥', '常田真太郎'],
            'ポルノグラフィティ': ['岡野昭仁', '新藤晴一'],
            'いきものがかり': ['吉岡聖恵', '水野良樹', '山下穂尊'],
            'DREAMS COME TRUE': ['吉田美和', '中村正人'],
            'Every Little Thing': ['持田香織', '伊藤一朗'],
            'globe': ['KEIKO', 'MARC PANTHER', '小室哲哉'],
            'TRF': ['YU-KI', 'DJ KOO', 'SAM', 'ETSU', 'CHIHARU'],
            'MAX': ['MINA', 'NANA', 'LINA', 'REINA'],
            'SPEED': ['島袋寛子', '今井絵理子', '上原多香子', '新垣仁絵'],
            'モーニング娘。': ['譜久村聖', '生田衣梨奈', '石田亜佑美'],  # 現メンバー代表
            'Perfume': ['のっち', 'かしゆか', 'あ〜ちゃん'],
            'BABYMETAL': ['SU-METAL', 'MOAMETAL'],
            'BAND-MAID': ['小鳩ミク', 'SAIKI', 'KANAMI', 'AKANE', 'MISA'],
            'SCANDAL': ['HARUNA', 'MAMI', 'TOMOMI', 'RINA'],
            'SILENT SIREN': ['すぅ', 'ひなんちゅ', 'あいにゃん', 'ゆかるん'],
            'SHISHAMO': ['宮崎朝子', '松岡彩', '吉川美冴貴'],
            'tricot': ['中嶋イッキュウ', 'キダ モティフォ', 'ヒロミ・ヒロヒロ'],
            'チャットモンチー': ['橋本絵莉子', '福岡晃子'],
            'Aimer': ['Aimer'],  # ソロだが表記確認用
            'LiSA': ['LiSA'],  # ソロだが表記確認用
            'YUKI': ['YUKI'],  # 元JUDY AND MARY
            'JUJU': ['JUJU'],  # ソロだが表記確認用
            'AI': ['AI'],  # ソロだが表記確認用
            'MISIA': ['MISIA'],  # ソロだが表記確認用
            'Superfly': ['越智志帆'],
            'miwa': ['miwa'],  # ソロだが表記確認用
            'YUI': ['YUI'],  # ソロだが表記確認用
            'aiko': ['aiko'],  # ソロだが表記確認用
            '宇多田ヒカル': ['宇多田ヒカル'],  # ソロだが表記確認用
            '浜崎あゆみ': ['浜崎あゆみ'],  # ソロだが表記確認用
            '安室奈美恵': ['安室奈美恵'],  # ソロだが表記確認用
            '倉木麻衣': ['倉木麻衣'],  # ソロだが表記確認用
            '西野カナ': ['西野カナ'],  # ソロだが表記確認用
            'あいみょん': ['あいみょん'],  # ソロだが表記確認用
            '米津玄師': ['米津玄師'],  # ソロだが表記確認用
            '星野源': ['星野源'],  # ソロだが表記確認用
            '藤井風': ['藤井風'],  # ソロだが表記確認用
            'Vaundy': ['Vaundy'],  # ソロだが表記確認用
            '優里': ['優里'],  # ソロだが表記確認用
            'YOASOBI': ['Ayase', 'ikura'],  # 再掲載（重要）
            'Ado': ['Ado'],  # ソロだが表記確認用
            'Eve': ['Eve'],  # ソロだが表記確認用
            'ヨルシカ': ['n-buna', 'suis'],
            'ずっと真夜中でいいのに。': ['ACAね'],
            'TUYU': ['ぷす', 'れい', 'みつ', 'おむ'],
            'Orangestar': ['Orangestar'],  # ソロだが表記確認用
            'DECO*27': ['DECO*27'],  # ソロだが表記確認用
            'ハチ': ['ハチ'],  # 米津玄師の別名
            'wowaka': ['wowaka'],  # ヒトリエ
            'ヒトリエ': ['wowaka', 'イガラシ', 'ゆーまお', 'シノダ']
        }
        
        # メンバー → グループの逆引き辞書作成
        self.member_to_group = {}
        for group_name, members in self.known_groups.items():
            for member in members:
                if member not in self.member_to_group:
                    self.member_to_group[member] = []
                self.member_to_group[member].append(group_name)
    
    def analyze_code_structure(self, df: pd.DataFrame) -> Dict:
        """
        1. まずコード全体の構造を理解
        データフレームとグループメンバーの構造を分析
        """
        logger.info("📊 ステップ1: コード構造分析")
        
        analysis = {
            'total_records': len(df),
            'columns': list(df.columns),
            'group_members_found': 0,
            'missing_group_names': [],
            'current_issues': []
        }
        
        # グループメンバーの検出
        for idx, row in df.iterrows():
            person_name = row['person_name']
            display_name = row['person_name_display']
            
            if person_name in self.member_to_group:
                analysis['group_members_found'] += 1
                groups = self.member_to_group[person_name]
                
                # グループ名が表示名に含まれているかチェック
                has_group = False
                for group in groups:
                    if '（' in display_name and group in display_name:
                        has_group = True
                        break
                
                if not has_group:
                    analysis['missing_group_names'].append({
                        'person_id': row['person_id'],
                        'person_name': person_name,
                        'current_display': display_name,
                        'groups': groups
                    })
        
        analysis['current_issues'] = analysis['missing_group_names'][:10]  # 最初の10件
        
        logger.info(f"  総レコード数: {analysis['total_records']}")
        logger.info(f"  グループメンバー検出: {analysis['group_members_found']}人")
        logger.info(f"  グループ名未記載: {len(analysis['missing_group_names'])}人")
        
        return analysis
    
    def verify_function_logic(self, df: pd.DataFrame) -> List[Dict]:
        """
        2. 各関数の動作を検証
        グループ名追加ロジックの検証
        """
        logger.info("🔍 ステップ2: 関数動作検証")
        
        verification_results = []
        
        # テストケース
        test_cases = [
            {'name': 'Ayase', 'expected_group': 'YOASOBI'},
            {'name': 'Fukase', 'expected_group': 'SEKAI NO OWARI'},
            {'name': 'YOSHIKI', 'expected_group': 'X JAPAN'},
            {'name': 'hyde', 'expected_group': 'L\'Arc〜en〜Ciel'},
            {'name': 'Taka', 'expected_group': 'ONE OK ROCK'}
        ]
        
        for test in test_cases:
            name = test['name']
            expected = test['expected_group']
            
            # メンバー検索
            found_groups = self.member_to_group.get(name, [])
            
            result = {
                'name': name,
                'expected': expected,
                'found': found_groups,
                'status': expected in found_groups
            }
            
            verification_results.append(result)
            
            if result['status']:
                logger.info(f"  ✅ {name} → {expected}: 正常")
            else:
                logger.warning(f"  ❌ {name} → {expected}: 検出失敗")
        
        return verification_results
    
    def identify_edge_cases(self, df: pd.DataFrame) -> List[Dict]:
        """
        3. 潜在的なバグやエッジケースを特定
        """
        logger.info("⚠️ ステップ3: エッジケース特定")
        
        edge_cases = []
        
        # 複数グループに所属するメンバー
        for member, groups in self.member_to_group.items():
            if len(groups) > 1:
                edge_cases.append({
                    'type': 'MULTIPLE_GROUPS',
                    'member': member,
                    'groups': groups,
                    'action': 'メインのグループを優先'
                })
        
        # ソロアーティストとして活動もしているグループメンバー
        solo_and_group = ['hyde', '稲葉浩志', '桑田佳祐', 'ATSUSHI', 'TAKAHIRO']
        for artist in solo_and_group:
            if artist in self.member_to_group:
                edge_cases.append({
                    'type': 'SOLO_AND_GROUP',
                    'member': artist,
                    'groups': self.member_to_group[artist],
                    'action': 'コンテキストに応じて判断'
                })
        
        logger.info(f"  エッジケース検出: {len(edge_cases)}件")
        
        return edge_cases[:5]  # 最初の5件
    
    def propose_improvements(self, analysis: Dict) -> List[Dict]:
        """
        4. 改善案を提示
        """
        logger.info("💡 ステップ4: 改善案生成")
        
        improvements = []
        
        # グループ名の追加
        improvements.append({
            'action': 'ADD_GROUP_NAMES',
            'description': 'グループメンバーの表示名にグループ名を追加',
            'target_count': len(analysis['missing_group_names']),
            'format': '名前（グループ名）',
            'examples': [
                'Ayase → Ayase（YOASOBI）',
                'Fukase → Fukase（SEKAI NO OWARI）',
                'YOSHIKI → YOSHIKI（X JAPAN）'
            ]
        })
        
        # PDCAルール追加
        improvements.append({
            'action': 'ADD_PDCA_RULE',
            'rule_id': 'RULE_097',
            'name': 'グループメンバー表示名ルール',
            'description': 'グループメンバーは必ず「名前（グループ名）」形式で表示'
        })
        
        # 自動化提案
        improvements.append({
            'action': 'AUTOMATION',
            'description': 'グループメンバーデータベースの定期更新',
            'frequency': '月次',
            'source': 'Wikipedia、公式サイト'
        })
        
        return improvements
    
    def fix_display_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """表示名の修正実行"""
        logger.info("🔧 表示名修正実行")
        
        fixed_count = 0
        
        for idx, row in df.iterrows():
            person_name = row['person_name']
            current_display = row['person_name_display']
            
            if person_name in self.member_to_group:
                groups = self.member_to_group[person_name]
                
                # グループ名が既に含まれているかチェック
                has_group = False
                for group in groups:
                    if '（' in current_display and group in current_display:
                        has_group = True
                        break
                
                if not has_group:
                    # 最初のグループを追加（通常は最も有名なグループ）
                    main_group = groups[0]
                    new_display = f"{person_name}（{main_group}）"
                    
                    df.at[idx, 'person_name_display'] = new_display
                    
                    self.fixes_applied.append({
                        'person_id': row['person_id'],
                        'person_name': person_name,
                        'old_display': current_display,
                        'new_display': new_display
                    })
                    
                    fixed_count += 1
                    
                    if fixed_count % 10 == 0:
                        logger.info(f"  修正済み: {fixed_count}件")
        
        logger.info(f"✅ 修正完了: {fixed_count}件")
        
        return df


def main():
    """メイン処理"""
    logger.info("=" * 60)
    logger.info("🚀 グループメンバー表示名修正システム起動")
    logger.info("=" * 60)
    
    # データ読み込み
    csv_file = Path('ultra_think_FINAL_VERIFIED_20250912_041421.csv')
    if not csv_file.exists():
        csv_file = Path('ultra_think_MASSIVE_CLEANED_20250912_035645.csv')
    
    logger.info(f"📂 データ読み込み: {csv_file}")
    df = pd.read_csv(csv_file)
    
    # 修正器初期化
    fixer = GroupMemberDisplayFixer()
    
    # 1. コード構造分析
    analysis = fixer.analyze_code_structure(df)
    
    # 2. 関数動作検証
    verification = fixer.verify_function_logic(df)
    
    # 3. エッジケース特定
    edge_cases = fixer.identify_edge_cases(df)
    
    # 4. 改善案生成
    improvements = fixer.propose_improvements(analysis)
    
    # 問題のあるレコード表示
    logger.info("\n📋 グループ名未記載の例:")
    for issue in analysis['current_issues'][:5]:
        logger.info(f"  {issue['person_id']}: {issue['person_name']} → {issue['current_display']}")
        logger.info(f"    所属: {', '.join(issue['groups'])}")
    
    # 修正実行
    logger.info("\n🔧 修正実行中...")
    df_fixed = fixer.fix_display_names(df)
    
    # バックアップ作成
    backup_file = f"backup_before_group_fix_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df.to_csv(backup_file, index=False, encoding='utf-8-sig')
    logger.info(f"📁 バックアップ作成: {backup_file}")
    
    # 修正済みデータ保存
    output_file = f"ultra_think_GROUP_FIXED_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    df_fixed.to_csv(output_file, index=False, encoding='utf-8-sig')
    logger.info(f"💾 修正データ保存: {output_file}")
    
    # 修正結果サマリー
    logger.info("\n" + "=" * 60)
    logger.info("📊 修正結果サマリー")
    logger.info("=" * 60)
    logger.info(f"修正件数: {len(fixer.fixes_applied)}件")
    
    if fixer.fixes_applied:
        logger.info("\n修正例（最初の10件）:")
        for fix in fixer.fixes_applied[:10]:
            logger.info(f"  {fix['person_id']}: {fix['old_display']} → {fix['new_display']}")
    
    # レポート生成
    report_file = f"GROUP_FIX_REPORT_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    report = {
        'timestamp': datetime.now().isoformat(),
        'analysis': analysis,
        'fixes_applied': fixer.fixes_applied,
        'total_fixed': len(fixer.fixes_applied)
    }
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    logger.info(f"\n📄 レポート生成: {report_file}")
    logger.info("\n✅ グループメンバー表示名修正完了")


if __name__ == "__main__":
    main()