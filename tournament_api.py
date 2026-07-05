import random
import importlib.util
from pathlib import Path
from copy import copy
from typing import Protocol
from time import time

"""
Logging info:
t#x is the tournament id, how the bot is referenced outside of any individual game.
g#x is the game id, identical to the tourney id, and this is how the bot is referenced inside a game.
r#x is the game number. This increases each game.

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

class Bot_protocol(Protocol):
    def start_game(self, player_id: int) -> None: ...
    def set_hand(self, hand: list[int]) -> None: ...
    def choose_card(self) -> int: ...
    def war(self, cards: dict[int, int], ofnum: int, bounty: list[int]) -> tuple[int, int, int, int]: ...

submissions_dir = Path(__file__).parent / "submissions"

class Player(object):
    def __init__(self, bot: Bot_protocol, name: str):
        self.bot = bot
        self.id = -1
        self.hand = []
        self.name = name
        self.elapsed_time = 0
    def start_game(self, bot_id: int):
        self.id = bot_id
        before = time()
        self.bot.start_game(bot_id)
        self.elapsed_time += time() - before
    def set_hand(self, hand: list[int]):
        self.hand = hand
        self.update_hand()
    def update_hand(self):
        before = time()
        self.bot.set_hand(copy(self.hand))
        self.elapsed_time += time() - before
    def choose_card(self):
        before = time()
        chose = self.bot.choose_card()
        self.elapsed_time += time() - before
        return chose
    def war(self, cards: dict[int, int], ofnum: int, bounty: list[int]):
        before = time()
        chose = self.bot.war(copy(cards), ofnum, copy(bounty))
        self.elapsed_time += time() - before
        return chose

def import_bots(bot_names: list[str] | None = None):
    submissions: list[Player] = []
    if bot_names == None:
        playing_bots = [path for path in submissions_dir.iterdir() if path.name[0].isalnum() and path.suffix == ".py"]
    else:
        playing_bots = [submissions_dir / (name+".py") for name in bot_names]

    for path in playing_bots:
        # print(f"Importing {path}")
        module_name = path.stem
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Failed import {module_name}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        bot = module.bot()
        submissions.append(Player(bot, module_name))
    return submissions

random.seed()

def war(cards: dict[int, int], ofnum: int, bounty: list[int], players: list[Player],
        played: dict[int, list[int]] = {}, verbose: bool = False):
    warring: list[int] = [k for k, v in cards.items() if v == ofnum]
    if verbose:
        print(f"war between {warring} with cards {cards}, {ofnum}, and bounty {bounty}")
    submitted_cards: dict[int, tuple[int, int, int, int]] = {} # first int is played card, other 3 are the sacrifice cards
    for id in warring[:]:
        if len(players[id].hand) < 4:
            bounty.extend(players[id].hand)
            if verbose:
                print(f"Player g#{id} eliminated in war. Cards: {players[id].hand}")
            players[id].set_hand([])
            warring.remove(id)
    if len(warring) == 0:
        if verbose:
            print(f"All players eliminated in war. Card dict: {cards}")
        return
    if len(warring) == 1:
        won = warring[0]
        if verbose:
            print(f"One player g#{won} left in war. They won total bounty of {bounty}")
        for card in played[won]:
            bounty.remove(card)
        if verbose:
            print(f"Real winnings {bounty}")
        players[won].hand.extend(bounty)
        players[won].update_hand()
        if verbose:
            print(f"New hand: {players[won].hand}")
        return
    for id in warring:
        chose = players[id].war(cards, ofnum, bounty)
        assert isinstance(chose, tuple)
        assert len(chose) == 4
        for card in chose:
            assert isinstance(card, int)
            players[id].hand.remove(card)
        submitted_cards[id] = chose
        players[id].update_hand()
    new_cards = {}
    new_bounty = bounty
    for sub, chose in submitted_cards.items():
        new_cards[sub] = chose[0]
        new_bounty.extend(chose[1:])
    resolve_matches(new_cards, players, new_bounty, played, verbose=verbose)

def resolve_matches(card_dict: dict[int, int], players: list[Player],
                    extra_bounty: list[int] = [], played: dict[int,list[int]] | None = None,
                    verbose: bool = False):
    if played is None:
        played = {sub:[card] for sub, card in card_dict.items()}
    cards = list(card_dict.values())
    if 14 in cards and 2 in cards:
        if cards.count(14) > 1:
            war(card_dict, 14, [c for c in cards if c != 2]+extra_bounty, players, played, verbose=verbose)
        else:
            ace = next((k for k, v in card_dict.items() if v == 14))
            winnings = [c for c in cards if c != 2] # extra bounty goes to 2(s)
            players[ace].hand.extend(winnings)
            players[ace].update_hand()
            if verbose:
                print(f"Ace card was single g#{ace} and won most of the cards. Winnings: {winnings}")
        if cards.count(2) > 1:
            war(card_dict, 2, [14]*cards.count(14)+[2]*cards.count(2)+extra_bounty, players, played, verbose=verbose)
        else:
            two = next((k for k, v in card_dict.items() if v == 2))
            winnings = [14]+extra_bounty
            players[two].hand.extend(winnings)
            players[two].update_hand()
            if verbose:
                print(f"2 card was single g#{two} and won the ace(s) and bount(y|ies) from previous round(s). Winnings: {winnings}")
    else:
        winner = max(cards)
        bounty = cards+extra_bounty
        if cards.count(winner) > 1:
            war(card_dict, winner, bounty, players, played, verbose=verbose)
        else:
            winsub = next((k for k, v in card_dict.items() if v == winner))
            for card in played[winsub]:
                bounty.remove(card)
            players[winsub].hand.extend(bounty)
            players[winsub].update_hand()
            if verbose:
                print(f"g#{winsub} won the bounty of {bounty} with card {winner}")
    # for i, bot in enumerate(submissions):
    #     bot.set_hand(copy(hands[i]))

def game(deal_count: int, players: list[Player], verbose: bool = False) -> dict[int, float]:
    """
    :param: deal_count: # of cards each bot starts with
    """
    sub_count = len(players)
    assert deal_count * sub_count <= 13 * 4
    deck = [i for i in range(2,15)]*4 # 2-10 + JQKA
    random.shuffle(deck)

    for i, bot in enumerate(players):
        bot.start_game(i)

    active_players = copy(players)
    
    for bot in active_players:
        if verbose:
            print(f"{bot.name} is g#{bot.id}")
        hand = deck[:deal_count]
        bot.set_hand(copy(hand))
        del deck[:deal_count]

    while True:
        submitted_cards: dict[int, int] = {}
        eliminated: list[Player] = []
        for bot in active_players:
            if len(bot.hand) == 0:
                if verbose:
                    print(f"{bot.name} eliminated from game")
                eliminated.append(bot)
        for bot in eliminated:
            active_players.remove(bot)
        if len(active_players) == 1:
            if verbose:
                print(f"{active_players[0].name} won the game.")
            return {active_players[0].id: 1.0}
        if len(active_players) == 0:
            if verbose:
                print(f"Win split between g#{', g#'.join([str(i) for i in eliminated])}")
            return {bot.id: 1/len(eliminated) for bot in eliminated}
        for bot in active_players:
            name = bot.name
            card = bot.choose_card()
            assert isinstance(card, int), f"{name} g#{bot.id} didn't submit an int"
            assert card in bot.hand, f"{name} g#{bot.id} didn't submitted a card that they don't have"
            submitted_cards[bot.id] = card
            bot.hand.remove(card)
            bot.update_hand()
            if verbose:
                print(f"{name} g#{bot.id} plays {card}")
        resolve_matches(submitted_cards, players, verbose=verbose)