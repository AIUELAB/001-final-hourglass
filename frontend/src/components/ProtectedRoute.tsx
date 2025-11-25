/**
 * 保護されたルート
 *
 * 認証済みユーザーのみアクセス可能なルートをラップ
 */

import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: 'admin' | 'editor' | 'viewer';
}

/**
 * 認証が必要なルートを保護
 *
 * @param children - ラップする子コンポーネント
 * @param requiredRole - 必要なロール（オプション）
 */
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children, requiredRole }) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  // ローディング中は何も表示しない
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-600">読み込み中...</div>
      </div>
    );
  }

  // 未認証の場合はログインページにリダイレクト
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // ロール要件がある場合はチェック
  if (requiredRole && user) {
    const roleHierarchy = {
      admin: 3,
      editor: 2,
      viewer: 1,
    };

    const userRoleLevel = roleHierarchy[user.role];
    const requiredRoleLevel = roleHierarchy[requiredRole];

    // ユーザーのロールが要件を満たさない場合
    if (userRoleLevel < requiredRoleLevel) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100">
          <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
            <h2 className="text-2xl font-bold text-center text-red-600 mb-4">
              アクセス権限がありません
            </h2>
            <p className="text-gray-700 text-center mb-6">
              このページにアクセスするには、{requiredRole} 権限が必要です。
            </p>
            <p className="text-gray-600 text-center text-sm">
              現在のロール: {user.role}
            </p>
          </div>
        </div>
      );
    }
  }

  return <>{children}</>;
};

export default ProtectedRoute;
