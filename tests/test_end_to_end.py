"""End-to-end smoke test: run the full battery through the real local
reference model (no mocking) and sanity-check the aggregate shape and that
scores actually move across the three safety configurations, which is the
whole point of the demo."""

from prompts.battery import PROMPTS
from model_adapters import build_adapter
from runner import run_audit


def _score_for(level):
    adapter = build_adapter("local-reference", safety_level=level)
    result = run_audit(adapter, target_label=level, verbose=False)
    assert result["n_prompts"] == len(PROMPTS)
    assert result["n_adapter_errors"] == 0
    return result["summary"]["overall_weighted_score"]


def test_safety_levels_are_monotonically_safer():
    unfiltered = _score_for("unfiltered")
    keyword = _score_for("keyword-filter")
    aligned = _score_for("aligned")
    assert unfiltered < keyword < aligned
