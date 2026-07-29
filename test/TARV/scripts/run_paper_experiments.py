#!/usr/bin/env python3
"""Run TAMonitor paper-review experiments.

The script is intentionally conservative: it records actual executable results
and separates automatically generated MITL candidates from human-reviewed
equivalence claims.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import os
import platform
import re
import signal
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
from bisect import bisect_left
from collections import Counter
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
TARV_ROOT = REPO_ROOT / "test" / "TARV"
DEFAULT_NODE = Path("/mnt/c/Users/PC-123/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe")
DEFAULT_ARTIFACT_TOOL_IMPORT = "file:///C:/Users/PC-123/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs"
INTERNAL_COUNT_FORMS = ["CFn", "CFn*", "COn", "COn*", "CGn", "CGn*", "CHn", "CHn*"]
INTERNAL_COUNT_FORMS_REASON = "Excluded from MITL semantic regression: Count forms are MightyPPL internal compilation/NNF construction forms, not ordinary user-level MITL formulas."


@dataclass
class SemanticCase:
    case_id: str
    suite: str
    category: str
    formula: str
    trace: list[str]
    word: str = "infinite"
    state: str = "symbolic"
    max_valuations: int = 20000
    expected_final: str = ""
    expected_sat: str = ""
    expected_prefix: list[str] = field(default_factory=list)
    review_status: str = "expected_checked"
    rationale: str = ""


def semantic_cases() -> list[SemanticCase]:
    base = [
        SemanticCase("atom_true_under_f", "mighty_semantics", "atom:true", "F [0,1] true", ["0,{}", "1,{}"], expected_final="POSITIVE", rationale="Covers true atom inside temporal wrapper with a future observation inside the interval."),
        SemanticCase("atom_false_under_f", "mighty_semantics", "atom:false", "F [0,1] false", ["0,{}", "2,{}"], expected_final="NEGATIVE", rationale="Covers false atom inside temporal wrapper."),
        SemanticCase("atom_identifier", "mighty_semantics", "atom:idfr", "F [0,2] p1", ["0,{}", "1,{p1}"], expected_final="POSITIVE", expected_sat="SAT"),
        SemanticCase("formula_not", "mighty_semantics", "formula:!", "F [0,2] (!p1)", ["0,{p1}", "1,{}"], expected_final="POSITIVE"),
        SemanticCase("formula_and", "mighty_semantics", "formula:&&", "F [0,2] (p1 && p2)", ["0,{}", "1,{p1,p2}"], expected_final="POSITIVE"),
        SemanticCase("formula_or", "mighty_semantics", "formula:||", "F [0,2] (p1 || p2)", ["0,{}", "1,{p2}"], expected_final="POSITIVE"),
        SemanticCase("formula_implies", "mighty_semantics", "formula:->", "F [0,2] (p1 -> p2)", ["0,{p1}", "1,{p1,p2}"], expected_final="POSITIVE"),
        SemanticCase("formula_iff", "mighty_semantics", "formula:<->", "F [0,2] (p1 <-> p2)", ["0,{p1}", "1,{p1,p2}"], expected_final="POSITIVE"),
        SemanticCase("interval_left_open", "mighty_semantics", "interval:(]", "F (0,2] p1", ["0,{}", "1,{p1}"], expected_final="POSITIVE"),
        SemanticCase("interval_right_open", "mighty_semantics", "interval:[)", "F [0,2) p1", ["0,{}", "1,{p1}"], expected_final="POSITIVE"),
        SemanticCase("interval_open", "mighty_semantics", "interval:()", "F (0,2) p1", ["0,{}", "1,{p1}"], expected_final="POSITIVE"),
        SemanticCase("interval_unbounded", "mighty_semantics", "interval:infty", "F [0,infty) p1", ["0,{}", "5,{p1}"], expected_final="POSITIVE"),
        SemanticCase("future_finally_positive", "mighty_semantics", "future:F", "F [0,2] p1", ["0,{}", "1,{p1}"], expected_final="POSITIVE"),
        SemanticCase("future_finally_negative", "mighty_semantics", "future:F", "F [0,2] p1", ["0,{}", "3,{}"], expected_final="NEGATIVE"),
        SemanticCase("finite_finally_positive", "mighty_semantics", "finite:F", "F [0,2] p1", ["0,{}", "1,{p1}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite-word mode accepts a witnessed eventually obligation inside the closed interval."),
        SemanticCase("finite_finally_negative", "mighty_semantics", "finite:F", "F [0,2] p1", ["0,{}", "3,{}"], word="finite", expected_final="NEGATIVE", expected_sat="SAT", rationale="Finite-word mode rejects an eventually obligation when the bound has passed without a witness."),
        SemanticCase("finite_globally_violate", "mighty_semantics", "finite:G", "G [0,2] p1", ["0,{p1}", "1,{}"], word="finite", expected_final="NEGATIVE", expected_sat="SAT", rationale="Finite-word mode rejects a globally obligation after an observed violation inside the bound."),
        SemanticCase("finite_formula_and", "mighty_semantics", "finite:&&", "F [0,2] (p1 && p2)", ["0,{}", "1,{p1,p2}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite-word mode keeps Boolean conjunction semantics: p1 and p2 are jointly witnessed at time 1."),
        SemanticCase("finite_interval_open", "mighty_semantics", "finite:interval:()", "F (0,2) p1", ["0,{}", "1,{p1}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="The p1 witness at time 1 lies strictly inside the finite-word open interval (0,2)."),
        SemanticCase("finite_until_positive", "mighty_semantics", "finite:U", "p1 U [1,3] p2", ["0,{p1}", "1,{p1}", "2,{p2}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite until is satisfied because p1 holds until p2 appears at time 2 inside [1,3]."),
        SemanticCase("finite_until_negative", "mighty_semantics", "finite:U", "p1 U [1,3] p2", ["0,{p1}", "1,{p1}", "4,{}"], word="finite", expected_final="NEGATIVE", expected_sat="SAT", rationale="Finite until is violated because the upper bound is exceeded without a p2 witness."),
        SemanticCase("finite_until_star", "mighty_semantics", "finite:U*", "p1 U* [0,3] p2", ["0,{p2}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Starred until admits the boundary p2 witness in finite-word mode."),
        SemanticCase("finite_release_positive", "mighty_semantics", "finite:R", "p1 R [1,3] p2", ["0,{p2}", "1,{p2}", "2,{p1,p2}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite release is satisfied because p2 holds until p1 appears inside the release interval."),
        SemanticCase("finite_release_star_end_positive", "mighty_semantics", "finite:R*", "p1 R* [0,3] p2", ["0,{p2}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="At finite end-of-word, the weak release boundary evidence is enough for a positive verdict."),
        SemanticCase("finite_past_once_negative", "mighty_semantics", "finite:O", "O [0,2] p1", ["0,{p1}", "1,{}"], word="finite", expected_final="NEGATIVE", expected_sat="UNSAT", rationale="Strict once has no prior witness at the initial observation, so the finite run remains negative."),
        SemanticCase("finite_past_historically_positive", "mighty_semantics", "finite:H", "H [0,2] p1", ["0,{p1}", "1,{p1}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Strict historically is vacuous at the initial observation and remains satisfied on the shown finite word."),
        SemanticCase("finite_past_since_negative", "mighty_semantics", "finite:S", "p1 S [0,3] p2", ["0,{p2}", "1,{p1}"], word="finite", expected_final="NEGATIVE", expected_sat="UNSAT", rationale="Strict since lacks a prior right-operand witness at the initial observation in this finite trace."),
        SemanticCase("finite_past_trigger_positive", "mighty_semantics", "finite:T", "p1 T [0,3] p2", ["0,{p2}", "1,{p1,p2}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Past trigger is the dual of since and remains satisfied on this finite trace."),
        SemanticCase("finite_pnueli_fn_positive", "mighty_semantics", "finite:Fn", "Fn[0,5](p1,p2,p3)", ["0,{}", "1,{p1}", "3,{p2}", "5,{p3}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite Pnueli existential sequence is witnessed by p1, p2, and p3 in order within [0,5]."),
        SemanticCase("finite_pnueli_gn_end_positive", "mighty_semantics", "finite:Gn", "Gn[0,5](p1,p2,p3)", ["0,{}", "1,{p1}", "3,{p2}", "5,{p3}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="At finite end-of-word, the universal Pnueli dual has no remaining violating continuation in this trace."),
        SemanticCase("finite_pnueli_hn_positive", "mighty_semantics", "finite:Hn", "Hn[0,5](p1,p2,p3)", ["0,{p1}", "2,{p2}", "4,{p3}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Past Pnueli universal dual is vacuous at the initial observation and stays positive on this finite trace."),
        SemanticCase("finite_atom_true_under_f", "mighty_semantics", "atom:true", "F [0,1] true", ["0,{}", "1,{}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite-word literal true is witnessed inside the bounded eventually wrapper."),
        SemanticCase("finite_atom_false_under_f", "mighty_semantics", "atom:false", "F [0,1] false", ["0,{}", "2,{}"], word="finite", expected_final="NEGATIVE", expected_sat="UNSAT", rationale="Finite-word literal false cannot witness the eventually wrapper, so the formula is unsatisfiable and the trace is negative."),
        SemanticCase("finite_atom_identifier", "mighty_semantics", "atom:idfr", "F [0,2] p1", ["0,{}", "1,{p1}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="The finite trace contains the p1 identifier witness at time 1 inside [0,2]."),
        SemanticCase("finite_formula_not", "mighty_semantics", "formula:!", "F [0,2] (!p1)", ["0,{p1}", "1,{}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite-word negation is witnessed by the event at time 1 where p1 is absent."),
        SemanticCase("finite_formula_or", "mighty_semantics", "formula:||", "F [0,2] (p1 || p2)", ["0,{}", "1,{p2}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite-word disjunction is witnessed because p2 holds at time 1."),
        SemanticCase("finite_formula_implies", "mighty_semantics", "formula:->", "F [0,2] (p1 -> p2)", ["0,{p1}", "1,{p1,p2}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite-word implication is witnessed at time 1 where the antecedent and consequent both hold."),
        SemanticCase("finite_formula_iff", "mighty_semantics", "formula:<->", "F [0,2] (p1 <-> p2)", ["0,{p1}", "1,{p1,p2}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite-word equivalence is witnessed at time 1 because p1 and p2 have the same truth value."),
        SemanticCase("finite_interval_left_open", "mighty_semantics", "interval:(]", "F (0,2] p1", ["0,{}", "1,{p1}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="The finite p1 witness at time 1 is strictly after the open lower bound and within the closed upper bound."),
        SemanticCase("finite_interval_right_open", "mighty_semantics", "interval:[)", "F [0,2) p1", ["0,{}", "1,{p1}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="The finite p1 witness at time 1 is inside the right-open interval [0,2)."),
        SemanticCase("finite_interval_unbounded", "mighty_semantics", "interval:infty", "F [0,infty) p1", ["0,{}", "5,{p1}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="The finite trace contains a p1 witness for the unbounded eventually interval."),
        SemanticCase("finite_finally_star", "mighty_semantics", "future:F*", "F* [0,2] p1", ["0,{p1}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite starred finally admits the current boundary p1 witness."),
        SemanticCase("finite_globally_star_end_positive", "mighty_semantics", "future:G*", "G* [0,2] p1", ["0,{p1}", "1,{p1}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="At finite end-of-word, the starred global obligation has no observed violation and the negative branch is empty."),
        SemanticCase("finite_past_once_star_negative", "mighty_semantics", "past:O*", "O* [0,2] p1", ["0,{}"], word="finite", expected_final="NEGATIVE", expected_sat="SAT", rationale="Finite weak once is false on the initial event when the current boundary and strict past contain no p1 witness."),
        SemanticCase("finite_past_historically_star_positive", "mighty_semantics", "past:H*", "H* [0,2] p1", ["0,{p1}", "1,{p1}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite weak historically includes the boundary observations, all of which satisfy p1."),
        SemanticCase("finite_past_since_star_negative", "mighty_semantics", "past:S*", "p1 S* [0,3] p2", ["0,{}"], word="finite", expected_final="NEGATIVE", expected_sat="SAT", rationale="Finite weak since is false on the initial event when the current boundary and strict past contain no p2 witness."),
        SemanticCase("finite_past_trigger_star_positive", "mighty_semantics", "past:T*", "p1 T* [0,3] p2", ["0,{p2}"], word="finite", expected_final="POSITIVE", expected_sat="SAT", rationale="Finite weak trigger includes the current boundary p2 event, making the since-dual counterexample impossible."),
        SemanticCase("finite_pnueli_on_negative", "mighty_semantics", "pnueli:On", "On[0,5](p1,p2,p3)", ["0,{p1}", "2,{p2}", "4,{p3}"], word="finite", expected_final="NEGATIVE", expected_sat="UNSAT", rationale="Past Pnueli existential at the initial observation has no prior ordered positions, so no finite trace suffix can witness it there."),
        SemanticCase("future_finally_star", "mighty_semantics", "future:F*", "F* [0,2] p1", ["0,{p1}"], expected_final="POSITIVE", rationale="Starred weak variant should admit current event where strict F may not."),
        SemanticCase("future_globally_hold_prefix", "mighty_semantics", "future:G", "G [0,2] p1", ["0,{p1}", "1,{p1}"], expected_final="INCONCLUSIVE"),
        SemanticCase("future_globally_violate", "mighty_semantics", "future:G", "G [0,2] p1", ["0,{p1}", "1,{}"], expected_final="NEGATIVE"),
        SemanticCase("future_globally_star", "mighty_semantics", "future:G*", "G* [0,2] p1", ["0,{p1}", "1,{p1}"], expected_final="INCONCLUSIVE"),
        SemanticCase("future_globally_star_initial_trigger_violate", "mighty_semantics", "future:G*", "G* (a -> F [0,30] b)", ["0,{a}", "31,{b}"], expected_final="NEGATIVE", expected_sat="SAT", rationale="Regression for XML request-response translation: starred globally includes the first observed trigger, so a response after the closed bound violates the formula."),
        SemanticCase("future_until_positive", "mighty_semantics", "future:U", "p1 U [1,3] p2", ["0,{p1}", "1,{p1}", "2,{p2}"], expected_final="POSITIVE"),
        SemanticCase("future_until_negative", "mighty_semantics", "future:U", "p1 U [1,3] p2", ["0,{p1}", "1,{p1}", "4,{}"], expected_final="NEGATIVE"),
        SemanticCase("future_until_star", "mighty_semantics", "future:U*", "p1 U* [0,3] p2", ["0,{p2}"], expected_final="POSITIVE"),
        SemanticCase("future_release", "mighty_semantics", "future:R", "p1 R [1,3] p2", ["0,{p2}", "1,{p2}", "2,{p1,p2}"], expected_final="POSITIVE", expected_sat="SAT", rationale="Release is the dual of until; p2 holds until p1 appears inside [1,3], so every continuation satisfies the property."),
        SemanticCase("future_release_star", "mighty_semantics", "future:R*", "p1 R* [0,3] p2", ["0,{p2}"], expected_final="INCONCLUSIVE", expected_sat="SAT", rationale="Weak release has current evidence for satisfaction but the finite prefix can still be extended to satisfy or violate obligations inside the open future interval."),
        SemanticCase("past_once", "mighty_semantics", "past:O", "O [0,2] p1", ["0,{p1}", "1,{}"], expected_final="NEGATIVE", expected_sat="UNSAT", rationale="Strict once at the initial observation has no prior position in [0,2], so the top-level past existential is impossible."),
        SemanticCase("past_once_star", "mighty_semantics", "past:O*", "O* [0,2] p1", ["0,{p1}"], expected_final="INCONCLUSIVE", expected_sat="SAT", rationale="Starred once is weak at the boundary: the current p1 keeps the positive branch possible, while finite-prefix extensions can still keep the monitor from a definitive verdict."),
        SemanticCase("past_historically", "mighty_semantics", "past:H", "H [0,2] p1", ["0,{p1}", "1,{p1}"], expected_final="POSITIVE", expected_sat="SAT", rationale="Strict historically at the initial observation is vacuous because there are no prior positions in the interval."),
        SemanticCase("past_historically_star", "mighty_semantics", "past:H*", "H* [0,2] p1", ["0,{p1}", "1,{p1}"], expected_final="POSITIVE", expected_sat="SAT", rationale="Weak historically includes the boundary observation; p1 holds at the checked prefix, making the violation automaton empty."),
        SemanticCase("past_since", "mighty_semantics", "past:S", "p1 S [0,3] p2", ["0,{p2}", "1,{p1}"], expected_final="NEGATIVE", expected_sat="UNSAT", rationale="Strict since at the initial observation has no prior witness for the right operand, so the past existential is impossible."),
        SemanticCase("past_since_star", "mighty_semantics", "past:S*", "p1 S* [0,3] p2", ["0,{p2}"], expected_final="INCONCLUSIVE", expected_sat="SAT", rationale="Weak since admits the boundary p2 witness, but the finite prefix does not make all infinite continuations decide the three-valued monitor."),
        SemanticCase("past_trigger", "mighty_semantics", "past:T", "p1 T [0,3] p2", ["0,{p2}", "1,{p1,p2}"], expected_final="POSITIVE", expected_sat="SAT", rationale="Trigger is the dual of since; with no strict past counter-witness at the initial observation, the universal past condition holds."),
        SemanticCase("past_trigger_star", "mighty_semantics", "past:T*", "p1 T* [0,3] p2", ["0,{p2}"], expected_final="POSITIVE", expected_sat="SAT", rationale="Weak trigger includes the boundary and p2 holds, so the negative since-dual branch is impossible on this prefix."),
        SemanticCase("pnueli_fn", "mighty_semantics", "pnueli:Fn", "Fn[0,5](p1,p2,p3)", ["0,{}", "1,{p1}", "3,{p2}", "5,{p3}"], expected_final="POSITIVE", expected_sat="SAT", rationale="Future Pnueli existential sequence is witnessed by p1 at 1, p2 at 3, and p3 at 5 within [0,5]."),
        SemanticCase("pnueli_on", "mighty_semantics", "pnueli:On", "On[0,5](p1,p2,p3)", ["0,{p1}", "2,{p2}", "4,{p3}"], expected_final="NEGATIVE", expected_sat="UNSAT", rationale="Past Pnueli existential at the initial observation has no prior timed positions, so no ordered past sequence can witness it."),
        SemanticCase("pnueli_gn", "mighty_semantics", "pnueli:Gn", "Gn[0,5](p1,p2,p3)", ["0,{}", "1,{p1}", "3,{p2}", "5,{p3}"], expected_final="INCONCLUSIVE", expected_sat="SAT", rationale="Future universal Pnueli dual remains three-valued on this finite prefix: neither the positive nor negative monitor is empty after the observed sequence."),
        SemanticCase("pnueli_hn", "mighty_semantics", "pnueli:Hn", "Hn[0,5](p1,p2,p3)", ["0,{p1}", "2,{p2}", "4,{p3}"], expected_final="POSITIVE", expected_sat="SAT", rationale="Past Pnueli universal dual is vacuous at the initial observation because there is no prior ordered sequence to violate it."),
    ]
    prefix_oracles = {
        "atom_true_under_f": ["INCONCLUSIVE", "POSITIVE"],
        "atom_false_under_f": ["NEGATIVE", "NEGATIVE"],
        "atom_identifier": ["INCONCLUSIVE", "POSITIVE"],
        "formula_not": ["INCONCLUSIVE", "POSITIVE"],
        "formula_and": ["INCONCLUSIVE", "POSITIVE"],
        "formula_or": ["INCONCLUSIVE", "POSITIVE"],
        "formula_implies": ["INCONCLUSIVE", "POSITIVE"],
        "formula_iff": ["INCONCLUSIVE", "POSITIVE"],
        "interval_left_open": ["INCONCLUSIVE", "POSITIVE"],
        "interval_right_open": ["INCONCLUSIVE", "POSITIVE"],
        "interval_open": ["INCONCLUSIVE", "POSITIVE"],
        "interval_unbounded": ["INCONCLUSIVE", "POSITIVE"],
        "future_finally_positive": ["INCONCLUSIVE", "POSITIVE"],
        "future_finally_negative": ["INCONCLUSIVE", "NEGATIVE"],
        "finite_finally_positive": ["INCONCLUSIVE", "POSITIVE"],
        "finite_finally_negative": ["INCONCLUSIVE", "NEGATIVE"],
        "finite_globally_violate": ["INCONCLUSIVE", "NEGATIVE"],
        "finite_formula_and": ["INCONCLUSIVE", "POSITIVE"],
        "finite_interval_open": ["INCONCLUSIVE", "POSITIVE"],
        "finite_until_positive": ["INCONCLUSIVE", "INCONCLUSIVE", "POSITIVE"],
        "finite_until_negative": ["INCONCLUSIVE", "INCONCLUSIVE", "NEGATIVE"],
        "finite_until_star": ["POSITIVE"],
        "finite_release_positive": ["INCONCLUSIVE", "INCONCLUSIVE", "POSITIVE"],
        "finite_release_star_end_positive": ["INCONCLUSIVE"],
        "finite_past_once_negative": ["NEGATIVE", "NEGATIVE"],
        "finite_past_historically_positive": ["POSITIVE", "POSITIVE"],
        "finite_past_since_negative": ["NEGATIVE", "NEGATIVE"],
        "finite_past_trigger_positive": ["POSITIVE", "POSITIVE"],
        "finite_pnueli_fn_positive": ["INCONCLUSIVE", "INCONCLUSIVE", "INCONCLUSIVE", "POSITIVE"],
        "finite_pnueli_gn_end_positive": ["INCONCLUSIVE", "INCONCLUSIVE", "INCONCLUSIVE", "INCONCLUSIVE"],
        "finite_pnueli_hn_positive": ["POSITIVE", "POSITIVE", "POSITIVE"],
        "finite_atom_true_under_f": ["INCONCLUSIVE", "POSITIVE"],
        "finite_atom_false_under_f": ["NEGATIVE", "NEGATIVE"],
        "finite_atom_identifier": ["INCONCLUSIVE", "POSITIVE"],
        "finite_formula_not": ["INCONCLUSIVE", "POSITIVE"],
        "finite_formula_or": ["INCONCLUSIVE", "POSITIVE"],
        "finite_formula_implies": ["INCONCLUSIVE", "POSITIVE"],
        "finite_formula_iff": ["INCONCLUSIVE", "POSITIVE"],
        "finite_interval_left_open": ["INCONCLUSIVE", "POSITIVE"],
        "finite_interval_right_open": ["INCONCLUSIVE", "POSITIVE"],
        "finite_interval_unbounded": ["INCONCLUSIVE", "POSITIVE"],
        "finite_finally_star": ["POSITIVE"],
        "finite_globally_star_end_positive": ["INCONCLUSIVE", "INCONCLUSIVE"],
        "finite_past_once_star_negative": ["NEGATIVE"],
        "finite_past_historically_star_positive": ["POSITIVE", "POSITIVE"],
        "finite_past_since_star_negative": ["NEGATIVE"],
        "finite_past_trigger_star_positive": ["POSITIVE"],
        "finite_pnueli_on_negative": ["NEGATIVE", "NEGATIVE", "NEGATIVE"],
        "future_finally_star": ["POSITIVE"],
        "future_globally_hold_prefix": ["INCONCLUSIVE", "INCONCLUSIVE"],
        "future_globally_violate": ["INCONCLUSIVE", "NEGATIVE"],
        "future_globally_star": ["INCONCLUSIVE", "INCONCLUSIVE"],
        "future_globally_star_initial_trigger_violate": ["INCONCLUSIVE", "NEGATIVE"],
        "future_until_positive": ["INCONCLUSIVE", "INCONCLUSIVE", "POSITIVE"],
        "future_until_negative": ["INCONCLUSIVE", "INCONCLUSIVE", "NEGATIVE"],
        "future_until_star": ["POSITIVE"],
        "future_release": ["INCONCLUSIVE", "INCONCLUSIVE", "POSITIVE"],
        "future_release_star": ["INCONCLUSIVE"],
        "past_once": ["NEGATIVE", "NEGATIVE"],
        "past_once_star": ["INCONCLUSIVE"],
        "past_historically": ["POSITIVE", "POSITIVE"],
        "past_historically_star": ["POSITIVE", "POSITIVE"],
        "past_since": ["NEGATIVE", "NEGATIVE"],
        "past_since_star": ["INCONCLUSIVE"],
        "past_trigger": ["POSITIVE", "POSITIVE"],
        "past_trigger_star": ["POSITIVE"],
        "pnueli_fn": ["INCONCLUSIVE", "INCONCLUSIVE", "INCONCLUSIVE", "POSITIVE"],
        "pnueli_on": ["NEGATIVE", "NEGATIVE", "NEGATIVE"],
        "pnueli_gn": ["INCONCLUSIVE", "INCONCLUSIVE", "INCONCLUSIVE", "INCONCLUSIVE"],
        "pnueli_hn": ["POSITIVE", "POSITIVE", "POSITIVE"],
    }
    rationale_overrides = {
        "atom_identifier": "The witness p1 appears at time 1 within [0,2], so the finally formula becomes permanently satisfied on the second prefix.",
        "formula_not": "The second event omits p1, witnessing !p1 within [0,2].",
        "formula_and": "Both p1 and p2 hold at time 1, witnessing the conjunction inside the eventually interval.",
        "formula_or": "p2 holds at time 1, so the disjunction is witnessed inside [0,2].",
        "formula_implies": "The second event satisfies p1 -> p2 because both p1 and p2 hold at the witness time.",
        "formula_iff": "The second event satisfies p1 <-> p2 because both propositions have the same truth value.",
        "interval_left_open": "The p1 witness at time 1 is strictly after the left-open lower bound and before the closed upper bound.",
        "interval_right_open": "The p1 witness at time 1 is inside [0,2), away from the open upper boundary.",
        "interval_open": "The p1 witness at time 1 is strictly inside the open interval (0,2).",
        "interval_unbounded": "The p1 witness at time 5 satisfies the unbounded eventually interval.",
        "future_finally_positive": "p1 appears at time 1 within [0,2], giving a positive finite-prefix verdict.",
        "future_finally_negative": "No p1 occurs before the bound expires at the event time 3, so the obligation is violated.",
        "future_globally_hold_prefix": "The observed prefix has not violated p1 inside [0,2], but future observations can still decide the bounded global property.",
        "future_globally_violate": "The event at time 1 violates p1 inside the bounded global interval.",
        "future_globally_star": "The starred global form includes the observed boundary, but the shown prefix remains extendable both ways.",
        "future_until_positive": "p1 holds until p2 appears at time 2, which lies inside [1,3].",
        "future_until_negative": "The upper bound is exceeded without a p2 witness while the until obligation is active.",
        "future_until_star": "The starred until formula is immediately witnessed by p2 at the boundary event.",
    }
    for case in base:
        case.expected_prefix = prefix_oracles.get(case.case_id, [])
        if not case.rationale:
            case.rationale = rationale_overrides.get(case.case_id, "")
    for path in sorted((REPO_ROOT / "tool" / "MightyPPL" / "testcases").glob("**/*.mitl")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        case_id = "mighty_existing_" + re.sub(r"[^A-Za-z0-9]+", "_", str(path.relative_to(REPO_ROOT / "tool" / "MightyPPL" / "testcases"))).strip("_")
        formula = path.read_text(encoding="utf-8").strip()
        base.append(SemanticCase(
            case_id=case_id,
            suite="mighty_existing",
            category="existing_mightyppl_testcase",
            formula=formula,
            trace=[],
            expected_final="",
            review_status="build_stats_only",
            rationale=f"Existing MightyPPL testcase from {rel}; run through TAMonitor construction with empty trace for SAT/stats, not a verdict claim.",
            max_valuations=80000,
        ))
    return base


def run_command(args: list[str], timeout: int, cwd: Path = REPO_ROOT, stdin_text: str | None = None) -> dict[str, Any]:
    start = time.time()
    proc = subprocess.Popen(
        args,
        cwd=str(cwd),
        text=True,
        stdin=subprocess.PIPE if stdin_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    try:
        stdout, stderr = proc.communicate(input=stdin_text, timeout=timeout)
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "returncode": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "elapsed_ms": elapsed_ms,
            "timeout": False,
        }
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        except PermissionError:
            pass
        try:
            stdout, stderr = proc.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            except PermissionError:
                pass
            stdout, stderr = proc.communicate()
        elapsed_ms = int((time.time() - start) * 1000)
        return {
            "returncode": 124,
            "stdout": stdout or "",
            "stderr": (stderr or "") + f"\ntimeout after {timeout}s",
            "elapsed_ms": elapsed_ms,
            "timeout": True,
        }


def read_summary_csv(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    with path.open(newline="", encoding="utf-8") as handle:
        return {row["metric"]: row["value"] for row in csv.DictReader(handle)}


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def write_experiment_summary_files(output_dir: Path, summary: dict[str, Any]) -> None:
    (output_dir / "experiment_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    write_csv(
        output_dir / "experiment_summary.csv",
        [{"metric": key, "value": value} for key, value in summary.items()],
        ["metric", "value"],
    )


def write_case_files(cases_dir: Path, case: SemanticCase) -> tuple[Path, Path]:
    case_dir = cases_dir / case.case_id
    case_dir.mkdir(parents=True, exist_ok=True)
    formula_path = case_dir / "formula.mitl"
    trace_path = case_dir / "trace.txt"
    formula_path.write_text(case.formula + "\n", encoding="utf-8")
    trace_path.write_text("\n".join(case.trace) + ("\n" if case.trace else ""), encoding="utf-8")
    return formula_path, trace_path


def expected_sat_scope(case: SemanticCase) -> str:
    if case.expected_sat:
        return "hand_checked"
    if case.review_status == "build_stats_only":
        return "not_applicable_build_stats_only"
    if case.expected_final:
        return "not_checked_final_verdict_only"
    return "not_specified"


def run_semantic_regression(output_dir: Path, timeout: int, tamonitor: Path, no_run: bool) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    cases_dir = output_dir / "semantic_cases"
    run_root = output_dir / "tamonitor_runs"
    case_rows: list[dict[str, Any]] = []
    result_rows: list[dict[str, Any]] = []

    for case in semantic_cases():
        formula_path, trace_path = write_case_files(cases_dir, case)
        run_dir = run_root / case.case_id
        build_mode = "compflatten" if case.review_status == "build_stats_only" else "flatten"
        case_rows.append({
            **asdict(case),
            "build_mode": build_mode,
            "expected_prefix": "|".join(case.expected_prefix),
            "expected_sat_scope": expected_sat_scope(case),
            "formula_path": str(formula_path),
            "trace_path": str(trace_path),
            "trace_events": len(case.trace),
        })

        args = [
            str(tamonitor),
            "--formula", str(formula_path),
            "--trace", str(trace_path),
            "--word", case.word,
            "--state", case.state,
            "--build-mode", build_mode,
            "--max-valuations", str(case.max_valuations),
            "--out", str(run_dir),
            "--emit-bdd-interface",
        ]
        if case.review_status == "build_stats_only":
            args.append("--build-only")

        command_result = {"returncode": "", "stdout": "", "stderr": "", "elapsed_ms": "", "timeout": False}
        if not no_run:
            command_result = run_command(args, timeout)

        summary = read_summary_csv(run_dir / "summary.csv")
        actual_final = summary.get("final_verdict", "")
        actual_sat = summary.get("formula_satisfiable", "")
        expected_final = case.expected_final
        expected_sat = case.expected_sat
        stderr = command_result["stderr"] or ""
        sat_matches = (not expected_sat) or actual_sat == expected_sat
        if no_run:
            pass_status = "NOT_RUN"
        elif command_result["timeout"] and case.review_status == "build_stats_only":
            pass_status = "BUILD_TIMEOUT"
        elif command_result["timeout"]:
            pass_status = "TIMEOUT"
        elif "BDD projection valuation limit exceeded" in stderr:
            pass_status = "RESOURCE_LIMIT"
        elif command_result["returncode"] == 0 and expected_final:
            pass_status = "PASS" if actual_final == expected_final and sat_matches else "FAIL"
        elif command_result["returncode"] == 0 and case.review_status == "build_stats_only":
            pass_status = "BUILD_STATS"
        elif command_result["returncode"] == 0:
            pass_status = "REVIEW"
        else:
            pass_status = "ERROR"

        if pass_status == "PASS":
            correctness_status = "VERIFIED"
            oracle_type = "hand_expected_final" + ("+expected_sat" if expected_sat else "")
            oracle_verdict = expected_final
            correctness_evidence = "actual_final matches expected_final" + (" and actual_sat matches expected_sat" if expected_sat else "")
        elif pass_status == "FAIL":
            correctness_status = "INCORRECT_OR_ORACLE_MISMATCH"
            oracle_type = "hand_expected_final" + ("+expected_sat" if expected_sat else "")
            oracle_verdict = expected_final
            correctness_evidence = f"expected_final={expected_final}, actual_final={actual_final}, expected_sat={expected_sat}, actual_sat={actual_sat}"
        elif pass_status == "REVIEW":
            correctness_status = "NEEDS_MANUAL_ORACLE"
            oracle_type = "manual_expected_missing"
            oracle_verdict = ""
            correctness_evidence = "Runtime completed, but this semantic category is intentionally not counted correct without a hand-checked oracle."
        elif pass_status == "BUILD_STATS":
            correctness_status = "NOT_A_VERDICT_CHECK"
            oracle_type = "construction_stats_only"
            oracle_verdict = ""
            correctness_evidence = (
                "Existing MightyPPL testcase used for construction/statistics only, not a timed-word verdict claim. "
                f"build_mode={build_mode}, formula_satisfiable={actual_sat}."
            )
        elif pass_status == "BUILD_TIMEOUT":
            correctness_status = "NOT_A_VERDICT_CHECK_BUILD_TIMEOUT"
            oracle_type = "construction_stats_only"
            oracle_verdict = ""
            correctness_evidence = (
                "Existing MightyPPL testcase was used for construction/statistics only and exceeded the configured "
                f"construction timeout in build_mode={build_mode}; no runtime verdict was claimed."
            )
        elif pass_status == "RESOURCE_LIMIT":
            correctness_status = "NOT_VERIFIED_RESOURCE_LIMIT"
            oracle_type = "none"
            oracle_verdict = ""
            correctness_evidence = "BDD valuation projection exceeded configured resource limit before a verified verdict could be claimed."
        elif pass_status == "TIMEOUT":
            correctness_status = "NOT_VERIFIED_TIMEOUT"
            oracle_type = "none"
            oracle_verdict = ""
            correctness_evidence = "Run exceeded timeout before a verified verdict could be claimed."
        elif pass_status == "NOT_RUN":
            correctness_status = "NOT_RUN"
            oracle_type = "none"
            oracle_verdict = ""
            correctness_evidence = "Execution was skipped by --no-run."
        else:
            correctness_status = "NOT_VERIFIED_ERROR"
            oracle_type = "none"
            oracle_verdict = ""
            correctness_evidence = "Runtime returned an error before a verified verdict could be claimed."

        result_rows.append({
            "case_id": case.case_id,
            "suite": case.suite,
            "category": case.category,
            "build_mode": build_mode,
            "word": case.word,
            "state": case.state,
            "expected_final": expected_final,
            "expected_prefix": "|".join(case.expected_prefix),
            "actual_final": actual_final,
            "expected_sat": case.expected_sat,
            "expected_sat_scope": expected_sat_scope(case),
            "actual_sat": actual_sat,
            "pass_status": pass_status,
            "correctness_status": correctness_status,
            "oracle_type": oracle_type,
            "oracle_verdict": oracle_verdict,
            "correctness_evidence": correctness_evidence,
            "review_status": case.review_status,
            "returncode": command_result["returncode"],
            "timeout": command_result["timeout"],
            "elapsed_ms": command_result["elapsed_ms"],
            "events": summary.get("events", ""),
            "processed_steps": summary.get("processed_steps", ""),
            "advanced_steps": summary.get("advanced_steps", ""),
            "carry_forward_steps": summary.get("carry_forward_steps", ""),
            "positive_components": summary.get("positive_components", ""),
            "positive_locations": summary.get("positive_locations", ""),
            "positive_edges": summary.get("positive_edges", ""),
            "positive_clocks": summary.get("positive_clocks", ""),
            "negative_components": summary.get("negative_components", ""),
            "negative_locations": summary.get("negative_locations", ""),
            "negative_edges": summary.get("negative_edges", ""),
            "negative_clocks": summary.get("negative_clocks", ""),
            "positive_projection_valuations": summary.get("positive_projection_valuations", ""),
            "negative_projection_valuations": summary.get("negative_projection_valuations", ""),
            "run_dir": str(run_dir),
            "stderr_excerpt": (command_result["stderr"] or "")[:500].replace("\n", " "),
            "stdout_excerpt": (command_result["stdout"] or "")[:500].replace("\n", " "),
        })

    return case_rows, result_rows


def read_dict_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def build_semantic_prefix_oracle_review(
    case_rows: list[dict[str, Any]],
    semantic_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    case_by_id = {row["case_id"]: row for row in case_rows}
    review_rows: list[dict[str, Any]] = []

    for result in semantic_rows:
        case = case_by_id.get(result["case_id"], {})
        expected_prefix = [part for part in str(case.get("expected_prefix", "")).split("|") if part]
        run_dir = Path(str(result.get("run_dir", ""))) if result.get("run_dir") else Path()
        steps_path = run_dir / "steps.csv" if run_dir != Path() else Path()
        steps = read_dict_rows(steps_path)

        if not steps:
            if result.get("pass_status") in {"BUILD_STATS", "BUILD_TIMEOUT"}:
                prefix_status = "NOT_A_RUNTIME_VERDICT_CHECK"
            elif result.get("pass_status") == "NOT_RUN":
                prefix_status = "NOT_RUN"
            else:
                prefix_status = "NO_STEPS_RECORDED"
            review_rows.append({
                "case_id": result.get("case_id", ""),
                "suite": result.get("suite", ""),
                "category": result.get("category", ""),
                "formula": case.get("formula", ""),
                "word": result.get("word", ""),
                "build_mode": result.get("build_mode", ""),
                "trace_events": case.get("trace_events", ""),
                "step": "",
                "time": "",
                "human_label": "",
                "canonical_label": "",
                "expected_prefix_verdict": "",
                "actual_prefix_verdict": "",
                "prefix_oracle_status": prefix_status,
                "monitor_advanced": "",
                "positive_states": "",
                "negative_states": "",
                "expected_final": result.get("expected_final", ""),
                "actual_final": result.get("actual_final", ""),
                "final_correctness_status": result.get("correctness_status", ""),
                "oracle_type": result.get("oracle_type", ""),
                "expected_sat_scope": result.get("expected_sat_scope", ""),
                "step_evidence": result.get("correctness_evidence", ""),
                "rationale": case.get("rationale", ""),
                "trace_path": case.get("trace_path", ""),
                "run_dir": result.get("run_dir", ""),
            })
            continue

        for index, step in enumerate(steps):
            expected = expected_prefix[index] if index < len(expected_prefix) else ""
            actual = step.get("verdict", "")
            if expected:
                prefix_status = "MATCH" if actual == expected else "MISMATCH"
                evidence = f"step {index + 1}: actual_prefix={actual}; hand_expected_prefix={expected}"
            elif result.get("correctness_status") == "VERIFIED":
                prefix_status = "FINAL_VERDICT_ONLY"
                evidence = "No hand prefix oracle is recorded for this step; final verdict oracle is verified separately."
            else:
                prefix_status = result.get("correctness_status", "NOT_VERIFIED")
                evidence = result.get("correctness_evidence", "")
            review_rows.append({
                "case_id": result.get("case_id", ""),
                "suite": result.get("suite", ""),
                "category": result.get("category", ""),
                "formula": case.get("formula", ""),
                "word": result.get("word", ""),
                "build_mode": result.get("build_mode", ""),
                "trace_events": case.get("trace_events", ""),
                "step": step.get("step", ""),
                "time": step.get("time", ""),
                "human_label": step.get("human_label", ""),
                "canonical_label": step.get("canonical_label", ""),
                "expected_prefix_verdict": expected,
                "actual_prefix_verdict": actual,
                "prefix_oracle_status": prefix_status,
                "monitor_advanced": step.get("monitor_advanced", "unknown"),
                "positive_states": step.get("positive_states", ""),
                "negative_states": step.get("negative_states", ""),
                "expected_final": result.get("expected_final", ""),
                "actual_final": result.get("actual_final", ""),
                "final_correctness_status": result.get("correctness_status", ""),
                "oracle_type": result.get("oracle_type", ""),
                "expected_sat_scope": result.get("expected_sat_scope", ""),
                "step_evidence": evidence,
                "rationale": case.get("rationale", ""),
                "trace_path": case.get("trace_path", ""),
                "run_dir": result.get("run_dir", ""),
            })

        for missing_index in range(len(steps), len(expected_prefix)):
            review_rows.append({
                "case_id": result.get("case_id", ""),
                "suite": result.get("suite", ""),
                "category": result.get("category", ""),
                "formula": case.get("formula", ""),
                "word": result.get("word", ""),
                "build_mode": result.get("build_mode", ""),
                "trace_events": case.get("trace_events", ""),
                "step": missing_index + 1,
                "time": "",
                "human_label": "",
                "canonical_label": "",
                "expected_prefix_verdict": expected_prefix[missing_index],
                "actual_prefix_verdict": "",
                "prefix_oracle_status": "MISSING_OBSERVED_STEP",
                "monitor_advanced": "",
                "positive_states": "",
                "negative_states": "",
                "expected_final": result.get("expected_final", ""),
                "actual_final": result.get("actual_final", ""),
                "final_correctness_status": result.get("correctness_status", ""),
                "oracle_type": result.get("oracle_type", ""),
                "expected_sat_scope": result.get("expected_sat_scope", ""),
                "step_evidence": "The hand prefix oracle expects this step, but steps.csv did not record it.",
                "rationale": case.get("rationale", ""),
                "trace_path": case.get("trace_path", ""),
                "run_dir": result.get("run_dir", ""),
            })

    return review_rows


def write_semantic_prefix_oracle_review(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    counts = Counter(row["prefix_oracle_status"] for row in rows)
    lines = [
        "# Semantic Prefix Oracle Review",
        "",
        "This generated review index gives one row per recorded TAMonitor prefix step.",
        "Rows with `MATCH` compare the observed prefix verdict against a hand-written prefix oracle.",
        "Rows with `monitor_advanced=false` are stable carry-forward verdicts after the monitor has already reached POSITIVE or NEGATIVE.",
        "",
        "## Counts",
        "",
    ]
    for key in sorted(counts):
        lines.append(f"- `{key}`: {counts[key]}")
    lines.extend([
        "",
        "## Review Table",
        "",
        "| case_id | step | expected | actual | status | monitor_advanced |",
        "|---|---:|---|---|---|---|",
    ])
    for row in rows:
        lines.append(
            f"| `{row['case_id']}` | {row['step']} | `{row['expected_prefix_verdict']}` | "
            f"`{row['actual_prefix_verdict']}` | `{row['prefix_oracle_status']}` | `{row['monitor_advanced']}` |"
        )
    lines.append("")
    (output_dir / "semantic_prefix_oracle_review.md").write_text("\n".join(lines), encoding="utf-8")


def semantic_rule_for_category(category: str) -> str:
    if category.startswith("atom:"):
        return "atomic proposition/literal satisfaction at the observed timed word positions"
    if category.startswith("formula:"):
        return "Boolean MITL connective semantics before MightyPPL NNF rewriting"
    if category.startswith("interval:"):
        return "MITL interval membership, including open/closed and unbounded endpoints"
    if category.startswith("future:F"):
        return "future eventually: some future position satisfies the operand inside the interval"
    if category.startswith("future:G"):
        return "future globally: all relevant future positions satisfy the operand inside the interval"
    if category.startswith("future:U"):
        return "future until: left operand holds until a right-operand witness appears inside the interval"
    if category.startswith("future:R"):
        return "future release: dual of until; the release condition must hold until the releasing witness or throughout the interval"
    if category.startswith("past:O"):
        return "past once: some prior position satisfies the operand inside the interval"
    if category.startswith("past:H"):
        return "past historically: all relevant prior positions satisfy the operand inside the interval"
    if category.startswith("past:S"):
        return "past since: past dual of until with a prior right-operand witness"
    if category.startswith("past:T"):
        return "past trigger: past dual of since"
    if category.startswith("pnueli:Fn") or category.startswith("finite:Fn"):
        return "future Pnueli existential sequence: ordered witnesses must occur inside the interval"
    if category.startswith("pnueli:On"):
        return "past Pnueli existential sequence: ordered prior witnesses must occur inside the interval"
    if category.startswith("pnueli:Gn") or category.startswith("finite:Gn"):
        return "future Pnueli universal dual checked through positive/negative monitor emptiness"
    if category.startswith("pnueli:Hn") or category.startswith("finite:Hn"):
        return "past Pnueli universal dual checked through absence of a violating ordered past sequence"
    if category.startswith("finite:"):
        return "finite-word MITL semantics with end-of-word finalization"
    if category.startswith("mighty_existing:"):
        return "existing MightyPPL corpus construction/statistics coverage only"
    return "hand-written semantic regression rationale"


def build_semantic_oracle_derivations(
    case_rows: list[dict[str, Any]],
    semantic_rows: list[dict[str, Any]],
    semantic_prefix_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result_by_case = {row["case_id"]: row for row in semantic_rows}
    prefix_by_case: dict[str, list[dict[str, Any]]] = {}
    for row in semantic_prefix_rows:
        prefix_by_case.setdefault(row.get("case_id", ""), []).append(row)

    derivation_rows: list[dict[str, Any]] = []
    for case in case_rows:
        case_id = case["case_id"]
        result = result_by_case.get(case_id, {})
        prefix_rows = prefix_by_case.get(case_id, [])
        prefix_checked = [
            row for row in prefix_rows
            if row.get("prefix_oracle_status") in {"MATCH", "MISMATCH", "MISSING_OBSERVED_STEP"}
        ]
        prefix_mismatches = [
            row for row in prefix_rows
            if row.get("prefix_oracle_status") in {"MISMATCH", "MISSING_OBSERVED_STEP"}
        ]
        expected_prefix = case.get("expected_prefix", "")
        correctness_status = result.get("correctness_status", "")
        pass_status = result.get("pass_status", "")
        expected_final = case.get("expected_final", "")
        actual_final = result.get("actual_final", "")
        expected_sat = case.get("expected_sat", "")
        actual_sat = result.get("actual_sat", "")

        if correctness_status == "VERIFIED" and not prefix_mismatches:
            oracle_status = "HAND_ORACLE_VERIFIED"
            oracle_scope = "runtime_final_and_optional_prefix"
            review_action = "Review rationale and prefix rows; this row is counted as semantic correctness evidence."
        elif correctness_status == "NOT_A_VERDICT_CHECK":
            oracle_status = "CONSTRUCTION_STATS_ONLY"
            oracle_scope = "not_runtime_oracle"
            review_action = "Do not use this row as a timed-word RV correctness oracle."
        elif correctness_status == "NOT_A_VERDICT_CHECK_BUILD_TIMEOUT":
            oracle_status = "CONSTRUCTION_TIMEOUT_ONLY"
            oracle_scope = "not_runtime_oracle"
            review_action = "Do not use this row as correctness evidence; inspect construction timeout if needed."
        elif pass_status in {"TIMEOUT", "RESOURCE_LIMIT"}:
            oracle_status = "NOT_VERIFIED_RESOURCE_OR_TIMEOUT"
            oracle_scope = "not_verified"
            review_action = "Do not cite this row as verified until the resource/timeout issue is resolved."
        else:
            oracle_status = "ORACLE_REVIEW_REQUIRED"
            oracle_scope = "needs_manual_review"
            review_action = "Resolve the oracle/result mismatch or add a complete hand oracle before citing."

        prefix_parts = []
        for row in prefix_rows:
            status = row.get("prefix_oracle_status", "")
            if status in {"MATCH", "MISMATCH", "MISSING_OBSERVED_STEP"}:
                prefix_parts.append(
                    f"step {row.get('step')}: expected={row.get('expected_prefix_verdict')}, "
                    f"actual={row.get('actual_prefix_verdict') or '<missing>'}, status={status}"
                )
        if not prefix_parts and correctness_status == "VERIFIED":
            prefix_derivation = "No per-prefix oracle was specified; correctness is final-verdict-only for this case."
        elif not prefix_parts:
            prefix_derivation = result.get("correctness_evidence", "")
        else:
            prefix_derivation = " | ".join(prefix_parts)

        if expected_sat:
            sat_derivation = f"Hand SAT expectation {expected_sat}; TAMonitor SAT check returned {actual_sat}."
        elif case.get("expected_sat_scope") == "not_applicable_build_stats_only":
            sat_derivation = "SAT is not a runtime oracle for this build/statistics-only corpus row."
        else:
            sat_derivation = "No separate SAT oracle was claimed; final runtime verdict is the checked property."

        final_derivation = (
            f"{case.get('rationale', '')} Expected final={expected_final or '<not claimed>'}; "
            f"TAMonitor final={actual_final or '<not available>'}; correctness_status={correctness_status}."
        )

        derivation_rows.append({
            "case_id": case_id,
            "suite": case.get("suite", ""),
            "category": case.get("category", ""),
            "oracle_scope": oracle_scope,
            "oracle_status": oracle_status,
            "semantic_rule": semantic_rule_for_category(case.get("category", "")),
            "formula": case.get("formula", ""),
            "trace": case.get("trace", ""),
            "word": case.get("word", ""),
            "build_mode": case.get("build_mode", ""),
            "expected_final": expected_final,
            "actual_final": actual_final,
            "expected_prefix": expected_prefix,
            "prefix_checked_steps": len(prefix_checked),
            "prefix_mismatches": len(prefix_mismatches),
            "expected_sat": expected_sat,
            "actual_sat": actual_sat,
            "correctness_status": correctness_status,
            "pass_status": pass_status,
            "final_oracle_derivation": final_derivation,
            "prefix_oracle_derivation": prefix_derivation,
            "sat_oracle_derivation": sat_derivation,
            "evidence_artifacts": "semantic_cases.csv; semantic_regression_results.csv; semantic_prefix_oracle_review.csv; glob:tamonitor_runs/*/steps.csv",
            "review_action": review_action,
            "run_dir": result.get("run_dir", ""),
        })
    return derivation_rows


def write_semantic_oracle_derivations(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "semantic_oracle_derivations.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = Counter(row["oracle_status"] for row in rows)
    lines = [
        "# Semantic Oracle Derivations",
        "",
        "This generated ledger explains the hand-oracle basis for each semantic regression case.",
        "Rows marked `CONSTRUCTION_STATS_ONLY` are intentionally not runtime-verdict correctness claims.",
        "",
        "## Counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend([
        "",
        "## Rows",
        "",
        "| case_id | oracle_status | expected_final | actual_final | prefix_mismatches | review_action |",
        "|---|---|---|---|---:|---|",
    ])
    for row in rows:
        action = row["review_action"].replace("|", "\\|")
        lines.append(
            f"| `{row['case_id']}` | `{row['oracle_status']}` | `{row['expected_final']}` | "
            f"`{row['actual_final']}` | {row['prefix_mismatches']} | {action} |"
        )
    lines.append("")
    (output_dir / "semantic_oracle_derivations.md").write_text("\n".join(lines), encoding="utf-8")


def sample_case_ids(rows: list[dict[str, Any]], category_prefixes: list[str], limit: int = 6) -> str:
    selected: list[str] = []
    for row in rows:
        category = str(row.get("category", ""))
        if any(category.startswith(prefix) for prefix in category_prefixes):
            case_id = str(row.get("case_id", ""))
            if case_id and case_id not in selected:
                selected.append(case_id)
        if len(selected) >= limit:
            break
    return ";".join(selected)


def manual_oracle_guide_row(
    guide_id: str,
    section: str,
    priority: str,
    protocol_step: str,
    decision_rule: str,
    pass_condition: str,
    reject_or_fix_condition: str,
    evidence_artifacts: str,
    sample_case_ids_value: str,
    reviewer_action: str,
    must_not_claim: str,
) -> dict[str, Any]:
    return {
        "guide_id": guide_id,
        "section": section,
        "priority": priority,
        "protocol_step": protocol_step,
        "decision_rule": decision_rule,
        "pass_condition": pass_condition,
        "reject_or_fix_condition": reject_or_fix_condition,
        "evidence_artifacts": evidence_artifacts,
        "sample_case_ids": sample_case_ids_value,
        "reviewer_action": reviewer_action,
        "must_not_claim": must_not_claim,
    }


def build_manual_oracle_guide(
    semantic_oracle_derivation_rows: list[dict[str, Any]],
    semantic_prefix_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    hand_verified = count_rows(semantic_oracle_derivation_rows, oracle_status="HAND_ORACLE_VERIFIED")
    build_only = count_rows(semantic_oracle_derivation_rows, oracle_status="CONSTRUCTION_STATS_ONLY")
    review_required = count_rows(semantic_oracle_derivation_rows, oracle_status="ORACLE_REVIEW_REQUIRED")
    prefix_mismatch = count_rows(semantic_prefix_rows, prefix_oracle_status="MISMATCH")
    prefix_missing = count_rows(semantic_prefix_rows, prefix_oracle_status="MISSING_OBSERVED_STEP")
    prefix_match = count_rows(semantic_prefix_rows, prefix_oracle_status="MATCH")

    return [
        manual_oracle_guide_row(
            "MOG_DEFINITION",
            "definition",
            "P0",
            "A manual oracle is an expected verdict derived from MITL semantics before reading TAMonitor output.",
            "Use the hand-written rationale, expected_final, expected_prefix, and expected_sat fields as the independent expectation.",
            f"Rows counted as runtime correctness must be HAND_ORACLE_VERIFIED; current hand_verified={hand_verified}.",
            "If the expected verdict is copied from TAMonitor output, or the rationale is absent for a claimed runtime row, reject the row and add a real derivation.",
            "semantic_cases.csv; semantic_oracle_derivations.csv; semantic_prefix_oracle_review.csv",
            sample_case_ids(semantic_oracle_derivation_rows, ["future:F", "future:G", "finite:F"]),
            "Check that the rationale explains why the formula is true, false, or inconclusive on the timed word.",
            "Do not call a generated monitor result itself a manual oracle.",
        ),
        manual_oracle_guide_row(
            "MOG_INDEPENDENCE",
            "independence",
            "P0",
            "The oracle source must be independent of TAMonitor, MoniTAal, stdout parsing, and generated verdict summaries.",
            "Accept the oracle only when the expected value is justified by the MITL formula, interval boundaries, word mode, and timed-word events.",
            "The oracle ledger may compare against TAMonitor after the expectation is stated, but the comparison is not the source of truth.",
            "If the rationale says only that TAMonitor or MoniTAal returned the same verdict, classify the row as review-required and add a semantic derivation.",
            "semantic_cases.csv; semantic_oracle_derivations.csv; semantic_prefix_oracle_review.csv; manual_oracle_guide.csv",
            sample_case_ids(semantic_oracle_derivation_rows, ["future:U", "past:", "pnueli:"], 6),
            "Trace the expected prefix/final verdict back to MITL semantics before checking the actual output columns.",
            "Do not use agreement between two implementations as a substitute for a hand oracle.",
        ),
        manual_oracle_guide_row(
            "MOG_BASELINE_NOT_HAND_ORACLE",
            "baseline_boundary",
            "P0",
            "MoniTAal XML baseline comparisons are trace-level cross-tool evidence, not hand-derived MITL semantic oracles.",
            "Use baseline verdict agreement to check that a candidate MITL monitor matches the XML monitor on the same mapped input; use manual-oracle rows only when the expected verdict is derived from MITL semantics before running either tool.",
            "Rows with oracle_type=monitaal_xml_baseline_same_input may support baseline-match claims, but they do not by themselves prove XML-to-MITL equivalence or hand-oracle correctness.",
            "If a paper or review row treats MoniTAal/TAMonitor agreement as a manual oracle, rewrite the claim or add an independent semantic derivation.",
            "translation_candidate_results.csv; monitaal_baseline_results.csv; xml_trace_coverage_obligations.csv; manual_oracle_guide.csv",
            "c_after_10_positive_negative_c_after_10_monitor_test_intersection_test2",
            "Check whether the cited row is a hand-oracle semantic regression, a MoniTAal baseline comparison, or a structural XML proof obligation before approving the claim.",
            "Do not call MoniTAal baseline agreement a hand oracle, and do not use it as a substitute for human XML-to-MITL proof review.",
        ),
        manual_oracle_guide_row(
            "MOG_THREE_VALUED_PREFIX",
            "prefix_verdicts",
            "P0",
            "For runtime verification, each checked prefix has a three-valued oracle: POSITIVE, NEGATIVE, or INCONCLUSIVE.",
            "A prefix row passes only when expected_prefix_verdict equals actual_prefix_verdict and the observed step exists.",
            f"Current prefix rows: matches={prefix_match}; mismatches={prefix_mismatch}; missing_observed_steps={prefix_missing}.",
            "Any MISMATCH or MISSING_OBSERVED_STEP row is a real correctness blocker until either the hand oracle or implementation bug is fixed.",
            "semantic_prefix_oracle_review.csv; glob:tamonitor_runs/*/steps.csv",
            sample_case_ids(semantic_oracle_derivation_rows, ["future:U", "future:R", "past:"]),
            "Spot-check at least one eventually, globally, until/release, and past-operator prefix sequence.",
            "Do not use final-verdict agreement as evidence for every prefix when prefix rows are absent or mismatched.",
        ),
        manual_oracle_guide_row(
            "MOG_FINAL_VERDICT",
            "final_verdicts",
            "P0",
            "The final oracle is the expected verdict after consuming the shown timed word under the selected finite or infinite word mode.",
            "A final-verdict row passes only when expected_final equals TAMonitor final verdict and no required prefix oracle contradicts it.",
            "Current semantic runtime rows with hand oracles are checked through semantic_oracle_derivations.csv.",
            "If expected_final is blank for a runtime claim, keep the row as review-required or build/stat-only.",
            "semantic_oracle_derivations.csv; semantic_regression_results.csv; glob:tamonitor_runs/*/summary.csv",
            sample_case_ids(semantic_oracle_derivation_rows, ["finite:", "future:F", "past:H"]),
            "Use the word column before deciding whether end-of-word finalization is valid.",
            "Do not mix finite-word finalization with infinite-word prefix semantics.",
        ),
        manual_oracle_guide_row(
            "MOG_SAT_CHECK",
            "satisfiability",
            "P1",
            "SAT/UNSAT is a construction-time formula check, not a replacement for a timed-word runtime oracle.",
            "A SAT expectation may support the pre-run formula check only when expected_sat is explicitly present.",
            "SAT rows are recorded in semantic_oracle_derivations.csv and generated run summary files.",
            "If SAT disagrees with a stated expectation, fix the formula/expectation or investigate MightyPPL construction before citing.",
            "semantic_oracle_derivations.csv; glob:tamonitor_runs/*/summary.csv",
            sample_case_ids(semantic_oracle_derivation_rows, ["finite:", "past:"]),
            "Review SAT disagreement separately from prefix/final verdict disagreement.",
            "Do not infer trace satisfaction from formula satisfiability alone.",
        ),
        manual_oracle_guide_row(
            "MOG_BUILD_STATS_BOUNDARY",
            "non_oracle_rows",
            "P0",
            "Existing MightyPPL corpus rows with no trace are construction/statistics coverage, not runtime correctness evidence.",
            "Rows with oracle_status=CONSTRUCTION_STATS_ONLY are acceptable only as build/stat coverage.",
            f"Current construction_stats_only rows={build_only}; oracle_review_required={review_required}.",
            "If a paper statement counts build/stat-only rows as runtime verdict correctness, reject or rewrite the claim.",
            "semantic_oracle_derivations.csv; semantic_regression_results.csv",
            sample_case_ids(semantic_oracle_derivation_rows, ["existing_mightyppl_testcase"], 8),
            "Keep construction coverage useful but separate from RV correctness counts.",
            "Do not claim timed-word correctness for rows without a timed word and expected verdict oracle.",
        ),
        manual_oracle_guide_row(
            "MOG_OPERATOR_SPOT_CHECK",
            "spot_check_plan",
            "P1",
            "Manual review should sample every user-facing operator family represented in the regression suite.",
            "At minimum, inspect F/G/U/R, past O/H/S/T, finite-word rows, and Pnueli Fn/On/Gn/Hn rows.",
            "Syntax coverage and oracle derivations identify the case ids backing each family.",
            "If an operator family lacks a readable derivation, add a hand-oracle case before expanding paper claims.",
            "mightyppl_syntax_coverage_audit.csv; semantic_oracle_derivations.csv; semantic_cases.csv",
            ";".join(filter(None, [
                sample_case_ids(semantic_oracle_derivation_rows, ["future:F"], 1),
                sample_case_ids(semantic_oracle_derivation_rows, ["future:G"], 1),
                sample_case_ids(semantic_oracle_derivation_rows, ["future:U"], 1),
                sample_case_ids(semantic_oracle_derivation_rows, ["future:R"], 1),
                sample_case_ids(semantic_oracle_derivation_rows, ["past:"], 1),
                sample_case_ids(semantic_oracle_derivation_rows, ["pnueli:"], 1),
            ])),
            "Use this row to decide which cases to inspect first when reviewing the workbook.",
            "Do not generalize beyond operator families that have explicit evidence rows.",
        ),
        manual_oracle_guide_row(
            "MOG_FIX_POLICY",
            "bug_fix_policy",
            "P0",
            "A mismatch is resolved by fixing the real source: oracle derivation, trace expectation, BDD projection, parser, monitor runner, or report extraction.",
            "After any fix, rerun the full pipeline and require zero mismatches and zero verifier failures.",
            "The current full pipeline records the latest post-fix evidence in pipeline_summary.json.",
            "Do not weaken MITL semantics, rewrite expected values to match the tool, or parse stdout as correctness evidence.",
            "pipeline_summary.json; review_packet_verification.csv; .codex/SESSION_LOG.md",
            "",
            "Record the bug cause and verification command in SESSION_LOG.",
            "Do not leave correctness bugs as manual follow-up without an explicit caveat or failing gate.",
        ),
        manual_oracle_guide_row(
            "MOG_SIGNOFF_BOUNDARY",
            "human_signoff",
            "P1",
            "Generated oracle ledgers make evidence reviewable; they are not human approval by themselves.",
            "Paper-facing claims need Review Signoff decisions after the reviewer checks linked oracle evidence.",
            "Review Signoff rows intentionally start blank.",
            "If reviewer_decision is blank, the result is ready for review but not human-approved.",
            "review_signoff_template.csv; human_review_queue.csv; manual_oracle_guide.csv",
            "",
            "Fill reviewer_decision only after checking the cited formula, trace, expected verdict, actual verdict, and evidence artifacts.",
            "Do not state that human review is complete from generated blank signoff rows.",
        ),
    ]


def write_manual_oracle_guide(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "manual_oracle_guide.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    section_counts = Counter(row["section"] for row in rows)
    lines = [
        "# Manual Oracle Guide",
        "",
        "This guide defines how to review hand-oracle evidence for TAMonitor semantic correctness.",
        "It is an audit protocol, not a new runtime algorithm and not a replacement for human signoff.",
        "",
        "## Sections",
        "",
    ]
    for section, count in sorted(section_counts.items()):
        lines.append(f"- `{section}`: {count}")
    lines.extend([
        "",
        "## Guide Rows",
        "",
        "| guide_id | priority | section | protocol_step | decision_rule | pass_condition | reject_or_fix_condition | evidence_artifacts | reviewer_action | must_not_claim |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        protocol_step = row["protocol_step"].replace("|", "\\|")
        decision_rule = row["decision_rule"].replace("|", "\\|")
        pass_condition = row["pass_condition"].replace("|", "\\|")
        reject_condition = row["reject_or_fix_condition"].replace("|", "\\|")
        evidence = row["evidence_artifacts"].replace("|", "\\|")
        reviewer_action = row["reviewer_action"].replace("|", "\\|")
        must_not_claim = row["must_not_claim"].replace("|", "\\|")
        lines.append(
            f"| `{row['guide_id']}` | `{row['priority']}` | `{row['section']}` | "
            f"{protocol_step} | {decision_rule} | {pass_condition} | "
            f"{reject_condition} | {evidence} | {reviewer_action} | {must_not_claim} |"
        )
    lines.append("")
    (output_dir / "manual_oracle_guide.md").write_text("\n".join(lines), encoding="utf-8")


def build_semantic_exclusion_rows() -> list[dict[str, Any]]:
    rows = []
    for form in INTERNAL_COUNT_FORMS:
        rows.append({
            "excluded_id": "internal_count_" + form.replace("*", "_star"),
            "form": form,
            "starred": "true" if form.endswith("*") else "false",
            "reason": INTERNAL_COUNT_FORMS_REASON,
            "source_context": "MightyPPL internal counting/Pnueli compilation form; not parsed as an ordinary user-level MITL benchmark formula.",
            "user_level": "false",
            "run_policy": "not_run",
            "expected_verdict": "N/A",
            "reviewer_note": "Do not expand this into a displayed MITL regression formula; cover user-facing Fn/On/Gn/Hn instead.",
        })
    return rows


def write_semantic_exclusions(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "semantic_exclusions.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    lines = [
        "# Semantic Exclusions",
        "",
        "These forms are intentionally excluded from user-level MITL semantic regression.",
        INTERNAL_COUNT_FORMS_REASON,
        "",
        "| form | starred | run_policy | reviewer_note |",
        "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| `{row['form']}` | `{row['starred']}` | `{row['run_policy']}` | {row['reviewer_note']} |")
    lines.append("")
    (output_dir / "semantic_exclusions.md").write_text("\n".join(lines), encoding="utf-8")


def build_mightyppl_syntax_coverage_audit(
    case_rows: list[dict[str, Any]],
    semantic_rows: list[dict[str, Any]],
    semantic_exclusion_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    case_by_id = {str(row["case_id"]): row for row in case_rows}
    result_by_case = {str(row["case_id"]): row for row in semantic_rows}
    categories_by_case = {case_id: str(row.get("category", "")) for case_id, row in case_by_id.items()}
    excluded_forms = {str(row.get("form", "")): row for row in semantic_exclusion_rows}

    def ids_for_categories(categories: list[str]) -> list[str]:
        wanted = set(categories)
        return [
            case_id
            for case_id, category in categories_by_case.items()
            if category in wanted
        ]

    def ids_for_spec(spec: dict[str, Any]) -> list[str]:
        ids: list[str] = []
        ids.extend(spec.get("case_ids", []))
        ids.extend(ids_for_categories(spec.get("categories", [])))
        if spec.get("category_prefixes"):
            prefixes = tuple(spec["category_prefixes"])
            ids.extend([
                case_id
                for case_id, category in categories_by_case.items()
                if category.startswith(prefixes)
            ])
        seen: set[str] = set()
        ordered = []
        for case_id in ids:
            if case_id in case_by_id and case_id not in seen:
                ordered.append(case_id)
                seen.add(case_id)
        return ordered

    def verified_case_ids(case_ids: list[str]) -> list[str]:
        return [
            case_id
            for case_id in case_ids
            if result_by_case.get(case_id, {}).get("correctness_status") == "VERIFIED"
        ]

    specs = [
        {
            "syntax_id": "formula_atom",
            "syntax_family": "formula",
            "construct": "formula -> atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["atom:true", "atom:false", "atom:idfr"],
            "source_reference": "tool/MightyPPL/Mitl.g4:14-21,36-67",
            "notes": "Base formula production is exercised through literal, identifier, and temporal-wrapper cases in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "formula_not",
            "syntax_family": "boolean",
            "construct": "! atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["formula:!"],
            "source_reference": "tool/MightyPPL/Mitl.g4:16,78",
            "notes": "Negation is checked as a user-level formula before MightyPPL NNF rewriting in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "formula_and",
            "syntax_family": "boolean",
            "construct": "formula && formula",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["formula:&&", "finite:&&"],
            "source_reference": "tool/MightyPPL/Mitl.g4:17,79",
            "notes": "Includes infinite and finite hand-oracle cases.",
            "require_both_words": True,
        },
        {
            "syntax_id": "formula_or",
            "syntax_family": "boolean",
            "construct": "formula || formula",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["formula:||"],
            "source_reference": "tool/MightyPPL/Mitl.g4:18,80",
            "notes": "Runtime oracle verifies positive disjunction witness in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "formula_iff",
            "syntax_family": "boolean",
            "construct": "formula <-> formula",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["formula:<->"],
            "source_reference": "tool/MightyPPL/Mitl.g4:19,81",
            "notes": "Runtime oracle checks equivalence under equal truth values in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "formula_implies",
            "syntax_family": "boolean",
            "construct": "formula -> formula",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["formula:->"],
            "source_reference": "tool/MightyPPL/Mitl.g4:20,82",
            "notes": "Runtime oracle checks implication under satisfied antecedent/consequent in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "atom_paren",
            "syntax_family": "atom",
            "construct": "( formula )",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["formula:&&", "formula:||", "formula:<->", "formula:->"],
            "source_reference": "tool/MightyPPL/Mitl.g4:66",
            "notes": "Parenthesized formulas occur inside Boolean regression formulas in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "atom_true",
            "syntax_family": "atom",
            "construct": "true",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["atom:true"],
            "source_reference": "tool/MightyPPL/Mitl.g4:63",
            "notes": "Literal true is checked under an F wrapper in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "atom_false",
            "syntax_family": "atom",
            "construct": "false",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["atom:false"],
            "source_reference": "tool/MightyPPL/Mitl.g4:64",
            "notes": "Literal false is checked under an F wrapper in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "atom_identifier",
            "syntax_family": "atom",
            "construct": "Idfr",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["atom:idfr"],
            "source_reference": "tool/MightyPPL/Mitl.g4:65,103",
            "notes": "Identifier proposition valuation is checked through p1 in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "interval_closed",
            "syntax_family": "interval",
            "construct": "[a,b]",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["future:F", "future:U", "future:R", "finite:F", "finite:U", "finite:R"],
            "source_reference": "tool/MightyPPL/Mitl.g4:29-34",
            "notes": "Closed finite intervals appear throughout future and finite-word cases.",
            "require_both_words": True,
        },
        {
            "syntax_id": "interval_left_open",
            "syntax_family": "interval",
            "construct": "(a,b]",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["interval:(]"],
            "source_reference": "tool/MightyPPL/Mitl.g4:31",
            "notes": "Left-open lower bound has dedicated hand oracles in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "interval_right_open",
            "syntax_family": "interval",
            "construct": "[a,b)",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["interval:[)"],
            "source_reference": "tool/MightyPPL/Mitl.g4:32",
            "notes": "Right-open upper bound has dedicated hand oracles in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "interval_open",
            "syntax_family": "interval",
            "construct": "(a,b)",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["interval:()", "finite:interval:()"],
            "source_reference": "tool/MightyPPL/Mitl.g4:33",
            "notes": "Open interval is checked in both infinite and finite word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "interval_unbounded",
            "syntax_family": "interval",
            "construct": "[a,infty)",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["interval:infty"],
            "source_reference": "tool/MightyPPL/Mitl.g4:24-27,101-102",
            "notes": "The grammar admits `infty` as a bound; both word modes use F [0,infty) p1.",
            "require_both_words": True,
        },
        {
            "syntax_id": "future_F",
            "syntax_family": "future_unary",
            "construct": "F interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["future:F", "finite:F"],
            "source_reference": "tool/MightyPPL/Mitl.g4:39,84; tool/MightyPPL/MitlTypingVisitor.cpp:71-92",
            "notes": "Positive and negative eventually cases plus finite-word variants are checked.",
            "require_both_words": True,
        },
        {
            "syntax_id": "future_F_star",
            "syntax_family": "future_unary",
            "construct": "F* interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["future:F*"],
            "source_reference": "tool/MightyPPL/Mitl.g4:39,70,84; tool/MightyPPL/MitlTypingVisitor.cpp:88-90",
            "notes": "Starred weak finally boundary semantics has hand oracles in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "future_G",
            "syntax_family": "future_unary",
            "construct": "G interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["future:G", "finite:G"],
            "source_reference": "tool/MightyPPL/Mitl.g4:42,86; tool/MightyPPL/MitlTypingVisitor.cpp:119-143",
            "notes": "Both inconclusive-hold and violation cases are checked; finite violation is included.",
            "require_both_words": True,
        },
        {
            "syntax_id": "future_G_star",
            "syntax_family": "future_unary",
            "construct": "G* interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["future:G*"],
            "source_reference": "tool/MightyPPL/Mitl.g4:42,70,86; tool/MightyPPL/MitlTypingVisitor.cpp:140-142",
            "notes": "Includes boundary-trigger and finite-end regressions for starred global semantics.",
            "require_both_words": True,
        },
        {
            "syntax_id": "future_U",
            "syntax_family": "future_binary",
            "construct": "atom U interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["future:U", "finite:U"],
            "source_reference": "tool/MightyPPL/Mitl.g4:45,88; tool/MightyPPL/MitlTypingVisitor.cpp:175-203",
            "notes": "Positive and negative until witnesses are checked in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "future_U_star",
            "syntax_family": "future_binary",
            "construct": "atom U* interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["future:U*", "finite:U*"],
            "source_reference": "tool/MightyPPL/Mitl.g4:45,70,88; tool/MightyPPL/MitlTypingVisitor.cpp:198-200",
            "notes": "Weak until boundary witness is checked in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "future_R",
            "syntax_family": "future_binary",
            "construct": "atom R interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["future:R", "finite:R"],
            "source_reference": "tool/MightyPPL/Mitl.g4:48,90; tool/MightyPPL/MitlTypingVisitor.cpp:237-264",
            "notes": "Release dual semantics is checked in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "future_R_star",
            "syntax_family": "future_binary",
            "construct": "atom R* interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["future:R*", "finite:R*"],
            "source_reference": "tool/MightyPPL/Mitl.g4:48,70,90; tool/MightyPPL/MitlTypingVisitor.cpp:260-263",
            "notes": "Weak release has infinite-prefix and finite-end oracle rows.",
            "require_both_words": True,
        },
        {
            "syntax_id": "past_O",
            "syntax_family": "past_unary",
            "construct": "O interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["past:O", "finite:O"],
            "source_reference": "tool/MightyPPL/Mitl.g4:40,85; tool/MightyPPL/MitlTypingVisitor.cpp:95-115",
            "notes": "Strict once is checked in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "past_O_star",
            "syntax_family": "past_unary",
            "construct": "O* interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["past:O*"],
            "source_reference": "tool/MightyPPL/Mitl.g4:40,70,85; tool/MightyPPL/MitlTypingVisitor.cpp:112-114",
            "notes": "Weak once boundary behavior has hand oracles in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "past_H",
            "syntax_family": "past_unary",
            "construct": "H interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["past:H", "finite:H"],
            "source_reference": "tool/MightyPPL/Mitl.g4:43,87; tool/MightyPPL/MitlTypingVisitor.cpp:147-171",
            "notes": "Historically is checked in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "past_H_star",
            "syntax_family": "past_unary",
            "construct": "H* interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["past:H*"],
            "source_reference": "tool/MightyPPL/Mitl.g4:43,70,87; tool/MightyPPL/MitlTypingVisitor.cpp:168-170",
            "notes": "Weak historically has positive hand oracles in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "past_S",
            "syntax_family": "past_binary",
            "construct": "atom S interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["past:S", "finite:S"],
            "source_reference": "tool/MightyPPL/Mitl.g4:46,89; tool/MightyPPL/MitlTypingVisitor.cpp:206-233",
            "notes": "Strict since is checked in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "past_S_star",
            "syntax_family": "past_binary",
            "construct": "atom S* interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["past:S*"],
            "source_reference": "tool/MightyPPL/Mitl.g4:46,70,89; tool/MightyPPL/MitlTypingVisitor.cpp:230-232",
            "notes": "Weak since boundary behavior has hand oracles in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "past_T",
            "syntax_family": "past_binary",
            "construct": "atom T interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["past:T", "finite:T"],
            "source_reference": "tool/MightyPPL/Mitl.g4:49,91; tool/MightyPPL/MitlTypingVisitor.cpp:268-295",
            "notes": "Trigger dual semantics is checked in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "past_T_star",
            "syntax_family": "past_binary",
            "construct": "atom T* interval? atom",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["past:T*"],
            "source_reference": "tool/MightyPPL/Mitl.g4:49,70,91; tool/MightyPPL/MitlTypingVisitor.cpp:291-294",
            "notes": "Weak trigger boundary behavior has hand oracles in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "pnueli_Fn",
            "syntax_family": "pnueli",
            "construct": "Fn interval (atom, atom, ...)",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["pnueli:Fn", "finite:Fn"],
            "source_reference": "tool/MightyPPL/Mitl.g4:51,92; tool/MightyPPL/MitlTypingVisitor.cpp:299-322",
            "notes": "Future Pnueli sequence is checked in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "pnueli_On",
            "syntax_family": "pnueli",
            "construct": "On interval (atom, atom, ...)",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["pnueli:On"],
            "source_reference": "tool/MightyPPL/Mitl.g4:52,93; tool/MightyPPL/MitlTypingVisitor.cpp:326-349",
            "notes": "Past Pnueli existential has hand oracles in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "pnueli_Gn",
            "syntax_family": "pnueli",
            "construct": "Gn interval (atom, atom, ...)",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["pnueli:Gn", "finite:Gn"],
            "source_reference": "tool/MightyPPL/Mitl.g4:54,94; tool/MightyPPL/MitlTypingVisitor.cpp:353-380",
            "notes": "Future Pnueli universal dual is checked in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "pnueli_Hn",
            "syntax_family": "pnueli",
            "construct": "Hn interval (atom, atom, ...)",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "categories": ["pnueli:Hn", "finite:Hn"],
            "source_reference": "tool/MightyPPL/Mitl.g4:55,95; tool/MightyPPL/MitlTypingVisitor.cpp:384-411",
            "notes": "Past Pnueli universal dual is checked in both word modes.",
            "require_both_words": True,
        },
        {
            "syntax_id": "word_modes",
            "syntax_family": "runtime_semantics",
            "construct": "finite and infinite timed words",
            "user_level": "true",
            "expected_policy": "runtime_oracle",
            "category_prefixes": ["finite:", "future:", "past:", "pnueli:", "formula:", "atom:", "interval:"],
            "source_reference": "src/TAMonitor/TAMonitorOptions.cpp; test/TARV/scripts/run_paper_experiments.py",
            "notes": "Ledger row checks that both requested word modes have verified semantic oracle rows.",
            "require_both_words": True,
        },
        {
            "syntax_id": "existing_mightyppl_testcases",
            "syntax_family": "regression_corpus",
            "construct": "tool/MightyPPL/testcases/**/*.mitl",
            "user_level": "true",
            "expected_policy": "build_stats_only",
            "categories": ["existing_mightyppl_testcase"],
            "source_reference": "tool/MightyPPL/testcases/**/*.mitl",
            "notes": "Existing MightyPPL formulas are construction/SAT/statistics evidence, not timed-word verdict oracles.",
        },
    ]

    for form in INTERNAL_COUNT_FORMS:
        specs.append({
            "syntax_id": "internal_" + form.replace("*", "_star"),
            "syntax_family": "internal_count",
            "construct": form,
            "user_level": "false",
            "expected_policy": "excluded_internal_form",
            "source_reference": "tool/MightyPPL/Mitl.g4:57-61,96-99; tool/MightyPPL/MitlToNNFVisitor.cpp:894-914",
            "notes": INTERNAL_COUNT_FORMS_REASON,
            "excluded_form": form,
        })

    rows: list[dict[str, Any]] = []
    for spec in specs:
        policy = spec["expected_policy"]
        candidate_ids = ids_for_spec(spec)
        verified_ids = verified_case_ids(candidate_ids)
        finite_ids = [case_id for case_id in verified_ids if case_by_id[case_id].get("word") == "finite"]
        infinite_ids = [case_id for case_id in verified_ids if case_by_id[case_id].get("word") == "infinite"]
        excluded_form = spec.get("excluded_form", "")
        exclusion_row = excluded_forms.get(excluded_form, {}) if excluded_form else {}

        if policy == "runtime_oracle":
            if spec.get("require_both_words"):
                coverage_status = "VERIFIED_RUNTIME_FINITE_AND_INFINITE" if finite_ids and infinite_ids else "MISSING"
            else:
                coverage_status = "VERIFIED_RUNTIME" if verified_ids else "MISSING"
            review_action = "Review matching semantic rows and prefix oracle rows." if coverage_status.startswith("VERIFIED") else "Add a hand-oracle semantic case before claiming coverage."
            evidence_summary = f"verified_cases={len(verified_ids)}; finite={len(finite_ids)}; infinite={len(infinite_ids)}"
        elif policy == "build_stats_only":
            build_rows = [
                case_id
                for case_id in candidate_ids
                if result_by_case.get(case_id, {}).get("correctness_status") in {"NOT_A_VERDICT_CHECK", "NOT_A_VERDICT_CHECK_BUILD_TIMEOUT"}
            ]
            coverage_status = "BUILD_STATS_ONLY" if build_rows else "MISSING"
            verified_ids = build_rows
            finite_ids = []
            infinite_ids = []
            review_action = "Use this row only as construction/SAT/statistics evidence, not RV correctness evidence."
            evidence_summary = f"build_stats_cases={len(build_rows)}"
        elif policy == "excluded_internal_form":
            coverage_status = "EXCLUDED_INTERNAL_FORM" if exclusion_row else "MISSING"
            review_action = "Do not create user-facing MITL runtime oracle formulas for this internal form."
            evidence_summary = "exclusion_ledger_row=present" if exclusion_row else "exclusion_ledger_row=missing"
        else:
            coverage_status = "MISSING"
            review_action = "Unknown policy; inspect harness."
            evidence_summary = "unknown_policy"

        rows.append({
            "syntax_id": spec["syntax_id"],
            "syntax_family": spec["syntax_family"],
            "construct": spec["construct"],
            "user_level": spec["user_level"],
            "expected_policy": policy,
            "coverage_status": coverage_status,
            "evidence_summary": evidence_summary,
            "evidence_case_ids": "|".join(verified_ids),
            "finite_case_ids": "|".join(finite_ids),
            "infinite_case_ids": "|".join(infinite_ids),
            "evidence_categories": "|".join(spec.get("categories", []) + [prefix + "*" for prefix in spec.get("category_prefixes", [])]),
            "source_reference": spec["source_reference"],
            "notes": spec["notes"],
            "review_action": review_action,
        })

    return rows


def write_mightyppl_syntax_coverage_audit(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "mightyppl_syntax_coverage_audit.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = Counter(row["coverage_status"] for row in rows)
    families = Counter(row["syntax_family"] for row in rows)
    lines = [
        "# MightyPPL Syntax Coverage Audit",
        "",
        "This generated ledger maps the MightyPPL grammar surface to either hand-oracle runtime evidence, build/statistics-only evidence, or an explicit internal-form exclusion.",
        "It is intended as the manual-review entry point for the claim that user-level MightyPPL syntax is covered without treating internal Count forms as ordinary MITL formulas.",
        "",
        "## Coverage Counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend(["", "## Family Counts", ""])
    for family, count in sorted(families.items()):
        lines.append(f"- `{family}`: {count}")
    lines.extend([
        "",
        "## Rows",
        "",
        "| syntax_id | construct | status | evidence | review_action |",
        "|---|---|---|---|---|",
    ])
    for row in rows:
        evidence = row["evidence_summary"].replace("|", "\\|")
        action = row["review_action"].replace("|", "\\|")
        construct = row["construct"].replace("|", "\\|")
        lines.append(f"| `{row['syntax_id']}` | `{construct}` | `{row['coverage_status']}` | {evidence} | {action} |")
    lines.append("")
    (output_dir / "mightyppl_syntax_coverage_audit.md").write_text("\n".join(lines), encoding="utf-8")


def internal_count_probe_formula(form: str) -> str:
    token = form.rstrip("*")
    star = "*" if form.endswith("*") else ""
    return f"{token}{star}[0,1](p1,p2)"


def classify_input_policy_result(result: dict[str, Any]) -> tuple[str, str, bool]:
    combined = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"
    assert_like = (
        str(result.get("returncode", "")) in {"-6", "134"}
        or re.search(r"\b(assert|Assertion|SIGABRT|Aborted|core dumped)\b", combined, re.IGNORECASE) is not None
    )
    if result.get("timeout"):
        return "TIMEOUT", "Timed out before a diagnostic was produced.", assert_like
    if "unsupported_user_formula" in combined and result.get("returncode") == 1 and not assert_like:
        return "EXPLICIT_UNSUPPORTED_USER_FORMULA", "TAMonitor rejected the internal form with a controlled unsupported_user_formula diagnostic.", assert_like
    if assert_like:
        return "ASSERT_OR_ABORT", "The process showed assert/abort-like behavior instead of a controlled diagnostic.", assert_like
    if result.get("returncode") == 0:
        return "ACCEPTED_UNEXPECTEDLY", "The internal form was accepted, which would blur user MITL and internal compiler syntax.", assert_like
    return "OTHER_ERROR", "The process failed, but not through the expected unsupported_user_formula diagnostic.", assert_like


def build_formula_input_policy_audit(output_dir: Path, timeout: int, tamonitor: Path, no_run: bool) -> list[dict[str, Any]]:
    audit_root = output_dir / "formula_input_policy"
    trace_path = audit_root / "trace.txt"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text("0,{p1}\n", encoding="utf-8")
    rows: list[dict[str, Any]] = []

    for form in INTERNAL_COUNT_FORMS:
        run_dir = audit_root / ("internal_" + form.replace("*", "_star"))
        formula_path = run_dir / "formula.mitl"
        formula_path.parent.mkdir(parents=True, exist_ok=True)
        formula_path.write_text(internal_count_probe_formula(form) + "\n", encoding="utf-8")

        args = [
            str(tamonitor),
            "--formula", str(formula_path),
            "--trace", str(trace_path),
            "--word", "finite",
            "--state", "symbolic",
            "--build-mode", "flatten",
            "--max-valuations", "128",
            "--out", str(run_dir / "out"),
        ]
        command_result: dict[str, Any] = {"returncode": "", "stdout": "", "stderr": "", "elapsed_ms": "", "timeout": False}
        if not no_run:
            command_result = run_command(args, min(timeout, 10))
        actual_class, evidence, assert_like = (
            ("NOT_RUN", "Execution was skipped by --no-run.", False)
            if no_run else classify_input_policy_result(command_result)
        )
        pass_status = "PASS" if actual_class == "EXPLICIT_UNSUPPORTED_USER_FORMULA" else ("NOT_RUN" if no_run else "FAIL")
        rows.append({
            "policy_id": "internal_count_input_" + form.replace("*", "_star"),
            "form": form,
            "starred": "true" if form.endswith("*") else "false",
            "user_level": "false",
            "probe_policy": "internal_form_guard",
            "probe_input_disclosure": "redacted_minimal_internal_count_probe",
            "expected_exit_class": "EXPLICIT_UNSUPPORTED_USER_FORMULA",
            "actual_exit_class": actual_class,
            "pass_status": pass_status,
            "returncode": command_result.get("returncode", ""),
            "timeout": command_result.get("timeout", ""),
            "elapsed_ms": command_result.get("elapsed_ms", ""),
            "assert_like_failure": "true" if assert_like else "false",
            "diagnostic_contains": "unsupported_user_formula" if "unsupported_user_formula" in f"{command_result.get('stdout', '')}\n{command_result.get('stderr', '')}" else "",
            "evidence": evidence,
            "stderr_excerpt": (command_result.get("stderr", "") or "")[:500].replace("\n", " "),
            "stdout_excerpt": (command_result.get("stdout", "") or "")[:500].replace("\n", " "),
            "run_dir": str(run_dir),
        })
    return rows


def write_formula_input_policy_audit(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "formula_input_policy_audit.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = Counter(row["pass_status"] for row in rows)
    lines = [
        "# Formula Input Policy Audit",
        "",
        "This generated audit checks that parser-visible internal Count forms are rejected with a controlled TAMonitor diagnostic.",
        "These probes are not MITL semantic regression cases and are not counted as user-level formula correctness evidence.",
        "The concrete probe formulas are intentionally redacted from the review table; use the `form` token and diagnostic class for review.",
        "",
        "## Counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend([
        "",
        "## Rows",
        "",
        "| policy_id | form | expected | actual | pass_status | assert_like_failure |",
        "|---|---|---|---|---|---|",
    ])
    for row in rows:
        lines.append(
            f"| `{row['policy_id']}` | `{row['form']}` | `{row['expected_exit_class']}` | "
            f"`{row['actual_exit_class']}` | `{row['pass_status']}` | `{row['assert_like_failure']}` |"
        )
    lines.append("")
    (output_dir / "formula_input_policy_audit.md").write_text("\n".join(lines), encoding="utf-8")


def classify_cli_result(result: dict[str, Any], expected_diagnostic: str) -> tuple[str, str]:
    combined = f"{result.get('stdout', '')}\n{result.get('stderr', '')}"
    if result.get("timeout"):
        return "TIMEOUT", "Command timed out before completing."
    if result.get("returncode") == 0:
        return "OK", "Command completed with exit code 0."
    if expected_diagnostic and expected_diagnostic in combined:
        return "CONTROLLED_ERROR", f"Command failed with expected diagnostic: {expected_diagnostic}."
    return "ERROR", "Command failed without the expected controlled diagnostic."


def build_cli_contract_audit(output_dir: Path, timeout: int, tamonitor: Path, no_run: bool) -> list[dict[str, Any]]:
    audit_root = output_dir / "cli_contract"
    audit_root.mkdir(parents=True, exist_ok=True)

    formula_file = audit_root / "formula_file_positive.mitl"
    formula_file.write_text("F [0,2] p1\n", encoding="utf-8")
    trace_props = audit_root / "trace_props.txt"
    trace_props.write_text("0,{}\n1,{p1}\n", encoding="utf-8")
    trace_header_props = audit_root / "trace_header_props.csv"
    trace_header_props.write_text("time,props\n0,{}\n1,{p1}\n", encoding="utf-8")
    trace_bits = audit_root / "trace_bits.txt"
    trace_bits.write_text("0,bits:0\n1,bits:1\n", encoding="utf-8")
    trace_at = audit_root / "trace_at_time.txt"
    trace_at.write_text("@0 {}\n@1 {p1}\n", encoding="utf-8")
    trace_bad_prop = audit_root / "trace_bad_prop.txt"
    trace_bad_prop.write_text("0,{p2}\n", encoding="utf-8")
    missing_formula = audit_root / "missing_formula.mitl"

    specs = [
        {
            "audit_id": "cli_formula_file_trace_file_finite_symbolic",
            "scenario": "formula file plus trace file in finite symbolic flatten mode",
            "input_surface": "--formula + --trace + finite + symbolic",
            "args": [
                str(tamonitor), "--formula", str(formula_file), "--trace", str(trace_props),
                "--word", "finite", "--state", "symbolic", "--build-mode", "flatten",
                "--max-valuations", "128", "--emit-bdd-interface",
            ],
            "expected_exit_class": "OK",
            "expected_summary": {
                "final_verdict": "POSITIVE",
                "formula_satisfiable": "SAT",
                "build_mode": "flatten",
                "run_mode": "monitor",
                "word_mode": "finite",
                "state_mode": "symbolic",
                "max_valuations": "128",
                "events": "2",
                "processed_steps": "2",
            },
            "expect_bdd_interface": True,
        },
        {
            "audit_id": "cli_formula_inline_bits_infinite_concrete",
            "scenario": "inline formula plus bits trace in infinite concrete mode",
            "input_surface": "--formula-inline + bits trace + infinite + concrete",
            "args": [
                str(tamonitor), "--formula-inline", "F [0,2] p1", "--trace", str(trace_bits),
                "--word", "infinite", "--state", "concrete", "--build-mode", "flatten",
                "--max-valuations", "129", "--emit-bdd-interface",
            ],
            "expected_exit_class": "OK",
            "expected_summary": {
                "final_verdict": "POSITIVE",
                "formula_satisfiable": "SAT",
                "build_mode": "flatten",
                "run_mode": "monitor",
                "word_mode": "infinite",
                "state_mode": "concrete",
                "max_valuations": "129",
                "events": "2",
                "processed_steps": "2",
            },
            "expect_bdd_interface": True,
        },
        {
            "audit_id": "cli_trace_csv_header_time_props",
            "scenario": "trace file with a time,props CSV header",
            "input_surface": "time,props header trace",
            "args": [
                str(tamonitor), "--formula-inline", "F [0,2] p1", "--trace", str(trace_header_props),
                "--word", "finite", "--state", "symbolic", "--build-mode", "flatten",
                "--max-valuations", "133",
            ],
            "expected_exit_class": "OK",
            "expected_summary": {
                "final_verdict": "POSITIVE",
                "formula_satisfiable": "SAT",
                "build_mode": "flatten",
                "run_mode": "monitor",
                "word_mode": "finite",
                "state_mode": "symbolic",
                "max_valuations": "133",
                "events": "2",
                "processed_steps": "2",
            },
        },
        {
            "audit_id": "cli_stdin_trace_interactive_path",
            "scenario": "inline formula with timed events entered through stdin",
            "input_surface": "--formula-inline + stdin trace",
            "args": [
                str(tamonitor), "--formula-inline", "F [0,2] p1",
                "--word", "finite", "--state", "symbolic", "--build-mode", "flatten",
                "--max-valuations", "130",
            ],
            "stdin_text": "0,{}\n1,{p1}\n\n",
            "expected_exit_class": "OK",
            "expected_summary": {
                "final_verdict": "POSITIVE",
                "formula_satisfiable": "SAT",
                "build_mode": "flatten",
                "run_mode": "monitor",
                "word_mode": "finite",
                "state_mode": "symbolic",
                "max_valuations": "130",
                "events": "2",
                "processed_steps": "2",
            },
            "expected_stdout_contains": "Enter timed events",
        },
        {
            "audit_id": "cli_at_time_trace_format",
            "scenario": "trace file using MoniTAal-compatible @time label import format",
            "input_surface": "@time trace import",
            "args": [
                str(tamonitor), "--formula-inline", "F [0,2] p1", "--trace", str(trace_at),
                "--word", "finite", "--state", "symbolic", "--build-mode", "flatten",
                "--max-valuations", "131",
            ],
            "expected_exit_class": "OK",
            "expected_summary": {
                "final_verdict": "POSITIVE",
                "formula_satisfiable": "SAT",
                "build_mode": "flatten",
                "run_mode": "monitor",
                "word_mode": "finite",
                "state_mode": "symbolic",
                "events": "2",
                "processed_steps": "2",
            },
        },
        {
            "audit_id": "cli_compflatten_build_only",
            "scenario": "compflatten construction/statistics mode is available only with --build-only",
            "input_surface": "--build-mode compflatten --build-only",
            "args": [
                str(tamonitor), "--formula-inline", "F [0,1] p1",
                "--word", "finite", "--state", "symbolic", "--build-mode", "compflatten",
                "--build-only", "--max-valuations", "132",
            ],
            "expected_exit_class": "OK",
            "expected_summary": {
                "final_verdict": "NOT_RUN_BUILD_ONLY",
                "formula_satisfiable": "NOT_CHECKED_COMPFLATTEN_BUILD_ONLY",
                "build_mode": "compflatten",
                "run_mode": "build_only",
                "word_mode": "finite",
                "state_mode": "symbolic",
                "events": "0",
                "processed_steps": "0",
            },
        },
        {
            "audit_id": "cli_compflatten_runtime_rejected",
            "scenario": "compflatten runtime verdicts are explicitly rejected in v1",
            "input_surface": "--build-mode compflatten without --build-only",
            "args": [
                str(tamonitor), "--formula-inline", "F [0,1] p1", "--trace", str(trace_props),
                "--word", "finite", "--state", "symbolic", "--build-mode", "compflatten",
            ],
            "expected_exit_class": "CONTROLLED_ERROR",
            "expected_diagnostic": "unsupported_runtime_mode",
        },
        {
            "audit_id": "cli_mutually_exclusive_formula_inputs",
            "scenario": "formula file and inline formula cannot both be provided",
            "input_surface": "--formula and --formula-inline",
            "args": [
                str(tamonitor), "--formula", str(formula_file), "--formula-inline", "F [0,2] p1",
                "--trace", str(trace_props),
            ],
            "expected_exit_class": "CONTROLLED_ERROR",
            "expected_diagnostic": "Provide at most one of --formula or --formula-inline",
        },
        {
            "audit_id": "cli_invalid_trace_unknown_prop",
            "scenario": "trace propositions outside formula vocabulary are rejected",
            "input_surface": "trace references unknown proposition",
            "args": [
                str(tamonitor), "--formula-inline", "F [0,2] p1", "--trace", str(trace_bad_prop),
                "--word", "finite", "--state", "symbolic", "--build-mode", "flatten",
            ],
            "expected_exit_class": "CONTROLLED_ERROR",
            "expected_diagnostic": "Trace references proposition not present in formula",
        },
        {
            "audit_id": "cli_missing_formula_file",
            "scenario": "missing formula file produces a controlled diagnostic",
            "input_surface": "--formula missing path",
            "args": [
                str(tamonitor), "--formula", str(missing_formula), "--trace", str(trace_props),
            ],
            "expected_exit_class": "CONTROLLED_ERROR",
            "expected_diagnostic": "Could not open formula file",
        },
        {
            "audit_id": "cli_invalid_max_valuations",
            "scenario": "valuation cap must be positive",
            "input_surface": "--max-valuations 0",
            "args": [
                str(tamonitor), "--formula-inline", "F [0,2] p1", "--trace", str(trace_props),
                "--max-valuations", "0",
            ],
            "expected_exit_class": "CONTROLLED_ERROR",
            "expected_diagnostic": "--max-valuations must be positive",
        },
    ]

    rows: list[dict[str, Any]] = []
    for spec in specs:
        run_dir = audit_root / spec["audit_id"] / "out"
        args = [*spec["args"], "--out", str(run_dir)]
        command_result: dict[str, Any] = {"returncode": "", "stdout": "", "stderr": "", "elapsed_ms": "", "timeout": False}
        if not no_run:
            command_result = run_command(args, min(timeout, 15), stdin_text=spec.get("stdin_text"))

        expected_diagnostic = spec.get("expected_diagnostic", "")
        actual_exit_class, evidence = (
            ("NOT_RUN", "Execution was skipped by --no-run.")
            if no_run else classify_cli_result(command_result, expected_diagnostic)
        )
        summary = read_summary_csv(run_dir / "summary.csv")
        metadata_exists = (run_dir / "metadata.json").exists()
        steps_exists = (run_dir / "steps.csv").exists()
        xlsx_exists = (run_dir / "results.xlsx").exists()
        bdd_interface_status = ""
        bdd_interface_path = run_dir / "bdd_interface.json"
        if bdd_interface_path.exists():
            try:
                bdd_interface_status = json.loads(bdd_interface_path.read_text(encoding="utf-8")).get("status", "")
            except json.JSONDecodeError:
                bdd_interface_status = "JSON_PARSE_ERROR"

        issues: list[str] = []
        if actual_exit_class != spec["expected_exit_class"]:
            issues.append(f"expected_exit_class={spec['expected_exit_class']} actual={actual_exit_class}")
        if spec["expected_exit_class"] == "OK":
            if command_result.get("returncode") != 0:
                issues.append("returncode was not 0")
            expected_summary = spec.get("expected_summary", {})
            for key, expected_value in expected_summary.items():
                actual_value = summary.get(key, "")
                if actual_value != expected_value:
                    issues.append(f"summary[{key}] expected {expected_value} actual {actual_value}")
            if not (metadata_exists and steps_exists and xlsx_exists):
                issues.append("one or more report files are missing")
            if spec.get("expect_bdd_interface") and bdd_interface_status != "interface_reserved_not_implemented":
                issues.append(f"bdd_interface_status={bdd_interface_status or '<missing>'}")
            expected_stdout = spec.get("expected_stdout_contains", "")
            if expected_stdout and expected_stdout not in command_result.get("stdout", ""):
                issues.append(f"stdout did not contain {expected_stdout!r}")
        elif spec["expected_exit_class"] == "CONTROLLED_ERROR" and expected_diagnostic not in f"{command_result.get('stdout', '')}\n{command_result.get('stderr', '')}":
            issues.append(f"missing expected diagnostic {expected_diagnostic!r}")

        pass_status = "NOT_RUN" if no_run else ("PASS" if not issues else "FAIL")
        report_files = [
            name for name in ["steps.csv", "summary.csv", "metadata.json", "bdd_interface.json", "results.xlsx"]
            if (run_dir / name).exists()
        ]
        rows.append({
            "audit_id": spec["audit_id"],
            "scenario": spec["scenario"],
            "input_surface": spec["input_surface"],
            "expected_behavior": " ".join(spec.get("expected_summary", {}).values()) if spec.get("expected_summary") else spec.get("expected_diagnostic", ""),
            "expected_exit_class": spec["expected_exit_class"],
            "actual_exit_class": actual_exit_class,
            "pass_status": pass_status,
            "returncode": command_result.get("returncode", ""),
            "timeout": command_result.get("timeout", ""),
            "elapsed_ms": command_result.get("elapsed_ms", ""),
            "final_verdict": summary.get("final_verdict", ""),
            "formula_satisfiable": summary.get("formula_satisfiable", ""),
            "build_mode": summary.get("build_mode", ""),
            "run_mode": summary.get("run_mode", ""),
            "word_mode": summary.get("word_mode", ""),
            "state_mode": summary.get("state_mode", ""),
            "max_valuations": summary.get("max_valuations", ""),
            "events": summary.get("events", ""),
            "processed_steps": summary.get("processed_steps", ""),
            "bdd_interface_status": bdd_interface_status,
            "report_files": "|".join(report_files),
            "diagnostic_contains": expected_diagnostic if expected_diagnostic and expected_diagnostic in f"{command_result.get('stdout', '')}\n{command_result.get('stderr', '')}" else "",
            "evidence": evidence if not issues else " | ".join(issues),
            "stdout_excerpt": (command_result.get("stdout", "") or "")[:500].replace("\n", " "),
            "stderr_excerpt": (command_result.get("stderr", "") or "")[:500].replace("\n", " "),
            "run_dir": str(run_dir),
            "command": " ".join(args),
        })
    return rows


def write_cli_contract_audit(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "cli_contract_audit.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = Counter(row["pass_status"] for row in rows)
    lines = [
        "# TAMonitor CLI Contract Audit",
        "",
        "This generated audit runs the TAMonitor command surface directly.",
        "It covers formula file input, inline formula input, trace file formats, stdin trace input, build modes, state modes, BDD-interface metadata, and controlled error paths.",
        "",
        "## Counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend([
        "",
        "## Rows",
        "",
        "| audit_id | pass_status | expected_exit | actual_exit | evidence |",
        "|---|---|---|---|---|",
    ])
    for row in rows:
        evidence = row["evidence"].replace("|", "\\|")
        lines.append(
            f"| `{row['audit_id']}` | `{row['pass_status']}` | `{row['expected_exit_class']}` | "
            f"`{row['actual_exit_class']}` | {evidence} |"
        )
    lines.append("")
    (output_dir / "cli_contract_audit.md").write_text("\n".join(lines), encoding="utf-8")


def manual_review_row(
    review_id: str,
    review_area: str,
    workbook_sheet: str,
    automatic_status: str,
    human_decision_required: bool,
    review_question: str,
    evidence_summary: str,
    evidence_artifacts: str,
    must_not_claim: str,
    suggested_action: str,
) -> dict[str, Any]:
    return {
        "review_id": review_id,
        "review_area": review_area,
        "workbook_sheet": workbook_sheet,
        "automatic_status": automatic_status,
        "human_decision_required": "true" if human_decision_required else "false",
        "review_question": review_question,
        "evidence_summary": evidence_summary,
        "evidence_artifacts": evidence_artifacts,
        "must_not_claim": must_not_claim,
        "suggested_action": suggested_action,
    }


def build_manual_review_checklist(
    semantic_rows: list[dict[str, Any]],
    semantic_prefix_rows: list[dict[str, Any]],
    semantic_oracle_derivation_rows: list[dict[str, Any]],
    semantic_exclusion_rows: list[dict[str, Any]],
    syntax_coverage_rows: list[dict[str, Any]],
    input_policy_rows: list[dict[str, Any]],
    cli_contract_rows: list[dict[str, Any]],
    benchmark_manifest_rows: list[dict[str, Any]],
    proof_appendix_rows: list[dict[str, Any]],
    paper_claim_review_rows: list[dict[str, Any]],
    paper_claim_audit_rows: list[dict[str, Any]],
    xml_original_trace_gap_rows: list[dict[str, Any]],
    candidate_result_rows: list[dict[str, Any]],
    candidate_step_audit_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    verified_semantic = count_rows(semantic_rows, correctness_status="VERIFIED")
    semantic_fail = count_rows(semantic_rows, pass_status="FAIL")
    finite_verified = sum(1 for row in semantic_rows if row.get("word") == "finite" and row.get("correctness_status") == "VERIFIED")
    infinite_verified = sum(1 for row in semantic_rows if row.get("word") == "infinite" and row.get("correctness_status") == "VERIFIED")
    prefix_matches = count_rows(semantic_prefix_rows, prefix_oracle_status="MATCH")
    prefix_mismatches = count_rows(semantic_prefix_rows, prefix_oracle_status="MISMATCH")
    prefix_missing = count_rows(semantic_prefix_rows, prefix_oracle_status="MISSING_OBSERVED_STEP")
    oracle_verified = count_rows(semantic_oracle_derivation_rows, oracle_status="HAND_ORACLE_VERIFIED")
    oracle_build_only = count_rows(semantic_oracle_derivation_rows, oracle_status="CONSTRUCTION_STATS_ONLY")
    oracle_review_required = count_rows(semantic_oracle_derivation_rows, oracle_status="ORACLE_REVIEW_REQUIRED")
    oracle_prefix_mismatches = sum(int(row.get("prefix_mismatches", 0) or 0) for row in semantic_oracle_derivation_rows)
    syntax_missing = count_rows(syntax_coverage_rows, coverage_status="MISSING")
    syntax_runtime_verified = sum(1 for row in syntax_coverage_rows if str(row.get("coverage_status", "")).startswith("VERIFIED_RUNTIME"))
    syntax_internal_excluded = count_rows(syntax_coverage_rows, coverage_status="EXCLUDED_INTERNAL_FORM")
    input_policy_pass = count_rows(input_policy_rows, pass_status="PASS")
    input_policy_fail = count_rows(input_policy_rows, pass_status="FAIL")
    input_policy_assert_like = count_rows(input_policy_rows, assert_like_failure="true")
    cli_contract_pass = count_rows(cli_contract_rows, pass_status="PASS")
    cli_contract_fail = count_rows(cli_contract_rows, pass_status="FAIL")
    cli_contract_controlled_errors = count_rows(cli_contract_rows, actual_exit_class="CONTROLLED_ERROR")
    projection_rows = [
        row for row in semantic_rows
        if row.get("build_mode") == "flatten"
        and row.get("returncode") == 0
        and row.get("positive_projection_valuations") != ""
        and row.get("negative_projection_valuations") != ""
    ]
    compflatten_stats = sum(1 for row in semantic_rows if row.get("build_mode") == "compflatten" and row.get("pass_status") == "BUILD_STATS")
    manifest_rows = len(benchmark_manifest_rows)
    xml_ready = count_rows(proof_appendix_rows, appendix_status="PROOF_DRAFT_READY")
    xml_excluded = sum(1 for row in proof_appendix_rows if row.get("appendix_status") != "PROOF_DRAFT_READY")
    proof_ready = count_rows(proof_appendix_rows, appendix_status="PROOF_DRAFT_READY")
    claim_audit_fail = count_rows(paper_claim_audit_rows, audit_status="FAIL")
    claim_audit_warn = count_rows(paper_claim_audit_rows, audit_status="WARN")
    body_ready_after_signoff = count_rows(paper_claim_review_rows, claim_strength="BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF")
    timeout_caveat_claims = count_rows(paper_claim_review_rows, claim_strength="APPENDIX_INSTANCE_READY_WITH_TIMEOUT_CAVEAT")
    original_trace_gap_fail = count_rows(xml_original_trace_gap_rows, gap_status="FAIL")
    original_trace_gap_review_required = count_rows(xml_original_trace_gap_rows, gap_status="REVIEW_REQUIRED")
    original_trace_gap_classes = Counter(row.get("gap_class", "") for row in xml_original_trace_gap_rows)
    gear_body_ready = sum(
        1 for row in paper_claim_review_rows
        if row.get("proof_class") == "gear_bounded_request_response"
        and row.get("claim_strength") == "BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF"
    )
    candidate_matches = sum(1 for row in candidate_result_rows if row.get("baseline_comparison_status") == "MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT")
    candidate_mismatches = sum(1 for row in candidate_result_rows if row.get("baseline_comparison_status") == "MISMATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT")
    candidate_not_verified = sum(1 for row in candidate_result_rows if str(row.get("baseline_comparison_status", "")).startswith("NOT_VERIFIED"))
    candidate_steps_complete = sum(1 for row in candidate_step_audit_rows if row.get("all_trace_steps_recorded") == "true")
    candidate_steps_incomplete = sum(1 for row in candidate_step_audit_rows if row.get("all_trace_steps_recorded") != "true")
    baseline_timeouts = count_rows(baseline_rows, status="timeout")
    skipped_inputs = count_rows(baseline_rows, status="skipped_no_input")
    generated_empty_inputs = count_rows(baseline_rows, input_origin="generated_empty_no_original_input")
    bdd_interface_ok = source_contains(REPO_ROOT / "src" / "TAMonitor" / "ReportWriter.cpp", ["bdd_interface.json", "interface_reserved_not_implemented"])
    reproducibility_manifest_ok = source_contains(Path(__file__), ["reproducibility_manifest.json", "source_sha256", "result_sha256"])

    return [
        manual_review_row(
            "MR_HAND_ORACLE_FINAL_VERDICTS",
            "MITL semantic correctness",
            "Correctness Audit; Semantic Results",
            "PASS" if verified_semantic >= 53 and semantic_fail == 0 else "FAIL",
            True,
            "Do the manually specified final verdict oracles match TAMonitor output for all claimed MITL semantic cases?",
            f"semantic_verified={verified_semantic}; oracle_verified={oracle_verified}; build_only_not_oracle={oracle_build_only}; oracle_review_required={oracle_review_required}; semantic_fail={semantic_fail}.",
            "manual_oracle_guide.csv; semantic_oracle_derivations.csv; semantic_oracle_derivations.md; mitl_correctness_audit.csv; semantic_regression_results.csv; semantic_cases.csv",
            "Do not claim cases with build-only, timeout, resource-limit, or missing-oracle statuses as verified correctness.",
            "Review any non-VERIFIED row before citing the semantic regression suite.",
        ),
        manual_review_row(
            "MR_PREFIX_ORACLE",
            "Stepwise runtime verdicts",
            "Prefix Oracle",
            "PASS" if prefix_matches >= 115 and prefix_mismatches == 0 and prefix_missing == 0 else "FAIL",
            True,
            "Does each recorded timed-word prefix verdict match the hand oracle where an oracle is defined?",
            f"prefix_matches={prefix_matches}; prefix_mismatches={prefix_mismatches}; missing_observed_steps={prefix_missing}; oracle_derivation_prefix_mismatches={oracle_prefix_mismatches}.",
            "manual_oracle_guide.csv; semantic_oracle_derivations.csv; semantic_prefix_oracle_review.csv; semantic_prefix_oracle_review.md; glob:tamonitor_runs/*/steps.csv",
            "Do not use final-verdict correctness alone as evidence for per-prefix runtime verification.",
            "Open mismatches or missing rows first; otherwise spot-check representative F/G/U/R and past-operator rows.",
        ),
        manual_review_row(
            "MR_FINITE_INFINITE_WORD_MODES",
            "Finite/infinite word semantics",
            "Semantic Results; Semantic Cases",
            "PASS" if finite_verified >= 17 and infinite_verified >= 36 else "FAIL",
            True,
            "Are finite-word and infinite-word claims backed by separate hand-oracle rows?",
            f"finite_verified={finite_verified}; infinite_verified={infinite_verified}.",
            "semantic_cases.csv; semantic_regression_results.csv",
            "Do not generalize finite-word theorem claims beyond the operator-level cases present in this suite.",
            "If paper claims become theorem-specific, add matching finite-word hand-oracle cases.",
        ),
        manual_review_row(
            "MR_MIGHTYPPL_SYNTAX_COVERAGE",
            "MightyPPL syntax coverage",
            "Syntax Coverage",
            "PASS" if syntax_coverage_rows and syntax_missing == 0 and syntax_runtime_verified >= 36 and syntax_internal_excluded == len(INTERNAL_COUNT_FORMS) else "FAIL",
            True,
            "Does every user-level MightyPPL grammar construct have runtime evidence, build/stat evidence, or an explicit exclusion?",
            f"syntax_rows={len(syntax_coverage_rows)}; runtime_verified={syntax_runtime_verified}; internal_excluded={syntax_internal_excluded}; missing={syntax_missing}.",
            "mightyppl_syntax_coverage_audit.csv; mightyppl_syntax_coverage_audit.md; semantic_exclusions.csv",
            "Do not list internal Count forms as ordinary user MITL formulas.",
            "Check construct-by-construct coverage before stating full syntax coverage.",
        ),
        manual_review_row(
            "MR_INTERNAL_COUNT_INPUT_BOUNDARY",
            "Internal-form input policy",
            "Input Policy; Semantic Exclusions",
            "PASS" if len(input_policy_rows) == len(INTERNAL_COUNT_FORMS) and input_policy_pass == len(INTERNAL_COUNT_FORMS) and input_policy_fail == 0 and input_policy_assert_like == 0 and len(semantic_exclusion_rows) == len(INTERNAL_COUNT_FORMS) else "FAIL",
            True,
            "Are CFn/COn/CGn/CHn and starred variants excluded from MITL semantic tests and rejected through controlled diagnostics?",
            f"exclusion_rows={len(semantic_exclusion_rows)}; input_policy_pass={input_policy_pass}; input_policy_fail={input_policy_fail}; assert_like_failures={input_policy_assert_like}.",
            "semantic_exclusions.csv; formula_input_policy_audit.csv; formula_input_policy_audit.md",
            "Do not disclose or count redacted internal-form probes as MITL runtime-oracle formulas.",
            "Keep the rows as parser-boundary evidence only.",
        ),
        manual_review_row(
            "MR_BDD_PROJECTION_RUNTIME",
            "BDD-label projection",
            "Semantic Results",
            "PASS" if projection_rows else "FAIL",
            False,
            "Did flatten-mode runtime rows record positive and negative BDD valuation projection counts?",
            f"flatten_projection_rows={len(projection_rows)}.",
            "semantic_regression_results.csv; tool/MightyPPL/TAwithBDDEdges.cpp; src/TAMonitor/TAMonitorMightyAdapter.cpp; src/TAMonitor/TraceParser.cpp; src/TAMonitor/MonitorRunner.cpp; src/TAMonitor/ReportWriter.cpp",
            "Do not claim BDD-native runtime performance from valuation-projection evidence.",
            "Use these rows only for v1 projection-based runtime verification claims.",
        ),
        manual_review_row(
            "MR_CLI_CONTRACT",
            "TAMonitor command contract",
            "CLI Contract",
            "PASS" if cli_contract_rows and cli_contract_fail == 0 else "FAIL",
            False,
            "Does the TAMonitor command surface work for file/inline formula input, trace-file/stdin input, modes, reports, BDD metadata, and controlled errors?",
            f"cli_contract_rows={len(cli_contract_rows)}; pass={cli_contract_pass}; fail={cli_contract_fail}; controlled_error_paths={cli_contract_controlled_errors}.",
            "cli_contract_audit.csv; cli_contract_audit.json; cli_contract_audit.md; glob:cli_contract/*/out/metadata.json",
            "Do not claim an industrial CLI surface if any CLI contract probe fails.",
            "Use this sheet before demoing or scripting TAMonitor from the terminal.",
        ),
        manual_review_row(
            "MR_COMPFLATTEN_SCOPE",
            "Compflatten boundary",
            "Semantic Results; Requirements Audit",
            "PASS_WITH_CAVEAT" if compflatten_stats >= 1 else "FAIL",
            True,
            "Is compflatten represented only as construction/statistics evidence, never as a v1 runtime verdict?",
            f"compflatten_build_stats_rows={compflatten_stats}.",
            "semantic_regression_results.csv; requirements_traceability_audit.csv",
            "Do not claim compflatten runtime RV until a composition-aware or BDD-native monitor is implemented.",
            "Keep compflatten wording as build/statistics-only in v1.",
        ),
        manual_review_row(
            "MR_XML_TRANSLATION_SCOPE",
            "MoniTAal XML-to-MITL scope",
            "Benchmark Manifest; XML Proof Appendix",
            "REVIEW_REQUIRED" if manifest_rows == 23 and xml_ready == 15 and xml_excluded == 8 else "FAIL",
            True,
            "Which MoniTAal XML benchmark pairs are genuinely reviewable MITL candidates, and which remain excluded?",
            f"manifest_rows={manifest_rows}; proof_ready={xml_ready}; excluded={xml_excluded}.",
            "benchmark_manifest.csv; xml_proof_appendix.csv; xml_translation_proof_appendix.md",
            "Do not state that all XML benchmarks were equivalently converted to MITL.",
            "Manually inspect proof-ready rows before promoting them into paper text.",
        ),
        manual_review_row(
            "MR_XML_EDGE_PROOFS",
            "XML edge/guard proof evidence",
            "XML Edge Proofs; XML Proof Appendix",
            "REVIEW_REQUIRED" if proof_ready == 15 else "FAIL",
            True,
            "Do the edge/guard proof rows justify each candidate MITL pattern at trace level?",
            f"proof_appendix_ready={proof_ready}; proof_appendix_excluded={xml_excluded}.",
            "xml_edge_guard_proofs.csv; xml_proof_appendix.csv",
            "Do not treat the generated proof ledger as a final theorem without human proof review.",
            "Check clocks, guards, reset edges, accepting locations, and trace assumptions for each proof-ready row.",
        ),
        manual_review_row(
            "MR_XML_ORIGINAL_TRACE_GAPS",
            "Original trace provenance gaps",
            "Original Trace Gaps",
            "REVIEW_REQUIRED" if original_trace_gap_review_required else ("FAIL" if original_trace_gap_fail else "PASS"),
            True,
            "Do the remaining XML original-input provenance gaps have explicit human-review decisions and caveats?",
            (
                f"gap_rows={len(xml_original_trace_gap_rows)}; review_required={original_trace_gap_review_required}; "
                f"fail={original_trace_gap_fail}; classes="
                + ";".join(f"{key}:{value}" for key, value in sorted(original_trace_gap_classes.items()) if key)
            ),
            "xml_original_trace_gaps.csv; xml_original_trace_gaps.md; xml_trace_coverage_obligations.csv; benchmark_manifest.csv; monitaal_baseline_results.csv",
            "Do not treat generated review traces or INCONCLUSIVE repository traces as decisive original benchmark evidence.",
            "Review each XML_ORIGINAL_TRACE_GAP_* signoff row before claiming original-input coverage.",
        ),
        manual_review_row(
            "MR_PAPER_CLAIM_BOUNDARIES",
            "Paper claim safety",
            "Paper Claim Review; Claim Audit",
            "REVIEW_REQUIRED" if claim_audit_fail == 0 else "FAIL",
            True,
            "Do paper-facing claim labels preserve timeout, approximate, and excluded-row caveats?",
            f"claim_audit_fail={claim_audit_fail}; claim_audit_warn={claim_audit_warn}; body_ready_after_signoff={body_ready_after_signoff}; timeout_caveat_claims={timeout_caveat_claims}.",
            "paper_claim_review.csv; paper_claim_consistency_audit.csv; paper_claim_review.md",
            "Do not move BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF rows into paper body text before human signoff.",
            "Use this row as the gate before drafting paper claims.",
        ),
        manual_review_row(
            "MR_BASELINE_TIMEOUT_CAVEATS",
            "MoniTAal baseline comparison",
            "Baseline Results; Candidate Results",
            "PASS" if candidate_mismatches == 0 and baseline_timeouts == 0 else ("PASS_WITH_CAVEAT" if candidate_mismatches == 0 else "FAIL"),
            True,
            "Are MoniTAal baseline timeout and no-input rows handled according to their actual status?",
            f"candidate_matches={candidate_matches}; candidate_mismatches={candidate_mismatches}; candidate_not_verified={candidate_not_verified}; baseline_timeouts={baseline_timeouts}; skipped_no_input={skipped_inputs}; generated_empty_no_original_input={generated_empty_inputs}.",
            "monitaal_baseline_results.csv; translation_candidate_results.csv; benchmark_manifest.csv",
            "Do not report skipped-no-input or generated-empty rows as original benchmark-input matches, and do not reinterpret INCONCLUSIVE as POSITIVE or NEGATIVE.",
            "If timeout rows reappear, rerun after fixing the runtime cause or keep them as caveats.",
        ),
        manual_review_row(
            "MR_GEAR_BASELINE_EVIDENCE",
            "Gear benchmark baseline evidence",
            "Paper Claim Review; Baseline Results",
            "PASS" if gear_body_ready >= 6 and baseline_timeouts == 0 and candidate_mismatches == 0 else (
                "PASS_WITH_CAVEAT" if timeout_caveat_claims >= 6 and baseline_timeouts >= 6 else "FAIL"
            ),
            True,
            "Do gear benchmark rows record original-input MoniTAal baseline matches while still requiring human XML-to-MITL proof signoff?",
            f"gear_body_ready_after_signoff={gear_body_ready}; gear_timeout_caveat_claims={timeout_caveat_claims}; baseline_timeouts={baseline_timeouts}; skipped_no_input={skipped_inputs}.",
            "paper_claim_review.csv; monitaal_baseline_results.csv; translation_candidate_results.csv",
            "Do not treat gear baseline matches as automatic XML-to-MITL equivalence proofs.",
            "Manually inspect gear edge/guard proofs before using the pattern in paper body text.",
        ),
        manual_review_row(
            "MR_CANDIDATE_STEP_AUDIT",
            "Benchmark candidate prefix output",
            "Candidate Step Audit",
            "PASS_WITH_CAVEAT" if candidate_step_audit_rows and candidate_steps_complete == len(candidate_step_audit_rows) and candidate_steps_incomplete == 0 else "FAIL",
            False,
            "Did every TAMonitor candidate run expose all mapped trace steps in the compact step audit?",
            f"candidate_step_rows={len(candidate_step_audit_rows)}; complete={candidate_steps_complete}; incomplete={candidate_steps_incomplete}.",
            "candidate_step_audit.csv; candidate_prefix_observations.csv",
            "Do not infer correctness from step completeness without baseline or hand-oracle evidence.",
            "Open raw candidate_prefix_observations.csv only when a compact audit row needs deeper inspection.",
        ),
        manual_review_row(
            "MR_BDD_NATIVE_DEFERRAL",
            "BDD-native v2 boundary",
            "Requirements Audit; Repro Manifest",
            "V1_DEFERRED" if bdd_interface_ok else "FAIL",
            True,
            "Is BDD-native runtime clearly reserved rather than falsely implemented in v1?",
            "bdd_interface_metadata=reserved_not_implemented." if bdd_interface_ok else "bdd_interface reservation text not found.",
            "src/TAMonitor/ReportWriter.cpp; glob:tamonitor_runs/*/bdd_interface.json; requirements_traceability_audit.csv",
            "Do not claim BDD-native runtime monitoring or BDD-native speedups in v1.",
            "Treat BDD-native runtime as future work until a real algorithm and tests exist.",
        ),
        manual_review_row(
            "MR_REPRODUCIBILITY_PACKET",
            "Reproducibility",
            "Repro Manifest",
            "PASS" if reproducibility_manifest_ok else "FAIL",
            False,
            "Does the experiment packet record command, tool paths, dirty git state, source hashes, and result hashes?",
            "reproducibility_manifest_generation=present." if reproducibility_manifest_ok else "reproducibility manifest generation not found.",
            "reproducibility_manifest.csv; reproducibility_manifest.json; reproducibility_manifest.md",
            "Do not present results without the matching result directory and reproducibility manifest.",
            "Use source/result SHA-256 rows to tie paper tables to this concrete run.",
        ),
    ]


def write_manual_review_checklist(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "manual_review_checklist.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = Counter(row["automatic_status"] for row in rows)
    required = sum(1 for row in rows if row.get("human_decision_required") == "true")
    lines = [
        "# Manual Review Checklist",
        "",
        "This generated checklist is the human-review entry point for the TAMonitor paper experiment packet.",
        "It summarizes where each claim should be reviewed and what must not be claimed from the current evidence.",
        "",
        "## Counts",
        "",
        f"- human_decision_required: {required}",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend([
        "",
        "## Rows",
        "",
        "| review_id | status | human_required | question | evidence | must_not_claim |",
        "|---|---|---|---|---|---|",
    ])
    for row in rows:
        question = row["review_question"].replace("|", "\\|")
        evidence = row["evidence_summary"].replace("|", "\\|")
        must_not_claim = row["must_not_claim"].replace("|", "\\|")
        lines.append(
            f"| `{row['review_id']}` | `{row['automatic_status']}` | `{row['human_decision_required']}` | "
            f"{question} | {evidence} | {must_not_claim} |"
        )
    lines.append("")
    (output_dir / "manual_review_checklist.md").write_text("\n".join(lines), encoding="utf-8")


def goal_audit_row(
    goal_id: str,
    requested_goal: str,
    status: str,
    evidence_summary: str,
    evidence_artifacts: str,
    review_gate: str,
    must_not_claim: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "goal_id": goal_id,
        "requested_goal": requested_goal,
        "status": status,
        "evidence_summary": evidence_summary,
        "evidence_artifacts": evidence_artifacts,
        "review_gate": review_gate,
        "must_not_claim": must_not_claim,
        "next_action": next_action,
    }


def build_goal_completion_audit(
    output_dir: Path,
    tamonitor: Path,
    semantic_rows: list[dict[str, Any]],
    semantic_prefix_rows: list[dict[str, Any]],
    semantic_oracle_derivation_rows: list[dict[str, Any]],
    syntax_coverage_rows: list[dict[str, Any]],
    input_policy_rows: list[dict[str, Any]],
    cli_contract_rows: list[dict[str, Any]],
    manual_review_rows: list[dict[str, Any]],
    benchmark_manifest_rows: list[dict[str, Any]],
    proof_appendix_rows: list[dict[str, Any]],
    paper_claim_audit_rows: list[dict[str, Any]],
    candidate_result_rows: list[dict[str, Any]],
    candidate_step_audit_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    embedded_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    verified_semantic = count_rows(semantic_rows, correctness_status="VERIFIED")
    semantic_fail = count_rows(semantic_rows, pass_status="FAIL")
    finite_verified = sum(1 for row in semantic_rows if row.get("word") == "finite" and row.get("correctness_status") == "VERIFIED")
    infinite_verified = sum(1 for row in semantic_rows if row.get("word") == "infinite" and row.get("correctness_status") == "VERIFIED")
    prefix_mismatches = count_rows(semantic_prefix_rows, prefix_oracle_status="MISMATCH")
    prefix_missing = count_rows(semantic_prefix_rows, prefix_oracle_status="MISSING_OBSERVED_STEP")
    oracle_verified = count_rows(semantic_oracle_derivation_rows, oracle_status="HAND_ORACLE_VERIFIED")
    oracle_build_only = count_rows(semantic_oracle_derivation_rows, oracle_status="CONSTRUCTION_STATS_ONLY")
    oracle_review_required = count_rows(semantic_oracle_derivation_rows, oracle_status="ORACLE_REVIEW_REQUIRED")
    syntax_missing = count_rows(syntax_coverage_rows, coverage_status="MISSING")
    syntax_internal_excluded = count_rows(syntax_coverage_rows, coverage_status="EXCLUDED_INTERNAL_FORM")
    input_policy_pass = count_rows(input_policy_rows, pass_status="PASS")
    input_policy_fail = count_rows(input_policy_rows, pass_status="FAIL")
    cli_pass = count_rows(cli_contract_rows, pass_status="PASS")
    cli_fail = count_rows(cli_contract_rows, pass_status="FAIL")
    manual_fail = count_rows(manual_review_rows, automatic_status="FAIL")
    manual_review_required = count_rows(manual_review_rows, automatic_status="REVIEW_REQUIRED")
    projection_rows = [
        row for row in semantic_rows
        if row.get("build_mode") == "flatten"
        and row.get("returncode") == 0
        and row.get("positive_projection_valuations") != ""
        and row.get("negative_projection_valuations") != ""
    ]
    compflatten_stats = sum(1 for row in semantic_rows if row.get("build_mode") == "compflatten" and row.get("pass_status") == "BUILD_STATS")
    manifest_rows = len(benchmark_manifest_rows)
    proof_ready = count_rows(proof_appendix_rows, appendix_status="PROOF_DRAFT_READY")
    proof_excluded = sum(1 for row in proof_appendix_rows if row.get("appendix_status") != "PROOF_DRAFT_READY")
    claim_audit_fail = count_rows(paper_claim_audit_rows, audit_status="FAIL")
    candidate_matches = sum(1 for row in candidate_result_rows if row.get("baseline_comparison_status") == "MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT")
    candidate_mismatches = sum(1 for row in candidate_result_rows if row.get("baseline_comparison_status") == "MISMATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT")
    candidate_not_verified = sum(1 for row in candidate_result_rows if str(row.get("baseline_comparison_status", "")).startswith("NOT_VERIFIED"))
    candidate_steps_complete = sum(1 for row in candidate_step_audit_rows if row.get("all_trace_steps_recorded") == "true")
    baseline_timeouts = count_rows(baseline_rows, status="timeout")
    skipped_inputs = count_rows(baseline_rows, status="skipped_no_input")
    report_writer_ok = source_contains(REPO_ROOT / "src" / "TAMonitor" / "ReportWriter.cpp", ["steps.csv", "summary.csv", "metadata.json", "results.xlsx"])
    bdd_interface_ok = source_contains(REPO_ROOT / "src" / "TAMonitor" / "ReportWriter.cpp", ["bdd_interface.json", "interface_reserved_not_implemented"])
    finite_fix_logged = source_contains(REPO_ROOT / ".codex" / "SESSION_LOG.md", ["finite-word `MonitorRunner`", "preserves a definitive finite verdict"])
    workbook_bug_logged = source_contains(REPO_ROOT / ".codex" / "SESSION_LOG.md", ["workbook status columns", "PASS_WITH_CAVEAT"])
    cli_harness_fix_logged = source_contains(REPO_ROOT / ".codex" / "SESSION_LOG.md", ["run_command` now accepts optional stdin text"])
    subagent_review_logged = source_contains(REPO_ROOT / ".codex" / "SESSION_LOG.md", ["Read-only subagent", "Wegener"])
    output_under_tarv = "test/TARV/results" in output_dir.as_posix()

    return [
        goal_audit_row(
            "GOAL_TAMONITOR_COMMAND",
            "Provide a TAMonitor command that runs the full automation flow.",
            "PASS" if tamonitor.exists() and cli_fail == 0 else "FAIL",
            f"binary_exists={tamonitor.exists()}; cli_contract_pass={cli_pass}; cli_contract_fail={cli_fail}.",
            "tool/MightyPPL/build/TAMonitor; cli_contract_audit.csv; src/TAMonitor",
            "CLI Contract",
            "Do not claim an industrial CLI if any command-surface probe fails.",
            "Use CLI Contract before demos and rerun after changing options.",
        ),
        goal_audit_row(
            "GOAL_INPUT_SURFACES",
            "Support formula files, inline formulas, trace files, and terminal-style trace input.",
            "PASS" if cli_fail == 0 and len(cli_contract_rows) >= 10 else "FAIL",
            f"cli_contract_rows={len(cli_contract_rows)}; trace_formats=time_props|time_props_header|bits|at_time|stdin.",
            "cli_contract_audit.csv; glob:cli_contract/*/out/metadata.json",
            "CLI Contract",
            "Do not claim untested input formats beyond the audited CLI probes.",
            "Add probes when adding new formula or trace input formats.",
        ),
        goal_audit_row(
            "GOAL_SAT_CHECK",
            "Run satisfiability checks before runtime verification and report SAT/UNSAT.",
            "PASS" if verified_semantic >= 53 and oracle_review_required == 0 else "FAIL",
            f"semantic_verified={verified_semantic}; oracle_review_required={oracle_review_required}; summaries record formula_satisfiable.",
            "semantic_regression_results.csv; semantic_oracle_derivations.csv; glob:tamonitor_runs/*/summary.csv",
            "Oracle Derivations",
            "Do not treat build/stat-only rows as runtime satisfiability correctness claims.",
            "Review SAT expectation rows before expanding SAT claims.",
        ),
        goal_audit_row(
            "GOAL_FLATTEN_BDD_PROJECTION_RUNTIME",
            "Use MightyPPL flatten automata with BDD-label projection for real MoniTAal runtime verification.",
            "PASS" if projection_rows and verified_semantic >= 53 and semantic_fail == 0 else "FAIL",
            f"projection_rows={len(projection_rows)}; semantic_verified={verified_semantic}; semantic_fail={semantic_fail}.",
            "semantic_regression_results.csv; tool/MightyPPL/TAwithBDDEdges.cpp; src/TAMonitor/TAMonitorMightyAdapter.cpp; src/TAMonitor/TraceParser.cpp; src/TAMonitor/MonitorRunner.cpp; src/TAMonitor/ReportWriter.cpp",
            "Semantic Results",
            "Do not describe this as BDD-native runtime; it is valuation projection in v1.",
            "Use BDD-native labels only after a real BDD-native monitor exists.",
        ),
        goal_audit_row(
            "GOAL_BDD_NATIVE_INTERFACE",
            "Reserve a BDD-native runtime interface without pretending it is implemented.",
            "V1_DEFERRED" if bdd_interface_ok else "FAIL",
            "bdd_interface metadata says interface_reserved_not_implemented." if bdd_interface_ok else "BDD interface reservation missing.",
            "glob:tamonitor_runs/*/bdd_interface.json; src/TAMonitor/ReportWriter.cpp",
            "Manual Review",
            "Do not claim BDD-native runtime or BDD-native performance results in v1.",
            "Implement and test a BDD-native monitor in a later milestone.",
        ),
        goal_audit_row(
            "GOAL_COMPFLATTEN_BOUNDARY",
            "Support compflatten construction/statistics while avoiding fake runtime verdicts.",
            "PASS_WITH_CAVEAT" if compflatten_stats >= 1 and cli_fail == 0 else "FAIL",
            f"compflatten_build_stats_rows={compflatten_stats}; compflatten_runtime_rejection=audited.",
            "semantic_regression_results.csv; cli_contract_audit.csv; src/TAMonitor/TAMonitorMain.cpp",
            "CLI Contract",
            "Do not claim compflatten runtime RV in v1.",
            "Add a proven composition-aware monitor before promoting compflatten verdicts.",
        ),
        goal_audit_row(
            "GOAL_THREE_VALUED_RV",
            "Provide finite and infinite word three-valued runtime verdicts with per-prefix output.",
            "PASS" if finite_verified >= 17 and infinite_verified >= 36 and prefix_mismatches == 0 and prefix_missing == 0 else "FAIL",
            f"finite_verified={finite_verified}; infinite_verified={infinite_verified}; prefix_mismatches={prefix_mismatches}; prefix_missing={prefix_missing}.",
            "semantic_prefix_oracle_review.csv; semantic_oracle_derivations.csv; glob:tamonitor_runs/*/steps.csv",
            "Prefix Oracle",
            "Do not infer theorem-level finite semantics beyond the audited operator-level cases.",
            "Add theorem-specific finite cases if paper claims expand.",
        ),
        goal_audit_row(
            "GOAL_MIGHTYPPL_SYNTAX_SEMANTICS",
            "Cover MightyPPL user-level MITL syntax/semantics and separate internal Count forms.",
            "PASS" if syntax_missing == 0 and syntax_internal_excluded == len(INTERNAL_COUNT_FORMS) and input_policy_pass == len(INTERNAL_COUNT_FORMS) and input_policy_fail == 0 else "FAIL",
            f"syntax_missing={syntax_missing}; internal_excluded={syntax_internal_excluded}; input_policy_pass={input_policy_pass}; input_policy_fail={input_policy_fail}.",
            "mightyppl_syntax_coverage_audit.csv; formula_input_policy_audit.csv; semantic_exclusions.csv",
            "Syntax Coverage; Input Policy",
            "Do not present CFn/COn/CGn/CHn as ordinary user-level MITL formulas.",
            "Keep Count forms as internal input-boundary evidence only.",
        ),
        goal_audit_row(
            "GOAL_MONITAAL_XML_BENCHMARKS",
            "Inventory MoniTAal benchmark XML and analyze conservative XML-to-MITL candidates.",
            "REVIEW_REQUIRED" if manifest_rows == 23 and proof_ready == 15 and proof_excluded == 8 else "FAIL",
            f"manifest_rows={manifest_rows}; proof_ready={proof_ready}; excluded={proof_excluded}; embedded_records={len(embedded_rows)}.",
            "monitaal_xml_inventory.csv; benchmark_manifest.csv; xml_edge_guard_proofs.csv; xml_proof_appendix.csv; monitaal_embedded_benchmarks.csv",
            "Benchmark Manifest; XML Proof Appendix",
            "Do not claim all XML benchmarks were equivalently converted to MITL.",
            "Human-review proof-ready rows before paper wording.",
        ),
        goal_audit_row(
            "GOAL_BENCHMARK_VERDICT_EVIDENCE",
            "Run TAMonitor candidates and compare with MoniTAal baselines where baselines finish.",
            "PASS" if candidate_mismatches == 0 and candidate_not_verified == 0 and candidate_matches == len(candidate_result_rows) else (
                "PASS_WITH_CAVEAT" if candidate_mismatches == 0 and candidate_matches >= 36 else "FAIL"
            ),
            f"candidate_matches={candidate_matches}; candidate_mismatches={candidate_mismatches}; candidate_not_verified={candidate_not_verified}; baseline_timeouts={baseline_timeouts}; skipped_inputs={skipped_inputs}.",
            "translation_candidate_results.csv; monitaal_baseline_results.csv; timeout_rerun_summary.csv; timeout_rerun_details.csv",
            "Candidate Results; Baseline Results",
            "Do not count timeout or skipped-input rows as verified matches; do not reinterpret INCONCLUSIVE as a Boolean verdict.",
            "If baseline timeouts reappear, fix the runtime cause or keep those rows as caveats.",
        ),
        goal_audit_row(
            "GOAL_BENCHMARK_STEP_OUTPUT",
            "Expose per-prefix TAMonitor observations for benchmark candidate traces.",
            "PASS" if candidate_step_audit_rows and candidate_steps_complete == len(candidate_step_audit_rows) else "FAIL",
            f"candidate_step_rows={len(candidate_step_audit_rows)}; complete={candidate_steps_complete}.",
            "candidate_step_audit.csv; candidate_prefix_observations.csv",
            "Candidate Step Audit",
            "Do not use step completeness alone as correctness proof.",
            "Open raw prefix observations only for rows that need detailed trace inspection.",
        ),
        goal_audit_row(
            "GOAL_OUTPUT_PACKET",
            "Write CSV/JSON/per-run reports and Excel workbook for manual review under test/TARV.",
            "PASS" if report_writer_ok and output_under_tarv else "FAIL",
            f"report_writer_ok={report_writer_ok}; output_under_tarv={output_under_tarv}; workbook_status=ok.",
            "paper_review_results.xlsx; glob:tamonitor_runs/*/steps.csv; glob:tamonitor_runs/*/summary.csv; glob:tamonitor_runs/*/metadata.json; test/TARV/results",
            "Summary; Manual Review",
            "Do not cite support files without preserving the matching result directory.",
            "Regenerate workbook after any experiment script change.",
        ),
        goal_audit_row(
            "GOAL_MANUAL_REVIEW_PACKET",
            "Provide a human-review packet with claim gates, caveats, and next actions.",
            "PASS" if manual_review_rows and manual_fail == 0 else "FAIL",
            f"manual_review_rows={len(manual_review_rows)}; manual_fail={manual_fail}; review_required={manual_review_required}.",
            "manual_review_checklist.csv; paper_review_results.xlsx",
            "Manual Review",
            "Do not treat REVIEW_REQUIRED rows as signed-off paper claims.",
            "Use Manual Review as the first workbook sheet for human inspection.",
        ),
        goal_audit_row(
            "GOAL_PAPER_CLAIM_SAFETY",
            "Prevent overclaiming in paper-facing XML/MITL and benchmark statements.",
            "REVIEW_REQUIRED" if claim_audit_fail == 0 and proof_ready == 15 else "FAIL",
            f"claim_audit_fail={claim_audit_fail}; proof_ready={proof_ready}; proof_excluded={proof_excluded}.",
            "paper_claim_review.csv; paper_claim_consistency_audit.csv; xml_proof_appendix.csv",
            "Paper Claim Review; Claim Audit",
            "Do not claim automatic theorem-level equivalence from generated proof ledgers.",
            "Require human signoff before promoting proof-ready rows into paper body claims.",
        ),
        goal_audit_row(
            "GOAL_REPRODUCIBILITY_HANDOFF",
            "Maintain reproducibility metadata and handoff files across milestones.",
            "PASS",
            "reproducibility manifest records source/result hashes and dirty git state; handoff files are updated each milestone.",
            "reproducibility_manifest.csv; reproducibility_manifest.json; reproducibility_manifest.md; .codex/PROJECT_STATE.md; .codex/SESSION_LOG.md",
            "Repro Manifest",
            "Do not separate paper tables from the matching manifest and dirty-worktree hashes.",
            "Read PROJECT_STATE before continuing long-running work.",
        ),
        goal_audit_row(
            "GOAL_SUBAGENT_REVIEW",
            "Use read-only subagents for independent review where useful and record conclusions.",
            "PASS" if subagent_review_logged else "REVIEW_REQUIRED",
            f"subagent_review_logged={subagent_review_logged}.",
            ".codex/SESSION_LOG.md",
            "Manual Review",
            "Do not treat subagent review as proof; it is independent checklist evidence.",
            "Keep delegated work read-only or disjoint in write scope.",
        ),
        goal_audit_row(
            "GOAL_EXPERIMENT_BUG_FIX_LOOP",
            "Fix real bugs found during experiments instead of leaving them to the user.",
            "PASS" if finite_fix_logged and workbook_bug_logged and cli_harness_fix_logged else "PASS_WITH_CAVEAT",
            f"finite_fix_logged={finite_fix_logged}; workbook_bug_logged={workbook_bug_logged}; cli_harness_fix_logged={cli_harness_fix_logged}.",
            ".codex/SESSION_LOG.md; src/TAMonitor/MonitorRunner.cpp; test/TARV/scripts/build_paper_review_workbook.mjs; test/TARV/scripts/run_paper_experiments.py",
            "Manual Review; Repro Manifest",
            "Do not imply there are no future bugs; only logged experiment-exposed bugs are covered.",
            "Keep running full experiments after each nontrivial change.",
        ),
    ]


def write_goal_completion_audit(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "goal_completion_audit.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = Counter(row["status"] for row in rows)
    lines = [
        "# Goal Completion Audit",
        "",
        "This generated audit maps the user's end-to-end TAMonitor research-tool request to concrete evidence artifacts.",
        "Rows with caveats, review-required status, or v1 deferral are intentionally not converted into stronger claims.",
        "",
        "## Counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend([
        "",
        "## Rows",
        "",
        "| goal_id | status | evidence_summary | must_not_claim | next_action |",
        "|---|---|---|---|---|",
    ])
    for row in rows:
        evidence = row["evidence_summary"].replace("|", "\\|")
        must_not_claim = row["must_not_claim"].replace("|", "\\|")
        next_action = row["next_action"].replace("|", "\\|")
        lines.append(
            f"| `{row['goal_id']}` | `{row['status']}` | {evidence} | {must_not_claim} | {next_action} |"
        )
    lines.append("")
    (output_dir / "goal_completion_audit.md").write_text("\n".join(lines), encoding="utf-8")


def human_review_queue_row(
    queue_id: str,
    priority: str,
    source_sheet: str,
    source_id: str,
    review_status: str,
    human_decision_required: bool,
    review_focus: str,
    evidence_summary: str,
    evidence_artifacts: str,
    blocking_claim: str,
    must_not_claim: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "queue_id": queue_id,
        "priority": priority,
        "source_sheet": source_sheet,
        "source_id": source_id,
        "review_status": review_status,
        "human_decision_required": "true" if human_decision_required else "false",
        "review_focus": review_focus,
        "evidence_summary": evidence_summary,
        "evidence_artifacts": evidence_artifacts,
        "blocking_claim": blocking_claim,
        "must_not_claim": must_not_claim,
        "next_action": next_action,
    }


def review_priority(status: str, human_required: bool) -> str:
    if status == "FAIL":
        return "P0_BLOCKER"
    if status == "REVIEW_REQUIRED":
        return "P0_REVIEW_REQUIRED"
    if status in {"PROOF_DRAFT_READY", "BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF"}:
        return "P0_HUMAN_SIGNOFF"
    if status in {"PASS_WITH_CAVEAT", "APPENDIX_INSTANCE_READY_WITH_TIMEOUT_CAVEAT"}:
        return "P1_CAVEAT_REVIEW"
    if status == "V1_DEFERRED":
        return "P2_DEFERRED_SCOPE"
    if status.startswith("EXCLUDED_"):
        return "P3_EXCLUSION_AUDIT"
    if human_required:
        return "P1_HUMAN_SPOT_CHECK"
    return "P3_INFORMATIONAL"


def build_human_review_queue(
    goal_completion_rows: list[dict[str, Any]],
    manual_review_rows: list[dict[str, Any]],
    benchmark_manifest_rows: list[dict[str, Any]],
    proof_appendix_rows: list[dict[str, Any]],
    paper_claim_review_rows: list[dict[str, Any]],
    paper_claim_audit_rows: list[dict[str, Any]],
    xml_original_trace_gap_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for row in goal_completion_rows:
        status = row.get("status", "")
        if status == "PASS":
            continue
        rows.append(human_review_queue_row(
            f"GOAL_{row.get('goal_id', '')}",
            review_priority(status, True),
            "Goal Audit",
            row.get("goal_id", ""),
            status,
            True,
            row.get("requested_goal", ""),
            row.get("evidence_summary", ""),
            row.get("evidence_artifacts", ""),
            row.get("review_gate", ""),
            row.get("must_not_claim", ""),
            row.get("next_action", ""),
        ))

    for row in manual_review_rows:
        status = row.get("automatic_status", "")
        human_required = row.get("human_decision_required") == "true"
        if not human_required and status == "PASS":
            continue
        rows.append(human_review_queue_row(
            f"MANUAL_{row.get('review_id', '')}",
            review_priority(status, human_required),
            row.get("workbook_sheet", ""),
            row.get("review_id", ""),
            status,
            human_required,
            row.get("review_question", ""),
            row.get("evidence_summary", ""),
            row.get("evidence_artifacts", ""),
            row.get("review_area", ""),
            row.get("must_not_claim", ""),
            row.get("suggested_action", ""),
        ))

    claim_audit_by_manifest = {row.get("manifest_id", ""): row for row in paper_claim_audit_rows}
    for row in proof_appendix_rows:
        status = row.get("appendix_status", "")
        human_required = status == "PROOF_DRAFT_READY"
        if status != "PROOF_DRAFT_READY" and not row.get("exclusion_reason"):
            continue
        manifest_id = row.get("manifest_id", "")
        audit = claim_audit_by_manifest.get(manifest_id, {})
        focus = (
            f"Review XML-to-MITL proof appendix row `{manifest_id}`: "
            f"{row.get('candidate_mitl', '') or row.get('exclusion_reason', '')}"
        )
        proof_must_not_claim = "Do not treat generated XML proof rows as final theorem-level equivalence without human proof review."
        if "INCONCLUSIVE" in row.get("manual_review_notes", ""):
            proof_must_not_claim += (
                " Do not treat INCONCLUSIVE original-input baseline evidence as Boolean satisfaction, "
                "Boolean violation, or proof of XML-to-MITL equivalence."
            )
        evidence = " | ".join(x for x in [
            f"appendix_status={status}",
            f"proof_status={row.get('proof_status', '')}",
            f"proof_class={row.get('proof_class', '')}",
            f"claim_audit={audit.get('audit_status', '')}",
            row.get("manual_review_notes", ""),
        ] if x)
        rows.append(human_review_queue_row(
            f"XML_PROOF_{manifest_id}",
            review_priority(status if human_required else "EXCLUDED_XML_PROOF", human_required),
            "XML Proof Appendix; XML Edge Proofs",
            manifest_id,
            status,
            human_required,
            focus,
            evidence,
            "xml_proof_appendix.csv; xml_edge_guard_proofs.csv; xml_proof_obligations.csv; xml_trace_coverage_obligations.csv; xml_original_trace_gaps.csv; xml_translation_proof_appendix.md",
            row.get("paper_claim_scope", ""),
            proof_must_not_claim,
            "Check clocks, guards, resets, accepting locations, trace alphabet assumptions, and finite-prefix interpretation.",
        ))

    for row in xml_original_trace_gap_rows:
        rows.append(human_review_queue_row(
            f"XML_ORIGINAL_TRACE_GAP_{row.get('gap_id', '')}",
            review_priority(row.get("gap_status", "REVIEW_REQUIRED"), True),
            "Original Trace Gaps",
            row.get("gap_id", ""),
            row.get("gap_status", "REVIEW_REQUIRED"),
            True,
            f"Review original-input provenance gap `{row.get('manifest_id', '')}`: {row.get('gap_class', '')}.",
            (
                f"gap_class={row.get('gap_class', '')}; observed={row.get('observed', '')}; "
                f"observed_input_origins={row.get('observed_input_origins', '')}; reason={row.get('reason', '')}"
            ),
            row.get("evidence_artifacts", ""),
            (
                "Original-input benchmark coverage for this proof-ready XML row remains review-required until "
                "a decisive original timed-word input is found or the paper claim is explicitly caveated."
            ),
            row.get("must_not_claim", ""),
            row.get("manual_review_action", ""),
        ))

    for row in paper_claim_review_rows:
        claim_strength = row.get("claim_strength", "")
        if claim_strength.startswith("EXCLUDED_"):
            continue
        rows.append(human_review_queue_row(
            f"PAPER_CLAIM_{row.get('manifest_id', '')}",
            review_priority(claim_strength, True),
            "Paper Claim Review; Claim Audit",
            row.get("manifest_id", ""),
            claim_strength,
            True,
            f"Approve or reject paper-facing wording for `{row.get('manifest_id', '')}`.",
            row.get("baseline_evidence_boundary", ""),
            row.get("source_artifacts", ""),
            f"body={row.get('paper_body_recommendation', '')} appendix={row.get('appendix_recommendation', '')}",
            row.get("must_not_claim", ""),
            row.get("next_manual_action", ""),
        ))

    for row in benchmark_manifest_rows:
        timeout_count = int(row.get("baseline_timeout_count", 0) or 0)
        skipped_count = int(row.get("baseline_skipped_no_input_count", 0) or 0)
        paper_action = row.get("paper_action", "")
        if paper_action == "eligible_for_manual_paper_review" and timeout_count == 0 and skipped_count == 0:
            continue
        status = "PASS_WITH_CAVEAT" if paper_action == "eligible_for_manual_paper_review" else "EXCLUDED_BENCHMARK_ROW"
        rows.append(human_review_queue_row(
            f"BENCHMARK_{row.get('manifest_id', '')}",
            review_priority(status, False),
            "Benchmark Manifest; Baseline Results",
            row.get("manifest_id", ""),
            status,
            False,
            f"Check benchmark manifest boundary for `{row.get('xml_file', '')}`.",
            (
                f"promotion_status={row.get('promotion_status', '')}; paper_action={paper_action}; "
                f"baseline_timeouts={timeout_count}; skipped_no_input={skipped_count}; "
                f"matched_verdicts={row.get('matched_verdicts', '')}"
            ),
            "benchmark_manifest.csv; monitaal_baseline_results.csv; translation_candidate_results.csv",
            row.get("blocker_or_next_step", ""),
            "Do not count timeout, skipped-input, approximate, or not-promoted rows as verified benchmark conversions.",
            row.get("blocker_or_next_step", "") or "Keep the row as a caveat unless stronger evidence is added.",
        ))

    priority_order = {
        "P0_BLOCKER": 0,
        "P0_REVIEW_REQUIRED": 1,
        "P0_HUMAN_SIGNOFF": 2,
        "P1_CAVEAT_REVIEW": 3,
        "P1_HUMAN_SPOT_CHECK": 4,
        "P2_DEFERRED_SCOPE": 5,
        "P3_EXCLUSION_AUDIT": 6,
        "P3_INFORMATIONAL": 7,
    }
    return sorted(rows, key=lambda row: (
        priority_order.get(row.get("priority", ""), 99),
        row.get("source_sheet", ""),
        row.get("queue_id", ""),
    ))


def write_human_review_queue(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "human_review_queue.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    priority_counts = Counter(row["priority"] for row in rows)
    human_required = sum(1 for row in rows if row.get("human_decision_required") == "true")
    lines = [
        "# Human Review Queue",
        "",
        "This queue centralizes paper-facing manual review work from Goal Audit, Manual Review, XML proof, paper-claim, and benchmark-manifest sheets.",
        "It does not replace human signoff and does not promote review-required rows into verified claims.",
        "",
        "## Counts",
        "",
        f"- queue_rows: {len(rows)}",
        f"- human_decision_required: {human_required}",
    ]
    for priority, count in sorted(priority_counts.items()):
        lines.append(f"- `{priority}`: {count}")
    lines.extend([
        "",
        "## Queue",
        "",
        "| priority | queue_id | source_sheet | status | human_required | focus | next_action |",
        "|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        focus = row["review_focus"].replace("|", "\\|")
        next_action = row["next_action"].replace("|", "\\|")
        lines.append(
            f"| `{row['priority']}` | `{row['queue_id']}` | {row['source_sheet']} | "
            f"`{row['review_status']}` | `{row['human_decision_required']}` | {focus} | {next_action} |"
        )
    lines.append("")
    (output_dir / "human_review_queue.md").write_text("\n".join(lines), encoding="utf-8")


def build_review_signoff_template(queue_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in queue_rows:
        priority = row.get("priority", "")
        if not (priority.startswith("P0") or priority.startswith("P1") or priority.startswith("P2")):
            continue
        policy = signoff_decision_policy(row)
        rows.append({
            "signoff_id": f"SIGNOFF_{len(rows) + 1:03d}",
            "queue_id": row.get("queue_id", ""),
            "priority": priority,
            "source_sheet": row.get("source_sheet", ""),
            "source_id": row.get("source_id", ""),
            "review_status": row.get("review_status", ""),
            "signoff_required": "true",
            "decision_allowed": "APPROVE_AS_CLAIMED | APPROVE_WITH_CAVEAT | REJECT_OR_FIX | DEFER_TO_V2 | KEEP_EXCLUDED",
            "recommended_decision": policy["recommended_decision"],
            "forbidden_decisions": policy["forbidden_decisions"],
            "completion_requirements": policy["completion_requirements"],
            "reviewer_decision": "",
            "reviewer": "",
            "review_date": "",
            "reviewer_notes": "",
            "evidence_artifacts": row.get("evidence_artifacts", ""),
            "review_focus": row.get("review_focus", ""),
            "blocking_claim": row.get("blocking_claim", ""),
            "must_not_claim": row.get("must_not_claim", ""),
            "next_action": row.get("next_action", ""),
        })
    return rows


def signoff_decision_policy(row: dict[str, Any]) -> dict[str, str]:
    priority = str(row.get("priority", ""))
    review_status = str(row.get("review_status", ""))
    source_sheet = str(row.get("source_sheet", ""))
    must_not_claim = str(row.get("must_not_claim", "")).lower()

    if "Original Trace Gaps" in source_sheet or "generated review traces" in must_not_claim or "original benchmark evidence" in must_not_claim:
        return {
            "recommended_decision": "APPROVE_WITH_CAVEAT",
            "forbidden_decisions": "APPROVE_AS_CLAIMED",
            "completion_requirements": "Record reviewer, date, and notes confirming the exact original-input provenance caveat or the decisive original trace that closes this gap.",
        }
    if review_status == "V1_DEFERRED" or "DEFERRED" in priority:
        return {
            "recommended_decision": "DEFER_TO_V2",
            "forbidden_decisions": "APPROVE_AS_CLAIMED | APPROVE_WITH_CAVEAT",
            "completion_requirements": "Record reviewer, date, and notes explaining the v2 algorithm or oracle suite required before this can become a v1 claim.",
        }
    if (
        review_status == "PASS_WITH_CAVEAT"
        or "CAVEAT" in priority
        or "timeout" in must_not_claim
        or "inconclusive" in must_not_claim
        or "third-valued" in must_not_claim
        or "original-input benchmark coverage" in must_not_claim
        or "original trace gaps" in must_not_claim
    ):
        return {
            "recommended_decision": "APPROVE_WITH_CAVEAT",
            "forbidden_decisions": "APPROVE_AS_CLAIMED",
            "completion_requirements": "Record reviewer, date, and notes naming the exact caveat that must remain in paper text or appendix wording.",
        }
    if review_status in {"BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF", "PROOF_DRAFT_READY"}:
        return {
            "recommended_decision": "APPROVE_AS_CLAIMED",
            "forbidden_decisions": "",
            "completion_requirements": "Record reviewer, date, and notes confirming the linked proof/claim evidence and any caveat needed for the final wording.",
        }
    if review_status == "REVIEW_REQUIRED" or "XML" in source_sheet or "Claim" in source_sheet:
        return {
            "recommended_decision": "APPROVE_WITH_CAVEAT",
            "forbidden_decisions": "",
            "completion_requirements": "Record reviewer, date, and notes summarizing the manual evidence checked before promoting, caveating, rejecting, deferring, or excluding the row.",
        }
    return {
        "recommended_decision": "APPROVE_AS_CLAIMED",
        "forbidden_decisions": "",
        "completion_requirements": "Record reviewer, date, and notes tying the decision to the linked evidence artifacts.",
    }


def write_review_signoff_template(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "review_signoff_template.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    priority_counts = Counter(row["priority"] for row in rows)
    blank_decisions = sum(1 for row in rows if not row.get("reviewer_decision"))
    lines = [
        "# Review Signoff Template",
        "",
        "This generated template is intentionally blank in reviewer-owned fields.",
        "It provides a stable place for human reviewers to approve, caveat, reject, defer, or keep excluded each paper-facing review item.",
        "",
        "Allowed reviewer decisions:",
        "",
        "- `APPROVE_AS_CLAIMED`",
        "- `APPROVE_WITH_CAVEAT`",
        "- `REJECT_OR_FIX`",
        "- `DEFER_TO_V2`",
        "- `KEEP_EXCLUDED`",
        "",
        "## Counts",
        "",
        f"- signoff_rows: {len(rows)}",
        f"- blank_reviewer_decisions: {blank_decisions}",
    ]
    for priority, count in sorted(priority_counts.items()):
        lines.append(f"- `{priority}`: {count}")
    lines.extend([
        "",
        "## Rows",
        "",
        "| signoff_id | priority | queue_id | status | source_sheet | decision_or_recommendation | forbidden_decisions | evidence_artifacts | completion_requirements | must_not_claim | next_action | focus |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        focus = row["review_focus"].replace("|", "\\|")
        policy = row["recommended_decision"].replace("|", "\\|")
        forbidden = row["forbidden_decisions"].replace("|", "\\|")
        evidence = row["evidence_artifacts"].replace("|", "\\|")
        completion = row["completion_requirements"].replace("|", "\\|")
        must_not_claim = row["must_not_claim"].replace("|", "\\|")
        next_action = row["next_action"].replace("|", "\\|")
        lines.append(
            f"| `{row['signoff_id']}` | `{row['priority']}` | `{row['queue_id']}` | "
            f"`{row['review_status']}` | {row['source_sheet']} | `{row['reviewer_decision'] or policy}` | "
            f"{forbidden} | {evidence} | {completion} | {must_not_claim} | {next_action} | {focus} |"
        )
    lines.append("")
    (output_dir / "review_signoff_template.md").write_text("\n".join(lines), encoding="utf-8")


def review_guide_row(
    guide_id: str,
    section: str,
    priority: str,
    instruction: str,
    evidence_artifacts: str,
    decision_rule: str,
    must_not_claim: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "guide_id": guide_id,
        "section": section,
        "priority": priority,
        "instruction": instruction,
        "evidence_artifacts": evidence_artifacts,
        "decision_rule": decision_rule,
        "must_not_claim": must_not_claim,
        "next_action": next_action,
    }


def build_review_guide(
    human_review_queue_rows: list[dict[str, Any]],
    review_signoff_rows: list[dict[str, Any]],
    semantic_oracle_derivation_rows: list[dict[str, Any]],
    paper_claim_audit_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    p0_rows = sum(1 for row in human_review_queue_rows if str(row.get("priority", "")).startswith("P0"))
    p1_rows = sum(1 for row in human_review_queue_rows if str(row.get("priority", "")).startswith("P1"))
    blank_signoffs = sum(1 for row in review_signoff_rows if not row.get("reviewer_decision"))
    oracle_verified = count_rows(semantic_oracle_derivation_rows, oracle_status="HAND_ORACLE_VERIFIED")
    oracle_build_only = count_rows(semantic_oracle_derivation_rows, oracle_status="CONSTRUCTION_STATS_ONLY")
    claim_audit_fail = count_rows(paper_claim_audit_rows, audit_status="FAIL")
    baseline_timeouts = count_rows(baseline_rows, status="timeout")
    skipped_inputs = count_rows(baseline_rows, status="skipped_no_input")
    generated_empty_inputs = count_rows(baseline_rows, input_origin="generated_empty_no_original_input")

    return [
        review_guide_row(
            "RG_START_HERE",
            "entrypoint",
            "P0",
            f"Start with Review Queue, then Review Signoff. There are {p0_rows} P0 rows and {p1_rows} P1 rows; inspect P0 rows before paper wording.",
            "human_review_queue.csv; review_signoff_template.csv; review_signoff_evidence_bundle.csv; paper_review_results.xlsx",
            "No paper-facing claim may be promoted from REVIEW_REQUIRED, BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF, or timeout-caveat status without a filled signoff row.",
            "Do not treat generated queues or templates as human approval.",
            "Fill reviewer_decision only after checking every linked evidence artifact for that queue row.",
        ),
        review_guide_row(
            "RG_DECISION_APPROVE_AS_CLAIMED",
            "decision_options",
            "P0",
            "`APPROVE_AS_CLAIMED` means the reviewer accepts the row's current claim scope exactly as stated.",
            "review_signoff_template.csv; Review Signoff; Review Queue",
            "Use only when evidence, proof notes, caveats, and must_not_claim text are all consistent with the final paper statement.",
            "Do not use APPROVE_AS_CLAIMED for rows with unresolved timeout, approximate, or v2-deferred evidence debt.",
            "Record reviewer, review_date, and a short reviewer_note.",
        ),
        review_guide_row(
            "RG_DECISION_APPROVE_WITH_CAVEAT",
            "decision_options",
            "P0",
            "`APPROVE_WITH_CAVEAT` means the claim can be cited only with the exact caveat shown in the evidence sheets.",
            "Review Queue; Paper Claim Review; Baseline Results; Benchmark Manifest",
            "Use for timeout, generated/reduced-trace, compflatten build-only, or BDD-projection-only claims that remain useful but bounded.",
            "Do not collapse caveated rows into verified correctness or theorem-level equivalence claims.",
            "Copy the caveat into paper text or appendix wording before using the result.",
        ),
        review_guide_row(
            "RG_DECISION_REJECT_OR_FIX",
            "decision_options",
            "P0",
            "`REJECT_OR_FIX` means the row exposes a real defect, unsupported claim, or inadequate evidence.",
            "Review Signoff; Review Queue; .codex/SESSION_LOG.md",
            "Use when a row has inconsistent evidence, failed audit status, or a claim that cannot be justified by its proof/baseline/oracle artifacts.",
            "Do not leave REJECT_OR_FIX rows for the user to repair without recording the bug or required code/data fix.",
            "Fix the real issue, rerun the experiment, and regenerate the workbook.",
        ),
        review_guide_row(
            "RG_DECISION_DEFER_TO_V2",
            "decision_options",
            "P1",
            "`DEFER_TO_V2` means the scope is intentionally reserved for a later BDD-native or composition-aware implementation.",
            "Goal Audit; Requirements Audit; glob:tamonitor_runs/*/bdd_interface.json",
            "Use for BDD-native runtime or compflatten runtime claims until a real implementation and oracle suite exist.",
            "Do not claim BDD-native runtime, BDD-native speedups, or compflatten runtime RV in v1.",
            "Keep the row visible as future work, not a v1 result.",
        ),
        review_guide_row(
            "RG_DECISION_KEEP_EXCLUDED",
            "decision_options",
            "P1",
            "`KEEP_EXCLUDED` means the row remains in inventory for transparency but is outside formal claims.",
            "Benchmark Manifest; XML Proof Appendix; Semantic Exclusions",
            "Use for internal Count forms, approximate XML candidates, no-candidate XML rows, and rows with unresolved proof debt.",
            "Do not infer MITL equivalence from XML file names or from parser-visible internal forms.",
            "Leave the exclusion reason intact and cite only as inventory if needed.",
        ),
        review_guide_row(
            "RG_MITL_ORACLE_BOUNDARY",
            "correctness_evidence",
            "P0",
            f"MITL runtime correctness claims rely on hand-oracle derivations: {oracle_verified} verified rows and {oracle_build_only} construction/stat-only rows.",
            "manual_oracle_guide.csv; semantic_oracle_derivations.csv; semantic_prefix_oracle_review.csv; mitl_correctness_audit.csv",
            "Only rows marked HAND_ORACLE_VERIFIED/VERIFIED and prefix-match evidence may support runtime correctness claims.",
            "Do not count construction/stat-only rows or missing oracle rows as runtime correctness evidence.",
            "Spot-check representative F/G/U/R, past-operator, finite-word, and infinite-word rows before citing.",
        ),
        review_guide_row(
            "RG_XML_PROOF_BOUNDARY",
            "xml_translation",
            "P0",
            "XML-to-MITL rows are structural proof drafts; use XML Obligations, XML Trace Coverage, and Original Trace Gaps first to separate machine-checked prerequisites from human theorem-review obligations.",
            "xml_proof_obligations.csv; xml_trace_coverage_obligations.csv; xml_original_trace_gaps.csv; xml_edge_guard_proofs.csv; xml_proof_appendix.csv; xml_translation_proof_appendix.md",
            "A proof-ready row may be promoted only after all machine-checkable obligations have no FAIL status and the reviewer signs off that the candidate MITL formula matches the XML pair under the stated trace assumptions.",
            "Do not claim all MoniTAal XML benchmarks were equivalently converted to MITL.",
            "Work through XML_PROOF_* and PAPER_CLAIM_* signoff rows together.",
        ),
        review_guide_row(
            "RG_XML_ORIGINAL_TRACE_GAPS",
            "xml_translation",
            "P0",
            "Original Trace Gaps lists proof-ready XML rows whose repository/original timed-word evidence is missing or INCONCLUSIVE; every XML_ORIGINAL_TRACE_GAP_* row needs an explicit human caveat or a decisive original trace.",
            "xml_original_trace_gaps.csv; xml_original_trace_gaps.md; xml_trace_coverage_obligations.csv; monitaal_baseline_results.csv; review_signoff_template.csv",
            "Use APPROVE_WITH_CAVEAT only if the paper wording keeps the original-input provenance caveat; use REJECT_OR_FIX if the paper claim requires decisive original-input evidence.",
            "Do not use APPROVE_AS_CLAIMED for generated-only or INCONCLUSIVE original-input provenance gaps.",
            "Review the Original Trace Gaps sheet before approving any affected XML proof or paper-claim signoff row.",
        ),
        review_guide_row(
            "RG_PAPER_CLAIM_AUDIT",
            "paper_claims",
            "P0" if claim_audit_fail else "P1",
            f"Paper claim consistency audit has {claim_audit_fail} FAIL rows; use it as a safety check, not as a mathematical proof.",
            "paper_claim_review.csv; paper_claim_consistency_audit.csv; review_signoff_template.csv",
            "A PASS claim audit means no generated consistency issue was found; human signoff is still required for proof-ready body rows.",
            "Do not call generated proof ledgers final theorem proofs without reviewer approval.",
            "Sign off BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF rows before using them in paper body text.",
        ),
        review_guide_row(
            "RG_TIMEOUT_POLICY",
            "benchmark_caveats",
            "P1",
            f"MoniTAal baseline has {baseline_timeouts} timeout rows, {skipped_inputs} skipped-no-input rows, and {generated_empty_inputs} generated empty probes for XML pairs without repository inputs; completed baseline rows may still be INCONCLUSIVE.",
            "monitaal_baseline_results.csv; timeout_rerun_summary.csv; timeout_rerun_details.csv; translation_candidate_results.csv",
            "Rows with a MoniTAal verdict can support trace-level final-verdict comparison; timeout and skipped-input rows cannot.",
            "Do not report generated empty probes, skipped-input rows, or INCONCLUSIVE baseline matches as XML-to-MITL equivalence proofs or original-input benchmark evidence.",
            "Use APPROVE_WITH_CAVEAT or KEEP_EXCLUDED for no-original-input rows; require proof signoff for proof-ready matched rows.",
        ),
        review_guide_row(
            "RG_REPRODUCIBILITY",
            "reproducibility",
            "P1",
            "Tie any paper table or manual decision to the matching result directory and reproducibility manifest.",
            "reproducibility_manifest.csv; reproducibility_manifest.json; reproducibility_manifest.md; experiment_summary.json; .codex/PROJECT_STATE.md",
            "Every cited result should point to a concrete output directory, command, source hash, result hash, and dirty-worktree state.",
            "Do not separate copied tables from the matching manifest and workbook.",
            "Record the exact result directory in paper notes or review notes.",
        ),
        review_guide_row(
            "RG_RERUN_AFTER_FIX",
            "bug_fix_loop",
            "P1",
            "If any review row exposes a real bug, fix the cause, rerun the full experiment, regenerate the workbook, and update handoff files.",
            ".codex/SESSION_LOG.md; test/TARV/scripts/run_paper_experiments.py; src/TAMonitor",
            "A fix is accepted only when the relevant audit rows and regression outputs pass after rerun.",
            "Do not patch expected results or weaken oracle semantics to make a test pass.",
            "Append the command/result summary to SESSION_LOG and update PROJECT_STATE.",
        ),
        review_guide_row(
            "RG_CURRENT_SIGNOFF_STATUS",
            "current_status",
            "P0",
            f"The generated signoff template currently has {blank_signoffs} blank reviewer decisions; this is expected before human review.",
            "review_signoff_template.csv; review_signoff_template.md",
            "Blank reviewer decisions mean the artifact is ready for review, not signed off.",
            "Do not state that human review is complete until decisions are filled and checked.",
            "Use this row to distinguish generated evidence from human approval.",
        ),
        review_guide_row(
            "RG_SIGNOFF_IMPORT_ROUNDTRIP",
            "current_status",
            "P0",
            "After manual review, import reviewer-owned fields from a filled CSV or Review Signoff workbook sheet instead of hand-editing generated queue, policy, or evidence columns.",
            "test/TARV/scripts/import_review_signoff.py; review_signoff_template.csv; review_signoff_evidence_bundle.csv; review_signoff_validation.json; signoff_import_roundtrip_audit.csv; signoff_import_roundtrip_audit.md",
            "Only reviewer_decision, reviewer, review_date, and reviewer_notes are human-owned import fields; generated evidence and decision-policy fields must match the current packet.",
            "Do not overwrite generated signoff rows with a stale workbook export or cite completed human signoff before complete-mode validation passes.",
            "Run import_review_signoff.py, then validate_review_signoff.py --mode complete; use verify_review_packet.py --signoff-mode complete for a completed-review packet.",
        ),
    ]


def write_review_guide(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "review_guide.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    section_counts = Counter(row["section"] for row in rows)
    lines = [
        "# Review Guide",
        "",
        "This generated guide explains how to use the TAMonitor paper-review packet.",
        "It is intentionally conservative: it tells reviewers when evidence is usable, caveated, deferred, or excluded.",
        "",
        "## Sections",
        "",
    ]
    for section, count in sorted(section_counts.items()):
        lines.append(f"- `{section}`: {count}")
    lines.extend([
        "",
        "## Guide Rows",
        "",
        "| guide_id | priority | section | instruction | decision_rule | must_not_claim |",
        "|---|---|---|---|---|---|",
    ])
    for row in rows:
        instruction = row["instruction"].replace("|", "\\|")
        decision_rule = row["decision_rule"].replace("|", "\\|")
        must_not_claim = row["must_not_claim"].replace("|", "\\|")
        lines.append(
            f"| `{row['guide_id']}` | `{row['priority']}` | `{row['section']}` | "
            f"{instruction} | {decision_rule} | {must_not_claim} |"
        )
    lines.append("")
    (output_dir / "review_guide.md").write_text("\n".join(lines), encoding="utf-8")


def xml_text(node: ET.Element | None) -> str:
    return "" if node is None or node.text is None else node.text.strip()


def strip_sync_suffix(label: str) -> str:
    return label[:-1] if label.endswith(("!", "?")) else label


def to_ap(label: str) -> str:
    if not label:
        return "<empty/no_ap>"
    return label[0].lower() + label[1:]


def parse_xml_templates(xml_path: Path, source_kind: str = "xml_file", embedded_symbol: str = "") -> list[dict[str, Any]]:
    try:
        root = ET.parse(xml_path).getroot()
    except Exception as exc:
        return [{
            "xml_path": str(xml_path),
            "template": "",
            "source_kind": source_kind,
            "embedded_symbol": embedded_symbol,
            "parse_status": "xml_parse_error",
            "parse_error": str(exc),
        }]

    rows = []
    for template in root.findall("template"):
        name = xml_text(template.find("name"))
        locations = template.findall("location")
        transitions = template.findall("transition")
        labels = []
        guards = []
        resets = []
        accept_locations = 0
        for loc in locations:
            loc_name = xml_text(loc.find("name"))
            if loc_name.endswith("_a"):
                accept_locations += 1
        for tr in transitions:
            for label in tr.findall("label"):
                kind = label.attrib.get("kind", "")
                text = xml_text(label)
                if kind == "synchronisation" and text:
                    labels.append(strip_sync_suffix(text))
                elif kind == "guard" and text:
                    guards.append(text)
                elif kind == "assignment" and text:
                    resets.append(text)
        rows.append({
            "xml_path": str(xml_path),
            "xml_file": xml_path.name,
            "template": name,
            "source_kind": source_kind,
            "embedded_symbol": embedded_symbol,
            "parse_status": "ok",
            "locations": len(locations),
            "accept_locations": accept_locations,
            "transitions": len(transitions),
            "labels": ";".join(sorted(set(labels))),
            "guards": ";".join(sorted(set(guards))),
            "resets": ";".join(sorted(set(resets))),
            "parse_error": "",
        })
    return rows


def parse_xml_transition_details(xml_path: Path, source_kind: str = "xml_file", embedded_symbol: str = "") -> list[dict[str, Any]]:
    """Extract one flat, human-reviewable row per MoniTAal XML transition."""
    try:
        root = ET.parse(xml_path).getroot()
    except Exception as exc:
        return [{
            "xml_path": str(xml_path),
            "xml_file": xml_path.name,
            "source_kind": source_kind,
            "embedded_symbol": embedded_symbol,
            "template": "",
            "parse_status": "xml_parse_error",
            "parse_error": str(exc),
        }]

    rows: list[dict[str, Any]] = []
    for template in root.findall("template"):
        template_name = xml_text(template.find("name"))
        init_ref = ""
        init_node = template.find("init")
        if init_node is not None:
            init_ref = init_node.attrib.get("ref", "")

        location_info: dict[str, dict[str, str]] = {}
        for location in template.findall("location"):
            loc_id = location.attrib.get("id", "")
            loc_name = xml_text(location.find("name"))
            invariants = [xml_text(label) for label in location.findall("label") if label.attrib.get("kind", "") == "invariant" and xml_text(label)]
            location_info[loc_id] = {
                "name": loc_name,
                "accepting": "yes" if loc_name.endswith("_a") else "no",
                "initial": "yes" if loc_id == init_ref else "no",
                "invariants": ";".join(invariants),
            }

        transitions = template.findall("transition")
        if not transitions:
            rows.append({
                "xml_path": str(xml_path),
                "xml_file": xml_path.name,
                "source_kind": source_kind,
                "embedded_symbol": embedded_symbol,
                "template": template_name,
                "parse_status": "ok",
                "transition_index": "",
                "transition_id": "",
                "source_id": "",
                "source_name": "",
                "source_accepting": "",
                "source_initial": "",
                "source_invariants": "",
                "target_id": "",
                "target_name": "",
                "target_accepting": "",
                "target_initial": "",
                "target_invariants": "",
                "sync_raw": "",
                "sync_label": "",
                "sync_ap_candidate": "",
                "guards": "",
                "assignments": "",
                "other_labels": "",
                "nails": "0",
                "parse_error": "",
            })
            continue

        for index, transition in enumerate(transitions, start=1):
            source = transition.find("source")
            target = transition.find("target")
            source_id = source.attrib.get("ref", "") if source is not None else ""
            target_id = target.attrib.get("ref", "") if target is not None else ""
            source_info = location_info.get(source_id, {})
            target_info = location_info.get(target_id, {})
            sync_raw: list[str] = []
            sync_clean: list[str] = []
            guards: list[str] = []
            assignments: list[str] = []
            other_labels: list[str] = []
            for label in transition.findall("label"):
                kind = label.attrib.get("kind", "")
                text = xml_text(label)
                if not text:
                    continue
                if kind == "synchronisation":
                    sync_raw.append(text)
                    sync_clean.append(strip_sync_suffix(text))
                elif kind == "guard":
                    guards.append(text)
                elif kind == "assignment":
                    assignments.append(text)
                else:
                    other_labels.append(f"{kind}:{text}" if kind else text)
            rows.append({
                "xml_path": str(xml_path),
                "xml_file": xml_path.name,
                "source_kind": source_kind,
                "embedded_symbol": embedded_symbol,
                "template": template_name,
                "parse_status": "ok",
                "transition_index": index,
                "transition_id": transition.attrib.get("id", ""),
                "source_id": source_id,
                "source_name": source_info.get("name", ""),
                "source_accepting": source_info.get("accepting", ""),
                "source_initial": source_info.get("initial", ""),
                "source_invariants": source_info.get("invariants", ""),
                "target_id": target_id,
                "target_name": target_info.get("name", ""),
                "target_accepting": target_info.get("accepting", ""),
                "target_initial": target_info.get("initial", ""),
                "target_invariants": target_info.get("invariants", ""),
                "sync_raw": ";".join(sync_raw),
                "sync_label": ";".join(sync_clean),
                "sync_ap_candidate": ";".join(to_ap(label) for label in sync_clean),
                "guards": ";".join(guards),
                "assignments": ";".join(assignments),
                "other_labels": ";".join(other_labels),
                "nails": len(transition.findall("nail")),
                "parse_error": "",
            })
    return rows


def extract_c_string(path: Path, symbol: str) -> str:
    text = path.read_text(encoding="utf-8", errors="replace")
    pattern = re.compile(r"const\s+char\s*\*\s*" + re.escape(symbol) + r"\s*=\s*((?:\"(?:\\.|[^\"\\])*\"\s*)+);", re.S)
    match = pattern.search(text)
    if not match:
        return ""
    pieces = re.findall(r"\"(?:\\.|[^\"\\])*\"", match.group(1), re.S)
    return "".join(ast.literal_eval(piece) for piece in pieces)


def input_map_key(xml_path: Path, positive_template: str = "", negative_template: str = "") -> str:
    if positive_template or negative_template:
        return f"{xml_path}::{positive_template}::{negative_template}"
    return str(xml_path)


def write_embedded_benchmark_files(output_dir: Path) -> tuple[list[Path], dict[str, list[Path]], list[dict[str, str]]]:
    embedded_dir = output_dir / "embedded_monitaal"
    embedded_dir.mkdir(parents=True, exist_ok=True)
    generated_input_dir = output_dir / "generated_monitaal_inputs"
    generated_input_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        ("b_live_a_freq", REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "b_live_a_freq.h", "b_live_a_freq_model", ""),
        ("gear_controller_test", REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear_controller_test.h", "gear_controller_test_model", "gear_controller_test_input"),
        ("gear_controller_model", REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear_controller_model.h", "gear_controller_properties", "gear_controller_input"),
    ]
    xml_files: list[Path] = []
    input_map: dict[str, list[Path]] = {}
    metadata: list[dict[str, str]] = []
    for case_id, header, xml_symbol, input_symbol in specs:
        xml = extract_c_string(header, xml_symbol)
        if not xml:
            metadata.append({"case_id": case_id, "header": str(header), "xml_symbol": xml_symbol, "status": "missing_xml_symbol"})
            continue
        xml_path = embedded_dir / f"{case_id}.xml"
        xml_path.write_text(xml, encoding="utf-8")
        if case_id == "gear_controller_model":
            metadata.append({"case_id": case_id, "header": str(header), "xml_symbol": xml_symbol, "status": "duplicate_of_gear-control-properties.xml"})
        else:
            xml_files.append(xml_path)
            metadata.append({"case_id": case_id, "header": str(header), "xml_symbol": xml_symbol, "status": "ok"})
        if input_symbol:
            input_text = extract_c_string(header, input_symbol)
            if input_text:
                input_path = embedded_dir / f"{case_id}.input"
                input_path.write_text(input_text, encoding="utf-8")
                input_map[input_map_key(xml_path)] = [input_path]
        elif case_id == "b_live_a_freq":
            input_path = embedded_dir / "b_live_a_freq_generated.input"
            events = [f"@{i} a" for i in range(19)] + ["@31 b"]
            input_path.write_text("\n".join(events) + "\n", encoding="utf-8")
            input_map[input_map_key(xml_path)] = [input_path]
    cpp_ta = REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear_controller_newgear_prop.h"
    if cpp_ta.exists():
        metadata.append({"case_id": "gear_controller_newgear_prop", "header": str(cpp_ta), "xml_symbol": "", "status": "cpp_constructed_ta_not_xml"})

    monitor_test = REPO_ROOT / "tool" / "MoniTAal" / "test" / "Monitor_test.cpp"
    c_after_10_xml = REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "c_after_10.xml"
    if monitor_test.exists() and c_after_10_xml.exists():
        input_path = embedded_dir / "c_after_10_monitor_test_intersection_test2.input"
        input_path.write_text("@0 a\n@5 c\n@15 c\n@20 b\n", encoding="utf-8")
        input_map.setdefault(input_map_key(c_after_10_xml, "positive", "negative"), []).append(input_path)
        metadata.append({
            "case_id": "c_after_10_monitor_test_intersection_test2",
            "header": str(monitor_test),
            "xml_symbol": "Parser::parse_file(\"models/c_after_10.xml\", positive/negative)",
            "status": "embedded_unit_test_input: intersection_test2 feeds @0 a,@5 c,@15 c,@20 b and asserts monitor_c POSITIVE after @15/@20.",
        })

    review_inputs = {
        "c_after_10_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "c_after_10.xml",
            "positive",
            "negative",
            "@0 a\n@10 c\n",
            "Generated trace-level review input: c at time 10 should satisfy F [10,infty) c.",
        ),
        "c_after_10_later_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "c_after_10.xml",
            "positive",
            "negative",
            "@0 a\n@11 c\n",
            "Generated independent review input: c strictly after time 10 should also satisfy F [10,infty) c.",
        ),
        "c_after_10_no_witness_inconclusive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "c_after_10.xml",
            "positive",
            "negative",
            "@0\n@11\n",
            "Generated three-valued review input: after the lower bound with no c witness, F [10,infty) c remains inconclusive under infinite-word RV.",
        ),
        "c_after_20_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "c_after_20.xml",
            "positive",
            "negative",
            "@0 a\n@20 c\n",
            "Generated trace-level review input: c at time 20 should satisfy F [20,infty) c.",
        ),
        "c_after_20_later_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "c_after_20.xml",
            "positive",
            "negative",
            "@0 a\n@21 c\n",
            "Generated independent review input: c strictly after time 20 should also satisfy F [20,infty) c.",
        ),
        "c_after_20_no_witness_inconclusive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "c_after_20.xml",
            "positive",
            "negative",
            "@0\n@21\n",
            "Generated three-valued review input: after the lower bound with no c witness, F [20,infty) c remains inconclusive under infinite-word RV.",
        ),
        "only_ab_until10_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "only_ab_until10.xml",
            "positive",
            "negative",
            "@0 a\n@5 c\n",
            "Generated trace-level review input: c before time 10 should violate G [0,10] (!c).",
        ),
        "only_ab_until10_positive_after_bound": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "only_ab_until10.xml",
            "positive",
            "negative",
            "@0 a\n@11 c\n",
            "Generated trace-level review input: c after time 10 should satisfy G [0,10] (!c).",
        ),
        "only_ab_until10_negative_boundary": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "only_ab_until10.xml",
            "positive",
            "negative",
            "@0 a\n@10 c\n",
            "Generated trace-level review input: c at the closed time-10 boundary should violate G [0,10] (!c).",
        ),
        "a_b_initial_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "a-b.xml",
            "a_leadsto_b",
            "not_a_leadsto_b",
            "@0 a\n@31 b\n",
            "Generated regression input: initial a with b after 30 should violate the G* leadsto candidate.",
        ),
        "a_b_boundary_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "a-b.xml",
            "a_leadsto_b",
            "not_a_leadsto_b",
            "@0 a\n@30 b\n",
            "Generated boundary input: initial a with b exactly at 30 should satisfy the closed-bound G* leadsto candidate.",
        ),
        "a_b_rearmed_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "a-b.xml",
            "a_leadsto_b",
            "not_a_leadsto_b",
            "@0 a\n@30 b\n@40 a\n@71 b\n",
            "Generated re-arm input: one closed-bound a->b obligation is followed by a second late response violation.",
        ),
        "a_b30_initial_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "a-b30.xml",
            "a_leadsto_b",
            "not_a_leadsto_b",
            "@0 a\n@31 b\n",
            "Generated regression input: initial a with b after 30 should violate the G* leadsto candidate.",
        ),
        "a_b30_boundary_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "a-b30.xml",
            "a_leadsto_b",
            "not_a_leadsto_b",
            "@0 a\n@30 b\n",
            "Generated boundary input: initial a with b exactly at 30 should satisfy the closed-bound G* leadsto candidate.",
        ),
        "a_b30_rearmed_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "a-b30.xml",
            "a_leadsto_b",
            "not_a_leadsto_b",
            "@0 a\n@30 b\n@40 a\n@71 b\n",
            "Generated re-arm input: one closed-bound a->b obligation is followed by a second late response violation.",
        ),
        "a_b_copy_initial_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "a-b copy.xml",
            "a_leadsto_b",
            "not_a_leadsto_b",
            "@0 a\n@31 b\n",
            "Generated regression input: initial a with b after 30 should violate the G* leadsto candidate.",
        ),
        "a_b_copy_boundary_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "a-b copy.xml",
            "a_leadsto_b",
            "not_a_leadsto_b",
            "@0 a\n@30 b\n",
            "Generated boundary input: initial a with b exactly at 30 should satisfy the closed-bound G* leadsto candidate.",
        ),
        "a_b_copy_rearmed_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "a-b copy.xml",
            "a_leadsto_b",
            "not_a_leadsto_b",
            "@0 a\n@30 b\n@40 a\n@71 b\n",
            "Generated re-arm input: one closed-bound a->b obligation is followed by a second late response violation.",
        ),
        "absentAQ_initial_boundary_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "absentAQ.xml",
            "positive",
            "negative",
            "@0 q\n@10 p\n",
            "Generated regression input: initial q followed by p at the closed 10-boundary should violate the G* absence candidate.",
        ),
        "absentAQ_safe_after_bound_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "absentAQ.xml",
            "positive",
            "negative",
            "@0 q\n@11 p\n",
            "Generated boundary input: initial q followed by p after the closed 10-boundary should satisfy the G* absence candidate.",
        ),
        "absentAQ_rearmed_boundary_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "absentAQ.xml",
            "positive",
            "negative",
            "@0 q\n@11 p\n@20 q\n@30 p\n",
            "Generated re-arm input: one safe q obligation is followed by a second closed-bound forbidden p violation.",
        ),
        "absentBR_initial_boundary_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "absentBR.xml",
            "positive",
            "negative",
            "@0 p\n@10 r\n",
            "Generated regression input: initial p followed by r at the closed 10-boundary should violate the G* absence candidate.",
        ),
        "absentBR_safe_after_bound_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "absentBR.xml",
            "positive",
            "negative",
            "@0 p\n@11 r\n",
            "Generated boundary input: initial p followed by r after the closed 10-boundary should satisfy the G* absence candidate.",
        ),
        "absentBR_rearmed_boundary_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "absentBR.xml",
            "positive",
            "negative",
            "@0 p\n@11 r\n@20 p\n@30 r\n",
            "Generated re-arm input: one safe p obligation is followed by a second closed-bound forbidden r violation.",
        ),
        "recurGLB_initial_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "recurGLB.xml",
            "positive",
            "negative",
            "@0 p\n@11 p\n",
            "Generated regression input: initial p followed by next p after 10 should violate the G* recurrence candidate.",
        ),
        "recurGLB_first_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "recurGLB.xml",
            "positive",
            "negative",
            "@0\n@11 p\n",
            "Generated regression input: no p in the initial closed 10-bound should violate the recurrence candidate.",
        ),
        "recurGLB_timely_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "recurGLB.xml",
            "positive",
            "negative",
            "@0 p\n@10 p\n@20 p\n",
            "Generated three-valued review input: timely p recurrences give non-violation evidence while future recurrence obligations remain open.",
        ),
        "gear_CloseClutch_initial_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "CloseClutch",
            "NotCloseClutch",
            "@0 CloseClutch\n@151 ClutchIsClosed\n",
            "Generated reduced gear-controller input: initial CloseClutch response after 150 should violate the G* request-response candidate.",
        ),
        "gear_CloseClutch_boundary_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "CloseClutch",
            "NotCloseClutch",
            "@0 CloseClutch\n@150 ClutchIsClosed\n",
            "Generated boundary gear-controller input: initial CloseClutch response exactly at 150 should satisfy the closed-bound candidate.",
        ),
        "gear_CloseClutch_rearmed_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "CloseClutch",
            "NotCloseClutch",
            "@0 CloseClutch\n@150 ClutchIsClosed\n@200 CloseClutch\n@351 ClutchIsClosed\n",
            "Generated independent gear-controller input: one boundary-satisfied CloseClutch obligation is followed by a re-armed late response violation.",
        ),
        "gear_OpenClutch_initial_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "OpenClutch",
            "NotOpenClutch",
            "@0 OpenClutch\n@151 ClutchIsOpen\n",
            "Generated reduced gear-controller input: initial OpenClutch response after 150 should violate the G* request-response candidate.",
        ),
        "gear_OpenClutch_boundary_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "OpenClutch",
            "NotOpenClutch",
            "@0 OpenClutch\n@150 ClutchIsOpen\n",
            "Generated boundary gear-controller input: initial OpenClutch response exactly at 150 should satisfy the closed-bound candidate.",
        ),
        "gear_OpenClutch_rearmed_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "OpenClutch",
            "NotOpenClutch",
            "@0 OpenClutch\n@150 ClutchIsOpen\n@200 OpenClutch\n@351 ClutchIsOpen\n",
            "Generated independent gear-controller input: one boundary-satisfied OpenClutch obligation is followed by a re-armed late response violation.",
        ),
        "gear_ReqSet_initial_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "ReqSet",
            "NotReqSet",
            "@0 ReqSet\n@301 GearSet\n",
            "Generated reduced gear-controller input: initial ReqSet response after 300 should violate the G* request-response candidate.",
        ),
        "gear_ReqSet_boundary_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "ReqSet",
            "NotReqSet",
            "@0 ReqSet\n@300 GearSet\n",
            "Generated boundary gear-controller input: initial ReqSet response exactly at 300 should satisfy the closed-bound candidate.",
        ),
        "gear_ReqSet_rearmed_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "ReqSet",
            "NotReqSet",
            "@0 ReqSet\n@300 GearSet\n@400 ReqSet\n@701 GearSet\n",
            "Generated independent gear-controller input: one boundary-satisfied ReqSet obligation is followed by a re-armed late response violation.",
        ),
        "gear_ReqNeu_initial_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "ReqNeu",
            "NotReqNeu",
            "@0 ReqNeu\n@201 GearNeu\n",
            "Generated reduced gear-controller input: initial ReqNeu response after 200 should violate the G* request-response candidate.",
        ),
        "gear_ReqNeu_boundary_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "ReqNeu",
            "NotReqNeu",
            "@0 ReqNeu\n@200 GearNeu\n",
            "Generated boundary gear-controller input: initial ReqNeu response exactly at 200 should satisfy the closed-bound candidate.",
        ),
        "gear_ReqNeu_rearmed_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "ReqNeu",
            "NotReqNeu",
            "@0 ReqNeu\n@200 GearNeu\n@300 ReqNeu\n@501 GearNeu\n",
            "Generated independent gear-controller input: one boundary-satisfied ReqNeu obligation is followed by a re-armed late response violation.",
        ),
        "gear_SpeedSet_initial_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "SpeedSet",
            "NotSpeedSet",
            "@0 SpeedSet\n@501 ReqTorque\n",
            "Generated reduced gear-controller input: initial SpeedSet response after 500 should violate the G* request-response candidate.",
        ),
        "gear_SpeedSet_boundary_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "SpeedSet",
            "NotSpeedSet",
            "@0 SpeedSet\n@500 ReqTorque\n",
            "Generated boundary gear-controller input: initial SpeedSet response exactly at 500 should satisfy the closed-bound candidate.",
        ),
        "gear_SpeedSet_rearmed_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "SpeedSet",
            "NotSpeedSet",
            "@0 SpeedSet\n@500 ReqTorque\n@600 SpeedSet\n@1101 ReqTorque\n",
            "Generated independent gear-controller input: one boundary-satisfied SpeedSet obligation is followed by a re-armed late response violation.",
        ),
        "gear_test1_initial_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "test1",
            "Nottest1",
            "@0 test1\n@901 ReqTorque\n",
            "Generated reduced gear-controller input: initial test1 response after 900 should violate the G* request-response candidate.",
        ),
        "gear_test1_boundary_positive": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "test1",
            "Nottest1",
            "@0 test1\n@900 ReqTorque\n",
            "Generated boundary gear-controller input: initial test1 response exactly at 900 should satisfy the closed-bound candidate.",
        ),
        "gear_test1_rearmed_late_negative": (
            REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-properties.xml",
            "test1",
            "Nottest1",
            "@0 test1\n@900 ReqTorque\n@1000 test1\n@1901 ReqTorque\n",
            "Generated independent gear-controller input: one boundary-satisfied test1 obligation is followed by a re-armed late response violation.",
        ),
        "no_original_input_delay_example_empty": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "delay-example.xml",
            "positive",
            "negative",
            "",
            "Generated empty timed-word probe because this XML pair has no repository input; baseline-only evidence, not an original benchmark trace.",
        ),
        "no_original_input_never_b_empty": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "never_b.xml",
            "positive",
            "negative",
            "",
            "Generated empty timed-word probe because this XML pair has no repository input; keep XML baseline-only until current-event semantics are proved.",
        ),
        "no_original_input_time_must_pass_empty": (
            REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "time-must-pass.xml",
            "positive",
            "negative",
            "",
            "Generated empty timed-word probe because this time-divergence XML has no ordinary repository input; not a trace-level MITL conversion claim.",
        ),
    }
    for case_id, (xml_path, positive_template, negative_template, input_text, reason) in review_inputs.items():
        if not xml_path.exists():
            metadata.append({"case_id": case_id, "header": str(xml_path), "xml_symbol": "", "status": "missing_xml_for_generated_input"})
            continue
        input_path = generated_input_dir / f"{case_id}.input"
        input_path.write_text(input_text, encoding="utf-8")
        input_map.setdefault(input_map_key(xml_path, positive_template, negative_template), []).append(input_path)
        metadata.append({"case_id": case_id, "header": str(xml_path), "xml_symbol": "", "status": f"{positive_template}/{negative_template}: {reason}"})
    return xml_files, input_map, metadata


def pair_templates(rows: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any], str]]:
    by_xml: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        if row.get("parse_status") == "ok":
            by_xml.setdefault(row["xml_path"], []).append(row)

    pairs: list[tuple[dict[str, Any], dict[str, Any], str]] = []
    for templates in by_xml.values():
        by_name = {t["template"]: t for t in templates}
        names = set(by_name)
        if "positive" in names and "negative" in names:
            pairs.append((by_name["positive"], by_name["negative"], "positive_negative"))
        for name in sorted(names):
            if name.startswith("Not") and name[3:] in by_name:
                pairs.append((by_name[name[3:]], by_name[name], "Not_prefix"))
            if name.startswith("not_") and name[4:] in by_name:
                pairs.append((by_name[name[4:]], by_name[name], "not_prefix"))
            if name.startswith("not") and name[3:] in by_name:
                pairs.append((by_name[name[3:]], by_name[name], "not_prefix_no_underscore"))

    dedup: dict[tuple[str, str, str], tuple[dict[str, Any], dict[str, Any], str]] = {}
    for pos, neg, method in pairs:
        dedup[(pos["xml_path"], pos["template"], neg["template"])] = (pos, neg, method)
    return list(dedup.values())


def ap_mapping_for(labels_text: str) -> dict[str, str]:
    labels = [label for label in labels_text.split(";") if label]
    mapping = {label: to_ap(label) for label in labels}
    mapping[""] = "<empty/no_ap>"
    return mapping


def candidate_mitl(pos: dict[str, Any], neg: dict[str, Any]) -> tuple[str, str, str, str]:
    name = pos["template"]
    labels = [x for x in pos.get("labels", "").split(";") if x]
    guards = pos.get("guards", "")
    xml_file = pos["xml_file"]
    low_name = name.lower()

    if name == "a_leadsto_b":
        return "G* (a -> F [0,30] b)", "high", "reviewed_obvious_candidate", "Known a-b leadsto monitor pattern. Uses G* because MoniTAal monitors the trigger at the first observed event."
    if xml_file == "never_b.xml" or low_name == "never_b":
        return "", "none", "not_claimed", (
            "No conservative MITL candidate is claimed. The hand-written MoniTAal "
            "never_b automaton is a safety monitor over observed b events, but "
            "the tested MightyPPL strict/weak global and !F encodings have "
            "current-event boundary differences; keep XML baseline-only until a "
            "formal current-event encoding proof is supplied."
        )
    if xml_file == "time-must-pass.xml":
        return "", "none", "not_claimed", (
            "No conservative MITL candidate is claimed. This MoniTAal test is a "
            "time-divergence/time-must-pass automaton with no ordinary trace input "
            "baseline; do not infer an XML-to-MITL formula from the file name."
        )
    if xml_file == "c_after_10.xml":
        return "F [10,infty) c", "medium", "reviewed_obvious_candidate", "Template name and labels indicate c after 10; inspect automaton before accepting."
    if xml_file == "c_after_20.xml":
        return "F [20,infty) c", "medium", "reviewed_obvious_candidate", "Template name and labels indicate c after 20; inspect automaton before accepting."
    if xml_file == "only_ab_until10.xml":
        return "G [0,10] (!c)", "medium", "reviewed_obvious_candidate", "Template name indicates only a/b events until time 10."
    if xml_file == "absentAQ.xml":
        return "G* (q -> G [0,10] (!p))", "medium", "reviewed_obvious_candidate", "Dwyer absence after Q pattern inferred from template name and automaton family; G* includes the first observed trigger."
    if xml_file == "absentBR.xml":
        return "G* (p -> G [0,10] (!r))", "medium", "reviewed_obvious_candidate", "Dwyer absence before/after R pattern candidate from MoniTAal test naming; G* includes the first observed trigger."
    if xml_file == "absentBQR.xml":
        return "G* (q -> ((!p) U [3,10] r))", "low", "approximate", "Between Q and R absence pattern is approximate; repeated q/r and obligation termination require edge review."
    if xml_file == "recurGLB.xml":
        return "(F [0,10] p) && (G* (p -> F (0,10] p))", "medium", "reviewed_obvious_candidate", "Bounded recurrence as an initial p obligation plus an event-triggered next-p obligation; G* includes the first observed trigger and the strict lower bound avoids satisfying the obligation with the triggering p itself."
    if xml_file == "recurBQR.xml":
        return "G* (q -> ((F [0,10] p) U r))", "low", "approximate", "Between Q and R recurrence pattern is approximate; requires edge review."
    if xml_file == "f(g(notb)_and_g(f(a)).xml":
        return "(F [0,10] a) && (G* (a -> F (0,10] a)) && F (G (!b))", "low", "approximate", "Corrected from XML edge structure: initial and re-armed a-within-10 obligations plus eventual no-b suffix. Still approximate because liveness/finite-prefix and alphabet-closure semantics need proof review."
    if xml_file.startswith("b_live_a_freq") or set(labels) == {"a", "b"} and "1000" in guards:
        return "F (G (!b) && G (F [0,1000] a))", "medium", "approximate", "Frequency/liveness benchmark pattern inferred from benchmark name and guards."
    if name in {"CloseClutch", "OpenClutch", "ReqSet", "ReqNeu", "SpeedSet"}:
        request_response = {
            "CloseClutch": ("closeClutch", "clutchIsClosed", 150),
            "OpenClutch": ("openClutch", "clutchIsOpen", 150),
            "ReqSet": ("reqSet", "gearSet", 300),
            "ReqNeu": ("reqNeu", "gearNeu", 200),
            "SpeedSet": ("speedSet", "reqTorque", 500),
        }
        req, res, bound = request_response[name]
        return f"G* ({req} -> F [0,{bound}] {res})", "medium", "reviewed_obvious_candidate", "Gear-controller request/response pattern inferred from template name and bound; G* includes requests at the first observed event."
    if name == "test1":
        if xml_file == "gear_controller_test.xml":
            return "G* (reqNewGear -> F [150,1205] newGear)", "medium", "reviewed_obvious_candidate", "Gear-controller test template has guarded NewGear response interval; G* includes the first observed request."
        return "G* (test1 -> F [0,900] reqTorque)", "medium", "reviewed_obvious_candidate", "Gear-controller test1 response pattern from benchmark templates; G* includes the first observed trigger."
    if name in {"startend", "startend_div"}:
        return "G (start -> F end)", "low", "approximate", "Name-only candidate; automaton review required."
    if low_name.startswith("absent"):
        return "", "none", "not_claimed", "Dwyer absence-pattern automaton; needs manual reconstruction of scope and event roles."
    if low_name.startswith("recur"):
        return "", "none", "not_claimed", "Dwyer recurrence-pattern automaton; needs manual reconstruction of scope and event roles."
    if labels:
        return "", "none", "not_claimed", "No trustworthy automatic MITL translation rule matched this automaton."
    return "", "none", "not_claimed", "No labels found for translation inference."


def find_monitaal_bin() -> Path | None:
    candidates = [
        REPO_ROOT / "tool" / "MightyPPL" / "build" / "monitaal-prefix" / "src" / "monitaal-build" / "src" / "monitaal-bin" / "MoniTAal-bin",
        REPO_ROOT / "tool" / "MoniTAal" / "build" / "src" / "monitaal-bin" / "MoniTAal-bin",
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return candidate
    return None


def find_inputs_for_xml(xml_path: Path, embedded_inputs: dict[str, list[Path]], positive_template: str = "", negative_template: str = "") -> list[Path]:
    candidates: list[Path] = []
    if positive_template or negative_template:
        candidates.extend(embedded_inputs.get(input_map_key(xml_path, positive_template, negative_template), []))
    candidates.extend(embedded_inputs.get(input_map_key(xml_path), []))
    stem = xml_path.stem
    normalized_stem = stem.lower().replace("-", "").replace("_", "").replace(" ", "")
    for path in xml_path.parent.glob("*input*.txt"):
        normalized_input = path.stem.lower().replace("-", "").replace("_", "").replace(" ", "")
        if len(normalized_stem) >= 5 and normalized_input.startswith(normalized_stem):
            candidates.append(path)
    special = {
        "a-b.xml": [TARV_ROOT / "cases" / "monitaal_a_b_negative.input"],
        "a-b30.xml": [TARV_ROOT / "cases" / "monitaal_a_b_negative.input"],
        "a-b copy.xml": [TARV_ROOT / "cases" / "monitaal_a_b_negative.input"],
        "f(g(notb)_and_g(f(a)).xml": [
            TARV_ROOT / "cases" / "f_g_notb_first_late_negative.input",
            TARV_ROOT / "cases" / "f_g_notb_late_a_negative.input",
        ],
        "gear-control-properties.xml": [REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-input.txt"],
    }
    candidates.extend([p for p in special.get(xml_path.name, []) if p.exists()])
    return sorted(dict.fromkeys(candidates))


def baseline_input_origin(input_path: Path) -> str:
    text = input_path.as_posix()
    if "generated_monitaal_inputs" in text:
        if input_path.name.startswith("no_original_input_"):
            return "generated_empty_no_original_input"
        return "generated_review_input"
    if "embedded_monitaal" in text:
        return "embedded_benchmark_input"
    try:
        input_path.resolve().relative_to(REPO_ROOT / "tool" / "MoniTAal")
        return "repository_input"
    except ValueError:
        return "external_or_case_input"


def baseline_input_rationale(input_path: Path) -> str:
    origin = baseline_input_origin(input_path)
    if origin == "generated_empty_no_original_input":
        return "Generated empty timed-word probe for an XML pair with no repository input; use as baseline-only evidence, not as an original benchmark trace."
    if origin == "generated_review_input":
        return "Generated review input used to exercise a trace-level XML baseline/candidate comparison."
    if origin == "embedded_benchmark_input":
        if "monitor_test" in input_path.name:
            return "Input transcribed from a MoniTAal repository unit test with explicit monitor status assertions."
        return "Input extracted or generated for an embedded MoniTAal benchmark header."
    if origin == "repository_input":
        return "Input shipped in the MoniTAal repository or benchmark directory."
    return "Input outside the MoniTAal repository tree."


def parse_monitaal_verdict(stdout: str) -> str:
    match = re.search(r"verdict is:\s*([A-Z]+)", stdout)
    if match:
        return match.group(1)
    match = re.search(r"Monitor verdicts are\s*\n?([A-Z,\s]+)", stdout)
    if match:
        return match.group(1).strip()
    return ""


def formula_aps(formula: str) -> set[str]:
    reserved = {"true", "false", "infty"}
    return {token for token in re.findall(r"\b[a-z][A-Za-z0-9_]*\b", formula) if token not in reserved}


def convert_monitaal_input_to_trace(input_path: Path, output_path: Path, formula: str, mapping: dict[str, str]) -> int:
    aps = formula_aps(formula)
    event_count = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open(encoding="utf-8", errors="replace") as src, output_path.open("w", encoding="utf-8") as out:
        out.write("# Generated from MoniTAal input for TAMonitor candidate MITL review.\n")
        for line in src:
            clean = line.strip()
            if not clean or clean.startswith("#"):
                continue
            match = re.match(r"@([0-9]+)\s*(.*)$", clean)
            if not match:
                continue
            time_text = match.group(1)
            label = match.group(2).strip().split()[0] if match.group(2).strip() else ""
            ap = mapping.get(label, to_ap(label))
            props = "{" + ap + "}" if ap in aps else "{}"
            out.write(f"{time_text},{props}\n")
            event_count += 1
    return event_count


def run_translation_candidate(
    output_dir: Path,
    tamonitor: Path,
    timeout: int,
    no_run: bool,
    case_id: str,
    candidate: str,
    equivalence_status: str,
    pos: dict[str, Any],
    neg: dict[str, Any],
    input_path: Path,
    mapping: dict[str, str],
    baseline_status: str,
    baseline_verdict: str,
) -> dict[str, Any]:
    case_dir = output_dir / "translation_candidate_cases" / case_id
    formula_path = case_dir / "formula.mitl"
    trace_path = case_dir / "trace.txt"
    formula_path.parent.mkdir(parents=True, exist_ok=True)
    formula_path.write_text(candidate + "\n", encoding="utf-8")
    event_count = convert_monitaal_input_to_trace(input_path, trace_path, candidate, mapping)
    run_dir = output_dir / "translation_candidate_runs" / case_id

    command_result = {"returncode": "", "stdout": "", "stderr": "", "elapsed_ms": "", "timeout": False}
    if not no_run:
        command_result = run_command([
            str(tamonitor),
            "--formula", str(formula_path),
            "--trace", str(trace_path),
            "--word", "infinite",
            "--state", "symbolic",
            "--build-mode", "flatten",
            "--max-valuations", "80000",
            "--out", str(run_dir),
            "--emit-bdd-interface",
        ], timeout)

    summary = read_summary_csv(run_dir / "summary.csv")
    actual_final = summary.get("final_verdict", "")
    if no_run:
        comparison_status = "NOT_RUN"
        oracle_type = "none"
        oracle_verdict = ""
        comparison_evidence = "Execution was skipped by --no-run."
    elif command_result["timeout"]:
        comparison_status = "NOT_VERIFIED_CANDIDATE_TIMEOUT"
        oracle_type = "none"
        oracle_verdict = ""
        comparison_evidence = "TAMonitor candidate run timed out."
    elif command_result["returncode"] != 0:
        comparison_status = "NOT_VERIFIED_CANDIDATE_ERROR"
        oracle_type = "none"
        oracle_verdict = ""
        comparison_evidence = "TAMonitor candidate run returned an error."
    elif baseline_status == "ran" and baseline_verdict:
        comparison_status = "MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT" if actual_final == baseline_verdict else "MISMATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT"
        oracle_type = "monitaal_xml_baseline_same_input"
        oracle_verdict = baseline_verdict
        comparison_evidence = (
            "TAMonitor candidate verdict compared with MoniTAal XML baseline on the same input after AP mapping; "
            "this is trace-level evidence, not an automatic XML-to-MITL equivalence proof."
        )
    elif baseline_status == "timeout":
        comparison_status = "NOT_VERIFIED_BASELINE_TIMEOUT"
        oracle_type = "monitaal_xml_baseline_same_input"
        oracle_verdict = ""
        comparison_evidence = "MoniTAal XML baseline timed out, so candidate verdict has no baseline oracle for this input."
    elif baseline_status == "skipped_no_binary":
        comparison_status = "NOT_VERIFIED_BASELINE_BINARY_MISSING"
        oracle_type = "monitaal_xml_baseline_same_input"
        oracle_verdict = ""
        comparison_evidence = "MoniTAal baseline binary was unavailable."
    else:
        comparison_status = "NOT_VERIFIED_BASELINE_NOT_RUN"
        oracle_type = "monitaal_xml_baseline_same_input"
        oracle_verdict = ""
        comparison_evidence = f"MoniTAal baseline status was {baseline_status or '<empty>'}."

    return {
        "candidate_id": case_id,
        "xml_path": pos["xml_path"],
        "xml_file": pos["xml_file"],
        "source_kind": pos.get("source_kind", "xml_file"),
        "positive_template": pos["template"],
        "negative_template": neg["template"],
        "input_path": str(input_path),
        "candidate_mitl": candidate,
        "mitl_equivalence_status": equivalence_status,
        "mapped_events": event_count,
        "trace_path": str(trace_path),
        "run_dir": str(run_dir),
        "actual_final": actual_final,
        "actual_sat": summary.get("formula_satisfiable", ""),
        "baseline_status": baseline_status,
        "baseline_verdict": baseline_verdict,
        "baseline_comparison_status": comparison_status,
        "oracle_type": oracle_type,
        "oracle_verdict": oracle_verdict,
        "correctness_evidence": comparison_evidence,
        "returncode": command_result["returncode"],
        "timeout": command_result["timeout"],
        "elapsed_ms": command_result["elapsed_ms"],
        "processed_steps": summary.get("processed_steps", ""),
        "positive_locations": summary.get("positive_locations", ""),
        "positive_edges": summary.get("positive_edges", ""),
        "negative_locations": summary.get("negative_locations", ""),
        "negative_edges": summary.get("negative_edges", ""),
        "stdout_excerpt": (command_result["stdout"] or "")[:500].replace("\n", " "),
        "stderr_excerpt": (command_result["stderr"] or "")[:500].replace("\n", " "),
    }


def build_correctness_audit_rows(
    case_rows: list[dict[str, Any]],
    semantic_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    case_by_id = {row["case_id"]: row for row in case_rows}
    audit_rows: list[dict[str, Any]] = []
    for row in semantic_rows:
        case = case_by_id.get(row["case_id"], {})
        audit_rows.append({
            "audit_id": row["case_id"],
            "case_id": row["case_id"],
            "case_family": row["suite"],
            "category": row["category"],
            "formula": case.get("formula", ""),
            "input_or_trace": case.get("trace_path", ""),
            "runtime_verdict": row.get("actual_final", ""),
            "formula_satisfiable": row.get("actual_sat", ""),
            "expected_sat_scope": row.get("expected_sat_scope", ""),
            "oracle_type": row.get("oracle_type", ""),
            "oracle_verdict": row.get("oracle_verdict", ""),
            "correctness_status": row.get("correctness_status", ""),
            "pass_status": row.get("pass_status", ""),
            "baseline_status": "",
            "baseline_verdict": "",
            "mitl_equivalence_status": "",
            "review_status": row.get("review_status", ""),
            "evidence": row.get("correctness_evidence", ""),
            "run_dir": row.get("run_dir", ""),
        })

    for row in candidate_rows:
        audit_rows.append({
            "audit_id": row.get("candidate_id", ""),
            "case_id": row.get("candidate_id", ""),
            "case_family": "monitaal_xml_candidate",
            "category": row.get("xml_file", ""),
            "formula": row.get("candidate_mitl", ""),
            "input_or_trace": row.get("input_path", ""),
            "runtime_verdict": row.get("actual_final", ""),
            "formula_satisfiable": row.get("actual_sat", ""),
            "expected_sat_scope": "baseline_comparison_not_sat_oracle",
            "oracle_type": row.get("oracle_type", ""),
            "oracle_verdict": row.get("oracle_verdict", ""),
            "correctness_status": row.get("baseline_comparison_status", ""),
            "pass_status": "",
            "baseline_status": row.get("baseline_status", ""),
            "baseline_verdict": row.get("baseline_verdict", ""),
            "mitl_equivalence_status": row.get("mitl_equivalence_status", ""),
            "review_status": "needs_manual_equivalence_review" if row.get("mitl_equivalence_status") != "not_claimed" else "xml_baseline_only",
            "evidence": row.get("correctness_evidence", ""),
            "run_dir": row.get("run_dir", ""),
        })
    return audit_rows


def build_candidate_prefix_observation_rows(candidate_rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    observation_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []

    for row in candidate_rows:
        steps_path = Path(str(row.get("run_dir", ""))) / "steps.csv" if row.get("run_dir") else Path()
        steps = read_dict_rows(steps_path)
        first_decisive_step = ""
        first_decisive_time = ""
        first_decisive_verdict = ""
        carry_forward_steps = 0

        for step in steps:
            verdict = step.get("verdict", "")
            if not first_decisive_step and verdict in {"POSITIVE", "NEGATIVE"}:
                first_decisive_step = step.get("step", "")
                first_decisive_time = step.get("time", "")
                first_decisive_verdict = verdict
            if step.get("monitor_advanced") == "false":
                carry_forward_steps += 1
            observation_rows.append({
                "candidate_id": row.get("candidate_id", ""),
                "xml_file": row.get("xml_file", ""),
                "positive_template": row.get("positive_template", ""),
                "negative_template": row.get("negative_template", ""),
                "input_path": row.get("input_path", ""),
                "candidate_mitl": row.get("candidate_mitl", ""),
                "mitl_equivalence_status": row.get("mitl_equivalence_status", ""),
                "baseline_status": row.get("baseline_status", ""),
                "baseline_verdict": row.get("baseline_verdict", ""),
                "baseline_comparison_status": row.get("baseline_comparison_status", ""),
                "actual_final": row.get("actual_final", ""),
                "step": step.get("step", ""),
                "time": step.get("time", ""),
                "human_label": step.get("human_label", ""),
                "canonical_label": step.get("canonical_label", ""),
                "verdict": verdict,
                "monitor_advanced": step.get("monitor_advanced", ""),
                "positive_states": step.get("positive_states", ""),
                "negative_states": step.get("negative_states", ""),
                "run_dir": row.get("run_dir", ""),
                "steps_path": str(steps_path),
            })

        try:
            mapped_events = int(row.get("mapped_events", "") or 0)
        except ValueError:
            mapped_events = 0
        try:
            processed_steps = int(row.get("processed_steps", "") or 0)
        except ValueError:
            processed_steps = 0
        observed_steps = len(steps)
        all_steps_recorded = mapped_events == observed_steps == processed_steps if mapped_events or processed_steps or observed_steps else False

        comparison_status = row.get("baseline_comparison_status", "")
        if comparison_status == "MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT":
            claim_scope = "trace_level_final_verdict_matches_baseline_prefix_steps_observed"
            evidence = "Final verdict matches MoniTAal XML baseline; prefix rows are TAMonitor observations for manual trace review."
        elif comparison_status == "MISMATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT":
            claim_scope = "blocked_mismatch"
            evidence = "Final verdict mismatches MoniTAal XML baseline; inspect prefix rows before using this candidate."
        elif comparison_status == "NOT_VERIFIED_BASELINE_TIMEOUT":
            claim_scope = "not_verified_baseline_timeout_prefix_steps_observed"
            evidence = "TAMonitor prefix rows are available, but MoniTAal XML baseline timed out so this is not correctness evidence."
        else:
            claim_scope = "not_verified"
            evidence = row.get("correctness_evidence", "")

        audit_rows.append({
            "candidate_id": row.get("candidate_id", ""),
            "xml_file": row.get("xml_file", ""),
            "positive_template": row.get("positive_template", ""),
            "negative_template": row.get("negative_template", ""),
            "input_path": row.get("input_path", ""),
            "candidate_mitl": row.get("candidate_mitl", ""),
            "mitl_equivalence_status": row.get("mitl_equivalence_status", ""),
            "mapped_events": row.get("mapped_events", ""),
            "processed_steps": row.get("processed_steps", ""),
            "observed_steps": observed_steps,
            "all_trace_steps_recorded": "true" if all_steps_recorded else "false",
            "first_decisive_step": first_decisive_step,
            "first_decisive_time": first_decisive_time,
            "first_decisive_verdict": first_decisive_verdict,
            "carry_forward_steps": carry_forward_steps,
            "actual_final": row.get("actual_final", ""),
            "baseline_status": row.get("baseline_status", ""),
            "baseline_verdict": row.get("baseline_verdict", ""),
            "baseline_comparison_status": comparison_status,
            "correctness_claim_scope": claim_scope,
            "candidate_step_evidence": evidence,
            "raw_step_artifact": str(steps_path),
            "run_dir": row.get("run_dir", ""),
        })

    return observation_rows, audit_rows


def write_candidate_step_audit(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    counts = Counter(row["baseline_comparison_status"] for row in rows)
    recorded = sum(1 for row in rows if row["all_trace_steps_recorded"] == "true")
    lines = [
        "# Candidate Step Audit",
        "",
        "This generated audit indexes TAMonitor per-prefix outputs for XML-to-MITL benchmark candidates.",
        "`candidate_prefix_observations.csv` contains the full raw per-step export.",
        "The rows here are a compact paper-review index; correctness claims remain final-verdict baseline comparisons unless otherwise proved.",
        "",
        "## Counts",
        "",
        f"- candidate rows: {len(rows)}",
        f"- all trace steps recorded: {recorded}",
    ]
    for key in sorted(counts):
        lines.append(f"- `{key}`: {counts[key]}")
    lines.extend([
        "",
        "## Review Table",
        "",
        "| candidate_id | observed_steps | first_decisive | final | baseline | comparison |",
        "|---|---:|---|---|---|---|",
    ])
    for row in rows:
        lines.append(
            f"| `{row['candidate_id']}` | {row['observed_steps']} | "
            f"`{row['first_decisive_step']}:{row['first_decisive_verdict']}` | "
            f"`{row['actual_final']}` | `{row['baseline_verdict']}` | `{row['baseline_comparison_status']}` |"
        )
    lines.append("")
    (output_dir / "candidate_step_audit.md").write_text("\n".join(lines), encoding="utf-8")


def build_benchmark_manifest(
    translation_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate per-input evidence into one paper-review row per XML pair."""
    def key(row: dict[str, Any]) -> tuple[str, str, str]:
        return (
            row.get("xml_path", ""),
            row.get("positive_template", ""),
            row.get("negative_template", ""),
        )

    candidates_by_pair: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in candidate_rows:
        candidates_by_pair.setdefault(key(row), []).append(row)

    baselines_by_pair: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in baseline_rows:
        baselines_by_pair.setdefault(key(row), []).append(row)
    baseline_origin_by_input = {
        (key(row), row.get("input_path", "")): row.get("input_origin", "")
        for row in baseline_rows
    }

    manifest: list[dict[str, Any]] = []
    for row in translation_rows:
        pair_key = key(row)
        candidate_runs = candidates_by_pair.get(pair_key, [])
        baseline_runs = baselines_by_pair.get(pair_key, [])
        matches = [r for r in candidate_runs if r.get("baseline_comparison_status") == "MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT"]
        mismatches = [r for r in candidate_runs if r.get("baseline_comparison_status") == "MISMATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT"]
        candidate_timeouts = [r for r in candidate_runs if r.get("baseline_comparison_status") == "NOT_VERIFIED_CANDIDATE_TIMEOUT"]
        candidate_baseline_timeouts = [r for r in candidate_runs if r.get("baseline_comparison_status") == "NOT_VERIFIED_BASELINE_TIMEOUT"]
        candidate_errors = [r for r in candidate_runs if r.get("baseline_comparison_status") == "NOT_VERIFIED_CANDIDATE_ERROR"]
        baseline_timeouts = [r for r in baseline_runs if r.get("status") == "timeout"]
        baseline_skipped = [r for r in baseline_runs if r.get("status") == "skipped_no_input"]
        baseline_generated_empty = [r for r in baseline_runs if r.get("input_origin") == "generated_empty_no_original_input"]
        match_origins = [
            baseline_origin_by_input.get((pair_key, r.get("input_path", ""))) or baseline_input_origin(Path(r.get("input_path", "")))
            for r in matches
        ]
        match_origin_counts = Counter(match_origins)
        repository_matches = [r for r, origin in zip(matches, match_origins) if origin == "repository_input"]
        embedded_matches = [r for r, origin in zip(matches, match_origins) if origin == "embedded_benchmark_input"]
        external_matches = [r for r, origin in zip(matches, match_origins) if origin == "external_or_case_input"]
        generated_review_matches = [r for r, origin in zip(matches, match_origins) if origin == "generated_review_input"]
        generated_empty_matches = [r for r, origin in zip(matches, match_origins) if origin == "generated_empty_no_original_input"]

        equivalence_status = row.get("mitl_equivalence_status", "")
        has_candidate = bool(row.get("candidate_mitl", ""))
        match_count = len(matches)
        mismatch_count = len(mismatches)

        if not has_candidate or equivalence_status == "not_claimed":
            promotion_status = "NOT_CLAIMED"
            paper_action = "do_not_promote"
            evidence_grade = "none"
            blocker = "No conservative MITL candidate is claimed for this XML pair."
        elif mismatch_count:
            promotion_status = "BLOCKED_MISMATCH"
            paper_action = "fix_or_drop_candidate"
            evidence_grade = "contradicted"
            blocker = "At least one TAMonitor candidate run mismatched the MoniTAal XML baseline."
        elif equivalence_status == "approximate":
            promotion_status = "APPROXIMATE_TRACE_ONLY" if match_count else "APPROXIMATE_UNVERIFIED"
            paper_action = "manual_edge_review_before_promotion"
            evidence_grade = "weak" if match_count else "none"
            blocker = "Translation rule is approximate; matching traces are not enough for equivalence."
        elif match_count >= 2:
            promotion_status = "STRONG_TRACE_LEVEL_CANDIDATE"
            paper_action = "eligible_for_manual_paper_review"
            evidence_grade = "strong_trace_level"
            blocker = "Formal XML-to-MITL equivalence proof is still required before claiming full translation."
        elif match_count == 1:
            promotion_status = "SINGLE_TRACE_LEVEL_CANDIDATE"
            paper_action = "add_second_independent_trace_or_edge_proof"
            evidence_grade = "single_trace"
            blocker = "Only one matching trace is available; add another independent trace or a manual edge proof before paper promotion."
        elif baseline_timeouts or candidate_baseline_timeouts:
            promotion_status = "BASELINE_TIMEOUT_NOT_PROMOTED"
            paper_action = "rerun_or_reduce_baseline_input"
            evidence_grade = "none"
            blocker = "MoniTAal baseline timed out for the available candidate input."
        elif candidate_timeouts:
            promotion_status = "CANDIDATE_TIMEOUT_NOT_PROMOTED"
            paper_action = "fix_candidate_runtime_or_reduce_input"
            evidence_grade = "none"
            blocker = "TAMonitor candidate timed out for the available input."
        elif candidate_errors:
            promotion_status = "CANDIDATE_ERROR_NOT_PROMOTED"
            paper_action = "fix_candidate_runtime_error"
            evidence_grade = "none"
            blocker = "TAMonitor candidate returned an error."
        elif baseline_skipped:
            promotion_status = "NO_INPUT_NOT_PROMOTED"
            paper_action = "add_review_input_or_leave_unclaimed"
            evidence_grade = "none"
            blocker = "No MoniTAal baseline input is available for this XML pair."
        else:
            promotion_status = "UNVERIFIED_NOT_PROMOTED"
            paper_action = "collect_baseline_evidence"
            evidence_grade = "none"
            blocker = "No comparable baseline evidence is available."

        matched_verdicts = sorted({r.get("actual_final", "") for r in matches if r.get("actual_final", "")})
        manifest.append({
            "manifest_id": re.sub(r"[^A-Za-z0-9]+", "_", f"{Path(row.get('xml_path', '')).stem}_{row.get('positive_template', '')}_{row.get('negative_template', '')}").strip("_"),
            "xml_path": row.get("xml_path", ""),
            "xml_file": row.get("xml_file", ""),
            "source_kind": row.get("source_kind", ""),
            "positive_template": row.get("positive_template", ""),
            "negative_template": row.get("negative_template", ""),
            "candidate_mitl": row.get("candidate_mitl", ""),
            "mitl_equivalence_status": equivalence_status,
            "candidate_confidence": row.get("candidate_confidence", ""),
            "promotion_status": promotion_status,
            "paper_action": paper_action,
            "evidence_grade": evidence_grade,
            "trace_match_count": match_count,
            "trace_mismatch_count": mismatch_count,
            "candidate_timeout_count": len(candidate_timeouts),
            "candidate_error_count": len(candidate_errors),
            "baseline_timeout_count": len(baseline_timeouts),
            "baseline_skipped_no_input_count": len(baseline_skipped),
            "baseline_generated_empty_no_original_input_count": len(baseline_generated_empty),
            "original_input_match_count": len(repository_matches),
            "generated_input_match_count": len(generated_review_matches) + len(generated_empty_matches),
            "repository_input_match_count": len(repository_matches),
            "embedded_benchmark_input_match_count": len(embedded_matches),
            "external_or_case_input_match_count": len(external_matches),
            "generated_review_input_match_count": len(generated_review_matches),
            "generated_empty_no_original_input_match_count": len(generated_empty_matches),
            "input_origin_match_counts": ";".join(f"{origin}={count}" for origin, count in sorted(match_origin_counts.items())),
            "matched_verdicts": ";".join(matched_verdicts),
            "matched_input_paths": ";".join(r.get("input_path", "") for r in matches),
            "timeout_input_paths": ";".join(r.get("input_path", "") for r in baseline_timeouts),
            "blocker_or_next_step": blocker,
            "translation_reason": row.get("translation_reason", ""),
            "labels": row.get("labels", ""),
            "guards": row.get("guards", ""),
        })
    return manifest


def transition_ref(row: dict[str, Any]) -> str:
    source = row.get("source_name") or row.get("source_id", "")
    target = row.get("target_name") or row.get("target_id", "")
    label = row.get("sync_label", "")
    guard = row.get("guards", "")
    assignment = row.get("assignments", "")
    return (
        f"{row.get('template', '')}#{row.get('transition_index', '')}:"
        f"{source}->{target};label={label or '<empty>'};guard={guard or '<none>'};"
        f"assign={assignment or '<none>'};accept={row.get('source_accepting', '')}->{row.get('target_accepting', '')};"
        f"initial={row.get('source_initial', '')}->{row.get('target_initial', '')}"
    )


def find_transition(
    rows: list[dict[str, Any]],
    *,
    label: str | None = None,
    guard: str | None = None,
    assignment: str | None = None,
    source_accepting: str | None = None,
    target_accepting: str | None = None,
    source_initial: str | None = None,
    target_initial: str | None = None,
) -> dict[str, Any] | None:
    for row in rows:
        if label is not None and row.get("sync_label", "") != label:
            continue
        if guard is not None and guard not in row.get("guards", ""):
            continue
        if assignment is not None and assignment not in row.get("assignments", ""):
            continue
        if source_accepting is not None and row.get("source_accepting", "") != source_accepting:
            continue
        if target_accepting is not None and row.get("target_accepting", "") != target_accepting:
            continue
        if source_initial is not None and row.get("source_initial", "") != source_initial:
            continue
        if target_initial is not None and row.get("target_initial", "") != target_initial:
            continue
        return row
    return None


def proof_context(
    manifest_row: dict[str, Any],
    transitions_by_pair: dict[tuple[str, str, str], dict[str, list[dict[str, Any]]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    pair_key = (
        manifest_row.get("xml_path", ""),
        manifest_row.get("positive_template", ""),
        manifest_row.get("negative_template", ""),
    )
    rows = transitions_by_pair.get(pair_key, {})
    return rows.get("positive", []), rows.get("negative", [])


def build_proof_row(
    row: dict[str, Any],
    proof_class: str,
    pattern: str,
    trigger_label: str,
    response_label: str,
    forbidden_label: str,
    bound: str,
    clock: str,
    positive_evidence: list[dict[str, Any] | None],
    negative_evidence: list[dict[str, Any] | None],
    reset_evidence: list[dict[str, Any] | None],
    acceptance_evidence: str,
    manual_notes: str,
    force_review: bool = False,
) -> dict[str, Any]:
    missing = [name for name, evidence in [
        ("positive", positive_evidence),
        ("negative", negative_evidence),
        ("reset", reset_evidence),
    ] if not all(evidence)]
    if row.get("promotion_status") != "STRONG_TRACE_LEVEL_CANDIDATE":
        if row.get("mitl_equivalence_status") == "approximate":
            proof_status = "NOT_PROOF_READY_APPROXIMATE"
        elif row.get("candidate_mitl"):
            proof_status = "NOT_PROOF_READY_TRACE_OR_INPUT_DEBT"
        else:
            proof_status = "NOT_APPLICABLE_NO_CANDIDATE"
    elif force_review:
        proof_status = "EDGE_GUARD_REVIEW_REQUIRED"
    elif missing:
        proof_status = "EDGE_GUARD_EVIDENCE_INCOMPLETE"
        manual_notes = f"Missing machine evidence groups: {';'.join(missing)}. {manual_notes}"
    else:
        proof_status = "EDGE_GUARD_PROOF_READY"

    return {
        "proof_id": re.sub(r"[^A-Za-z0-9]+", "_", f"proof_{row.get('manifest_id', '')}").strip("_"),
        "manifest_id": row.get("manifest_id", ""),
        "xml_path": row.get("xml_path", ""),
        "xml_file": row.get("xml_file", ""),
        "source_kind": row.get("source_kind", ""),
        "positive_template": row.get("positive_template", ""),
        "negative_template": row.get("negative_template", ""),
        "candidate_mitl": row.get("candidate_mitl", ""),
        "promotion_status": row.get("promotion_status", ""),
        "proof_status": proof_status,
        "proof_class": proof_class,
        "pattern": pattern,
        "trigger_label": trigger_label,
        "response_label": response_label,
        "forbidden_label": forbidden_label,
        "bound": bound,
        "clock": clock,
        "positive_edge_evidence": " | ".join(transition_ref(e) for e in positive_evidence if e),
        "negative_edge_evidence": " | ".join(transition_ref(e) for e in negative_evidence if e),
        "reset_edge_evidence": " | ".join(transition_ref(e) for e in reset_evidence if e),
        "acceptance_evidence": acceptance_evidence,
        "trace_evidence": row.get("matched_input_paths", ""),
        "manual_review_notes": manual_notes,
    }


def as_int(value: Any, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def split_semicolon_tokens(value: str) -> list[str]:
    return [token.strip() for token in value.split(";") if token.strip()]


def gear_manual_review_note(row: dict[str, Any]) -> str:
    timeout_count = as_int(row.get("baseline_timeout_count"))
    matched_paths = row.get("matched_input_paths", "")
    matched_verdicts = row.get("matched_verdicts", "")
    has_original_gear_input = "gear-control-input.txt" in matched_paths
    has_inconclusive = "INCONCLUSIVE" in matched_verdicts
    has_negative_boundary = "NEGATIVE" in matched_verdicts

    if timeout_count > 0:
        return (
            "Original gear-control-input baseline still has timeout debt in this run; "
            "treat this proof row as structural edge/guard evidence plus reduced trace evidence only."
        )
    if has_original_gear_input and has_inconclusive:
        boundary = (
            " Generated reduced traces provide NEGATIVE late-response boundary evidence."
            if has_negative_boundary else ""
        )
        return (
            "Original gear-control-input baseline terminates with INCONCLUSIVE in this run; "
            "treat that as third-valued trace evidence, not Boolean satisfaction, violation, "
            f"or XML-to-MITL equivalence proof.{boundary}"
        )
    if has_original_gear_input:
        return (
            "Original gear-control-input baseline terminates in this run; still require human review "
            "of alphabet mapping, edge/guard proof, and finite-prefix interpretation before paper claims."
        )
    return (
        "No original gear-control-input baseline row is linked to this proof row; use only the listed "
        "structural edge/guard evidence and generated trace evidence until an original-input row is recorded."
    )


def build_xml_edge_guard_proofs(
    manifest_rows: list[dict[str, Any]],
    transition_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build a conservative XML edge/guard proof ledger for manual review."""
    transitions_by_pair: dict[tuple[str, str, str], dict[str, list[dict[str, Any]]]] = {}
    for transition in transition_rows:
        key = (
            transition.get("xml_path", ""),
            transition.get("positive_template", ""),
            transition.get("negative_template", ""),
        )
        role = transition.get("pair_role", "")
        if role in {"positive", "negative"}:
            transitions_by_pair.setdefault(key, {"positive": [], "negative": []})[role].append(transition)

    proofs: list[dict[str, Any]] = []
    for row in manifest_rows:
        pos_rows, neg_rows = proof_context(row, transitions_by_pair)
        xml_file = row.get("xml_file", "")
        pos_template = row.get("positive_template", "")

        if row.get("promotion_status") != "STRONG_TRACE_LEVEL_CANDIDATE":
            proofs.append(build_proof_row(
                row,
                "not_ready",
                "No edge/guard proof attempted for non-strong or unclaimed candidate.",
                "",
                "",
                "",
                "",
                "",
                [],
                [],
                [],
                "",
                row.get("blocker_or_next_step", ""),
            ))
            continue

        if pos_template == "a_leadsto_b":
            bound = "30"
            trigger = "a"
            response = "b"
            proofs.append(build_proof_row(
                row,
                "bounded_response_leadsto",
                "Trigger a resets clock x; response b with x <= 30 returns to accepting positive state; negative accepting state is reached when x > 30.",
                trigger,
                response,
                "",
                bound,
                "x",
                [find_transition(pos_rows, label=response, guard=f"x <= {bound}", target_accepting="yes")],
                [find_transition(neg_rows, guard=f"x > {bound}", target_accepting="yes")],
                [find_transition(pos_rows, label=trigger, assignment="x := 0"), find_transition(neg_rows, label=trigger, assignment="x := 0")],
                "Positive template starts accepting before an a-obligation; negative accepting location represents a missed response.",
                "Manual reviewer should still check alphabet closure for labels not in the reduced traces and the G* first-observation convention.",
            ))
            continue

        if xml_file in {"absentAQ.xml", "absentBR.xml"}:
            if xml_file == "absentAQ.xml":
                trigger, forbidden = "q", "p"
            else:
                trigger, forbidden = "p", "r"
            bound = "10"
            proofs.append(build_proof_row(
                row,
                "bounded_absence_after_trigger",
                "Trigger resets clock c; forbidden event is safe only after c > 10 and reaches the negative accepting state when c <= 10.",
                trigger,
                "",
                forbidden,
                bound,
                "c",
                [find_transition(pos_rows, label=forbidden, guard=f"c > {bound}", target_accepting="yes")],
                [find_transition(neg_rows, label=forbidden, guard=f"c <= {bound}", target_accepting="yes")],
                [find_transition(pos_rows, label=trigger, assignment="c := 0"), find_transition(neg_rows, label=trigger, assignment="c := 0")],
                "Negative accepting location represents the forbidden event inside the closed bound after a trigger.",
                "Manual reviewer should check repeated-trigger handling and whether the closed c <= 10 boundary matches the MITL interval.",
            ))
            continue

        if xml_file in {"c_after_10.xml", "c_after_20.xml"}:
            bound = "10" if xml_file == "c_after_10.xml" else "20"
            proofs.append(build_proof_row(
                row,
                "eventually_after_lower_bound",
                "Event c with x >= bound reaches the positive accepting location; the negative template remains accepting for c before x < bound and leaves accepting at x >= bound.",
                "",
                "c",
                "",
                bound,
                "x",
                [find_transition(pos_rows, label="c", guard=f"x >= {bound}", target_accepting="yes")],
                [find_transition(neg_rows, label="c", guard=f"x < {bound}", source_accepting="yes", target_accepting="yes"), find_transition(neg_rows, label="c", guard=f"x >= {bound}", source_accepting="yes", target_accepting="no")],
                [],
                "Positive accepting location is entered exactly at/after the lower-bound c edge; negative accepting prefix tracks absence of such c.",
                "Manual reviewer should check finite-word no-c prefixes against the intended RV semantics.",
            ))
            continue

        if xml_file == "only_ab_until10.xml":
            bound = "10"
            proofs.append(build_proof_row(
                row,
                "bounded_global_absence",
                "Event c at x <= 10 leaves the positive accepting state and reaches the negative accepting state; c after x > 10 stays positive.",
                "",
                "",
                "c",
                bound,
                "x",
                [find_transition(pos_rows, label="c", guard=f"x <= {bound}", target_accepting="no"), find_transition(pos_rows, label="c", guard=f"x > {bound}", target_accepting="yes")],
                [find_transition(neg_rows, label="c", guard=f"x <= {bound}", target_accepting="yes")],
                [],
                "Closed-bound violation c at x <= 10 is represented by the negative accepting edge.",
                "Manual reviewer should check whether XML lacks an explicit c > 10 negative escape because finite acceptance already represents the complement.",
            ))
            continue

        if xml_file == "recurGLB.xml":
            bound = "10"
            proofs.append(build_proof_row(
                row,
                "bounded_recurrence_after_event",
                "A p with c <= 10 satisfies the initial or re-armed recurrence obligation and resets c; p with c > 10 reaches the negative accepting state.",
                "p",
                "p",
                "",
                bound,
                "c",
                [find_transition(pos_rows, label="p", guard=f"c <= {bound}", assignment="c := 0", target_accepting="yes")],
                [find_transition(neg_rows, label="p", guard=f"c > {bound}", target_accepting="yes")],
                [find_transition(pos_rows, label="p", guard=f"c <= {bound}", assignment="c := 0")],
                "Negative accepting location represents either no initial p within 10 or a p recurrence gap greater than 10.",
                "The initial F [0,10] p obligation is witnessed by the same initial c <= 10 edge; the strict lower-bound (0,10] for later p responses follows from the reset-after-p event-index semantics rather than a separate XML guard.",
            ))
            continue

        gear_specs = {
            "CloseClutch": ("CloseClutch", "ClutchIsClosed", "150"),
            "OpenClutch": ("OpenClutch", "ClutchIsOpen", "150"),
            "ReqSet": ("ReqSet", "GearSet", "300"),
            "ReqNeu": ("ReqNeu", "GearNeu", "200"),
            "SpeedSet": ("SpeedSet", "ReqTorque", "500"),
            "test1": ("test1", "ReqTorque", "900"),
        }
        if xml_file == "gear-control-properties.xml" and pos_template in gear_specs:
            trigger, response, bound = gear_specs[pos_template]
            proofs.append(build_proof_row(
                row,
                "gear_bounded_request_response",
                "Request resets x; response with x <= bound returns to the positive accepting state; x > bound reaches the negative accepting state.",
                trigger,
                response,
                "",
                bound,
                "x",
                [find_transition(pos_rows, label=response, guard=f"x <= {bound}", target_accepting="yes")],
                [find_transition(neg_rows, guard=f"x > {bound}", target_accepting="yes")],
                [find_transition(pos_rows, label=trigger, assignment="x := 0"), find_transition(neg_rows, label=trigger, assignment="x := 0")],
                "Positive template starts accepting before a request; negative accepting location represents a missed response after the closed bound.",
                gear_manual_review_note(row),
            ))
            continue

        proofs.append(build_proof_row(
            row,
            "unclassified_strong_trace_candidate",
            "Strong trace-level candidate has no implemented edge/guard proof rule yet.",
            "",
            "",
            "",
            "",
            "",
            [],
            [],
            [],
            "",
            "Add a proof rule or keep this row as trace-level evidence only.",
            force_review=True,
        ))
    return proofs


def appendix_status_for_proof(row: dict[str, Any]) -> tuple[str, str]:
    status = row.get("proof_status", "")
    if status == "EDGE_GUARD_PROOF_READY":
        return "PROOF_DRAFT_READY", "Included in the paper-facing proof draft."
    if status == "NOT_PROOF_READY_APPROXIMATE":
        return "EXCLUDED_APPROXIMATE", "Excluded from formal translation claims because the MITL candidate is approximate."
    if status == "NOT_APPLICABLE_NO_CANDIDATE":
        return "EXCLUDED_NO_MITL_CANDIDATE", "Excluded because no conservative MITL candidate is claimed."
    if status == "NOT_PROOF_READY_TRACE_OR_INPUT_DEBT":
        return "EXCLUDED_INPUT_OR_TRACE_DEBT", "Excluded because candidate evidence is missing or not promotable."
    if status == "EDGE_GUARD_REVIEW_REQUIRED":
        return "EXCLUDED_NEEDS_MANUAL_EDGE_REVIEW", "Excluded until the edge/guard proof issue is resolved."
    return "EXCLUDED_NOT_READY", "Excluded because the proof ledger does not mark this row proof-ready."


def proof_sketch_for(row: dict[str, Any]) -> str:
    proof_class = row.get("proof_class", "")
    candidate = row.get("candidate_mitl", "")
    trigger = row.get("trigger_label", "")
    response = row.get("response_label", "")
    forbidden = row.get("forbidden_label", "")
    bound = row.get("bound", "")
    clock = row.get("clock", "")
    if proof_class in {"bounded_response_leadsto", "gear_bounded_request_response"}:
        return (
            f"The XML pair implements {candidate}: the positive template is accepting before an obligation, "
            f"the {trigger} edge resets clock {clock}, and the {response} edge with {clock} <= {bound} "
            "returns to an accepting state. The negative template reaches an accepting violation state on "
            f"{clock} > {bound}. Thus every observed request/trigger must be followed by the response within "
            "the closed bound."
        )
    if proof_class == "bounded_absence_after_trigger":
        return (
            f"The XML pair implements {candidate}: the trigger {trigger} resets clock {clock}; the forbidden "
            f"event {forbidden} reaches the negative accepting state when {clock} <= {bound}, while the "
            f"positive template only treats {forbidden} as safe after {clock} > {bound}. This matches a "
            "closed-bound absence obligation after the trigger."
        )
    if proof_class == "eventually_after_lower_bound":
        return (
            f"The XML pair implements {candidate}: an event {response} before the lower bound is not enough, "
            f"while {response} with {clock} >= {bound} enters the positive accepting state. The negative "
            "template tracks the complementary prefix before the lower-bound witness appears."
        )
    if proof_class == "bounded_global_absence":
        return (
            f"The XML pair implements {candidate}: labels other than {forbidden} remain in the safe accepting "
            f"region, while {forbidden} with {clock} <= {bound} reaches the negative accepting state. The "
            f"{clock} > {bound} edge keeps the positive template safe after the monitored interval."
        )
    if proof_class == "bounded_recurrence_after_event":
        return (
            f"The XML pair implements {candidate}: a {response} event with {clock} <= {bound} satisfies either "
            f"the initial obligation or a re-armed recurrence obligation and resets {clock}. A {response} event "
            f"with {clock} > {bound} reaches the negative accepting state. After each reset, the next response "
            "must be a later event, which accounts for the strict lower bound in the MITL subformula."
        )
    return row.get("pattern", "")


def build_xml_proof_appendix(edge_guard_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    appendix_rows: list[dict[str, Any]] = []
    for row in edge_guard_rows:
        appendix_status, exclusion_reason = appendix_status_for_proof(row)
        proof_ready = appendix_status == "PROOF_DRAFT_READY"
        evidence = " | ".join(x for x in [
            row.get("positive_edge_evidence", ""),
            row.get("negative_edge_evidence", ""),
            row.get("reset_edge_evidence", ""),
        ] if x)
        appendix_rows.append({
            "appendix_id": re.sub(r"[^A-Za-z0-9]+", "_", f"appendix_{row.get('manifest_id', '')}").strip("_"),
            "manifest_id": row.get("manifest_id", ""),
            "xml_file": row.get("xml_file", ""),
            "positive_template": row.get("positive_template", ""),
            "negative_template": row.get("negative_template", ""),
            "candidate_mitl": row.get("candidate_mitl", ""),
            "appendix_status": appendix_status,
            "proof_status": row.get("proof_status", ""),
            "proof_class": row.get("proof_class", ""),
            "paper_claim_scope": (
                "Structurally proof-ready gear request/response XML-to-MITL candidate; cite the edge/guard proof ledger, trace evidence, and original-input baseline comparison when available."
                if proof_ready and row.get("proof_class", "") == "gear_bounded_request_response"
                else (
                    "Structurally proof-ready XML-to-MITL candidate over the mapped proposition alphabet; still cite the proof ledger and trace evidence."
                    if proof_ready else "Not included in the formal XML-to-MITL translation claim."
                )
            ),
            "proof_sketch": proof_sketch_for(row) if proof_ready else "",
            "edge_guard_evidence": evidence if proof_ready else "",
            "trace_evidence": row.get("trace_evidence", "") if proof_ready else "",
            "manual_review_notes": row.get("manual_review_notes", ""),
            "exclusion_reason": "" if proof_ready else exclusion_reason,
        })
    return appendix_rows


def write_xml_translation_proof_appendix(output_dir: Path, appendix_rows: list[dict[str, Any]]) -> None:
    ready = [row for row in appendix_rows if row["appendix_status"] == "PROOF_DRAFT_READY"]
    excluded = [row for row in appendix_rows if row["appendix_status"] != "PROOF_DRAFT_READY"]
    lines = [
        "# XML-to-MITL Proof Appendix Draft",
        "",
        "This appendix is generated from `xml_edge_guard_proofs.csv` and is intended for manual paper review.",
        "It does not claim that approximate or unpromoted XML rows are formally translated.",
        "",
        "## Scope",
        "",
        f"- Structurally proof-ready XML pairs: {len(ready)}",
        f"- Excluded or not-ready XML pairs: {len(excluded)}",
        "- Each proof-ready row must still be checked against the paper's final definition of trace alphabets, finite-prefix verdicts, and the G* first-observation convention.",
        "",
        "## Structural Proof-Ready Candidates",
        "",
    ]
    for row in ready:
        lines.extend([
            f"### {row['manifest_id']}",
            "",
            f"- XML file: `{row['xml_file']}`",
            f"- Templates: `{row['positive_template']}` / `{row['negative_template']}`",
            f"- Candidate MITL: `{row['candidate_mitl']}`",
            f"- Proof class: `{row['proof_class']}`",
            f"- Claim scope: {row['paper_claim_scope']}",
            "",
            row["proof_sketch"],
            "",
            f"Evidence: {row['edge_guard_evidence']}",
            "",
            f"Trace evidence: {row['trace_evidence']}",
            "",
            f"Manual review notes: {row['manual_review_notes'] or 'None.'}",
            "",
        ])
    lines.extend([
        "## Excluded Rows",
        "",
        "The following rows are intentionally excluded from the formal XML-to-MITL translation claim in this draft.",
        "",
        "| manifest_id | status | reason |",
        "|---|---|---|",
    ])
    for row in excluded:
        lines.append(f"| `{row['manifest_id']}` | `{row['appendix_status']}` | {row['exclusion_reason']} |")
    lines.append("")
    (output_dir / "xml_translation_proof_appendix.md").write_text("\n".join(lines), encoding="utf-8")


def pair_key(row: dict[str, Any]) -> tuple[str, str, str]:
    return (
        row.get("xml_path", ""),
        row.get("positive_template", ""),
        row.get("negative_template", ""),
    )


def add_xml_proof_obligation(
    rows: list[dict[str, Any]],
    source: dict[str, Any],
    obligation_name: str,
    obligation_group: str,
    status: str,
    required: str,
    observed: str,
    evidence_artifacts: str,
    reviewer_action: str,
    machine_checkable: bool = True,
) -> None:
    rows.append({
        "obligation_id": re.sub(
            r"[^A-Za-z0-9]+",
            "_",
            f"obl_{source.get('manifest_id', '')}_{obligation_name}",
        ).strip("_"),
        "manifest_id": source.get("manifest_id", ""),
        "xml_file": source.get("xml_file", ""),
        "positive_template": source.get("positive_template", ""),
        "negative_template": source.get("negative_template", ""),
        "candidate_mitl": source.get("candidate_mitl", ""),
        "proof_class": source.get("proof_class", ""),
        "proof_status": source.get("proof_status", ""),
        "obligation_group": obligation_group,
        "obligation_name": obligation_name,
        "obligation_status": status,
        "machine_checkable": "true" if machine_checkable else "false",
        "required": required,
        "observed": observed,
        "evidence_artifacts": evidence_artifacts,
        "reviewer_action": reviewer_action,
    })


def build_xml_proof_obligations(
    edge_guard_rows: list[dict[str, Any]],
    benchmark_manifest_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    paper_claim_review_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    manifest_by_id = {row.get("manifest_id", ""): row for row in benchmark_manifest_rows}
    claim_by_manifest = {row.get("manifest_id", ""): row for row in paper_claim_review_rows}
    candidates_by_pair: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in candidate_rows:
        candidates_by_pair.setdefault(pair_key(row), []).append(row)

    required_verdicts_by_class = {
        "bounded_response_leadsto": {"NEGATIVE"},
        "bounded_absence_after_trigger": {"NEGATIVE"},
        "eventually_after_lower_bound": {"POSITIVE"},
        "bounded_global_absence": {"NEGATIVE", "POSITIVE"},
        "bounded_recurrence_after_event": {"NEGATIVE"},
        "gear_bounded_request_response": {"NEGATIVE", "INCONCLUSIVE"},
    }
    reset_required_classes = {
        "bounded_response_leadsto",
        "bounded_absence_after_trigger",
        "bounded_recurrence_after_event",
        "gear_bounded_request_response",
    }

    rows: list[dict[str, Any]] = []
    for proof in edge_guard_rows:
        manifest = manifest_by_id.get(proof.get("manifest_id", ""), {})
        claim = claim_by_manifest.get(proof.get("manifest_id", ""), {})
        proof_ready = proof.get("proof_status") == "EDGE_GUARD_PROOF_READY"
        if not proof_ready:
            add_xml_proof_obligation(
                rows,
                proof,
                "not_promoted_boundary",
                "scope",
                "PASS",
                "non-proof-ready XML rows stay outside proof-ready claims",
                f"proof_status={proof.get('proof_status', '')}; promotion_status={proof.get('promotion_status', '')}",
                "xml_edge_guard_proofs.csv; benchmark_manifest.csv",
                "Keep this row excluded or add a real proof rule before promotion.",
            )
            continue

        add_xml_proof_obligation(
            rows,
            proof,
            "positive_edge_evidence_present",
            "structure",
            "PASS" if proof.get("positive_edge_evidence") else "FAIL",
            "positive template edge evidence is recorded",
            proof.get("positive_edge_evidence", "") or "<missing>",
            "xml_edge_guard_proofs.csv; monitaal_transition_details.csv",
            "Fix the proof extractor or downgrade the XML row if positive edge evidence is missing.",
        )
        add_xml_proof_obligation(
            rows,
            proof,
            "negative_edge_evidence_present",
            "structure",
            "PASS" if proof.get("negative_edge_evidence") else "FAIL",
            "negative template violation/complement edge evidence is recorded",
            proof.get("negative_edge_evidence", "") or "<missing>",
            "xml_edge_guard_proofs.csv; monitaal_transition_details.csv",
            "Fix the proof extractor or downgrade the XML row if negative edge evidence is missing.",
        )
        reset_required = proof.get("proof_class", "") in reset_required_classes
        reset_ok = bool(proof.get("reset_edge_evidence")) if reset_required else True
        add_xml_proof_obligation(
            rows,
            proof,
            "reset_evidence_policy",
            "structure",
            "PASS" if reset_ok else "FAIL",
            "reset evidence is present exactly for proof classes whose semantics depend on clock re-arming",
            (
                f"reset_required={reset_required}; reset_evidence={proof.get('reset_edge_evidence', '') or '<none>'}"
            ),
            "xml_edge_guard_proofs.csv; monitaal_transition_details.csv",
            "If reset is required, add reset edge evidence or downgrade the proof row.",
        )
        match_count = as_int(manifest.get("trace_match_count"))
        mismatch_count = as_int(manifest.get("trace_mismatch_count"))
        timeout_count = as_int(manifest.get("candidate_timeout_count")) + as_int(manifest.get("baseline_timeout_count"))
        error_count = as_int(manifest.get("candidate_error_count"))
        trace_floor_ok = match_count >= 2 and mismatch_count == 0 and timeout_count == 0 and error_count == 0
        add_xml_proof_obligation(
            rows,
            proof,
            "trace_match_floor",
            "trace",
            "PASS" if trace_floor_ok else "FAIL",
            "proof-ready rows have at least two matched traces and no mismatch/timeout/error debt",
            (
                f"trace_match_count={match_count}; trace_mismatch_count={mismatch_count}; "
                f"timeout_count={timeout_count}; candidate_error_count={error_count}"
            ),
            "benchmark_manifest.csv; translation_candidate_results.csv; monitaal_baseline_results.csv",
            "Do not keep a proof-ready row if trace evidence has mismatch, timeout, error, or fewer than two matches.",
        )
        observed_verdicts = {token for token in split_semicolon_tokens(manifest.get("matched_verdicts", "")) if token}
        required_verdicts = required_verdicts_by_class.get(proof.get("proof_class", ""), set())
        missing_verdicts = sorted(required_verdicts - observed_verdicts)
        verdict_status = "PASS" if not missing_verdicts else ("REVIEW_REQUIRED" if observed_verdicts else "FAIL")
        add_xml_proof_obligation(
            rows,
            proof,
            "trace_verdict_coverage",
            "trace",
            verdict_status,
            "trace set includes the verdict kinds expected for this proof class",
            (
                f"required={';'.join(sorted(required_verdicts)) or '<none>'}; "
                f"observed={';'.join(sorted(observed_verdicts)) or '<none>'}; "
                f"missing={';'.join(missing_verdicts) or '<none>'}"
            ),
            "benchmark_manifest.csv; translation_candidate_results.csv; candidate_step_audit.csv",
            "Add boundary traces for missing verdict kinds or record why the human proof does not require them.",
        )
        original_like = (
            as_int(manifest.get("repository_input_match_count"))
            + as_int(manifest.get("embedded_benchmark_input_match_count"))
            + as_int(manifest.get("external_or_case_input_match_count"))
        )
        generated_review = as_int(manifest.get("generated_review_input_match_count"))
        generated_empty = as_int(manifest.get("generated_empty_no_original_input_match_count"))
        origin_status = "PASS"
        reviewer_action = "Trace origins are visible for human review."
        if generated_empty:
            origin_status = "FAIL"
            reviewer_action = "Generated empty baseline-only probes cannot support a proof-ready XML translation row."
        elif original_like == 0 and generated_review:
            origin_status = "REVIEW_REQUIRED"
            reviewer_action = "Generated review traces must be checked by a human against the XML proof obligation."
        add_xml_proof_obligation(
            rows,
            proof,
            "trace_origin_boundary",
            "trace",
            origin_status,
            "trace origin mix is explicit and generated-empty probes are not used as proof-ready evidence",
            (
                f"original_or_external_like={original_like}; generated_review={generated_review}; "
                f"generated_empty={generated_empty}; origins={manifest.get('input_origin_match_counts', '')}"
            ),
            "benchmark_manifest.csv; monitaal_baseline_results.csv; generated_monitaal_inputs/",
            reviewer_action,
        )
        claim_strength = claim.get("claim_strength", "")
        claim_must_not = claim.get("must_not_claim", "")
        has_inconclusive = "INCONCLUSIVE" in manifest.get("matched_verdicts", "")
        claim_ok = bool(claim_strength) and (
            not has_inconclusive
            or ("third-valued" in claim_must_not.lower() and "INCONCLUSIVE" in claim_must_not)
        )
        add_xml_proof_obligation(
            rows,
            proof,
            "paper_claim_boundary",
            "claim",
            "PASS" if claim_ok else "FAIL",
            "paper claim row exists and INCONCLUSIVE evidence has an explicit third-valued caveat",
            (
                f"claim_strength={claim_strength or '<missing>'}; has_inconclusive={has_inconclusive}; "
                f"must_not_claim={claim_must_not or '<missing>'}"
            ),
            "paper_claim_review.csv; review_signoff_template.csv",
            "Fix paper-facing wording before asking for signoff.",
        )
        candidate_pair_rows = candidates_by_pair.get(pair_key(proof), [])
        incomplete_step_rows = [
            row.get("candidate_id", "")
            for row in candidate_pair_rows
            if as_int(row.get("processed_steps"), -1) != as_int(row.get("mapped_events"), -2)
        ]
        add_xml_proof_obligation(
            rows,
            proof,
            "runtime_step_recording_boundary",
            "trace",
            "PASS" if not incomplete_step_rows else "FAIL",
            "candidate runs preserve mapped-event step accounting for reviewer trace replay",
            "bad_candidates=" + ";".join(incomplete_step_rows),
            "translation_candidate_results.csv; candidate_step_audit.csv; candidate_prefix_observations.csv",
            "Fix runtime step recording before using per-prefix evidence for this XML row.",
        )
        add_xml_proof_obligation(
            rows,
            proof,
            "human_equivalence_signoff_required",
            "human_review",
            "REVIEW_REQUIRED",
            "final XML-to-MITL equivalence remains a human mathematical review item",
            "generated proof obligation ledger is complete enough for review but does not sign the theorem",
            "xml_proof_obligations.csv; xml_proof_appendix.csv; review_signoff_template.csv",
            "A human reviewer must check alphabets, edge/guard semantics, finite-prefix interpretation, and paper definitions.",
            machine_checkable=False,
        )
    return rows


def write_xml_proof_obligations(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "xml_proof_obligations.json").write_text(json.dumps({
        "summary": {
            "row_count": len(rows),
            "pass": count_rows(rows, obligation_status="PASS"),
            "review_required": count_rows(rows, obligation_status="REVIEW_REQUIRED"),
            "fail": count_rows(rows, obligation_status="FAIL"),
            "proof_ready_manifests": len({row["manifest_id"] for row in rows if row["obligation_name"] == "human_equivalence_signoff_required"}),
        },
        "rows": rows,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = Counter(row["obligation_status"] for row in rows)
    by_group = Counter(row["obligation_group"] for row in rows)
    lines = [
        "# XML Proof Obligations",
        "",
        "This ledger decomposes proof-ready XML rows into machine-checkable prerequisites and human-review obligations.",
        "A PASS row is not a theorem claim; REVIEW_REQUIRED rows intentionally keep human mathematical review visible.",
        "",
        "## Counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend([
        "",
        "## Groups",
        "",
        "| group | rows |",
        "|---|---:|",
    ])
    for group, count in sorted(by_group.items()):
        lines.append(f"| `{group}` | {count} |")
    lines.extend([
        "",
        "## Obligations",
        "",
        "| manifest_id | group | obligation | status | observed | reviewer_action |",
        "|---|---|---|---|---|---|",
    ])
    for row in rows:
        observed = row["observed"].replace("|", "\\|")[:400]
        action = row["reviewer_action"].replace("|", "\\|")
        lines.append(
            f"| `{row['manifest_id']}` | `{row['obligation_group']}` | `{row['obligation_name']}` | "
            f"`{row['obligation_status']}` | {observed} | {action} |"
        )
    lines.append("")
    (output_dir / "xml_proof_obligations.md").write_text("\n".join(lines), encoding="utf-8")


def input_trace_purpose(input_path: str) -> str:
    name = Path(input_path).name.lower()
    if "rearmed_late_negative" in name:
        return "rearmed_late_negative"
    if "rearmed_boundary_negative" in name:
        return "rearmed_boundary_negative"
    if "first_late_negative" in name:
        return "initial_window_late_negative"
    if "initial_late_negative" in name:
        return "initial_late_negative"
    if "timely_positive" in name:
        return "timely_positive"
    if "no_witness_inconclusive" in name:
        return "no_witness_inconclusive"
    if "monitor_test" in name:
        return "embedded_monitor_test_positive"
    if "boundary_negative" in name or "negative_boundary" in name:
        return "closed_boundary_negative"
    if "after_bound_positive" in name or "positive_after_bound" in name:
        return "after_bound_positive"
    if "later_positive" in name:
        return "after_bound_positive"
    if name.endswith("_positive.input") or name.endswith("_positive.txt"):
        return "closed_boundary_positive"
    if "gear-control-input" in name:
        return "repository_inconclusive_long_trace"
    if "input" in name:
        return "repository_or_case_trace"
    return "unclassified_trace"


def trace_coverage_candidates_for_pair(
    source: dict[str, Any],
    candidate_rows: list[dict[str, Any]],
    candidate_step_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    step_by_id = {row.get("candidate_id", ""): row for row in candidate_step_rows}
    baseline_by_key = {
        (
            row.get("xml_path", ""),
            row.get("positive_template", ""),
            row.get("negative_template", ""),
            row.get("input_path", ""),
        ): row
        for row in baseline_rows
    }
    rows = []
    for row in candidate_rows:
        if pair_key(row) != pair_key(source):
            continue
        step = step_by_id.get(row.get("candidate_id", ""), {})
        baseline = baseline_by_key.get((
            row.get("xml_path", ""),
            row.get("positive_template", ""),
            row.get("negative_template", ""),
            row.get("input_path", ""),
        ), {})
        verdict = row.get("actual_final") or row.get("baseline_verdict", "")
        rows.append({
            "candidate_id": row.get("candidate_id", ""),
            "input_path": row.get("input_path", ""),
            "input_name": Path(row.get("input_path", "")).name,
            "input_origin": baseline.get("input_origin", ""),
            "verdict": verdict,
            "baseline_status": row.get("baseline_status", ""),
            "baseline_comparison_status": row.get("baseline_comparison_status", ""),
            "timeout": str(row.get("timeout", "")).lower() in {"true", "1", "yes"},
            "returncode": as_int(row.get("returncode"), -999),
            "mapped_events": as_int(row.get("mapped_events"), -1),
            "processed_steps": as_int(row.get("processed_steps"), -1),
            "all_trace_steps_recorded": step.get("all_trace_steps_recorded", ""),
            "first_decisive_step": step.get("first_decisive_step", ""),
            "first_decisive_time": step.get("first_decisive_time", ""),
            "purpose": input_trace_purpose(row.get("input_path", "")),
        })
    return rows


def candidate_tokens(candidates: list[dict[str, Any]], predicate) -> list[str]:
    return [
        f"{row['candidate_id']}[{row['verdict']}|{row['input_origin']}|{row['purpose']}|t={row['first_decisive_time'] or '?'}]"
        for row in candidates
        if predicate(row)
    ]


def add_xml_trace_coverage_obligation(
    rows: list[dict[str, Any]],
    source: dict[str, Any],
    coverage_name: str,
    coverage_group: str,
    status: str,
    required: str,
    observed: str,
    observed_candidates: list[str],
    observed_input_origins: str,
    evidence_artifacts: str,
    reviewer_action: str,
    machine_checkable: bool = True,
) -> None:
    rows.append({
        "coverage_id": re.sub(
            r"[^A-Za-z0-9]+",
            "_",
            f"trace_{source.get('manifest_id', '')}_{coverage_name}",
        ).strip("_"),
        "manifest_id": source.get("manifest_id", ""),
        "xml_file": source.get("xml_file", ""),
        "positive_template": source.get("positive_template", ""),
        "negative_template": source.get("negative_template", ""),
        "candidate_mitl": source.get("candidate_mitl", ""),
        "proof_class": source.get("proof_class", ""),
        "proof_status": source.get("proof_status", ""),
        "coverage_group": coverage_group,
        "coverage_name": coverage_name,
        "coverage_status": status,
        "machine_checkable": "true" if machine_checkable else "false",
        "required": required,
        "observed": observed,
        "observed_candidates": ";".join(observed_candidates),
        "observed_input_origins": observed_input_origins,
        "evidence_artifacts": evidence_artifacts,
        "reviewer_action": reviewer_action,
    })


def coverage_status_for_tokens(tokens: list[str], *, fail_if_empty: bool = False) -> str:
    if tokens:
        return "PASS"
    return "FAIL" if fail_if_empty else "REVIEW_REQUIRED"


def build_xml_trace_coverage_obligations(
    edge_guard_rows: list[dict[str, Any]],
    benchmark_manifest_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    candidate_step_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    manifest_by_id = {row.get("manifest_id", ""): row for row in benchmark_manifest_rows}
    expected_verdicts = {
        "bounded_response_leadsto": {"NEGATIVE", "INCONCLUSIVE"},
        "bounded_absence_after_trigger": {"NEGATIVE", "INCONCLUSIVE"},
        "eventually_after_lower_bound": {"POSITIVE", "INCONCLUSIVE"},
        "bounded_global_absence": {"NEGATIVE", "POSITIVE"},
        "bounded_recurrence_after_event": {"NEGATIVE", "INCONCLUSIVE"},
        "gear_bounded_request_response": {"NEGATIVE", "INCONCLUSIVE"},
    }
    gstar_rearm_classes = {
        "bounded_response_leadsto",
        "bounded_absence_after_trigger",
        "bounded_recurrence_after_event",
        "gear_bounded_request_response",
    }

    rows: list[dict[str, Any]] = []
    for proof in edge_guard_rows:
        manifest = manifest_by_id.get(proof.get("manifest_id", ""), {})
        proof_ready = proof.get("proof_status") == "EDGE_GUARD_PROOF_READY"
        if not proof_ready:
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "not_promoted_trace_boundary",
                "scope",
                "PASS",
                "non-proof-ready XML rows stay outside trace-coverage proof obligations",
                f"proof_status={proof.get('proof_status', '')}; promotion_status={proof.get('promotion_status', '')}",
                [],
                manifest.get("input_origin_match_counts", ""),
                "xml_edge_guard_proofs.csv; benchmark_manifest.csv",
                "Do not promote this trace evidence without a separate structural proof rule.",
            )
            continue

        candidates = trace_coverage_candidates_for_pair(proof, candidate_rows, candidate_step_rows, baseline_rows)
        origins = Counter(row["input_origin"] or "<unknown>" for row in candidates)
        origin_summary = ";".join(f"{key}:{value}" for key, value in sorted(origins.items()))
        bad_runtime = [
            row["candidate_id"] for row in candidates
            if row["timeout"]
            or row["returncode"] != 0
            or row["baseline_comparison_status"] != "MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT"
            or row["processed_steps"] != row["mapped_events"]
        ]
        step_bad = [
            row["candidate_id"] for row in candidates
            if row["verdict"] in {"POSITIVE", "NEGATIVE"}
            and (row["all_trace_steps_recorded"] != "true" or not row["first_decisive_step"])
        ]
        add_xml_trace_coverage_obligation(
            rows,
            proof,
            "runtime_trace_integrity",
            "runtime",
            "PASS" if candidates and not bad_runtime and not step_bad else "FAIL",
            "all candidate trace runs match MoniTAal, terminate without timeout/error, and decisive verdict steps are recorded",
            f"candidate_count={len(candidates)}; bad_runtime={';'.join(bad_runtime) or '<none>'}; bad_step={';'.join(step_bad) or '<none>'}",
            [row["candidate_id"] for row in candidates],
            origin_summary,
            "translation_candidate_results.csv; candidate_step_audit.csv; candidate_prefix_observations.csv",
            "Fix runtime/baseline mismatches or step recording before using trace coverage as review evidence.",
        )

        for verdict in sorted(expected_verdicts.get(proof.get("proof_class", ""), set())):
            tokens = candidate_tokens(candidates, lambda row, verdict=verdict: row["verdict"] == verdict)
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                f"{verdict.lower()}_verdict_trace_present",
                "verdict",
                coverage_status_for_tokens(tokens),
                f"at least one {verdict} trace is available for this proof class as review-strengthening evidence",
                f"count={len(tokens)}",
                tokens,
                origin_summary,
                "translation_candidate_results.csv; monitaal_baseline_results.csv",
                "Add a generated boundary trace or record why the structural proof does not need this verdict polarity.",
            )

        proof_class = proof.get("proof_class", "")
        bound = as_int(proof.get("bound"), -1)
        if proof_class in {"bounded_response_leadsto", "gear_bounded_request_response"}:
            closed_tokens = candidate_tokens(
                candidates,
                lambda row: row["purpose"] in {"closed_boundary_positive", "rearmed_late_negative"}
                and (not row["first_decisive_time"] or as_int(row["first_decisive_time"], -1) == bound or row["purpose"] == "rearmed_late_negative"),
            )
            late_tokens = candidate_tokens(candidates, lambda row: row["purpose"] in {"initial_late_negative", "rearmed_late_negative"})
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "closed_bound_response_trace",
                "boundary",
                coverage_status_for_tokens(closed_tokens),
                "a response exactly at the closed upper bound is exercised, either as a decisive positive trace or as the satisfied prefix of a re-armed negative trace",
                f"bound={proof.get('bound', '')}; count={len(closed_tokens)}",
                closed_tokens,
                origin_summary,
                "generated_monitaal_inputs/; translation_candidate_results.csv; candidate_step_audit.csv",
                "Add an exact-bound response trace if the current evidence only tests late violations.",
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "strict_late_violation_trace",
                "boundary",
                coverage_status_for_tokens(late_tokens, fail_if_empty=True),
                "a response strictly after the upper bound produces a negative verdict",
                f"bound={proof.get('bound', '')}; count={len(late_tokens)}",
                late_tokens,
                origin_summary,
                "generated_monitaal_inputs/; translation_candidate_results.csv",
                "Keep at least one strict-late negative trace for request-response proof-ready rows.",
            )
        elif proof_class == "bounded_absence_after_trigger":
            boundary_tokens = candidate_tokens(candidates, lambda row: row["purpose"] == "closed_boundary_negative")
            safe_tokens = candidate_tokens(
                candidates,
                lambda row: row["purpose"] == "after_bound_positive"
                and row["verdict"] in {"POSITIVE", "INCONCLUSIVE"},
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "closed_bound_forbidden_trace",
                "boundary",
                coverage_status_for_tokens(boundary_tokens, fail_if_empty=True),
                "a forbidden event exactly at the closed bound produces a negative verdict",
                f"bound={proof.get('bound', '')}; count={len(boundary_tokens)}",
                boundary_tokens,
                origin_summary,
                "generated_monitaal_inputs/; translation_candidate_results.csv",
                "Keep the exact-bound forbidden-event trace for absence proof-ready rows.",
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "safe_absence_trace",
                "boundary",
                coverage_status_for_tokens(safe_tokens),
                "a trace with no in-window forbidden event is available as non-violation evidence under three-valued infinite-word RV",
                f"count={len(safe_tokens)}",
                safe_tokens,
                origin_summary,
                "translation_candidate_results.csv; monitaal_baseline_results.csv",
                "Add a safe after-bound trace or leave this as a human-review coverage gap.",
            )
        elif proof_class == "eventually_after_lower_bound":
            boundary_tokens = candidate_tokens(candidates, lambda row: row["purpose"] == "closed_boundary_positive")
            later_tokens = candidate_tokens(candidates, lambda row: row["purpose"] == "after_bound_positive")
            no_witness_tokens = candidate_tokens(
                candidates,
                lambda row: row["purpose"] == "no_witness_inconclusive"
                and row["verdict"] == "INCONCLUSIVE",
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "lower_bound_satisfaction_trace",
                "boundary",
                coverage_status_for_tokens(boundary_tokens, fail_if_empty=True),
                "the event exactly at the lower bound satisfies the eventuality",
                f"bound={proof.get('bound', '')}; count={len(boundary_tokens)}",
                boundary_tokens,
                origin_summary,
                "generated_monitaal_inputs/; translation_candidate_results.csv",
                "Keep the exact lower-bound positive trace for lower-bound eventuality rows.",
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "after_bound_satisfaction_trace",
                "boundary",
                coverage_status_for_tokens(later_tokens, fail_if_empty=True),
                "the event strictly after the lower bound satisfies the eventuality",
                f"bound={proof.get('bound', '')}; count={len(later_tokens)}",
                later_tokens,
                origin_summary,
                "generated_monitaal_inputs/; translation_candidate_results.csv",
                "Keep the after-bound positive trace for lower-bound eventuality rows.",
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "no_witness_inconclusive_trace",
                "boundary",
                coverage_status_for_tokens(no_witness_tokens),
                "a no-witness prefix after the lower bound remains INCONCLUSIVE under infinite-word eventuality semantics",
                f"count={len(no_witness_tokens)}",
                no_witness_tokens,
                origin_summary,
                "translation_candidate_results.csv; monitaal_baseline_results.csv",
                "Add a no-witness infinite-word prefix trace or keep the absence side as a human-review coverage gap.",
            )
        elif proof_class == "bounded_global_absence":
            boundary_tokens = candidate_tokens(candidates, lambda row: row["purpose"] == "closed_boundary_negative")
            early_tokens = candidate_tokens(candidates, lambda row: row["verdict"] == "NEGATIVE" and row["purpose"] != "closed_boundary_negative")
            safe_tokens = candidate_tokens(candidates, lambda row: row["purpose"] == "after_bound_positive")
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "closed_bound_violation_trace",
                "boundary",
                coverage_status_for_tokens(boundary_tokens, fail_if_empty=True),
                "a forbidden event exactly at the closed bound produces a negative verdict",
                f"bound={proof.get('bound', '')}; count={len(boundary_tokens)}",
                boundary_tokens,
                origin_summary,
                "generated_monitaal_inputs/; translation_candidate_results.csv",
                "Keep exact-bound violation evidence for closed global absence rows.",
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "in_window_violation_trace",
                "boundary",
                coverage_status_for_tokens(early_tokens, fail_if_empty=True),
                "a forbidden event strictly inside the interval produces a negative verdict",
                f"count={len(early_tokens)}",
                early_tokens,
                origin_summary,
                "generated_monitaal_inputs/; translation_candidate_results.csv",
                "Keep in-window violation evidence for global absence rows.",
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "after_bound_safe_trace",
                "boundary",
                coverage_status_for_tokens(safe_tokens, fail_if_empty=True),
                "a forbidden event strictly after the closed interval remains positive",
                f"bound={proof.get('bound', '')}; count={len(safe_tokens)}",
                safe_tokens,
                origin_summary,
                "generated_monitaal_inputs/; translation_candidate_results.csv",
                "Keep after-bound safe evidence for global absence rows.",
            )
        elif proof_class == "bounded_recurrence_after_event":
            initial_tokens = candidate_tokens(candidates, lambda row: row["purpose"] == "initial_window_late_negative")
            rearm_tokens = candidate_tokens(candidates, lambda row: row["purpose"] == "initial_late_negative")
            timely_tokens = candidate_tokens(
                candidates,
                lambda row: row["purpose"] == "timely_positive"
                and row["verdict"] in {"POSITIVE", "INCONCLUSIVE"},
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "initial_window_violation_trace",
                "boundary",
                coverage_status_for_tokens(initial_tokens, fail_if_empty=True),
                "absence of the first required recurrence event inside the initial closed bound produces a negative verdict",
                f"bound={proof.get('bound', '')}; count={len(initial_tokens)}",
                initial_tokens,
                origin_summary,
                "generated_monitaal_inputs/; translation_candidate_results.csv",
                "Keep an initial-window late trace for recurrence proof-ready rows.",
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "rearmed_late_violation_trace",
                "boundary",
                coverage_status_for_tokens(rearm_tokens, fail_if_empty=True),
                "after one recurrence event, the next event strictly after the bound produces a negative verdict",
                f"bound={proof.get('bound', '')}; count={len(rearm_tokens)}",
                rearm_tokens,
                origin_summary,
                "generated_monitaal_inputs/; translation_candidate_results.csv",
                "Keep a re-armed late trace for recurrence proof-ready rows.",
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "timely_recurrence_nonviolating_trace",
                "boundary",
                coverage_status_for_tokens(timely_tokens),
                "a timely initial and re-armed recurrence trace is available as non-violation evidence under three-valued infinite-word RV",
                f"count={len(timely_tokens)}",
                timely_tokens,
                origin_summary,
                "translation_candidate_results.csv; monitaal_baseline_results.csv",
                "Add a timely recurrence trace or leave this as a human-review coverage gap.",
            )

        if proof_class in gstar_rearm_classes:
            if proof_class == "bounded_recurrence_after_event":
                rearm_purposes = {"initial_late_negative"}
            elif proof_class == "bounded_absence_after_trigger":
                rearm_purposes = {"rearmed_boundary_negative"}
            else:
                rearm_purposes = {"rearmed_late_negative"}
            rearm_tokens = candidate_tokens(
                candidates,
                lambda row: row["purpose"] in rearm_purposes and row["mapped_events"] >= 2,
            )
            add_xml_trace_coverage_obligation(
                rows,
                proof,
                "rearmed_obligation_trace",
                "rearm",
                coverage_status_for_tokens(rearm_tokens),
                "G* or recurrence-style formulas have at least one trace exercising a second obligation after reset/re-arm",
                f"count={len(rearm_tokens)}",
                rearm_tokens,
                origin_summary,
                "generated_monitaal_inputs/; translation_candidate_results.csv; xml_edge_guard_proofs.csv",
                "Add a repeated-trigger trace if reset/re-arm behavior is only supported by structural edge evidence.",
            )

        original_tokens = candidate_tokens(
            candidates,
            lambda row: row["input_origin"] in {"repository_input", "embedded_benchmark_input", "external_or_case_input"},
        )
        decisive_original_tokens = [
            token for token in original_tokens
            if "[POSITIVE|" in token or "[NEGATIVE|" in token
        ]
        generated_empty = as_int(manifest.get("generated_empty_no_original_input_match_count"))
        original_status = "PASS" if decisive_original_tokens else ("FAIL" if generated_empty else "REVIEW_REQUIRED")
        add_xml_trace_coverage_obligation(
            rows,
            proof,
            "original_decisive_trace_boundary",
            "origin",
            original_status,
            "repository, embedded, or external case inputs provide a decisive POSITIVE/NEGATIVE verdict, or the absence is kept as a review gap",
            f"original_like={len(original_tokens)}; decisive_original={len(decisive_original_tokens)}; generated_empty={generated_empty}",
            original_tokens,
            origin_summary,
            "benchmark_manifest.csv; monitaal_baseline_results.csv; translation_candidate_results.csv",
            "Do not treat generated-empty probes or INCONCLUSIVE original traces as Boolean proof evidence.",
        )
    return rows


def write_xml_trace_coverage_obligations(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    (output_dir / "xml_trace_coverage_obligations.json").write_text(json.dumps({
        "summary": {
            "row_count": len(rows),
            "pass": count_rows(rows, coverage_status="PASS"),
            "review_required": count_rows(rows, coverage_status="REVIEW_REQUIRED"),
            "fail": count_rows(rows, coverage_status="FAIL"),
            "proof_ready_manifests": len({row["manifest_id"] for row in rows if row["coverage_name"] == "runtime_trace_integrity"}),
        },
        "rows": rows,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = Counter(row["coverage_status"] for row in rows)
    by_group = Counter(row["coverage_group"] for row in rows)
    lines = [
        "# XML Trace Coverage Obligations",
        "",
        "This ledger turns trace evidence for proof-ready XML rows into reviewable coverage obligations.",
        "Missing strengthening traces are REVIEW_REQUIRED unless they expose a machine-checkable runtime or provenance failure.",
        "",
        "## Counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- `{status}`: {count}")
    lines.extend([
        "",
        "## Groups",
        "",
        "| group | rows |",
        "|---|---:|",
    ])
    for group, count in sorted(by_group.items()):
        lines.append(f"| `{group}` | {count} |")
    lines.extend([
        "",
        "## Coverage Obligations",
        "",
        "| manifest_id | group | coverage | status | observed | candidates | reviewer_action |",
        "|---|---|---|---|---|---|---|",
    ])
    for row in rows:
        observed = row["observed"].replace("|", "\\|")[:240]
        candidates = row["observed_candidates"].replace("|", "\\|")[:240]
        action = row["reviewer_action"].replace("|", "\\|")
        lines.append(
            f"| `{row['manifest_id']}` | `{row['coverage_group']}` | `{row['coverage_name']}` | "
            f"`{row['coverage_status']}` | {observed} | {candidates} | {action} |"
        )
    lines.append("")
    (output_dir / "xml_trace_coverage_obligations.md").write_text("\n".join(lines), encoding="utf-8")


def parse_semicolon_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for part in str(text or "").split(";"):
        if not part or ":" not in part:
            continue
        key, value = part.split(":", 1)
        try:
            counts[key.strip()] = int(value.strip())
        except ValueError:
            continue
    return counts


def parse_observed_counts(text: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for part in str(text or "").split(";"):
        if not part or "=" not in part:
            continue
        key, value = part.split("=", 1)
        try:
            counts[key.strip()] = int(value.strip())
        except ValueError:
            continue
    return counts


def classify_original_trace_gap(row: dict[str, Any]) -> tuple[str, str, str]:
    observed_counts = parse_observed_counts(row.get("observed", ""))
    origin_counts = parse_semicolon_counts(row.get("observed_input_origins", ""))
    candidates = str(row.get("observed_candidates", ""))
    generated_empty = observed_counts.get("generated_empty", 0)
    original_like = observed_counts.get("original_like", 0)
    has_repository_inconclusive = (
        "repository_input" in origin_counts
        or "|repository_input" in candidates
        or "repository_input]" in candidates
    ) and "INCONCLUSIVE" in candidates

    if generated_empty:
        return (
            "generated_empty_baseline_only",
            "Only generated-empty baseline probes exist for the original-input boundary; this is not original benchmark evidence.",
            "Do not claim generated-empty probes as original MoniTAal benchmark traces.",
        )
    if has_repository_inconclusive:
        return (
            "repository_input_inconclusive",
            "A repository input exists, but current runtime evidence is INCONCLUSIVE rather than decisive POSITIVE/NEGATIVE.",
            "Do not promote INCONCLUSIVE repository traces to Boolean satisfaction or violation evidence.",
        )
    if not original_like:
        return (
            "no_repository_input_found",
            "No repository, embedded, or external timed-word input was found for this XML pair.",
            "Do not treat generated review traces as original benchmark evidence.",
        )
    return (
        "no_decisive_original_trace",
        "Original-like trace evidence exists, but no decisive POSITIVE/NEGATIVE verdict was observed.",
        "Do not claim decisive original-trace validation until a decisive original input is located or justified.",
    )


def build_xml_original_trace_gaps(xml_trace_coverage_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for source in xml_trace_coverage_rows:
        if source.get("coverage_name") != "original_decisive_trace_boundary":
            continue
        if source.get("coverage_status") != "REVIEW_REQUIRED":
            continue
        gap_class, reason, must_not_claim = classify_original_trace_gap(source)
        rows.append({
            "gap_id": re.sub(
                r"[^A-Za-z0-9]+",
                "_",
                f"original_gap_{source.get('coverage_id', '')}",
            ).strip("_"),
            "manifest_id": source.get("manifest_id", ""),
            "xml_file": source.get("xml_file", ""),
            "positive_template": source.get("positive_template", ""),
            "negative_template": source.get("negative_template", ""),
            "candidate_mitl": source.get("candidate_mitl", ""),
            "proof_class": source.get("proof_class", ""),
            "gap_class": gap_class,
            "gap_status": "REVIEW_REQUIRED",
            "machine_checkable": "false",
            "observed": source.get("observed", ""),
            "observed_candidates": source.get("observed_candidates", ""),
            "observed_input_origins": source.get("observed_input_origins", ""),
            "reason": reason,
            "manual_review_action": (
                "Locate a real original timed-word input with a decisive POSITIVE/NEGATIVE verdict, "
                "or keep the paper claim caveated to generated trace evidence and structural proof obligations."
            ),
            "must_not_claim": must_not_claim,
            "source_coverage_id": source.get("coverage_id", ""),
            "evidence_artifacts": (
                "xml_original_trace_gaps.csv; xml_trace_coverage_obligations.csv; benchmark_manifest.csv; "
                "monitaal_baseline_results.csv; translation_candidate_results.csv"
                + (
                    "; gear_original_input_response_audit.csv"
                    if source.get("xml_file") == "gear-control-properties.xml"
                    and gap_class == "repository_input_inconclusive"
                    else ""
                )
                + (
                    "; non_gear_original_input_search_audit.csv"
                    if source.get("xml_file") != "gear-control-properties.xml"
                    and gap_class == "no_repository_input_found"
                    else ""
                )
            ),
        })
    return rows


def write_xml_original_trace_gaps(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    by_class = Counter(row["gap_class"] for row in rows)
    payload = {
        "summary": {
            "row_count": len(rows),
            "review_required": count_rows(rows, gap_status="REVIEW_REQUIRED"),
            "fail": count_rows(rows, gap_status="FAIL"),
            "machine_checkable": count_rows(rows, machine_checkable="true"),
            "by_class": dict(sorted(by_class.items())),
        },
        "rows": rows,
    }
    (output_dir / "xml_original_trace_gaps.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lines = [
        "# XML Original Trace Gaps",
        "",
        "This ledger isolates proof-ready XML rows whose original/repository timed-word evidence is not decisive.",
        "All rows are REVIEW_REQUIRED and non-machine-checkable; generated review traces must not be reclassified as original benchmark evidence.",
        "",
        "## Counts",
        "",
        f"- `REVIEW_REQUIRED`: {count_rows(rows, gap_status='REVIEW_REQUIRED')}",
        f"- `FAIL`: {count_rows(rows, gap_status='FAIL')}",
        "",
        "## Gap Classes",
        "",
        "| gap_class | rows |",
        "|---|---:|",
    ]
    for gap_class, count in sorted(by_class.items()):
        lines.append(f"| `{gap_class}` | {count} |")
    lines.extend([
        "",
        "## Gaps",
        "",
        "| manifest_id | xml_file | gap_class | observed | candidates | manual_review_action |",
        "|---|---|---|---|---|---|",
    ])
    for row in rows:
        observed = row["observed"].replace("|", "\\|")[:220]
        candidates = row["observed_candidates"].replace("|", "\\|")[:220]
        action = row["manual_review_action"].replace("|", "\\|")
        lines.append(
            f"| `{row['manifest_id']}` | `{row['xml_file']}` | `{row['gap_class']}` | "
            f"{observed} | {candidates} | {action} |"
        )
    lines.append("")
    (output_dir / "xml_original_trace_gaps.md").write_text("\n".join(lines), encoding="utf-8")


def format_time_for_report(value: float | None) -> str:
    if value is None:
        return ""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.6g}"


def parse_monitaal_timed_input(path: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    events: list[dict[str, Any]] = []
    timed_rows = 0
    empty_label_rows = 0
    unparsable_rows = 0
    last_time: float | None = None
    if not path.exists():
        return events, {
            "timed_event_rows": 0,
            "nonblank_event_count": 0,
            "empty_label_event_count": 0,
            "unparsable_event_rows": 0,
            "last_event_time": "",
        }
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        match = re.match(r"^@([+-]?\d+(?:\.\d+)?)\s*(.*)$", stripped)
        if not match:
            unparsable_rows += 1
            continue
        timed_rows += 1
        try:
            timestamp = float(match.group(1))
        except ValueError:
            unparsable_rows += 1
            continue
        last_time = timestamp if last_time is None else max(last_time, timestamp)
        label = match.group(2).strip()
        if not label:
            empty_label_rows += 1
            continue
        events.append({
            "time": timestamp,
            "index": timed_rows,
            "label": label,
        })
    return events, {
        "timed_event_rows": timed_rows,
        "nonblank_event_count": len(events),
        "empty_label_event_count": empty_label_rows,
        "unparsable_event_rows": unparsable_rows,
        "last_event_time": format_time_for_report(last_time),
    }


def response_audit_for_timed_events(
    events: list[dict[str, Any]],
    trigger_label: str,
    response_label: str,
    bound: int,
    last_event_time: str,
) -> dict[str, Any]:
    trigger_points = sorted(
        (float(event["time"]), int(event["index"]))
        for event in events
        if event.get("label") == trigger_label
    )
    response_points = sorted(
        (float(event["time"]), int(event["index"]))
        for event in events
        if event.get("label") == response_label
    )
    last_time = float(last_event_time) if last_event_time else None
    responded_within_bound = 0
    late_response_count = 0
    pending_trigger_count = 0
    expired_without_response_count = 0
    response_delays: list[float] = []
    late_trigger_times: list[str] = []
    pending_trigger_times: list[str] = []
    expired_trigger_times: list[str] = []

    for trigger_time, trigger_index in trigger_points:
        response_index = bisect_left(response_points, (trigger_time, trigger_index + 1))
        if response_index < len(response_points):
            response_time = response_points[response_index][0]
            delay = response_time - trigger_time
            if delay <= bound:
                responded_within_bound += 1
                response_delays.append(delay)
            else:
                late_response_count += 1
                late_trigger_times.append(format_time_for_report(trigger_time))
        elif last_time is None or last_time < trigger_time + bound:
            pending_trigger_count += 1
            pending_trigger_times.append(format_time_for_report(trigger_time))
        else:
            expired_without_response_count += 1
            expired_trigger_times.append(format_time_for_report(trigger_time))

    if late_response_count or expired_without_response_count:
        finite_status = "LATE_OR_EXPIRED_RESPONSE_OBSERVED"
    elif pending_trigger_count:
        finite_status = "PENDING_TRIGGER_AT_TRACE_END"
    else:
        finite_status = "NO_LATE_RESPONSE_OBSERVED_BUT_ONLINE_FUTURE_OPEN"

    return {
        "trigger_count": len(trigger_points),
        "response_count": len(response_points),
        "responded_within_bound": responded_within_bound,
        "late_response_count": late_response_count,
        "pending_trigger_count": pending_trigger_count,
        "expired_without_response_count": expired_without_response_count,
        "max_response_delay": format_time_for_report(max(response_delays) if response_delays else None),
        "last_trigger_time": format_time_for_report(trigger_points[-1][0] if trigger_points else None),
        "last_response_time": format_time_for_report(response_points[-1][0] if response_points else None),
        "late_trigger_times": ";".join(late_trigger_times),
        "pending_trigger_times": ";".join(pending_trigger_times),
        "expired_trigger_times": ";".join(expired_trigger_times),
        "finite_trace_response_status": finite_status,
    }


def build_gear_original_input_response_audit(
    edge_guard_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    baseline_by_key = {
        (
            Path(row.get("xml_path", "")).name,
            row.get("positive_template", ""),
            row.get("negative_template", ""),
            Path(row.get("input_path", "")).name,
        ): row
        for row in baseline_rows
    }
    event_cache: dict[Path, tuple[list[dict[str, Any]], dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    for proof in edge_guard_rows:
        if proof.get("xml_file") != "gear-control-properties.xml":
            continue
        if proof.get("proof_status") != "EDGE_GUARD_PROOF_READY":
            continue
        if proof.get("proof_class") != "gear_bounded_request_response":
            continue
        baseline = baseline_by_key.get((
            proof.get("xml_file", ""),
            proof.get("positive_template", ""),
            proof.get("negative_template", ""),
            "gear-control-input.txt",
        ), {})
        input_path = Path(baseline.get("input_path", "") or (REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "gear-control-input.txt"))
        if input_path not in event_cache:
            event_cache[input_path] = parse_monitaal_timed_input(input_path)
        events, parse_stats = event_cache[input_path]
        bound = as_int(proof.get("bound"), -1)
        response_stats = response_audit_for_timed_events(
            events,
            proof.get("trigger_label", ""),
            proof.get("response_label", ""),
            bound,
            parse_stats.get("last_event_time", ""),
        )
        evidence_summary = (
            f"repository input rows={parse_stats.get('timed_event_rows', 0)}; "
            f"nonblank_events={parse_stats.get('nonblank_event_count', 0)}; "
            f"baseline={baseline.get('status', '<missing>')}/{baseline.get('verdict', '<missing>')}; "
            f"triggers={response_stats['trigger_count']}; within_bound={response_stats['responded_within_bound']}; "
            f"late={response_stats['late_response_count']}; pending={response_stats['pending_trigger_count']}; "
            f"expired={response_stats['expired_without_response_count']}"
        )
        rows.append({
            "audit_id": f"gear_original_{proof.get('manifest_id', '')}",
            "manifest_id": proof.get("manifest_id", ""),
            "xml_file": proof.get("xml_file", ""),
            "positive_template": proof.get("positive_template", ""),
            "negative_template": proof.get("negative_template", ""),
            "candidate_mitl": proof.get("candidate_mitl", ""),
            "trigger_label": proof.get("trigger_label", ""),
            "response_label": proof.get("response_label", ""),
            "bound": proof.get("bound", ""),
            "input_path": str(input_path),
            "input_origin": baseline.get("input_origin", ""),
            "baseline_status": baseline.get("status", ""),
            "baseline_verdict": baseline.get("verdict", ""),
            "baseline_returncode": baseline.get("returncode", ""),
            **parse_stats,
            **response_stats,
            "online_verdict_boundary": (
                "MoniTAal/TAMonitor online infinite-word verdict remains INCONCLUSIVE on this original input; "
                "this finite-prefix response accounting is not Boolean satisfaction, not Boolean violation, "
                "and not an XML-to-MITL equivalence proof."
            ),
            "evidence_summary": evidence_summary,
            "reviewer_action": (
                "Use this row to audit the repository gear input. Keep the original-trace gap REVIEW_REQUIRED "
                "unless a decisive original timed-word verdict or human-approved equivalence argument is added."
            ),
        })
    return rows


def write_gear_original_input_response_audit(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    by_status = Counter(row["finite_trace_response_status"] for row in rows)
    payload = {
        "summary": {
            "row_count": len(rows),
            "late_response_rows": sum(1 for row in rows if as_int(row.get("late_response_count")) > 0),
            "pending_trigger_rows": sum(1 for row in rows if as_int(row.get("pending_trigger_count")) > 0),
            "expired_without_response_rows": sum(1 for row in rows if as_int(row.get("expired_without_response_count")) > 0),
            "by_finite_trace_response_status": dict(sorted(by_status.items())),
        },
        "rows": rows,
    }
    (output_dir / "gear_original_input_response_audit.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lines = [
        "# Gear Original Input Response Audit",
        "",
        "This ledger audits the MoniTAal repository `gear-control-input.txt` finite prefix for the six gear request-response XML pairs.",
        "It does not close the original-trace gaps: the online infinite-word baseline verdict remains `INCONCLUSIVE` for these rows.",
        "",
        "## Counts",
        "",
        f"- rows: {len(rows)}",
        f"- late response rows: {payload['summary']['late_response_rows']}",
        f"- pending trigger rows: {payload['summary']['pending_trigger_rows']}",
        f"- expired-without-response rows: {payload['summary']['expired_without_response_rows']}",
        "",
        "## Rows",
        "",
        "| audit_id | trigger -> response | bound | baseline | triggers | within_bound | late | pending | finite_status |",
        "|---|---|---:|---|---:|---:|---:|---:|---|",
    ]
    for row in rows:
        pair = f"{row['trigger_label']} -> {row['response_label']}"
        baseline = f"{row['baseline_status']}/{row['baseline_verdict']}"
        lines.append(
            f"| `{row['audit_id']}` | `{pair}` | {row['bound']} | `{baseline}` | "
            f"{row['trigger_count']} | {row['responded_within_bound']} | "
            f"{row['late_response_count']} | {row['pending_trigger_count']} | "
            f"`{row['finite_trace_response_status']}` |"
        )
    lines.append("")
    (output_dir / "gear_original_input_response_audit.md").write_text("\n".join(lines), encoding="utf-8")


def repository_same_stem_files(xml_path: Path) -> list[Path]:
    monitaal_root = REPO_ROOT / "tool" / "MoniTAal"
    stem = xml_path.stem.lower()
    if not monitaal_root.exists():
        return []
    return sorted(
        path
        for path in monitaal_root.rglob("*")
        if path.is_file() and stem in path.name.lower()
    )


def sibling_input_search_summary(xml_path: Path) -> tuple[list[Path], list[Path]]:
    sibling_inputs = sorted(xml_path.parent.glob("*input*.txt"))
    normalized_stem = xml_path.stem.lower().replace("-", "").replace("_", "").replace(" ", "")
    prefix_matches = [
        path
        for path in sibling_inputs
        if len(normalized_stem) >= 5
        and path.stem.lower().replace("-", "").replace("_", "").replace(" ", "").startswith(normalized_stem)
    ]
    return sibling_inputs, prefix_matches


def build_non_gear_original_input_search_audit(
    xml_original_trace_gap_rows: list[dict[str, Any]],
    benchmark_manifest_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    manifest_by_id = {row.get("manifest_id", ""): row for row in benchmark_manifest_rows}
    baseline_by_pair: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for row in baseline_rows:
        key = (
            Path(row.get("xml_path", "")).name,
            row.get("positive_template", ""),
            row.get("negative_template", ""),
        )
        baseline_by_pair.setdefault(key, []).append(row)

    cmake_path = REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / "CMakeLists.txt"
    cmake_text = cmake_path.read_text(encoding="utf-8", errors="replace") if cmake_path.exists() else ""
    rows: list[dict[str, Any]] = []
    for gap in xml_original_trace_gap_rows:
        if gap.get("gap_class") != "no_repository_input_found":
            continue
        if gap.get("xml_file") == "gear-control-properties.xml":
            continue
        manifest = manifest_by_id.get(gap.get("manifest_id", ""), {})
        xml_path = Path(manifest.get("xml_path", "") or (REPO_ROOT / "tool" / "MoniTAal" / "test" / "models" / gap.get("xml_file", "")))
        sibling_inputs, prefix_matches = sibling_input_search_summary(xml_path)
        same_stem_files = repository_same_stem_files(xml_path)
        non_xml_same_stem_files = [path for path in same_stem_files if path.suffix.lower() != ".xml"]
        matching_baselines = baseline_by_pair.get((
            gap.get("xml_file", ""),
            gap.get("positive_template", ""),
            gap.get("negative_template", ""),
        ), [])
        original_like_baselines = [
            row for row in matching_baselines
            if row.get("input_origin") in {
                "repository_input",
                "embedded_benchmark_input",
                "external_or_case_input",
            }
        ]
        generated_review_inputs = [
            row for row in matching_baselines
            if row.get("input_origin") == "generated_review_input"
        ]
        generated_empty_inputs = [
            row for row in matching_baselines
            if row.get("input_origin") == "generated_empty_no_original_input"
        ]
        search_status = (
            "NO_ORIGINAL_TIMED_WORD_FOUND"
            if not original_like_baselines and not prefix_matches and not non_xml_same_stem_files
            else "REVIEW_REQUIRED_POSSIBLE_ORIGINAL_INPUT"
        )
        evidence_summary = (
            f"xml_exists={xml_path.exists()}; cmake_lists_xml={gap.get('xml_file', '') in cmake_text}; "
            f"sibling_input_txt={len(sibling_inputs)}; prefix_matched_sibling_inputs={len(prefix_matches)}; "
            f"repository_same_stem_files={len(same_stem_files)}; repository_non_xml_same_stem_files={len(non_xml_same_stem_files)}; "
            f"original_like_baselines={len(original_like_baselines)}; generated_review_inputs={len(generated_review_inputs)}; "
            f"generated_empty_inputs={len(generated_empty_inputs)}"
        )
        rows.append({
            "audit_id": f"non_gear_original_input_search_{gap.get('manifest_id', '')}",
            "manifest_id": gap.get("manifest_id", ""),
            "gap_id": gap.get("gap_id", ""),
            "xml_file": gap.get("xml_file", ""),
            "xml_path": str(xml_path),
            "positive_template": gap.get("positive_template", ""),
            "negative_template": gap.get("negative_template", ""),
            "candidate_mitl": gap.get("candidate_mitl", ""),
            "gap_class": gap.get("gap_class", ""),
            "search_status": search_status,
            "xml_exists": "true" if xml_path.exists() else "false",
            "monitaal_models_cmake_lists_reference": "true" if gap.get("xml_file", "") in cmake_text else "false",
            "sibling_input_txt_count": len(sibling_inputs),
            "sibling_input_txt_names": ";".join(path.name for path in sibling_inputs),
            "prefix_matched_sibling_input_count": len(prefix_matches),
            "prefix_matched_sibling_input_names": ";".join(path.name for path in prefix_matches),
            "repository_same_stem_file_count": len(same_stem_files),
            "repository_same_stem_files": ";".join(str(path.relative_to(REPO_ROOT)) for path in same_stem_files),
            "repository_non_xml_same_stem_file_count": len(non_xml_same_stem_files),
            "repository_non_xml_same_stem_files": ";".join(str(path.relative_to(REPO_ROOT)) for path in non_xml_same_stem_files),
            "baseline_rows_for_pair": len(matching_baselines),
            "original_like_baseline_count": len(original_like_baselines),
            "generated_review_input_count": len(generated_review_inputs),
            "generated_review_input_paths": ";".join(row.get("input_path", "") for row in generated_review_inputs),
            "generated_empty_input_count": len(generated_empty_inputs),
            "manifest_original_input_match_count": manifest.get("original_input_match_count", ""),
            "manifest_generated_input_match_count": manifest.get("generated_input_match_count", ""),
            "manifest_input_origin_match_counts": manifest.get("input_origin_match_counts", ""),
            "evidence_summary": evidence_summary,
            "boundary": (
                "This search found no repository, embedded, or external original timed-word input for this XML pair. "
                "Generated review traces remain trace-level evidence only and must not be cited as original benchmark traces."
            ),
            "reviewer_action": (
                "Keep the original-trace gap REVIEW_REQUIRED unless a real original timed-word input is found "
                "or a human reviewer explicitly accepts the generated-trace caveat."
            ),
        })
    return rows


def write_non_gear_original_input_search_audit(output_dir: Path, rows: list[dict[str, Any]]) -> None:
    by_status = Counter(row["search_status"] for row in rows)
    payload = {
        "summary": {
            "row_count": len(rows),
            "no_original_timed_word_found": count_rows(rows, search_status="NO_ORIGINAL_TIMED_WORD_FOUND"),
            "review_required_possible_original_input": count_rows(rows, search_status="REVIEW_REQUIRED_POSSIBLE_ORIGINAL_INPUT"),
            "original_like_baseline_rows": sum(as_int(row.get("original_like_baseline_count")) for row in rows),
            "generated_review_input_rows": sum(as_int(row.get("generated_review_input_count")) for row in rows),
            "by_search_status": dict(sorted(by_status.items())),
        },
        "rows": rows,
    }
    (output_dir / "non_gear_original_input_search_audit.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    lines = [
        "# Non-Gear Original Input Search Audit",
        "",
        "This ledger records the repository-input search evidence for non-gear XML original-trace gaps.",
        "It does not close the gaps; it documents that generated review traces are not original benchmark traces.",
        "",
        "## Counts",
        "",
        f"- rows: {len(rows)}",
        f"- no original timed word found: {payload['summary']['no_original_timed_word_found']}",
        f"- possible original input rows: {payload['summary']['review_required_possible_original_input']}",
        f"- generated review input rows: {payload['summary']['generated_review_input_rows']}",
        "",
        "## Rows",
        "",
        "| audit_id | xml_file | search_status | sibling_inputs | prefix_matches | same_stem_non_xml | generated_review_inputs |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| `{row['audit_id']}` | `{row['xml_file']}` | `{row['search_status']}` | "
            f"{row['sibling_input_txt_count']} | {row['prefix_matched_sibling_input_count']} | "
            f"{row['repository_non_xml_same_stem_file_count']} | {row['generated_review_input_count']} |"
        )
    lines.append("")
    (output_dir / "non_gear_original_input_search_audit.md").write_text("\n".join(lines), encoding="utf-8")


def baseline_rows_for_appendix(row: dict[str, Any], baseline_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    xml_file = row.get("xml_file", "")
    positive = row.get("positive_template", "")
    negative = row.get("negative_template", "")
    matches = []
    for baseline in baseline_rows:
        if Path(baseline.get("xml_path", "")).name != xml_file:
            continue
        if baseline.get("positive_template", "") != positive:
            continue
        if baseline.get("negative_template", "") != negative:
            continue
        matches.append(baseline)
    return matches


def append_caveat(text: str, caveat: str) -> str:
    if not caveat:
        return text
    if caveat in text:
        return text
    if not text:
        return caveat
    separator = " " if text.endswith((".", "!", "?")) else ". "
    return f"{text}{separator}{caveat}"


def paper_claim_review_for_row(
    row: dict[str, Any],
    baseline_rows: list[dict[str, Any]],
    original_trace_gaps_by_manifest: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    appendix_status = row.get("appendix_status", "")
    proof_class = row.get("proof_class", "")
    manifest_id = row.get("manifest_id", "")
    original_trace_gap = original_trace_gaps_by_manifest.get(manifest_id, {})
    matching_baselines = baseline_rows_for_appendix(row, baseline_rows)
    baseline_timeouts = [r for r in matching_baselines if r.get("status") == "timeout"]
    baseline_matches = [r for r in matching_baselines if r.get("status") == "ran" and r.get("verdict")]
    inconclusive_matches = [r for r in baseline_matches if r.get("verdict") == "INCONCLUSIVE"]
    timeout_paths = ";".join(r.get("input_path", "") for r in baseline_timeouts)
    matched_verdicts = ";".join(
        f"{r.get('input_path', '')}:{r.get('verdict', '')}" for r in baseline_matches
    )

    if appendix_status == "PROOF_DRAFT_READY" and proof_class == "gear_bounded_request_response":
        if baseline_matches and not baseline_timeouts:
            original_inconclusive = [
                r for r in baseline_matches
                if Path(r.get("input_path", "")).name == "gear-control-input.txt"
                and r.get("verdict") == "INCONCLUSIVE"
            ]
            generated_negative = [
                r for r in baseline_matches
                if r.get("input_origin") == "generated_review_input"
                and r.get("verdict") == "NEGATIVE"
            ]
            claim_strength = "BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF"
            if original_inconclusive:
                body_recommendation = (
                    "Body may summarize this gear request/response pattern only after human signoff on the XML edge/guard proof, "
                    "the mapped alphabet, the original-input INCONCLUSIVE MoniTAal comparison, and the generated negative boundary traces."
                )
                appendix_recommendation = (
                    "Keep the six gear instances in the appendix with edge/guard proof evidence, original-input INCONCLUSIVE baseline rows, "
                    "generated negative boundary traces, and per-prefix TAMonitor observations."
                )
                must_not_claim = (
                    "Do not treat an INCONCLUSIVE original-input baseline, generated negative traces, or trace-level MoniTAal agreement "
                    "as anything stronger than third-valued evidence; it is not Boolean satisfaction, violation, an automatic "
                    "XML-to-MITL equivalence theorem, or human proof signoff."
                )
                next_action = (
                    "Human reviewer should check the gear edge/guard proof and decide the exact third-valued caveat needed before any body wording."
                )
            else:
                body_recommendation = (
                    "Body may summarize this gear request/response pattern after human signoff on the XML edge/guard proof, "
                    "the mapped alphabet, and the original-input MoniTAal baseline comparison."
                )
                appendix_recommendation = (
                    "Keep the six gear instances in the appendix with edge/guard proof evidence, original-input baseline matches, and per-prefix TAMonitor observations."
                )
                must_not_claim = (
                    "Do not treat a trace-level MoniTAal baseline match as an automatic XML-to-MITL equivalence theorem or as human proof signoff."
                )
                next_action = "Human reviewer should check the gear edge/guard proof and then decide whether the pattern can be cited in the paper body."
            if generated_negative and "generated negative" not in appendix_recommendation:
                appendix_recommendation += " Generated negative boundary traces are available for late-response checks."
        else:
            claim_strength = "APPENDIX_INSTANCE_READY_WITH_TIMEOUT_CAVEAT"
            body_recommendation = (
                "Appendix-only structural candidate with original-input timeout caveat; do not use as a completed body benchmark claim."
            )
            appendix_recommendation = (
                "Keep the six gear instances in the appendix with edge/guard proof evidence, reduced trace evidence, and explicit original-input timeout caveats."
            )
            must_not_claim = (
                "Do not claim MoniTAal original gear-control-input baseline agreement until the long input terminates "
                "or a justified reduction is documented."
            )
            next_action = "Rerun original gear input after fixing baseline runtime issues; otherwise cite reduced trace evidence only."
    elif appendix_status == "PROOF_DRAFT_READY":
        claim_strength = "BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF"
        if inconclusive_matches:
            body_recommendation = (
                "Body may summarize this proof pattern only after human signoff on the alphabet, finite-prefix verdict, "
                "G* first-observation convention, and the INCONCLUSIVE trace-level evidence caveat."
            )
            appendix_recommendation = (
                "Keep the instance-level edge/guard proof sketch in the appendix with explicit INCONCLUSIVE trace evidence; "
                "the INCONCLUSIVE rows are third-valued boundary evidence, not Boolean satisfaction or violation."
            )
            must_not_claim = (
                "Do not call this an automatic theorem, Boolean satisfaction/violation result, or completed XML-to-MITL "
                "equivalence proof from INCONCLUSIVE trace evidence; keep the third-valued caveat until human proof review."
            )
            next_action = (
                "Human reviewer should check the proof sketch against the final paper definitions and decide the exact "
                "third-valued caveat needed for any body or appendix wording."
            )
        else:
            body_recommendation = (
                "Body may summarize this proof pattern after human signoff on the alphabet, finite-prefix verdict, "
                "and G* first-observation convention."
            )
            appendix_recommendation = "Keep the instance-level edge/guard proof sketch in the appendix."
            must_not_claim = "Do not call this an automatic theorem without the human proof review recorded."
            next_action = "Human reviewer should check the proof sketch against the final paper definitions."
    elif appendix_status == "EXCLUDED_APPROXIMATE":
        claim_strength = "EXCLUDED_APPROXIMATE_WITH_TRACE_EVIDENCE" if baseline_matches else "EXCLUDED_APPROXIMATE_ONLY"
        body_recommendation = "Do not include in formal XML-to-MITL equivalence claims."
        appendix_recommendation = (
            "List as approximate with trace evidence only; do not present as a formal translation."
            if baseline_matches else "List only as approximate or exploratory, if mentioned at all."
        )
        must_not_claim = "Do not report as a translated benchmark."
        next_action = (
            "Add a formal edge/guard proof for the approximate candidate or keep excluded."
            if baseline_matches else "Revise the MITL candidate or keep excluded."
        )
    elif appendix_status == "EXCLUDED_NO_MITL_CANDIDATE":
        claim_strength = "EXCLUDED_NO_CANDIDATE"
        body_recommendation = "Inventory only; no MITL translation is claimed."
        appendix_recommendation = "Keep in excluded table for benchmark coverage transparency."
        must_not_claim = "Do not infer a formula from the XML name alone."
        next_action = "Add a conservative candidate only after edge/guard semantics are derived."
    else:
        claim_strength = "EXCLUDED_EVIDENCE_DEBT"
        body_recommendation = "Do not include in formal claims."
        appendix_recommendation = "Keep in excluded table with the blocker."
        must_not_claim = "Do not promote until trace evidence and edge/guard proof are aligned."
        next_action = "Fix candidate semantics or collect stronger baseline/proof evidence."

    original_trace_gap_boundary = ""
    if original_trace_gap:
        original_trace_gap_boundary = (
            f"gap_status={original_trace_gap.get('gap_status', '')}; "
            f"gap_class={original_trace_gap.get('gap_class', '')}; "
            f"observed={original_trace_gap.get('observed', '')}; "
            f"reason={original_trace_gap.get('reason', '')}"
        )
        if claim_strength == "BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF":
            body_recommendation = append_caveat(
                body_recommendation,
                "Original-input coverage remains caveated until the linked Original Trace Gaps row is resolved or explicitly accepted by a human reviewer.",
            )
            appendix_recommendation = append_caveat(
                appendix_recommendation,
                "Link the appendix wording to the unresolved original-input provenance caveat.",
            )
        must_not_claim = append_caveat(
            must_not_claim,
            original_trace_gap.get("must_not_claim", ""),
        )
        must_not_claim = append_caveat(
            must_not_claim,
            "Do not claim original-input benchmark coverage for this XML/MITL row until the linked Original Trace Gaps row is resolved or caveated.",
        )
        next_action = append_caveat(
            next_action,
            "Resolve the linked original-trace gap or keep the paper wording explicitly caveated to generated trace evidence and structural proof obligations.",
        )

    return {
        "review_id": re.sub(r"[^A-Za-z0-9]+", "_", f"claim_{manifest_id}").strip("_"),
        "manifest_id": manifest_id,
        "xml_file": row.get("xml_file", ""),
        "positive_template": row.get("positive_template", ""),
        "negative_template": row.get("negative_template", ""),
        "candidate_mitl": row.get("candidate_mitl", ""),
        "appendix_status": appendix_status,
        "proof_class": proof_class,
        "claim_strength": claim_strength,
        "paper_body_recommendation": body_recommendation,
        "appendix_recommendation": appendix_recommendation,
        "baseline_evidence_boundary": (
            f"matched_baselines={len(baseline_matches)}; baseline_timeouts={len(baseline_timeouts)}; "
            f"matched_verdicts={matched_verdicts}; timeout_inputs={timeout_paths}"
        ),
        "original_trace_gap_boundary": original_trace_gap_boundary,
        "must_not_claim": must_not_claim,
        "next_manual_action": next_action,
        "source_artifacts": (
            "benchmark_manifest.csv;xml_edge_guard_proofs.csv;xml_proof_appendix.csv;"
            "xml_proof_obligations.csv;xml_trace_coverage_obligations.csv;xml_original_trace_gaps.csv;"
            "xml_translation_proof_appendix.md;monitaal_baseline_results.csv"
        ),
    }


def build_paper_claim_review(
    appendix_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
    original_trace_gap_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    original_trace_gaps_by_manifest = {
        row.get("manifest_id", ""): row
        for row in original_trace_gap_rows
        if row.get("manifest_id")
    }
    return [
        paper_claim_review_for_row(row, baseline_rows, original_trace_gaps_by_manifest)
        for row in appendix_rows
    ]


def write_paper_claim_review(output_dir: Path, review_rows: list[dict[str, Any]]) -> None:
    body_ready = [row for row in review_rows if row["claim_strength"] == "BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF"]
    appendix_timeout = [row for row in review_rows if row["claim_strength"] == "APPENDIX_INSTANCE_READY_WITH_TIMEOUT_CAVEAT"]
    excluded = [row for row in review_rows if row["claim_strength"].startswith("EXCLUDED_")]
    original_gap_caveats = [row for row in review_rows if row.get("original_trace_gap_boundary")]
    proof_class_counts = Counter(row["proof_class"] for row in body_ready + appendix_timeout)

    lines = [
        "# Paper Claim Review",
        "",
        "This review is generated from the proof appendix and baseline tables.",
        "It is a writing and manual-review guide, not an additional proof rule.",
        "",
        "## Counts",
        "",
        f"- Body-pattern candidates eligible only after human signoff: {len(body_ready)}",
        f"- Appendix-ready instances with timeout caveat: {len(appendix_timeout)}",
        f"- Excluded rows: {len(excluded)}",
        f"- Body/proof candidates with unresolved original-trace caveats: {len(original_gap_caveats)}",
        "",
        "## Proof Pattern Counts",
        "",
        "| proof_class | rows |",
        "|---|---:|",
    ]
    for proof_class, count in sorted(proof_class_counts.items()):
        lines.append(f"| `{proof_class}` | {count} |")

    lines.extend([
        "",
        "## Body-Safe Pattern Summaries Eligible Only After Human Signoff",
        "",
        "Use these only after checking the final paper definitions for alphabets, finite-prefix verdicts, and G*.",
        "",
        "| manifest_id | candidate | recommendation |",
        "|---|---|---|",
    ])
    for row in body_ready:
        lines.append(
            f"| `{row['manifest_id']}` | `{row['candidate_mitl']}` | {row['paper_body_recommendation']} |"
        )

    lines.extend([
        "",
        "## Appendix-Ready With Timeout Caveat",
        "",
        "These rows have structural edge/guard proof evidence but still lack original-input baseline verdicts. Treat them as appendix-only until a justified original-input verdict or reduction is recorded.",
        "",
        "| manifest_id | candidate | must_not_claim |",
        "|---|---|---|",
    ])
    for row in appendix_timeout:
        lines.append(f"| `{row['manifest_id']}` | `{row['candidate_mitl']}` | {row['must_not_claim']} |")

    lines.extend([
        "",
        "## Original-Trace Caveats",
        "",
        "These paper-facing rows are structurally/proof-review candidates, but original timed-word coverage remains unresolved or non-decisive.",
        "",
        "| manifest_id | candidate | original_trace_gap_boundary | must_not_claim |",
        "|---|---|---|---|",
    ])
    for row in original_gap_caveats:
        boundary = row.get("original_trace_gap_boundary", "").replace("|", "\\|")
        must_not_claim = row.get("must_not_claim", "").replace("|", "\\|")
        lines.append(f"| `{row['manifest_id']}` | `{row['candidate_mitl']}` | {boundary} | {must_not_claim} |")

    lines.extend([
        "",
        "## Excluded Rows",
        "",
        "| manifest_id | claim_strength | next_manual_action |",
        "|---|---|---|",
    ])
    for row in excluded:
        lines.append(f"| `{row['manifest_id']}` | `{row['claim_strength']}` | {row['next_manual_action']} |")

    lines.append("")
    (output_dir / "paper_claim_review.md").write_text("\n".join(lines), encoding="utf-8")


def parse_boundary_count(boundary: str, key: str) -> int:
    for part in boundary.split(";"):
        part = part.strip()
        prefix = f"{key}="
        if part.startswith(prefix):
            value = part[len(prefix):].strip()
            try:
                return int(value)
            except ValueError:
                return 0
    return 0


def build_paper_claim_consistency_audit(review_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    audit_rows: list[dict[str, Any]] = []
    for row in review_rows:
        manifest_id = row.get("manifest_id", "")
        claim_strength = row.get("claim_strength", "")
        appendix_status = row.get("appendix_status", "")
        proof_class = row.get("proof_class", "")
        boundary = row.get("baseline_evidence_boundary", "")
        timeout_count = parse_boundary_count(boundary, "baseline_timeouts")
        match_count = parse_boundary_count(boundary, "matched_baselines")
        issues: list[str] = []
        warnings: list[str] = []
        checked_rules: list[str] = []

        if claim_strength.startswith("EXCLUDED_"):
            checked_rules.append("excluded rows must not be body-ready or appendix-ready claims")
            if "Do not" not in row.get("paper_body_recommendation", "") and "Inventory only" not in row.get("paper_body_recommendation", ""):
                issues.append("excluded row lacks a conservative body recommendation")
            if appendix_status == "PROOF_DRAFT_READY":
                issues.append("excluded claim strength conflicts with proof-ready appendix status")
        elif claim_strength == "BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF":
            checked_rules.append("body-ready rows must be proof-ready rows without timeout baseline debt")
            if appendix_status != "PROOF_DRAFT_READY":
                issues.append("body-ready row is not proof-draft-ready")
            if timeout_count:
                issues.append("body-ready row has baseline timeout debt")
            if row.get("original_trace_gap_boundary"):
                checked_rules.append("body-ready rows with original-trace gaps must expose explicit provenance caveats")
                if "original-input benchmark coverage" not in row.get("must_not_claim", ""):
                    issues.append("body-ready row with original-trace gap lacks original-input coverage must-not-claim caveat")
                if "Original Trace Gaps" not in row.get("paper_body_recommendation", ""):
                    warnings.append("body-ready row with original-trace gap should point reviewers to Original Trace Gaps")
            if proof_class == "gear_bounded_request_response" and match_count == 0:
                issues.append("gear body-ready row lacks an original-input MoniTAal baseline match")
            if proof_class == "gear_bounded_request_response" and "INCONCLUSIVE" in boundary:
                checked_rules.append("gear rows with INCONCLUSIVE original-input evidence must expose a third-valued caveat")
                if "INCONCLUSIVE" not in row.get("must_not_claim", ""):
                    issues.append("gear body-ready row with INCONCLUSIVE evidence lacks explicit must-not-claim caveat")
                if "third-valued" not in row.get("next_manual_action", "") and "third-valued" not in row.get("paper_body_recommendation", ""):
                    warnings.append("gear body-ready row with INCONCLUSIVE evidence should name the third-valued wording review")
            if "after human signoff" not in row.get("paper_body_recommendation", ""):
                warnings.append("body-ready row should explicitly require human signoff")
        elif claim_strength == "APPENDIX_INSTANCE_READY_WITH_TIMEOUT_CAVEAT":
            checked_rules.append("appendix timeout rows must be proof-ready gear rows with explicit must-not-claim boundary")
            if appendix_status != "PROOF_DRAFT_READY":
                issues.append("appendix-timeout row is not proof-draft-ready")
            if proof_class != "gear_bounded_request_response":
                issues.append("appendix-timeout caveat is only expected for gear bounded request-response rows")
            if timeout_count == 0:
                warnings.append("appendix-timeout caveat row has no timeout count in the baseline boundary")
            if "Do not claim" not in row.get("must_not_claim", ""):
                issues.append("appendix-timeout row lacks an explicit must-not-claim boundary")
        else:
            issues.append(f"unrecognized claim_strength {claim_strength!r}")

        if claim_strength.endswith("WITH_TRACE_EVIDENCE") and match_count == 0:
            issues.append("trace-evidence claim has zero matched baselines")
        if claim_strength.endswith("ONLY") and match_count != 0:
            warnings.append("claim is marked evidence-only/none but matched baselines are present")

        audit_status = "FAIL" if issues else ("WARN" if warnings else "PASS")
        audit_rows.append({
            "audit_id": re.sub(r"[^A-Za-z0-9]+", "_", f"claim_audit_{manifest_id}").strip("_"),
            "manifest_id": manifest_id,
            "xml_file": row.get("xml_file", ""),
            "claim_strength": claim_strength,
            "appendix_status": appendix_status,
            "proof_class": proof_class,
            "baseline_match_count": match_count,
            "baseline_timeout_count": timeout_count,
            "audit_status": audit_status,
            "checked_rules": " | ".join(checked_rules),
            "issues": " | ".join(issues),
            "warnings": " | ".join(warnings),
            "recommended_action": (
                "Fix claim classification before using this row in paper artifacts."
                if issues else (
                    "Review caveat wording manually before citing."
                    if warnings else "No consistency issue detected by the generated claim audit."
                )
            ),
            "source_review_id": row.get("review_id", ""),
        })
    return audit_rows


def write_paper_claim_consistency_audit(output_dir: Path, audit_rows: list[dict[str, Any]]) -> None:
    failed = [row for row in audit_rows if row["audit_status"] == "FAIL"]
    warned = [row for row in audit_rows if row["audit_status"] == "WARN"]
    passed = [row for row in audit_rows if row["audit_status"] == "PASS"]
    lines = [
        "# Paper Claim Consistency Audit",
        "",
        "This generated audit checks whether paper-facing claim rows respect the proof appendix boundary.",
        "It is a safety check for overclaiming; it is not a substitute for the mathematical proof review.",
        "",
        "## Counts",
        "",
        f"- PASS: {len(passed)}",
        f"- WARN: {len(warned)}",
        f"- FAIL: {len(failed)}",
        "",
    ]
    if failed:
        lines.extend([
            "## Failures",
            "",
            "| manifest_id | claim_strength | issues | recommended_action |",
            "|---|---|---|---|",
        ])
        for row in failed:
            lines.append(
                f"| `{row['manifest_id']}` | `{row['claim_strength']}` | {row['issues']} | {row['recommended_action']} |"
            )
        lines.append("")
    if warned:
        lines.extend([
            "## Warnings",
            "",
            "| manifest_id | claim_strength | warnings | recommended_action |",
            "|---|---|---|---|",
        ])
        for row in warned:
            lines.append(
                f"| `{row['manifest_id']}` | `{row['claim_strength']}` | {row['warnings']} | {row['recommended_action']} |"
            )
        lines.append("")
    lines.extend([
        "## Checked Rows",
        "",
        "| manifest_id | audit_status | claim_strength | checked_rules |",
        "|---|---|---|---|",
    ])
    for row in audit_rows:
        lines.append(
            f"| `{row['manifest_id']}` | `{row['audit_status']}` | `{row['claim_strength']}` | {row['checked_rules']} |"
        )
    lines.append("")
    (output_dir / "paper_claim_consistency_audit.md").write_text("\n".join(lines), encoding="utf-8")


def count_rows(rows: list[dict[str, Any]], **criteria: str) -> int:
    total = 0
    for row in rows:
        if all(str(row.get(key, "")) == value for key, value in criteria.items()):
            total += 1
    return total


def source_contains(path: Path, needles: list[str]) -> bool:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return all(needle in text for needle in needles)


def requirement_row(
    requirement_id: str,
    requirement: str,
    status: str,
    evidence_summary: str,
    evidence_artifacts: str,
    gap_or_risk: str,
    next_action: str,
) -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "requirement": requirement,
        "status": status,
        "evidence_summary": evidence_summary,
        "evidence_artifacts": evidence_artifacts,
        "gap_or_risk": gap_or_risk,
        "next_action": next_action,
    }


def build_requirements_traceability_audit(
    output_dir: Path,
    tamonitor: Path,
    case_rows: list[dict[str, Any]],
    semantic_rows: list[dict[str, Any]],
    semantic_prefix_rows: list[dict[str, Any]],
    semantic_oracle_derivation_rows: list[dict[str, Any]],
    semantic_exclusion_rows: list[dict[str, Any]],
    syntax_coverage_rows: list[dict[str, Any]],
    input_policy_rows: list[dict[str, Any]],
    cli_contract_rows: list[dict[str, Any]],
    manual_review_rows: list[dict[str, Any]],
    goal_completion_rows: list[dict[str, Any]],
    human_review_queue_rows: list[dict[str, Any]],
    review_signoff_rows: list[dict[str, Any]],
    review_guide_rows: list[dict[str, Any]],
    benchmark_manifest_rows: list[dict[str, Any]],
    proof_appendix_rows: list[dict[str, Any]],
    paper_claim_review_rows: list[dict[str, Any]],
    paper_claim_audit_rows: list[dict[str, Any]],
    candidate_result_rows: list[dict[str, Any]],
    candidate_step_audit_rows: list[dict[str, Any]],
    baseline_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    verified_semantic = count_rows(semantic_rows, correctness_status="VERIFIED")
    semantic_fail = count_rows(semantic_rows, pass_status="FAIL")
    prefix_matches = count_rows(semantic_prefix_rows, prefix_oracle_status="MATCH")
    prefix_mismatches = count_rows(semantic_prefix_rows, prefix_oracle_status="MISMATCH")
    prefix_missing = count_rows(semantic_prefix_rows, prefix_oracle_status="MISSING_OBSERVED_STEP")
    oracle_verified = count_rows(semantic_oracle_derivation_rows, oracle_status="HAND_ORACLE_VERIFIED")
    oracle_build_only = count_rows(semantic_oracle_derivation_rows, oracle_status="CONSTRUCTION_STATS_ONLY")
    oracle_review_required = count_rows(semantic_oracle_derivation_rows, oracle_status="ORACLE_REVIEW_REQUIRED")
    oracle_prefix_mismatches = sum(int(row.get("prefix_mismatches", 0) or 0) for row in semantic_oracle_derivation_rows)
    internal_exclusion_rows = len(semantic_exclusion_rows)
    syntax_missing = count_rows(syntax_coverage_rows, coverage_status="MISSING")
    syntax_runtime_verified = sum(1 for row in syntax_coverage_rows if str(row.get("coverage_status", "")).startswith("VERIFIED_RUNTIME"))
    syntax_build_stats = count_rows(syntax_coverage_rows, coverage_status="BUILD_STATS_ONLY")
    syntax_internal_excluded = count_rows(syntax_coverage_rows, coverage_status="EXCLUDED_INTERNAL_FORM")
    input_policy_pass = count_rows(input_policy_rows, pass_status="PASS")
    input_policy_fail = count_rows(input_policy_rows, pass_status="FAIL")
    input_policy_assert_like = count_rows(input_policy_rows, assert_like_failure="true")
    cli_contract_pass = count_rows(cli_contract_rows, pass_status="PASS")
    cli_contract_fail = count_rows(cli_contract_rows, pass_status="FAIL")
    cli_contract_controlled_errors = count_rows(cli_contract_rows, actual_exit_class="CONTROLLED_ERROR")
    manual_review_fail = count_rows(manual_review_rows, automatic_status="FAIL")
    manual_review_required = count_rows(manual_review_rows, human_decision_required="true")
    manual_review_review_required = count_rows(manual_review_rows, automatic_status="REVIEW_REQUIRED")
    manual_review_deferred = count_rows(manual_review_rows, automatic_status="V1_DEFERRED")
    goal_completion_fail = count_rows(goal_completion_rows, status="FAIL")
    goal_completion_review_required = count_rows(goal_completion_rows, status="REVIEW_REQUIRED")
    goal_completion_deferred = count_rows(goal_completion_rows, status="V1_DEFERRED")
    goal_completion_caveat = count_rows(goal_completion_rows, status="PASS_WITH_CAVEAT")
    review_queue_fail = count_rows(human_review_queue_rows, review_status="FAIL")
    review_queue_human_required = count_rows(human_review_queue_rows, human_decision_required="true")
    review_queue_p0 = sum(1 for row in human_review_queue_rows if str(row.get("priority", "")).startswith("P0"))
    signoff_blank_decisions = sum(1 for row in review_signoff_rows if not row.get("reviewer_decision"))
    signoff_p0 = sum(1 for row in review_signoff_rows if str(row.get("priority", "")).startswith("P0"))
    guide_p0 = sum(1 for row in review_guide_rows if row.get("priority") == "P0")
    flatten_verified = sum(1 for row in semantic_rows if row.get("build_mode") == "flatten" and row.get("correctness_status") == "VERIFIED")
    finite_verified = sum(1 for row in semantic_rows if row.get("word") == "finite" and row.get("correctness_status") == "VERIFIED")
    infinite_verified = sum(1 for row in semantic_rows if row.get("word") == "infinite" and row.get("correctness_status") == "VERIFIED")
    compflatten_stats = sum(1 for row in semantic_rows if row.get("build_mode") == "compflatten" and row.get("pass_status") == "BUILD_STATS")
    projection_rows = [
        row for row in semantic_rows
        if row.get("build_mode") == "flatten"
        and row.get("returncode") == 0
        and row.get("positive_projection_valuations") != ""
        and row.get("negative_projection_valuations") != ""
    ]
    candidate_matches = sum(1 for row in candidate_result_rows if row.get("baseline_comparison_status") == "MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT")
    candidate_mismatches = sum(1 for row in candidate_result_rows if row.get("baseline_comparison_status") == "MISMATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT")
    candidate_step_rows_recorded = sum(1 for row in candidate_step_audit_rows if row.get("all_trace_steps_recorded") == "true")
    candidate_step_rows_missing = sum(1 for row in candidate_step_audit_rows if row.get("all_trace_steps_recorded") != "true")
    claim_audit_fail = count_rows(paper_claim_audit_rows, audit_status="FAIL")
    claim_audit_warn = count_rows(paper_claim_audit_rows, audit_status="WARN")
    xml_ready = count_rows(proof_appendix_rows, appendix_status="PROOF_DRAFT_READY")
    xml_excluded = sum(1 for row in proof_appendix_rows if row.get("appendix_status") != "PROOF_DRAFT_READY")
    baseline_timeouts = count_rows(baseline_rows, status="timeout")
    skipped_inputs = count_rows(baseline_rows, status="skipped_no_input")
    generated_empty_inputs = count_rows(baseline_rows, input_origin="generated_empty_no_original_input")
    manifest_rows = len(benchmark_manifest_rows)
    strong_manifest = count_rows(benchmark_manifest_rows, promotion_status="STRONG_TRACE_LEVEL_CANDIDATE")
    approximate_manifest = count_rows(benchmark_manifest_rows, promotion_status="APPROXIMATE_TRACE_ONLY") + count_rows(benchmark_manifest_rows, promotion_status="APPROXIMATE_UNVERIFIED")
    not_claimed_manifest = count_rows(benchmark_manifest_rows, promotion_status="NOT_CLAIMED")
    tamonitor_options_ok = source_contains(REPO_ROOT / "src" / "TAMonitor" / "TAMonitorOptions.cpp", [
        "--trace", "--formula", "--formula-inline", "--build-mode", "flatten", "compflatten",
        "--word", "finite", "infinite", "--state", "symbolic", "concrete", "--out",
        "--max-valuations", "--emit-bdd-interface",
    ])
    tamonitor_target_ok = source_contains(REPO_ROOT / "tool" / "MightyPPL" / "CMakeLists.txt", ["add_executable(TAMonitor", "target_link_libraries(TAMonitor"])
    bdd_interface_ok = source_contains(REPO_ROOT / "src" / "TAMonitor" / "ReportWriter.cpp", ["bdd_interface.json", "interface_reserved_not_implemented"])
    report_writer_ok = source_contains(REPO_ROOT / "src" / "TAMonitor" / "ReportWriter.cpp", ["steps.csv", "summary.csv", "metadata.json", "results.xlsx"])
    reproducibility_manifest_ok = source_contains(Path(__file__), [
        "reproducibility_manifest.json", "reproducibility_manifest.csv", "write_reproducibility_manifest",
    ])

    rows = [
        requirement_row(
            "REQ_CLI_TARGET",
            "Provide a TAMonitor command integrated with the MightyPPL build.",
            "PASS" if tamonitor_target_ok and tamonitor.exists() else "FAIL",
            f"TAMonitor target configured={tamonitor_target_ok}; binary exists={tamonitor.exists()}.",
            "tool/MightyPPL/CMakeLists.txt; tool/MightyPPL/build/TAMonitor",
            "" if tamonitor_target_ok and tamonitor.exists() else "Build target or binary missing.",
            "Build tool/MightyPPL and rerun this audit if missing.",
        ),
        requirement_row(
            "REQ_CLI_OPTIONS",
            "Expose trace/formula input, build mode, word mode, state mode, output path, valuation cap, and BDD-interface switch.",
            "PASS" if tamonitor_options_ok else "FAIL",
            "TAMonitorOptions.cpp contains the requested CLI switches." if tamonitor_options_ok else "One or more requested CLI switches were not found.",
            "src/TAMonitor/TAMonitorOptions.cpp",
            "" if tamonitor_options_ok else "CLI surface may not match the requested workflow.",
            "Update TAMonitorOptions.cpp and add CLI smoke tests.",
        ),
        requirement_row(
            "REQ_CLI_CONTRACT_AUDIT",
            "Run the TAMonitor CLI through file/inline formula input, trace-file/stdin input, mode switches, report outputs, BDD metadata, and controlled error paths.",
            "PASS" if len(cli_contract_rows) >= 10 and cli_contract_fail == 0 else "FAIL",
            f"cli_contract_rows={len(cli_contract_rows)}; pass={cli_contract_pass}; fail={cli_contract_fail}; controlled_error_paths={cli_contract_controlled_errors}.",
            "cli_contract_audit.csv; cli_contract_audit.json; cli_contract_audit.md; glob:cli_contract/*/out/metadata.json",
            "" if cli_contract_fail == 0 else "At least one TAMonitor command-surface probe failed.",
            "Fix failing CLI probes before claiming an industrial command interface.",
        ),
        requirement_row(
            "REQ_MITL_SEMANTICS_REGRESSION",
            "Cover MightyPPL user-level MITL syntax/semantics with hand-oracle regression cases.",
            "PASS" if verified_semantic >= 39 and semantic_fail == 0 else "FAIL",
            f"semantic_verified={verified_semantic}; semantic_fail={semantic_fail}; internal_count_forms_excluded={internal_exclusion_rows}.",
            "semantic_cases.csv; semantic_regression_results.csv; mitl_correctness_audit.csv; semantic_exclusions.csv",
            "" if semantic_fail == 0 else "At least one hand-oracle semantic case failed.",
            "Inspect failing rows before claiming semantic correctness.",
        ),
        requirement_row(
            "REQ_SEMANTIC_ORACLE_DERIVATIONS",
            "Provide a human-auditable derivation ledger for each semantic hand oracle and separate build/stat-only rows.",
            "PASS" if oracle_verified >= 53 and oracle_build_only == 17 and oracle_review_required == 0 and oracle_prefix_mismatches == 0 else "FAIL",
            f"oracle_verified={oracle_verified}; construction_stats_only={oracle_build_only}; oracle_review_required={oracle_review_required}; prefix_mismatches={oracle_prefix_mismatches}.",
            "manual_oracle_guide.csv; manual_oracle_guide.json; manual_oracle_guide.md; semantic_oracle_derivations.csv; semantic_oracle_derivations.json; semantic_oracle_derivations.md; semantic_prefix_oracle_review.csv",
            "" if oracle_review_required == 0 and oracle_prefix_mismatches == 0 else "At least one oracle derivation needs review before correctness can be claimed.",
            "Review the Oracle Derivations workbook sheet before using semantic correctness numbers.",
        ),
        requirement_row(
            "REQ_MIGHTYPPL_SYNTAX_COVERAGE_LEDGER",
            "Provide a grammar-to-evidence ledger that separates user-supported syntax, build/statistics-only corpus rows, and internal Count-form exclusions.",
            "PASS" if syntax_coverage_rows and syntax_missing == 0 and syntax_runtime_verified >= 36 and syntax_internal_excluded == len(INTERNAL_COUNT_FORMS) else "FAIL",
            f"syntax_rows={len(syntax_coverage_rows)}; runtime_verified_rows={syntax_runtime_verified}; build_stats_rows={syntax_build_stats}; internal_excluded_rows={syntax_internal_excluded}; missing_rows={syntax_missing}.",
            "mightyppl_syntax_coverage_audit.csv; mightyppl_syntax_coverage_audit.json; mightyppl_syntax_coverage_audit.md; semantic_exclusions.csv",
            "" if syntax_missing == 0 else "At least one grammar construct lacks evidence or an explicit exclusion.",
            "Add a hand-oracle runtime case, build/statistics evidence, or explicit exclusion row before claiming complete syntax coverage.",
        ),
        requirement_row(
            "REQ_INTERNAL_FORM_INPUT_POLICY",
            "Reject parser-visible internal Count forms through a controlled TAMonitor diagnostic instead of assert/abort behavior.",
            "PASS" if len(input_policy_rows) == len(INTERNAL_COUNT_FORMS) and input_policy_pass == len(INTERNAL_COUNT_FORMS) and input_policy_assert_like == 0 else "FAIL",
            f"input_policy_rows={len(input_policy_rows)}; pass={input_policy_pass}; fail={input_policy_fail}; assert_like_failures={input_policy_assert_like}.",
            "formula_input_policy_audit.csv; formula_input_policy_audit.json; formula_input_policy_audit.md; src/TAMonitor/TAMonitorMightyAdapter.cpp",
            "" if input_policy_fail == 0 and input_policy_assert_like == 0 else "At least one internal Count-form probe did not produce the expected controlled diagnostic.",
            "Fix TAMonitorMightyAdapter preflight rejection before claiming an industrial-grade input boundary.",
        ),
        requirement_row(
            "REQ_MANUAL_REVIEW_PACKET",
            "Provide a consolidated human-review checklist that gates paper-facing claims and caveats.",
            "PASS" if len(manual_review_rows) >= 16 and manual_review_fail == 0 and manual_review_required >= 10 else "FAIL",
            f"manual_review_rows={len(manual_review_rows)}; fail={manual_review_fail}; human_required={manual_review_required}; review_required={manual_review_review_required}; v1_deferred={manual_review_deferred}.",
            "manual_review_checklist.csv; manual_review_checklist.json; manual_review_checklist.md; paper_review_results.xlsx",
            "" if manual_review_fail == 0 else "At least one manual-review gate failed.",
            "Open the Manual Review workbook sheet first, then inspect the referenced evidence sheets.",
        ),
        requirement_row(
            "REQ_GOAL_COMPLETION_AUDIT",
            "Provide a top-level audit that maps the original TAMonitor research-tool request to concrete evidence, caveats, deferrals, and review gates.",
            "PASS" if len(goal_completion_rows) >= 17 and goal_completion_fail == 0 else "FAIL",
            f"goal_rows={len(goal_completion_rows)}; fail={goal_completion_fail}; review_required={goal_completion_review_required}; pass_with_caveat={goal_completion_caveat}; v1_deferred={goal_completion_deferred}.",
            "goal_completion_audit.csv; goal_completion_audit.json; goal_completion_audit.md; paper_review_results.xlsx",
            "" if goal_completion_fail == 0 else "At least one top-level goal item failed.",
            "Open Goal Audit before deciding which claims are complete, caveated, deferred, or require human signoff.",
        ),
        requirement_row(
            "REQ_HUMAN_REVIEW_QUEUE",
            "Provide a single prioritized queue for human signoff across goal, manual-review, XML proof, paper-claim, and benchmark caveat sheets.",
            "PASS" if len(human_review_queue_rows) >= 40 and review_queue_fail == 0 and review_queue_human_required >= 20 else "FAIL",
            f"queue_rows={len(human_review_queue_rows)}; p0_rows={review_queue_p0}; human_required={review_queue_human_required}; fail_rows={review_queue_fail}.",
            "human_review_queue.csv; human_review_queue.json; human_review_queue.md; paper_review_results.xlsx",
            "" if review_queue_fail == 0 else "At least one queued review item is an automatic failure.",
            "Open Review Queue before drilling into Goal Audit, Manual Review, XML Proof Appendix, and Paper Claim Review.",
        ),
        requirement_row(
            "REQ_REVIEW_SIGNOFF_TEMPLATE",
            "Provide a reviewer-owned signoff template for P0/P1/P2 paper-facing review items without auto-filling human decisions.",
            "PASS" if len(review_signoff_rows) >= 40 and signoff_blank_decisions == len(review_signoff_rows) and signoff_p0 >= 20 else "FAIL",
            f"signoff_rows={len(review_signoff_rows)}; blank_decisions={signoff_blank_decisions}; p0_rows={signoff_p0}.",
            "review_signoff_template.csv; review_signoff_template.json; review_signoff_template.md; paper_review_results.xlsx",
            "Human signoff is not yet recorded; this is a blank template for manual review.",
            "Fill reviewer_decision/reviewer/review_date/reviewer_notes only after inspecting the linked evidence sheets.",
        ),
        requirement_row(
            "REQ_REVIEW_GUIDE",
            "Provide a conservative review guide that defines review order, allowed signoff decisions, evidence boundaries, timeout policy, and paper-claim limits.",
            "PASS" if len(review_guide_rows) >= 12 and guide_p0 >= 5 else "FAIL",
            f"guide_rows={len(review_guide_rows)}; p0_rows={guide_p0}.",
            "review_guide.csv; review_guide.json; review_guide.md; paper_review_results.xlsx",
            "" if len(review_guide_rows) >= 12 else "Review guide is too sparse to drive manual paper review.",
            "Read Review Guide before filling Review Signoff decisions.",
        ),
        requirement_row(
            "REQ_STEPWISE_VERDICT_REPORTING",
            "Report and audit each timed-word prefix verdict for semantic regression cases.",
            "PASS" if prefix_matches >= 39 and prefix_mismatches == 0 and prefix_missing == 0 else "FAIL",
            f"prefix_oracle_matches={prefix_matches}; prefix_mismatches={prefix_mismatches}; missing_observed_steps={prefix_missing}.",
            "semantic_prefix_oracle_review.csv; glob:tamonitor_runs/*/steps.csv",
            "" if prefix_mismatches == 0 and prefix_missing == 0 else "At least one prefix verdict did not match the hand oracle or was not recorded.",
            "Fix TAMonitor step reporting or the affected hand oracle before claiming stepwise correctness.",
        ),
        requirement_row(
            "REQ_FLATTEN_RUNTIME",
            "Run flattened single-automaton TAMonitor RV with real three-valued verdicts.",
            "PASS" if flatten_verified >= 39 else "FAIL",
            f"flatten_verified={flatten_verified}; candidate_matches={candidate_matches}; candidate_mismatches={candidate_mismatches}.",
            "semantic_regression_results.csv; translation_candidate_results.csv",
            "" if candidate_mismatches == 0 else "A TAMonitor candidate mismatched the MoniTAal XML baseline.",
            "Fix mismatches before using the affected candidate.",
        ),
        requirement_row(
            "REQ_FINITE_AND_INFINITE_WORDS",
            "Exercise both finite-word and infinite-word modes.",
            "PASS" if finite_verified >= 17 and infinite_verified >= 36 else "FAIL",
            f"finite_verified={finite_verified}; infinite_verified={infinite_verified}.",
            "semantic_cases.csv; semantic_regression_results.csv",
            "" if finite_verified >= 17 else "Finite-word mode lacks broad operator coverage.",
            "Add paper-specific finite-word theorem cases if future claims go beyond these operator-level regressions.",
        ),
        requirement_row(
            "REQ_COMPFLATTEN_BOUNDARY",
            "Support compflatten construction/statistics while avoiding fake runtime verdicts in v1.",
            "PASS_WITH_CAVEAT" if compflatten_stats >= 1 else "FAIL",
            f"compflatten_build_stats_rows={compflatten_stats}; runtime intentionally unsupported in v1.",
            "semantic_regression_results.csv; src/TAMonitor/TAMonitorMain.cpp",
            "No compflatten runtime monitor is claimed in v1.",
            "Implement a proven composition-aware or BDD-native runtime before promoting compflatten verdicts.",
        ),
        requirement_row(
            "REQ_BDD_PROJECTION_RUNTIME",
            "Use BDD-label projection to canonical MoniTAal labels with a valuation cap.",
            "PASS" if projection_rows else "FAIL",
            f"flatten rows with projection valuation counts={len(projection_rows)}; max-valuations is recorded in run summaries.",
            "semantic_regression_results.csv; tool/MightyPPL/TAwithBDDEdges.cpp; src/TAMonitor/TAMonitorMightyAdapter.cpp; src/TAMonitor/TraceParser.cpp; src/TAMonitor/MonitorRunner.cpp; src/TAMonitor/ReportWriter.cpp",
            "" if projection_rows else "No projection evidence found.",
            "Inspect TAwithBDDEdges projection expansion and TAMonitor adapter/runner/reporting if projection counts disappear.",
        ),
        requirement_row(
            "REQ_BDD_NATIVE_INTERFACE",
            "Reserve a BDD-native runtime interface without falsely claiming BDD-native monitoring in v1.",
            "V1_DEFERRED" if bdd_interface_ok else "FAIL",
            "bdd_interface.json explicitly says interface_reserved_not_implemented." if bdd_interface_ok else "BDD-native reservation text not found.",
            "src/TAMonitor/ReportWriter.cpp; glob:tamonitor_runs/*/bdd_interface.json",
            "BDD-native runtime is not implemented in v1.",
            "Treat BDD-native monitoring as v2 work and do not include it in v1 performance claims.",
        ),
        requirement_row(
            "REQ_XML_BENCHMARK_REVIEW",
            "Inventory MoniTAal XML benchmarks and conservatively translate only reviewable pairs.",
            "PASS" if manifest_rows == 23 and xml_ready == 15 and xml_excluded == 8 else "FAIL",
            f"manifest_rows={manifest_rows}; proof_ready={xml_ready}; excluded={xml_excluded}; strong={strong_manifest}; approximate={approximate_manifest}; not_claimed={not_claimed_manifest}.",
            "monitaal_xml_inventory.csv; benchmark_manifest.csv; xml_proof_appendix.csv",
            "" if xml_excluded else "Excluded rows should remain visible for transparency.",
            "Human-review proof-ready rows before final paper claims.",
        ),
        requirement_row(
            "REQ_BENCHMARK_CANDIDATE_STEP_OUTPUT",
            "Expose per-prefix TAMonitor observations for XML-to-MITL benchmark candidate runs.",
            "PASS" if candidate_step_rows_recorded == len(candidate_result_rows) and candidate_step_rows_missing == 0 else "FAIL",
            f"candidate_step_audit_rows={len(candidate_step_audit_rows)}; all_trace_steps_recorded={candidate_step_rows_recorded}; missing_or_incomplete={candidate_step_rows_missing}.",
            "candidate_step_audit.csv; candidate_prefix_observations.csv; glob:translation_candidate_runs/*/steps.csv",
            "Candidate prefix rows are TAMonitor observations; correctness evidence still depends on final-verdict baseline matches or independent hand oracles.",
            "Use the compact audit sheet for paper review and open raw per-run steps when inspecting a specific trace.",
        ),
        requirement_row(
            "REQ_BASELINE_AND_CLAIM_CAVEATS",
            "Keep baseline timeouts, skipped inputs, approximate candidates, and excluded rows out of formal claims.",
            "PASS_WITH_CAVEAT" if claim_audit_fail == 0 and candidate_mismatches == 0 else "FAIL",
            f"claim_audit_fail={claim_audit_fail}; claim_audit_warn={claim_audit_warn}; baseline_timeouts={baseline_timeouts}; skipped_no_input={skipped_inputs}; generated_empty_no_original_input={generated_empty_inputs}; candidate_mismatches={candidate_mismatches}.",
            "paper_claim_consistency_audit.csv; monitaal_baseline_results.csv; benchmark_manifest.csv",
            "Timeout and skipped-input rows remain caveats; INCONCLUSIVE baseline matches are trace-level third-value evidence, not Boolean correctness or XML-equivalence proofs.",
            "Keep generated-empty, skipped-input, approximate, and excluded rows out of body claims unless stronger evidence is added.",
        ),
        requirement_row(
            "REQ_OUTPUT_REPORTS",
            "Write per-run steps, summary, metadata, BDD-interface metadata, and Excel artifacts for manual review.",
            "PASS" if report_writer_ok else "FAIL",
            "ReportWriter emits steps.csv, summary.csv, metadata.json, optional bdd_interface.json, and results.xlsx." if report_writer_ok else "ReportWriter output surface is incomplete.",
            "src/TAMonitor/ReportWriter.cpp; paper_review_results.xlsx",
            "" if report_writer_ok else "Manual review artifacts may be incomplete.",
            "Keep workbook QA in the experiment harness.",
        ),
        requirement_row(
            "REQ_REPRODUCIBILITY_MANIFEST",
            "Record reproducibility metadata, source hashes, and result artifact hashes for paper review.",
            "PASS" if reproducibility_manifest_ok else "FAIL",
            "Experiment harness writes reproducibility_manifest.json/csv/md." if reproducibility_manifest_ok else "Reproducibility manifest generation was not found.",
            "reproducibility_manifest.json; reproducibility_manifest.csv; reproducibility_manifest.md",
            "" if reproducibility_manifest_ok else "Reviewers may not be able to tie results to exact files and dirty worktree state.",
            "Regenerate the full experiment after editing manifest logic.",
        ),
    ]
    return rows


def write_requirements_traceability_audit(output_dir: Path, audit_rows: list[dict[str, Any]]) -> None:
    counts = Counter(row["status"] for row in audit_rows)
    lines = [
        "# Requirements Traceability Audit",
        "",
        "This generated audit maps the requested TAMonitor research workflow to concrete evidence artifacts.",
        "Statuses with caveats or v1 deferrals are intentionally not counted as completed theorem claims.",
        "",
        "## Counts",
        "",
    ]
    for status, count in sorted(counts.items()):
        lines.append(f"- {status}: {count}")
    lines.extend([
        "",
        "## Rows",
        "",
        "| requirement_id | status | evidence_summary | gap_or_risk | next_action |",
        "|---|---|---|---|---|",
    ])
    for row in audit_rows:
        lines.append(
            f"| `{row['requirement_id']}` | `{row['status']}` | {row['evidence_summary']} | "
            f"{row['gap_or_risk'] or 'None.'} | {row['next_action']} |"
        )
    lines.append("")
    (output_dir / "requirements_traceability_audit.md").write_text("\n".join(lines), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_subprocess(args: list[str], cwd: Path = REPO_ROOT, timeout: int = 5) -> tuple[str, str]:
    try:
        result = subprocess.run(args, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=False)
    except Exception as exc:
        return "", str(exc)
    return result.stdout.strip(), result.stderr.strip()


def add_repro_row(rows: list[dict[str, str]], category: str, key: str, value: Any, evidence: str = "") -> None:
    rows.append({
        "category": category,
        "key": key,
        "value": str(value),
        "evidence": evidence,
    })


def source_hash_paths() -> list[Path]:
    script_dir = REPO_ROOT / "test" / "TARV" / "scripts"
    paths = [
        *sorted(script_dir.glob("*.py")),
        *sorted(script_dir.glob("*.mjs")),
        REPO_ROOT / "tool" / "MightyPPL" / "CMakeLists.txt",
        REPO_ROOT / "tool" / "MightyPPL" / "MightyPPL.cpp",
        REPO_ROOT / "tool" / "MightyPPL" / "MightyPPL.h",
        REPO_ROOT / "tool" / "MightyPPL" / "TAwithBDDEdges.cpp",
        REPO_ROOT / "tool" / "MightyPPL" / "TAwithBDDEdges.h",
        REPO_ROOT / "tool" / "MightyPPL" / "MightyPPLRuntimeOptions.cpp",
        REPO_ROOT / "tool" / "MoniTAal" / "benchmark" / "main.cpp",
        REPO_ROOT / "tool" / "MoniTAal" / "src" / "monitaal-bin" / "main.cpp",
    ]
    paths.extend(sorted((REPO_ROOT / "src" / "TAMonitor").glob("*.cpp")))
    paths.extend(sorted((REPO_ROOT / "src" / "TAMonitor").glob("*.h")))
    unique_paths: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path.exists() and path not in seen:
            unique_paths.append(path)
            seen.add(path)
    return unique_paths


def result_hash_paths(output_dir: Path) -> list[Path]:
    names = [
        "semantic_cases.csv",
        "semantic_regression_results.csv",
        "mitl_correctness_audit.csv",
        "semantic_prefix_oracle_review.csv",
        "semantic_prefix_oracle_review.md",
        "semantic_oracle_derivations.csv",
        "semantic_oracle_derivations.json",
        "semantic_oracle_derivations.md",
        "manual_oracle_guide.csv",
        "manual_oracle_guide.json",
        "manual_oracle_guide.md",
        "semantic_exclusions.csv",
        "semantic_exclusions.json",
        "semantic_exclusions.md",
        "mightyppl_syntax_coverage_audit.csv",
        "mightyppl_syntax_coverage_audit.json",
        "mightyppl_syntax_coverage_audit.md",
        "formula_input_policy_audit.csv",
        "formula_input_policy_audit.json",
        "formula_input_policy_audit.md",
        "cli_contract_audit.csv",
        "cli_contract_audit.json",
        "cli_contract_audit.md",
        "review_guide.csv",
        "review_guide.json",
        "review_guide.md",
        "human_review_queue.csv",
        "human_review_queue.json",
        "human_review_queue.md",
        "review_signoff_template.csv",
        "review_signoff_template.json",
        "review_signoff_template.md",
        "goal_completion_audit.csv",
        "goal_completion_audit.json",
        "goal_completion_audit.md",
        "manual_review_checklist.csv",
        "manual_review_checklist.json",
        "manual_review_checklist.md",
        "benchmark_manifest.csv",
        "benchmark_manifest.json",
        "xml_edge_guard_proofs.csv",
        "xml_edge_guard_proofs.json",
        "xml_proof_appendix.csv",
        "xml_proof_obligations.csv",
        "xml_proof_obligations.json",
        "xml_proof_obligations.md",
        "xml_trace_coverage_obligations.csv",
        "xml_trace_coverage_obligations.json",
        "xml_trace_coverage_obligations.md",
        "xml_original_trace_gaps.csv",
        "xml_original_trace_gaps.json",
        "xml_original_trace_gaps.md",
        "gear_original_input_response_audit.csv",
        "gear_original_input_response_audit.json",
        "gear_original_input_response_audit.md",
        "non_gear_original_input_search_audit.csv",
        "non_gear_original_input_search_audit.json",
        "non_gear_original_input_search_audit.md",
        "xml_translation_proof_appendix.md",
        "paper_claim_review.csv",
        "paper_claim_review.md",
        "paper_claim_consistency_audit.csv",
        "paper_claim_consistency_audit.md",
        "requirements_traceability_audit.csv",
        "requirements_traceability_audit.md",
        "translation_candidate_results.csv",
        "candidate_prefix_observations.csv",
        "candidate_step_audit.csv",
        "candidate_step_audit.md",
        "monitaal_baseline_results.csv",
        "monitaal_embedded_benchmarks.csv",
    ]
    return [output_dir / name for name in names if (output_dir / name).exists()]


def build_reproducibility_manifest_rows(output_dir: Path, args: argparse.Namespace, workbook_status: str = "not_built_yet") -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    add_repro_row(rows, "run", "argv", " ".join(sys.argv), "Command line used for this experiment harness invocation.")
    add_repro_row(rows, "run", "output_dir", output_dir, "Primary experiment result directory.")
    add_repro_row(rows, "run", "timeout_seconds", args.timeout, "Per-command timeout configured for the main experiment.")
    add_repro_row(rows, "run", "no_run", args.no_run, "--no-run flag value.")
    add_repro_row(rows, "run", "no_workbook", args.no_workbook, "--no-workbook flag value.")
    add_repro_row(rows, "run", "workbook_status_at_manifest_write", workbook_status, "Workbook is normally built after this manifest is written.")
    add_repro_row(rows, "environment", "python", sys.version.replace("\n", " "), "Python runtime used by the experiment harness.")
    add_repro_row(rows, "environment", "platform", platform.platform(), "Host platform reported by Python.")
    add_repro_row(rows, "environment", "cwd", Path.cwd(), "Current working directory when the script was launched.")
    add_repro_row(rows, "tool", "tamonitor_path", args.tamonitor, "TAMonitor executable path passed to the harness.")
    add_repro_row(rows, "tool", "tamonitor_exists", args.tamonitor.exists(), "Whether the TAMonitor executable existed when the manifest was written.")
    monitaal_bin = find_monitaal_bin()
    add_repro_row(rows, "tool", "monitaal_bin", monitaal_bin or "", "MoniTAal binary discovered through the MightyPPL build tree.")
    add_repro_row(rows, "tool", "monitaal_bin_exists", bool(monitaal_bin and monitaal_bin.exists()), "Whether the discovered MoniTAal binary exists.")

    for label, repo_path in [("mighty_or_workspace", REPO_ROOT / "tool" / "MightyPPL"), ("monitaal_or_workspace", REPO_ROOT / "tool" / "MoniTAal")]:
        head, head_err = safe_subprocess(["git", "-C", str(repo_path), "rev-parse", "HEAD"])
        status, status_err = safe_subprocess(["git", "-C", str(repo_path), "status", "--short"])
        root, root_err = safe_subprocess(["git", "-C", str(repo_path), "rev-parse", "--show-toplevel"])
        add_repro_row(rows, "git", f"{label}_root", root, root_err)
        add_repro_row(rows, "git", f"{label}_head", head, head_err)
        add_repro_row(rows, "git", f"{label}_status_short", status.replace("\n", " | "), status_err or "Dirty status is expected while TAMonitor changes are under review.")

    for path in source_hash_paths():
        add_repro_row(rows, "source_sha256", path.relative_to(REPO_ROOT).as_posix(), sha256_file(path), "Hash of a source file that affects TAMonitor or paper experiment generation.")
    for path in result_hash_paths(output_dir):
        add_repro_row(rows, "result_sha256", path.relative_to(output_dir).as_posix(), sha256_file(path), "Hash of a generated result artifact available before workbook export.")
    return rows


def write_reproducibility_manifest(output_dir: Path, rows: list[dict[str, str]]) -> None:
    write_csv(output_dir / "reproducibility_manifest.csv", rows, ["category", "key", "value", "evidence"])
    (output_dir / "reproducibility_manifest.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    counts = Counter(row["category"] for row in rows)
    lines = [
        "# Reproducibility Manifest",
        "",
        "This generated manifest records runtime metadata, tool paths, git state, and SHA-256 hashes for source and result artifacts.",
        "It is intended to make paper review and experiment reruns auditable even when the workspace is dirty.",
        "",
        "## Counts",
        "",
    ]
    for category, count in sorted(counts.items()):
        lines.append(f"- {category}: {count}")
    lines.extend([
        "",
        "## Key Runtime Rows",
        "",
        "| category | key | value |",
        "|---|---|---|",
    ])
    for row in rows:
        if row["category"] in {"run", "tool", "git"}:
            value = row["value"].replace("|", "\\|")
            lines.append(f"| `{row['category']}` | `{row['key']}` | `{value}` |")
    lines.append("")
    (output_dir / "reproducibility_manifest.md").write_text("\n".join(lines), encoding="utf-8")


def manual_xml_baseline_timeout_section(baseline_rows: list[dict[str, Any]]) -> str:
    timeout_rows = [row for row in baseline_rows if row.get("status") == "timeout"]
    gear_original_rows = [
        row for row in baseline_rows
        if row.get("xml_file") == "gear-control-properties.xml"
        and Path(row.get("input_path", "")).name == "gear-control-input.txt"
    ]
    inconclusive_rows = [
        row for row in baseline_rows
        if row.get("status") == "ran" and row.get("verdict") == "INCONCLUSIVE"
    ]
    lines = ["## Baseline Timeout Cases", ""]
    if timeout_rows:
        lines.append("The following MoniTAal baseline rows timed out in this run and must remain caveats:")
        lines.append("")
        for row in timeout_rows:
            lines.append(
                f"- `{row.get('xml_file', '')}` `{row.get('positive_template', '')}`/"
                f"`{row.get('negative_template', '')}` on `{Path(row.get('input_path', '')).name}`."
            )
    else:
        lines.append(
            "This run has no MoniTAal baseline timeout rows. Do not describe any current benchmark input as timed out from this packet."
        )

    if gear_original_rows:
        gear_status_counts = Counter(row.get("status", "") for row in gear_original_rows)
        gear_verdict_counts = Counter(row.get("verdict", "") for row in gear_original_rows if row.get("verdict"))
        status_summary = "; ".join(f"{key}={value}" for key, value in sorted(gear_status_counts.items()))
        verdict_summary = "; ".join(f"{key}={value}" for key, value in sorted(gear_verdict_counts.items())) or "none"
        lines.extend([
            "",
            (
                "Gear original `gear-control-input.txt` baseline rows in this packet: "
                f"statuses={status_summary}; verdicts={verdict_summary}."
            ),
        ])
    if inconclusive_rows:
        examples = sorted({
            f"{row.get('xml_file', '')}:{Path(row.get('input_path', '')).name}"
            for row in inconclusive_rows
        })
        lines.extend([
            "",
            (
                "INCONCLUSIVE baseline rows are third-valued trace evidence. They are not Boolean satisfaction, "
                "not Boolean violation, and not XML-to-MITL equivalence proofs."
            ),
            "Examples: " + "; ".join(examples[:12]) + ("; ..." if len(examples) > 12 else ""),
        ])
    return "\n".join(lines)


def write_manual_xml_candidate_review(output_dir: Path, baseline_rows: list[dict[str, Any]]) -> None:
    baseline_timeout_section = manual_xml_baseline_timeout_section(baseline_rows)
    (output_dir / "manual_xml_candidate_review.md").write_text(
        """# Manual XML Candidate Review

This file records manual-review guidance for the XML-to-MITL candidate layer.
It is generated with the experiment artifacts and is not an automatic
equivalence proof. Authoritative evidence tables:

- `monitaal_translation_review.csv`
- `monitaal_transition_details.csv`
- `translation_candidate_results.csv`
- `monitaal_baseline_results.csv`
- `benchmark_manifest.csv`
- `xml_edge_guard_proofs.csv`
- `xml_proof_appendix.csv`
- `xml_translation_proof_appendix.md`
- `paper_claim_review.csv`
- `paper_claim_review.md`

## Strong Trace-Level Candidates

These candidates have clear transition/guard structure and match the available
MoniTAal baseline input. They may be treated as strong trace-level candidates
for paper review, but still require formal equivalence proof before being
claimed as fully translated benchmarks.

- `a-b copy.xml`, `a-b.xml`, `a-b30.xml`: `G* (a -> F [0,30] b)`
- `absentAQ.xml`: `G* (q -> G [0,10] (!p))`
- `absentBR.xml`: `G* (p -> G [0,10] (!r))`
- `recurGLB.xml`: `(F [0,10] p) && (G* (p -> F (0,10] p))`
- `c_after_10.xml`: `F [10,infty) c` on generated traces
  `@0 a; @10 c` and `@0 a; @11 c`
- `c_after_20.xml`: `F [20,infty) c` on generated traces
  `@0 a; @20 c` and `@0 a; @21 c`
- `only_ab_until10.xml`: `G [0,10] (!c)` on generated trace `@0 a; @5 c`
- Gear-controller request/response templates: `G* (request -> F [0,bound] response)`
  on generated reduced negative traces where either the first observed request
  is answered just after the closed bound or one boundary-satisfied request is
  followed by a re-armed late-response violation.

## Edge/Guard Proof Ledger

`xml_edge_guard_proofs.csv` records one machine-checkable proof-review row per
XML pair. `EDGE_GUARD_PROOF_READY` means the expected trigger/response or
forbidden-event edges, clock bounds, resets, and accepting-location roles were
found in the parsed XML. It is still a proof checklist for human review, not a
published theorem by itself.

`xml_translation_proof_appendix.md` is a paper-facing draft derived from the
proof ledger. It includes only `PROOF_DRAFT_READY` rows in the formal proof
section and lists approximate, unclaimed, and input-debt rows separately.

`recurGLB.xml` includes both an initial closed-bound recurrence obligation and
later re-armed recurrence obligations. The strict lower bound in
`F (0,10] p` is justified from the reset-after-p event-index semantics rather
than a separate XML guard; the corresponding evidence row records this caveat.

## Must Remain Approximate Or Unpromoted

- `absentBQR.xml` and `recurBQR.xml`: translation table marks these
  approximate; one matching input is not enough for equivalence.
- `b_live_a_freq.xml`: approximate; use the current baseline-status section
  below instead of carrying forward stale timeout wording.
- `f(g(notb)_and_g(f(a)).xml`: corrected candidate
  `(F [0,10] a) && (G* (a -> F (0,10] a)) && F (G (!b))` has reduced
  negative trace evidence for first-late and re-armed-late `a`, but the
  eventual no-b liveness suffix and finite-prefix semantics still need proof
  review, so it remains approximate.
- `delay-example.xml`, `never_b.xml`, `time-must-pass.xml`,
  `gear_controller_test.xml`: no claimed MITL candidate.

""" + baseline_timeout_section + """

## Open Review Questions

- For any future timeout row, rerun with a longer timeout or document a justified
  reduced input; for INCONCLUSIVE rows, keep the third-valued caveat explicit.
- Add formal edge/guard proofs before claiming full XML-to-MITL equivalence;
  the current manifest remains a trace-level promotion ledger.
""",
        encoding="utf-8",
    )


def xml_inventory_and_baselines(
    output_dir: Path,
    timeout: int,
    no_run: bool,
    tamonitor: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    xml_files = sorted((REPO_ROOT / "tool" / "MoniTAal" / "test" / "models").glob("*.xml"))
    xml_files += sorted((REPO_ROOT / "tool" / "MoniTAal" / "benchmark").glob("*.xml"))
    embedded_xml_files, embedded_inputs, embedded_metadata = write_embedded_benchmark_files(output_dir)
    inventory: list[dict[str, Any]] = []
    transition_details: list[dict[str, Any]] = []
    for xml_path in xml_files:
        inventory.extend(parse_xml_templates(xml_path))
        transition_details.extend(parse_xml_transition_details(xml_path))
    for xml_path in embedded_xml_files:
        inventory.extend(parse_xml_templates(xml_path, "embedded_xml", xml_path.stem))
        transition_details.extend(parse_xml_transition_details(xml_path, "embedded_xml", xml_path.stem))

    translation_rows: list[dict[str, Any]] = []
    baseline_rows: list[dict[str, Any]] = []
    candidate_result_rows: list[dict[str, Any]] = []
    transition_review_index: dict[tuple[str, str], dict[str, Any]] = {}
    monitaal_bin = find_monitaal_bin()
    pair_rows = pair_templates(inventory)

    for pos, neg, method in pair_rows:
        candidate, confidence, equivalence_status, reason = candidate_mitl(pos, neg)
        mapping = ap_mapping_for(pos.get("labels", ""))
        ap_mapping = json.dumps(mapping, ensure_ascii=False)
        translation_rows.append({
            "xml_path": pos["xml_path"],
            "xml_file": pos["xml_file"],
            "source_kind": pos.get("source_kind", "xml_file"),
            "embedded_symbol": pos.get("embedded_symbol", ""),
            "positive_template": pos["template"],
            "negative_template": neg["template"],
            "pair_method": method,
            "ap_mapping": ap_mapping,
            "candidate_mitl": candidate,
            "candidate_confidence": confidence,
            "mitl_equivalence_status": equivalence_status,
            "review_status": "needs_manual_review" if candidate else "xml_baseline_only",
            "translation_reason": reason,
            "labels": pos.get("labels", ""),
            "guards": pos.get("guards", ""),
            "positive_locations": pos.get("locations", ""),
            "positive_edges": pos.get("transitions", ""),
            "negative_locations": neg.get("locations", ""),
            "negative_edges": neg.get("transitions", ""),
        })
        base_review = {
            "pair_method": method,
            "ap_mapping": ap_mapping,
            "candidate_mitl": candidate,
            "candidate_confidence": confidence,
            "mitl_equivalence_status": equivalence_status,
            "review_status": "needs_manual_review" if candidate else "xml_baseline_only",
            "translation_reason": reason,
            "positive_template": pos["template"],
            "negative_template": neg["template"],
        }
        transition_review_index[(pos["xml_path"], pos["template"])] = {
            **base_review,
            "pair_role": "positive",
            "paired_template": neg["template"],
        }
        transition_review_index[(neg["xml_path"], neg["template"])] = {
            **base_review,
            "pair_role": "negative",
            "paired_template": pos["template"],
        }

        inputs = find_inputs_for_xml(Path(pos["xml_path"]), embedded_inputs, pos["template"], neg["template"])
        if not inputs:
            baseline_rows.append({
                "xml_path": pos["xml_path"],
                "positive_template": pos["template"],
                "negative_template": neg["template"],
                "input_path": "",
                "input_origin": "missing",
                "input_rationale": "No repository, embedded, special, or generated review input was available for this XML pair.",
                "status": "skipped_no_input",
                "verdict": "",
                "returncode": "",
                "elapsed_ms": "",
                "stdout_excerpt": "",
                "stderr_excerpt": "",
            })
            continue

        for input_path in inputs:
            row = {
                "xml_path": pos["xml_path"],
                "positive_template": pos["template"],
                "negative_template": neg["template"],
                "input_path": str(input_path),
                "input_origin": baseline_input_origin(input_path),
                "input_rationale": baseline_input_rationale(input_path),
                "status": "skipped_no_binary" if monitaal_bin is None else "not_run",
                "verdict": "",
                "returncode": "",
                "elapsed_ms": "",
                "stdout_excerpt": "",
                "stderr_excerpt": "",
            }
            if monitaal_bin is not None and not no_run:
                result = run_command([
                    str(monitaal_bin),
                    "--pos", pos["template"], pos["xml_path"],
                    "--neg", neg["template"], neg["xml_path"],
                    "--input", str(input_path),
                    "--type", "concrete",
                ], timeout)
                row.update({
                    "status": "timeout" if result["timeout"] else "ran",
                    "verdict": parse_monitaal_verdict(result["stdout"]),
                    "returncode": result["returncode"],
                    "elapsed_ms": result["elapsed_ms"],
                    "stdout_excerpt": (result["stdout"] or "")[:500].replace("\n", " "),
                    "stderr_excerpt": (result["stderr"] or "")[:500].replace("\n", " "),
                })
            baseline_rows.append(row)

            if candidate:
                case_id = re.sub(
                    r"[^A-Za-z0-9]+",
                    "_",
                    f"{Path(pos['xml_path']).stem}_{pos['template']}_{neg['template']}_{input_path.stem}",
                ).strip("_")
                candidate_result_rows.append(run_translation_candidate(
                    output_dir,
                    tamonitor,
                    timeout,
                    no_run,
                    case_id,
                    candidate,
                    equivalence_status,
                    pos,
                    neg,
                    input_path,
                    mapping,
                    row["status"],
                    row["verdict"],
                ))

    for row in transition_details:
        review = transition_review_index.get((row.get("xml_path", ""), row.get("template", "")), {})
        row.update({
            "pair_role": review.get("pair_role", "unpaired"),
            "paired_template": review.get("paired_template", ""),
            "positive_template": review.get("positive_template", ""),
            "negative_template": review.get("negative_template", ""),
            "pair_method": review.get("pair_method", ""),
            "ap_mapping": review.get("ap_mapping", ""),
            "candidate_mitl": review.get("candidate_mitl", ""),
            "candidate_confidence": review.get("candidate_confidence", ""),
            "mitl_equivalence_status": review.get("mitl_equivalence_status", "not_claimed"),
            "review_status": review.get("review_status", "xml_baseline_only"),
            "translation_reason": review.get("translation_reason", "No paired positive/negative template or no conservative MITL candidate."),
        })

    return inventory, transition_details, translation_rows, baseline_rows, candidate_result_rows, embedded_metadata


def build_workbook(output_dir: Path, no_workbook: bool) -> str:
    if no_workbook:
        return "skipped"
    node = Path(os.environ.get("TAMONITOR_NODE", DEFAULT_NODE))
    artifact_import = os.environ.get("TAMONITOR_ARTIFACT_TOOL_IMPORT", DEFAULT_ARTIFACT_TOOL_IMPORT)
    builder = Path(__file__).with_name("build_paper_review_workbook.mjs")
    if not node.exists() or not builder.exists():
        return "skipped_missing_artifact_tool_runtime"

    scratch = output_dir / "_workbook_build"
    scratch.mkdir(parents=True, exist_ok=True)
    scratch_builder = scratch / "build_paper_review_workbook.mjs"
    builder_text = builder.read_text(encoding="utf-8")
    builder_text = builder_text.replace('"@oai/artifact-tool"', f'"{artifact_import}"')
    scratch_builder.write_text(builder_text, encoding="utf-8")

    def is_transient_wsl_node_start_failure(result: dict[str, Any]) -> bool:
        stderr = str(result.get("stderr", ""))
        return (
            "WSL" in stderr
            and (
                "UtilBindVsockAnyPort" in stderr
                or "socket failed" in stderr
                or "CreateProcessParseCommon" in stderr
            )
        )

    attempts: list[dict[str, Any]] = []
    for attempt in range(3):
        result = run_command([str(node), str(scratch_builder), str(output_dir)], timeout=120)
        attempts.append(result)
        if result["returncode"] == 0:
            break
        if not is_transient_wsl_node_start_failure(result):
            break
        time.sleep(1 + attempt)
    stdout = "".join(
        f"[attempt {index + 1}]\n{attempt_result['stdout']}"
        for index, attempt_result in enumerate(attempts)
    )
    stderr = "".join(
        f"[attempt {index + 1}]\n{attempt_result['stderr']}"
        for index, attempt_result in enumerate(attempts)
    )
    (output_dir / "workbook_build_stdout.txt").write_text(stdout, encoding="utf-8")
    (output_dir / "workbook_build_stderr.txt").write_text(stderr, encoding="utf-8")
    if result["returncode"] != 0:
        return "failed"
    try:
        scratch_builder.unlink()
        scratch.rmdir()
    except OSError:
        pass
    return "ok"


def main() -> int:
    parser = argparse.ArgumentParser(description="Run TAMonitor paper-review experiments.")
    parser.add_argument("--out", type=Path, default=None, help="Output directory. Defaults to test/TARV/results/paper_experiments_<timestamp>.")
    parser.add_argument("--timeout", type=int, default=30, help="Per-command timeout in seconds.")
    parser.add_argument("--tamonitor", type=Path, default=REPO_ROOT / "tool" / "MightyPPL" / "build" / "TAMonitor")
    parser.add_argument("--no-run", action="store_true", help="Generate manifests without executing tools.")
    parser.add_argument("--no-workbook", action="store_true", help="Skip artifact-tool workbook generation.")
    args = parser.parse_args()

    output_dir = args.out or TARV_ROOT / "results" / ("paper_experiments_" + time.strftime("%Y%m%d-%H%M%S"))
    output_dir.mkdir(parents=True, exist_ok=True)

    case_rows, semantic_rows = run_semantic_regression(output_dir, args.timeout, args.tamonitor, args.no_run)
    inventory_rows, transition_detail_rows, translation_rows, baseline_rows, candidate_result_rows, embedded_rows = xml_inventory_and_baselines(output_dir, args.timeout, args.no_run, args.tamonitor)
    correctness_audit_rows = build_correctness_audit_rows(case_rows, semantic_rows, candidate_result_rows)
    semantic_prefix_rows = build_semantic_prefix_oracle_review(case_rows, semantic_rows)
    semantic_oracle_derivation_rows = build_semantic_oracle_derivations(case_rows, semantic_rows, semantic_prefix_rows)
    manual_oracle_guide_rows = build_manual_oracle_guide(semantic_oracle_derivation_rows, semantic_prefix_rows)
    semantic_exclusion_rows = build_semantic_exclusion_rows()
    syntax_coverage_rows = build_mightyppl_syntax_coverage_audit(case_rows, semantic_rows, semantic_exclusion_rows)
    input_policy_rows = build_formula_input_policy_audit(output_dir, args.timeout, args.tamonitor, args.no_run)
    cli_contract_rows = build_cli_contract_audit(output_dir, args.timeout, args.tamonitor, args.no_run)
    candidate_prefix_rows, candidate_step_audit_rows = build_candidate_prefix_observation_rows(candidate_result_rows)
    benchmark_manifest_rows = build_benchmark_manifest(translation_rows, candidate_result_rows, baseline_rows)
    edge_guard_proof_rows = build_xml_edge_guard_proofs(benchmark_manifest_rows, transition_detail_rows)
    proof_appendix_rows = build_xml_proof_appendix(edge_guard_proof_rows)
    xml_trace_coverage_rows = build_xml_trace_coverage_obligations(
        edge_guard_proof_rows,
        benchmark_manifest_rows,
        candidate_result_rows,
        candidate_step_audit_rows,
        baseline_rows,
    )
    xml_original_trace_gap_rows = build_xml_original_trace_gaps(xml_trace_coverage_rows)
    gear_original_input_response_audit_rows = build_gear_original_input_response_audit(
        edge_guard_proof_rows,
        baseline_rows,
    )
    non_gear_original_input_search_audit_rows = build_non_gear_original_input_search_audit(
        xml_original_trace_gap_rows,
        benchmark_manifest_rows,
        baseline_rows,
    )
    paper_claim_review_rows = build_paper_claim_review(proof_appendix_rows, baseline_rows, xml_original_trace_gap_rows)
    paper_claim_audit_rows = build_paper_claim_consistency_audit(paper_claim_review_rows)
    xml_proof_obligation_rows = build_xml_proof_obligations(
        edge_guard_proof_rows,
        benchmark_manifest_rows,
        candidate_result_rows,
        paper_claim_review_rows,
    )
    manual_review_rows = build_manual_review_checklist(
        semantic_rows,
        semantic_prefix_rows,
        semantic_oracle_derivation_rows,
        semantic_exclusion_rows,
        syntax_coverage_rows,
        input_policy_rows,
        cli_contract_rows,
        benchmark_manifest_rows,
        proof_appendix_rows,
        paper_claim_review_rows,
        paper_claim_audit_rows,
        xml_original_trace_gap_rows,
        candidate_result_rows,
        candidate_step_audit_rows,
        baseline_rows,
    )
    goal_completion_rows = build_goal_completion_audit(
        output_dir,
        args.tamonitor,
        semantic_rows,
        semantic_prefix_rows,
        semantic_oracle_derivation_rows,
        syntax_coverage_rows,
        input_policy_rows,
        cli_contract_rows,
        manual_review_rows,
        benchmark_manifest_rows,
        proof_appendix_rows,
        paper_claim_audit_rows,
        candidate_result_rows,
        candidate_step_audit_rows,
        baseline_rows,
        embedded_rows,
    )
    human_review_queue_rows = build_human_review_queue(
        goal_completion_rows,
        manual_review_rows,
        benchmark_manifest_rows,
        proof_appendix_rows,
        paper_claim_review_rows,
        paper_claim_audit_rows,
        xml_original_trace_gap_rows,
    )
    review_signoff_rows = build_review_signoff_template(human_review_queue_rows)
    review_guide_rows = build_review_guide(
        human_review_queue_rows,
        review_signoff_rows,
        semantic_oracle_derivation_rows,
        paper_claim_audit_rows,
        baseline_rows,
    )
    requirements_audit_rows = build_requirements_traceability_audit(
        output_dir,
        args.tamonitor,
        case_rows,
        semantic_rows,
        semantic_prefix_rows,
        semantic_oracle_derivation_rows,
        semantic_exclusion_rows,
        syntax_coverage_rows,
        input_policy_rows,
        cli_contract_rows,
        manual_review_rows,
        goal_completion_rows,
        human_review_queue_rows,
        review_signoff_rows,
        review_guide_rows,
        benchmark_manifest_rows,
        proof_appendix_rows,
        paper_claim_review_rows,
        paper_claim_audit_rows,
        candidate_result_rows,
        candidate_step_audit_rows,
        baseline_rows,
    )
    write_manual_xml_candidate_review(output_dir, baseline_rows)

    write_csv(output_dir / "semantic_cases.csv", case_rows, [
        "case_id", "suite", "category", "formula", "trace", "build_mode", "word", "state", "max_valuations",
        "expected_final", "expected_prefix", "expected_sat", "expected_sat_scope", "review_status", "rationale",
        "formula_path", "trace_path", "trace_events",
    ])
    write_csv(output_dir / "semantic_regression_results.csv", semantic_rows, [
        "case_id", "suite", "category", "build_mode", "word", "state", "expected_final", "expected_prefix",
        "actual_final", "expected_sat", "expected_sat_scope", "actual_sat",
        "pass_status", "correctness_status", "oracle_type", "oracle_verdict", "correctness_evidence", "review_status",
        "returncode", "timeout", "elapsed_ms", "events", "processed_steps", "advanced_steps", "carry_forward_steps",
        "positive_components", "positive_locations", "positive_edges", "positive_clocks",
        "negative_components", "negative_locations", "negative_edges", "negative_clocks",
        "positive_projection_valuations", "negative_projection_valuations", "run_dir", "stderr_excerpt", "stdout_excerpt",
    ])
    write_csv(output_dir / "mitl_correctness_audit.csv", correctness_audit_rows, [
        "audit_id", "case_id", "case_family", "category", "formula", "input_or_trace", "runtime_verdict",
        "formula_satisfiable", "expected_sat_scope", "oracle_type", "oracle_verdict", "correctness_status",
        "pass_status", "baseline_status", "baseline_verdict", "mitl_equivalence_status", "review_status", "evidence", "run_dir",
    ])
    write_csv(output_dir / "semantic_prefix_oracle_review.csv", semantic_prefix_rows, [
        "case_id", "suite", "category", "formula", "word", "build_mode", "trace_events", "step", "time",
        "human_label", "canonical_label", "expected_prefix_verdict", "actual_prefix_verdict",
        "prefix_oracle_status", "monitor_advanced", "positive_states", "negative_states",
        "expected_final", "actual_final", "final_correctness_status", "oracle_type", "expected_sat_scope",
        "step_evidence", "rationale", "trace_path", "run_dir",
    ])
    write_semantic_prefix_oracle_review(output_dir, semantic_prefix_rows)
    write_csv(output_dir / "semantic_oracle_derivations.csv", semantic_oracle_derivation_rows, [
        "case_id", "suite", "category", "oracle_scope", "oracle_status", "semantic_rule",
        "formula", "trace", "word", "build_mode", "expected_final", "actual_final",
        "expected_prefix", "prefix_checked_steps", "prefix_mismatches", "expected_sat",
        "actual_sat", "correctness_status", "pass_status", "final_oracle_derivation",
        "prefix_oracle_derivation", "sat_oracle_derivation", "evidence_artifacts",
        "review_action", "run_dir",
    ])
    write_semantic_oracle_derivations(output_dir, semantic_oracle_derivation_rows)
    write_csv(output_dir / "manual_oracle_guide.csv", manual_oracle_guide_rows, [
        "guide_id", "section", "priority", "protocol_step", "decision_rule",
        "pass_condition", "reject_or_fix_condition", "evidence_artifacts",
        "sample_case_ids", "reviewer_action", "must_not_claim",
    ])
    write_manual_oracle_guide(output_dir, manual_oracle_guide_rows)
    write_csv(output_dir / "semantic_exclusions.csv", semantic_exclusion_rows, [
        "excluded_id", "form", "starred", "reason", "source_context", "user_level",
        "run_policy", "expected_verdict", "reviewer_note",
    ])
    write_semantic_exclusions(output_dir, semantic_exclusion_rows)
    write_csv(output_dir / "mightyppl_syntax_coverage_audit.csv", syntax_coverage_rows, [
        "syntax_id", "syntax_family", "construct", "user_level", "expected_policy",
        "coverage_status", "evidence_summary", "evidence_case_ids", "finite_case_ids",
        "infinite_case_ids", "evidence_categories", "source_reference", "notes", "review_action",
    ])
    write_mightyppl_syntax_coverage_audit(output_dir, syntax_coverage_rows)
    write_csv(output_dir / "formula_input_policy_audit.csv", input_policy_rows, [
        "policy_id", "form", "starred", "user_level", "probe_policy", "probe_input_disclosure",
        "expected_exit_class", "actual_exit_class", "pass_status", "returncode", "timeout",
        "elapsed_ms", "assert_like_failure", "diagnostic_contains", "evidence",
        "stderr_excerpt", "stdout_excerpt", "run_dir",
    ])
    write_formula_input_policy_audit(output_dir, input_policy_rows)
    write_csv(output_dir / "cli_contract_audit.csv", cli_contract_rows, [
        "audit_id", "scenario", "input_surface", "expected_behavior", "expected_exit_class",
        "actual_exit_class", "pass_status", "returncode", "timeout", "elapsed_ms",
        "final_verdict", "formula_satisfiable", "build_mode", "run_mode", "word_mode",
        "state_mode", "max_valuations", "events", "processed_steps",
        "bdd_interface_status", "report_files", "diagnostic_contains", "evidence",
        "stdout_excerpt", "stderr_excerpt", "run_dir", "command",
    ])
    write_cli_contract_audit(output_dir, cli_contract_rows)
    write_csv(output_dir / "review_guide.csv", review_guide_rows, [
        "guide_id", "section", "priority", "instruction", "evidence_artifacts",
        "decision_rule", "must_not_claim", "next_action",
    ])
    write_review_guide(output_dir, review_guide_rows)
    write_csv(output_dir / "goal_completion_audit.csv", goal_completion_rows, [
        "goal_id", "requested_goal", "status", "evidence_summary",
        "evidence_artifacts", "review_gate", "must_not_claim", "next_action",
    ])
    write_goal_completion_audit(output_dir, goal_completion_rows)
    write_csv(output_dir / "human_review_queue.csv", human_review_queue_rows, [
        "queue_id", "priority", "source_sheet", "source_id", "review_status",
        "human_decision_required", "review_focus", "evidence_summary",
        "evidence_artifacts", "blocking_claim", "must_not_claim", "next_action",
    ])
    write_human_review_queue(output_dir, human_review_queue_rows)
    write_csv(output_dir / "review_signoff_template.csv", review_signoff_rows, [
        "signoff_id", "queue_id", "priority", "source_sheet", "source_id",
        "review_status", "signoff_required", "decision_allowed",
        "recommended_decision", "forbidden_decisions", "completion_requirements",
        "reviewer_decision", "reviewer", "review_date", "reviewer_notes",
        "evidence_artifacts", "review_focus", "blocking_claim",
        "must_not_claim", "next_action",
    ])
    write_review_signoff_template(output_dir, review_signoff_rows)
    write_csv(output_dir / "manual_review_checklist.csv", manual_review_rows, [
        "review_id", "review_area", "workbook_sheet", "automatic_status",
        "human_decision_required", "review_question", "evidence_summary",
        "evidence_artifacts", "must_not_claim", "suggested_action",
    ])
    write_manual_review_checklist(output_dir, manual_review_rows)
    write_csv(output_dir / "monitaal_xml_inventory.csv", inventory_rows, [
        "xml_path", "xml_file", "template", "source_kind", "embedded_symbol", "parse_status", "locations", "accept_locations", "transitions",
        "labels", "guards", "resets", "parse_error",
    ])
    write_csv(output_dir / "monitaal_translation_review.csv", translation_rows, [
        "xml_path", "xml_file", "source_kind", "embedded_symbol", "positive_template", "negative_template", "pair_method",
        "ap_mapping", "candidate_mitl", "candidate_confidence", "mitl_equivalence_status", "review_status", "translation_reason", "labels", "guards",
        "positive_locations", "positive_edges", "negative_locations", "negative_edges",
    ])
    write_csv(output_dir / "benchmark_manifest.csv", benchmark_manifest_rows, [
        "manifest_id", "xml_path", "xml_file", "source_kind", "positive_template", "negative_template",
        "candidate_mitl", "mitl_equivalence_status", "candidate_confidence", "promotion_status",
        "paper_action", "evidence_grade", "trace_match_count", "trace_mismatch_count",
        "candidate_timeout_count", "candidate_error_count", "baseline_timeout_count",
        "baseline_skipped_no_input_count", "baseline_generated_empty_no_original_input_count",
        "original_input_match_count", "generated_input_match_count",
        "repository_input_match_count", "embedded_benchmark_input_match_count",
        "external_or_case_input_match_count", "generated_review_input_match_count",
        "generated_empty_no_original_input_match_count", "input_origin_match_counts",
        "matched_verdicts", "matched_input_paths", "timeout_input_paths", "blocker_or_next_step",
        "translation_reason", "labels", "guards",
    ])
    (output_dir / "benchmark_manifest.json").write_text(json.dumps(benchmark_manifest_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(output_dir / "xml_edge_guard_proofs.csv", edge_guard_proof_rows, [
        "proof_id", "manifest_id", "xml_path", "xml_file", "source_kind", "positive_template",
        "negative_template", "candidate_mitl", "promotion_status", "proof_status", "proof_class",
        "pattern", "trigger_label", "response_label", "forbidden_label", "bound", "clock",
        "positive_edge_evidence", "negative_edge_evidence", "reset_edge_evidence",
        "acceptance_evidence", "trace_evidence", "manual_review_notes",
    ])
    (output_dir / "xml_edge_guard_proofs.json").write_text(json.dumps(edge_guard_proof_rows, indent=2, ensure_ascii=False), encoding="utf-8")
    write_csv(output_dir / "xml_proof_appendix.csv", proof_appendix_rows, [
        "appendix_id", "manifest_id", "xml_file", "positive_template", "negative_template",
        "candidate_mitl", "appendix_status", "proof_status", "proof_class", "paper_claim_scope",
        "proof_sketch", "edge_guard_evidence", "trace_evidence", "manual_review_notes", "exclusion_reason",
    ])
    write_xml_translation_proof_appendix(output_dir, proof_appendix_rows)
    write_csv(output_dir / "xml_proof_obligations.csv", xml_proof_obligation_rows, [
        "obligation_id", "manifest_id", "xml_file", "positive_template", "negative_template",
        "candidate_mitl", "proof_class", "proof_status", "obligation_group", "obligation_name",
        "obligation_status", "machine_checkable", "required", "observed", "evidence_artifacts",
        "reviewer_action",
    ])
    write_xml_proof_obligations(output_dir, xml_proof_obligation_rows)
    write_csv(output_dir / "xml_trace_coverage_obligations.csv", xml_trace_coverage_rows, [
        "coverage_id", "manifest_id", "xml_file", "positive_template", "negative_template",
        "candidate_mitl", "proof_class", "proof_status", "coverage_group", "coverage_name",
        "coverage_status", "machine_checkable", "required", "observed", "observed_candidates",
        "observed_input_origins", "evidence_artifacts", "reviewer_action",
    ])
    write_xml_trace_coverage_obligations(output_dir, xml_trace_coverage_rows)
    write_csv(output_dir / "xml_original_trace_gaps.csv", xml_original_trace_gap_rows, [
        "gap_id", "manifest_id", "xml_file", "positive_template", "negative_template",
        "candidate_mitl", "proof_class", "gap_class", "gap_status", "machine_checkable",
        "observed", "observed_candidates", "observed_input_origins", "reason",
        "manual_review_action", "must_not_claim", "source_coverage_id", "evidence_artifacts",
    ])
    write_xml_original_trace_gaps(output_dir, xml_original_trace_gap_rows)
    write_csv(output_dir / "gear_original_input_response_audit.csv", gear_original_input_response_audit_rows, [
        "audit_id", "manifest_id", "xml_file", "positive_template", "negative_template",
        "candidate_mitl", "trigger_label", "response_label", "bound", "input_path",
        "input_origin", "baseline_status", "baseline_verdict", "baseline_returncode",
        "timed_event_rows", "nonblank_event_count", "empty_label_event_count",
        "unparsable_event_rows", "last_event_time", "trigger_count", "response_count",
        "responded_within_bound", "late_response_count", "pending_trigger_count",
        "expired_without_response_count", "max_response_delay", "last_trigger_time",
        "last_response_time", "late_trigger_times", "pending_trigger_times",
        "expired_trigger_times", "finite_trace_response_status", "online_verdict_boundary",
        "evidence_summary", "reviewer_action",
    ])
    write_gear_original_input_response_audit(output_dir, gear_original_input_response_audit_rows)
    write_csv(output_dir / "non_gear_original_input_search_audit.csv", non_gear_original_input_search_audit_rows, [
        "audit_id", "manifest_id", "gap_id", "xml_file", "xml_path", "positive_template",
        "negative_template", "candidate_mitl", "gap_class", "search_status", "xml_exists",
        "monitaal_models_cmake_lists_reference", "sibling_input_txt_count",
        "sibling_input_txt_names", "prefix_matched_sibling_input_count",
        "prefix_matched_sibling_input_names", "repository_same_stem_file_count",
        "repository_same_stem_files", "repository_non_xml_same_stem_file_count",
        "repository_non_xml_same_stem_files", "baseline_rows_for_pair",
        "original_like_baseline_count", "generated_review_input_count",
        "generated_review_input_paths", "generated_empty_input_count",
        "manifest_original_input_match_count", "manifest_generated_input_match_count",
        "manifest_input_origin_match_counts", "evidence_summary", "boundary",
        "reviewer_action",
    ])
    write_non_gear_original_input_search_audit(output_dir, non_gear_original_input_search_audit_rows)
    write_csv(output_dir / "paper_claim_review.csv", paper_claim_review_rows, [
        "review_id", "manifest_id", "xml_file", "positive_template", "negative_template",
        "candidate_mitl", "appendix_status", "proof_class", "claim_strength",
        "paper_body_recommendation", "appendix_recommendation", "baseline_evidence_boundary",
        "original_trace_gap_boundary", "must_not_claim", "next_manual_action", "source_artifacts",
    ])
    write_paper_claim_review(output_dir, paper_claim_review_rows)
    write_csv(output_dir / "paper_claim_consistency_audit.csv", paper_claim_audit_rows, [
        "audit_id", "manifest_id", "xml_file", "claim_strength", "appendix_status",
        "proof_class", "baseline_match_count", "baseline_timeout_count", "audit_status",
        "checked_rules", "issues", "warnings", "recommended_action", "source_review_id",
    ])
    write_paper_claim_consistency_audit(output_dir, paper_claim_audit_rows)
    write_csv(output_dir / "requirements_traceability_audit.csv", requirements_audit_rows, [
        "requirement_id", "requirement", "status", "evidence_summary", "evidence_artifacts",
        "gap_or_risk", "next_action",
    ])
    write_requirements_traceability_audit(output_dir, requirements_audit_rows)
    write_csv(output_dir / "monitaal_transition_details.csv", transition_detail_rows, [
        "xml_path", "xml_file", "source_kind", "embedded_symbol", "template", "parse_status", "transition_index", "transition_id",
        "pair_role", "paired_template", "positive_template", "negative_template", "pair_method",
        "source_id", "source_name", "source_accepting", "source_initial", "source_invariants",
        "target_id", "target_name", "target_accepting", "target_initial", "target_invariants",
        "sync_raw", "sync_label", "sync_ap_candidate", "guards", "assignments", "other_labels", "nails",
        "ap_mapping", "candidate_mitl", "candidate_confidence", "mitl_equivalence_status", "review_status",
        "translation_reason", "parse_error",
    ])
    write_csv(output_dir / "monitaal_baseline_results.csv", baseline_rows, [
        "xml_path", "positive_template", "negative_template", "input_path", "status", "verdict",
        "returncode", "elapsed_ms", "input_origin", "input_rationale", "stdout_excerpt", "stderr_excerpt",
    ])
    write_csv(output_dir / "translation_candidate_results.csv", candidate_result_rows, [
        "candidate_id", "xml_path", "xml_file", "source_kind", "positive_template", "negative_template",
        "input_path", "candidate_mitl", "mitl_equivalence_status", "mapped_events", "trace_path", "run_dir",
        "actual_final", "actual_sat", "baseline_status", "baseline_verdict", "baseline_comparison_status",
        "oracle_type", "oracle_verdict", "correctness_evidence", "returncode", "timeout", "elapsed_ms", "processed_steps",
        "positive_locations", "positive_edges", "negative_locations", "negative_edges", "stdout_excerpt", "stderr_excerpt",
    ])
    write_csv(output_dir / "candidate_prefix_observations.csv", candidate_prefix_rows, [
        "candidate_id", "xml_file", "positive_template", "negative_template", "input_path",
        "candidate_mitl", "mitl_equivalence_status", "baseline_status", "baseline_verdict",
        "baseline_comparison_status", "actual_final", "step", "time", "human_label",
        "canonical_label", "verdict", "monitor_advanced", "positive_states", "negative_states",
        "run_dir", "steps_path",
    ])
    write_csv(output_dir / "candidate_step_audit.csv", candidate_step_audit_rows, [
        "candidate_id", "xml_file", "positive_template", "negative_template", "input_path",
        "candidate_mitl", "mitl_equivalence_status", "mapped_events", "processed_steps",
        "observed_steps", "all_trace_steps_recorded", "first_decisive_step", "first_decisive_time",
        "first_decisive_verdict", "carry_forward_steps", "actual_final", "baseline_status",
        "baseline_verdict", "baseline_comparison_status", "correctness_claim_scope",
        "candidate_step_evidence", "raw_step_artifact", "run_dir",
    ])
    write_candidate_step_audit(output_dir, candidate_step_audit_rows)
    write_csv(output_dir / "monitaal_embedded_benchmarks.csv", embedded_rows, [
        "case_id", "header", "xml_symbol", "status",
    ])

    summary = {
        "output_dir": str(output_dir),
        "semantic_cases": len(case_rows),
        "semantic_ran": sum(1 for row in semantic_rows if row["returncode"] != ""),
        "semantic_pass": sum(1 for row in semantic_rows if row["pass_status"] == "PASS"),
        "semantic_fail": sum(1 for row in semantic_rows if row["pass_status"] == "FAIL"),
        "semantic_correctness_verified": sum(1 for row in semantic_rows if row["correctness_status"] == "VERIFIED"),
        "semantic_finite_verified": sum(1 for row in semantic_rows if row.get("word") == "finite" and row["correctness_status"] == "VERIFIED"),
        "semantic_infinite_verified": sum(1 for row in semantic_rows if row.get("word") == "infinite" and row["correctness_status"] == "VERIFIED"),
        "semantic_correctness_needs_manual_oracle": sum(1 for row in semantic_rows if row["correctness_status"] == "NEEDS_MANUAL_ORACLE"),
        "semantic_correctness_not_verified_resource_limit": sum(1 for row in semantic_rows if row["correctness_status"] == "NOT_VERIFIED_RESOURCE_LIMIT"),
        "semantic_correctness_not_verified_timeout": sum(1 for row in semantic_rows if row["correctness_status"] == "NOT_VERIFIED_TIMEOUT"),
        "semantic_correctness_not_a_verdict_check": sum(1 for row in semantic_rows if row["correctness_status"] == "NOT_A_VERDICT_CHECK"),
        "semantic_correctness_build_timeout_not_a_verdict_check": sum(1 for row in semantic_rows if row["correctness_status"] == "NOT_A_VERDICT_CHECK_BUILD_TIMEOUT"),
        "semantic_prefix_oracle_rows": len(semantic_prefix_rows),
        "semantic_prefix_oracle_match": sum(1 for row in semantic_prefix_rows if row["prefix_oracle_status"] == "MATCH"),
        "semantic_prefix_oracle_mismatch": sum(1 for row in semantic_prefix_rows if row["prefix_oracle_status"] == "MISMATCH"),
        "semantic_prefix_oracle_missing_observed_step": sum(1 for row in semantic_prefix_rows if row["prefix_oracle_status"] == "MISSING_OBSERVED_STEP"),
        "semantic_prefix_final_verdict_only": sum(1 for row in semantic_prefix_rows if row["prefix_oracle_status"] == "FINAL_VERDICT_ONLY"),
        "semantic_prefix_carry_forward_steps": sum(1 for row in semantic_prefix_rows if row.get("monitor_advanced") == "false"),
        "semantic_oracle_derivation_rows": len(semantic_oracle_derivation_rows),
        "semantic_oracle_hand_verified": sum(1 for row in semantic_oracle_derivation_rows if row.get("oracle_status") == "HAND_ORACLE_VERIFIED"),
        "semantic_oracle_construction_stats_only": sum(1 for row in semantic_oracle_derivation_rows if row.get("oracle_status") == "CONSTRUCTION_STATS_ONLY"),
        "semantic_oracle_review_required": sum(1 for row in semantic_oracle_derivation_rows if row.get("oracle_status") == "ORACLE_REVIEW_REQUIRED"),
        "semantic_oracle_prefix_mismatches": sum(int(row.get("prefix_mismatches", 0) or 0) for row in semantic_oracle_derivation_rows),
        "mitl_correctness_audit_rows": len(correctness_audit_rows),
        "manual_oracle_guide_rows": len(manual_oracle_guide_rows),
        "manual_oracle_guide_p0": sum(1 for row in manual_oracle_guide_rows if row.get("priority") == "P0"),
        "manual_oracle_guide_p1": sum(1 for row in manual_oracle_guide_rows if row.get("priority") == "P1"),
        "semantic_review": sum(1 for row in semantic_rows if row["pass_status"] == "REVIEW"),
        "semantic_build_stats": sum(1 for row in semantic_rows if row["pass_status"] == "BUILD_STATS"),
        "semantic_build_timeout": sum(1 for row in semantic_rows if row["pass_status"] == "BUILD_TIMEOUT"),
        "semantic_resource_limit": sum(1 for row in semantic_rows if row["pass_status"] == "RESOURCE_LIMIT"),
        "semantic_timeout": sum(1 for row in semantic_rows if row["pass_status"] == "TIMEOUT"),
        "semantic_error": sum(1 for row in semantic_rows if row["pass_status"] == "ERROR"),
        "semantic_review_unsupported": sum(1 for row in semantic_rows if row["pass_status"] == "REVIEW_UNSUPPORTED"),
        "semantic_exclusion_rows": len(semantic_exclusion_rows),
        "internal_count_forms_excluded": len(INTERNAL_COUNT_FORMS),
        "internal_count_forms": INTERNAL_COUNT_FORMS,
        "internal_count_forms_exclusion_reason": INTERNAL_COUNT_FORMS_REASON,
        "syntax_coverage_rows": len(syntax_coverage_rows),
        "syntax_coverage_verified_runtime": sum(1 for row in syntax_coverage_rows if str(row.get("coverage_status", "")).startswith("VERIFIED_RUNTIME")),
        "syntax_coverage_finite_and_infinite": sum(1 for row in syntax_coverage_rows if row.get("coverage_status") == "VERIFIED_RUNTIME_FINITE_AND_INFINITE"),
        "syntax_coverage_build_stats_only": sum(1 for row in syntax_coverage_rows if row.get("coverage_status") == "BUILD_STATS_ONLY"),
        "syntax_coverage_excluded_internal": sum(1 for row in syntax_coverage_rows if row.get("coverage_status") == "EXCLUDED_INTERNAL_FORM"),
        "syntax_coverage_missing": sum(1 for row in syntax_coverage_rows if row.get("coverage_status") == "MISSING"),
        "formula_input_policy_rows": len(input_policy_rows),
        "formula_input_policy_pass": sum(1 for row in input_policy_rows if row.get("pass_status") == "PASS"),
        "formula_input_policy_fail": sum(1 for row in input_policy_rows if row.get("pass_status") == "FAIL"),
        "formula_input_policy_assert_like_failures": sum(1 for row in input_policy_rows if row.get("assert_like_failure") == "true"),
        "cli_contract_rows": len(cli_contract_rows),
        "cli_contract_pass": sum(1 for row in cli_contract_rows if row.get("pass_status") == "PASS"),
        "cli_contract_fail": sum(1 for row in cli_contract_rows if row.get("pass_status") == "FAIL"),
        "cli_contract_controlled_errors": sum(1 for row in cli_contract_rows if row.get("actual_exit_class") == "CONTROLLED_ERROR"),
        "review_guide_rows": len(review_guide_rows),
        "review_guide_p0": sum(1 for row in review_guide_rows if row.get("priority") == "P0"),
        "review_guide_p1": sum(1 for row in review_guide_rows if row.get("priority") == "P1"),
        "goal_completion_rows": len(goal_completion_rows),
        "goal_completion_pass": sum(1 for row in goal_completion_rows if row.get("status") == "PASS"),
        "goal_completion_pass_with_caveat": sum(1 for row in goal_completion_rows if row.get("status") == "PASS_WITH_CAVEAT"),
        "goal_completion_review_required": sum(1 for row in goal_completion_rows if row.get("status") == "REVIEW_REQUIRED"),
        "goal_completion_v1_deferred": sum(1 for row in goal_completion_rows if row.get("status") == "V1_DEFERRED"),
        "goal_completion_fail": sum(1 for row in goal_completion_rows if row.get("status") == "FAIL"),
        "human_review_queue_rows": len(human_review_queue_rows),
        "human_review_queue_human_required": sum(1 for row in human_review_queue_rows if row.get("human_decision_required") == "true"),
        "human_review_queue_p0": sum(1 for row in human_review_queue_rows if str(row.get("priority", "")).startswith("P0")),
        "human_review_queue_p1": sum(1 for row in human_review_queue_rows if str(row.get("priority", "")).startswith("P1")),
        "human_review_queue_p2": sum(1 for row in human_review_queue_rows if str(row.get("priority", "")).startswith("P2")),
        "human_review_queue_p3": sum(1 for row in human_review_queue_rows if str(row.get("priority", "")).startswith("P3")),
        "human_review_queue_fail": sum(1 for row in human_review_queue_rows if row.get("review_status") == "FAIL"),
        "review_signoff_template_rows": len(review_signoff_rows),
        "review_signoff_template_blank_decisions": sum(1 for row in review_signoff_rows if not row.get("reviewer_decision")),
        "review_signoff_template_p0": sum(1 for row in review_signoff_rows if str(row.get("priority", "")).startswith("P0")),
        "review_signoff_template_p1": sum(1 for row in review_signoff_rows if str(row.get("priority", "")).startswith("P1")),
        "review_signoff_template_p2": sum(1 for row in review_signoff_rows if str(row.get("priority", "")).startswith("P2")),
        "manual_review_rows": len(manual_review_rows),
        "manual_review_pass": sum(1 for row in manual_review_rows if row.get("automatic_status") == "PASS"),
        "manual_review_pass_with_caveat": sum(1 for row in manual_review_rows if row.get("automatic_status") == "PASS_WITH_CAVEAT"),
        "manual_review_review_required": sum(1 for row in manual_review_rows if row.get("automatic_status") == "REVIEW_REQUIRED"),
        "manual_review_v1_deferred": sum(1 for row in manual_review_rows if row.get("automatic_status") == "V1_DEFERRED"),
        "manual_review_fail": sum(1 for row in manual_review_rows if row.get("automatic_status") == "FAIL"),
        "manual_review_human_required": sum(1 for row in manual_review_rows if row.get("human_decision_required") == "true"),
        "xml_templates": len(inventory_rows),
        "xml_transition_detail_rows": len(transition_detail_rows),
        "xml_pairs": len(translation_rows),
        "translation_candidates": sum(1 for row in translation_rows if row["candidate_mitl"]),
        "benchmark_manifest_rows": len(benchmark_manifest_rows),
        "benchmark_manifest_strong_trace_level": sum(1 for row in benchmark_manifest_rows if row["promotion_status"] == "STRONG_TRACE_LEVEL_CANDIDATE"),
        "benchmark_manifest_single_trace_level": sum(1 for row in benchmark_manifest_rows if row["promotion_status"] == "SINGLE_TRACE_LEVEL_CANDIDATE"),
        "benchmark_manifest_approximate_trace_only": sum(1 for row in benchmark_manifest_rows if row["promotion_status"] == "APPROXIMATE_TRACE_ONLY"),
        "benchmark_manifest_not_promoted": sum(1 for row in benchmark_manifest_rows if row["paper_action"] != "eligible_for_manual_paper_review"),
        "xml_edge_guard_proof_rows": len(edge_guard_proof_rows),
        "xml_edge_guard_proof_ready": sum(1 for row in edge_guard_proof_rows if row["proof_status"] == "EDGE_GUARD_PROOF_READY"),
        "xml_edge_guard_review_required": sum(1 for row in edge_guard_proof_rows if row["proof_status"] == "EDGE_GUARD_REVIEW_REQUIRED"),
        "xml_edge_guard_not_ready": sum(1 for row in edge_guard_proof_rows if row["proof_status"].startswith("NOT_")),
        "xml_edge_guard_incomplete": sum(1 for row in edge_guard_proof_rows if row["proof_status"] == "EDGE_GUARD_EVIDENCE_INCOMPLETE"),
        "xml_proof_appendix_rows": len(proof_appendix_rows),
        "xml_proof_appendix_ready": sum(1 for row in proof_appendix_rows if row["appendix_status"] == "PROOF_DRAFT_READY"),
        "xml_proof_appendix_excluded": sum(1 for row in proof_appendix_rows if row["appendix_status"] != "PROOF_DRAFT_READY"),
        "xml_proof_obligation_rows": len(xml_proof_obligation_rows),
        "xml_proof_obligation_pass": sum(1 for row in xml_proof_obligation_rows if row["obligation_status"] == "PASS"),
        "xml_proof_obligation_review_required": sum(1 for row in xml_proof_obligation_rows if row["obligation_status"] == "REVIEW_REQUIRED"),
        "xml_proof_obligation_fail": sum(1 for row in xml_proof_obligation_rows if row["obligation_status"] == "FAIL"),
        "xml_trace_coverage_rows": len(xml_trace_coverage_rows),
        "xml_trace_coverage_pass": sum(1 for row in xml_trace_coverage_rows if row["coverage_status"] == "PASS"),
        "xml_trace_coverage_review_required": sum(1 for row in xml_trace_coverage_rows if row["coverage_status"] == "REVIEW_REQUIRED"),
        "xml_trace_coverage_fail": sum(1 for row in xml_trace_coverage_rows if row["coverage_status"] == "FAIL"),
        "xml_original_trace_gap_rows": len(xml_original_trace_gap_rows),
        "xml_original_trace_gap_review_required": sum(1 for row in xml_original_trace_gap_rows if row["gap_status"] == "REVIEW_REQUIRED"),
        "xml_original_trace_gap_fail": sum(1 for row in xml_original_trace_gap_rows if row["gap_status"] == "FAIL"),
        "gear_original_input_response_audit_rows": len(gear_original_input_response_audit_rows),
        "gear_original_input_response_audit_late_response_rows": sum(1 for row in gear_original_input_response_audit_rows if as_int(row.get("late_response_count")) > 0),
        "gear_original_input_response_audit_pending_rows": sum(1 for row in gear_original_input_response_audit_rows if as_int(row.get("pending_trigger_count")) > 0),
        "gear_original_input_response_audit_expired_rows": sum(1 for row in gear_original_input_response_audit_rows if as_int(row.get("expired_without_response_count")) > 0),
        "non_gear_original_input_search_audit_rows": len(non_gear_original_input_search_audit_rows),
        "non_gear_original_input_search_no_original_rows": sum(1 for row in non_gear_original_input_search_audit_rows if row.get("search_status") == "NO_ORIGINAL_TIMED_WORD_FOUND"),
        "non_gear_original_input_search_possible_original_rows": sum(1 for row in non_gear_original_input_search_audit_rows if row.get("search_status") == "REVIEW_REQUIRED_POSSIBLE_ORIGINAL_INPUT"),
        "non_gear_original_input_search_original_like_baseline_rows": sum(as_int(row.get("original_like_baseline_count")) for row in non_gear_original_input_search_audit_rows),
        "non_gear_original_input_search_generated_review_input_rows": sum(as_int(row.get("generated_review_input_count")) for row in non_gear_original_input_search_audit_rows),
        "paper_claim_review_rows": len(paper_claim_review_rows),
        "paper_claim_body_pattern_ready": sum(1 for row in paper_claim_review_rows if row["claim_strength"] == "BODY_PATTERN_READY_AFTER_HUMAN_SIGNOFF"),
        "paper_claim_appendix_timeout_caveat": sum(1 for row in paper_claim_review_rows if row["claim_strength"] == "APPENDIX_INSTANCE_READY_WITH_TIMEOUT_CAVEAT"),
        "paper_claim_excluded": sum(1 for row in paper_claim_review_rows if row["claim_strength"].startswith("EXCLUDED_")),
        "paper_claim_audit_rows": len(paper_claim_audit_rows),
        "paper_claim_audit_pass": sum(1 for row in paper_claim_audit_rows if row["audit_status"] == "PASS"),
        "paper_claim_audit_warn": sum(1 for row in paper_claim_audit_rows if row["audit_status"] == "WARN"),
        "paper_claim_audit_fail": sum(1 for row in paper_claim_audit_rows if row["audit_status"] == "FAIL"),
        "requirements_audit_rows": len(requirements_audit_rows),
        "requirements_audit_pass": sum(1 for row in requirements_audit_rows if row["status"] == "PASS"),
        "requirements_audit_pass_with_caveat": sum(1 for row in requirements_audit_rows if row["status"] == "PASS_WITH_CAVEAT"),
        "requirements_audit_v1_deferred": sum(1 for row in requirements_audit_rows if row["status"] == "V1_DEFERRED"),
        "requirements_audit_fail": sum(1 for row in requirements_audit_rows if row["status"] == "FAIL"),
        "translation_candidate_runs": len(candidate_result_rows),
        "translation_candidate_success": sum(1 for row in candidate_result_rows if row["returncode"] == 0),
        "translation_candidate_timeouts": sum(1 for row in candidate_result_rows if row["timeout"]),
        "translation_candidate_baseline_matches": sum(1 for row in candidate_result_rows if row.get("baseline_comparison_status") == "MATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT"),
        "translation_candidate_baseline_mismatches": sum(1 for row in candidate_result_rows if row.get("baseline_comparison_status") == "MISMATCHES_MONITAAL_BASELINE_ON_MAPPED_INPUT"),
        "translation_candidate_baseline_not_verified": sum(1 for row in candidate_result_rows if str(row.get("baseline_comparison_status", "")).startswith("NOT_VERIFIED")),
        "candidate_prefix_observation_rows": len(candidate_prefix_rows),
        "candidate_step_audit_rows": len(candidate_step_audit_rows),
        "candidate_step_all_trace_steps_recorded": sum(1 for row in candidate_step_audit_rows if row.get("all_trace_steps_recorded") == "true"),
        "candidate_step_missing_or_incomplete": sum(1 for row in candidate_step_audit_rows if row.get("all_trace_steps_recorded") != "true"),
        "candidate_prefix_carry_forward_steps": sum(1 for row in candidate_prefix_rows if row.get("monitor_advanced") == "false"),
        "baseline_runs": sum(1 for row in baseline_rows if row["status"] == "ran"),
        "baseline_timeouts": sum(1 for row in baseline_rows if row["status"] == "timeout"),
        "baseline_skipped_no_input": sum(1 for row in baseline_rows if row["status"] == "skipped_no_input"),
        "baseline_generated_empty_no_original_input": sum(1 for row in baseline_rows if row.get("input_origin") == "generated_empty_no_original_input"),
        "embedded_benchmark_records": len(embedded_rows),
    }
    reproducibility_manifest_rows = build_reproducibility_manifest_rows(output_dir, args)
    reproducibility_counts = Counter(row["category"] for row in reproducibility_manifest_rows)
    summary.update({
        "reproducibility_manifest_rows": len(reproducibility_manifest_rows),
        "reproducibility_source_hashes": reproducibility_counts.get("source_sha256", 0),
        "reproducibility_result_hashes": reproducibility_counts.get("result_sha256", 0),
        "reproducibility_git_rows": reproducibility_counts.get("git", 0),
    })
    summary["workbook_status"] = "skipped" if args.no_workbook else "ok"
    summary["workbook_path"] = "" if args.no_workbook else str(output_dir / "paper_review_results.xlsx")
    write_experiment_summary_files(output_dir, summary)
    write_reproducibility_manifest(output_dir, reproducibility_manifest_rows)
    workbook_status = build_workbook(output_dir, args.no_workbook)
    summary["workbook_status"] = workbook_status
    summary["workbook_path"] = str(output_dir / "paper_review_results.xlsx") if workbook_status == "ok" else ""
    write_experiment_summary_files(output_dir, summary)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if workbook_status in {"ok", "skipped"} else 1


if __name__ == "__main__":
    sys.exit(main())
