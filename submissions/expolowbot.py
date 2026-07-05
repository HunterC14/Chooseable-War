# ExpoLowBot: lowbot variant with exponential (geometric) decay weighting
# 0.7^rank — prefers the cheapest winner by a constant ratio per rank step,
# so high cards get vanishingly small weight regardless of hand size. See
# ./_util/_lowbot.py; composed with a TrackedPlayer (./_util/_tracking.py).
import sys
from functools import partial
from pathlib import Path

_root = str(Path(__file__).resolve().parent / "_util")
if _root not in sys.path:
    sys.path.insert(0, _root)

from _lowbot import make_lowbot_decide, shape_expo
from _tracking import TrackedPlayer

bot = partial(TrackedPlayer, make_lowbot_decide(shape_expo))
# highness: 0.339
