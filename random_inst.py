import random

import numpy as np


class FixedRandom():
    instance:random.Random = None # type: ignore

    def __init__(self, random_seed : int = 0, numpy_seed: int = 0):
        FixedRandom.instance = random.Random()
        if random_seed is not None:
            FixedRandom.instance.seed(random_seed)
        np.random.seed(seed=numpy_seed)
        np.random.default_rng(seed=numpy_seed)

