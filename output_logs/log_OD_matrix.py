import pandas as pd

import sys

import seaborn as sns
import matplotlib.pyplot as plt

path = sys.argv[1]

name = sys.argv[2]

base_path = path.split('.')[0].split('\\')[-1]

# fig = make_subplots(rows= 1, cols=1,
# subplot_titles = ("Origin-Destiny Matrix"))

df = pd.read_csv(path, sep=';',  index_col = 0)

df.sort_index(axis=0, ascending=True, inplace=True)
df.sort_index(axis=1, ascending=True, inplace=True)

plt.figure(figsize=(15, 15))
s = sns.heatmap(df, annot=True)

#plt.figure(figsize=(15, 15))
#s = sns.heatmap(df, annot=False)


# fig.add_trace(px.line(df, x = range(200), y = 'Accumulated', title='Accumulated').data[0], row=2, col=1)
#fig = ff.create_annotated_heatmap(df, x=, y='Regions', colorscale='Viridis')


figure = s.get_figure()    

figure.savefig(f'{name}_od_matrix.png')#, dpi=400)

#plt.show()


# fig.update_yaxes(title_text="Daily infections for that 24 period", row=1, col=1)
# fig.update_yaxes(title_text="Total infections", row=2, col=1)

# fig.update_xaxes(title_text="Days since 50th infection", row=1, col=1)
# fig.update_xaxes(title_text="Days since 50th infection", row=2, col=1)


# fig.update_layout(
# title = "Infection Data",
# font=dict(
#     family="Courier New, monospace",
#     size=22,
#     color="RebeccaPurple"
# )
# )

#fig.show()