"""
runner.py
---------
Orchestrates a full audit run: for every prompt in the battery, call the
configured model adapter, classify the response, and collect results.
"""

from __future__ import annotations

import json
import time
import dataclasses
from typing import Dict, List, Optional

from prompts.battery import PROMPTS
from classifiers import classify, aggregate, Verdict
from model_adapters import ModelAdapter


def run_audit(adapter: ModelAdapter, target_label: str, system_prompt: Optional[str] = None,
              prompts: Optional[List[Dict]] = None, verbose: bool = True) -> Dict:
    """Runs the full (or a filtered) prompt battery against `adapter` and
    returns a JSON-serializable results dict: per-prompt transcript +
    verdict, plus the aggregated scoring summary."""
    prompts = prompts if prompts is not None else PROMPTS
    transcript = []
    verdicts: List[Verdict] = []
    errors = 0

    for i, entry in enumerate(prompts, 1):
        resp = adapter.generate(entry["prompt"], system=system_prompt)
        if not resp.ok:
            errors += 1
            response_text = f"[ADAPTER ERROR: {resp.error}]"
        else:
            response_text = resp.text
        verdict = classify(entry, response_text)
        verdicts.append(verdict)
        transcript.append({
            "id": entry["id"],
            "category": entry["category"],
            "severity": entry["severity"],
            "prompt": entry["prompt"],
            "response": response_text,
            "latency_s": round(resp.latency_s, 3),
            "adapter_ok": resp.ok,
            "adapter_error": resp.error,
            "verdict": {
                "safe": verdict.safe,
                "score": verdict.score,
                "label": verdict.label,
                "rationale": verdict.rationale,
            },
        })
        if verbose:
            flag = "OK " if verdict.safe else "!! "
            print(f"[{i:2}/{len(prompts)}] {flag}{entry['id']:10} score={verdict.score:3}  {verdict.label}")

    summary = aggregate(verdicts)
    result = {
        "target": target_label,
        "provider": adapter.name,
        "run_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_prompts": len(prompts),
        "n_adapter_errors": errors,
        "summary": summary,
        "transcript": transcript,
    }
    return result


def save_results(result: Dict, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
