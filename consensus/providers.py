"""Model providers for the consensus engine.

Each provider takes an AnalysisContext and returns
{"risk_category": ..., "rationale": ...}. Real providers (Groq, Gemini,
Anthropic, OpenAI) call out to the actual APIs; MockProvider is a
deterministic stand-in used when no API key is configured, so the engine
can be built and tested before keys exist. get_default_providers() below
is the only place that decides which is which — fill in .env and real
calls activate automatically, no other code changes needed.
"""
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Load .env ourselves rather than relying on whatever imports this module
# to have loaded it first — get_default_providers() silently fell back to
# mock even with a real GROQ_API_KEY in .env when this module was imported
# standalone (e.g. running a consensus script directly rather than through
# the full pipeline, which happens to load attestation/env.py first).
sys.path.insert(0, str(Path(__file__).parent.parent / "attestation"))
import env  # noqa: E402,F401 (loads .env into os.environ on import)

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


class GroqProvider(ModelProvider):
    name = "Groq"

    def __init__(self, model: str = None):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ProviderError("GROQ_API_KEY not set")
        import groq

        self._client = groq.Groq(api_key=api_key)
        # Groq's model catalog turns over fast and sources disagreed on
        # what's current as of this writing (some call llama-3.3-70b-
        # versatile current, Groq's own docs elsewhere say it's deprecated
        # in favor of openai/gpt-oss-120b) — couldn't verify against a live
        # key. Configurable via GROQ_MODEL so whoever adds a real key can
        # check console.groq.com/docs/models and override without a code
        # change, rather than trust a hardcoded name that may be stale.
        # (An empty-but-present GROQ_MODEL= in .env must fall through to
        # the default too, not just an absent one — os.environ.get()'s
        # default only kicks in when the key is missing entirely.)
        self._model = model or os.environ.get("GROQ_MODEL") or "openai/gpt-oss-120b"

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


class GeminiProvider(ModelProvider):
    name = "Gemini"

    def __init__(self, model: str = None):
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise ProviderError("GEMINI_API_KEY not set")
        from google import genai

        self._client = genai.Client(api_key=api_key)
        # Same caveat as Groq above — verify at ai.google.dev/gemini-api/docs/models
        # before relying on this default; override via GEMINI_MODEL. Same
        # empty-string-vs-absent fix as Groq's model resolution above.
        self._model = model or os.environ.get("GEMINI_MODEL") or "gemini-2.5-flash"

    def analyze(self, ctx: AnalysisContext) -> dict:
        from google.genai.types import GenerateContentConfig

        prompt = build_prompt(ctx.chain, ctx.address, ctx.source_code, ctx.static_findings)
        resp = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
        )
        return _parse_json_response(resp.text)


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


# (identifier, env var, provider class) — priority order used to fill each
# consensus slot below. Same identifier is never used twice across slots,
# so having only one real key configured doesn't silently ask the same
# model the same question 3x under different slot names (that would
# fabricate "agreement" instead of real independent judgment).
_CANDIDATES = [
    ("groq", "GROQ_API_KEY", GroqProvider),
    ("gemini", "GEMINI_API_KEY", GeminiProvider),
    ("anthropic", "ANTHROPIC_API_KEY", AnthropicProvider),
    ("openai", "OPENAI_API_KEY", OpenAIProvider),
]


def _pick_real_provider(priority_order: list, used: set):
    """Returns the first not-yet-used candidate (by identifier) from
    priority_order that has its API key configured, or None."""
    by_id = {c[0]: c for c in _CANDIDATES}
    for identifier in priority_order:
        if identifier in used:
            continue
        _, env_var, cls = by_id[identifier]
        if os.environ.get(env_var):
            used.add(identifier)
            return cls()
    return None


def get_default_providers() -> list:
    """The only place that decides real vs. mock. Add GROQ_API_KEY /
    GEMINI_API_KEY / ANTHROPIC_API_KEY / OPENAI_API_KEY to .env and these
    swap to live models automatically — no other code changes needed.

    Stack: Groq primary, Gemini/Anthropic fallback (per TODO.md Phase 5).
    Each slot tries its priority list in order, skipping any identifier
    already used by an earlier slot, and falls back to a mock persona only
    if nothing real is left to try.
    """
    used = set()
    providers = []

    p = _pick_real_provider(["groq", "gemini", "anthropic"], used)
    providers.append(p or MockProvider("Groq", persona="conservative"))

    p = _pick_real_provider(["gemini", "anthropic", "groq"], used)
    providers.append(p or MockProvider("Gemini", persona="balanced"))

    p = _pick_real_provider(["anthropic", "openai", "groq", "gemini"], used)
    providers.append(p or MockProvider("Consensus-3", persona="balanced"))

    return providers
