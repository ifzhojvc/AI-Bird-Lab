export interface UserProfile {
  id: string;
  email: string;
  createdAt: string;
}
export interface Session {
  user: UserProfile;
  accessToken: string | null;
  expiresAt: string;
}
export interface Plan {
  id: number;
  name: string;
  price: string;
  currency: string;
  durationDays: number;
  analysisLimit: number;
  features: string[];
  tokenDecimals: number;
}
export interface Entitlement {
  planId: number;
  plan: string;
  status: string;
  analysisLimit: number;
  analysesUsed: number;
  remaining: number;
  features: string[];
  startDate: string;
  endDate: string;
  subscriptionId: string | null;
}
export interface Network {
  enabled: boolean;
  testMode: boolean;
  chainId: number;
  rpcUrl: string;
  tokenAddress: `0x${string}`;
  paymentContractAddress: `0x${string}`;
  tokenDecimals: number;
  confirmations: number;
  explorerUrl: string;
}
export interface PaymentOrder {
  id: string;
  orderId: `0x${string}`;
  planId: number;
  walletAddress: `0x${string}`;
  chainId: number;
  tokenContractAddress: `0x${string}`;
  paymentContractAddress: `0x${string}`;
  amount: string;
  tokenDecimals: number;
  durationDays: number;
  analysisLimit: number;
  features: string[];
  status: string;
  createdAt: string;
  expiresAt: string;
  replaceCurrentPlan: boolean;
}
export interface CryptoPayment {
  id: string;
  paymentOrderId: string;
  orderId: string;
  subscriptionPlanId: number;
  walletAddress: string;
  blockchainNetwork: string;
  chainId: number;
  amount: string;
  transactionHash: string;
  blockNumber: number | null;
  logIndex: number | null;
  status: string;
  error: string | null;
  createdAt: string;
  confirmedAt: string | null;
  explorerUrl: string | null;
  tokenDecimals: number;
}
export interface SubscriptionPeriod {
  id: string;
  planId: number;
  status: string;
  startDate: string;
  endDate: string;
  analysisLimit: number;
  analysesUsed: number;
}
export const featureLabels: Record<string, string> = {
  image: "Фотоаналіз",
  audio: "Аудіоаналіз",
  history: "Історія результатів",
  basicInfo: "Інформація про птахів",
  gallery: "Галерея",
  statistics: "Розширена статистика",
  batch: "Пакетний аналіз",
  compare: "Порівняння птахів",
  advancedStatistics: "Статистика еталонних оцінок",
};
export const paymentLabels: Record<string, string> = {
  Created: "Створено",
  Submitted: "Надіслано",
  Pending: "Очікуємо підтвердження",
  Confirmed: "Підтверджено сервером",
  Rejected: "Відхилено",
  Reorged: "Повторна перевірка ланцюжка",
  ReviewRequired: "Потрібна перевірка адміністратора",
  Paid: "Оплачено",
  Active: "Активний",
  Scheduled: "Наступний період",
  Expired: "Строк минув",
  Replaced: "Замінено",
  Free: "Безкоштовний",
};
export function formatToken(value: string, decimals = 6) {
  const digits = BigInt(value)
    .toString()
    .padStart(decimals + 1, "0");
  if (decimals === 0) return digits;
  const fraction = digits.slice(-decimals).replace(/0+$/, "");
  return digits.slice(0, -decimals) + (fraction ? `.${fraction}` : "");
}
export const shortAddress = (value: string) =>
  `${value.slice(0, 6)}…${value.slice(-4)}`;
