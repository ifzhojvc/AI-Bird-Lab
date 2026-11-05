import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClient } from "../../shared/api";
import { watchAnalysis, pollingInterval } from "../../shared/polling";
import { analysisStatusText } from "../../shared/contracts";

afterEach(() => { vi.unstubAllGlobals(); vi.useRealTimers(); });
const client = new ApiClient("http://server:5100");

describe("асинхронний контракт вебу та Expo", () => {
  it("показує справжні стани і завершує polling після Completed", async () => {
    vi.useFakeTimers();
    const fetcher = vi.fn();
    for (const status of ["Queued", "Processing", "Completed"]) fetcher.mockResolvedValueOnce(new Response(JSON.stringify({ status, result: status === "Completed" ? { id: 8 } : null })));
    vi.stubGlobal("fetch", fetcher);
    const values: string[] = [];
    const result = watchAnalysis(client, "job", new AbortController().signal, (value) => values.push(analysisStatusText[value.status]), vi.fn());
    await vi.advanceTimersByTimeAsync(10000);
    await result;
    expect(values).toEqual(["Очікування в черзі", "Обробка", "Аналіз завершено"]);
    expect(fetcher).toHaveBeenCalledTimes(3);
  });

  it("перериває поточний fetch після unmount/background", async () => {
    const controller = new AbortController();
    const fetcher = vi.fn((_url, init: RequestInit) => new Promise((_resolve, reject) => init.signal!.addEventListener("abort", () => reject(Object.assign(new Error(), { name: "AbortError" })))));
    vi.stubGlobal("fetch", fetcher);
    const update = vi.fn();
    const result = watchAnalysis(client, "job", controller.signal, update, vi.fn());
    controller.abort();
    await result;
    expect(update).not.toHaveBeenCalled();
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("не запитує API, поки екран неактивний", async () => {
    vi.useFakeTimers();
    const controller = new AbortController();
    const fetcher = vi.fn();
    vi.stubGlobal("fetch", fetcher);
    const result = watchAnalysis(client, "job", controller.signal, vi.fn(), vi.fn(), 2000, () => false);
    await vi.advanceTimersByTimeAsync(10000);
    controller.abort();
    await result;
    expect(fetcher).not.toHaveBeenCalled();
  });

  it("не повторює назавжди запит до видаленого завдання", async () => {
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ detail: "Завдання не знайдено." }), { status: 404 }));
    vi.stubGlobal("fetch", fetcher);
    await watchAnalysis(client, "deleted", new AbortController().signal, vi.fn(), vi.fn());
    expect(fetcher).toHaveBeenCalledTimes(1);
  });

  it("валідує налаштований інтервал", () => {
    expect(pollingInterval(undefined)).toBe(2000);
    expect(pollingInterval("3000")).toBe(3000);
    expect(pollingInterval(0)).toBe(2000);
  });
});
