import argparse
import json
import subprocess
import time
from pathlib import Path
from urllib.parse import urlparse

import requests


ROOT = Path(__file__).resolve().parents[1]


class Anvil:
    def __init__(self, url="http://127.0.0.1:8545"):
        if urlparse(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("Local integration accepts loopback Anvil only.")
        self.url = url
        self.http = requests.Session()

    def rpc(self, method, params=None):
        response = self.http.post(self.url, json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or []}, timeout=15)
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(f"Anvil RPC {method} failed: {payload['error'].get('message', '')[:200]}")
        return payload["result"]

    def require_local(self):
        if int(self.rpc("eth_chainId"), 16) != 31337:
            raise RuntimeError("Mainnet and external networks are forbidden by this script.")

    def receipt(self, transaction):
        for _ in range(100):
            value = self.rpc("eth_getTransactionReceipt", [transaction])
            if value:
                if int(value["status"], 16) != 1:
                    raise RuntimeError("Local transaction reverted.")
                return value
            time.sleep(.1)
        raise RuntimeError("Local transaction was not mined.")

    def send(self, sender, to=None, data="0x"):
        self.require_local()
        transaction = {"from": sender, "data": data, "gas": hex(5_000_000)}
        if to:
            transaction["to"] = to
        return self.rpc("eth_sendTransaction", [transaction])

    @staticmethod
    def calldata(signature, *args):
        return subprocess.check_output(["cast", "calldata", signature, *map(str, args)], cwd=ROOT / "contracts", text=True, encoding="utf-8").strip()

    def call(self, sender, target, signature, *args):
        transaction = self.send(sender, target, self.calldata(signature, *args))
        self.receipt(transaction)
        return transaction

    def deploy(self):
        self.require_local()
        subprocess.run(["forge", "build", "--offline"], cwd=ROOT / "contracts", check=True, capture_output=True)
        accounts = self.rpc("eth_accounts")
        owner = accounts[0]
        token_bytecode = json.loads((ROOT / "contracts/out/MockUSDC.sol/MockUSDC.json").read_text())["bytecode"]["object"]
        token_hash = self.send(owner, data=token_bytecode)
        token = self.receipt(token_hash)["contractAddress"]
        bytecode = json.loads((ROOT / "contracts/out/BirdLabSubscriptions.sol/BirdLabSubscriptions.json").read_text())["bytecode"]["object"]
        constructor = token[2:].rjust(64, "0") + owner[2:].rjust(64, "0")
        deploy_hash = self.send(owner, data=bytecode + constructor)
        contract = self.receipt(deploy_hash)["contractAddress"]
        self.call(owner, contract, "setPlanPrice(uint256,uint256)", 1, 5_000_000)
        self.call(owner, contract, "setPlanPrice(uint256,uint256)", 2, 10_000_000)
        result = {"chainId": 31337, "rpcUrl": self.url, "tokenAddress": token, "paymentContractAddress": contract, "ownerAddress": owner, "tokenDecimals": 6, "deploymentTransactionHash": deploy_hash, "tokenDeploymentTransactionHash": token_hash, "testOnly": True}
        (ROOT / "verification/local-deployment.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
        return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Реальне локальне розгортання в Anvil без приватних ключів.")
    parser.add_argument("--rpc", default="http://127.0.0.1:8545")
    args = parser.parse_args()
    print(json.dumps(Anvil(args.rpc).deploy()))
