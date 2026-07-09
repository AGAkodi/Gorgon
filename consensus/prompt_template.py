"""Structured prompt template for the multi-model consensus engine.

Contract context + Phase 1 static findings go in; each model is asked to
independently produce {risk_category, rationale} for the same input.
"""
import json

RISK_CATEGORIES = ["safe", "caution", "high_risk", "critical"]

SYSTEM_PROMPT = """You are a smart contract security reviewer. You are given a \
contract's source and a list of findings from an automated static analyzer. \
Form your own independent judgment — the static findings are input, not a \
conclusion to rubber-stamp. Static analysis catches known patterns; it \
misses things like missing access control on state-changing functions, so \
read the source yourself.

Respond with strict JSON only, no prose outside the JSON object, in exactly \
this shape:

{"risk_category": "safe|caution|high_risk|critical", "rationale": "one or two sentences"}

risk_category must be exactly one of: safe, caution, high_risk, critical."""


def build_prompt(chain: str, address: str, source_code: str, static_findings: list) -> str:
    findings_json = json.dumps(static_findings, indent=2)
    return f"""Chain: {chain}
Address: {address}

Static analyzer findings:
{findings_json}

Contract source:
```solidity
{source_code}
```

Assess this contract's risk and respond with the JSON object described in \
your instructions."""
