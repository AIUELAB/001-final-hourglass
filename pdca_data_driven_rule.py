#!/usr/bin/env python3
"""
PDCAガーディアンルール: データ駆動開発の厳守
仮定駆動によるバグを二度と起こさないための必須ルール
"""

PDCA_RULE_099 = {
    "rule_id": "DATA_DRIVEN_099",
    "title": "データ駆動開発の絶対遵守",
    "severity": "CRITICAL",
    "created_date": "2025-09-15",
    "created_by": "Wikipedia判定バグからの教訓",

    "problem_statement": """
    【発生した問題】
    - 存在しないフィールド名を仮定してコードを書いた（has_wikipedia）
    - 実際のデータ構造を確認せずに推測でフィールド名を決めた
    - 削除済みフィールドを参照していた（accuracy_score, news_score）
    - フィールドの値を英語と仮定したが実際は日本語だった
    - 結果：2,443件のWikipedia存在データが0点になった
    """,

    "mandatory_checks": [
        "1. データ処理前に必ずdf.columns.tolist()で全カラムを確認",
        "2. フィールドの値はvalue_counts()やhead()で実際の内容を確認",
        "3. 存在確認：'field_name' in df.columnsで必ず検証",
        "4. 型確認：df.dtypesで各フィールドの型を確認",
        "5. サンプル実行：最初の5-10件で動作確認してから全件処理"
    ],

    "prohibited_actions": [
        "❌ フィールド名を推測で決める",
        "❌ 一般的な命名規則から仮定する",
        "❌ データの中身を見ずにコードを書く",
        "❌ 英語前提で値を判定する（日本語データの可能性）",
        "❌ 削除済みカラムの存在を仮定する"
    ],

    "correct_workflow": """
    # 正しいワークフロー
    1. データ読み込み
       df = pd.read_csv('file.csv')

    2. 構造確認（必須）
       print(df.columns.tolist())
       print(df.dtypes)
       print(df.head())

    3. フィールド検証（必須）
       if 'target_field' in df.columns:
           print(df['target_field'].value_counts())

    4. サンプル実行（必須）
       sample_df = df.head(10)
       # サンプルで関数をテスト

    5. 全件処理
       # 検証済みのコードで全件処理
    """,

    "verification_checklist": [
        "□ df.columns.tolist()でカラム名を確認した",
        "□ 使用する全フィールドの存在を確認した",
        "□ フィールドの実際の値を確認した",
        "□ 日本語/英語の区別を確認した",
        "□ サンプルデータで動作確認した",
        "□ エラーケースを想定した"
    ],

    "examples": {
        "wrong": """
        # ❌ 間違い：仮定駆動
        if row.get('has_wikipedia'):  # フィールドの存在を仮定
            return True
        """,

        "correct": """
        # ✅ 正解：データ駆動
        # 事前に確認：'wikipedia_status' in df.columns
        # 値も確認：df['wikipedia_status'].value_counts()
        if row.get('wikipedia_status') == '存在':
            return True
        """
    },

    "monitoring": {
        "trigger_keywords": ["get(", "row[", "df[", ".get('", "columns"],
        "review_required": True,
        "auto_validation": True
    }
}

def validate_data_driven_approach(code_string):
    """コードがデータ駆動アプローチに従っているか検証"""

    violations = []

    # チェック1: カラム確認なしでget()を使用
    if "row.get('" in code_string and "columns" not in code_string:
        violations.append("カラム存在確認なしでrow.get()を使用")

    # チェック2: 仮定的なフィールド名
    suspicious_fields = ['has_', 'is_', 'should_', 'can_']
    for field in suspicious_fields:
        if f"'{field}" in code_string:
            violations.append(f"仮定的なフィールド名'{field}'の使用")

    # チェック3: 英語前提の文字列比較
    if "'champion'" in code_string or "'winner'" in code_string:
        violations.append("英語前提の文字列比較（日本語の可能性）")

    return violations

if __name__ == "__main__":
    print("=" * 60)
    print("PDCAガーディアンルール DATA_DRIVEN_099")
    print("データ駆動開発の絶対遵守")
    print("=" * 60)
    print()
    print("【教訓】")
    print("仮定ではなく、実際のデータを見てコードを書く")
    print()
    print("【チェックリスト】")
    for check in PDCA_RULE_099["verification_checklist"]:
        print(check)
