import random
import numpy as np

class FixedRandom:
    """This class is used to fix the random seed for both the random and numpy libraries."""
    instance: random.Random = None  # type: ignore

    def __init__(self, random_seed: int = 0, numpy_seed: int = 0):
        self.set_random_seed(random_seed)
        self.set_numpy_seed(numpy_seed)

    @classmethod
    def set_random_seed(cls, seed: int):
        if cls.instance is None:
            cls.instance = random.Random()
        cls.instance.seed(seed)

    @staticmethod
    def set_numpy_seed(seed: int):
        np.random.seed(seed)
        np.random.default_rng(seed)