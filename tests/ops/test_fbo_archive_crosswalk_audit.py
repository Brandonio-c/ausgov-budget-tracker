from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts" / "ops"))

from fbo_archive_crosswalk_audit import (  # noqa: E402
    _abs_amount,
    _fbo_function_amount,
)


def test_fbo_function_amount_prefers_reported_total() -> None:
    values = {
        "Education / Schools": 8,
        "Education / Tertiary": 5,
        "Total Education": 12,
    }
    assert _fbo_function_amount(values, "Education") == (12, "Total Education")


def test_fbo_function_amount_supports_defence_nested_under_gps() -> None:
    values = {"General public services / Defence": 42}
    assert _fbo_function_amount(values, "Defence") == (
        42,
        "General public services / Defence",
    )


def test_fbo_function_amount_sums_children_only_when_total_is_absent() -> None:
    values = {
        "Housing and community amenities / Housing": 8,
        "Housing and community amenities / Environment": 5,
    }
    assert _fbo_function_amount(values, "Housing and community amenities") == (
        13,
        "sum of 2 subfunctions",
    )


def test_abs_amount_accepts_total_label_variant_case_insensitively() -> None:
    assert _abs_amount({"Total education": 53}, "Education") == (
        53,
        "Total Education",
    )
