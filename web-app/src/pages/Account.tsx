import { useState, type FormEvent } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth";
import { useApi } from "../api";
import { PageTitle, State } from "../components/Common";
import {
  featureLabels,
  paymentLabels,
  formatToken,
  shortAddress,
  type CryptoPayment,
  type Entitlement,
  type Plan,
  type SubscriptionPeriod,
} from "../../../shared/subscriptions";

export function AuthPage() {
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const auth = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await auth.signIn(email, password, register);
      navigate(
        (location.state as { from?: string } | null)?.from || "/account",
        { replace: true },
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel auth-panel">
      <span className="eyebrow">ВАША ОСОБИСТА ЛАБОРАТОРІЯ</span>
      <h1>{register ? "Створити обліковий запис" : "Вітаємо у Bird Lab"}</h1>
      <p>
        FREE: 5 фотоаналізів на добу. Гаманець для безкоштовного тарифу не
        потрібен.
      </p>
      <form onSubmit={(e) => void submit(e)}>
        <label>
          Електронна пошта
          <input
            type="email"
            autoComplete="email"
            required
            maxLength={254}
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
        </label>
        <label>
          Пароль
          <input
            type="password"
            autoComplete={register ? "new-password" : "current-password"}
            required
            minLength={12}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {register && (
          <p className="caption">
            Від 12 символів: велика й мала літери, цифра та спеціальний символ.
          </p>
        )}
        {error && (
          <p className="error" role="alert">
            {error}
          </p>
        )}
        <button className="button primary" disabled={busy}>
          {busy ? "Зачекайте…" : register ? "Зареєструватися" : "Увійти"}
        </button>
      </form>
      <button
        className="text-button"
        onClick={() => {
          setRegister(!register);
          setError("");
        }}
      >
        {register
          ? "У мене вже є обліковий запис"
          : "Створити новий обліковий запис"}
      </button>
      <Link to="/plans">Переглянути тарифи</Link>
    </section>
  );
}

export function Plans() {
  const query = useApi<Plan[]>("/subscriptions/plans");
  const auth = useAuth();
  return (
    <>
      <PageTitle
        eyebrow="ОБЕРІТЬ СВІЙ РИТМ ДОСЛІДЖЕНЬ"
        title="Тарифи лабораторії"
        text="Передплачений доступ без автоматичних списань. Оплата лише тестовими USDC у тестовій мережі."
      />
      <State
        loading={query.isLoading}
        error={query.error}
        retry={() => void query.refetch()}
      >
        <div className="plans-grid">
          {query.data?.map((plan) => (
            <section
              key={plan.id}
              className={`panel plan-card ${plan.id === 1 ? "featured" : ""}`}
            >
              <span className="eyebrow">
                {plan.id === 1
                  ? "ДЛЯ РЕГУЛЯРНИХ ВІДКРИТТІВ"
                  : plan.id === 2
                    ? "ПОВНИЙ ПРОСТІР МОЖЛИВОСТЕЙ"
                    : "ПОЧНІТЬ СПОСТЕРІГАТИ"}
              </span>
              <h2>{plan.name}</h2>
              <div className="plan-price">
                {formatToken(plan.price, plan.tokenDecimals)}
                <span>{plan.id ? "тестових USDC" : "безкоштовно"}</span>
              </div>
              <p>
                {plan.analysisLimit} аналізів{" "}
                {plan.id ? `за ${plan.durationDays} днів` : "на добу UTC"}
              </p>
              <ul>
                {plan.features.map((feature) => (
                  <li key={feature}>{featureLabels[feature] || feature}</li>
                ))}
              </ul>
              <Link
                className={`button ${plan.id === 1 ? "primary" : ""}`}
                to={
                  !auth.user
                    ? "/login"
                    : plan.id
                      ? `/checkout/${plan.id}`
                      : "/account"
                }
              >
                {plan.id ? `Обрати ${plan.name}` : "Почати безкоштовно"}
              </Link>
            </section>
          ))}
        </div>
      </State>
      <div className="research-note">
        <p>
          Токени тестової мережі призначені для навчання. Кожну покупку ви
          підтверджуєте вручну. Невикористаний ліміт не переноситься до
          наступного періоду; зміна тарифу замінює залишок лише за вашим явним
          погодженням.
        </p>
      </div>
    </>
  );
}

