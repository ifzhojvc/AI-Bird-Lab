// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {BirdLabSubscriptions} from "../src/BirdLabSubscriptions.sol";
import {MockUSDC} from "../src/MockUSDC.sol";
import {ERC20} from "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import {IERC20Errors} from "@openzeppelin/contracts/interfaces/draft-IERC6093.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

interface Vm {
    function prank(address) external;
    function startPrank(address) external;
    function stopPrank() external;
    function expectRevert(bytes4) external;
    function expectRevert(bytes calldata) external;
    function expectEmit(bool, bool, bool, bool, address) external;
    function chainId(uint256) external;
}

contract FeeToken is ERC20 {
    constructor() ERC20("Fee token", "FEE") { _mint(msg.sender, 100_000_000); }
    function _update(address from, address to, uint256 value) internal override {
        if (from != address(0) && to != address(0) && value > 1) {
            super._update(from, address(0), 1);
            super._update(from, to, value - 1);
        } else super._update(from, to, value);
    }
}

contract ReentrantToken is ERC20 {
    BirdLabSubscriptions public target;
    bool public blocked;
    constructor() ERC20("Reentrant token", "RNT") { _mint(msg.sender, 100_000_000); }
    function setTarget(BirdLabSubscriptions value) external { target = value; }
    function transferFrom(address from, address to, uint256 amount) public override returns (bool) {
        (bool success, bytes memory data) = address(target).call(abi.encodeCall(target.purchaseSubscription, (bytes32(bytes20(address(this))), 1)));
        blocked = !success && data.length >= 4 && bytes4(data) == bytes4(keccak256("ReentrancyGuardReentrantCall()"));
        return super.transferFrom(from, to, amount);
    }
}

