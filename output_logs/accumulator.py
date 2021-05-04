import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import sys
import plotly.graph_objects as go
import numpy as np

path = sys.argv[1]


df = pd.read_csv(path, sep=';')


# df_first = df.iloc[0:94]
# print(df_first)
# df_first = pd.concat([df_first]* 1300 , ignore_index=True)

# df['f0'] = df_first['Total']
# df['nf0'] = df_first['Locals']

# print(len(df_first))
# print(len(df))
# df['TotalIsolation'] = df['Total'] / df['f0']
# df['LocalsIsolation'] = df['Locals'] / df['nf0']

df = df[df["Hour"] == 8]


df.to_csv('filtered_8_hour.csv', sep=';')