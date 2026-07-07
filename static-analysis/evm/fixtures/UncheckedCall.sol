// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

// Known-vulnerable fixture: unchecked low-level call return value. If the
// payout fails, execution continues as if it succeeded.
contract Payroll {
    address[] public employees;
    mapping(address => uint256) public salary;

    function addEmployee(address employee, uint256 amount) external {
        employees.push(employee);
        salary[employee] = amount;
    }

    function payAll() external {
        for (uint256 i = 0; i < employees.length; i++) {
            address employee = employees[i];
            employee.call{value: salary[employee]}("");
        }
    }
}
