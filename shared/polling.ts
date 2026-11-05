import { ApiClient, ApiError } from "./api";
import { isTerminal, type AnalysisStatus } from "./contracts";

export function pollingInterval(value: unknown): number {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed >= 500 && parsed <= 60000 ? parsed : 2000;
}

function delay(ms: number, signal: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    if (signal.aborted) { resolve(); return; }
    const finish = () => { clearTimeout(timer); signal.removeEventListener("abort", finish); resolve(); };
    const timer = setTimeout(finish, ms);
    signal.addEventListener("abort", finish, { once: true });
  });
}

export async function watchAnalysis(api: ApiClient, id: string, signal: AbortSignal, update: (status: AnalysisStatus) => void, error: (message: string) => void, interval = 2000, active = () => true): Promise<void> {
  let failures = 0;
  while (!signal.aborted) {
    if (active()) {
      try {
        const value = await api.request<AnalysisStatus>(`/analyses/${encodeURIComponent(id)}/status`, { signal }, 20000);
        if (signal.aborted) return;
        update(value);
        error("");
        failures = 0;
        if (isTerminal(value.status)) return;
      } catch (e) {
        if (signal.aborted) return;
        error((e as Error).message);
        failures++;
        if (e instanceof ApiError && e.status >= 400 && e.status < 500 && e.status !== 429) return;
      }
    }
    await delay(Math.min(30000, pollingInterval(interval) * Math.pow(2, Math.min(failures, 4))), signal);
  }
}
