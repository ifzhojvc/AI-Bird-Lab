// @vitest-environment jsdom
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api } from "../api";
import Checkout from "./Checkout";
import { MySubscription, Plans } from "./Account";
import * as wallet from "../web3";
import type {
  CryptoPayment,
  Network,
  PaymentOrder,
  Plan,
} from "../../../shared/subscriptions";

vi.mock("../auth", () => ({
  useAuth: () => ({
    user: { id: "test-user", email: "test@example.test" },
    signOut: vi.fn(),
  }),
}));
vi.mock("../web3", () => ({
  discoverWallets: vi.fn((announce) => {
    announce({
      id: "test-wallet",
      name: "MetaMask",
      provider: { on: vi.fn(), removeListener: vi.fn() },
    });
    return () => {};
  }),
  connectWallet: vi.fn(),
  switchNetwork: vi.fn(),
  signWallet: vi.fn(),
  walletBalances: vi.fn(),
  approveOrder: vi.fn(),
  payOrder: vi.fn(),
  estimatePayment: vi.fn(),
  walletError: (error: { code?: number; message?: string }) =>
    error.code === 4001
      ? "Дію скасовано у гаманці. Ви можете спробувати ще раз."
      : error.message || "Помилка гаманця",
}));
const address = "0x3333333333333333333333333333333333333333" as const;
const network: Network = {
  enabled: true,
  testMode: true,
  chainId: 84532,
  rpcUrl: "https://sepolia.base.org",
  tokenAddress: "0x1111111111111111111111111111111111111111",
  paymentContractAddress: "0x2222222222222222222222222222222222222222",
  tokenDecimals: 6,
  confirmations: 12,
  explorerUrl: "https://sepolia.basescan.org",
};
const plans: Plan[] = [
  {
    id: 0,
    name: "FREE",
    price: "0",
    currency: "USDC",
    durationDays: 1,
    analysisLimit: 5,
    features: ["image"],
    tokenDecimals: 6,
  },
  {
    id: 1,
    name: "PRO",
    price: "5000000",
    currency: "USDC",
    durationDays: 30,
    analysisLimit: 100,
    features: ["image", "audio"],
    tokenDecimals: 6,
  },
  {
    id: 2,
    name: "PREMIUM",
    price: "10000000",
    currency: "USDC",
    durationDays: 30,
    analysisLimit: 500,
    features: ["batch", "compare"],
    tokenDecimals: 6,
  },
];
let serverStatus = "Pending";
let order: PaymentOrder;
beforeEach(() => {
  localStorage.clear();
  serverStatus = "Pending";
  order = {
    id: "test-order",
    orderId: `0x${"3".repeat(64)}`,
    planId: 1,
    walletAddress: address,
    chainId: 84532,
    tokenContractAddress: network.tokenAddress,
    paymentContractAddress: network.paymentContractAddress,
    amount: "5000000",
    tokenDecimals: 6,
    durationDays: 30,
    analysisLimit: 100,
    features: ["image", "audio"],
    status: "Created",
    createdAt: new Date().toISOString(),
    expiresAt: new Date(Date.now() + 1800000).toISOString(),
    replaceCurrentPlan: false,
  };
  vi.mocked(wallet.connectWallet).mockResolvedValue({
    address,
    chainId: 84532,
  });
  vi.mocked(wallet.switchNetwork).mockResolvedValue(84532);
  vi.mocked(wallet.walletBalances).mockResolvedValue({
    usdc: 10000000n,
    gas: 1000000000000000000n,
  });
  vi.mocked(wallet.signWallet).mockResolvedValue(`0x${"a".repeat(130)}`);
  vi.mocked(wallet.approveOrder).mockResolvedValue(`0x${"b".repeat(64)}`);
  vi.mocked(wallet.payOrder).mockResolvedValue(`0x${"c".repeat(64)}`);
  vi.mocked(wallet.estimatePayment).mockResolvedValue("0.000001");
  vi.spyOn(api, "request").mockImplementation(async (path) => {
    if (path === "/subscriptions/plans") return plans;
    if (path === "/subscriptions/network") return network;
    if (path === "/wallets/nonce")
      return {
        nonce: "one-time-nonce",
        message: "server-generated SIWE message",
      };
    if (path === "/wallets/verify") return { isVerified: true };
    if (path === "/subscriptions/orders") return order;
    if (path === "/subscriptions/payments/verify")
      return {
        status: serverStatus,
        error: null,
        paymentOrderId: order.id,
      } as CryptoPayment;
    if (path === "/subscriptions/me")
      return {
        planId: 1,
        plan: "PRO",
        status: "Active",
        remaining: 99,
        analysesUsed: 1,
        analysisLimit: 100,
        features: ["image", "audio"],
        endDate: new Date(Date.now() + 86400000).toISOString(),
      };
    if (path === "/subscriptions/history") return [];
    throw new Error(`Unexpected unit-test API ${path}`);
  });
});
afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  vi.clearAllMocks();
});
function view(component = <Checkout />, path = "/checkout/1") {
  const cache = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  render(
    <QueryClientProvider client={cache}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="*" element={component} />
          <Route path="/checkout/:planId" element={component} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return userEvent.setup();
}
async function prepare() {
  const user = view();
  await user.click(
    await screen.findByRole("button", { name: "Підключити MetaMask" }),
  );
  await user.click(
    await screen.findByRole("button", { name: "Підписати повідомлення" }),
  );
  await user.click(
    await screen.findByRole("button", { name: "Створити замовлення PRO" }),
  );
  await screen.findByRole("button", { name: "Підтвердити дозвіл ERC-20" });
  return user;
}
async function approve(user: ReturnType<typeof userEvent.setup>) {
  await user.click(
    screen.getByRole("button", { name: "Підтвердити дозвіл ERC-20" }),
  );
  await screen.findByRole("button", { name: "Точну суму дозволено ✓" });
  await user.click(screen.getByLabelText(/Я перевірив/));
}
describe("тестові криптопідписки — змодельований гаманець і API", () => {
  it("показує серверні тарифи та вибір PRO", async () => {
    view(<Plans />, "/plans");
    expect(
      (await screen.findByRole("link", { name: "Обрати PRO" })).getAttribute(
        "href",
      ),
    ).toBe("/checkout/1");
    expect(screen.getByText("100 аналізів за 30 днів")).toBeTruthy();
    expect(screen.getByText("5 аналізів на добу UTC")).toBeTruthy();
  });
  it("підключає гаманець лише після натискання та перевіряє неправильну мережу", async () => {
    vi.mocked(wallet.connectWallet).mockResolvedValue({ address, chainId: 1 });
    const user = view();
    expect(wallet.connectWallet).not.toHaveBeenCalled();
    await user.click(
      await screen.findByRole("button", { name: "Підключити MetaMask" }),
    );
    expect(await screen.findByText(/Неправильна мережа/)).toBeTruthy();
    await user.click(
      screen.getByRole("button", { name: "Переключити мережу" }),
    );
    await screen.findByRole("button", { name: "Підписати повідомлення" });
    expect(wallet.switchNetwork).toHaveBeenCalledOnce();
  });
  it("створює замовлення без передавання клієнтської ціни", async () => {
    await prepare();
    const call = vi
      .mocked(api.request)
      .mock.calls.find(([path]) => path === "/subscriptions/orders")!;
    expect(JSON.parse(call[1]!.body as string)).toEqual({
      planId: 1,
      walletAddress: address,
      replaceCurrentPlan: false,
    });
    expect(wallet.payOrder).not.toHaveBeenCalled();
  });
  it("не активує підписку до серверного підтвердження", async () => {
    const user = await prepare();
    await approve(user);
    await user.click(
      screen.getByRole("button", { name: "Оплатити 5 тестових USDC" }),
    );
    expect(
      await screen.findByRole("heading", { name: "Очікуємо підтвердження" }),
    ).toBeTruthy();
    expect(screen.queryByText(/Сервер перевірив блокчейн/)).toBeNull();
  });
  it("показує успіх лише після підтвердження backend", async () => {
    serverStatus = "Confirmed";
    const user = await prepare();
    await approve(user);
    await user.click(
      screen.getByRole("button", { name: "Оплатити 5 тестових USDC" }),
    );
    expect(await screen.findByText(/Сервер перевірив блокчейн/)).toBeTruthy();
  });
  it("показує скасування транзакції користувачем", async () => {
    const user = await prepare();
    await approve(user);
    vi.mocked(wallet.payOrder).mockRejectedValue({ code: 4001 });
    await user.click(
      screen.getByRole("button", { name: "Оплатити 5 тестових USDC" }),
    );
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      "Дію скасовано у гаманці. Ви можете спробувати ще раз.",
    );
    expect(
      vi
        .mocked(api.request)
        .mock.calls.some(([path]) => path === "/subscriptions/payments/verify"),
    ).toBe(false);
  });
  it("не переходить до оплати за недостатнього балансу", async () => {
    const user = await prepare();
    vi.mocked(wallet.approveOrder).mockRejectedValue(
      new Error("Недостатньо тестових USDC для цього тарифу."),
    );
    await user.click(
      screen.getByRole("button", { name: "Підтвердити дозвіл ERC-20" }),
    );
    expect(await screen.findByRole("alert")).toHaveProperty(
      "textContent",
      "Недостатньо тестових USDC для цього тарифу.",
    );
    expect(
      (
        screen.getByRole("button", {
          name: "Оплатити 5 тестових USDC",
        }) as HTMLButtonElement
      ).disabled,
    ).toBe(true);
  });
  it("відображає активний тариф і залишок із API", async () => {
    view(<MySubscription />, "/account");
    await waitFor(() => expect(screen.getByText("99 / 100")).toBeTruthy());
    expect(screen.getByRole("heading", { name: "PRO" })).toBeTruthy();
  });
});
