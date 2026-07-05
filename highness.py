#!/usr/bin/env python3
"""Measure a bot's empirical propensity to play high cards.

Plays the bot against itself using the real engine (tournament_api.py) and
scores every choose_card() pick by its position within the current hand:

    (# cards strictly below the pick) / (# strictly below + # strictly above)

(picks with no strictly-lower and no strictly-higher card are skipped). The
printed result is the average over all picks: 0.0 = always plays its lowest
card (minbot), 1.0 = always its highest (maxbot), ~0.5 = uniform random.
War compare-cards are not scored, only regular round picks.

The number is meant to live in the bot file as a standardized comment that
grid.py reads to order its rows/columns:

    # highness: 0.503

Usage:
  python3 highness.py minbot            # print the score
  python3 highness.py minbot -c 2000    # more games
  python3 highness.py minbot --write    # also insert/update the comment
"""

import re
import sys
from argparse import ArgumentParser
from pathlib import Path

import tournament_api as api

HERE = Path(__file__).parent
SUBMISSIONS = HERE / "submissions"
COMMENT_RE = re.compile(r"^#\s*highness:\s*[0-9.]+[^\n]*\n?", re.MULTILINE)


class Probe:
    """Wraps a bot (Bot_protocol), recording the highness of every
    choose_card() pick relative to the hand it was picked from."""

    def __init__(self, bot):
        self.bot = bot
        self.hand: list[int] = []
        self.picks: list[float] = []

    def start_game(self, player_id: int):
        self.bot.start_game(player_id)

    def set_hand(self, toset: list[int]):
        self.hand = list(toset)
        self.bot.set_hand(toset)

    def choose_card(self) -> int:
        card = self.bot.choose_card()
        below = sum(1 for c in self.hand if c < card)
        above = sum(1 for c in self.hand if c > card)
        if below + above:
            self.picks.append(below / (below + above))
        return card

    def war(self, cards, ofnum, bounty):
        return self.bot.war(cards, ofnum, bounty)


def probe_players(name: str, seats: int = 2) -> list:
    """Two independent instances of the bot (like engine self-play), each
    wrapped in a Probe."""
    players = []
    for _ in range(seats):
        try:
            [player] = api.import_bots([name])
        except (FileNotFoundError, ImportError) as e:
            sys.exit(f"cannot load bot {name!r}: {e}")
        player.bot = Probe(player.bot)
        players.append(player)
    return players


def write_comment(path: Path, score: float):
    text = path.read_text()
    line = f"# highness: {score:.3f}\n"
    if COMMENT_RE.search(text):
        text = COMMENT_RE.sub(line, text, count=1)
    else:
        text = text.rstrip("\n") + "\n" + line
    path.write_text(text)


def main():
    parser = ArgumentParser(description="Measure a bot's propensity to play "
                            "high cards (0.0 = lowest, 1.0 = highest).")
    parser.add_argument("bot", help="bot name (file in submissions/)")
    parser.add_argument("-c", "--count", type=int, default=1_000,
                        help="self-play games to run (default 1,000)")
    parser.add_argument("--write", action="store_true",
                        help="insert/update the '# highness:' comment in the "
                             "bot file")
    args = parser.parse_args()

    players = probe_players(args.bot)
    for _ in range(args.count):
        api.game(13 * 4 // len(players), players)
    picks = [p for player in players for p in player.bot.picks]
    if not picks:
        sys.exit("no picks recorded")
    score = sum(picks) / len(picks)
    print(f"{score:.3f}")
    if args.write:
        write_comment(SUBMISSIONS / f"{args.bot}.py", score)


if __name__ == "__main__":
    main()
