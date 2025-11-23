/**
 * 認証Context
 *
 * アプリケーション全体で認証状態を管理
 */

import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { login as apiLogin, getCurrentUser, logout as apiLogout, UserInfo } from '../api/client';

interface AuthContextType {
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // アプリ起動時に認証状態をチェック
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('auth_token');
      if (token) {
        try {
          const userInfo = await getCurrentUser();
          setUser(userInfo);
        } catch (error) {
          // トークンが無効な場合は削除
          localStorage.removeItem('auth_token');
          setUser(null);
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = async (username: string, password: string): Promise<void> => {
    try {
      await apiLogin(username, password);
      const userInfo = await getCurrentUser();
      setUser(userInfo);
    } catch (error) {
      setUser(null);
      throw error;
    }
  };

  const logout = (): void => {
    apiLogout();
    setUser(null);
  };

  const value: AuthContextType = {
    user,
    isAuthenticated: !!user,
    isLoading,
    login,
    logout,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

/**
 * 認証Contextを使用するカスタムフック
 */
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
