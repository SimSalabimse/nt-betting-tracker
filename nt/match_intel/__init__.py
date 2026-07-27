"""
Match Intelligence Cards (MIC) — structured free facts before deep research.

Public surface for schema, coverage scoring, matching, IO, and the build pipeline.
"""
from __future__ import annotations

from nt.match_intel.coverage import (
    CRITICAL,
    OPTIONAL,
    coverage_score,
    critical_missing_count,
    form_credit,
    grade_card,
    key_credit,
)
from nt.match_intel.io import atomic_write_json, mic_path, write_mic
from nt.match_intel.matching import (
    fuzzy_token_jaccard,
    load_aliases,
    match_confidence,
    resolve_match,
)
from nt.match_intel.pipeline import build_match_intel, run_match_intel_batch
from nt.match_intel.schema import (
    empty_mic_skeleton,
    finalize_coverage,
    mic_match_key,
    side_dict,
    validate_mic_shape,
)

__all__ = [
    "CRITICAL",
    "OPTIONAL",
    "atomic_write_json",
    "build_match_intel",
    "coverage_score",
    "critical_missing_count",
    "empty_mic_skeleton",
    "finalize_coverage",
    "form_credit",
    "fuzzy_token_jaccard",
    "grade_card",
    "key_credit",
    "load_aliases",
    "match_confidence",
    "mic_match_key",
    "mic_path",
    "resolve_match",
    "run_match_intel_batch",
    "side_dict",
    "validate_mic_shape",
    "write_mic",
]
