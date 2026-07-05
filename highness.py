#!/usr/bin/env python3
"""Measure a bot's empirical propensity to play high cards.

Plays the bot against itself under the same rules as tournament.py and scores
every choose_card() pick by its position within the current hand:

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

import importlib.util
import random
import re
import sys
from argparse import ArgumentParser
from copy import copy
from pathlib import Path

HERE = Path(__file__).parent
SUBMISSIONS = HERE / "submissions"
COMMENT_RE = re.compile(r"^#\s*highness:\s*[0-9.]+[^\n]*\n?", re.MULTILINE)
MAX_ROUNDS = 5_000  # per game, in case a matchup stalls

submissions = []  # the two probe-wrapped players (module global, like tournament.py)


def load_bot(name: str):
    path = SUBMISSIONS / f"{name}.py"
    if not path.exists():
        sys.exit(f"no such bot: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        sys.exit(f"failed to import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.bot()


class Probe:
    """Wraps a bot for the engine, recording the highness of every
    choose_card() pick relative to the hand it was picked from."""

    def __init__(self, bot):
        self.bot = bot
        self.hand: list[int] = []
        self.picks: list[float] = []

    def set_id(self, i: int):
        self.bot.set_id(i)

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


# ---- game engine: copied from tournament.py with debug output removed ------

def war(cards, ofnum, bounty, hands, played={}):
    warring = [k for k, v in cards.items() if v == ofnum]
    submitted_cards = {}
    for sub in warring[:]:
        if len(hands[sub]) < 4:
            bounty.extend(hands[sub])
            hands[sub] = []
            submissions[sub].set_hand([])
            warring.remove(sub)
    if len(warring) == 0:
        return
    if len(warring) == 1:
        won = warring[0]
        for card in played[won]:
            bounty.remove(card)
        hands[won].extend(bounty)
        return
    for sub in warring:
        chose = submissions[sub].war(copy(cards), ofnum, copy(bounty))
        for card in chose:
            hands[sub].remove(card)
        submitted_cards[sub] = chose
        submissions[sub].set_hand(copy(hands[sub]))
    new_cards = {}
    new_bounty = bounty
    for sub, chose in submitted_cards.items():
        new_cards[sub] = chose[0]
        new_bounty.extend(chose[1:])
    resolve_matches(new_cards, hands, new_bounty, played)


def resolve_matches(card_dict, hands, extra_bounty=[], played=None):
    if played is None:
        played = {sub: [card] for sub, card in card_dict.items()}
    cards = list(card_dict.values())
    if 14 in cards and 2 in cards:
        if cards.count(14) > 1:
            war(card_dict, 14, [c for c in cards if c != 2] + extra_bounty, hands, played)
        else:
            ace = next((k for k, v in card_dict.items() if v == 14))
            winnings = [c for c in cards if c != 2]
            hands[ace].extend(winnings)
            submissions[ace].set_hand(copy(hands[ace]))
        if cards.count(2) > 1:
            war(card_dict, 2, [14] * cards.count(14) + [2] * cards.count(2) + extra_bounty, hands, played)
        else:
            two = next((k for k, v in card_dict.items() if v == 2))
            hands[two].extend([14] + extra_bounty)
            submissions[two].set_hand(copy(hands[two]))
    else:
        winner = max(cards)
        bounty = cards + extra_bounty
        if cards.count(winner) > 1:
            war(card_dict, winner, bounty, hands, played)
        else:
            winsub = next((k for k, v in card_dict.items() if v == winner))
            for card in played[winsub]:
                bounty.remove(card)
            hands[winsub].extend(bounty)
    for i, bot in enumerate(submissions):
        bot.set_hand(copy(hands[i]))


def game(deal_count: int):
    deck = [i for i in range(2, 15)] * 4
    random.shuffle(deck)
    for i, sub in enumerate(submissions):
        sub.set_id(i)
    active_players = list(range(len(submissions)))
    hands = []
    for i in active_players:
        hand = deck[:deal_count]
        hands.append(hand)
        submissions[i].set_hand(copy(hand))
        del deck[:deal_count]
    for _ in range(MAX_ROUNDS):
        submitted_cards = {}
        eliminated = [i for i in active_players if len(hands[i]) == 0]
        for i in eliminated:
            active_players.remove(i)
        if len(active_players) <= 1:
            return
        for i in active_players:
            card = submissions[i].choose_card()
            submitted_cards[i] = card
            hands[i].remove(card)
            submissions[i].set_hand(copy(hands[i]))
        resolve_matches(submitted_cards, hands)


# -----------------------------------------------------------------------------

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

    global submissions
    submissions = [Probe(load_bot(args.bot)) for _ in range(2)]
    for _ in range(args.count):
        game(52 // len(submissions))
    picks = [p for probe in submissions for p in probe.picks]
    if not picks:
        sys.exit("no picks recorded")
    score = sum(picks) / len(picks)
    print(f"{score:.3f}")
    if args.write:
        write_comment(SUBMISSIONS / f"{args.bot}.py", score)


if __name__ == "__main__":
    main()
