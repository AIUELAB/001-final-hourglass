#!/bin/bash
# デプロイスクリプト
# 本番環境へのデプロイを自動化

set -e  # エラーで即座に終了

echo "🚀 最期の砂時計 - デプロイスクリプト"
echo "======================================"

# 1. バックエンドのビルド確認
echo ""
echo "📦 1/5: バックエンドの依存関係を確認中..."
cd backend
if [ ! -d "venv" ]; then
    echo "⚠️  仮想環境が見つかりません。作成中..."
    python3 -m venv venv
fi
source venv/bin/activate
pip install -r requirements.txt --quiet
echo "✅ バックエンドの依存関係 OK"

# 2. バックエンドのテスト実行
echo ""
echo "🧪 2/5: バックエンドのテストを実行中..."
pytest tests/ -v --cov=app --cov-report=term-missing
echo "✅ バックエンドのテスト OK"

# 3. フロントエンドのビルド
echo ""
echo "🏗️  3/5: フロントエンドをビルド中..."
cd ../frontend
npm install --quiet
npm run build
echo "✅ フロントエンドのビルド OK"

# 4. フロントエンドのテスト実行
echo ""
echo "🧪 4/5: フロントエンドのテストを実行中..."
npm run test -- --run
echo "✅ フロントエンドのテスト OK"

# 5. ビルド成果物の確認
echo ""
echo "📊 5/5: ビルド成果物を確認中..."
cd ../

if [ -d "frontend/dist" ]; then
    echo "✅ フロントエンドビルド: frontend/dist"
    du -sh frontend/dist
fi

if [ -f "backend/characters.db" ]; then
    echo "✅ データベース: backend/characters.db"
    du -sh backend/characters.db
fi

echo ""
echo "======================================"
echo "✨ デプロイ準備完了！"
echo ""
echo "📝 次のステップ:"
echo "1. バックエンドをRailway/Renderにデプロイ"
echo "2. フロントエンドをVercel/Netlifyにデプロイ"
echo "3. 環境変数を設定"
echo "   - VITE_API_BASE_URL（フロントエンド）"
echo "   - CORS_ORIGINS（バックエンド）"
echo ""
echo "🔗 デプロイガイド: DEPLOYMENT_GUIDE.md を参照"
