from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest


ADAPTER_ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ADAPTER_ROOT))

from tafuzz_pgfuzz.catalog import (  # noqa: E402
    command_rows,
    flatten_parameter_metadata,
    merge_parameters,
    migration_rows,
    write_compatibility_inputs,
)
from tafuzz_pgfuzz.common import load_json  # noqa: E402


class CatalogTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_json(ADAPTER_ROOT / "data/safety_policy.json")

    def test_flatten_parameter_metadata_prefers_richer_record(self) -> None:
        document = {
            "A": {"P": {"DisplayName": "short"}},
            "B": {"P": {"DisplayName": "rich", "Range": {"low": "0", "high": "2"}}},
        }
        flattened = flatten_parameter_metadata(document)
        self.assertEqual(flattened["P"]["DisplayName"], "rich")
        self.assertEqual(flattened["P"]["MetadataGroup"], "B")

    def test_runtime_parameter_set_is_authoritative(self) -> None:
        snapshot = {
            "status": "COMPLETE", "expected_count": 3,
            "parameters": [
                {"name": "P", "decoded_value": 1, "param_type_name": "MAV_PARAM_TYPE_INT16", "param_index": 0, "param_count": 3},
                {"name": "SIM_X", "decoded_value": 0.0, "param_type_name": "MAV_PARAM_TYPE_REAL32", "param_index": 1, "param_count": 3},
                {"name": "READ_ONLY", "decoded_value": 2, "param_type_name": "MAV_PARAM_TYPE_INT16", "param_index": 2, "param_count": 3},
            ],
        }
        metadata = {"": {
            "P": {"Range": {"low": "0", "high": "2"}},
            "SIM_X": {"Range": {"low": "0", "high": "10"}},
            "READ_ONLY": {"ReadOnly": "True", "Range": {"low": "0", "high": "3"}},
            "STATIC_ONLY": {"Range": {"low": "0", "high": "1"}},
        }}
        rows = merge_parameters(snapshot, metadata, self.policy)
        self.assertEqual({row["name"] for row in rows}, {"P", "SIM_X", "READ_ONLY"})
        self.assertEqual(next(row for row in rows if row["name"] == "P")["input_type"], "INPUT_P")
        self.assertEqual(next(row for row in rows if row["name"] == "SIM_X")["input_type"], "INPUT_E")
        self.assertEqual(next(row for row in rows if row["name"] == "READ_ONLY")["execution_class"], "DISRUPTIVE_EXCLUDED")

    def test_incomplete_snapshot_fails_closed(self) -> None:
        snapshot = {"status": "PARTIAL", "expected_count": 2, "parameters": []}
        with self.assertRaisesRegex(ValueError, "not COMPLETE"):
            merge_parameters(snapshot, {}, self.policy)

    def test_migration_exact_renamed_removed_and_ambiguous(self) -> None:
        current = [
            {"name": "A"}, {"name": "RTL_ALT_M"},
            {"name": "SIM_GPS1_POS_X"}, {"name": "SIM_GPS2_POS_X"},
        ]
        legacy = [
            {"legacy_kind": "ENVIRONMENT", "legacy_name": "A", "legacy_value": ""},
            {"legacy_kind": "ENVIRONMENT", "legacy_name": "RTL_ALT", "legacy_value": ""},
            {"legacy_kind": "ENVIRONMENT", "legacy_name": "SIM_GPS_POS_X", "legacy_value": ""},
            {"legacy_kind": "ENVIRONMENT", "legacy_name": "GONE", "legacy_value": ""},
        ]
        statuses = {row["legacy_name"]: row["migration_status"]
                    for row in migration_rows(legacy, current, self.policy)}
        self.assertEqual(statuses, {
            "A": "EXACT", "RTL_ALT": "RENAMED",
            "SIM_GPS_POS_X": "RENAMED", "GONE": "REMOVED",
        })

    def test_compatibility_lines_use_exact_identifier_deduplication(self) -> None:
        rows = [
            {"input_type": "INPUT_C", "name": "RC1", "numeric_id": 0},
            {"input_type": "INPUT_C", "name": "RC10", "numeric_id": 0},
            {"input_type": "INPUT_E", "name": "SIM_X", "numeric_id": None},
            {"input_type": "INPUT_P", "name": "P", "numeric_id": None},
        ]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            write_compatibility_inputs(root, rows, [])
            self.assertEqual((root / "cmds.txt").read_text(encoding="utf-8"),
                             "RC1,0\nRC10,0\n")
            self.assertEqual((root / "envs.txt").read_text(encoding="utf-8"), "SIM_X\n")
            self.assertEqual((root / "params.txt").read_text(encoding="utf-8"), "P\n")

    def test_rc_input_has_protocol_field_and_pgfuzz_compatibility_name(self) -> None:
        parameters = [{"name": "RCMAP_ROLL", "current_value": 1}]
        rows = command_rows({}, parameters, self.policy)
        rc1 = next(row for row in rows if row["name"] == "RC1")
        self.assertEqual(rc1["protocol_field"],
                         "RC_CHANNELS_OVERRIDE.chan1_raw")


if __name__ == "__main__":
    unittest.main()
