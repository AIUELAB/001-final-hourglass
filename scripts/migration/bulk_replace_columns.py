"""
Phase 28: 一括置換スクリプト
日本語カラム名を英語に一括置換

Note: このスクリプトは既に実行済みです（122ファイル、1871箇所置換）
"""

from pathlib import Path

# 置換マップ（元の日本語 → 英語）
REPLACEMENTS = {
    "記憶性スコア": "memorability_score",
    "共感性スコア": "empathy_score",
    "意外性スコア": "surprise_score",
    "生成品質スコア": "generation_quality_score",
    "教育的価値": "educational_value",
    "ストーリー品質": "story_quality",
    "事実密度": "factual_density",
    "象徴性スコア": "iconic_score",
}


def replace_in_file(filepath: Path) -> int:
    """ファイル内の日本語カラム名を置換"""
    try:
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        print(f"  Error reading {filepath}: {e}")
        return 0

    original = content
    count = 0

    for jp, en in REPLACEMENTS.items():
        if jp in content:
            occurrences = content.count(jp)
            content = content.replace(jp, en)
            count += occurrences

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        return count

    return 0


def main():
    project_root = Path(__file__).parent.parent.parent

    # 対象ディレクトリ
    dirs = ["scripts", "src", "tests", "backend"]

    total_files = 0
    total_replacements = 0

    for dir_name in dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            continue

        for filepath in dir_path.rglob("*.py"):
            count = replace_in_file(filepath)
            if count > 0:
                print(f"  {filepath.relative_to(project_root)}: {count} replacements")
                total_files += 1
                total_replacements += count

    print("\n=== Summary ===")
    print(f"Files modified: {total_files}")
    print(f"Total replacements: {total_replacements}")


if __name__ == "__main__":
    main()
