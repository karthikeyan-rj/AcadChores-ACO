'use client';

import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react';
import { api, setAuthFailureHandler } from '@/lib/api';

interface User {
  id: string;
  email: string;
  name: string;
  avatar_url?: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, name: string, password: string) => Promise<void>;
  loginWithGoogle: (credential: string) => Promise<void>;
  logout: () => void;
}

import { getBackendUrl } from '@/lib/config';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

const BACKEND_URL = getBackendUrl();

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const wsCloseRefs = useRef<Set<() => void>>(new Set());

  const logout = useCallback(() => {
    wsCloseRefs.current.forEach((close) => {
      try { close(); } catch {}
    });
    wsCloseRefs.current.clear();
    localStorage.removeItem('aco_token');
    localStorage.removeItem('aco_user');
    setToken(null);
    setUser(null);
  }, []);

  useEffect(() => {
    setAuthFailureHandler(() => {
      localStorage.removeItem('aco_token');
      localStorage.removeItem('aco_user');
      setToken(null);
      setUser(null);
    });
    return () => setAuthFailureHandler(null);
  }, []);

  useEffect(() => {
    const storedToken = localStorage.getItem('aco_token');
    const storedUser = localStorage.getItem('aco_user');

    if (!storedToken || !storedUser) {
      setLoading(false);
      return;
    }

    let parsedUser: User;
    try {
      parsedUser = JSON.parse(storedUser);
    } catch {
      localStorage.removeItem('aco_token');
      localStorage.removeItem('aco_user');
      setLoading(false);
      return;
    }

    setToken(storedToken);
    setUser(parsedUser);

    api.me(storedToken)
      .then((data: any) => {
        const freshUser: User = {
          id: data.id || data._id,
          email: data.email,
          name: data.name,
          avatar_url: data.avatar_url,
          role: data.role,
        };
        setUser(freshUser);
        localStorage.setItem('aco_user', JSON.stringify(freshUser));
      })
      .catch(() => {
        localStorage.removeItem('aco_token');
        localStorage.removeItem('aco_user');
        setToken(null);
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const saveAuth = (accessToken: string, userData: User) => {
    localStorage.setItem('aco_token', accessToken);
    localStorage.setItem('aco_user', JSON.stringify(userData));
    setToken(accessToken);
    setUser(userData);
  };

  const login = async (email: string, password: string) => {
    const res = await fetch(`${BACKEND_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    saveAuth(data.access_token, data.user);
  };

  const register = async (email: string, name: string, password: string) => {
    const res = await fetch(`${BACKEND_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, name, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Registration failed');
    }
    const data = await res.json();
    saveAuth(data.access_token, data.user);
  };

  const loginWithGoogle = async (credential: string) => {
    const res = await fetch(`${BACKEND_URL}/api/v1/auth/google`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ credential }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Google login failed');
    }
    const data = await res.json();
    saveAuth(data.access_token, data.user);
  };

  return (
    <AuthContext.Provider value={{ user, token, loading, login, register, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
