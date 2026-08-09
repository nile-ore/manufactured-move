"""Black-Scholes pricing and Greeks (vectorised, with tau -> 0 settlement handling).

The options market in this simulation is a *price-taker* on the spot: option marks
are pinned to the underlying via Black-Scholes, and the manipulator can hold arbitrary
size without moving option prices. Only trades in the cash/futures market move the spot
(see ``mmove.impact``). That asymmetry is the whole game.
"""

from __future__ import annotations

import numpy as np
from scipy.stats import norm

ArrayLike = np.ndarray | float


def _d1_d2(S: ArrayLike, K: float, tau: ArrayLike, r: float, sigma: float):
    S = np.asarray(S, dtype=float)
    tau = np.asarray(tau, dtype=float)
    sqrt_tau = np.sqrt(np.maximum(tau, 1e-12))
    with np.errstate(divide="ignore", invalid="ignore"):
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * tau) / (sigma * sqrt_tau)
        d2 = d1 - sigma * sqrt_tau
    return d1, d2


def bs_price(S: ArrayLike, K: float, tau: ArrayLike, r: float, sigma: float, kind: str) -> np.ndarray:
    """European option price. At ``tau <= 0`` returns intrinsic value (settlement)."""
    S = np.asarray(S, dtype=float)
    tau = np.asarray(tau, dtype=float)
    intrinsic = np.maximum(S - K, 0.0) if kind == "call" else np.maximum(K - S, 0.0)
    d1, d2 = _d1_d2(S, K, tau, r, sigma)
    disc = np.exp(-r * tau)
    if kind == "call":
        price = S * norm.cdf(d1) - K * disc * norm.cdf(d2)
    elif kind == "put":
        price = K * disc * norm.cdf(-d2) - S * norm.cdf(-d1)
    else:
        raise ValueError(f"kind must be 'call' or 'put', got {kind!r}")
    return np.where(tau <= 0.0, intrinsic, price)


def bs_delta(S: ArrayLike, K: float, tau: ArrayLike, r: float, sigma: float, kind: str) -> np.ndarray:
    S = np.asarray(S, dtype=float)
    tau = np.asarray(tau, dtype=float)
    d1, _ = _d1_d2(S, K, tau, r, sigma)
    delta = norm.cdf(d1) if kind == "call" else norm.cdf(d1) - 1.0
    # settlement: delta is a step function of moneyness
    settle = (S > K).astype(float) if kind == "call" else -(S < K).astype(float)
    return np.where(tau <= 0.0, settle, delta)


def bs_gamma(S: ArrayLike, K: float, tau: ArrayLike, r: float, sigma: float) -> np.ndarray:
    S = np.asarray(S, dtype=float)
    tau = np.asarray(tau, dtype=float)
    d1, _ = _d1_d2(S, K, tau, r, sigma)
    g = norm.pdf(d1) / (S * sigma * np.sqrt(np.maximum(tau, 1e-12)))
    return np.where(tau <= 0.0, 0.0, g)


def bs_vega(S: ArrayLike, K: float, tau: ArrayLike, r: float, sigma: float) -> np.ndarray:
    S = np.asarray(S, dtype=float)
    tau = np.asarray(tau, dtype=float)
    d1, _ = _d1_d2(S, K, tau, r, sigma)
    v = S * norm.pdf(d1) * np.sqrt(np.maximum(tau, 0.0))
    return np.where(tau <= 0.0, 0.0, v)
