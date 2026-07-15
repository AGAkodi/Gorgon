// X Layer testnet chain params, used for the wallet_switchEthereumChain /
// wallet_addEthereumChain flow. Chain ID confirmed via a real eth_chainId
// RPC call earlier in this project (0x7a0 = 1952). Explorer URL matches the
// one already used/confirmed elsewhere in this project (TODO.md's on-chain
// verification steps), not a fresh guess.
export const X_LAYER_TESTNET = {
  chainId: '0x7a0',
  chainName: 'X Layer Testnet',
  nativeCurrency: { name: 'OKB', symbol: 'OKB', decimals: 18 },
  rpcUrls: ['https://testrpc.xlayer.tech'],
  blockExplorerUrls: ['https://www.oklink.com/x-layer-testnet'],
}

export const X_LAYER_CHAIN_ID_DECIMAL = 1952

/** Gets window.okxwallet if present, else falls back to window.ethereum
 * (labeled honestly as "other wallet" by the caller — this is not a
 * WalletConnect integration, just generic EIP-1193 fallback). */
export function getInjectedProvider(preferOkx = true) {
  if (typeof window === 'undefined') return null
  if (preferOkx && window.okxwallet) return window.okxwallet
  return window.ethereum || null
}

/** Ensures the given EIP-1193 provider is on X Layer testnet, prompting a
 * switch (and add, if the wallet doesn't know the chain yet) if not. */
export async function ensureXLayerChain(provider) {
  const currentChainId = await provider.request({ method: 'eth_chainId' })
  if (currentChainId?.toLowerCase() === X_LAYER_TESTNET.chainId) return

  try {
    await provider.request({
      method: 'wallet_switchEthereumChain',
      params: [{ chainId: X_LAYER_TESTNET.chainId }],
    })
  } catch (switchError) {
    // 4902 = chain not added to the wallet yet
    if (switchError?.code === 4902) {
      await provider.request({
        method: 'wallet_addEthereumChain',
        params: [X_LAYER_TESTNET],
      })
    } else {
      throw switchError
    }
  }
}
