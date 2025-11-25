import { Routes, Route, Link, useNavigate } from 'react-router-dom'
import { Statistics } from './pages/Statistics'
import { CharacterList } from './pages/CharacterList'
import { CharacterDetail } from './pages/CharacterDetail'
import { FameRanking } from './pages/FameRanking'
import { Analytics } from './pages/Analytics'
import { AdvancedSearch } from './pages/AdvancedSearch'
import { DataManagement } from './pages/DataManagement'
import Login from './pages/Login'
import ProtectedRoute from './components/ProtectedRoute'
import { useAuth } from './contexts/AuthContext'

function App() {
  const { isAuthenticated, user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
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
                    to="/analytics"
                    className="px-4 py-2 rounded-lg hover:bg-white/20 transition-colors"
                  >
                    📈 7軸分析
                  </Link>
                  <Link
                    to="/search"
                    className="px-4 py-2 rounded-lg hover:bg-white/20 transition-colors"
                  >
                    🔍 高度な検索
                  </Link>
                  <Link
                    to="/management"
                    className="px-4 py-2 rounded-lg hover:bg-white/20 transition-colors"
                  >
                    🛠️ データ管理
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
              <div className="flex items-center space-x-4">
                {isAuthenticated && user ? (
                  <>
                    <div className="text-sm">
                      <div className="font-medium">{user.full_name}</div>
                      <div className="text-xs opacity-75">{user.role}</div>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="px-4 py-2 bg-white/20 rounded-lg hover:bg-white/30 transition-colors text-sm"
                    >
                      ログアウト
                    </button>
                  </>
                ) : (
                  <Link
                    to="/login"
                    className="px-4 py-2 bg-white/20 rounded-lg hover:bg-white/30 transition-colors text-sm"
                  >
                    ログイン
                  </Link>
                )}
              </div>
            </div>
          </div>
        </nav>

        {/* メインコンテンツ */}
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<Statistics />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/search" element={<AdvancedSearch />} />
          <Route
            path="/management"
            element={
              <ProtectedRoute requiredRole="editor">
                <DataManagement />
              </ProtectedRoute>
            }
          />
          <Route path="/characters" element={<CharacterList />} />
          <Route path="/characters/:id" element={<CharacterDetail />} />
          <Route path="/ranking" element={<FameRanking />} />
        </Routes>
      </div>
  )
}

export default App
