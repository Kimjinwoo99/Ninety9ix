import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import type { AuthUser, UserRole } from '../types';
import { clearAuthToken, getAuthToken, setAuthToken } from '../api/authStorage';
import { fetchMeFromSpring, isSpringConfigured, loginToSpring } from '../api/springApi';

interface AuthContextValue {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  hasRole: (role: UserRole) => boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [token, setToken] = useState<string | null>(getAuthToken());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const boot = async () => {
      if (!isSpringConfigured()) {
        setLoading(false);
        return;
      }
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const me = await fetchMeFromSpring();
        setUser(me);
      } catch {
        clearAuthToken();
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };
    void boot();
  }, [token]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      loading,
      isAuthenticated: Boolean(user && token),
      login: async (username, password) => {
        const result = await loginToSpring({ username, password });
        setAuthToken(result.token);
        setToken(result.token);
        setUser(result.user);
      },
      logout: () => {
        clearAuthToken();
        setToken(null);
        setUser(null);
      },
      hasRole: (role) => user?.role === role,
    }),
    [loading, token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth는 AuthProvider 내부에서 사용해야 합니다.');
  }
  return context;
}
