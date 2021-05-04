import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import sys
import plotly.graph_objects as go

path = sys.argv[1]


fig = make_subplots(rows= 2, cols=1,
subplot_titles = ("Daily Infections over Time", "Accumulated Infections over Time"))

df = pd.read_csv(path, sep=';', index_col='Frame')


slices = df.iloc[::24, :]
slices = slices - slices.shift(-1)

susc = slices['Susceptible']
days = range(200)

fig.add_trace(px.bar(x= days,  y=susc, title='Susceptible').data[0], row=1, col=1)


acum = df['Infected'] + df['Removed']
df['Accumulated'] = acum

df = df.iloc[::24, :]

fig.add_trace(px.line(df, x = range(200), y = 'Accumulated', title='Accumulated').data[0], row=2, col=1)





fig.update_yaxes(title_text="Daily infections for that 24 period", row=1, col=1)
fig.update_yaxes(title_text="Total infections", row=2, col=1)

fig.update_xaxes(title_text="Days since 50th infection", row=1, col=1)
fig.update_xaxes(title_text="Days since 50th infection", row=2, col=1)


fig.update_layout(
title = "Infection Data",
font=dict(
    family="Courier New, monospace",
    size=22,
    color="RebeccaPurple"
)
)

fig.show()