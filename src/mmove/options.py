"""The options book: a set of signed legs, marked to spot via Black-Scholes.

The manipulator establishes this book *at the manufactured peak* and lets it settle at
the (depressed) closing spot. Because option prices here are pinned to the underlying and
the book carries no price impact of its own, the manipulator can hold size far exceeding
the cash quantity used to move the spot.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .black_scholes import bs_delta, bs_price
from .market import MarketParams


@dataclass
class Leg:
    qty: float      # signed contracts: + = long, - = short
    kind: str       # "call" or "put"
    strike: float


@dataclass
class OptionsBook:
    legs: list[Leg] = field(default_factory=list)

    def value(self, market: MarketParams, spot: float, tau: float) -> float:
        return float(
            sum(
                leg.qty * bs_price(spot, leg.strike, tau, market.r, market.sigma_annual, leg.kind)
                for leg in self.legs
            )
        )

    def delta(self, market: MarketParams, spot: float, tau: float) -> float:
        return float(
            sum(
                leg.qty * bs_delta(spot, leg.strike, tau, market.r, market.sigma_annual, leg.kind)
                for leg in self.legs
            )
        )


def bearish_book(structure: str, units: float, entry_spot: float) -> OptionsBook:
    """Construct a bearish book of the given ``structure``, all struck around ``entry_spot``.

    - ``synthetic_short``: short ATM call + long ATM put  (delta ~ -units; clean intuition)
    - ``risk_reversal``  : short OTM call + long OTM put   (cheaper, wider, still bearish)
    - ``otm_puts``       : long OTM puts only              (convex; explodes if spot pushed down)
    """
    K = entry_spot
    if structure == "synthetic_short":
        return OptionsBook([Leg(-units, "call", K), Leg(+units, "put", K)])
    if structure == "risk_reversal":
        return OptionsBook([Leg(-units, "call", 1.02 * K), Leg(+units, "put", 0.98 * K)])
    if structure == "otm_puts":
        return OptionsBook([Leg(+units, "put", 0.98 * K)])
    raise ValueError(f"unknown structure {structure!r}")
