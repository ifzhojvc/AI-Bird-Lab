export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

export class ApiClient {
  readonly base: string;
  private accessToken: string | null = null;
  constructor(base: string) {
    this.base = base.trim().replace(/\/$/, "");
  }
  file(path: string) {
    return `${this.base}${path}`;
  }
  setAccessToken(value: string | null) {
    this.accessToken = value;
  }
  authHeaders(): Record<string, string> {
    return this.accessToken
      ? { Authorization: `Bearer ${this.accessToken}` }
      : {};
  }
  async request<T>(
    path: string,
    init: RequestInit = {},
    timeoutMs = 240000,
  ): Promise<T> {
    if (!/^https?:\/\//.test(this.base))
      throw new Error(
        "Вкажіть HTTP або HTTPS адресу центрального сервера в налаштуваннях.",
      );
    const controller = new AbortController();
    const abort = () => controller.abort();
    init.signal?.addEventListener("abort", abort, { once: true });
    if (init.signal?.aborted) controller.abort();
    const timeout = setTimeout(() => controller.abort(), timeoutMs);
    try {
      const response = await fetch(`${this.base}/api${path}`, {
        credentials: "include",
        ...init,
        headers:
          this.accessToken || init.headers
            ? {
                ...this.authHeaders(),
                ...Object.fromEntries(new Headers(init.headers).entries()),
              }
            : undefined,
        signal: controller.signal,
      });
      if (!response.ok) {
        const payload = (await response.json().catch(() => ({}))) as {
          detail?: string;
          message?: string;
          title?: string;
        };
        throw new ApiError(
          payload.detail ||
            payload.message ||
            payload.title ||
            `Сервер повернув помилку ${response.status}.`,
          response.status,
        );
      }
      if (response.status === 204) return undefined as T;
      return (await response.json()) as T;
    } catch (error) {
      if (init.signal?.aborted) throw error;
      if (error instanceof Error && error.name === "AbortError")
        throw new Error(
          "Час очікування минув. Перевірте історію перед повторною відправкою.",
        );
      if (error instanceof TypeError)
        throw new Error(
          "Немає зв’язку з центральним сервером. Перевірте адресу API та мережу.",
        );
      throw error;
    } finally {
      clearTimeout(timeout);
      init.signal?.removeEventListener("abort", abort);
    }
  }
}
