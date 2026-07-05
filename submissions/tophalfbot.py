import random

# 2-14, 2-10 + JQKA

class tophalfbot:
    def __init__(self):
        self.hand: list[int] = []
        self.my_id = None

    def start_game(self, id: int):
        self.my_id = id # the id which this bot is referenced as in the cards dict

    def set_hand(self, toset: list[int]):
        self.hand = toset

    def _top_half_pick(self):
        ordered = sorted(self.hand, reverse=True)
        return random.choice(ordered[:max(1, len(ordered) // 2)])

    def choose_card(self):
        return self._top_half_pick() # no need to remove it; set_hand is called after every card use

    def war(self, cards: dict[int, int], ofnum: int, bounty: list[int]):
        play = self._top_half_pick()
        rest = sorted(self.hand)
        rest.remove(play)
        return (play, *rest[:3]) # play from top half, discard the 3 weakest cards

bot = tophalfbot
# highness: 0.788
