"""Run a single expiry-day path and decompose the P&L into its two legs.

The headline result: with a hand-coded pump-and-dump the **cash/futures leg is a small
loss** (round-trip costs) while the **options leg is a large gain** (the book was
established at the manufactured peak and settles at the depressed close). Net positive,
because the options size dwarfs the cash size used to move the market.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .market import MarketParams, evolve_spot
from .options import OptionsBook, bearish_book
from .strategy import PumpDump


@dataclass
class SimResult:
    # path
    spot: np.ndarray
    exec_price: np.ndarray
    cash_trades: np.ndarray
    inventory: np.ndarray
    # key prints
    entry_step: int
    entry_spot: float
    peak_spot: float
    settle_spot: float
    # P&L decomposition (in points x units)
    cash_pnl: float
    options_pnl: float
    total_pnl: float
    # diagnostics
    temp_impact_cost: float
    manufactured_move: float
    leverage_ratio: float
    options_pnl_fair: float   # counterfactual: same book, no manufactured move
    manip_alpha: float        # options_pnl attributable to the manufactured move
    book: OptionsBook

    def summary(self) -> str:
        lines = [
            f"  peak spot         {self.peak_spot:8.3f}   (open {self.spot[0]:.3f})",
            f"  entry spot        {self.entry_spot:8.3f}   (book established here)",
            f"  settle spot       {self.settle_spot:8.3f}",
            f"  manufactured move {self.manufactured_move:8.3f}   (entry - settle)",
            f"  leverage ratio    {self.leverage_ratio:8.2f}x  (options units / cash units)",
            "  " + "-" * 44,
            f"  cash / futures leg {self.cash_pnl:12.1f}",
            f"  options leg        {self.options_pnl:12.1f}",
            f"  {'':17s} {'=' * 12}",
            f"  TOTAL P&L          {self.total_pnl:12.1f}",
            "  " + "-" * 44,
            f"  temp-impact cost   {self.temp_impact_cost:12.1f}   (paid to move the spot)",
            f"  manip alpha        {self.manip_alpha:12.1f}   (options P&L from the move alone)",
        ]
        return "\n".join(lines)


def simulate(
    market: MarketParams,
    strategy: PumpDump,
    rng: np.random.Generator | None = None,
    with_noise: bool = False,
) -> SimResult:
    n = market.n_steps
    cash_trades, entry_step = strategy.schedule(n)

    spot, exec_price = evolve_spot(market, cash_trades, rng=rng, with_noise=with_noise)
    inventory = np.concatenate([[0.0], np.cumsum(cash_trades)])

    entry_spot = float(spot[entry_step])
    settle_spot = float(spot[n])
    peak_spot = float(spot.max())

    # --- cash / futures leg -------------------------------------------------
    # cashflow: buying (q>0) costs cash; selling returns cash. Mark terminal inventory at close.
    cashflow = -float(np.sum(cash_trades * exec_price))
    cash_pnl = cashflow + float(inventory[n]) * settle_spot
    temp_impact_cost = float(np.sum(market.eta * cash_trades**2))

    # --- options leg --------------------------------------------------------
    book = bearish_book(strategy.options_structure, strategy.options_units, entry_spot)
    tau_entry = market.tau(entry_step)
    v_entry = book.value(market, entry_spot, tau_entry)
    v_settle = book.value(market, settle_spot, market.tau(n))  # tau -> 0 => intrinsic
    options_pnl = v_settle - v_entry

    # counterfactual: identical book but no manufactured move (open == close == s0)
    fair_book = bearish_book(strategy.options_structure, strategy.options_units, market.s0)
    v_fair_entry = fair_book.value(market, market.s0, tau_entry)
    v_fair_settle = fair_book.value(market, market.s0, market.tau(n))
    options_pnl_fair = v_fair_settle - v_fair_entry

    total_pnl = cash_pnl + options_pnl
    cash_units = strategy.accumulate_units if strategy.accumulate_units else 1.0
    return SimResult(
        spot=spot,
        exec_price=exec_price,
        cash_trades=cash_trades,
        inventory=inventory,
        entry_step=entry_step,
        entry_spot=entry_spot,
        peak_spot=peak_spot,
        settle_spot=settle_spot,
        cash_pnl=cash_pnl,
        options_pnl=options_pnl,
        total_pnl=total_pnl,
        temp_impact_cost=temp_impact_cost,
        manufactured_move=entry_spot - settle_spot,
        leverage_ratio=strategy.options_units / cash_units,
        options_pnl_fair=options_pnl_fair,
        manip_alpha=options_pnl - options_pnl_fair,
        book=book,
    )


def monte_carlo(
    market: MarketParams,
    strategy: PumpDump,
    n_paths: int = 2000,
    seed: int = 0,
) -> dict[str, np.ndarray]:
    """Repeat the strategy over noisy paths; returns arrays of the P&L legs."""
    rng = np.random.default_rng(seed)
    total = np.empty(n_paths)
    cash = np.empty(n_paths)
    opts = np.empty(n_paths)
    for i in range(n_paths):
        res = simulate(market, strategy, rng=rng, with_noise=True)
        total[i], cash[i], opts[i] = res.total_pnl, res.cash_pnl, res.options_pnl
    return {"total": total, "cash": cash, "options": opts}
