"""Invariants of the pump-and-dump simulation."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mmove import MarketParams, PumpDump, simulate  # noqa: E402


def test_roundtrip_returns_spot_and_isolates_the_edge():
    """A clean round-trip to flat: cash leg is a pure cost, options leg is the win."""
    res = simulate(MarketParams(), PumpDump(end_short_units=0.0), with_noise=False)
    # deterministic round-trip brings the settlement print back to the open
    assert np.isclose(res.settle_spot, res.spot[0], atol=1e-9)
    # ends flat in the cash book
    assert np.isclose(res.inventory[-1], 0.0, atol=1e-9)
    # the cash leg loses (round-trip impact), the options leg more than pays for it
    assert res.cash_pnl < 0
    assert res.options_pnl > 0
    assert res.total_pnl > 0


def test_manufactured_move_scales_with_pump():
    """Pumping harder (more permanent impact) manufactures a bigger move."""
    small = simulate(MarketParams(), PumpDump(accumulate_units=500.0), with_noise=False)
    big = simulate(MarketParams(), PumpDump(accumulate_units=2000.0), with_noise=False)
    assert big.manufactured_move > small.manufactured_move


def test_edge_scales_with_options_size():
    small = simulate(MarketParams(), PumpDump(options_units=1000.0), with_noise=False)
    big = simulate(MarketParams(), PumpDump(options_units=8000.0), with_noise=False)
    assert big.options_pnl > small.options_pnl
    # cash cost is unchanged by the options size
    assert np.isclose(small.cash_pnl, big.cash_pnl)
