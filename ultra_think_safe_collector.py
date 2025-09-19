#!/usr/bin/env python3
"""
Ultra Think Safe Collector
エラー防止型段階的収集システム
100件ごとの検証とチェックポイント保存機能付き
"""

import csv
import json
import re
from datetime import datetime
from typing import Dict, List, Set, Tuple, Optional
import os
import time


class SafeCollector:
    """エラー防止型収集システム"""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.base_file = "ultra_think_massive_20250825_170109.csv"
        self.checkpoint_dir = "checkpoints"
        self.output_csv = f"ultra_think_safe_{self.timestamp}.csv"
        self.output_json = f"ultra_think_safe_{self.timestamp}.json"
        self.report_file = f"SAFE_COLLECTION_REPORT_{self.timestamp}.md"
        
        # 統計情報
        self.stats = {
            'initial_count': 0,
            'added_count': 0,
            'duplicate_count': 0,
            'error_count': 0,
            'fixed_count': 0,
            'validation_passes': 0,
            'validation_failures': 0,
            'phase_results': {}
        }
        
        # 既存データ
        self.existing_data = []
        self.existing_names = set()
        self.existing_display = set()
        
        # 収集データ
        self.new_data = []
        
        # バッチサイズ
        self.batch_size = 100
        
        # チェックポイントディレクトリ作成
        os.makedirs(self.checkpoint_dir, exist_ok=True)
    
    def load_existing_data(self) -> bool:
        """既存データを読み込み"""
        try:
            print(f"📂 既存データ読み込み中: {self.base_file}")
            
            with open(self.base_file, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                self.existing_data = list(reader)
            
            self.stats['initial_count'] = len(self.existing_data)
            
            # 重複チェック用セット作成
            for record in self.existing_data:
                person_name = record.get('person_name', '').strip()
                person_name_display = record.get('person_name_display', '').strip()
                
                if person_name:
                    self.existing_names.add(person_name.lower())
                if person_name_display:
                    self.existing_display.add(person_name_display)
            
            print(f"✅ {len(self.existing_data)}件の既存データ読み込み完了")
            print(f"   - 既存person_name: {len(self.existing_names)}件")
            print(f"   - 既存person_name_display: {len(self.existing_display)}件")
            
            return True
            
        except Exception as e:
            print(f"❌ データ読み込みエラー: {e}")
            return False
    
    def validate_record(self, record: Dict) -> Tuple[bool, List[str]]:
        """レコードの検証"""
        errors = []
        
        # 必須フィールドチェック
        if not record.get('person_name', '').strip():
            errors.append("person_name is empty")
        
        if not record.get('person_name_display', '').strip():
            errors.append("person_name_display is empty")
        
        # birth_year検証（存在する場合）
        birth_year = record.get('birth_year', '')
        if birth_year:
            try:
                year = int(birth_year)
                if year < -3000 or year > 2025:
                    errors.append(f"Invalid birth_year: {year}")
            except:
                errors.append(f"birth_year is not a number: {birth_year}")
        
        # 重複チェック
        person_name = record.get('person_name', '').strip()
        person_name_display = record.get('person_name_display', '').strip()
        
        if person_name.lower() in self.existing_names:
            errors.append(f"Duplicate person_name: {person_name}")
        
        if person_name_display in self.existing_display:
            errors.append(f"Duplicate person_name_display: {person_name_display}")
        
        # パターンチェック（問題のあるパターン）
        if re.match(r'^.+_\d{3,4}$', person_name_display):
            errors.append(f"Invalid pattern (occupation_number): {person_name_display}")
        
        if '_Person_' in person_name:
            errors.append(f"Invalid pattern (_Person_): {person_name}")
        
        return len(errors) == 0, errors
    
    def validate_batch(self, batch: List[Dict]) -> Tuple[bool, Dict]:
        """バッチ単位の検証"""
        print(f"\n🔍 バッチ検証中（{len(batch)}件）...")
        
        validation_result = {
            'total': len(batch),
            'passed': 0,
            'failed': 0,
            'errors': []
        }
        
        for i, record in enumerate(batch):
            is_valid, errors = self.validate_record(record)
            
            if is_valid:
                validation_result['passed'] += 1
            else:
                validation_result['failed'] += 1
                validation_result['errors'].append({
                    'index': i,
                    'person_name': record.get('person_name', ''),
                    'errors': errors
                })
        
        # 結果表示
        print(f"   ✅ 合格: {validation_result['passed']}件")
        print(f"   ❌ 不合格: {validation_result['failed']}件")
        
        if validation_result['failed'] > 0:
            print(f"   ⚠️ エラー詳細:")
            for error_info in validation_result['errors'][:5]:  # 最初の5件表示
                print(f"      - {error_info['person_name']}: {', '.join(error_info['errors'])}")
        
        return validation_result['failed'] == 0, validation_result
    
    def fix_batch_errors(self, batch: List[Dict], validation_result: Dict) -> List[Dict]:
        """バッチのエラーを修正"""
        print(f"\n🔧 エラー修正中...")
        
        fixed_batch = []
        fixed_count = 0
        
        for i, record in enumerate(batch):
            # エラーがあるレコードを探す
            error_info = None
            for err in validation_result['errors']:
                if err['index'] == i:
                    error_info = err
                    break
            
            if error_info:
                # 修正可能なエラーのみ修正
                fixed_record = record.copy()
                fixed = False
                
                # 空のperson_nameを修正
                if "person_name is empty" in error_info['errors']:
                    if record.get('name'):
                        fixed_record['person_name'] = record['name']
                        fixed = True
                
                # 修正できた場合のみ追加
                if fixed:
                    # 再検証
                    is_valid, _ = self.validate_record(fixed_record)
                    if is_valid:
                        fixed_batch.append(fixed_record)
                        fixed_count += 1
                        self.stats['fixed_count'] += 1
                # 修正できない場合はスキップ
                else:
                    self.stats['error_count'] += 1
            else:
                # エラーなしのレコード
                fixed_batch.append(record)
        
        print(f"   ✅ {fixed_count}件修正完了")
        print(f"   ⚠️ {len(batch) - len(fixed_batch)}件スキップ")
        
        return fixed_batch
    
    def save_checkpoint(self, phase_name: str, data: List[Dict]):
        """チェックポイント保存"""
        checkpoint_file = os.path.join(
            self.checkpoint_dir,
            f"checkpoint_{phase_name}_{self.timestamp}.json"
        )
        
        with open(checkpoint_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 チェックポイント保存: {checkpoint_file}")
    
    def create_person_record(self, 
                           person_name: str,
                           person_name_ja: str,
                           person_name_display: str,
                           birth_year: Optional[int] = None,
                           occupation: str = "",
                           nationality: str = "日本",
                           category: str = "",
                           subcategory: str = "",
                           group_name: str = "",
                           is_fictional: bool = False,
                           is_animal: bool = False,
                           phase: str = "SafeCollection") -> Dict:
        """人物レコード作成"""
        
        # グループメンバーの場合の表示名調整
        if group_name:
            person_name_display = f"{person_name_ja}（{group_name}）"
        
        record = {
            'batch_id': f'safe_{phase.lower()}',
            'birth_year': str(birth_year) if birth_year else '',
            'category': category,
            'cultural_significance': '',
            'description': '',
            'educational_value': '',
            'era': '',
            'followers': '',
            'global_recognition': '',
            'grade': 'A',
            'historical_impact': '',
            'is_animal': 'true' if is_animal else '',
            'is_fictional': 'true' if is_fictional else '',
            'main_category': category,
            'name': person_name,
            'nationality': nationality,
            'occupation': occupation,
            'person_name': person_name,
            'person_name_display': person_name_display,
            'person_name_ja': person_name_ja,
            'phase': phase,
            'platform': '',
            'subcategory': subcategory
        }
        
        return record
    
    def collect_phase1_politicians_business(self) -> List[Dict]:
        """Phase 1-1: 日本の政治家・経営者（200件）"""
        print("\n📊 Phase 1-1: 政治家・経営者収集中...")
        
        data = []
        
        # 歴代首相（戦後主要）
        prime_ministers = [
            ("Shigeru Yoshida", "吉田茂", "吉田茂", 1878, "政治家"),
            ("Hayato Ikeda", "池田勇人", "池田勇人", 1899, "政治家"),
            ("Eisaku Sato", "佐藤栄作", "佐藤栄作", 1901, "政治家"),
            ("Kakuei Tanaka", "田中角栄", "田中角栄", 1918, "政治家"),
            ("Takeo Miki", "三木武夫", "三木武夫", 1907, "政治家"),
            ("Takeo Fukuda", "福田赳夫", "福田赳夫", 1905, "政治家"),
            ("Masayoshi Ohira", "大平正芳", "大平正芳", 1910, "政治家"),
            ("Zenko Suzuki", "鈴木善幸", "鈴木善幸", 1911, "政治家"),
            ("Yasuhiro Nakasone", "中曽根康弘", "中曽根康弘", 1918, "政治家"),
            ("Noboru Takeshita", "竹下登", "竹下登", 1924, "政治家"),
            ("Sosuke Uno", "宇野宗佑", "宇野宗佑", 1922, "政治家"),
            ("Toshiki Kaifu", "海部俊樹", "海部俊樹", 1931, "政治家"),
            ("Kiichi Miyazawa", "宮澤喜一", "宮澤喜一", 1919, "政治家"),
            ("Morihiro Hosokawa", "細川護熙", "細川護熙", 1938, "政治家"),
            ("Tsutomu Hata", "羽田孜", "羽田孜", 1935, "政治家"),
            ("Tomiichi Murayama", "村山富市", "村山富市", 1924, "政治家"),
            ("Ryutaro Hashimoto", "橋本龍太郎", "橋本龍太郎", 1937, "政治家"),
            ("Keizo Obuchi", "小渕恵三", "小渕恵三", 1937, "政治家"),
            ("Yoshiro Mori", "森喜朗", "森喜朗", 1937, "政治家"),
            ("Junichiro Koizumi", "小泉純一郎", "小泉純一郎", 1942, "政治家"),
            ("Shinzo Abe", "安倍晋三", "安倍晋三", 1954, "政治家"),
            ("Yasuo Fukuda", "福田康夫", "福田康夫", 1936, "政治家"),
            ("Taro Aso", "麻生太郎", "麻生太郎", 1940, "政治家"),
            ("Yukio Hatoyama", "鳩山由紀夫", "鳩山由紀夫", 1947, "政治家"),
            ("Naoto Kan", "菅直人", "菅直人", 1946, "政治家"),
            ("Yoshihiko Noda", "野田佳彦", "野田佳彦", 1957, "政治家"),
            ("Yoshihide Suga", "菅義偉", "菅義偉", 1948, "政治家"),
            ("Fumio Kishida", "岸田文雄", "岸田文雄", 1957, "政治家"),
        ]
        
        # 現役知事（主要都道府県）
        governors = [
            ("Yuriko Koike", "小池百合子", "小池百合子", 1952, "政治家"),
            ("Hideaki Omura", "大村秀章", "大村秀章", 1960, "政治家"),
            ("Yoshimura Hirofumi", "吉村洋文", "吉村洋文", 1975, "政治家"),
            ("Motohiko Saito", "斎藤元彦", "斎藤元彦", 1977, "政治家"),
            ("Denny Tamaki", "玉城デニー", "玉城デニー", 1959, "政治家"),
        ]
        
        # 大企業創業者・経営者
        business_leaders = [
            ("Konosuke Matsushita", "松下幸之助", "松下幸之助", 1894, "実業家"),
            ("Soichiro Honda", "本田宗一郎", "本田宗一郎", 1906, "実業家"),
            ("Akio Morita", "盛田昭夫", "盛田昭夫", 1921, "実業家"),
            ("Masaru Ibuka", "井深大", "井深大", 1908, "実業家"),
            ("Kiichiro Toyoda", "豊田喜一郎", "豊田喜一郎", 1894, "実業家"),
            ("Tadao Kashio", "樫尾忠雄", "樫尾忠雄", 1917, "実業家"),
            ("Masayoshi Son", "孫正義", "孫正義", 1957, "実業家"),
            ("Tadashi Yanai", "柳井正", "柳井正", 1949, "実業家"),
            ("Hiroshi Mikitani", "三木谷浩史", "三木谷浩史", 1965, "実業家"),
            ("Takeshi Niinami", "新浪剛史", "新浪剛史", 1959, "実業家"),
            ("Kazuo Hirai", "平井一夫", "平井一夫", 1960, "実業家"),
            ("Akio Toyoda", "豊田章男", "豊田章男", 1956, "実業家"),
            ("Carlos Ghosn", "カルロス・ゴーン", "カルロス・ゴーン", 1954, "実業家"),
            ("Takahiro Hachigo", "八郷隆弘", "八郷隆弘", 1959, "実業家"),
            ("Makoto Uchida", "内田誠", "内田誠", 1966, "実業家"),
        ]
        
        # データ作成
        for person in prime_ministers + governors + business_leaders:
            if len(person) == 5:
                name, display, ja, year, occ = person
                record = self.create_person_record(
                    person_name=name,
                    person_name_ja=ja,
                    person_name_display=display,
                    birth_year=year,
                    occupation=occ,
                    category="政治・経済",
                    phase="Phase1-1"
                )
                data.append(record)
        
        return data
    
    def collect_phase1_cultural(self) -> List[Dict]:
        """Phase 1-2: 日本の文化人（300件）"""
        print("\n📚 Phase 1-2: 文化人収集中...")
        
        data = []
        
        # ノーベル賞受賞者
        nobel_winners = [
            ("Hideki Yukawa", "湯川秀樹", "湯川秀樹", 1907, "物理学者"),
            ("Shinichiro Tomonaga", "朝永振一郎", "朝永振一郎", 1906, "物理学者"),
            ("Leo Esaki", "江崎玲於奈", "江崎玲於奈", 1925, "物理学者"),
            ("Kenichi Fukui", "福井謙一", "福井謙一", 1918, "化学者"),
            ("Susumu Tonegawa", "利根川進", "利根川進", 1939, "生物学者"),
            ("Kenzaburo Oe", "大江健三郎", "大江健三郎", 1935, "作家"),
            ("Hideki Shirakawa", "白川英樹", "白川英樹", 1936, "化学者"),
            ("Ryoji Noyori", "野依良治", "野依良治", 1938, "化学者"),
            ("Koichi Tanaka", "田中耕一", "田中耕一", 1959, "化学者"),
            ("Makoto Kobayashi", "小林誠", "小林誠", 1944, "物理学者"),
            ("Toshihide Maskawa", "益川敏英", "益川敏英", 1940, "物理学者"),
            ("Osamu Shimomura", "下村脩", "下村脩", 1928, "化学者"),
            ("Ei-ichi Negishi", "根岸英一", "根岸英一", 1935, "化学者"),
            ("Akira Suzuki", "鈴木章", "鈴木章", 1930, "化学者"),
            ("Shinya Yamanaka", "山中伸弥", "山中伸弥", 1962, "医学者"),
            ("Isamu Akasaki", "赤崎勇", "赤崎勇", 1929, "物理学者"),
            ("Hiroshi Amano", "天野浩", "天野浩", 1960, "物理学者"),
            ("Shuji Nakamura", "中村修二", "中村修二", 1954, "物理学者"),
            ("Satoshi Omura", "大村智", "大村智", 1935, "化学者"),
            ("Takaaki Kajita", "梶田隆章", "梶田隆章", 1959, "物理学者"),
            ("Yoshinori Ohsumi", "大隅良典", "大隅良典", 1945, "生物学者"),
            ("Kazuo Ishiguro", "カズオ・イシグロ", "カズオ・イシグロ", 1954, "作家"),
            ("Tasuku Honjo", "本庶佑", "本庶佑", 1942, "医学者"),
            ("Akira Yoshino", "吉野彰", "吉野彰", 1948, "化学者"),
            ("Syukuro Manabe", "真鍋淑郎", "真鍋淑郎", 1931, "気象学者"),
        ]
        
        # 芥川賞受賞作家（近年の主要）
        akutagawa_writers = [
            ("Risa Wataya", "綿矢りさ", "綿矢りさ", 1984, "作家"),
            ("Hitomi Kanehara", "金原ひとみ", "金原ひとみ", 1983, "作家"),
            ("Fuminori Nakamura", "中村文則", "中村文則", 1977, "作家"),
            ("Naoki Matayoshi", "又吉直樹", "又吉直樹", 1980, "作家"),
            ("Sayaka Murata", "村田沙耶香", "村田沙耶香", 1979, "作家"),
            ("Natsuko Imamura", "今村夏子", "今村夏子", 1980, "作家"),
            ("Rin Usami", "宇佐見りん", "宇佐見りん", 1999, "作家"),
        ]
        
        # 直木賞受賞作家（近年の主要）
        naoki_writers = [
            ("Ryo Asai", "朝井リョウ", "朝井リョウ", 1989, "作家"),
            ("Hideo Yokoyama", "横山秀夫", "横山秀夫", 1957, "作家"),
            ("Mitsuyo Kakuta", "角田光代", "角田光代", 1967, "作家"),
            ("Eto Mori", "森絵都", "森絵都", 1968, "作家"),
            ("Natsuhiko Kyogoku", "京極夏彦", "京極夏彦", 1963, "作家"),
            ("Keigo Higashino", "東野圭吾", "東野圭吾", 1958, "作家"),
            ("Hisashi Inoue", "井上ひさし", "井上ひさし", 1934, "作家"),
            ("Shuhei Fujisawa", "藤沢周平", "藤沢周平", 1927, "作家"),
        ]
        
        # 建築家
        architects = [
            ("Kenzo Tange", "丹下健三", "丹下健三", 1913, "建築家"),
            ("Tadao Ando", "安藤忠雄", "安藤忠雄", 1941, "建築家"),
            ("Kisho Kurokawa", "黒川紀章", "黒川紀章", 1934, "建築家"),
            ("Toyo Ito", "伊東豊雄", "伊東豊雄", 1941, "建築家"),
            ("Kengo Kuma", "隈研吾", "隈研吾", 1954, "建築家"),
            ("Shigeru Ban", "坂茂", "坂茂", 1957, "建築家"),
            ("SANAA", "妹島和世", "妹島和世", 1956, "建築家"),
            ("Ryue Nishizawa", "西沢立衛", "西沢立衛", 1966, "建築家"),
        ]
        
        # データ作成
        for person in nobel_winners + akutagawa_writers + naoki_writers + architects:
            if len(person) == 5:
                name, display, ja, year, occ = person
                record = self.create_person_record(
                    person_name=name,
                    person_name_ja=ja,
                    person_name_display=display,
                    birth_year=year,
                    occupation=occ,
                    category="文化・学術",
                    phase="Phase1-2"
                )
                data.append(record)
        
        return data
    
    def process_phase(self, phase_name: str, collect_func) -> List[Dict]:
        """フェーズ単位の処理"""
        print(f"\n{'='*60}")
        print(f"🚀 {phase_name} 開始")
        print(f"{'='*60}")
        
        # データ収集
        phase_data = collect_func()
        print(f"\n📊 {len(phase_data)}件のデータを収集")
        
        # バッチ処理
        processed_data = []
        
        for i in range(0, len(phase_data), self.batch_size):
            batch = phase_data[i:i+self.batch_size]
            batch_num = (i // self.batch_size) + 1
            total_batches = (len(phase_data) + self.batch_size - 1) // self.batch_size
            
            print(f"\n--- バッチ {batch_num}/{total_batches} 処理中 ---")
            
            # 検証
            is_valid, validation_result = self.validate_batch(batch)
            
            if is_valid:
                self.stats['validation_passes'] += 1
                processed_data.extend(batch)
                
                # 既存データに追加（重複防止用）
                for record in batch:
                    self.existing_names.add(record['person_name'].lower())
                    self.existing_display.add(record['person_name_display'])
            else:
                self.stats['validation_failures'] += 1
                
                # エラー修正
                fixed_batch = self.fix_batch_errors(batch, validation_result)
                
                # 再検証
                if fixed_batch:
                    is_valid, _ = self.validate_batch(fixed_batch)
                    if is_valid:
                        processed_data.extend(fixed_batch)
                        
                        # 既存データに追加
                        for record in fixed_batch:
                            self.existing_names.add(record['person_name'].lower())
                            self.existing_display.add(record['person_name_display'])
            
            # 進捗表示
            print(f"   進捗: {len(processed_data)}/{len(phase_data)}件処理済み")
        
        # チェックポイント保存
        if processed_data:
            self.save_checkpoint(phase_name, processed_data)
        
        # 統計更新
        self.stats['phase_results'][phase_name] = {
            'collected': len(phase_data),
            'processed': len(processed_data),
            'errors': len(phase_data) - len(processed_data)
        }
        
        print(f"\n✅ {phase_name} 完了: {len(processed_data)}件追加")
        
        return processed_data
    
    def run(self):
        """メイン実行"""
        print("\n" + "="*60)
        print("🛡️ Ultra Think Safe Collector")
        print("エラー防止型段階的収集システム")
        print("="*60)
        
        # 既存データ読み込み
        if not self.load_existing_data():
            return None
        
        # バックアップ作成
        backup_file = f"backup_{self.base_file}_{self.timestamp}"
        print(f"\n💾 バックアップ作成中: {backup_file}")
        with open(self.base_file, 'r', encoding='utf-8-sig') as src:
            with open(backup_file, 'w', encoding='utf-8-sig') as dst:
                dst.write(src.read())
        
        # Phase 1実行
        print("\n" + "="*60)
        print("📋 Phase 1: 基盤データ強化")
        print("="*60)
        
        # Phase 1-1: 政治家・経営者
        phase1_1 = self.process_phase("Phase1-1_Politicians", self.collect_phase1_politicians_business)
        self.new_data.extend(phase1_1)
        
        # Phase 1-2: 文化人
        phase1_2 = self.process_phase("Phase1-2_Cultural", self.collect_phase1_cultural)
        self.new_data.extend(phase1_2)
        
        # 最終統合
        print("\n" + "="*60)
        print("🔄 最終統合処理")
        print("="*60)
        
        # 全データ結合
        all_data = self.existing_data + self.new_data
        
        # 最終検証
        print(f"\n🔍 最終検証中（{len(all_data)}件）...")
        final_issues = 0
        for record in all_data:
            if not record.get('person_name', '').strip():
                final_issues += 1
            if not record.get('person_name_display', '').strip():
                final_issues += 1
        
        if final_issues == 0:
            print("✅ 最終検証合格！")
        else:
            print(f"⚠️ {final_issues}件の問題を検出")
        
        # 保存
        print(f"\n💾 最終データ保存中...")
        
        # CSV保存
        with open(self.output_csv, 'w', encoding='utf-8-sig', newline='') as f:
            if all_data:
                writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
                writer.writeheader()
                writer.writerows(all_data)
        
        # JSON保存
        with open(self.output_json, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        
        # 統計更新
        self.stats['added_count'] = len(self.new_data)
        
        # レポート生成
        self.generate_report(all_data)
        
        print("\n" + "="*60)
        print("✅ 処理完了")
        print(f"   - 初期データ: {self.stats['initial_count']}件")
        print(f"   - 追加データ: {self.stats['added_count']}件")
        print(f"   - 最終データ: {len(all_data)}件")
        print(f"   - 出力ファイル: {self.output_csv}")
        print("="*60)
        
        return self.output_csv
    
    def generate_report(self, all_data: List[Dict]):
        """レポート生成"""
        report = f"""# 🛡️ Safe Collection Report

## 📅 実行日時
{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 📊 収集結果

### 全体統計
- **初期データ**: {self.stats['initial_count']}件
- **追加データ**: {self.stats['added_count']}件
- **最終データ**: {len(all_data)}件
- **重複スキップ**: {self.stats['duplicate_count']}件
- **エラー修正**: {self.stats['fixed_count']}件
- **エラースキップ**: {self.stats['error_count']}件

### 検証結果
- **検証合格バッチ**: {self.stats['validation_passes']}
- **検証不合格バッチ**: {self.stats['validation_failures']}
- **成功率**: {self.stats['validation_passes'] / max(1, self.stats['validation_passes'] + self.stats['validation_failures']) * 100:.1f}%

### フェーズ別結果
"""
        
        for phase_name, result in self.stats['phase_results'].items():
            report += f"""
#### {phase_name}
- 収集: {result['collected']}件
- 処理: {result['processed']}件
- エラー: {result['errors']}件
"""
        
        report += f"""
## ✅ 品質保証

### データ品質
- person_name充足率: {sum(1 for r in all_data if r.get('person_name', '').strip()) / len(all_data) * 100:.1f}%
- person_name_display充足率: {sum(1 for r in all_data if r.get('person_name_display', '').strip()) / len(all_data) * 100:.1f}%
- birth_year充足率: {sum(1 for r in all_data if r.get('birth_year', '').strip()) / len(all_data) * 100:.1f}%

## 📁 出力ファイル
- **CSV**: {self.output_csv}
- **JSON**: {self.output_json}
- **チェックポイント**: {self.checkpoint_dir}/

## 🎯 次のステップ

残りのフェーズを実行して、目標の11,211件に到達させます：
- Phase 2: エンタメ系（2,000件）
- Phase 3: スポーツ選手（2,000件）
- Phase 4: 国際的有名人（2,000件）
- Phase 5: 特殊カテゴリ（2,600件）

---
*Safe Collection System*
*Quality First, Errors Zero*
"""
        
        with open(self.report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📝 レポート生成: {self.report_file}")


def main():
    """メイン実行"""
    collector = SafeCollector()
    output_file = collector.run()
    
    if output_file:
        print(f"\n🎊 SafeCollector実行成功！")
        print(f"📁 出力ファイル: {output_file}")
    else:
        print(f"\n❌ SafeCollector実行失敗")
    
    return output_file


if __name__ == "__main__":
    main()