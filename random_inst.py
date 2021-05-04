import random


class FixedRandom():
    instance = None

    def __init__(self, _seed = None):
        FixedRandom.instance = random.Random()
        if _seed is not None:
            FixedRandom.instance.seed(_seed)

