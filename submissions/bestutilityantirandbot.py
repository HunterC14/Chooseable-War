# BestUtilityAntiRandBot (formerly utilitymaxbot): plays the card with the
# highest expected utility, modeling the opponent as uniform-random over
# their tracked hand. See ./_util/_utilitybrain.py; composed with a TrackedPlayer.
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent / "_util")
if _root not in sys.path:
    sys.path.insert(0, _root)

from _tracking import bot_class
from _utilitybrain import make_utility_decide, pick_max

bot = bot_class(__name__, make_utility_decide(pick_max))
