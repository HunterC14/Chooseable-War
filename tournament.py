import random
import importlib.util
# from shutil import rmtree
from pathlib import Path
from time import time
from sys import stderr
from argparse import ArgumentParser
from copy import copy

"""
Logging info:
t#x is the tournament id, how the bot is referenced outside of any individual game.
g#x is the game id, identical to the tourney id, and this is how the bot is referenced inside a game.
r#x is the round number. This increases each round.

Many times a bot's name will be combined with their game id but the game id is always shown
and is the most foolproof way to identify a bot inside any particular game.

How to play Chooseable War:
Every player starts with floor(52 / p) cards where p is the # of players. The other cards aren't used.
("Player" refers to whoever is playing, which in this case will be bots.)
There are no turns. Per “round”, each player will secretly pick a card to play. The player with the highest card will win all the cards except their own.
2 beats ace, but ace beats everything else. This means that if there is both a 2 and an ace, the 2 will win the ace,
 and extra bounties (which is discussed later), and the ace will win all other cards.
If multiple players share the winning card, there is a “war”. This means that the players involved in the war pick 1 card to play, and 3 cards to add to the bounty.
 This is almost the same as regular round structure. The only difference is that not all players are included, and the extra bounty,
 which is every card that was played (in the current round). If you win, you do not get any cards you played.
If there are multiple 2s and multiple aces, there will just be 2 wars. It is no different.
 The 2s are warring over extra bounties and the aces and the aces are warring over the other cards.
If you have less than 4 cards and are engaged in a war, you are immediately eliminated and your cards are added to the bounty.
If you ever cannot play (you have 0 cards), you are eliminated.
If multiple players are eliminated in 1 war and there are no players left, those eliminated players get a shared win.
 (p players each get 1/p score each)
Last player(s) standing win. They gain 1 score.
"""

submissions_dir = Path(__file__).parent / "submissions"

parser = ArgumentParser(
    prog="tournament.py",
    description="Runs a Chooseable War tourney with bots"
)

parser.add_argument("-v", "--verbose", action="store_true")
parser.add_argument("-c", "--count", "--games", type=int, default=30_000)
parser.add_argument("-b","--bots", nargs="+", default=[])
parser.add_argument("-p", "--progress", action="store_true")
args = parser.parse_args()
DEBUG = args.verbose
round_count = args.count
playing_bots = args.bots
show_progress = args.progress
if playing_bots == []:
    playing_bots = [path for path in submissions_dir.iterdir() if path.name[0].isalnum() and path.suffix == ".py"]
else:
    custom_bots = playing_bots[:]
    playing_bots = [submissions_dir / (name+".py") for name in custom_bots]

# try:
#     rmtree(submissions_dir / "__pycache__")
#     if DEBUG:
#         print("Removed pycache")
# except FileNotFoundError:
#     if DEBUG:
#         print("No pycache to remove")
# del rmtree
submissions = []
for path in playing_bots:
    print(f"Importing {path}")
    module_name = path.stem
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        print(f"Failed import {module_name}", file=stderr)
        continue
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    bot = module.bot()
    submissions.append(bot)

random.seed()
sub_count = len(submissions)

def war(cards: dict[int, int], ofnum: int, bounty: list[int], hands: list[list[int]], played: dict[int, list[int]] = {}):
    warring: list[int] = [k for k, v in cards.items() if v == ofnum]
    if DEBUG:
        print(f"war between {warring} with cards {cards}, {ofnum}, and bounty {bounty}")
    submitted_cards: dict[int, tuple[int, int, int, int]] = {} # first int is played card, other 3 are the sacrifice cards
    for sub in warring[:]:
        if len(hands[sub]) < 4:
            bounty.extend(hands[sub])
            if DEBUG:
                print(f"Player g#{sub} eliminated in war. Cards: {hands[sub]}")
            hands[sub] = []
            submissions[sub].set_hand([])
            warring.remove(sub)
    if len(warring) == 0:
        if DEBUG:
            print(f"All players eliminated in war. Card dict: {cards}")
        return
    if len(warring) == 1:
        won = warring[0]
        if DEBUG:
            print(f"One player g#{won} left in war. They won total bounty of {bounty}")
        for card in played[won]:
            bounty.remove(card)
        if DEBUG:
            print(f"Real winnings {bounty}")
        hands[won].extend(bounty)
        if DEBUG:
            print(f"New hand: {hands[won]}")
        return
    for sub in warring:
        chose = submissions[sub].war(copy(cards), ofnum, copy(bounty))
        assert isinstance(chose, tuple)
        assert len(chose) == 4
        for card in chose:
            assert isinstance(card, int)
            hands[sub].remove(card)
        submitted_cards[sub] = chose
        submissions[sub].set_hand(copy(hands[sub]))
    new_cards = {}
    new_bounty = bounty
    for sub, chose in submitted_cards.items():
        new_cards[sub] = chose[0]
        new_bounty.extend(chose[1:])
    resolve_matches(new_cards, hands, new_bounty, played)

