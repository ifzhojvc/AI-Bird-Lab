import { useState } from "react";
import { ActivityIndicator, Text, TextInput, View } from "react-native";
import { Button, Screen, State, Title } from "../components/Common";
import { colors, styles as s } from "../theme";
import { useAuth } from "../auth";
import { useRemote } from "../api";
import {
  featureLabels,
  formatToken,
  paymentLabels,
  type CryptoPayment,
  type Entitlement,
  type SubscriptionPeriod,
} from "../../../shared/subscriptions";

export function LoginScreen() {
  const auth = useAuth();
  const [register, setRegister] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function submit() {
    setBusy(true);
    setError("");
    try {
      await auth.signIn(email.trim(), password, register);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Screen>
      <Title
        title={register ? "Створити обліковий запис" : "Увійти до лабораторії"}
        description="Безкоштовний тариф: 5 фотоаналізів на добу UTC. Гаманець не потрібен."
      />
      <View style={s.card}>
        <Text style={s.text}>Електронна пошта</Text>
        <TextInput
          style={s.input}
          accessibilityLabel="Електронна пошта"
          autoCapitalize="none"
          autoComplete="email"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
          placeholder="name@example.com"
          placeholderTextColor={colors.muted}
        />
        <Text style={s.text}>Пароль</Text>
        <TextInput
          style={s.input}
          accessibilityLabel="Пароль"
          secureTextEntry
          autoCapitalize="none"
          autoComplete={register ? "new-password" : "current-password"}
          value={password}
          onChangeText={setPassword}
          maxLength={128}
        />
        <Text style={s.muted}>
          Від 12 символів: велика й мала літери, цифра та спеціальний символ.
        </Text>
        <Button
          title={busy ? "Зачекайте…" : register ? "Зареєструватися" : "Увійти"}
          primary
          disabled={busy || !email || password.length < 12}
          onPress={() => void submit()}
        />
        <Button
          title={
            register
              ? "У мене вже є обліковий запис"
              : "Створити обліковий запис"
          }
          disabled={busy}
          onPress={() => {
            setRegister(!register);
            setError("");
          }}
        />
        {!!(error || auth.error) && (
          <Text style={s.error} accessibilityRole="alert">
            {error || auth.error}
          </Text>
        )}
        {!!auth.error && (
          <Button
            title="Перевірити сесію знову"
            onPress={() => void auth.retry()}
          />
        )}
        {auth.loading && <ActivityIndicator color={colors.green} />}
      </View>
    </Screen>
  );
}

export default function MySubscriptionScreen() {
  const auth = useAuth();
  const access = useRemote<Entitlement>("/subscriptions/me");
  const payments = useRemote<CryptoPayment[]>("/subscriptions/payments");
  const periods = useRemote<SubscriptionPeriod[]>("/subscriptions/history");
  const [error, setError] = useState("");
  return (
    <Screen>
      <Title
        title="Мій тариф"
        description={auth.user?.email || "Обліковий запис"}
      />
      <State
        loading={access.loading && !access.data}
        error={access.error}
        retry={() => void access.reload()}
      >
        {access.data && (
          <>
            <View style={s.card}>
              <Text style={s.title}>{access.data.plan}</Text>
              <Text style={s.link}>
                {paymentLabels[access.data.status] || access.data.status}
              </Text>
              <Text style={s.h2}>Використані аналізи</Text>
              <Text style={s.text}>
                {access.data.analysesUsed} із {access.data.analysisLimit} ·
                залишилось {access.data.remaining}
              </Text>
              <Text style={s.h2}>Термін дії підписки</Text>
              <Text style={s.text}>
                {access.data.planId ? "Діє до" : "Добовий ліміт оновиться"}{" "}
                {new Date(access.data.endDate).toLocaleString("uk-UA")}
              </Text>
              <Text style={s.muted}>
                Після завершення платного періоду працює FREE. Ваша історія
                зберігається.
              </Text>
              <Button
                title="Оновити підписку з сервера"
                onPress={() => {
                  void access.reload();
                  void payments.reload();
                  void periods.reload();
                }}
              />
            </View>
            <View style={s.card}>
              <Text style={s.h2}>Доступні можливості</Text>
              {access.data.features.map((feature) => (
                <Text key={feature} style={s.text}>
                  ✓ {featureLabels[feature] || feature}
                </Text>
              ))}
            </View>
          </>
        )}
      </State>
      <View style={s.card}>
        <Text style={s.h2}>Історія платежів</Text>
        <State
          loading={payments.loading && !payments.data}
          error={payments.error}
          empty={payments.data?.length === 0}
          retry={() => void payments.reload()}
        >
          {payments.data?.map((payment) => (
            <View key={payment.id} style={{ gap: 8, paddingVertical: 12 }}>
              <Text style={s.text}>
                {payment.subscriptionPlanId === 1 ? "PRO" : "PREMIUM"} ·{" "}
                {formatToken(payment.amount, payment.tokenDecimals)} тестових
                USDC
              </Text>
              <Text style={s.link}>
                {paymentLabels[payment.status] || payment.status}
              </Text>
              <Text style={s.muted}>
                {payment.blockchainNetwork} ·{" "}
                {new Date(payment.createdAt).toLocaleString("uk-UA")}
              </Text>
              {!!payment.error && <Text style={s.muted}>{payment.error}</Text>}
              <Text selectable style={s.muted}>
                {payment.transactionHash}
              </Text>
            </View>
          ))}
        </State>
      </View>
      <View style={s.card}>
        <Text style={s.h2}>Історія підписок</Text>
        <State
          loading={periods.loading && !periods.data}
          error={periods.error}
          empty={periods.data?.length === 0}
        >
          {periods.data?.map((period) => (
            <View key={period.id} style={{ gap: 6, paddingVertical: 10 }}>
              <Text style={s.text}>
                {period.planId === 1 ? "PRO" : "PREMIUM"} ·{" "}
                {paymentLabels[period.status] || period.status}
              </Text>
              <Text style={s.muted}>
                {new Date(period.startDate).toLocaleDateString("uk-UA")} —{" "}
                {new Date(period.endDate).toLocaleDateString("uk-UA")}
              </Text>
            </View>
          ))}
        </State>
      </View>
      {!!error && <Text style={s.error}>{error}</Text>}
      <Button
        title="Вийти з облікового запису"
        onPress={() =>
          void auth.signOut().catch((e: Error) => setError(e.message))
        }
      />
    </Screen>
  );
}
