import sys

sys.path.append('../')

import argparse

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import plotly.express as px

def movement_displacement_histogram(experiment_name:str, bin_size:float = 500, 
                                    x_limit:int | None = None, y_limit:int | None = None):
    __header:str = "Experiment Movement Displacement:"
    dir_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "data_frames"
    output_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "results"
    output_path.mkdir(parents=True, exist_ok=True)

    # Load dataframs from CSVs
    df_movement = pd.read_csv(dir_path / "movement_counter.csv", sep=';')
    df_group_movement = pd.read_csv(dir_path / "group_movement_counter.csv", sep=';')

    # Creates lists using the data (column_0 = distance; column_1 = frequency)
    movement_list = []
    group_movement_list = []
    for index, row in df_movement.iterrows():
        movement_list.extend([row.iloc[0]] * int(row.iloc[1]))
    for index, row in df_group_movement.iterrows():
        group_movement_list.extend([row.iloc[0]] * int(row.iloc[1]))

    # Creates a histogram of frequencies for the movement data
    movement_data = np.array(movement_list)
    max_distance = np.amax(movement_data) * 1.05
    bins = np.arange(0.0, max_distance, bin_size)
    s = sns.histplot(data=movement_data, bins=bins) # type: ignore
    fig_path = output_path / f"movement_distribution_size{movement_data.size}_bin{bin_size}.png"
    print(__header, "Saving movement displacement histogram at:\n\t", fig_path)
    if x_limit is not None: plt.xlim(0, x_limit)
    if y_limit is not None: plt.ylim(0, y_limit)
    plt.savefig(fig_path, dpi=400)
    plt.clf()

    # Creates a histogram of frequencies for the group movement data
    group_movement_data = np.array(group_movement_list)
    max_distance = np.amax(group_movement_data) * 1.05
    bins = np.arange(0.0, max_distance, bin_size)
    s = sns.histplot(data=group_movement_data, bins=bins) # type: ignore
    fig_path = output_path / f"group_movement_distribution_size{group_movement_data.size}_bin{bin_size}.png"
    print(__header, "Saving group movement displacement histogram at:\n\t", fig_path)
    # if x_limit is not None: plt.xlim(0, x_limit)
    # if y_limit is not None: plt.ylim(0, y_limit)
    plt.savefig(fig_path, dpi=400)
    plt.clf()

def movement_displacement_linechart(experiment_name:str, bin_size:float = 0.005, 
                                    x_limit:int | None = None, y_limit:int | None = None):
    __header:str = "Experiment Movement Displacement:"
    dir_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "data_frames"
    output_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "results"
    output_path.mkdir(parents=True, exist_ok=True)

    xaxis = dict(tickmode = 'linear',
                 tick0 = 0.0,
                 dtick = bin_size * 2)

    # Load dataframe from CSVs
    df_movement = pd.read_csv(dir_path / "movement_counter.csv", sep=';')
    
    # Gets max distance traveled and organizes bins
    max_distance = float(df_movement.max().loc['distance'])
    bins_limits = np.arange(0.0, max_distance, bin_size).tolist()
    data = {b:0 for b in bins_limits}

    # Sums frequencies for each bin
    for index, row in df_movement.iterrows():
        key = int((row.iloc[0] // bin_size))
        data[list(data.keys())[key]] += int(row.iloc[1])
        
    # Creates a dataframe from dict and the
    df = pd.DataFrame.from_dict(data, orient='index')

    # Creates and save html
    fig = px.bar(df, y = 0, title=f'Movement displacement data - {experiment_name}')
    fig.update_layout(xaxis = xaxis, hovermode="x")
    if x_limit is not None: fig.update_xaxes(range = [0, x_limit])
    if y_limit is not None: fig.update_yaxes(range = [0, y_limit])
    fig_path = output_path / f"movement_distance_bar_chart_size{len(df.index)}_bin{bin_size}.html"
    fig.write_html(fig_path)
    print(__header, "Saving movement displacement linechart at:\n\t", fig_path)
    
    # Repeats process for the group movement data
    df_group_movement = pd.read_csv(dir_path / "group_movement_counter.csv", sep=';')
    max_distance = df_group_movement.max().loc['distance']
    bins_limits = np.arange(0.0, max_distance, bin_size).tolist()#[1:]
    data = {b:0 for b in bins_limits}

    for index, row in df_group_movement.iterrows():
        key = int((row.iloc[0] // bin_size))
        data[list(data.keys())[key]] += int(row.iloc[1])

    df = pd.DataFrame.from_dict(data, orient='index')
    fig = px.bar(df, title=f'Group movement displacement data - {experiment_name}')
    fig.update_layout(xaxis = xaxis, hovermode="x")
    # if x_limit is not None: fig.update_xaxes(range = [0, x_limit])
    # if y_limit is not None: fig.update_yaxes(range = [0, y_limit])
    fig_path = output_path / f"group_movement_distance_bar_chart_size{len(df.index)}_bin{bin_size}.html"
    fig.write_html(fig_path)
    print(__header, "Saving group movement displacement linechart at:\n\t", fig_path)
    

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Create Node Distante Distribution Figure.")
    arg_parser.add_argument('--e', metavar="E", type=str, default = None, help='Experiment Name (same as experiment configuration file)')
    arg_parser.add_argument('--b', metavar="B", type=float, default = 500, help='Bin Size')
    arg_parser.add_argument('--x', metavar="X", type=float, default = None, help='X-Limit')
    arg_parser.add_argument('--y', metavar="Y", type=float, default = None, help='Y-Limit')
    args = vars(arg_parser.parse_args())
    movement_displacement_histogram(experiment_name=args['e'], bin_size=args['b'], x_limit=args['x'], y_limit=args['y'])
    movement_displacement_linechart(experiment_name=args['e'], bin_size=args['b'], x_limit=args['x'], y_limit=args['y'])