"""Opponent-hand tracking helpers, built for composition (no bot base class).

Two pieces, meant to be HELD by bots rather than inherited from:

* OpponentTracker - pure state machine estimating the opponent's hand.
  Knows nothing about strategies or the engine interface.
* TrackedPlayer   - engine adapter. HAS an OpponentTracker and HAS a
  `decide` callable (the strategy); it wires start_game / set_hand /
  choose_card / war to the tracker at the right moments. A submission
  module exposes it directly:

      bot = partial(TrackedPlayer, my_decide_function)

  where `my_decide_function(candidates, hand, tracker) -> card` receives the
  distinct playable values (sorted), the current hand, and the tracker.

The tournament engine instantiates `module.bot()` and displays bots by module
(file) name, so no per-bot wrapper class is needed.

HOW TRACKING WORKS (assumes a 2-PLAYER game)
============================================
The full deck is known (four copies of each value 2..14), so at the first
sync after a deal the opponent's hand is exactly (full deck - my hand). From
then on the tracker maintains an estimate `opp` (value -> fractional count)
updated from what the bot can observe:

* If our hand grew since our last decision, we won the previous trick/war.
  The cards we gained (minus our own returning war-sacrifice cards) came from
  the opponent, so we subtract them from the estimate. Our own compare card
  left play (the engine never returns the winner's compared card).
* If our hand only shrank by what we played, we lost. Everything we committed
  went to the opponent, and the opponent's winning compare card left play. We
  don't observe its value, so we remove 1.0 of probability mass, spread
  proportionally over the values that could have beaten our card (v > ours;
  only 2 if we played an ace, since 2 beats ace; 3..13 if we played a 2,
  since our 2 beats an ace).
* In a war we DO see the opponent's compare card (the `cards` dict), and
  subtract it directly.

The estimate is approximate (unknown cards leave play on losses, and the
engine's ace-vs-2 branch duplicates cards), but it stays close to the true
hand and gives a sensible probability distribution over the opponent's next
card.
"""

from collections import Counter

FULL_DECK = Counter({v: 4 for v in range(2, 15)})  # 2-10 + JQKA(11-14), 4 suits


def joint_ranks(cards: list[int]) -> dict[int, float]:
    """Rank map for a multiset of cards: sorted ascending, smallest has rank 1,
    largest rank N; equal values share their average rank."""
    ordered = sorted(cards)
    n = len(ordered)
    ranks: dict[int, float] = {}
    i = 0
    while i < n:
        j = i
        while j < n and ordered[j] == ordered[i]:
            j += 1
        ranks[ordered[i]] = (i + 1 + j) / 2  # average of ranks i+1 .. j
        i = j
    return ranks


def beats(a: int, b: int) -> bool:
    """Does card a beat card b in this game? (2 beats ace; ace beats the rest.)"""
    if {a, b} == {2, 14}:
        return a == 2
    return a > b


