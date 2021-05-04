import pandas as pd

import sys

import seaborn as sns
import matplotlib.pyplot as plt

### instructions
# use *neigh.csv log file and chosen region name



path = sys.argv[1]
name  = sys.argv[2]
region = sys.argv[3]
values = sys.argv[4:]

split_path = path.split('.')[0].split('\\')
base_path = split_path[-1]

# fig = make_subplots(rows= 1, cols=1,
# subplot_titles = ("Origin-Destiny Matrix"))

df = pd.read_csv(path, sep=';',  index_col = 0)

# chosen_region = df[df['Neighbourhood'] == region]
# chosen_region = df["Total"]
# plt.figure()
# s   = sns.lineplot(data=chosen_region, x="Frame", legend='full')


df = df[df['Neighbourhood'] == region]
df = df[values]

print(df)
#df = df.melt('Frame', value_vars = values, value_name = 'Population' )
s   = sns.lineplot(data=df, legend='full')
plt.title(region)
ax = plt.gca()
ax.set(xlabel='Simulation hour', ylabel='Population Size in Region')
#s = sns.factorplot(x = "Frame", y= values, hue=values, data=df)

# fig.add_trace(px.line(df, x = range(200), y = 'Accumulated', title='Accumulated').data[0], row=2, col=1)
#fig = ff.create_annotated_heatmap(df, x=, y='Regions', colorscale='Viridis')


figure = s.get_figure()    


figure.savefig(f'{split_path[-2]}_{region}.png', dpi=400)
#figure.savefig(f'{base_path}_{region}_{values}_quantity_over_time.png', dpi=400)


