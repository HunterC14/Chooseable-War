import random

class example:
    hand: list[int] = []
    my_id = None

    # 2-14, 2-10 + JQKA

    def set_id(self, id: int):
        self.my_id = id # the id which this submission is referenced as in the cards dict
        # print(f"{__name__} g#{my_id}")

    def set_hand(self, toset: list[int]):
        self.hand = toset
        # print(f"Set hand to {hand} ({__name__} g#{my_id})")

    def choose_card(self):
        card = random.choice(self.hand)
        # print(f"Choosing card {card} ({__name__} g#{my_id})")
        return card # don't need to remove it from the hand because set_hand is called after every card use

    def war(self, cards: dict[int, int], ofnum: int, bounty: list[int]):
        # print(f"Bounty: {bounty} cont. ({__name__} g#{my_id})")
        # print(f"Warring with number {ofnum} cont.")
        # print(f"All cards: {cards} cont.")
        random.shuffle(self.hand)
        # print(f"Choosing cards for war: {hand[:4]} end")
        return tuple(self.hand[:4]) # first int is the played card, the one that is actually compared.
                            # other 3 are the "bounty" cards which don't affect the outcome but lets the winner win more cards.

bot=example