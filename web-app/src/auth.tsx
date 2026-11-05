import { createContext, useContext, type ReactNode } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Navigate, Outlet, useLocation, Link } from "react-router-dom";
import { api, useApi } from "./api";
import { ApiError } from "../../shared/api";
import type {
  Entitlement,
  Session,
  UserProfile,
} from "../../shared/subscriptions";

const Auth = createContext<{
  user?: UserProfile;
  loading: boolean;
  signIn: (email: string, password: string, register: boolean) => Promise<void>;
  signOut: () => Promise<void>;
} | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const cache = useQueryClient();
  const session = useQuery({
    queryKey: ["session"],
    queryFn: () => api.request<UserProfile>("/auth/me"),
    retry: false,
    staleTime: 60000,
  });
  async function signIn(email: string, password: string, register: boolean) {
    const data = await api.request<Session>(
      `/auth/${register ? "register" : "login"}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      },
    );
    cache.clear();
    cache.setQueryData(["session"], data.user);
  }
  async function signOut() {
    try {
      await api.request("/auth/logout", { method: "POST" });
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 401)) throw error;
    }
    for (const key of Object.keys(localStorage))
      if (key.startsWith("bird-tasks:")) localStorage.removeItem(key);
    cache.clear();
    cache.setQueryData(["session"], null);
  }
  return (
    <Auth.Provider
      value={{
        user: session.data || undefined,
        loading: session.isLoading,
        signIn,
        signOut,
      }}
    >
      {children}
    </Auth.Provider>
  );
}
export function useAuth() {
  const value = useContext(Auth);
  if (!value) throw new Error("AuthProvider required");
  return value;
}
export function RequireAuth() {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading)
    return (
      <div className="state" role="status">
        Перевіряємо обліковий запис…
      </div>
    );
  return user ? (
    <Outlet />
  ) : (
    <Navigate to="/login" state={{ from: location.pathname }} replace />
  );
}
export function FeatureGate({
  feature,
  children,
}: {
  feature: string;
  children: ReactNode;
}) {
  const access = useApi<Entitlement>("/subscriptions/me");
  if (access.isLoading)
    return (
      <div className="state" role="status">
        Перевіряємо можливості тарифу…
      </div>
    );
  if (access.error)
    return (
      <div className="state error" role="alert">
        {access.error.message}
      </div>
    );
  if (!access.data?.features.includes(feature))
    return (
      <section className="panel subscription-intro">
        <h1>Розширте можливості лабораторії</h1>
        <p>
          Ця функція недоступна у вашому поточному тарифі {access.data?.plan}.
        </p>
        <Link className="button primary" to="/plans">
          Переглянути тарифи
        </Link>
      </section>
    );
  return children;
}
