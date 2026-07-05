# WeightedUtilityAntiUtilityBot (formerly utilitysuperbot): picks
# logistically-weighted random by expected utility, modeling the opponent as
# a WEIGHTEDUTILITYANTIRANDBOT (their EUs computed from their perspective,
# logistic-weighted into a play distribution). See ./_util/_utilitybrain.py;
# composed with a TrackedPlayer.
import sys
from functools import partial
from pathlib import Path

_root = str(Path(__file__).resolve().parent / "_util")
if _root not in sys.path:
    sys.path.insert(0, _root)

from _tracking import TrackedPlayer
from _utilitybrain import make_utility_decide, pick_logistic, weighted_utility_opp_model

bot = partial(TrackedPlayer, make_utility_decide(pick_logistic, weighted_utility_opp_model))
# highness: 0.423
