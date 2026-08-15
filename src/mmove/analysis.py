"""Sensitivity analysis (P1): when does manufacturing a move actually pay?

The manipulation is profitable when the options gain beats the round-trip cost of moving
the spot, roughly::

    options_units * |manufactured_move|   >   temp_impact_cost(cash_units, eta)

``sweep_2d`` traces that boundary over any two parameters so the break-even surface can be
plotted as a heatmap.
"""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from .market import MarketParams
from .simulator import simulate
from .strategy import PumpDump


def _set_param(market: MarketParams, strategy: PumpDump, name: str, value: float):
    """Override a field on whichever of (market, strategy) owns it."""
    if hasattr(market, name) and name in market.__dataclass_fields__:
        return replace(market, **{name: value}), strategy
    if hasattr(strategy, name) and name in strategy.__dataclass_fields__:
        return market, replace(strategy, **{name: value})
    raise KeyError(f"no field {name!r} on MarketParams or PumpDump")


def sweep_2d(
    market: MarketParams,
    strategy: PumpDump,
    x_name: str,
    x_values: np.ndarray,
    y_name: str,
    y_values: np.ndarray,
    metric: str = "total_pnl",
) -> np.ndarray:
    """Return a ``(len(y_values), len(x_values))`` grid of ``metric`` over the two axes."""
    grid = np.empty((len(y_values), len(x_values)), dtype=float)
    for i, yv in enumerate(y_values):
        for j, xv in enumerate(x_values):
            m, s = _set_param(market, strategy, x_name, xv)  # `replace` returns copies; originals untouched
            m, s = _set_param(m, s, y_name, yv)
            grid[i, j] = getattr(simulate(m, s), metric)
    return grid
