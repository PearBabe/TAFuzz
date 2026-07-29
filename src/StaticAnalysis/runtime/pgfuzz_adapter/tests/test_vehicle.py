from __future__ import annotations

from pathlib import Path
import tempfile
import types
import unittest
import sys


ADAPTER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ADAPTER_ROOT))

from tafuzz_pgfuzz.states import FEATURE_GROUP, FEATURE_TOLERANCE  # noqa: E402
from tafuzz_pgfuzz.vehicle import SITLSession  # noqa: E402


class VehicleContractTests(unittest.TestCase):
    def test_default_gcs_system_id_matches_current_arducopter_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            session = SITLSession(Path(temporary))
            self.assertEqual(session.source_system, 255)

    def test_first_eight_rc_channels_release_with_zero(self) -> None:
        sent: list[tuple[int, ...]] = []
        mav = types.SimpleNamespace(
            rc_channels_override_send=lambda _sysid, _component, *values:
            sent.append(tuple(values)))
        with tempfile.TemporaryDirectory() as temporary:
            session = SITLSession(Path(temporary))
            session.connection = types.SimpleNamespace(mav=mav)
            session.release_rc_overrides()
        self.assertEqual(sent, [(0,) * 8])

    def test_gcs_failsafe_latency_is_a_status_feature(self) -> None:
        feature = "event.gcs_failsafe_observed_latency"
        self.assertEqual(FEATURE_GROUP[feature], "status")
        self.assertEqual(FEATURE_TOLERANCE[feature], 0.5)


if __name__ == "__main__":
    unittest.main()
