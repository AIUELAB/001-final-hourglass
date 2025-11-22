import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { Statistics } from './pages/Statistics'
import { CharacterList } from './pages/CharacterList'
import { CharacterDetail } from './pages/CharacterDetail'
import { FameRanking } from './pages/FameRanking'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        {/* ヘッダーナビゲーション */}
        <nav className="bg-gradient-to-r from-blue-600 to-purple-600 text-white shadow-lg">
          <div className="container mx-auto px-4">
            <div className="flex items-center justify-between h-16">
              <div className="flex items-center space-x-8">
                <h1 className="text-2xl font-bold">
                  ⏳ 最期の砂時計 v2
                </h1>
                <div className="flex space-x-4">
                  <Link
                    to="/"
                    className="px-4 py-2 rounded-lg hover:bg-white/20 transition-colors"
                  >
                    📊 統計
                  </Link>
                  <Link
                    to="/characters"
                    className="px-4 py-2 rounded-lg hover:bg-white/20 transition-colors"
                  >
                    📚 キャラクター一覧
                  </Link>
                  <Link
                    to="/ranking"
                    className="px-4 py-2 rounded-lg hover:bg-white/20 transition-colors"
                  >
                    🏆 有名度ランキング
                  </Link>
                </div>
              </div>
              <div className="text-sm opacity-90">
                エピソードデータベース
              </div>
            </div>
          </div>
        </nav>

        {/* メインコンテンツ */}
        <Routes>
          <Route path="/" element={<Statistics />} />
          <Route path="/characters" element={<CharacterList />} />
          <Route path="/characters/:id" element={<CharacterDetail />} />
          <Route path="/ranking" element={<FameRanking />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}

export default App
