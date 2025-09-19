#!/usr/bin/env python3
"""
Ultra Think エピソード重複削除システム
同一人物・同一年齢のエピソードから最良のものを選定
品質基準：accuracy_score、impact_score、テキストの充実度
"""
import csv
import json
from datetime import datetime
from typing import Dict, List, Tuple
from collections import defaultdict
import hashlib

class EpisodeDuplicateRemover:
    def __init__(self):
        self.stats = {
            'total_episodes': 0,
            'unique_combinations': 0,
            'duplicates_found': 0,
            'duplicates_removed': 0,
            'kept_episodes': 0,
            'errors': 0
        }
        self.duplicate_details = []
        
    def calculate_quality_score(self, episode: Dict) -> float:
        """エピソードの品質スコアを計算"""
        try:
            # 基本スコア（accuracy_score + impact_score）
            accuracy = float(episode.get('accuracy_score', 0))
            impact = float(episode.get('impact_score', 0))
            base_score = (accuracy + impact) / 2
            
            # テキストの充実度スコア
            text_length = len(episode.get('episode_text', ''))
            text_score = min(100, text_length / 10)  # 1000文字で満点
            
            # name_recognitionスコア
            recognition = float(episode.get('name_recognition', 0))
            
            # 総合スコア計算（重み付き平均）
            total_score = (
                base_score * 0.5 +      # accuracy + impact: 50%
                text_score * 0.3 +      # テキスト充実度: 30% 
                recognition * 0.2       # 知名度: 20%
            )
            
            return round(total_score, 2)
            
        except (ValueError, TypeError) as e:
            print(f"  ⚠️ スコア計算エラー: {e}")
            return 0.0
    
    def get_episode_key(self, episode: Dict) -> str:
        """エピソードの一意キーを生成（人物名+年齢）"""
        person_name = episode.get('person_name', '').strip()
        age = str(episode.get('age', '')).strip()
        return f"{person_name}#{age}"
    
    def create_episode_summary(self, episode: Dict) -> str:
        """エピソードの要約情報を作成"""
        return (f"ID: {episode.get('episode_id', 'N/A')}, "
                f"Quality: {self.calculate_quality_score(episode):.1f}, "
                f"Text: {len(episode.get('episode_text', ''))}chars, "
                f"Accuracy: {episode.get('accuracy_score', 'N/A')}, "
                f"Impact: {episode.get('impact_score', 'N/A')}")
    
    def select_best_episode(self, episodes: List[Dict]) -> Dict:
        """複数のエピソードから最良のものを選択"""
        if len(episodes) == 1:
            return episodes[0]
        
        # 各エピソードにスコアを計算
        scored_episodes = []
        for ep in episodes:
            score = self.calculate_quality_score(ep)
            scored_episodes.append((score, ep))
        
        # スコア順でソート（降順）
        scored_episodes.sort(reverse=True, key=lambda x: x[0])
        
        # 重複詳細を記録
        best_episode = scored_episodes[0][1]
        removed_episodes = [ep for _, ep in scored_episodes[1:]]
        
        duplicate_info = {
            'key': self.get_episode_key(best_episode),
            'person_name': best_episode.get('person_name', ''),
            'age': best_episode.get('age', ''),
            'total_duplicates': len(episodes),
            'kept': self.create_episode_summary(best_episode),
            'removed': [self.create_episode_summary(ep) for ep in removed_episodes]
        }
        
        self.duplicate_details.append(duplicate_info)
        self.stats['duplicates_found'] += len(episodes) - 1
        self.stats['duplicates_removed'] += len(episodes) - 1
        
        return best_episode
    
    def process_file(self, input_file: str) -> str:
        """ファイルの重複削除を実行"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"ultra_think_deduplicated_{timestamp}.csv"
        
        print("🔍 Ultra Think エピソード重複削除開始...")
        print(f"  入力: {input_file}")
        print(f"  出力: {output_file}")
        
        # エピソードをキー別にグループ化
        episode_groups = defaultdict(list)
        
        # ファイル読み込み
        with open(input_file, 'r', encoding='utf-8-sig') as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            
            for row_num, row in enumerate(reader, 1):
                self.stats['total_episodes'] += 1
                
                try:
                    key = self.get_episode_key(row)
                    episode_groups[key].append(row)
                    
                    # 進捗表示
                    if row_num % 500 == 0:
                        print(f"  読み込み中... {row_num:,}エピソード処理")
                        
                except Exception as e:
                    print(f"  ⚠️ 読み込みエラー (行{row_num}): {e}")
                    self.stats['errors'] += 1
        
        self.stats['unique_combinations'] = len(episode_groups)
        print(f"  📊 読み込み完了: {self.stats['total_episodes']:,}エピソード")
        print(f"  📊 ユニーク組み合わせ: {self.stats['unique_combinations']:,}件")
        
        # 重複削除とファイル出力
        with open(output_file, 'w', encoding='utf-8-sig', newline='') as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            
            processed = 0
            for key, episodes in episode_groups.items():
                processed += 1
                
                if len(episodes) > 1:
                    # 重複がある場合は最良のものを選択
                    best_episode = self.select_best_episode(episodes)
                    writer.writerow(best_episode)
                else:
                    # 重複がない場合はそのまま保持
                    writer.writerow(episodes[0])
                
                self.stats['kept_episodes'] += 1
                
                # 進捗表示
                if processed % 100 == 0:
                    print(f"  処理中... {processed:,}/{self.stats['unique_combinations']:,}組み合わせ完了")
        
        self.create_report(timestamp, output_file)
        return output_file
    
    def create_report(self, timestamp: str, output_file: str):
        """重複削除レポート作成"""
        # 詳細レポート用JSONファイル
        details_file = f"ultra_think_deduplication_details_{timestamp}.json"
        with open(details_file, 'w', encoding='utf-8') as f:
            json.dump(self.duplicate_details, f, ensure_ascii=False, indent=2)
        
        # Markdownレポート作成
        report = f"""# 🔍 Ultra Think エピソード重複削除レポート