def resolve_matches(card_dict: dict[int, int], hands: list[list[int]],
                    extra_bounty: list[int] = [], played: dict[int,list[int]] | None = None):
    if played is None:
        played = {sub:[card] for sub, card in card_dict.items()}
    cards = list(card_dict.values())
    if 14 in cards and 2 in cards:
        if cards.count(14) > 1:
            war(card_dict, 14, [c for c in cards if c != 2]+extra_bounty, hands, played)
        else:
            ace = next((k for k, v in card_dict.items() if v == 14))
            winnings = [c for c in cards if c != 2] # extra bounty goes to 2(s)
            hands[ace].extend(winnings)
            submissions[ace].set_hand(copy(hands[ace]))
            if DEBUG:
                print(f"Ace card was single g#{ace} and won most of the cards. Winnings: {winnings}")
        if cards.count(2) > 1:
            war(card_dict, 2, [14]*cards.count(14)+[2]*cards.count(2)+extra_bounty, hands, played)
        else:
            two = next((k for k, v in card_dict.items() if v == 2))
            winnings = [14]+extra_bounty
            hands[two].extend(winnings)
            submissions[two].set_hand(copy(hands[two]))
            if DEBUG:
                print(f"2 card was single g#{two} and won the ace(s) and bount(y|ies) from previous round(s). Winnings: {winnings}")
    else:
        winner = max(cards)
        bounty = cards+extra_bounty
        if cards.count(winner) > 1:
            war(card_dict, winner, bounty, hands, played)
        else:
            winsub = next((k for k, v in card_dict.items() if v == winner))
            for card in played[winsub]:
                bounty.remove(card)
            hands[winsub].extend(bounty)
            if DEBUG:
                print(f"g#{winsub} won the bounty of {bounty} with card {winner}")
    for i, bot in enumerate(submissions):
        bot.set_hand(copy(hands[i]))

def game(deal_count: int) -> dict[int, float]:
    assert deal_count * sub_count <= 13 * 4
    deck = [i for i in range(2,15)]*4 # 2-10 + JQKA
    random.shuffle(deck)

    for i, sub in enumerate(submissions):
        sub.set_id(i)

    active_players = list(range(sub_count))
    
    hands: list[list[int]] = []
    for i in active_players:
        bot = submissions[i]
        if DEBUG:
            print(f"{bot.__class__.__name__} is g#{i}")
        hand = deck[:deal_count]
        hands.append(hand)
        bot.set_hand(copy(hand))
        del deck[:deal_count]

    while True:
        submitted_cards: dict[int, int] = {}
        eliminated: list[int] = []
        for i in active_players:
            if len(hands[i]) == 0:
                if DEBUG:
                    print(f"{submissions[i].__class__.__name__} eliminated from game")
                eliminated.append(i)
        for i in eliminated:
            active_players.remove(i)
        if len(active_players) == 1:
            if DEBUG:
                print(f"{submissions[active_players[0]].__class__.__name__} won the game.")
            return {active_players[0]: 1.0}
        if len(active_players) == 0:
            if DEBUG:
                print(f"Win split between g#{', g#'.join([str(i) for i in eliminated])}")
            return {i: 1/len(eliminated) for i in eliminated}
        for i in active_players:
            bot = submissions[i]
            name = bot.__class__.__name__
            card = bot.choose_card()
            assert isinstance(card, int), f"{name} g#{i} didn't submit an int"
            assert card in hands[i], f"{name} g#{i} didn't submitted a card that they don't have"
            submitted_cards[i] = card
            hands[i].remove(card)
            bot.set_hand(copy(hands[i]))
            if DEBUG:
                print(f"{name} g#{i} plays {card}")
        resolve_matches(submitted_cards, hands)

assert __name__ == "__main__"

for i, bot in enumerate(submissions):
    print(f"{bot.__class__.__name__} is t#{i}")

def overview_print():
    for tid, score in points.items():
        name = submissions[tid].__class__.__name__
        print(f"{name} t#{tid} has {score:,.3f} points ({score/(round_num+1)*100:.2f}%)", file=stderr)

points: dict[int, float] = {i: 0.0 for i in range(sub_count)}
start_time = time()
round_time = 0
last_shown = start_time
if show_progress:
    print("\n"*sub_count,file=stderr)
round_num = 0
try:
    for round_num in range(round_count):
        if DEBUG:
            print(f"Initiating r#{round_num} (0-indexed)")
        round_start = time()
        scores = game(13 * 4 // sub_count)
        round_time += time()-round_start
        if DEBUG:
            print()
        for gid, incscore in scores.items():
            points[gid] += incscore
        if show_progress:
            if time() - last_shown > 0.01:
                last_shown = time()
                print("\x1b[A"*(sub_count+1),end="",file=stderr)
                print(f"Working round: {round_num+1}", file=stderr)
                overview_print()
                    
except KeyboardInterrupt:
    print(f"\rRan for {time()-start_time:,.1f} sec")
    round_num -= 1
total_time = time() - start_time
rounds_done = round_num + 1
print("Overview:", file=stderr)
print(f"{rounds_done}/{round_count:,} rounds", file=stderr)
overview_print()
print(f"Avg. game time: {round_time/rounds_done*1_000_000:.2f} \u03bcs", file=stderr)
print(f"Total elapsed time: {total_time:,.2f} sec", file=stderr)
print(f"Avg. time per round: {total_time/rounds_done*1_000_000:.2f} \u03bcs", file=stderr)