contract BirdLabSubscriptionsTest {
    Vm private constant vm = Vm(address(uint160(uint256(keccak256("hevm cheat code")))));
    MockUSDC private token;
    BirdLabSubscriptions private subscriptions;
    address private constant payer = address(0xB1);
    uint256 private constant price = 5_000_000;
    event SubscriptionPurchased(bytes32 indexed orderId, address indexed payer, uint256 indexed planId, uint256 amount, address token);

    function setUp() public {
        vm.chainId(31337);
        token = new MockUSDC();
        subscriptions = new BirdLabSubscriptions(address(token), address(this));
        subscriptions.setPlanPrice(1, price);
        subscriptions.setPlanPrice(2, 10_000_000);
        token.mint(payer, 100_000_000);
        vm.prank(payer);
        token.approve(address(subscriptions), price);
    }

    function order(address who, uint96 nonce) private pure returns (bytes32) { return bytes32((uint256(uint160(who)) << 96) | nonce); }

    function testPurchaseAndEvent() public {
        bytes32 id = order(payer, 1);
        vm.expectEmit(true, true, true, true, address(subscriptions));
        emit SubscriptionPurchased(id, payer, 1, price, address(token));
        vm.prank(payer);
        subscriptions.purchaseSubscription(id, 1);
        (address paidBy, uint256 plan, uint256 amount) = subscriptions.paidOrders(id);
        require(paidBy == payer && plan == 1 && amount == price);
        require(token.balanceOf(address(subscriptions)) == price);
        require(token.allowance(payer, address(subscriptions)) == 0);
    }

    function testInsufficientAllowance() public {
        vm.prank(payer); token.approve(address(subscriptions), price - 1);
        vm.expectRevert(abi.encodeWithSelector(IERC20Errors.ERC20InsufficientAllowance.selector, address(subscriptions), price - 1, price));
        vm.prank(payer); subscriptions.purchaseSubscription(order(payer, 1), 1);
        (address paidBy,,) = subscriptions.paidOrders(order(payer, 1));
        require(paidBy == address(0));
    }

    function testInsufficientBalance() public {
        address empty = address(0xB2);
        vm.prank(empty); token.approve(address(subscriptions), price);
        vm.expectRevert(abi.encodeWithSelector(IERC20Errors.ERC20InsufficientBalance.selector, empty, 0, price));
        vm.prank(empty); subscriptions.purchaseSubscription(order(empty, 1), 1);
    }

    function testInvalidPlan() public {
        vm.expectRevert(BirdLabSubscriptions.InvalidPlan.selector);
        vm.prank(payer); subscriptions.purchaseSubscription(order(payer, 1), 99);
    }

    function testDuplicateDoesNotChargeAgain() public {
        vm.startPrank(payer);
        token.approve(address(subscriptions), price * 2);
        subscriptions.purchaseSubscription(order(payer, 1), 1);
        uint256 balance = token.balanceOf(payer);
        vm.expectRevert(BirdLabSubscriptions.OrderAlreadyPaid.selector);
        subscriptions.purchaseSubscription(order(payer, 1), 2);
        require(token.balanceOf(payer) == balance);
        vm.stopPrank();
    }

    function testFrontrunningWrongPayer() public {
        vm.expectRevert(BirdLabSubscriptions.WrongPayer.selector);
        vm.prank(address(0xB2)); subscriptions.purchaseSubscription(order(payer, 1), 1);
    }

    function testZeroOrder() public {
        vm.expectRevert(BirdLabSubscriptions.InvalidOrder.selector);
        vm.prank(payer); subscriptions.purchaseSubscription(bytes32(0), 1);
    }

    function testOnlyOwnerAdministration() public {
        vm.startPrank(payer);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, payer)); subscriptions.setPlanPrice(1, 1);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, payer)); subscriptions.withdraw(payer, 1);
        vm.expectRevert(abi.encodeWithSelector(Ownable.OwnableUnauthorizedAccount.selector, payer)); subscriptions.pause();
        vm.stopPrank();
    }

    function testWithdrawAndTwoStepOwnership() public {
        vm.prank(payer); subscriptions.purchaseSubscription(order(payer, 1), 1);
        subscriptions.withdraw(address(0xB2), price);
        require(token.balanceOf(address(0xB2)) == price);
        subscriptions.transferOwnership(payer);
        require(subscriptions.owner() == address(this));
        vm.prank(payer); subscriptions.acceptOwnership();
        require(subscriptions.owner() == payer);
    }

    function testPause() public {
        subscriptions.pause();
        vm.expectRevert(Pausable.EnforcedPause.selector);
        vm.prank(payer); subscriptions.purchaseSubscription(order(payer, 1), 1);
        subscriptions.unpause();
        vm.prank(payer); subscriptions.purchaseSubscription(order(payer, 1), 1);
    }

    function testRejectsWrongAmountReceived() public {
        FeeToken fee = new FeeToken();
        BirdLabSubscriptions target = new BirdLabSubscriptions(address(fee), address(this));
        target.setPlanPrice(1, price);
        fee.approve(address(target), price);
        vm.expectRevert(BirdLabSubscriptions.IncorrectAmount.selector);
        target.purchaseSubscription(order(address(this), 1), 1);
        require(fee.balanceOf(address(target)) == 0);
    }

    function testReentrancyBlocked() public {
        ReentrantToken reentrant = new ReentrantToken();
        BirdLabSubscriptions target = new BirdLabSubscriptions(address(reentrant), address(this));
        reentrant.setTarget(target);
        target.setPlanPrice(1, price);
        reentrant.approve(address(target), price);
        target.purchaseSubscription(order(address(this), 1), 1);
        require(reentrant.blocked());
    }

    function testOnlyConfiguredTokenCanPay() public {
        MockUSDC other = new MockUSDC();
        other.mint(address(0xB2), price);
        vm.prank(address(0xB2)); other.approve(address(subscriptions), price);
        vm.expectRevert(abi.encodeWithSelector(IERC20Errors.ERC20InsufficientAllowance.selector, address(subscriptions), 0, price));
        vm.prank(address(0xB2)); subscriptions.purchaseSubscription(order(address(0xB2), 1), 1);
    }

    function testFuzzExactPriceAndOneTimeOrder(uint96 nonce) public {
        bytes32 id = order(payer, nonce);
        vm.prank(payer); subscriptions.purchaseSubscription(id, 1);
        vm.expectRevert(BirdLabSubscriptions.OrderAlreadyPaid.selector);
        vm.prank(payer); subscriptions.purchaseSubscription(id, 1);
        require(token.balanceOf(address(subscriptions)) == price);
    }
}