## 📅 実行情報
- 実行日時: {datetime.now().strftime("%Y年%m月%d日 %H:%M:%S")}
- 入力ファイル: ultra_think_perfect_20250827_043032.csv
- 出力ファイル: {output_file}
- 詳細ログ: {details_file}

## 📊 重複削除統計
- 元エピソード数: {self.stats['total_episodes']:,}件
- ユニーク組み合わせ数: {self.stats['unique_combinations']:,}件
- 重複発見数: {self.stats['duplicates_found']:,}件
- 重複削除数: {self.stats['duplicates_removed']:,}件
- 保持エピソード数: {self.stats['kept_episodes']:,}件
- エラー数: {self.stats['errors']}件

## 📈 削減効果
- 削減率: {(self.stats['duplicates_removed'] / max(self.stats['total_episodes'], 1)) * 100:.1f}%
- 圧縮率: {(self.stats['kept_episodes'] / max(self.stats['total_episodes'], 1)) * 100:.1f}%

## 🎯 品質基準
### 選定基準（重み付き）
1. **基本スコア (50%)**: (accuracy_score + impact_score) / 2
2. **テキスト充実度 (30%)**: エピソードテキストの長さ
3. **知名度 (20%)**: name_recognitionスコア

### 品質スコア分布
"""
        
        # 品質スコア分布の計算
        if self.duplicate_details:
            quality_scores = []
            for detail in self.duplicate_details:
                # kept episodeから品質スコアを推定（kept文字列からパース）
                kept_info = detail['kept']
                if 'Quality: ' in kept_info:
                    try:
                        score_part = kept_info.split('Quality: ')[1].split(',')[0]
                        quality_scores.append(float(score_part))
                    except:
                        pass
            
            if quality_scores:
                avg_score = sum(quality_scores) / len(quality_scores)
                max_score = max(quality_scores)
                min_score = min(quality_scores)
                
                report += f"""
- 平均品質スコア: {avg_score:.1f}点
- 最高品質スコア: {max_score:.1f}点
- 最低品質スコア: {min_score:.1f}点
"""
        
        report += f"""
## 📝 重複パターン分析
- 重複が発見された組み合わせ: {len([d for d in self.duplicate_details if d['total_duplicates'] > 1])}件
- 最大重複数: {max([d['total_duplicates'] for d in self.duplicate_details], default=1)}件

## 🔧 処理詳細
### 重複判定ロジック
- 重複キー: `person_name + "#" + age`
- 同一人物の同一年齢エピソードを重複と判定

### 選定ロジック
1. 各エピソードの品質スコアを計算
2. スコアが最も高いエピソードを保持
3. その他のエピソードを削除

## ✅ 品質保証
- 全フィールドの整合性保持
- 文字エンコーディング: UTF-8 with BOM
- 元データの品質スコア計算による最適選択
- 削除詳細の完全ログ保存

## 📁 出力ファイル
- **メインデータ**: {output_file}
- **詳細ログ**: {details_file}
"""
        
        report_file = f"ULTRA_THINK_DEDUPLICATION_REPORT_{timestamp}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n✨ Ultra Think エピソード重複削除完了!")
        print(f"  📊 元エピソード: {self.stats['total_episodes']:,}件")
        print(f"  📊 保持エピソード: {self.stats['kept_episodes']:,}件")
        print(f"  📊 削除エピソード: {self.stats['duplicates_removed']:,}件")
        print(f"  📊 削減率: {(self.stats['duplicates_removed'] / max(self.stats['total_episodes'], 1)) * 100:.1f}%")
        print(f"  📁 出力: {output_file}")
        print(f"  📋 レポート: {report_file}")
        print(f"  📄 詳細ログ: {details_file}")

def main():
    remover = EpisodeDuplicateRemover()
    input_file = "ultra_think_perfect_20250827_043032.csv"
    
    try:
        output_file = remover.process_file(input_file)
        print("\n🎉 重複削除成功！品質の高いエピソードのみが保持されました。")
        return output_file
    except Exception as e:
        print(f"\n❌ 重複削除エラー: {e}")
        raise

if __name__ == "__main__":
    main()