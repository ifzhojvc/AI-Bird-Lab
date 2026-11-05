// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {BirdLabSubscriptions} from "../src/BirdLabSubscriptions.sol";

interface BaseDeployVm {
    function startBroadcast() external;
    function stopBroadcast() external;
    function envAddress(string calldata) external returns (address);
    function envUint(string calldata) external returns (uint256);
}

contract DeployBaseSepolia {
    BaseDeployVm private constant vm = BaseDeployVm(address(uint160(uint256(keccak256("hevm cheat code")))));
    function run() external returns (BirdLabSubscriptions subscriptions) {
        require(block.chainid == 84532, "Base Sepolia only; mainnet disabled");
        address token = vm.envAddress("BIRD_TOKEN_ADDRESS");
        require(token == 0x036CbD53842c5426634e7929541eC2318f3dCF7e, "Verify Circle Base Sepolia USDC");
        address owner = vm.envAddress("BIRD_OWNER_ADDRESS");
        vm.startBroadcast();
        subscriptions = new BirdLabSubscriptions(token, owner);
        subscriptions.setPlanPrice(1, vm.envUint("BIRD_PRO_PRICE_ATOMIC"));
        subscriptions.setPlanPrice(2, vm.envUint("BIRD_PREMIUM_PRICE_ATOMIC"));
        vm.stopBroadcast();
    }
}
