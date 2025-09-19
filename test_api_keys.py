#!/usr/bin/env python3
"""
APIキー設定のテストスクリプト
"""

import os
import json
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv()

# APIキーの確認
openai_key = os.environ.get('OPENAI_API_KEY', '')
anthropic_key = os.environ.get('ANTHROPIC_API_KEY', '')

print('APIキー確認:')
print(f'OPENAI_API_KEY: {"設定済み" if openai_key else "未設定"} (長さ: {len(openai_key)}文字)')
print(f'ANTHROPIC_API_KEY: {"設定済み" if anthropic_key else "未設定"} (長さ: {len(anthropic_key)}文字)')

# 最初の10文字を表示（デバッグ用）
if openai_key:
    print(f'  OpenAI: {openai_key[:20]}...')
if anthropic_key:
    print(f'  Anthropic: {anthropic_key[:20]}...')

# config/api_config.jsonの確認
config_path = 'config/api_config.json'
if os.path.exists(config_path):
    with open(config_path, 'r') as f:
        config = json.load(f)
    print(f'\nAPI設定ファイル: 存在')
    print(f'  予算設定: ${config.get("api_budget_per_month", 0)}/月')
    print(f'  最大リトライ: {config.get("max_retries", 0)}回')
    print(f'  品質閾値: {config.get("quality_threshold", 0)}')
else:
    print(f'\nAPI設定ファイル: 未作成')

# PremiumEpisodeGeneratorのテスト
print('\n=== PremiumEpisodeGeneratorのロードテスト ===')
try:
    from premium_episode_generator import PremiumEpisodeGenerator
    generator = PremiumEpisodeGenerator()

    print('✅ PremiumEpisodeGenerator初期化成功')
    print(f'  OpenAI クライアント: {"設定済み" if generator.openai_client else "未設定"}')
    print(f'  Anthropic クライアント: {"設定済み" if generator.anthropic_client else "未設定"}')

    if generator.openai_client or generator.anthropic_client:
        print('\n✅ APIキーは正しく認識されています！')
    else:
        print('\n⚠️ APIキーが認識されていません')

except Exception as e:
    print(f'❌ エラー: {e}')