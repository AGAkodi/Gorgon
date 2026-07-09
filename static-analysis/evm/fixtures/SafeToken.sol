// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Known-good fixture: plain balance-ledger transfer, no external calls, no
// privileged functions — nothing for a security scan to legitimately flag.
contract SimpleToken {
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;

    constructor(uint256 initialSupply) {
        totalSupply = initialSupply;
        balanceOf[msg.sender] = initialSupply;
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}
