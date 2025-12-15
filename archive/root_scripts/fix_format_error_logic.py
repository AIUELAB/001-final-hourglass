#!/usr/bin/env python3
"""
PDCAガーディアンのFORMAT_ERRORチェックロジックを修正
"""

import re

def create_format_error_fix():
    """FORMAT_ERRORチェックロジックの修正版を生成"""

    fix_code = '''
        # エピソードフォーマットチェック（修正版）
        # 許容されるフォーマット：
        # 1. あなたと同じX歳のとき、名前（X歳）は
        # 2. あなたと同じX歳のとき、名前は（年齢表記なしも許容）
        # 3. 実はあなたと同じX歳のとき、名前は（「実は」が先頭も許容）

        standard_prefix_with_age = f"あなたと同じ{age}歳のとき、{person_name_display}は"
        standard_prefix_without_age = f"あなたと同じ{age}歳のとき、{person_name}は"

        # 「実は」で始まるパターン
        prefix_with_jitsuha_age = f"実はあなたと同じ{age}歳のとき、{person_name_display}は"
        prefix_with_jitsuha_no_age = f"実はあなたと同じ{age}歳のとき、{person_name}は"

        # カタカナ表記パターン
        katakana_matches = re.findall(r'[ァ-ヶー]+', person_name)
        alt_prefixes = []
        if katakana_matches:
            for katakana in katakana_matches:
                alt_prefixes.append(f"あなたと同じ{age}歳のとき、{katakana}は")
                alt_prefixes.append(f"実はあなたと同じ{age}歳のとき、{katakana}は")

        # すべての許容パターンをリスト化
        all_valid_prefixes = [
            standard_prefix_with_age,
            standard_prefix_without_age,
            prefix_with_jitsuha_age,
            prefix_with_jitsuha_no_age
        ] + alt_prefixes

        # エピソードが許容されるフォーマットで始まっているかチェック
        if not any(episode_text.startswith(prefix) for prefix in all_valid_prefixes):
            violations.append({
                'type': 'FORMAT_ERROR',
                'message': f"エピソードが標準フォーマットで始まっていません。「{standard_prefix_with_age}」で始めてください。",
                'severity': 'high'
            })
'''
    return fix_code

# PDCAガーディアンのチェックロジックを修正するパッチファイル
patch_content = """
--- a/pdca_guardian.py
+++ b/pdca_guardian.py
@@ -1642,21 +1642,45 @@ class PDCAGuardian:
         violations = []

         # エピソードフォーマットチェック
-        standard_prefix = f"あなたと同じ{age}歳のとき、{person_name_display}は"
+        # 修正版: 複数のフォーマットを許容
+        # 1. あなたと同じX歳のとき、名前（X歳）は
+        # 2. あなたと同じX歳のとき、名前は（年齢表記なしも許容）
+        # 3. 実はあなたと同じX歳のとき、名前は（「実は」が先頭も許容）
+
+        # person_nameを抽出（年齢表記を除去）
+        person_name = person_name_display.split('（')[0] if '（' in person_name_display else person_name_display
+
+        standard_prefix_with_age = f"あなたと同じ{age}歳のとき、{person_name_display}は"
+        standard_prefix_without_age = f"あなたと同じ{age}歳のとき、{person_name}は"
+
+        # 「実は」で始まるパターン
+        prefix_with_jitsuha_age = f"実はあなたと同じ{age}歳のとき、{person_name_display}は"
+        prefix_with_jitsuha_no_age = f"実はあなたと同じ{age}歳のとき、{person_name}は"

-        # エピソードが標準フォーマットで始まっているかチェック
-        if not episode_text.startswith(standard_prefix):
-            # 代替フォーマットの許容（カタカナ表記など）
-            katakana_matches = re.findall(r'[ァ-ヶー]+', person_name_display)
-            alt_prefixes = [f"あなたと同じ{age}歳のとき、{katakana}は" for katakana in katakana_matches]
-
-            # いずれのフォーマットでも始まっていない場合
-            if not any(episode_text.startswith(prefix) for prefix in alt_prefixes):
-                violations.append({
-                    'type': 'FORMAT_ERROR',
-                    'message': f"エピソードが標準フォーマットで始まっていません。「{standard_prefix}」で始めてください。",
-                    'severity': 'high'
-                })
+        # カタカナ表記パターン
+        katakana_matches = re.findall(r'[ァ-ヶー]+', person_name)
+        alt_prefixes = []
+        if katakana_matches:
+            for katakana in katakana_matches:
+                alt_prefixes.append(f"あなたと同じ{age}歳のとき、{katakana}は")
+                alt_prefixes.append(f"実はあなたと同じ{age}歳のとき、{katakana}は")
+
+        # すべての許容パターンをリスト化
+        all_valid_prefixes = [
+            standard_prefix_with_age,
+            standard_prefix_without_age,
+            prefix_with_jitsuha_age,
+            prefix_with_jitsuha_no_age
+        ] + alt_prefixes
+
+        # エピソードが許容されるフォーマットで始まっているかチェック
+        if not any(episode_text.startswith(prefix) for prefix in all_valid_prefixes):
+            violations.append({
+                'type': 'FORMAT_ERROR',
+                'message': f"エピソードが標準フォーマットで始まっていません。「{standard_prefix_with_age}」で始めてください。",
+                'severity': 'high'
+            })

         return violations
"""

print("FORMAT_ERRORチェックロジックの修正パッチを生成しました")
print("\n修正内容:")
print("1. person_name_displayから名前部分を抽出")
print("2. 年齢表記あり/なし両方のパターンを許容")
print("3. 「実は」で始まるパターンを許容")
print("4. カタカナ表記のバリエーションも考慮")

# パッチファイルを保存
with open('format_error_fix.patch', 'w', encoding='utf-8') as f:
    f.write(patch_content)

print("\nパッチファイル作成: format_error_fix.patch")
print("\n適用方法:")
print("patch pdca_guardian.py < format_error_fix.patch")
print("\nまたは手動で修正箇所を適用してください")
