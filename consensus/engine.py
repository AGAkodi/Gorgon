"""Multi-model consensus engine (Phase 2).

Runs each configured provider in parallel on the same contract context,
then combines their {risk_category, rationale} outputs into a single
verdict + confidence. Disagreement is a signal, not noise: when models
don't agree, the overall verdict is the *most severe* category among them
(fail closed, not averaged away), confidence is dampened accordingly, and
the full disagreement is appended to a log for later corpus review
(Phase 9's flywheel).
"""
import json
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from providers import AnalysisContext, ProviderError, get_default_providers

SEVERITY_ORDER = {"safe": 0, "caution": 1, "high_risk": 2, "critical": 3}

DISAGREEMENT_LOG = Path(__file__).parent / "data" / "disagreements.jsonl"


def _run_one(provider, ctx: AnalysisContext) -> dict:
    result = provider.analyze(ctx)
    return {"model": provider.name, "risk_category": result["risk_category"], "rationale": result["rationale"]}


def run_consensus(ctx: AnalysisContext, providers=None) -> dict:
    providers = providers if providers is not None else get_default_providers()

    model_consensus = []
    errors = []
    with ThreadPoolExecutor(max_workers=len(providers)) as pool:
        futures = {pool.submit(_run_one, p, ctx): p for p in providers}
        for future, provider in futures.items():
            try:
                model_consensus.append(future.result())
            except ProviderError as exc:
                errors.append({"model": provider.name, "error": str(exc)})

    if not model_consensus:
        raise RuntimeError(f"all providers failed: {errors}")

    categories = [r["risk_category"] for r in model_consensus]
    counts = Counter(categories)
    majority_category, majority_count = counts.most_common(1)[0]
    agreement_ratio = majority_count / len(categories)
    disagreement = len(counts) > 1

    if disagreement:
        # Fail closed: the overall verdict is the most severe category any
        # model raised, not the majority and not an average.
        overall = max(categories, key=lambda c: SEVERITY_ORDER[c])
        confidence = round(agreement_ratio * 0.7, 2)
    else:
        overall = majority_category
        confidence = round(agreement_ratio, 2)

    result = {
        "verdict": overall,
        "confidence": confidence,
        "model_consensus": model_consensus,
        "disagreement": disagreement,
    }

    if disagreement:
        _log_disagreement(ctx, result)

    if errors:
        result["provider_errors"] = errors

    return result


def _log_disagreement(ctx: AnalysisContext, result: dict) -> None:
    DISAGREEMENT_LOG.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "chain": ctx.chain,
        "address": ctx.address,
        "static_findings": ctx.static_findings,
        "model_consensus": result["model_consensus"],
        "resolved_verdict": result["verdict"],
    }
    with open(DISAGREEMENT_LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
