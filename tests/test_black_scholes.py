"""Sanity checks on the Black-Scholes layer."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mmove.black_scholes import bs_delta, bs_price  # noqa: E402


def test_put_call_parity():
    S, K, tau, r, sigma = 102.0, 100.0, 0.02, 0.065, 0.20
    call = bs_price(S, K, tau, r, sigma, "call")
    put = bs_price(S, K, tau, r, sigma, "put")
    # C - P = S - K e^{-r tau}
    assert np.isclose(call - put, S - K * np.exp(-r * tau), atol=1e-8)


def test_settlement_is_intrinsic():
    assert np.isclose(bs_price(105.0, 100.0, 0.0, 0.065, 0.20, "call"), 5.0)
    assert np.isclose(bs_price(95.0, 100.0, 0.0, 0.065, 0.20, "put"), 5.0)
    assert np.isclose(bs_price(95.0, 100.0, 0.0, 0.065, 0.20, "call"), 0.0)


def test_delta_bounds():
    S = np.linspace(80, 120, 40)
    cd = bs_delta(S, 100.0, 0.02, 0.065, 0.20, "call")
    pd = bs_delta(S, 100.0, 0.02, 0.065, 0.20, "put")
    assert np.all((cd >= 0) & (cd <= 1))
    assert np.all((pd >= -1) & (pd <= 0))
    assert np.allclose(cd - pd, 1.0)  # call delta - put delta = 1
