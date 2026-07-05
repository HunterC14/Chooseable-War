# BestUtilityAntiRandBot (formerly utilitymaxbot): plays the card with the
# highest expected utility, modeling the opponent as uniform-random over
# their tracked hand. See ./_util/_utilitybrain.py; composed with a TrackedPlayer.
import sys
from functools import partial
from pathlib import Path

_root = str(Path(__file__).resolve().parent / "_util")
if _root not in sys.path:
    sys.path.insert(0, _root)

from _tracking import TrackedPlayer
from _utilitybrain import make_utility_decide, pick_max

bot = partial(TrackedPlayer, make_utility_decide(pick_max))
# highness: 0.095
