// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Known-good fixture: checks-effects-interactions done correctly — balance
// is decremented before the external call, so reentrancy can't drain it.
contract SafeVault {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    function withdraw(uint256 amount) external {
        require(balances[msg.sender] >= amount, "insufficient balance");
        balances[msg.sender] -= amount;
        (bool ok, ) = msg.sender.call{value: amount}("");
        require(ok, "transfer failed");
    }
}
