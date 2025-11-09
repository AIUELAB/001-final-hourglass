import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  // 本番ビルド最適化
  build: {
    // ソースマップ生成（本番環境では false を推奨）
    sourcemap: false,

    // チャンク分割戦略
    rollupOptions: {
      output: {
        manualChunks: {
          // React関連を別チャンクに分離
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          // グラフライブラリを別チャンクに分離
          'charts': ['recharts'],
        },
      },
    },

    // チャンクサイズ警告の閾値（KB）
    chunkSizeWarningLimit: 1000,

    // 最小化設定
    minify: 'esbuild', // terserの代わりにesbuildを使用（Vite推奨）
  },

  // プレビューサーバー設定
  preview: {
    port: 5173,
    strictPort: true,
  },

  // 開発サーバー設定
  server: {
    port: 5175,
    strictPort: true,
  },
})
