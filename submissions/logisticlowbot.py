# LogisticLowBot: lowbot variant with a logistic cutoff at the median rank —
# roughly uniform among the cheap winning cards, near-zero weight for the top
# half: play any cheap winner, actively hoard the big cards. See
# ./_util/_lowbot.py; composed with a TrackedPlayer (./_util/_tracking.py).
import sys
from functools import partial
from pathlib import Path

_root = str(Path(__file__).resolve().parent / "_util")
if _root not in sys.path:
    sys.path.insert(0, _root)

from _lowbot import make_lowbot_decide, shape_logistic
from _tracking import TrackedPlayer

bot = partial(TrackedPlayer, make_lowbot_decide(shape_logistic))
# highness: 0.414
