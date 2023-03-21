import pandas as pd
import plotly.express as px
from plotly.subplots import make_subplots
import sys
import plotly.graph_objects as go

path = sys.argv[1]


fig = make_subplots(rows= 2, cols=1,
subplot_titles = ("Susc over Time", "Accumulated Infections over Time"))

df = pd.read_csv(path, sep=';', index_col='Frame')

filter_operation = df['ID'] == 'Centro\\home' 


filtered_df = df[filter_operation] 

susc = filtered_df['S']
days = range(31)


fig = px.line(filtered_df,   y=['S','I','R','aS','aI','aR','nS','nI','nR'], title="stuff", color_discrete_map={
                 'I': 'maroon',
                 'nI': 'red',
                 'aI':'plum',
                 'S': 'chartreuse',
                 'nS': 'darkgreen',
                 'aS': 'darkseagreen',
                 'aR':'royalblue',
                 'R': 'blue',
                 'nR':'darkturquoise'
             })


# acum = df['Infected'] + df['Removed']
# df['Accumulated'] = acum



# fig.add_trace(px.line(df, x = range(4800), y = 'Accumulated', title='Accumulated').data[0], row=2, col=1)





# fig.update_yaxes(title_text="Daily infections for that 24 period", row=1, col=1)
# fig.update_yaxes(title_text="Total infections", row=2, col=1)

# fig.update_xaxes(title_text="Days since first infection", row=1, col=1)
# fig.update_xaxes(title_text="Days since first infection", row=2, col=1)


# fig.update_layout(
# title = "Infection Data",
# font=dict(
#     family="Courier New, monospace",
#     size=22,
#     color="RebeccaPurple"
# )
# )

fig.show()