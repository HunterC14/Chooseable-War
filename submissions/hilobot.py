# HiLoBot: bimodal play — 50% of the time a random card from the bottom
# 10%ile of its hand, 50% of the time from the top 10%ile (percentile pools
# always hold at least one card). Wars sacrifice the 3 weakest cards and pick
# the compare card by the same hi/lo rule from the rest.
import random

# 2-14, 2-10 + JQKA


class hilobot:
    def __init__(self):
        self.hand: list[int] = []
        self.my_id = None

    def start_game(self, id: int):
        self.my_id = id  # the id which this bot is referenced as in the cards dict

    def set_hand(self, toset: list[int]):
        self.hand = toset

    def _hilo_pick(self, cards: list[int]) -> int:
        ordered = sorted(cards)
        k = max(1, -(-len(ordered) // 10))  # ceil(10%ile), at least 1 card
        pool = ordered[:k] if random.random() < 0.5 else ordered[-k:]
        return random.choice(pool)

    def choose_card(self):
        return self._hilo_pick(self.hand)  # no need to remove it; set_hand is called after every card use

    def war(self, cards: dict[int, int], ofnum: int, bounty: list[int]):
        ordered = sorted(self.hand)
        sacrifice = ordered[:3]  # always sacrifice the 3 weakest cards
        play = self._hilo_pick(ordered[3:])
        return (play, *sacrifice)


bot = hilobot
# highness: 0.500