export function MySubscription() {
  const auth = useAuth();
  const access = useApi<Entitlement>("/subscriptions/me");
  const periods = useApi<SubscriptionPeriod[]>("/subscriptions/history");
  const [error, setError] = useState("");
  return (
    <>
      <PageTitle
        eyebrow="ОБЛІКОВИЙ ЗАПИС"
        title="Моя підписка"
        text={auth.user?.email || ""}
        action={
          <button
            className="button"
            onClick={() =>
              void auth.signOut().catch((e: Error) => setError(e.message))
            }
          >
            Вийти
          </button>
        }
      />
      {error && <p role="alert">{error}</p>}
      <State
        loading={access.isLoading}
        error={access.error}
        retry={() => void access.refetch()}
      >
        {access.data && (
          <section className="panel subscription-overview">
            <div>
              <span className="eyebrow">ПОТОЧНИЙ ТАРИФ</span>
              <h2>{access.data.plan}</h2>
              <p>{paymentLabels[access.data.status] || access.data.status}</p>
            </div>
            <div>
              <strong>
                {access.data.remaining} / {access.data.analysisLimit}
              </strong>
              <p>аналізів залишилось</p>
              <progress
                max={access.data.analysisLimit}
                value={access.data.analysesUsed}
                aria-label="Використано аналізів"
              />
              <p className="caption">
                Використано {access.data.analysesUsed}.{" "}
                {access.data.planId ? "Строк до" : "Ліміт оновиться"}{" "}
                {new Date(access.data.endDate).toLocaleString("uk-UA")}
              </p>
            </div>
            <div>
              <Link className="button primary" to="/plans">
                {access.data.planId
                  ? "Продовжити або змінити тариф"
                  : "Переглянути тарифи"}
              </Link>
              <Link className="button" to="/payments">
                Історія платежів
              </Link>
            </div>
            <ul className="feature-list">
              {access.data.features.map((f) => (
                <li key={f}>{featureLabels[f] || f}</li>
              ))}
            </ul>
          </section>
        )}
      </State>
      <section className="panel">
        <h2>Історія періодів</h2>
        <State
          loading={periods.isLoading}
          error={periods.error}
          empty={periods.data?.length === 0}
        >
          <div className="payment-list">
            {periods.data?.map((p) => (
              <article key={p.id}>
                <strong>
                  {p.planId === 1 ? "PRO" : "PREMIUM"} ·{" "}
                  {paymentLabels[p.status] || p.status}
                </strong>
                <p>
                  {new Date(p.startDate).toLocaleDateString("uk-UA")} —{" "}
                  {new Date(p.endDate).toLocaleDateString("uk-UA")} ·{" "}
                  {p.analysesUsed} / {p.analysisLimit} аналізів
                </p>
              </article>
            ))}
          </div>
        </State>
      </section>
      <p className="caption">
        Після закінчення платного періоду працює FREE. Власна історія
        зберігається. Старі спільні дані залишаються окремим архівом
        адміністратора.
      </p>
    </>
  );
}

export function Payments() {
  const query = useApi<CryptoPayment[]>("/subscriptions/payments");
  return (
    <>
      <PageTitle
        eyebrow="ПРОЗОРА ІСТОРІЯ"
        title="Історія платежів"
        text="Статус підтвердження визначає сервер після перевірки RPC. Транзакція у гаманці ще не означає активацію."
      />
      <State
        loading={query.isLoading}
        error={query.error}
        empty={query.data?.length === 0}
        retry={() => void query.refetch()}
      >
        <div className="payment-list">
          {query.data?.map((p) => (
            <article className="panel" key={p.id}>
              <div className="section-title">
                <strong>
                  {p.subscriptionPlanId === 1 ? "PRO" : "PREMIUM"} ·{" "}
                  {formatToken(p.amount, p.tokenDecimals)} тестових USDC
                </strong>
                <span
                  className={`pill ${p.status === "Confirmed" ? "success" : ""}`}
                >
                  {paymentLabels[p.status] || p.status}
                </span>
              </div>
              <p>
                {p.blockchainNetwork} · {shortAddress(p.walletAddress)} ·{" "}
                {new Date(p.createdAt).toLocaleString("uk-UA")}
              </p>
              {p.error && <p role="status">{p.error}</p>}
              <code className="address">{p.transactionHash}</code>
              {p.explorerUrl && (
                <a href={p.explorerUrl} target="_blank" rel="noreferrer">
                  Переглянути транзакцію ↗
                </a>
              )}
            </article>
          ))}
        </div>
      </State>
    </>
  );
}
