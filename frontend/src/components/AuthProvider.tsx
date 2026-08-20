"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  clearAuth,
  getMe,
  getToken,
  login as apiLogin,
  register as apiRegister,
  saveAuth,
  type User,
} from "@/lib/auth";

interface AuthContextValue {
  user: User | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (data: {
    email: string;
    password: string;
    name: string;
    phone?: string;
  }) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const token = getToken();
    if (!token) {
      setIsLoading(false);
      return;
    }
    getMe()
      .then((fresh) => {
        saveAuth(token, fresh);
        setUser(fresh);
      })
      .catch(() => {
        clearAuth();
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const res = await apiLogin(email, password);
    saveAuth(res.access_token, res.user);
    setUser(res.user);
  }, []);

  const register = useCallback(
    async (data: {
      email: string;
      password: string;
      name: string;
      phone?: string;
    }) => {
      const res = await apiRegister(data);
      saveAuth(res.access_token, res.user);
      setUser(res.user);
    },
    []
  );

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
  }, []);

  const refreshUser = useCallback(async () => {
    const token = getToken();
    if (!token) {
      setUser(null);
      return;
    }
    const fresh = await getMe();
    saveAuth(token, fresh);
    setUser(fresh);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
