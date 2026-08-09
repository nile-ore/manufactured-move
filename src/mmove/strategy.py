"""Hand-coded pump-and-dump strategy (the documented SEBI/Jane Street pattern).

Phase 1 (accumulate): buy the basket over the morning -> permanent impact pumps spot up.
   ...establish a large bearish options book at the manufactured peak...
Phase 2 (distribute): sell the basket back down -> spot falls, the bearish book pays.

``end_short_units > 0`` leaves a net short into the close ("marking the close"): the
extra net selling drags the *settlement* print below the open, amplifying the options
payoff. ``end_short_units == 0`` is a clean round-trip to flat, which isolates the
manipulation edge: the cash leg is a pure cost, yet the options leg still wins because
the book was established at the pumped peak.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class PumpDump:
    accumulate_units: float = 1000.0   # total bought during the pump
    accumulate_frac: float = 0.40      # fraction of the session spent accumulating
    distribute_frac: float = 0.40      # fraction spent distributing (selling back)
    end_short_units: float = 0.0       # extra net-short carried into the close (marking the close)
    options_units: float = 5000.0      # size per leg of the bearish options book
    options_structure: str = "synthetic_short"

    def schedule(self, n_steps: int) -> tuple[np.ndarray, int]:
        """Build the signed per-step cash-trade array and the options-establishment step.

        Returns ``(cash_trades, entry_step)`` where ``entry_step`` is the peak, i.e. the
        moment the bearish book is established.
        """
        acc_steps = max(1, int(round(self.accumulate_frac * n_steps)))
        dist_steps = max(1, int(round(self.distribute_frac * n_steps)))
        if acc_steps + dist_steps > n_steps:
            raise ValueError("accumulate_frac + distribute_frac must be <= 1")

        trades = np.zeros(n_steps, dtype=float)
        trades[:acc_steps] = self.accumulate_units / acc_steps  # buy up
        to_sell = self.accumulate_units + self.end_short_units
        trades[acc_steps : acc_steps + dist_steps] = -to_sell / dist_steps  # sell down
        entry_step = acc_steps  # establish the book right at the manufactured peak
        return trades, entry_step
