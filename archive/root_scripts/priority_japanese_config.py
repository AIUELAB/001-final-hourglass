#!/usr/bin/env python3
"""
優先度レベルの日本語表示設定
CRITICAL, HIGH, MEDIUM, LOW を日本語で表示するための設定
"""

# 優先度の日本語マッピング
PRIORITY_JAPANESE = {
    "CRITICAL": "最重要",
    "HIGH": "重要",
    "MEDIUM": "中程度",
    "LOW": "軽微"
}

# 優先度の日本語説明
PRIORITY_DESCRIPTIONS = {
    "CRITICAL": "即座に処理を停止すべき最重要問題",
    "HIGH": "早急に対処が必要な重要な問題",
    "MEDIUM": "改善が推奨される中程度の問題",
    "LOW": "情報レベルの軽微な問題"
}

# 優先度の色設定（HTMLやターミナル表示用）
PRIORITY_COLORS = {
    "CRITICAL": "#dc3545",  # 赤
    "HIGH": "#ffc107",      # 黄色
    "MEDIUM": "#17a2b8",    # 青
    "LOW": "#6c757d"        # グレー
}

# 優先度のアイコン
PRIORITY_ICONS = {
    "CRITICAL": "🚨",
    "HIGH": "⚠️",
    "MEDIUM": "ℹ️",
    "LOW": "💡"
}

def get_japanese_priority(priority: str) -> str:
    """英語の優先度を日本語に変換"""
    return PRIORITY_JAPANESE.get(priority.upper(), priority)

def get_priority_display(priority: str, with_icon: bool = True) -> str:
    """優先度の表示文字列を取得"""
    jp = PRIORITY_JAPANESE.get(priority.upper(), priority)
    if with_icon:
        icon = PRIORITY_ICONS.get(priority.upper(), "")
        return f"{icon} {jp}"
    return jp

def get_priority_html(priority: str) -> str:
    """HTML用の優先度表示を取得"""
    jp = PRIORITY_JAPANESE.get(priority.upper(), priority)
    color = PRIORITY_COLORS.get(priority.upper(), "#666")
    icon = PRIORITY_ICONS.get(priority.upper(), "")
    return f'<span style="color: {color}; font-weight: bold;">{icon} {jp}</span>'

# テスト用
if __name__ == "__main__":
    print("優先度の日本語表示テスト:\n")

    for eng, jp in PRIORITY_JAPANESE.items():
        print(f"{eng:10} → {jp}")
        print(f"  説明: {PRIORITY_DESCRIPTIONS[eng]}")
        print(f"  表示: {get_priority_display(eng)}")
        print()
