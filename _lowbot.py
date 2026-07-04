"""Core of lowbot's strategy, shared by submissions/lowbot.py (which samples
from it) and the ...antilowbot utility bots (which use it as a model of
their opponent's play via `lowbot_opp_model`).

Lowbot never plays at-or-below the opponent's minimum (those plays just lose
the trick and bleed cards); it plays randomly among the cards that beat that
minimum, weighted towards LOW-RANKED ones, where rank is computed among all
cards still in play: with N cards remaining, a card of rank r gets weight
N + 1 - r. Edge cases: a 2 beats an ace, so it plays a 2 if the opponent's
minimum is an ace; if nothing beats that minimum, it dumps its lowest card.
"""

from _tracking import OpponentTracker, joint_ranks


def lowbot_weights(candidates: list[int], opp_min: int,
                   remaining: list[int]) -> dict[int, float]:
    """Lowbot's play distribution (value -> weight) over `candidates`, given
    the opponent's minimum card and the multiset of all cards still in play."""
    if opp_min == 14 and 2 in candidates:
        return {2: 1.0}  # 2 beats ace
    beating = [c for c in candidates if c > opp_min]
    if not beating:
        return {min(candidates): 1.0}  # nothing wins: dump the lowest card
    ranks = joint_ranks(remaining)
    n = len(remaining)
    return {c: n + 1 - ranks[c] for c in beating}


def lowbot_opp_model(hand: list[int], opp_hand: list[int],
                     tracker: OpponentTracker) -> dict[int, float]:
    """Opponent-model form of lowbot for make_utility_decide: their play
    distribution from their perspective (they hold our tracked estimate of
    their hand, our minimum is what they try to beat, and remaining cards
    are both hands; their estimate of us is assumed accurate)."""
    if not opp_hand:
        return tracker.estimate
    my_min = min(hand) if hand else 2
    return lowbot_weights(sorted(set(opp_hand)), my_min, opp_hand + hand)
