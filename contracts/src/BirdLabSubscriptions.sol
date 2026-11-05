// SPDX-License-Identifier: MIT
pragma solidity 0.8.30;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import {SafeERC20} from "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Ownable2Step} from "@openzeppelin/contracts/access/Ownable2Step.sol";
import {ReentrancyGuard} from "@openzeppelin/contracts/utils/ReentrancyGuard.sol";
import {Pausable} from "@openzeppelin/contracts/utils/Pausable.sol";

contract BirdLabSubscriptions is Ownable2Step, ReentrancyGuard, Pausable {
    using SafeERC20 for IERC20;

    struct PaidOrder {
        address payer;
        uint256 planId;
        uint256 amount;
    }

    IERC20 public immutable paymentToken;
    mapping(uint256 => uint256) public prices;
    mapping(bytes32 => PaidOrder) public paidOrders;

    error InvalidToken();
    error InvalidOrder();
    error WrongPayer();
    error OrderAlreadyPaid();
    error InvalidPlan();
    error IncorrectAmount();
    error InvalidRecipient();

    event SubscriptionPurchased(bytes32 indexed orderId, address indexed payer, uint256 indexed planId, uint256 amount, address token);
    event PlanPriceUpdated(uint256 indexed planId, uint256 amount);
    event TokensWithdrawn(address indexed recipient, uint256 amount);

    constructor(address token, address initialOwner) Ownable(initialOwner) {
        if (token == address(0) || token.code.length == 0) revert InvalidToken();
        paymentToken = IERC20(token);
    }

    function setPlanPrice(uint256 planId, uint256 amount) external onlyOwner {
        if (planId == 0) revert InvalidPlan();
        prices[planId] = amount;
        emit PlanPriceUpdated(planId, amount);
    }

    function pause() external onlyOwner { _pause(); }
    function unpause() external onlyOwner { _unpause(); }

    function purchaseSubscription(bytes32 orderId, uint256 planId) external nonReentrant whenNotPaused {
        if (orderId == bytes32(0)) revert InvalidOrder();
        if (address(bytes20(orderId)) != msg.sender) revert WrongPayer();
        if (paidOrders[orderId].payer != address(0)) revert OrderAlreadyPaid();
        uint256 amount = prices[planId];
        if (amount == 0) revert InvalidPlan();
        paidOrders[orderId] = PaidOrder(msg.sender, planId, amount);
        uint256 beforeBalance = paymentToken.balanceOf(address(this));
        paymentToken.safeTransferFrom(msg.sender, address(this), amount);
        if (paymentToken.balanceOf(address(this)) - beforeBalance != amount) revert IncorrectAmount();
        emit SubscriptionPurchased(orderId, msg.sender, planId, amount, address(paymentToken));
    }

    function withdraw(address recipient, uint256 amount) external onlyOwner nonReentrant {
        if (recipient == address(0)) revert InvalidRecipient();
        paymentToken.safeTransfer(recipient, amount);
        emit TokensWithdrawn(recipient, amount);
    }
}
