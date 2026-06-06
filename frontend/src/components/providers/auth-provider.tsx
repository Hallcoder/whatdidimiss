"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { UserResponse } from "@/lib/api/types";
import { setAccessToken } from "@/lib/api/client";
import { logout as apiLogout, getMe, refreshToken } from "@/lib/api/auth";

const AUTH_DISABLED = process.env.NEXT_PUBLIC_AUTH_DISABLED === "true";

interface AuthContextValue {
  user: UserResponse | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (token: string, user: UserResponse) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  login: () => {},
  logout: async () => {},
});

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (AUTH_DISABLED) {
      // Skip token refresh, just fetch the dev user
      getMe()
        .then((userData) => setUser(userData))
        .catch(() => setUser({ id: "dev", email: "dev@localhost", display_name: "Dev User", avatar_url: null, channel: null }))
        .finally(() => setIsLoading(false));
      return;
    }

    refreshToken()
      .then(async (data) => {
        setAccessToken(data.access_token);
        try {
          const fullUser = await getMe();
          setUser(fullUser);
        } catch {
          setUser(data.user);
        }
      })
      .catch(() => {
        setAccessToken(null);
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (token: string, userData: UserResponse) => {
    setAccessToken(token);
    try {
      const fullUser = await getMe();
      setUser(fullUser);
    } catch {
      setUser(userData);
    }
  }, []);

  const logout = useCallback(async () => {
    try {
      await apiLogout();
    } catch {
      // ignore
    }
    setAccessToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        isLoading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
