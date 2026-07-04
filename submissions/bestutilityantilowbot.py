# BestUtilityAntiLowBot (formerly utilityantilowbot): plays the card with the
# highest expected utility, modeling the opponent as LOWBOT (play distribution
# from ../_lowbot.py). See ../_utilitybrain.py; composed with a TrackedPlayer.
import sys
from pathlib import Path

_root = str(Path(__file__).resolve().parent.parent)
if _root not in sys.path:
    sys.path.insert(0, _root)

from _lowbot import lowbot_opp_model
from _tracking import bot_class
from _utilitybrain import make_utility_decide, pick_max

bot = bot_class(__name__, make_utility_decide(pick_max, lowbot_opp_model))
