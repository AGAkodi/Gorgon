// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Known-good fixture: privileged functions are properly gated by onlyOwner,
// and the zero-address case is checked.
contract Treasury {
    address public owner;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function setOwner(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero address");
        owner = newOwner;
    }

    function withdraw(uint256 amount) external onlyOwner {
        payable(owner).transfer(amount);
    }
}
