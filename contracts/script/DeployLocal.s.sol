// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {MockUSDC} from "../src/MockUSDC.sol";
import {BirdLabSubscriptions} from "../src/BirdLabSubscriptions.sol";

interface DeployVm {
    function startBroadcast() external;
    function stopBroadcast() external;
    function envAddress(string calldata) external returns (address);
}

contract DeployLocal {
    DeployVm private constant vm = DeployVm(address(uint160(uint256(keccak256("hevm cheat code")))));
    function run() external returns (MockUSDC token, BirdLabSubscriptions subscriptions) {
        require(block.chainid == 31337, "Local Anvil only");
        address owner = vm.envAddress("BIRD_OWNER_ADDRESS");
        vm.startBroadcast();
        token = new MockUSDC();
        subscriptions = new BirdLabSubscriptions(address(token), owner);
        subscriptions.setPlanPrice(1, 5_000_000);
        subscriptions.setPlanPrice(2, 10_000_000);
        vm.stopBroadcast();
    }
}
