# AntiMinBot: assumes the opponent is minbot (always plays their lowest card)
# and plays the cheapest card that still beats it: the smallest card in our
# hand strictly above the opponent's estimated minimum. Edge cases: a 2 beats
# an ace, so play a 2 if their minimum is an ace; if nothing beats their
# minimum, dump our lowest card. Composed with a TrackedPlayer (./_util/_tracking.py)
# which supplies the opponent estimate and war handling.
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent / "_util")
if _root not in sys.path:
    sys.path.insert(0, _root)

from _tracking import OpponentTracker, bot_class


def antimin_decide(candidates: list[int], hand: list[int], tracker: OpponentTracker) -> int:
    opp_min = tracker.min_estimate()
    if opp_min == 14 and 2 in candidates:
        return 2  # 2 beats ace
    above = [c for c in candidates if c > opp_min]
    return min(above) if above else min(candidates)


bot = bot_class(__name__, antimin_decide)
