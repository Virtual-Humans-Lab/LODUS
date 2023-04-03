import random

import numpy as np


class FixedRandom():
    instance:random.Random = None # type: ignore

    def __init__(self, seed = None, numpy_seed: int = 0):
        FixedRandom.instance = random.Random()
        if seed is not None:
            FixedRandom.instance.seed(seed)
        np.random.seed(seed=numpy_seed)

