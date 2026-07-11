#!/usr/bin/env python3
"""文件功能：验证 FORMATS 2020 Romeo 输出解析和固定 benchmark/oracle 清单。"""

from __future__ import annotations

import unittest

import run_romeo_benchmarks as harness


SAMPLE_OUTPUT = """
\x1b[1m\x1b[34m[info]\x1b[0m Checking mincost E (true U goal)
\x1b[1m\x1b[32m=-1140\x1b[0m
[info] Time: 1.2s (total) = 1.0s (user) + 0.2s (system)
[info] Max memory used: 8.5Mo
[info] Checking backward mincost (true U goal)
\x1b[1m\x1b[32m=-1140\x1b[0m
[info] Time: 0.7s (total) = 0.5s (user) + 0.2s (system)
[info] Max memory used: 17.0Mo
"""


class RomeoParserTests(unittest.TestCase):
    def test_parses_forward_and_backward_blocks(self) -> None:
        modes, errors = harness.parse_romeo_output(SAMPLE_OUTPUT)

        self.assertEqual([], errors)
        self.assertEqual("-1140", modes["forward"]["cost"])
        self.assertEqual("-1140", modes["backward"]["cost"])
        self.assertEqual(1.2, modes["forward"]["total_seconds"])
        self.assertEqual(0.5, modes["backward"]["user_seconds"])
        self.assertEqual(8.5, modes["forward"]["max_memory_mb"])

    def test_missing_backward_metrics_is_an_explicit_error(self) -> None:
        prefix = SAMPLE_OUTPUT.split("[info] Checking backward", maxsplit=1)[0]
        _, errors = harness.parse_romeo_output(prefix)

        self.assertTrue(any(error.startswith("backward 缺少 cost") for error in errors))

    def test_manifest_contains_all_nine_artifact_models(self) -> None:
        self.assertEqual(9, len(harness.FULL_MODELS))
        self.assertEqual(set(harness.QUICK_MODELS), set(harness.QUICK_ORACLES))
        self.assertTrue(set(harness.QUICK_MODELS).issubset(harness.FULL_MODELS))

    def test_fixed_artifact_identity_and_oracles(self) -> None:
        self.assertEqual(
            "6045841f964a5e37fcb6354eae6999355f8e308292406ff5a09412bccd2d9a29",
            harness.ARCHIVE_SHA256,
        )
        self.assertEqual("-1140", harness.QUICK_ORACLES["aircraft3"])
        self.assertEqual("-4140", harness.QUICK_ORACLES["aircraft4"])
        self.assertEqual("-1760", harness.QUICK_ORACLES["scheduling2"])
        self.assertEqual("-2560", harness.QUICK_ORACLES["scheduling3"])


if __name__ == "__main__":
    unittest.main()
