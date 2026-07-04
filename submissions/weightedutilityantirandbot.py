# WeightedUtilityAntiRandBot (formerly utilityrandbot): picks logistically-
# weighted random by expected utility, modeling the opponent as uniform-
# random over their tracked hand. See ../_utilitybrain.py; composed with a
# TrackedPlayer.
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from _tracking import bot_class
from _utilitybrain import make_utility_decide, pick_logistic

bot = bot_class(__name__, make_utility_decide(pick_logistic))
