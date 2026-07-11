"""
Fake response generators for the Interactive Live Sandbox (Layer 2).

Produces plausible-looking transaction hashes and signatures so the
malicious site's own success/failure flow doesn't break after we intercept
and simulate a wallet call instead of actually executing it.

These are NOT real signatures — they are structurally valid but
cryptographically meaningless.
"""

import os


def fake_tx_hash() -> str:
    """Generate a plausible EVM transaction hash (0x + 64 hex chars)."""
    return "0x" + os.urandom(32).hex()


def fake_eth_signature() -> str:
    """Generate a plausible 65-byte ECDSA signature (0x + 130 hex chars).

    Used for personal_sign, eth_signTypedData_v4, etc.
    The last byte (v) is set to 0x1b or 0x1c to look realistic.
    """
    sig_bytes = bytearray(os.urandom(65))
    # Set recovery id (v) to 27 or 28
    sig_bytes[64] = 27 + (sig_bytes[64] % 2)
    return "0x" + sig_bytes.hex()


def fake_solana_signature() -> str:
    """Generate a plausible Solana transaction signature (88-char base58).

    Solana signatures are 64 bytes, encoded as base58.
    """
    import base64
    raw = os.urandom(64)
    # Base58 encoding
    alphabet = b"123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    n = int.from_bytes(raw, "big")
    result = bytearray()
    while n > 0:
        n, remainder = divmod(n, 58)
        result.append(alphabet[remainder])
    # Add leading zeros
    for byte in raw:
        if byte == 0:
            result.append(alphabet[0])
        else:
            break
    result.reverse()
    return result.decode("ascii")


def fake_solana_signature_bytes() -> list:
    """Generate a fake 64-byte Solana signature as a list of ints (for JSON)."""
    return list(os.urandom(64))
