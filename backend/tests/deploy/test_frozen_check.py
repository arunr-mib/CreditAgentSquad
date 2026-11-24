"""The frozen-site comparison reports every difference by path and nothing when unchanged."""
import importlib.util
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "frozen_check", Path(__file__).resolve().parents[3] / "scripts" / "hosted" / "frozen_check.py")
frozen_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(frozen_check)


def test_differences_are_listed_by_path():
    assert frozen_check.differences({"a": {"b": 1}}, {"a": {"b": 2}, "c": 3}) == ["/a/b: 1 -> 2", "/c: None -> 3"]


def test_identical_captures_have_no_differences():
    x = {"a": {"b": [1, "h"]}, "c": None}
    assert frozen_check.differences(x, x) == []
