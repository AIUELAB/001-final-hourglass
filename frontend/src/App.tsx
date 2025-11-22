/**
 * メインアプリケーション
 */

import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { Statistics } from './pages/Statistics';

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        {/* ヘッダー */}
        <header className="bg-white shadow">
          <div className="container mx-auto px-4 py-6">
            <div className="flex items-center justify-between">
              <Link to="/" className="flex items-center space-x-3">
                <span className="text-3xl">⏳</span>
                <h1 className="text-2xl font-bold text-gray-900">
                  Final Hourglass
                </h1>
              </Link>
              <nav className="flex space-x-6">
                <Link
                  to="/"
                  className="text-gray-700 hover:text-blue-600 font-medium transition-colors"
                >
                  統計
                </Link>
              </nav>
            </div>
          </div>
        </header>

        {/* メインコンテンツ */}
        <main>
          <Routes>
            <Route path="/" element={<Statistics />} />
          </Routes>
        </main>

        {/* フッター */}
        <footer className="bg-white border-t mt-12">
          <div className="container mx-auto px-4 py-6">
            <p className="text-center text-gray-600">
              © 2025 Final Hourglass - 最期の砂時計
            </p>
          </div>
        </footer>
      </div>
    </BrowserRouter>
  );
}

export default App;
