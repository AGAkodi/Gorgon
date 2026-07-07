// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Known-vulnerable fixture: privileged function with no access control.
// Anyone can call setOwner() and take over the contract.
contract Treasury {
    address public owner;

    constructor() {
        owner = msg.sender;
    }

    function setOwner(address newOwner) external {
        owner = newOwner;
    }

    function withdraw(uint256 amount) external {
        payable(owner).transfer(amount);
    }
}
