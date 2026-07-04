class minbot:
    hand: list[int] = []
    my_id = None

    def set_id(self, id: int):
        self.my_id = id
        # print(f"{__name__} g#{my_id}")

    def set_hand(self, toset: list[int]):
        self.hand = toset
        # print(f"Set hand to {hand} ({__name__} g#{my_id})")

    def choose_card(self):
        card = min(self.hand)
        # print(f"Choosing card {card} ({__name__} g#{my_id})")
        return card

    def war(self, cards: dict[int, int], ofnum: int, bounty: list[int]):
        # print(f"Bounty: {bounty} cont. ({__name__} g#{my_id})")
        # print(f"Warring with number {ofnum} cont.")
        # print(f"All cards: {cards} cont.")
        picks = tuple(sorted(self.hand)[:4][::-1])
        # print(f"Choosing cards for war: {picks} end")
        return picks
bot=minbot