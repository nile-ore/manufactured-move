"""P1: sweep the break-even surface — when does manufacturing a move pay?

    python scripts/sweep.py

Produces reports/breakeven.png: total P&L over (options size) x (temporary impact),
with the zero-P&L contour drawn on top.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mmove import MarketParams, PumpDump  # noqa: E402
from mmove.analysis import sweep_2d  # noqa: E402

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def main() -> None:
    market = MarketParams()
    strategy = PumpDump(end_short_units=0.0)

    options_units = np.linspace(0.0, 8000.0, 60)     # x: size of the bearish book
    eta = np.linspace(0.001, 0.02, 60)               # y: cost of moving the spot

    grid = sweep_2d(market, strategy, "options_units", options_units, "eta", eta,
                    metric="total_pnl")

    REPORTS.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(7.5, 5.5))
    vmax = np.abs(grid).max()
    im = ax.pcolormesh(options_units, eta, grid, cmap="RdYlGn", vmin=-vmax, vmax=vmax,
                       shading="auto")
    cs = ax.contour(options_units, eta, grid, levels=[0], colors="k", linewidths=1.6)
    ax.clabel(cs, fmt="break-even", fontsize=9)
    fig.colorbar(im, ax=ax, label="total P&L (points x units)")
    ax.set_xlabel("options book size (units)  ->  leverage over cash")
    ax.set_ylabel("temporary impact eta  ->  cost of moving the spot")
    ax.set_title("When does manufacturing a move pay?\n"
                 "green = profitable manipulation, red = costs exceed the options gain")
    fig.tight_layout()
    out = REPORTS / "breakeven.png"
    fig.savefig(out, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"saved -> {out}")


if __name__ == "__main__":
    main()
