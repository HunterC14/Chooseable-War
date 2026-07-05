# 2-14, 2-10 + JQKA

class maxbot:
    def __init__(self):
        self.hand: list[int] = []
        self.my_id = None

    def start_game(self, id: int):
        self.my_id = id # the id which this bot is referenced as in the cards dict

    def set_hand(self, toset: list[int]):
        self.hand = toset

    def choose_card(self):
        return max(self.hand) # no need to remove it; set_hand is called after every card use

    def war(self, cards: dict[int, int], ofnum: int, bounty: list[int]):
        ordered = sorted(self.hand, reverse=True)
        return (ordered[0], *ordered[-3:]) # play biggest, discard the 3 weakest cards

bot = maxbot
# highness: 1.000
