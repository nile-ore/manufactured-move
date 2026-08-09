"""manufactured-move: a simulation of the SEBI/Jane Street expiry-day options strategy.

Move the spot in the (smaller) cash/futures market so the (much larger) options book,
established at the manufactured peak, settles in the money. See ``README.md``.
"""

from __future__ import annotations

from .market import MarketParams
from .options import Leg, OptionsBook, bearish_book
from .simulator import SimResult, monte_carlo, simulate
from .strategy import PumpDump

__version__ = "0.1.0"
__all__ = [
    "MarketParams",
    "PumpDump",
    "OptionsBook",
    "Leg",
    "bearish_book",
    "SimResult",
    "simulate",
    "monte_carlo",
]
