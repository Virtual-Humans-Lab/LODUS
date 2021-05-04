import sys
import re
import numpy as np

import seaborn as sns
import matplotlib.pyplot as plt
import numpy as np


with open(sys.argv[1], 'r') as f:
    lines = f.readlines()

d = {}
key = ''
numbers = []

for line in lines:
    if re.match('[A-Za-z]+', line) is not None:
        key = line
        d[key] = []
    if re.match('[0-9]+', line) is not None:
        d[key] += [float(line)]
        numbers += [float(line)]


bins = np.arange(0,500, 10)
s = sns.histplot(numbers, bins=bins)
#figure = s.get_figure()
plt.savefig('distances-nodes.png', dpi=400)

