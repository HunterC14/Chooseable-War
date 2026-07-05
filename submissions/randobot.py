import random

# 2-14, 2-10 + JQKA

class randobot:
    def __init__(self):
        self.hand: list[int] = []
        self.my_id = None

    def start_game(self, id: int):
        self.my_id = id # the id which this bot is referenced as in the cards dict

    def set_hand(self, toset: list[int]):
        self.hand = toset

    def choose_card(self):
        return random.choice(self.hand) # no need to remove it; set_hand is called after every card use

    def war(self, cards: dict[int, int], ofnum: int, bounty: list[int]):
        play = random.choice(self.hand)
        rest = sorted(self.hand)
        rest.remove(play)
        return (play, *rest[:3]) # first int is the played (compared) card;
                                 # the other 3 are the discarded 3 weakest cards, which
                                 # feed the bounty without affecting the outcome

bot = randobot
# highness: 0.494
