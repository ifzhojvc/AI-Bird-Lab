import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiClient } from "../../shared/api";

afterEach(() => vi.unstubAllGlobals());
describe("центральний HTTP API", () => {
  it("передає multipart без ручного Content-Type", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(
        new Response(JSON.stringify({ id: 17 }), { status: 201 }),
      );
    vi.stubGlobal("fetch", fetcher);
    const client = new ApiClient("http://192.168.1.2:5100/");
    const body = new FormData();
    body.append("file", new Blob(["bird"]), "bird.jpg");
    expect(
      await client.request("/analysis/image", { method: "POST", body }),
    ).toEqual({ id: 17 });
    expect(fetcher.mock.calls[0][0]).toBe(
      "http://192.168.1.2:5100/api/analysis/image",
    );
    expect(fetcher.mock.calls[0][1].headers).toBeUndefined();
  });
  it("показує ProblemDetails від ASP.NET", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response(JSON.stringify({ detail: "AI-сервіс недоступний." }), {
            status: 502,
          }),
        ),
    );
    await expect(
      new ApiClient("http://server:5100").request("/analysis/image"),
    ).rejects.toThrow("AI-сервіс недоступний.");
  });
  it("обробляє видалення 204 без спроби читання JSON", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );
    expect(
      await new ApiClient("http://server:5100").request("/analyses/7", {
        method: "DELETE",
      }),
    ).toBeUndefined();
  });
  it("обробляє недоступну мережу", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );
    await expect(
      new ApiClient("http://server:5100").request("/health"),
    ).rejects.toThrow("Немає зв’язку");
  });
  it("вимагає налаштовану адресу API", async () => {
    await expect(new ApiClient("").request("/health")).rejects.toThrow(
      "Вкажіть HTTP",
    );
  });
});
