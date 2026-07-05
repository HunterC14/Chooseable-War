# SquareLowBot: lowbot variant with power-law weighting (n + 1 - r)^2 —
# squares the linear ramp, concentrating much harder on the cheapest winning
# cards (towards antiminbot as the exponent grows). See ./_util/_lowbot.py;
# composed with a TrackedPlayer (./_util/_tracking.py).
import sys
from functools import partial
from pathlib import Path

_root = str(Path(__file__).resolve().parent / "_util")
if _root not in sys.path:
    sys.path.insert(0, _root)

from _lowbot import make_lowbot_decide, shape_square
from _tracking import TrackedPlayer

bot = partial(TrackedPlayer, make_lowbot_decide(shape_square))
# highness: 0.392
