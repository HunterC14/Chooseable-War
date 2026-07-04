# LowBot: anti-(minbot/antiminbot). Samples from the play distribution in
# ./_util/_lowbot.py: random among the cards that beat the opponent's estimated
# minimum, weighted towards low-ranked ones (rank taken among all cards still
# in play). Composed with a TrackedPlayer (./_util/_tracking.py) for the opponent
# estimate and war handling.
import random
import sys
from functools import partial
from pathlib import Path

_root = str(Path(__file__).resolve().parent / "_util")
if _root not in sys.path:
    sys.path.insert(0, _root)

from _lowbot import lowbot_weights
from _tracking import OpponentTracker, TrackedPlayer


def lowbot_decide(candidates: list[int], hand: list[int], tracker: OpponentTracker) -> int:
    weights = lowbot_weights(candidates, tracker.min_estimate(),
                             hand + tracker.concrete())
    cards = list(weights)
    return random.choices(cards, weights=[weights[c] for c in cards])[0]


bot = partial(TrackedPlayer, lowbot_decide)
