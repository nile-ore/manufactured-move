"""P0 demo: run the pump-and-dump once, print the P&L decomposition, and plot it.

    python scripts/run_baseline.py

Produces reports/baseline.png (spot path + P&L waterfall) and prints the decomposition.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mmove import MarketParams, PumpDump, monte_carlo, simulate  # noqa: E402

REPORTS = Path(__file__).resolve().parents[1] / "reports"


def main() -> None:
    market = MarketParams()
    strategy = PumpDump(
        accumulate_units=1000.0,
        accumulate_frac=0.40,
        distribute_frac=0.40,
        end_short_units=0.0,        # clean round-trip to flat: cash leg is pure cost
        options_units=5000.0,
        options_structure="synthetic_short",
    )

    res = simulate(market, strategy, with_noise=False)

    print("\n=== manufactured-move :: baseline pump-and-dump (deterministic) ===\n")
    print(res.summary())
    print()
    print(f"  interpretation: paid ~{-res.cash_pnl:.0f} in the cash market to move the spot,")
    print(f"                  harvested ~{res.options_pnl:.0f} in the options book -> ", end="")
    print(f"{res.total_pnl / max(1.0, -res.cash_pnl):.0f}x return on the manipulation cost.\n")

    # Monte Carlo with noise, to show the edge survives diffusion
    mc = monte_carlo(market, strategy, n_paths=3000, seed=7)
    win = float((mc["total"] > 0).mean())
    print(f"  Monte Carlo (3000 noisy paths): mean total P&L {mc['total'].mean():.0f}, "
          f"P(profit) {win:.1%}\n")

    _plot(res, mc, REPORTS / "baseline.png")
    print(f"  saved plot -> {REPORTS / 'baseline.png'}\n")


def _plot(res, mc, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(15, 4.5))

    # --- spot path ---
    n = len(res.spot) - 1
    ax1.plot(res.spot, color="#1f77b4", lw=1.6)
    ax1.axhline(res.spot[0], color="grey", ls=":", lw=1, label="open")
    ax1.axvline(res.entry_step, color="#d62728", ls="--", lw=1)
    ax1.scatter([res.entry_step], [res.entry_spot], color="#d62728", zorder=5,
                label=f"book established @ {res.entry_spot:.2f}")
    ax1.scatter([n], [res.settle_spot], color="#2ca02c", zorder=5,
                label=f"settle @ {res.settle_spot:.2f}")
    ax1.axvspan(0, res.entry_step, color="#d62728", alpha=0.06)
    ax1.set_title("Manufactured spot path")
    ax1.set_xlabel("minute of session")
    ax1.set_ylabel("spot")
    ax1.legend(fontsize=8, loc="upper right")

    # --- P&L waterfall ---
    labels = ["cash /\nfutures", "options", "TOTAL"]
    vals = [res.cash_pnl, res.options_pnl, res.total_pnl]
    colors = ["#d62728" if v < 0 else "#2ca02c" for v in vals[:2]] + ["#1f77b4"]
    ax2.bar(labels, vals, color=colors)
    ax2.axhline(0, color="k", lw=0.8)
    for i, v in enumerate(vals):
        ax2.text(i, v, f"{v:,.0f}", ha="center",
                 va="bottom" if v >= 0 else "top", fontsize=9)
    ax2.set_title("P&L decomposition")
    ax2.set_ylabel("P&L (points x units)")

    # --- Monte Carlo distribution ---
    ax3.hist(mc["total"], bins=50, color="#1f77b4", alpha=0.8)
    ax3.axvline(0, color="k", lw=1)
    ax3.axvline(mc["total"].mean(), color="#d62728", ls="--", lw=1.2,
                label=f"mean {mc['total'].mean():,.0f}")
    ax3.set_title(f"Total P&L over {len(mc['total'])} noisy paths")
    ax3.set_xlabel("total P&L")
    ax3.legend(fontsize=8)

    fig.suptitle("manufactured-move — expiry-day pump-and-dump into a bearish options book",
                 fontsize=12, y=1.02)
    fig.tight_layout()
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
