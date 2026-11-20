"""The v1 book is frozen (design spec 2.3): the existing engine tests run on it, and the kept four rest on it.

A failure here means a legacy generator file changed. If that was deliberate, say so in the commit, regenerate
`synthetic/out`, have the owner re-sign what moved, and update the digests below; never edit the key to make it pass."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "__init__.py": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "book.py": "df0bcbab44f214b92a72b4b17d7dad6e5b8df155d202f0c0545b65ed7672e674",
    "certificates.py": "b0983ffc3002f73585ed40159266c0fa4fa13fa0dc99646016afb1f0fab55177",
    "collateral.py": "3b8eead1e2e44b7768d81c18f1df38b571b234e044d93fcda69d1f05745e14c7",
    "expected.py": "50538df6a5cb1d322ebec8dec62d53b435d5045ebe32644136820348cdcf421a",
    "generate.py": "b31db0b252a2f3c2e1b3dee44c0a7871c8195cd3be122f83ff056c058fb36588",
    "model.py": "34c97762adce57b51766fb7387e9c587d2e1df96f353c3638d7c20f9e482087d",
    "scenarios.py": "401832e5c62e8e65e7f333fc982fd1866e9815c70f88fbb8d65d31b1aad97d47",
    "terms.py": "b14b53d5d12237ef9ef71509603efa62401524c885a466e4af75d5d156abe832",
    "render/__init__.py": "809d3245e0ac45db447987b20af07c15101fd4373c6084202a8f7ff9b2712550",
    "render/certificates.py": "5f46348d615eb03d1498f65cabbf924f36b97e0e575c05ada45e158f0b97ab53",
    "render/common.py": "42a797bceb6f12b96f2ebf49e010c4edb3327c0a24494bd07852a573ade4a668",
    "render/legal.py": "5950ae6a3db6290a810f672a47411c9027cc21e943cfb9beec4f3e48105ad388",
    "render/statements.py": "4d95875ce13e5492a4d261006a979842a48f4bf02b89891e9dc1dabd7082a2cc",
}  # fmt: skip
TRUTH = {
    "kestrel-bay-packaging": "9d08a6c314ecee174eddc578885efd213de7b859bf22a9358f9eb6e543e23b10",
    "harrowgate-precision": "7244c3d51b3c1bfc7882997c407902d45b5a25698431cdbc1758b172eb4809c1",
    "briarstone-beverage": "4931dc641fdd5836a1228f68546ce075706d75e99f0144fda044bdb434525e3a",
    "pellham-grain": "eca053369d10b150700ac45e41eb5c2fa570cac412843210c6bd7f99b65d19fe",
}  # fmt: skip


@pytest.mark.parametrize("name", sorted(SOURCES))
def test_legacy_source_is_unchanged(name):
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == SOURCES[name], f"synthetic/{name} changed"


@pytest.mark.parametrize("borrower_id", sorted(TRUTH))
def test_kept_truth_files_are_unchanged(borrower_id):
    path = ROOT / "out" / "truth" / f"{borrower_id}.json"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == TRUTH[borrower_id]
