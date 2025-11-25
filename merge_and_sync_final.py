#!/usr/bin/env python3
"""
最終的なデータ統合とGoogle Sheets同期
1. 拡張されたname_recognition (0-100,000)
2. 実際のGoogle検索結果数
3. Google Sheetsへの同期
"""

import pandas as pd
import numpy as np
from datetime import datetime
import json
import os
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import time

def merge_all_data():
    """すべてのデータを統合"""
    print("=" * 60)
    print("📊 最終データ統合処理")
    print("=" * 60)

    # 1. 拡張されたname_recognitionデータを読み込み
    expanded_file = 'ultra_think_expanded_recognition_20250915_142615.csv'
    print(f"\n📂 拡張データ読み込み: {expanded_file}")
    df_expanded = pd.read_csv(expanded_file)
    print(f"  ✅ {len(df_expanded)}件")

    # 2. 検索結果が含まれたデータを読み込み
    search_file = 'ultra_think_with_search_counts_20250915_140948.csv'
    print(f"\n📂 検索結果データ読み込み: {search_file}")
    df_search = pd.read_csv(search_file)
    print(f"  ✅ {len(df_search)}件")

    # 3. person_idでマージ
    print("\n🔄 データ統合中...")

    # 検索結果から必要なカラムを抽出
    search_columns = ['person_id', 'search_result_count', 'search_query',
                     'search_timestamp', 'search_source']
    df_search_subset = df_search[search_columns].copy()

    # マージ
    df_final = df_expanded.merge(df_search_subset, on='person_id', how='left', suffixes=('', '_new'))

    # search_result_countの更新（実データがある場合は上書き）
    if 'search_result_count_new' in df_final.columns:
        mask = df_final['search_result_count_new'].notna() & (df_final['search_result_count_new'] > 0)
        df_final.loc[mask, 'search_result_count'] = df_final.loc[mask, 'search_result_count_new']
        df_final = df_final.drop('search_result_count_new', axis=1)

    print(f"  ✅ 統合完了: {len(df_final)}件")

    # 統計表示
    show_statistics(df_final)

    return df_final

def show_statistics(df):
    """統計情報を表示"""
    print("\n📊 最終統計:")

    # name_recognition (0-100,000)
    print("\n🎯 name_recognition (拡張版 0-100,000):")
    print(f"  最大値: {df['name_recognition'].max():,.2f}")
    print(f"  平均値: {df['name_recognition'].mean():,.2f}")
    print(f"  中央値: {df['name_recognition'].median():,.2f}")

    # search_result_count
    real_search = df[df['search_source'] == 'serpapi']
    if len(real_search) > 0:
        print(f"\n🔍 Google検索結果数 (実データ):")
        print(f"  取得件数: {len(real_search)}件")
        print(f"  最大値: {real_search['search_result_count'].max():,}")
        print(f"  平均値: {real_search['search_result_count'].mean():,.0f}")
        print(f"  中央値: {real_search['search_result_count'].median():,.0f}")

    # トップ10
    print("\n🏆 総合トップ10 (name_recognition):")
    top10 = df.nlargest(10, 'name_recognition')[['person_name_display', 'name_recognition',
                                                  'search_result_count', 'category']]
    for i, (_, row) in enumerate(top10.iterrows(), 1):
        search_count = f"{row['search_result_count']:,}" if pd.notna(row['search_result_count']) else "N/A"
        print(f"  {i:2d}. {row['person_name_display']:20s}: "
              f"{row['name_recognition']:,.0f}点 "
              f"(検索: {search_count}件)")

