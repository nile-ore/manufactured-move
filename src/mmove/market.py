"""Market state and spot dynamics under an Almgren-Chriss impact model.

Spot (the index / basket mid) evolves as::

    S[t+1] = S[t] + gamma * q[t] + sigma_step * Z[t]     # permanent impact + diffusion

and a cash-market trade of signed size ``q[t]`` (>0 = buy) executes at::

    exec[t] = S[t] + eta * q[t]                          # temporary impact (you cross the spread)

``gamma`` (permanent) is what lets the manipulator *manufacture* a move: buy the basket
up in the morning, then sell it back down. ``eta`` (temporary) is the round-trip cost
of doing so. The bet pays when the options book monetises the manufactured move for more
than the round-trip costs — because it is far larger than the cash size moving the market.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

TRADING_DAYS = 252


@dataclass
class MarketParams:
    """Parameters for one expiry-day session, discretised into ``n_steps`` intervals."""

    s0: float = 100.0            # spot at the open (normalised index; scale to BANKNIFTY in README)
    n_steps: int = 375          # NSE session is 375 minutes (09:15-15:30)
    sigma_annual: float = 0.20  # annualised vol, used for BOTH the path and BS marks
    r: float = 0.065            # risk-free (India ~ repo rate)
    gamma: float = 0.002        # permanent impact: points of spot per unit of net trade
    eta: float = 0.004          # temporary impact: points of slippage per unit traded per step
    tau0_days: float = 1.0      # time to expiry at the open, in trading days (expiry = today's close)

    @property
    def dt_year(self) -> float:
        """Length of one step in years."""
        return (self.tau0_days / TRADING_DAYS) / self.n_steps

    @property
    def sigma_step(self) -> float:
        """Per-step price stdev of the diffusion term (arithmetic, small-move regime)."""
        return self.s0 * self.sigma_annual * np.sqrt(self.dt_year)

    def tau(self, step: int) -> float:
        """Time to expiry (years) remaining at ``step``; hits 0 at settlement (step == n_steps)."""
        frac_left = 1.0 - step / self.n_steps
        return (self.tau0_days / TRADING_DAYS) * frac_left


def evolve_spot(
    market: MarketParams,
    cash_trades: np.ndarray,
    rng: np.random.Generator | None = None,
    with_noise: bool = False,
) -> tuple[np.ndarray, np.ndarray]:
    """Roll the spot path forward given a schedule of signed cash trades.

    Returns
    -------
    spot : ndarray, shape (n_steps + 1,)
        Mid path, ``spot[0] == s0`` and ``spot[n_steps]`` is the settlement print.
    exec_price : ndarray, shape (n_steps,)
        Fill price for each step's trade, including temporary impact.
    """
    n = market.n_steps
    if cash_trades.shape[0] != n:
        raise ValueError(f"cash_trades must have length n_steps={n}, got {cash_trades.shape[0]}")

    spot = np.empty(n + 1, dtype=float)
    exec_price = np.empty(n, dtype=float)
    spot[0] = market.s0

    noise = (
        rng.normal(0.0, market.sigma_step, size=n)
        if (with_noise and rng is not None)
        else np.zeros(n)
    )
    for t in range(n):
        q = cash_trades[t]
        exec_price[t] = spot[t] + market.eta * q          # temporary impact on the fill
        spot[t + 1] = spot[t] + market.gamma * q + noise[t]  # permanent impact persists
    return spot, exec_price
