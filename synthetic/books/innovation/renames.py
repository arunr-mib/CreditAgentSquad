"""The eight clients renamed on 22 November 2026 (owner decision; web check in docs/product/name-check-2026-11-22.md).

A client's random draws, and the credit officer who approved its terms, are chosen from a code. For these eight it is
the code the client had when the owner signed its answer-key rows, so the rename changes names and codes only, never a
figure or a signer. This module is the one place the old
codes are kept on purpose; nothing here is shown to a user."""

from __future__ import annotations

# new code -> the code the client's draws have always been chosen by
SEED_CODE: dict[str, str] = {
    "datamarrow": "dataflake",
    "tarnavi-ai": "quillon-ai",
    "calvere-health": "lumora-health",
    "tavernel-grid": "halcyon-grid",
    "vantrell-labs": "tessaract-labs",
    "meridew-analytics": "corvane-analytics",
    "brackmere-medical": "tidewell-medical",
    "cindrel-tech": "stripple-tech",
}

RENAMED_ON = "2026-11-22"


def seed_code(client_id: str) -> str:
    """The code a client's draws and approving officer are chosen by (its own code unless it was renamed)."""
    return SEED_CODE.get(client_id, client_id)
