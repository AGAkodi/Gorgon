# Vetra shared API/MCP pricing configuration (Phase 6)

# Float pricing displayed on the UI and API gateway (vUSD)
VERDICT_PRICE_UI = 0.001
SIMULATION_PRICE_UI = 0.002

# Actual on-chain exact pricing denominated in payment token (18 decimals)
VERDICT_PRICE_WEI = str(int(VERDICT_PRICE_UI * 10**18))
SIMULATION_PRICE_WEI = str(int(SIMULATION_PRICE_UI * 10**18))
