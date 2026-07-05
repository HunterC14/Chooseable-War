import random
import importlib.util
from pathlib import Path
from copy import copy
from typing import Protocol

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

class Bot_protocol(Protocol):
    def set_id(self, player_id: int) -> None: ...
    def set_hand(self, hand: list[int]) -> None: ...
    def choose_card(self) -> int: ...
    def war(self, cards: dict[int, int], ofnum: int, bounty: list[int]) -> tuple[int, int, int, int]: ...

submissions_dir = Path(__file__).parent / "submissions"

class Player(object):
    def __init__(self, bot: Bot_protocol, name: str):
        self.bot = bot
        self.name = name
        self.set_id = bot.set_id
        self.set_hand = bot.set_hand
        self.choose_card = bot.choose_card
        self.war = bot.war

submissions: list[Player] = []
def import_bots(bot_names: list[str] | None = None):
    global submissions
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

random.seed()

def war(cards: dict[int, int], ofnum: int, bounty: list[int], hands: list[list[int]],
        played: dict[int, list[int]] = {}, verbose: bool = False):
    warring: list[int] = [k for k, v in cards.items() if v == ofnum]
    if verbose:
        print(f"war between {warring} with cards {cards}, {ofnum}, and bounty {bounty}")
    submitted_cards: dict[int, tuple[int, int, int, int]] = {} # first int is played card, other 3 are the sacrifice cards
    for sub in warring[:]:
        if len(hands[sub]) < 4:
            bounty.extend(hands[sub])
            if verbose:
                print(f"Player g#{sub} eliminated in war. Cards: {hands[sub]}")
            hands[sub] = []
            submissions[sub].set_hand([])
            warring.remove(sub)
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
        hands[won].extend(bounty)
        if verbose:
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
    resolve_matches(new_cards, hands, new_bounty, played, verbose=verbose)

def resolve_matches(card_dict: dict[int, int], hands: list[list[int]],
                    extra_bounty: list[int] = [], played: dict[int,list[int]] | None = None,
                    verbose: bool = False):
    if played is None:
        played = {sub:[card] for sub, card in card_dict.items()}
    cards = list(card_dict.values())
    if 14 in cards and 2 in cards:
        if cards.count(14) > 1:
            war(card_dict, 14, [c for c in cards if c != 2]+extra_bounty, hands, played, verbose=verbose)
        else:
            ace = next((k for k, v in card_dict.items() if v == 14))
            winnings = [c for c in cards if c != 2] # extra bounty goes to 2(s)
            hands[ace].extend(winnings)
            submissions[ace].set_hand(copy(hands[ace]))
            if verbose:
                print(f"Ace card was single g#{ace} and won most of the cards. Winnings: {winnings}")
        if cards.count(2) > 1:
            war(card_dict, 2, [14]*cards.count(14)+[2]*cards.count(2)+extra_bounty, hands, played, verbose=verbose)
        else:
            two = next((k for k, v in card_dict.items() if v == 2))
            winnings = [14]+extra_bounty
            hands[two].extend(winnings)
            submissions[two].set_hand(copy(hands[two]))
            if verbose:
                print(f"2 card was single g#{two} and won the ace(s) and bount(y|ies) from previous round(s). Winnings: {winnings}")
    else:
        winner = max(cards)
        bounty = cards+extra_bounty
        if cards.count(winner) > 1:
            war(card_dict, winner, bounty, hands, played, verbose=verbose)
        else:
            winsub = next((k for k, v in card_dict.items() if v == winner))
            for card in played[winsub]:
                bounty.remove(card)
            hands[winsub].extend(bounty)
            if verbose:
                print(f"g#{winsub} won the bounty of {bounty} with card {winner}")
    for i, bot in enumerate(submissions):
        bot.set_hand(copy(hands[i]))

def game(deal_count: int, players_id: list[int], verbose: bool = False) -> dict[int, float]:
    """
    :param: deal_count: # of cards each bot starts with
    """
    sub_count = len(players_id)
    assert deal_count * sub_count <= 13 * 4
    deck = [i for i in range(2,15)]*4 # 2-10 + JQKA
    random.shuffle(deck)

    players: list[Player] = []
    for id in players_id:
        players.append(submissions[id])

    for i, bot in enumerate(players):
        bot.set_id(i)

    active_players = copy(players_id)
    
    hands: list[list[int]] = []
    for i in active_players:
        bot = players[i]
        if verbose:
            print(f"{players[i].name} is g#{i}")
        hand = deck[:deal_count]
        hands.append(hand)
        bot.set_hand(copy(hand))
        del deck[:deal_count]

    while True:
        submitted_cards: dict[int, int] = {}
        eliminated: list[int] = []
        for i in active_players:
            if len(hands[i]) == 0:
                if verbose:
                    print(f"{players[i].name} eliminated from game")
                eliminated.append(i)
        for i in eliminated:
            active_players.remove(i)
        if len(active_players) == 1:
            if verbose:
                print(f"{players[active_players[0]].name} won the game.")
            return {active_players[0]: 1.0}
        if len(active_players) == 0:
            if verbose:
                print(f"Win split between g#{', g#'.join([str(i) for i in eliminated])}")
            return {i: 1/len(eliminated) for i in eliminated}
        for i in active_players:
            bot = submissions[i]
            name = bot.name
            card = bot.choose_card()
            assert isinstance(card, int), f"{name} g#{i} didn't submit an int"
            assert card in hands[i], f"{name} g#{i} didn't submitted a card that they don't have"
            submitted_cards[i] = card
            hands[i].remove(card)
            bot.set_hand(copy(hands[i]))
            if verbose:
                print(f"{name} g#{i} plays {card}")
        resolve_matches(submitted_cards, hands, verbose=verbose)