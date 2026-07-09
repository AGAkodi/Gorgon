"""Model providers for the consensus engine.

Each provider takes an AnalysisContext and returns
{"risk_category": ..., "rationale": ...}. Real providers (Anthropic, OpenAI)
call out to the actual APIs; MockProvider is a deterministic stand-in used
when no API key is configured, so the engine can be built and tested before
keys exist. get_default_providers() below is the only place that decides
which is which — fill in .env and real calls activate automatically, no
other code changes needed.
"""
import json
import os
import re
from dataclasses import dataclass, field

from prompt_template import SYSTEM_PROMPT, RISK_CATEGORIES, build_prompt


@dataclass
class AnalysisContext:
    chain: str
    address: str
    source_code: str
    static_findings: list = field(default_factory=list)


class ProviderError(Exception):
    pass


def _parse_json_response(text: str) -> dict:
    """Models sometimes wrap JSON in prose or code fences despite instructions."""
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ProviderError(f"no JSON object found in model response: {text!r}")
    data = json.loads(match.group(0))
    if data.get("risk_category") not in RISK_CATEGORIES:
        raise ProviderError(f"invalid risk_category in model response: {data!r}")
    if "rationale" not in data:
        raise ProviderError(f"missing rationale in model response: {data!r}")
    return {"risk_category": data["risk_category"], "rationale": data["rationale"]}


class ModelProvider:
    name = "base"

    def analyze(self, ctx: AnalysisContext) -> dict:
        raise NotImplementedError


class AnthropicProvider(ModelProvider):
    name = "Claude"

    def __init__(self, model: str = "claude-sonnet-4-5-20250929"):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError("ANTHROPIC_API_KEY not set")
        import anthropic

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def analyze(self, ctx: AnalysisContext) -> dict:
        prompt = build_prompt(ctx.chain, ctx.address, ctx.source_code, ctx.static_findings)
        resp = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(block.text for block in resp.content if block.type == "text")
        return _parse_json_response(text)


class OpenAIProvider(ModelProvider):
    name = "GPT-4"

    def __init__(self, model: str = "gpt-4o"):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ProviderError("OPENAI_API_KEY not set")
        import openai

        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def analyze(self, ctx: AnalysisContext) -> dict:
        prompt = build_prompt(ctx.chain, ctx.address, ctx.source_code, ctx.static_findings)
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        text = resp.choices[0].message.content
        return _parse_json_response(text)


# Findings/rules a real model would treat as an automatic escalation, used
# to give the mock personas defensible (not random) behavior.
_SEVERITY_WEIGHT = {"critical": 3, "high": 2, "medium": 1, "low": 0, "info": 0}


class MockProvider(ModelProvider):
    """Deterministic stand-in for a real LLM, so the consensus engine's
    parallel execution, consensus, and disagreement logic can be built and
    tested end-to-end before API keys exist. Two personas are intentionally
    different: 'conservative' escalates on any low-level external call
    regardless of context, 'balanced' reasons about checks-effects-
    interactions ordering — the same kind of genuine disagreement real
    models produce on borderline contracts.
    """

    def __init__(self, name: str, persona: str = "balanced"):
        self.name = name
        self.persona = persona

    def analyze(self, ctx: AnalysisContext) -> dict:
        findings = ctx.static_findings
        rules = {f["rule"] for f in findings}
        max_weight = max((_SEVERITY_WEIGHT.get(f["severity"], 0) for f in findings), default=0)

        if self.persona == "conservative":
            # Flags any external call pattern as risky regardless of ordering.
            if "reentrancy-eth" in rules or max_weight >= 3:
                return {
                    "risk_category": "critical",
                    "rationale": "External call combined with state changes; treating as exploitable regardless of surrounding checks.",
                }
            if rules & {"low-level-calls", "unchecked-lowlevel", "calls-loop"}:
                return {
                    "risk_category": "high_risk",
                    "rationale": "Low-level external call present; can't rule out reentrancy or unchecked-failure risk from static shape alone.",
                }
            if max_weight >= 1:
                return {
                    "risk_category": "caution",
                    "rationale": "Minor findings present; nothing severe but worth a second look.",
                }
            return {"risk_category": "safe", "rationale": "No externally-reachable risk patterns found."}

        # "balanced" persona: reasons about severity rather than pattern presence alone.
        if max_weight >= 3 or "reentrancy-eth" in rules:
            return {
                "risk_category": "critical",
                "rationale": "Static findings indicate a high-confidence exploitable pattern.",
            }
        if max_weight == 2:
            return {
                "risk_category": "high_risk",
                "rationale": "A high-severity finding is present; likely exploitable but not certain without deeper review.",
            }
        if max_weight == 1:
            return {
                "risk_category": "caution",
                "rationale": "Only low-severity findings; unlikely to be exploitable but worth noting.",
            }
        return {"risk_category": "safe", "rationale": "No security-relevant findings beyond informational."}


def get_default_providers() -> list:
    """The only place that decides real vs. mock. Add ANTHROPIC_API_KEY /
    OPENAI_API_KEY to .env and these swap to live models automatically."""
    providers = []

    if os.environ.get("ANTHROPIC_API_KEY"):
        providers.append(AnthropicProvider())
    else:
        providers.append(MockProvider("Claude", persona="conservative"))

    if os.environ.get("OPENAI_API_KEY"):
        providers.append(OpenAIProvider())
    else:
        providers.append(MockProvider("GPT-4", persona="balanced"))

    # Third opinion, always mock for now — swap for a real third model
    # (e.g. another Anthropic model, Gemini) by replacing this line.
    providers.append(MockProvider("Consensus-3", persona="balanced"))

    return providers
