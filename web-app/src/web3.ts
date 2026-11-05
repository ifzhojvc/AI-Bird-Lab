import {
  createPublicClient,
  createWalletClient,
  custom,
  defineChain,
  erc20Abi,
  formatEther,
  http,
  type Address,
  type EIP1193Provider,
  type Hash,
} from "viem";
import type { Network, PaymentOrder } from "../../shared/subscriptions";

export interface WalletChoice {
  id: string;
  name: string;
  provider: EIP1193Provider;
}
declare global {
  interface Window {
    ethereum?: EIP1193Provider & { providers?: EIP1193Provider[] };
  }
}
export const subscriptionsAbi = [
  {
    type: "function",
    name: "purchaseSubscription",
    stateMutability: "nonpayable",
    inputs: [
      { name: "orderId", type: "bytes32" },
      { name: "planId", type: "uint256" },
    ],
    outputs: [],
  },
] as const;
function chain(network: Network) {
  if (!network.testMode || ![84532, 31337].includes(network.chainId))
    throw new Error("Дозволені лише Base Sepolia та локальний Anvil.");
  return defineChain({
    id: network.chainId,
    name: network.chainId === 84532 ? "Base Sepolia" : "Local Anvil",
    nativeCurrency: { name: "Test Ether", symbol: "ETH", decimals: 18 },
    rpcUrls: { default: { http: [network.rpcUrl] } },
    testnet: true,
  });
}
function clients(provider: EIP1193Provider, network: Network) {
  const target = chain(network);
  return {
    publicClient: createPublicClient({
      chain: target,
      transport: http(network.rpcUrl),
    }),
    wallet: createWalletClient({ chain: target, transport: custom(provider) }),
  };
}
export function discoverWallets(announce: (wallet: WalletChoice) => void) {
  const receive = (event: Event) => {
    const data = (
      event as CustomEvent<{
        info: { uuid: string; name: string };
        provider: EIP1193Provider;
      }>
    ).detail;
    if (typeof data?.provider?.request === "function" && data.info?.uuid)
      announce({
        id: data.info.uuid,
        name: data.info.name.slice(0, 80),
        provider: data.provider,
      });
  };
  window.addEventListener("eip6963:announceProvider", receive);
  window.dispatchEvent(new Event("eip6963:requestProvider"));
  const injected = window.ethereum;
  if (injected)
    (injected.providers || [injected]).forEach((provider, index) =>
      announce({
        id: `injected-${index}`,
        name: index ? `EVM-гаманець ${index + 1}` : "MetaMask / EVM-гаманець",
        provider,
      }),
    );
  return () => window.removeEventListener("eip6963:announceProvider", receive);
}
export async function connectWallet(
  provider: EIP1193Provider,
  network: Network,
) {
  const { wallet } = clients(provider, network);
  const [address] = await wallet.requestAddresses();
  if (!address) throw new Error("Гаманець не надав адресу.");
  return { address, chainId: await wallet.getChainId() };
}
export async function switchNetwork(
  provider: EIP1193Provider,
  network: Network,
) {
  const { wallet } = clients(provider, network);
  try {
    await wallet.switchChain({ id: network.chainId });
  } catch (error) {
    const cause = error as { code?: number; cause?: { code?: number } };
    if (cause.code !== 4902 && cause.cause?.code !== 4902) throw error;
    await wallet.addChain({ chain: chain(network) });
    await wallet.switchChain({ id: network.chainId });
  }
  return wallet.getChainId();
}
async function assertAccount(
  provider: EIP1193Provider,
  network: Network,
  address: Address,
) {
  const { wallet, publicClient } = clients(provider, network);
  const [current] = await wallet.getAddresses();
  if (
    current?.toLowerCase() !== address.toLowerCase() ||
    (await wallet.getChainId()) !== network.chainId ||
    (await publicClient.getChainId()) !== network.chainId
  )
    throw new Error("Адреса або мережа гаманця змінилася. Підключіться знову.");
  return { wallet, publicClient };
}
export async function walletBalances(
  provider: EIP1193Provider,
  network: Network,
  address: Address,
) {
  const { publicClient } = await assertAccount(provider, network, address);
  const [usdc, gas] = await Promise.all([
    publicClient.readContract({
      address: network.tokenAddress,
      abi: erc20Abi,
      functionName: "balanceOf",
      args: [address],
    }),
    publicClient.getBalance({ address }),
  ]);
  return { usdc, gas };
}
export async function signWallet(
  provider: EIP1193Provider,
  network: Network,
  address: Address,
  message: string,
) {
  const { wallet } = await assertAccount(provider, network, address);
  return wallet.signMessage({ account: address, message });
}
export async function approveOrder(
  provider: EIP1193Provider,
  network: Network,
  order: PaymentOrder,
) {
  const { wallet, publicClient } = await assertAccount(
    provider,
    network,
    order.walletAddress,
  );
  const balance = await walletBalances(provider, network, order.walletAddress);
  if (balance.usdc < BigInt(order.amount))
    throw new Error("Недостатньо тестових USDC для цього тарифу.");
  if (balance.gas === 0n)
    throw new Error("Немає тестового ETH для комісії мережі.");
  if (Date.parse(order.expiresAt) <= Date.now())
    throw new Error("Строк замовлення минув. Створіть нове замовлення.");
  const request = {
    account: order.walletAddress,
    address: order.tokenContractAddress,
    abi: erc20Abi,
    functionName: "approve" as const,
    args: [order.paymentContractAddress, BigInt(order.amount)] as const,
  };
  const simulation = await publicClient.simulateContract(request);
  const hash = await wallet.writeContract(simulation.request);
  const receipt = await publicClient.waitForTransactionReceipt({
    hash,
    confirmations: 1,
    timeout: 120000,
  });
  if (receipt.status !== "success")
    throw new Error("Дозвіл ERC-20 не підтверджено.");
  return hash;
}
export async function estimatePayment(
  provider: EIP1193Provider,
  network: Network,
  order: PaymentOrder,
) {
  const { publicClient } = await assertAccount(
    provider,
    network,
    order.walletAddress,
  );
  const gas = await publicClient.estimateContractGas({
    account: order.walletAddress,
    address: order.paymentContractAddress,
    abi: subscriptionsAbi,
    functionName: "purchaseSubscription",
    args: [order.orderId, BigInt(order.planId)],
  });
  return formatEther(gas * (await publicClient.getGasPrice()));
}
export async function payOrder(
  provider: EIP1193Provider,
  network: Network,
  order: PaymentOrder,
): Promise<Hash> {
  const { wallet, publicClient } = await assertAccount(
    provider,
    network,
    order.walletAddress,
  );
  if (Date.parse(order.expiresAt) <= Date.now())
    throw new Error("Строк замовлення минув. Не надсилайте платіж.");
  const simulation = await publicClient.simulateContract({
    account: order.walletAddress,
    address: order.paymentContractAddress,
    abi: subscriptionsAbi,
    functionName: "purchaseSubscription",
    args: [order.orderId, BigInt(order.planId)],
  });
  return wallet.writeContract(simulation.request);
}
export function walletError(error: unknown) {
  const value = error as {
    code?: number;
    name?: string;
    message?: string;
    cause?: { code?: number };
  };
  if (
    value.code === 4001 ||
    value.cause?.code === 4001 ||
    /UserRejected/.test(value.name || "") ||
    /User rejected/i.test(value.message || "")
  )
    return "Дію скасовано у гаманці. Ви можете спробувати ще раз.";
  if (/InsufficientFunds/.test(value.name || ""))
    return "Недостатньо тестового ETH для комісії мережі.";
  return /[А-Яа-яІіЇїЄєҐґ]/.test(value.message || "")
    ? value.message!
    : "Гаманець або RPC не виконав запит. Перевірте мережу, баланс та статус транзакції перед повтором.";
}
