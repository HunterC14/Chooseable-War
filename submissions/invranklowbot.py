# InvRankLowBot: lowbot variant with inverse-rank weighting 1/r — heavier
# low-preference than linear but with a fat tail: occasionally plays a high
# card, making it less exploitable by opponents that assume near-deterministic
# cheap wins. See ./_util/_lowbot.py; composed with a TrackedPlayer
# (./_util/_tracking.py).
import sys
from functools import partial
from pathlib import Path

_root = str(Path(__file__).resolve().parent / "_util")
if _root not in sys.path:
    sys.path.insert(0, _root)

from _lowbot import make_lowbot_decide, shape_invrank
from _tracking import TrackedPlayer

bot = partial(TrackedPlayer, make_lowbot_decide(shape_invrank))
# highness: 0.522
