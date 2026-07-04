"""Utility strategies for the utility bots in submissions/. Bot names follow
the scheme <pick>utility<opponent-model>:

  pick:  best...     = play the highest-EU card (pick_max)
         weighted... = logistic-weighted random by EU (pick_logistic)
  model: ...antirandbot    = opponent plays uniformly over their hand
         ...antilowbot     = opponent is lowbot (model in _lowbot.py)
         ...antiutilitybot = opponent is weightedutilityantirandbot

This module contains no classes to inherit: a submission composes
`make_utility_decide(pick, opp_model)` with a TrackedPlayer from
_tracking.py, which supplies opponent-hand tracking.

STRATEGY (assumes a 2-PLAYER game)
==================================

Utility
-------
Rank every card in (my hand + opponent hand) jointly: sorted ascending, the
smallest card has rank 1, the largest rank N; equal values share their
average rank (needed because the real deck has duplicates). A player's
utility is the sum of the ranks of their cards; our objective is the
DIFFERENCE (my utility - opponent utility).

Example (from the spec, with distinct values): A={11,13,16}, B={12,15,30}.
Ranks of 11,12,13,15,16,30 are 1..6, so utility(A)=1+3+5=9, utility(B)=
2+4+6=12. If A plays 11 and B plays 30, B wins A's 11 but B's own played
card leaves play (mirroring the engine, where the winner never gets their
compared card back): A={13,16}, B={11,12,15}. Re-ranking the 5 remaining
cards gives utility(A)=3+5=8, utility(B)=1+2+4=7 - so B's "win" actually
LOST B utility relative to A. That reversal is the whole point: winning a
trick costs you the card you won it with, and utility measures whether the
exchange was worth it.

Move selection
--------------
For each candidate card n in our hand and each value m the opponent might
play (probability proportional to its modeled weight), simulate the trick
under the engine's rules (higher wins; 2 beats ace; ace still beats the
other non-2 cards; a tie is approximated as both compare cards leaving play,
standing in for a war ante) and compute the resulting utility difference.
EU(n) = sum_m P(m) * utility_diff_after(n, m).

Pick strategies:
* pick_max      (best...)     - play the card with the highest EU; ties
  broken uniformly at random.
* pick_logistic (weighted...) - play a random card, weighted by a logistic
  function of EU: w(n) = 1 / (1 + exp(-(EU(n) - mean EU) / T)) with T the
  standard deviation of the EUs (uniform if all EUs are equal). Centering on
  the mean keeps weights meaningful regardless of the EUs' absolute scale.

Opponent models:
* uniform_opp_model         (...antirandbot)    - uniform over the tracked
  estimate of the opponent's hand.
* weighted_utility_opp_model (...antiutilitybot) - the opponent is a
  weightedutilityantirandbot: compute their EUs from THEIR perspective
  (their hand is our tracked estimate; they are assumed to model us as
  uniform over our actual hand) and logistic-weight those into a play
  distribution.
* lowbot_opp_model (in _lowbot.py) (...antilowbot) - the opponent is lowbot.

Wars: the TrackedPlayer discards our 3 lowest cards (they only feed the
bounty) and picks the compare card with the same decide function.
"""

import math
import random
from collections import Counter

from _tracking import OpponentTracker, beats, joint_ranks


def rank_utilities(mine: list[int], theirs: list[int]) -> tuple[float, float]:
    """Utility of each hand = sum of joint ranks (ties get their average rank)."""
    ranks = joint_ranks(mine + theirs)
    return (sum(ranks[c] for c in mine), sum(ranks[c] for c in theirs))


def simulate_trick(my_hand: list[int], opp_hand: list[int], n: int, m: int) -> float:
    """Utility difference (mine - theirs) after I play n and the opponent plays m.

    Engine-faithful outcome for a 2-player trick: the winner takes the loser's
    card, but the winner's own compared card leaves play. In the ace-vs-2 case
    the engine returns the ace to its owner and awards a copy to the 2's owner
    (the 2 is spent); we model that too. A tie (-> war) is approximated as both
    compare cards leaving play.
    """
    my = Counter(my_hand)
    my[n] -= 1
    opp = Counter(opp_hand)
    opp[m] -= 1
    if {n, m} == {14, 2}:
        my[14] += 1   # ace owner keeps it / 2's owner gains one
        opp[14] += 1
    elif n == m:
        pass          # war ante approximation: both compare cards gone
    elif beats(n, m):
        my[m] += 1    # I take their card; my n stays gone
    else:
        opp[n] += 1   # they take mine; their m stays gone
    mu, ou = rank_utilities(list(my.elements()), list(opp.elements()))
    return mu - ou


def expected_utilities(my_hand: list[int], candidates: list[int],
                       opp_hand: list[int], opp_dist: dict[int, float]) -> dict[int, float]:
    """EU (my utility - theirs) of playing each candidate, against an opponent
    whose played card is distributed proportionally to `opp_dist` and whose
    remaining hand is `opp_hand`."""
    total_w = sum(w for w in opp_dist.values() if w > 1e-9)
    if total_w <= 0:
        return {n: float(n) for n in candidates}  # no info: prefer high cards
    eus: dict[int, float] = {}
    for n in candidates:
        eu = 0.0
        for m, w in opp_dist.items():
            if w <= 1e-9:
                continue
            hypo = opp_hand if m in opp_hand else opp_hand + [m]
            eu += (w / total_w) * simulate_trick(my_hand, hypo, n, m)
        eus[n] = eu
    return eus


def logistic_weights(eus: dict[int, float]) -> dict[int, float]:
    """w(c) = sigmoid((EU(c) - mean) / stdev); uniform if all EUs are equal."""
    vals = list(eus.values())
    mean = sum(vals) / len(vals)
    t = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))  # stdev
    if t < 1e-9:
        return {c: 1.0 for c in eus}
    return {c: 1.0 / (1.0 + math.exp(-(u - mean) / t)) for c, u in eus.items()}


def pick_max(eus: dict[int, float]) -> int:
    best = max(eus.values())
    return random.choice([c for c, u in eus.items() if u == best])


def pick_logistic(eus: dict[int, float]) -> int:
    weights = logistic_weights(eus)
    cards = list(weights)
    return random.choices(cards, weights=[weights[c] for c in cards])[0]


def uniform_opp_model(hand: list[int], opp_hand: list[int],
                      tracker: OpponentTracker) -> dict[int, float]:
    """Opponent plays uniformly at random over their (estimated) hand."""
    return tracker.estimate


def weighted_utility_opp_model(hand: list[int], opp_hand: list[int],
                               tracker: OpponentTracker) -> dict[int, float]:
    """Opponent is a weightedutilityantirandbot: their play distribution is
    the logistic weighting of their EUs, computed from their perspective
    (they hold opp_hand, we hold `hand`, and they model us as uniform over it)."""
    if not opp_hand:
        return tracker.estimate
    opp_eus = expected_utilities(opp_hand, sorted(set(opp_hand)),
                                 hand, dict(Counter(hand)))
    return logistic_weights(opp_eus)


def make_utility_decide(pick, opp_model=uniform_opp_model):
    """Build a decide(candidates, hand, tracker) function for TrackedPlayer:
    expected utility against `opp_model`'s play distribution, chosen by `pick`."""
    def decide(candidates: list[int], hand: list[int], tracker: OpponentTracker) -> int:
        if len(candidates) == 1:
            return candidates[0]
        opp_hand = tracker.concrete()
        eus = expected_utilities(hand, candidates, opp_hand,
                                 opp_model(hand, opp_hand, tracker))
        return pick(eus)
    return decide
