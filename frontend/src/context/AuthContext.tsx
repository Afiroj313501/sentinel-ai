import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import {
  clearToken,
  fetchCurrentUser,
  getToken,
  loginUser,
  registerUser,
} from "../services/auth";
import type { AuthPayload, User } from "../types/auth";
import { AuthContext } from "./authContext.value";

export function AuthProvider({ children }: { children: ReactNode }) {
  // Initialise loading lazily: true only when a saved token exists
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => Boolean(getToken()));

  useEffect(() => {
    const token = getToken();
    if (!token) return; // loading already false from initialiser

    const controller = new AbortController();
    fetchCurrentUser(controller.signal)
      .then((profile) => setUser(profile))
      .catch(() => {
        clearToken();
        setUser(null);
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, []);

  async function login(payload: AuthPayload) {
    const res = await loginUser(payload);
    setUser(res.user);
  }

  async function register(payload: AuthPayload) {
    const res = await registerUser(payload);
    setUser(res.user);
  }

  function logout() {
    clearToken();
    setUser(null);
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