class OpponentTracker:
    """Estimates the opponent's hand in a 2-player game. Pure state: the
    owner must call `sync` at each decision point, `played` after deciding,
    and `saw_opponent_card` when a war reveals the opponent's compare card."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Forget everything (call at the start of a new game)."""
        self._opp: dict[int, float] | None = None  # value -> estimated count
        self._expected: Counter = Counter()  # hand we expect if we won nothing
        self._pending_compare: Counter = Counter()    # compare cards in flight
        self._pending_sacrifice: Counter = Counter()  # war sacrifices in flight
        self._last_compare: int | None = None

    # ---- observations ------------------------------------------------------

    def sync(self, hand: list[int]):
        """Bring the estimate up to date at a decision point, inferring the
        previous trick's outcome from how our hand changed."""
        cur = Counter(hand)
        if self._opp is None:
            if hand:  # first sight of our deal: opponent holds the rest
                self._opp = {v: float(c) for v, c in (FULL_DECK - cur).items()}
                self._expected = cur
            return
        pending = self._pending_compare + self._pending_sacrifice
        if not pending:
            return
        gained = cur - self._expected
        if gained:
            # We won. Our sacrifices came back; anything else was the opponent's.
            # Exception: winning an ace-vs-2 as the ace returns our own ace
            # (the opponent played the 2).
            if self._last_compare == 14 and gained == Counter([14]):
                self._sub(2, 1)
                self._opp[14] = self._opp.get(14, 0.0) + 1  # engine grants them a copy
            else:
                for v, k in (gained - self._pending_sacrifice).items():
                    self._sub(v, k)
        else:
            # We lost: everything we committed is theirs now...
            for v, k in pending.items():
                self._opp[v] = self._opp.get(v, 0.0) + k
            # ...and their (unseen) winning card left play: remove 1.0 of mass
            # spread over the values that could have beaten ours.
            c = self._last_compare
            if c is not None:
                if c == 14:
                    could_win = [2]
                elif c == 2:
                    could_win = list(range(3, 14))
                else:
                    could_win = list(range(c + 1, 15))
                mass = sum(self._opp.get(v, 0.0) for v in could_win)
                if mass > 0:
                    for v in could_win:
                        w = self._opp.get(v, 0.0)
                        if w > 0:
                            self._opp[v] = max(0.0, w - w / mass)
        self._pending_compare = Counter()
        self._pending_sacrifice = Counter()
        self._expected = cur

    def played(self, hand: list[int], compare: int, sacrifices: list[int] = []):
        """Record our own play (hand = our hand BEFORE the engine removes the
        cards): a compare card and, in wars, the sacrificed cards."""
        self._pending_compare[compare] += 1
        for c in sacrifices:
            self._pending_sacrifice[c] += 1
        self._last_compare = compare
        self._expected = Counter(hand) - Counter([compare, *sacrifices])

    def saw_opponent_card(self, card: int):
        """A war revealed the opponent's compare card."""
        self._sub(card, 1)

    # ---- queries -----------------------------------------------------------

    @property
    def estimate(self) -> dict[int, float]:
        """Estimated opponent hand: value -> fractional count."""
        return dict(self._opp) if self._opp else {}

    def concrete(self) -> list[int]:
        """The estimate rounded to a concrete multiset."""
        out: list[int] = []
        for v, w in (self._opp or {}).items():
            out.extend([v] * min(4, round(w)))
        return out

    def min_estimate(self) -> int:
        """Lowest card the opponent likely holds (ignoring residual mass)."""
        est = self.estimate
        solid = [v for v, w in est.items() if w > 0.5]
        return min(solid or [v for v, w in est.items() if w > 1e-9] or [2])

    def _sub(self, v: int, k: float):
        if self._opp is not None:
            self._opp[v] = max(0.0, self._opp.get(v, 0.0) - k)


class TrackedPlayer:
    """Engine adapter: owns an OpponentTracker and a strategy callable
    `decide(candidates, hand, tracker) -> card`. Wars discard the 3 weakest
    cards and use `decide` for the compare card."""

    def __init__(self, decide):
        self.decide = decide
        self.tracker = OpponentTracker()
        self.my_id: int | None = None
        self.hand: list[int] = []

    def start_game(self, id: int):
        self.my_id = id
        self.hand = []
        self.tracker.reset()  # start_game marks the start of a new game

    def set_hand(self, toset: list[int]):
        self.hand = list(toset)  # copy: the engine mutates its lists in place

    def choose_card(self) -> int:
        self.tracker.sync(self.hand)
        card = self.decide(sorted(set(self.hand)), self.hand, self.tracker)
        self.tracker.played(self.hand, card)
        return card

    def war(self, cards: dict[int, int], ofnum: int, bounty: list[int]) -> tuple[int, int, int, int]:
        for pid, c in cards.items():
            if pid != self.my_id:
                self.tracker.saw_opponent_card(c)
        ordered = sorted(self.hand)
        sacrifice = ordered[:3]  # discard the 3 weakest cards
        play = self.decide(sorted(set(ordered[3:])), self.hand, self.tracker)
        self.tracker.played(self.hand, play, sacrifice)
        return (play, *sacrifice)
