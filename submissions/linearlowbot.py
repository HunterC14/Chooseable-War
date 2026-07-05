# LinearLowBot (formerly lowbot): anti-(minbot/antiminbot). Samples from the
# play distribution in ./_util/_lowbot.py: random among the cards that beat
# the opponent's estimated minimum, weighted LINEARLY towards low-ranked ones
# (weight n + 1 - r, rank taken among all cards still in play). Composed with
# a TrackedPlayer (./_util/_tracking.py) for the opponent estimate and war
# handling.
import sys
from functools import partial
from pathlib import Path

_root = str(Path(__file__).resolve().parent / "_util")
if _root not in sys.path:
    sys.path.insert(0, _root)

from _lowbot import make_lowbot_decide, shape_linear
from _tracking import TrackedPlayer

bot = partial(TrackedPlayer, make_lowbot_decide(shape_linear))
# highness: 0.474
