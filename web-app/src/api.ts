import { useQuery } from "@tanstack/react-query";
import { ApiClient } from "../../shared/api";

export const api = new ApiClient(
  import.meta.env.VITE_API_URL || "http://localhost:5100",
);
export function useApi<T>(path: string, enabled = true) {
  return useQuery({
    queryKey: [path],
    queryFn: () => api.request<T>(path),
    refetchInterval: 15000,
    retry: 1,
    enabled,
  });
}
