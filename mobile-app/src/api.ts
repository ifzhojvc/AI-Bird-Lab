import { useCallback, useState } from "react";
import { useFocusEffect } from "@react-navigation/native";
import { ApiClient } from "../../shared/api";

const configured = process.env.EXPO_PUBLIC_API_URL || "";
const isLoopback =
  /^https?:\/\/(localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?=[:/]|$)/i.test(
    configured,
  );
export const api = new ApiClient(isLoopback ? "" : configured);
export function useRemote<T>(path: string | null) {
  const [data, setData] = useState<T>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const reload = useCallback(async () => {
    if (!path) {
      setLoading(false);
      return;
    }
    setLoading(true);
    try {
      setData(await api.request<T>(path));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }, [path]);
  useFocusEffect(
    useCallback(() => {
      void reload();
      const interval = setInterval(() => void reload(), 15000);
      return () => clearInterval(interval);
    }, [reload]),
  );
  return { data, loading, error, reload };
}
