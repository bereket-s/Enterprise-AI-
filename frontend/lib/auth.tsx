"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "./api";
import { CurrentUser, ModuleStatus } from "./types";

interface AuthState {
  user: CurrentUser | null;
  modules: ModuleStatus[];
  loading: boolean;
  refreshModules: () => Promise<void>;
  refreshUser: () => Promise<CurrentUser | null>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>({
  user: null,
  modules: [],
  loading: true,
  refreshModules: async () => {},
  refreshUser: async () => null,
  logout: () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [modules, setModules] = useState<ModuleStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refreshModules = useCallback(async () => {
    try {
      const resp = await api.get<ModuleStatus[]>("/api/org/modules");
      setModules(resp.data);
    } catch {
      setModules([]);
    }
  }, []);

  // Re-fetches /api/auth/me from the current localStorage token and updates
  // context state. Exposed so login/register can call it directly after
  // storing a fresh token — client-side navigation to /dashboard does not
  // remount AuthProvider, so the mount-only effect below would otherwise
  // never notice the new token and the dashboard would bounce back to /login.
  const refreshUser = useCallback(async (): Promise<CurrentUser | null> => {
    const token = typeof window !== "undefined" ? window.localStorage.getItem("access_token") : null;
    if (!token) {
      setUser(null);
      setModules([]);
      return null;
    }
    try {
      const resp = await api.get<CurrentUser>("/api/auth/me");
      setUser(resp.data);
      await refreshModules();
      return resp.data;
    } catch {
      window.localStorage.removeItem("access_token");
      setUser(null);
      setModules([]);
      return null;
    }
  }, [refreshModules]);

  useEffect(() => {
    refreshUser().finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const logout = () => {
    window.localStorage.removeItem("access_token");
    setUser(null);
    setModules([]);
    router.push("/login");
  };

  return (
    <AuthContext.Provider value={{ user, modules, loading, refreshModules, refreshUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
