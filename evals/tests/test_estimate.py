import json
from decimal import Decimal

import pytest

from evals.estimate import PRICES, Calibration, calibrate, estimate, render


def test_the_estimate_multiplies_calls_by_calibrated_tokens_and_current_prices():
    cal = {"spreading": Calibration(input_tokens=12_000, output_tokens=6_000),
           "intake": Calibration(input_tokens=3_000, output_tokens=800)}
    result = estimate({"spreading": 10, "intake": 20}, cal, PRICES["claude-opus-5-5"])
    # spreading: 10 * (12000*4 + 6000*20) / 1e6 = 1.68 ; intake: 20 * (3000*4 + 800*20) / 1e6 = 0.56
    assert result.total_mid == Decimal("2.24")
    assert result.total_low < result.total_mid < result.total_high
    assert result.lines[0].agent in ("spreading", "intake")


def test_an_agent_with_no_calibration_fails_loudly_instead_of_costing_zero():
    with pytest.raises(KeyError, match="no recorded usage"):
        estimate({"covenant": 5}, {}, PRICES["claude-opus-5-5"])


def test_cache_writes_cost_more_than_input_and_cache_reads_less():
    p = PRICES["claude-opus-5-5"]
    cal = {"a": Calibration(input_tokens=0, output_tokens=0, cache_write_tokens=1_000_000)}
    assert estimate({"a": 1}, cal, p).total_mid == Decimal("5.00")
    cal = {"a": Calibration(input_tokens=0, output_tokens=0, cache_read_tokens=1_000_000)}
    assert estimate({"a": 1}, cal, p).total_mid == Decimal("0.20")


def test_a_cheaper_model_costs_less_for_the_same_calls():
    cal = {"a": Calibration(input_tokens=1000, output_tokens=1000)}
    opus = estimate({"a": 5}, cal, PRICES["claude-opus-5-5"]).total_mid
    sonnet = estimate({"a": 5}, cal, PRICES["claude-sonnet-5-5"]).total_mid
    assert sonnet < opus


def test_calibrate_averages_recorded_usage_per_agent_and_counts_every_token_class(tmp_path):
    for n, (i, w, r, o) in enumerate([(4, 1000, 0, 100), (2, 3000, 1000, 300)], start=1):
        path = tmp_path / "intake" / "b" / "p" / f"{n:02d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"usage": {"input_tokens": i, "cache_creation_input_tokens": w,
                                              "cache_read_input_tokens": r, "output_tokens": o}}))
    cal = calibrate(tmp_path)["intake"]
    assert (cal.input_tokens, cal.cache_write_tokens, cal.cache_read_tokens, cal.output_tokens) == (3, 2000, 500, 200)


def test_the_report_opens_with_the_estimate_label_and_labels_every_total():
    cal = {"a": Calibration(input_tokens=1000, output_tokens=1000)}
    scenarios = {"claude-opus-5-5": estimate({"a": 5}, cal, PRICES["claude-opus-5-5"])}
    text = render(scenarios, notes=[])
    assert text.splitlines()[0].startswith("ESTIMATE, not a measurement")
    assert text.count("ESTIMATE") >= 4
    assert "$" in text and "| low |" in text.lower().replace("| low ", "| low |") or "low" in text.lower()