def sync_to_sheets(df):
    """Google Sheetsに同期"""
    print("\n" + "=" * 60)
    print("📤 Google Sheets同期処理")
    print("=" * 60)

    # 認証情報読み込み
    credentials_file = 'key/credentials.json'
    if not os.path.exists(credentials_file):
        print(f"❌ 認証ファイルが見つかりません: {credentials_file}")
        return False

    try:
        # Google Sheets API初期化
        creds = Credentials.from_service_account_file(
            credentials_file,
            scopes=['https://www.googleapis.com/auth/spreadsheets']
        )
        service = build('sheets', 'v4', credentials=creds)

        # sheets_config.jsonから設定読み込み
        with open('sheets_config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)

        spreadsheet_id = config['spreadsheet_id']

        # 新しいシート名を生成
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        sheet_name = f"Final Integrated {timestamp}"

        print(f"📋 スプレッドシートID: {spreadsheet_id}")
        print(f"📝 シート名: {sheet_name}")

        # 新しいシートを作成
        request_body = {
            'requests': [{
                'addSheet': {
                    'properties': {
                        'title': sheet_name,
                        'gridProperties': {
                            'rowCount': len(df) + 1,
                            'columnCount': len(df.columns)
                        }
                    }
                }
            }]
        }

        response = service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=request_body
        ).execute()

        sheet_id = response['replies'][0]['addSheet']['properties']['sheetId']
        print(f"✅ 新しいシート作成: ID {sheet_id}")

        # データ準備
        values = [df.columns.tolist()]  # ヘッダー
        for _, row in df.iterrows():
            row_values = []
            for val in row.values:
                if pd.isna(val):
                    row_values.append('')
                elif isinstance(val, (int, float)):
                    row_values.append(val)
                else:
                    row_values.append(str(val))
            values.append(row_values)

        # データ書き込み
        range_name = f"{sheet_name}!A1"
        body = {'values': values}

        result = service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='USER_ENTERED',
            body=body
        ).execute()

        print(f"✅ {result.get('updatedCells')}セル更新完了")

        # フォーマット設定
        format_requests = []

        # ヘッダー行を太字に
        format_requests.append({
            'repeatCell': {
                'range': {
                    'sheetId': sheet_id,
                    'startRowIndex': 0,
                    'endRowIndex': 1
                },
                'cell': {
                    'userEnteredFormat': {
                        'textFormat': {'bold': True},
                        'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                    }
                },
                'fields': 'userEnteredFormat(textFormat,backgroundColor)'
            }
        })

        # 条件付き書式（name_recognition）
        format_requests.append({
            'addConditionalFormatRule': {
                'rule': {
                    'ranges': [{
                        'sheetId': sheet_id,
                        'startColumnIndex': df.columns.get_loc('name_recognition'),
                        'endColumnIndex': df.columns.get_loc('name_recognition') + 1,
                        'startRowIndex': 1
                    }],
                    'gradientRule': {
                        'minpoint': {
                            'color': {'red': 1, 'green': 0.8, 'blue': 0.8},
                            'type': 'MIN'
                        },
                        'maxpoint': {
                            'color': {'red': 0.2, 'green': 0.8, 'blue': 0.2},
                            'type': 'MAX'
                        }
                    }
                }
            }
        })

        # フォーマット適用
        if format_requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={'requests': format_requests}
            ).execute()
            print("✅ フォーマット設定完了")

        # URLを表示
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit#gid={sheet_id}"
        print(f"\n🌐 スプレッドシートURL:")
        print(f"  {sheet_url}")

        # config更新
        config['latest_sync'] = datetime.now().isoformat()
        config['latest_sheet_name'] = sheet_name
        config['latest_sheet_id'] = sheet_id
        config['final_integrated'] = True

        with open('sheets_config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        print(f"❌ エラー: {e}")
        return False

def main():
    # データ統合
    df_final = merge_all_data()

    # 保存
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    output_file = f'ultra_think_FINAL_INTEGRATED_{timestamp}.csv'

    # UTF-8 BOMで保存
    with open(output_file, 'w', encoding='utf-8-sig') as f:
        df_final.to_csv(f, index=False)

    print(f"\n💾 最終データ保存: {output_file}")

    # Google Sheets同期
    if sync_to_sheets(df_final):
        print("\n✅ すべての処理が完了しました！")

        # ブラウザで開く
        os.system('open "https://docs.google.com/spreadsheets/d/1G0ec3d5DHGiahLetsqey9W23HGFOn2tkEacsFd5ZSps"')
    else:
        print("\n⚠️ Google Sheets同期に失敗しました")

if __name__ == "__main__":
    main()
