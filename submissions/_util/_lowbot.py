"""Core of the lowbot strategy family, shared by the *lowbot submissions
(which sample from it with different weight shapes) and the ...antilowbot
utility bots (which use the linear shape as a model of their opponent's play
via `lowbot_opp_model`).

A lowbot never plays at-or-below the opponent's minimum (those plays just
lose the trick and bleed cards); it plays randomly among the cards that beat
that minimum, weighted towards LOW cards. How strongly it prefers low is set
by a SHAPE function `shape(card, rank, n, opp_min) -> weight`, where rank is
the card's joint rank among all `n` cards still in play (rank 1 = lowest).
Edge cases (all shapes): a 2 beats an ace, so play a 2 if the opponent's
minimum is an ace; if nothing beats that minimum, dump the lowest card.

Shapes (each a submission in ../):

* shape_linear    - weight n + 1 - r: the original lowbot ramp (linearlowbot)
* shape_square    - (n + 1 - r)^2: concentrates on the cheapest winners
* shape_expo      - 0.7^r: geometric decay, constant preference ratio per rank
* shape_logistic  - smooth cutoff at median rank: any cheap winner is fine,
                    the top half is hoarded
* shape_margin    - exp(-(card - opp_min)): weights by wasted VALUE over the
                    opponent's minimum instead of rank
* shape_invrank   - 1/r: strong low preference with a fat high-card tail
"""

import math
import random

from _tracking import OpponentTracker, joint_ranks


# ---- weight shapes: shape(card, rank, n, opp_min) -> weight ----------------

def shape_linear(c: int, r: float, n: int, opp_min: int) -> float:
    return n + 1 - r


def shape_square(c: int, r: float, n: int, opp_min: int) -> float:
    return (n + 1 - r) ** 2


def shape_expo(c: int, r: float, n: int, opp_min: int) -> float:
    return 0.7 ** r


def shape_logistic(c: int, r: float, n: int, opp_min: int) -> float:
    return 1 / (1 + math.exp((r - n / 2) / max(1.0, n / 8)))


def shape_margin(c: int, r: float, n: int, opp_min: int) -> float:
    return math.exp(-(c - opp_min))


def shape_invrank(c: int, r: float, n: int, opp_min: int) -> float:
    return 1 / r


# -----------------------------------------------------------------------------

def lowbot_weights(candidates: list[int], opp_min: int, remaining: list[int],
                   shape=shape_linear) -> dict[int, float]:
    """The play distribution (value -> weight) over `candidates`, given the
    opponent's minimum card, the multiset of all cards still in play, and a
    weight shape."""
    if opp_min == 14 and 2 in candidates:
        return {2: 1.0}  # 2 beats ace
    beating = [c for c in candidates if c > opp_min]
    if not beating:
        return {min(candidates): 1.0}  # nothing wins: dump the lowest card
    ranks = joint_ranks(remaining)
    n = len(remaining)
    return {c: shape(c, ranks[c], n, opp_min) for c in beating}


def make_lowbot_decide(shape):
    """Build a TrackedPlayer `decide` that samples from lowbot_weights with
    the given shape."""
    def decide(candidates: list[int], hand: list[int],
               tracker: OpponentTracker) -> int:
        weights = lowbot_weights(candidates, tracker.min_estimate(),
                                 hand + tracker.concrete(), shape)
        cards = list(weights)
        return random.choices(cards, weights=[weights[c] for c in cards])[0]
    return decide


def lowbot_opp_model(hand: list[int], opp_hand: list[int],
                     tracker: OpponentTracker) -> dict[int, float]:
    """Opponent-model form of the original (linear) lowbot for
    make_utility_decide: their play distribution from their perspective (they
    hold our tracked estimate of their hand, our minimum is what they try to
    beat, and remaining cards are both hands; their estimate of us is assumed
    accurate)."""
    if not opp_hand:
        return tracker.estimate
    my_min = min(hand) if hand else 2
    return lowbot_weights(sorted(set(opp_hand)), my_min, opp_hand + hand)
