# MarginLowBot: lowbot variant weighted by margin instead of rank —
# exp(-(card - opp_min)) penalizes wasted VALUE over the opponent's minimum,
# so it behaves differently from rank-based shapes when the remaining cards
# are lumpy (e.g. a gap between your 5 and your king). See
# ./_util/_lowbot.py; composed with a TrackedPlayer (./_util/_tracking.py).
import sys
from functools import partial
from pathlib import Path

_root = str(Path(__file__).resolve().parent / "_util")
if _root not in sys.path:
    sys.path.insert(0, _root)

from _lowbot import make_lowbot_decide, shape_margin
from _tracking import TrackedPlayer

bot = partial(TrackedPlayer, make_lowbot_decide(shape_margin))
# highness: 0.315
