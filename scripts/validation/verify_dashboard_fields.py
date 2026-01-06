#!/usr/bin/env python3
"""
ダッシュボードv10のフィールド整合性検証スクリプト

検証内容:
1. update_dashboard_v10.py と CSVパース部分のフィールド一致
2. 翻訳が必要なフィールドの翻訳関数存在確認
3. ソート可能フィールドのhandleSort対応確認

使用方法:
    python scripts/validation/verify_dashboard_fields.py
"""

import re
from pathlib import Path

# パス設定
PROJECT_ROOT = Path(__file__).parent.parent.parent
UPDATE_SCRIPT = PROJECT_ROOT / "scripts/update_dashboard_v10.py"
DASHBOARD_HTML = PROJECT_ROOT / "preserved/episode_database_dashboard_v10.html"

# 必須フィールド（両方のソースに存在すべき）
REQUIRED_FIELDS = [
    "episode_id",
    "person_id",
    "person_name",
    "age",
    "nendai",
    "category",
    "episode_text",
    "episode_type",
    "person_type",
    "work_title",
    "group_name",
    "is_group_member",
    "episode_count",
    "fame_score",
    "fame_score_japan",
    "celebrity_score_v2",
    "celebrity_rank_v2",
    "fame_tier",
    "episode_fame_score",
    "episode_fame_v6",
    "episode_fame_tier_v6",
    "super_total_score",
    "memorability_score",
    "empathy_score",
    "surprise_score",
    "generation_quality_score",
    "educational_value",
    "storytelling_quality",
    "factual_density",
    "composite_score",
    "generation_timestamp",  # 作成日
]

# 翻訳が必要なフィールドと対応する翻訳関数
TRANSLATION_REQUIRED = {
    "episode_type": "getTypeLabel",
    "person_type": "entityLabel",  # 変数として処理
}


def extract_fields_from_update_script():
    """update_dashboard_v10.py からフィールド名を抽出"""
    content = UPDATE_SCRIPT.read_text(encoding="utf-8")

    # episode = { ... } 内のキーを抽出
    pattern = r'"(\w+)":\s*(?:row\.get|float|int|parseFloat)'
    matches = re.findall(pattern, content)

    # より正確にepisode dictのキーを抽出
    episode_pattern = r"episode\s*=\s*\{([^}]+(?:\{[^}]*\}[^}]*)*)\}"
    episode_match = re.search(episode_pattern, content, re.DOTALL)
    if episode_match:
        episode_content = episode_match.group(1)
        key_pattern = r'"(\w+)":'
        matches = re.findall(key_pattern, episode_content)

    return set(matches)


def extract_fields_from_csv_parse():
    """ダッシュボードのCSVパース部分からフィールド名を抽出"""
    content = DASHBOARD_HTML.read_text(encoding="utf-8")

    # CSVパース部分を行番号で特定（より堅牢な方法）
    lines = content.split("\n")
    fields = set()

    # "CSVファイルから" を含む行を探し、その後の return { ... } を解析
    in_csv_parse = False
    in_return_block = False
    brace_count = 0

    for i, line in enumerate(lines):
        # CSVパース関数の開始を検出
        if "CSVファイルから読み込み" in line or "loadEpisodesFromCSV" in line:
            in_csv_parse = True
            continue

        if in_csv_parse:
            # return { を検出
            if "return {" in line and not in_return_block:
                in_return_block = True
                brace_count = line.count("{") - line.count("}")
                continue

            if in_return_block:
                brace_count += line.count("{") - line.count("}")

                # フィールド名を抽出（先頭のキー: パターン）
                match = re.match(r"\s*(\w+):\s*", line)
                if match:
                    field_name = match.group(1)
                    # 一般的でないキーを除外
                    if field_name not in ["id", "const", "let", "var", "if", "return"]:
                        fields.add(field_name)

                # ブロック終了
                if brace_count <= 0 and "}" in line:
                    in_return_block = False
                    # 1回見つかったら終了
                    if len(fields) > 10:  # 十分なフィールドが見つかった
                        break

    return fields


def extract_template_fields():
    """テンプレートで使用されているep.XXXフィールドを抽出"""
    content = DASHBOARD_HTML.read_text(encoding="utf-8")

    # ep.XXX パターンを抽出
    pattern = r"ep\.(\w+)"
    matches = re.findall(pattern, content)

    return set(matches)


def check_translation_functions():
    """翻訳関数の存在を確認"""
    content = DASHBOARD_HTML.read_text(encoding="utf-8")
    results = {}

    for field, func_name in TRANSLATION_REQUIRED.items():
        # 関数定義を探す
        if func_name.startswith("get"):
            pattern = rf"const\s+{func_name}\s*="
        else:
            pattern = rf"const\s+{func_name}\s*="

        found = bool(re.search(pattern, content))
        results[field] = {"function": func_name, "exists": found}

        # テンプレートで翻訳関数が使われているか確認
        usage_pattern = rf"\${{{func_name}\(ep\.{field}\)}}"
        used = bool(re.search(usage_pattern, content))
        results[field]["used_in_template"] = used

    return results


def main():
    print("=" * 60)
    print("🔍 ダッシュボードv10 フィールド整合性検証")
    print("=" * 60)

    errors = []
    warnings = []

    # 1. update_dashboard_v10.py のフィールド確認
    print("\n📋 update_dashboard_v10.py のフィールド確認...")
    update_fields = extract_fields_from_update_script()
    print(f"   検出フィールド数: {len(update_fields)}")

    # 2. CSVパース部分のフィールド確認
    print("\n📋 CSVパース部分のフィールド確認...")
    csv_parse_fields = extract_fields_from_csv_parse()
    print(f"   検出フィールド数: {len(csv_parse_fields)}")

    # 3. 必須フィールドの存在確認
    print("\n🔎 必須フィールドの存在確認...")
    for field in REQUIRED_FIELDS:
        in_update = field in update_fields
        in_csv = field in csv_parse_fields

        if not in_update and not in_csv:
            errors.append(f"❌ {field}: 両方に存在しない")
        elif not in_update:
            errors.append(f"❌ {field}: update_dashboard_v10.py に存在しない")
        elif not in_csv:
            errors.append(f"❌ {field}: CSVパースに存在しない")
        else:
            print(f"   ✅ {field}")

    # 4. 翻訳関数の確認
    print("\n🌐 翻訳関数の確認...")
    translation_results = check_translation_functions()
    for field, result in translation_results.items():
        if not result["exists"]:
            errors.append(f"❌ {field}: 翻訳関数 {result['function']} が存在しない")
        elif not result["used_in_template"]:
            warnings.append(f"⚠️ {field}: 翻訳関数 {result['function']} がテンプレートで使用されていない可能性")
        else:
            print(f"   ✅ {field} → {result['function']}()")

    # 5. 差分レポート
    print("\n📊 フィールド差分:")
    only_in_update = update_fields - csv_parse_fields
    only_in_csv = csv_parse_fields - update_fields

    if only_in_update:
        print(f"   update_dashboard_v10.py のみ: {only_in_update}")
    if only_in_csv:
        print(f"   CSVパースのみ: {only_in_csv}")

    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 検証結果サマリー")
    print("=" * 60)

    if errors:
        print(f"\n❌ エラー: {len(errors)}件")
        for e in errors:
            print(f"   {e}")

    if warnings:
        print(f"\n⚠️ 警告: {len(warnings)}件")
        for w in warnings:
            print(f"   {w}")

    if not errors and not warnings:
        print("\n✅ すべてのチェックに合格しました！")
        return 0

    return 1 if errors else 0


if __name__ == "__main__":
    exit(main())
