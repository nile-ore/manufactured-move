"""Invariants of the pump-and-dump simulation."""

import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mmove import MarketParams, PumpDump, simulate  # noqa: E402
from mmove.market import evolve_spot  # noqa: E402


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


def test_options_pnl_matches_closed_form():
    """Synthetic short P&L equals units·[(entry−settle) + entry·(1−e^{−rτ})] by put-call parity."""
    market = MarketParams()
    strat = PumpDump(options_units=5000.0, options_structure="synthetic_short")
    res = simulate(market, strat, with_noise=False)
    tau_entry = market.tau(res.entry_step)
    expected = strat.options_units * (
        (res.entry_spot - res.settle_spot)
        + res.entry_spot * (1.0 - math.exp(-market.r * tau_entry))
    )
    assert np.isclose(res.options_pnl, expected, rtol=1e-9)


def test_cash_pnl_decomposition_identity():
    """cash_pnl == −Σ(q·mid) − temp_impact_cost + terminal_inventory·settle (end net short)."""
    market = MarketParams()
    res = simulate(market, PumpDump(end_short_units=300.0), with_noise=False)
    n = market.n_steps
    rhs = (
        -float(np.sum(res.cash_trades * res.spot[:n]))
        - res.temp_impact_cost
        + res.inventory[n] * res.settle_spot
    )
    assert np.isclose(res.cash_pnl, rhs, rtol=1e-9)


def test_vectorised_evolve_matches_reference_loop():
    """The cumulative-sum spot path is identical to the step-by-step recursion."""
    market = MarketParams(n_steps=200)
    rng = np.random.default_rng(3)
    trades = rng.normal(0.0, 5.0, size=market.n_steps)
    spot, exec_price = evolve_spot(market, trades, with_noise=False)
    ref = np.empty(market.n_steps + 1)
    ref[0] = market.s0
    ref_exec = np.empty(market.n_steps)
    for t in range(market.n_steps):
        ref_exec[t] = ref[t] + market.eta * trades[t]
        ref[t + 1] = ref[t] + market.gamma * trades[t]
    assert np.allclose(spot, ref)
    assert np.allclose(exec_price, ref_exec)
