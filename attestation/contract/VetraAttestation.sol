// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @notice Stores hash(chain+address+verdict+timestamp) attestations written
/// by the Vetra verdict pipeline, so any agent/tool can verify a prior
/// verdict without re-running analysis. `target` is a string (not the
/// native `address` type) because Vetra attests addresses on other chains,
/// including ones whose address format isn't a 20-byte EVM address.
contract VetraAttestation {
    address public owner;

    struct Attestation {
        bytes32 verdictHash;
        uint256 timestamp;
    }

    mapping(bytes32 => Attestation) private attestations;

    event VerdictAttested(
        string chain,
        string target,
        bytes32 verdictHash,
        uint256 timestamp
    );

    event OwnershipTransferred(address indexed previousOwner, address indexed newOwner);

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor() {
        owner = msg.sender;
    }

    function _key(string calldata chain, string calldata target) private pure returns (bytes32) {
        // abi.encode (not encodePacked) — two dynamic strings packed without
        // length-prefixing can collide, e.g. ("ev","mFoo") == ("evm","Foo").
        return keccak256(abi.encode(chain, target));
    }

    function attest(
        string calldata chain,
        string calldata target,
        bytes32 verdictHash
    ) external onlyOwner {
        bytes32 key = _key(chain, target);
        attestations[key] = Attestation(verdictHash, block.timestamp);
        emit VerdictAttested(chain, target, verdictHash, block.timestamp);
    }

    function getAttestation(string calldata chain, string calldata target)
        external
        view
        returns (bytes32 verdictHash, uint256 timestamp, bool exists)
    {
        Attestation memory a = attestations[_key(chain, target)];
        return (a.verdictHash, a.timestamp, a.timestamp != 0);
    }

    function transferOwnership(address newOwner) external onlyOwner {
        require(newOwner != address(0), "zero address");
        emit OwnershipTransferred(owner, newOwner);
        owner = newOwner;
    }
}
