import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import { formatEther, type Address } from "viem";
import { api, useApi } from "../api";
import { useAuth } from "../auth";
import { PageTitle, State } from "../components/Common";
import {
  approveOrder,
  connectWallet,
  discoverWallets,
  estimatePayment,
  payOrder,
  signWallet,
  switchNetwork,
  walletBalances,
  walletError,
  type WalletChoice,
} from "../web3";
import {
  formatToken,
  paymentLabels,
  shortAddress,
  type CryptoPayment,
  type Network,
  type PaymentOrder,
  type Plan,
} from "../../../shared/subscriptions";

export default function Checkout() {
  const planId = Number(useParams().planId);
  const plans = useApi<Plan[]>("/subscriptions/plans");
  const networkQuery = useApi<Network>("/subscriptions/network");
  const plan = plans.data?.find((p) => p.id === planId && p.id > 0);
  const network = networkQuery.data;
  const { user } = useAuth();
  const cache = useQueryClient();
  const [choices, setChoices] = useState<WalletChoice[]>([]);
  const [selected, setSelected] = useState<WalletChoice>();
  const [address, setAddress] = useState<Address>();
  const [chainId, setChainId] = useState<number>();
  const [verified, setVerified] = useState(false);
  const [balances, setBalances] = useState<{ usdc: bigint; gas: bigint }>();
  const [order, setOrder] = useState<PaymentOrder>();
  const [approved, setApproved] = useState(false);
  const [consent, setConsent] = useState(false);
  const [replace, setReplace] = useState(false);
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");
  const [fee, setFee] = useState("");
  const [transactionHash, setTransactionHash] = useState("");
  const [payment, setPayment] = useState<CryptoPayment>();
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 5000);
    return () => clearInterval(timer);
  }, []);
  const storageKey = `bird-payment:${user?.id}:${planId}`;
  useEffect(
    () =>
      discoverWallets((wallet) =>
        setChoices((list) =>
          list.some((w) => w.provider === wallet.provider)
            ? list
            : [...list, wallet],
        ),
      ),
    [],
  );
  useEffect(() => {
    if (!selected) return;
    const accounts = () => {
      setAddress(undefined);
      setVerified(false);
      setBalances(undefined);
      setApproved(false);
      setError(
        "Адреса гаманця змінилася. Підключіть потрібну адресу повторно.",
      );
    };
    const changed = (id: string) => {
      setChainId(Number(id));
      setBalances(undefined);
    };
    selected.provider.on?.("accountsChanged", accounts);
    selected.provider.on?.("chainChanged", changed);
    return () => {
      selected.provider.removeListener?.("accountsChanged", accounts);
      selected.provider.removeListener?.("chainChanged", changed);
    };
  }, [selected]);
  useEffect(() => {
    let active = true;
    try {
      const saved = JSON.parse(localStorage.getItem(storageKey) || "null") as {
        orderId?: string;
        hash?: string;
      } | null;
      if (saved?.orderId && saved.hash)
        void api
          .request<PaymentOrder>(`/subscriptions/orders/${saved.orderId}`)
          .then((data) => {
            if (active) {
              setOrder(data);
              setTransactionHash(saved.hash!);
            }
          })
          .catch(() => {});
    } catch {
      localStorage.removeItem(storageKey);
    }
    return () => {
      active = false;
    };
  }, [storageKey]);
  useEffect(() => {
    if (!order || !transactionHash) return;
    let active = true;
    let pending = false;
    let finished = false;
    const check = async () => {
      if (pending || finished) return;
      pending = true;
      try {
        const response = await api.request<CryptoPayment>(
          "/subscriptions/payments/verify",
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ orderId: order.id, transactionHash }),
          },
        );
        if (!active) return;
        setPayment(response);
        setError("");
        finished = ["Confirmed", "Rejected", "ReviewRequired"].includes(
          response.status,
        );
        if (response.status === "Confirmed") {
          await cache.invalidateQueries({ queryKey: ["/subscriptions/me"] });
          await cache.invalidateQueries({
            queryKey: ["/subscriptions/history"],
          });
        }
      } catch (e) {
        if (active) setError((e as Error).message);
      } finally {
        pending = false;
      }
    };
    void check();
    const timer = setInterval(() => {
      if (active) void check();
    }, 7000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [order?.id, transactionHash, cache]);
  async function action(label: string, callback: () => Promise<void>) {
    setBusy(label);
    setError("");
    try {
      await callback();
    } catch (e) {
      setError(walletError(e));
    } finally {
      setBusy("");
    }
  }
  async function connect(choice: WalletChoice) {
    if (!network) return;
    const result = await connectWallet(choice.provider, network);
    setSelected(choice);
    setAddress(result.address);
    setChainId(result.chainId);
    setVerified(false);
    setApproved(false);
    if (result.chainId === network.chainId)
      setBalances(
        await walletBalances(choice.provider, network, result.address),
      );
  }
  const rightNetwork = chainId === network?.chainId;
  const samePayer =
    !order || order.walletAddress.toLowerCase() === address?.toLowerCase();
  const expired = !!order && Date.parse(order.expiresAt) <= now;
  function resetOrder() {
    localStorage.removeItem(storageKey);
    setOrder(undefined);
    setTransactionHash("");
    setPayment(undefined);
    setApproved(false);
    setConsent(false);
    setError("");
  }
  return (
    <>
      <PageTitle
        eyebrow="КРОК ДО НОВИХ ВІДКРИТТІВ"
        title="Оплата підписки"
        text="Кошти залишають ваш гаманець лише після окремого підтвердження транзакції. Приватний ключ і seed phrase ніколи не потрібні."
      />
      <State
        loading={plans.isLoading || networkQuery.isLoading}
        error={plans.error || networkQuery.error}
      >
        {((expired && !transactionHash) || payment?.status === "Rejected") && (
          <div className="notice">
            <p>
              {payment?.status === "Rejected"
                ? "Платіж не прийнято. Перевірте історію транзакцій перед новою спробою."
                : "Строк замовлення минув. Не надсилайте оплату за цим замовленням."}
            </p>
            <button className="button" onClick={resetOrder}>
              Створити інше замовлення
            </button>
          </div>
        )}
        {!plan ? (
          <div className="state">
            Оберіть доступний тариф на <Link to="/plans">сторінці тарифів</Link>
            .
          </div>
        ) : (
          <div className="checkout-grid">
            <section className="panel checkout-main">
              <h2>1. Підключіть гаманець</h2>
              {!network?.enabled ? (
                <p role="status">
                  Тестові платежі ще не налаштовано власником лабораторії.
                </p>
              ) : (
                <>
                  {!address ? (
                    <div className="actions">
                      {choices.map((choice) => (
                        <button
                          className="button primary"
                          key={choice.id}
                          disabled={!!busy}
                          onClick={() =>
                            void action("Підключення…", () => connect(choice))
                          }
                        >
                          Підключити {choice.name}
                        </button>
                      ))}
                      {choices.length === 0 && (
                        <p>
                          Відкрийте сторінку в браузері з MetaMask або іншим
                          сумісним EVM-гаманцем.
                        </p>
                      )}
                    </div>
                  ) : (
                    <>
                      <div className="wallet-line">
                        <code>{shortAddress(address)}</code>
                        <span>
                          {chainId === 84532
                            ? "Base Sepolia"
                            : chainId === 31337
                              ? "Local Anvil"
                              : `Мережа ${chainId}`}
                        </span>
                        <button
                          className="text-button"
                          disabled={!!busy}
                          onClick={() => {
                            setAddress(undefined);
                            setSelected(undefined);
                            setVerified(false);
                            setBalances(undefined);
                          }}
                        >
                          Відключити
                        </button>
                      </div>
                      {!rightNetwork && (
                        <div className="notice" role="alert">
                          <p>
                            Неправильна мережа. Для оплати потрібна{" "}
                            {network.chainId === 84532
                              ? "Base Sepolia"
                              : "Local Anvil"}
                            .
                          </p>
                          <button
                            className="button"
                            disabled={!!busy}
                            onClick={() =>
                              void action("Перемикання…", async () => {
                                const id = await switchNetwork(
                                  selected!.provider,
                                  network,
                                );
                                setChainId(id);
                                if (id === network.chainId)
                                  setBalances(
                                    await walletBalances(
                                      selected!.provider,
                                      network,
                                      address,
                                    ),
                                  );
                              })
                            }
                          >
                            Переключити мережу
                          </button>
                        </div>
                      )}
                      {rightNetwork && (
                        <>
                          <p>
                            Баланс:{" "}
                            {balances
                              ? formatToken(
                                  balances.usdc.toString(),
                                  network.tokenDecimals,
                                )
                              : "…"}{" "}
                            USDC · {balances ? formatEther(balances.gas) : "…"}{" "}
                            тестового ETH
                          </p>
                          <button
                            className="text-button"
                            disabled={!!busy}
                            onClick={() =>
                              void action("Перевірка балансу…", async () =>
                                setBalances(
                                  await walletBalances(
                                    selected!.provider,
                                    network,
                                    address,
                                  ),
                                ),
                              )
                            }
                          >
                            Оновити баланс
                          </button>
                          <h2>2. Підтвердіть адресу</h2>
                          <p>
                            Підпис одноразового SIWE-повідомлення прив’яже
                            адресу до вашого облікового запису. Комісія не
                            стягується.
                          </p>
                          <button
                            className="button"
                            disabled={!!busy || verified}
                            onClick={() =>
                              void action("Підпис повідомлення…", async () => {
                                const nonce = await api.request<{
                                  nonce: string;
                                  message: string;
                                }>("/wallets/nonce", {
                                  method: "POST",
                                  headers: {
                                    "Content-Type": "application/json",
                                  },
                                  body: JSON.stringify({
                                    walletAddress: address,
                                  }),
                                });
                                const signature = await signWallet(
                                  selected!.provider,
                                  network,
                                  address,
                                  nonce.message,
                                );
                                await api.request("/wallets/verify", {
                                  method: "POST",
                                  headers: {
                                    "Content-Type": "application/json",
                                  },
                                  body: JSON.stringify({ ...nonce, signature }),
                                });
                                setVerified(true);
                              })
                            }
                          >
                            {verified
                              ? "Адресу підтверджено ✓"
                              : "Підписати повідомлення"}
                          </button>
                        </>
                      )}
                    </>
                  )}
                  <h2>3. Перевірте замовлення</h2>
                  <label className="check-label">
                    <input
                      type="checkbox"
                      checked={replace}
                      disabled={!!order || !!busy}
                      onChange={(e) => setReplace(e.target.checked)}
                    />
                    <span>
                      Якщо поточний платний тариф відрізняється, погоджуюся
                      замінити невикористані дні та ліміт. Перерахунку коштів
                      немає.
                    </span>
                  </label>
                  <button
                    className="button"
                    disabled={
                      !!busy ||
                      !verified ||
                      !rightNetwork ||
                      !!transactionHash ||
                      (!!order && order.status !== "Expired")
                    }
                    onClick={() =>
                      void action("Створення замовлення…", async () => {
                        const response = await api.request<PaymentOrder>(
                          "/subscriptions/orders",
                          {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({
                              planId,
                              walletAddress: address,
                              replaceCurrentPlan: replace,
                            }),
                          },
                        );
                        setOrder(response);
                        setApproved(false);
                      })
                    }
                  >
                    Створити замовлення {plan.name}
                  </button>
                  {order && (
                    <>
                      <p className="caption">
                        Замовлення діє до{" "}
                        {new Date(order.expiresAt).toLocaleString("uk-UA")}.
                        Транзакція має потрапити до блоку до цього часу.
                      </p>
                      <code className="address">{order.orderId}</code>
                      <h2>4. Дозвольте точну суму</h2>
                      <p>
                        Окремий дозвіл ERC-20 лише на{" "}
                        {formatToken(order.amount, order.tokenDecimals)} USDC.
                        Це ще не платіж за підписку.
                      </p>
                      <button
                        className="button"
                        disabled={
                          !!busy ||
                          !rightNetwork ||
                          !samePayer ||
                          approved ||
                          !!transactionHash
                        }
                        onClick={() =>
                          void action("Підтвердження дозволу…", async () => {
                            await approveOrder(
                              selected!.provider,
                              network,
                              order,
                            );
                            setApproved(true);
                            setBalances(
                              await walletBalances(
                                selected!.provider,
                                network,
                                order.walletAddress,
                              ),
                            );
                            setFee(
                              await estimatePayment(
                                selected!.provider,
                                network,
                                order,
                              ),
                            );
                          })
                        }
                      >
                        {approved
                          ? "Точну суму дозволено ✓"
                          : "Підтвердити дозвіл ERC-20"}
                      </button>
                      <h2>5. Підтвердіть платіж</h2>
                      <label className="check-label">
                        <input
                          type="checkbox"
                          checked={consent}
                          onChange={(e) => setConsent(e.target.checked)}
                        />
                        <span>
                          Я перевірив(-ла) суму, токен, мережу та одержувача.
                          Розумію, що криптовалютний платіж може бути
                          незворотним і комісія сплачується окремо.
                        </span>
                      </label>
                      <button
                        className="button primary"
                        disabled={
                          !!busy ||
                          !approved ||
                          !consent ||
                          !rightNetwork ||
                          !samePayer ||
                          !!transactionHash
                        }
                        onClick={() =>
                          void action(
                            "Підтвердіть платіж у гаманці…",
                            async () => {
                              const hash = await payOrder(
                                selected!.provider,
                                network,
                                order,
                              );
                              localStorage.setItem(
                                storageKey,
                                JSON.stringify({ orderId: order.id, hash }),
                              );
                              setTransactionHash(hash);
                            },
                          )
                        }
                      >
                        Оплатити{" "}
                        {formatToken(order.amount, order.tokenDecimals)}{" "}
                        тестових USDC
                      </button>
                    </>
                  )}
                </>
              )}
              {busy && <p role="status">{busy}</p>}
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              {transactionHash && (
                <div className="notice" role="status">
                  <h3>{paymentLabels[payment?.status || "Pending"]}</h3>
                  <p>
                    {payment?.status === "Confirmed"
                      ? "Сервер перевірив блокчейн. Оплачений період збережено; якщо це продовження, він почнеться після поточного."
                      : payment?.error ||
                        "Сервер очікує транзакцію та необхідні підтвердження."}
                  </p>
                  <code className="address">{transactionHash}</code>
                  {network?.explorerUrl && (
                    <a
                      target="_blank"
                      rel="noreferrer"
                      href={`${network.explorerUrl}/tx/${transactionHash}`}
                    >
                      Відкрити транзакцію ↗
                    </a>
                  )}
                  <Link className="button" to="/account">
                    Моя підписка
                  </Link>
                </div>
              )}
            </section>
            <aside className="panel invoice">
              <span className="eyebrow">ВАШЕ ЗАМОВЛЕННЯ</span>
              <h2>{plan.name}</h2>
              <div className="plan-price">
                {formatToken(
                  order?.amount || plan.price,
                  order?.tokenDecimals ?? plan.tokenDecimals,
                )}
                <span>тестових USDC</span>
              </div>
              <dl>
                <dt>Період</dt>
                <dd>{order?.durationDays ?? plan.durationDays} днів</dd>
                <dt>Ліміт</dt>
                <dd>{order?.analysisLimit ?? plan.analysisLimit} аналізів</dd>
                <dt>Мережа</dt>
                <dd>
                  {network?.chainId === 31337
                    ? "Local Anvil · 31337"
                    : "Base Sepolia · 84532"}
                </dd>
                <dt>Токен</dt>
                <dd className="address">
                  {order?.tokenContractAddress || network?.tokenAddress}
                </dd>
                <dt>Одержувач — платіжний контракт</dt>
                <dd className="address">
                  {order?.paymentContractAddress ||
                    network?.paymentContractAddress ||
                    "Ще не налаштовано"}
                </dd>
                <dt>Комісія мережі</dt>
                <dd>
                  {fee
                    ? `Орієнтовно ${fee} ETH`
                    : "Остаточну суму покаже гаманець перед підписом"}
                </dd>
                <dt>Підтвердження</dt>
                <dd>{network?.confirmations}</dd>
              </dl>
              <p className="caption">
                Без автоматичних списань. Для продовження ви самостійно
                оплачуєте новий період. Підписка активується після незалежної
                серверної перевірки.
              </p>
              <Link to="/payments">Історія платежів</Link>
            </aside>
          </div>
        )}
      </State>
    </>
  );
}
