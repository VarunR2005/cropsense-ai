import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, clearToken, getToken, setToken, setUnauthorizedHandler } from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(getToken()));

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(logout);
  }, [logout]);

  useEffect(() => {
    if (!getToken()) {
      setLoading(false);
      return;
    }
    api
      .me()
      .then(setUser)
      .catch((e) => {
        if (e.status === 401) clearToken();
      })
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (email, password) => {
    const res = await api.login(email, password);
    setToken(res.access_token);
    setUser(await api.me());
  }, []);

  const register = useCallback(
    async (form) => {
      await api.register(form);
      await login(form.email, form.password);
    },
    [login]
  );

  const value = useMemo(
    () => ({ user, setUser, loading, login, register, logout }),
    [user, loading, login, register, logout]
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export const useAuth = () => useContext(AuthContext);
