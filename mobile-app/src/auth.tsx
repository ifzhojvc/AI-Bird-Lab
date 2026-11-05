import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import * as SecureStore from "expo-secure-store";
import { ApiError } from "../../shared/api";
import type { Session, UserProfile } from "../../shared/subscriptions";
import { api } from "./api";

const sessionKey = "birdlab.auth.session";
const AuthContext = createContext<{
  user?: UserProfile;
  loading: boolean;
  error: string;
  signIn: (email: string, password: string, register: boolean) => Promise<void>;
  signOut: () => Promise<void>;
  retry: () => Promise<void>;
} | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserProfile>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  async function restore() {
    setLoading(true);
    setError("");
    try {
      const value = await SecureStore.getItemAsync(sessionKey);
      api.setAccessToken(value);
      if (value) setUser(await api.request<UserProfile>("/auth/me"));
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        await SecureStore.deleteItemAsync(sessionKey);
        api.setAccessToken(null);
        setUser(undefined);
      } else setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }
  useEffect(() => {
    void restore();
  }, []);
  async function signIn(email: string, password: string, register: boolean) {
    const result = await api.request<Session>(
      `/auth/${register ? "register" : "login"}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, useBearerToken: true }),
      },
    );
    if (!result.accessToken) throw new Error("Сервер не повернув сесію.");
    await SecureStore.setItemAsync(sessionKey, result.accessToken, {
      keychainAccessible: SecureStore.WHEN_UNLOCKED_THIS_DEVICE_ONLY,
    });
    api.setAccessToken(result.accessToken);
    setUser(result.user);
    setError("");
  }
  async function signOut() {
    let offline = false;
    try {
      await api.request("/auth/logout", { method: "POST" });
    } catch (error) {
      offline = !(error instanceof ApiError && error.status === 401);
    }
    await SecureStore.deleteItemAsync(sessionKey);
    api.setAccessToken(null);
    setUser(undefined);
    setError(
      offline
        ? "Вихід на пристрої виконано. Сервер тимчасово недоступний; серверна сесія завершиться не пізніше ніж за 8 годин."
        : "",
    );
  }
  return (
    <AuthContext.Provider
      value={{ user, loading, error, signIn, signOut, retry: restore }}
    >
      {children}
    </AuthContext.Provider>
  );
}
export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error("AuthProvider required");
  return value;
}
