// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Known-vulnerable fixture: classic reentrancy (balance decremented after
// the external call, so a malicious receiver can re-enter withdraw()).
contract VulnerableVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient balance");
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
        balances[msg.sender] -= amount;
    }
}
