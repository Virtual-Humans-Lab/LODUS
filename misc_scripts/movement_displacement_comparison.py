import sys

sys.path.append('../')

import argparse

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import plotly.express as px

def displacement_histogram_comparison(experiment_names:list[str], 
                                      additional_exp_path:str = '', 
                                      bin_size:float = 500, 
                                      x_limit:int | None = None, y_limit:int | None = None):
    __header:str = "Displacement Histogram Comparison:"

    # Setup
    # Creates the output directory if necessary
    dir_path = Path() / "movement_displacement_comparison" / additional_exp_path
    dir_path.mkdir(parents=True, exist_ok=True)
    data_list:list[tuple[str,np.ndarray]] = []
    for exp in experiment_names:
        _exp_path = Path(__file__).parent.parent / "output_logs" / additional_exp_path / exp / "data_frames"
        _df = pd.read_csv(_exp_path / "movement_counter.csv", sep=';')
        _exp_movement_list = []
        for index, row in _df.iterrows():
            _exp_movement_list.extend([row.iloc[0]] * int(row.iloc[1]))
        _exp_movement_data = np.array(_exp_movement_list)
        data_list.append((exp, _exp_movement_data))

    # Find max displacement to create bins
    max_displacement = 0
    for (exp, _data) in data_list:
        max_displacement = max(max_displacement, np.amax(_data) * 1.05)
    bins = np.arange(0.0, max_displacement, bin_size)

    # Plot multiple histograms
    sns.set_theme()
    for (exp, _data) in data_list:
        s = sns.histplot(data=_data, bins=bins, element='poly', fill=False, label=exp) # type: ignore
    plt.legend(fancybox=True, shadow=True, fontsize = 'x-small')
    plt.tight_layout()
    fig_path = dir_path / f"displacement_histogram_comparison_{experiment_names}.png"
    print(__header, "Saving displacement histogram comparison at:\n\t", fig_path)
    if x_limit is not None: plt.xlim(0, x_limit)
    if y_limit is not None: plt.ylim(0, y_limit)
    plt.savefig(fig_path, dpi=400)
    plt.clf()

def combined_movement_displacement_barchart(experiment_name:str, bin_size:float = 0.005, 
                                    x_limit:int | None = None, y_limit:int | None = None):
    __header:str = "Experiment Movement Displacement:"
    dir_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "data_frames"
    output_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "results"
    dir_path.mkdir(parents=True, exist_ok=True)

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
    arg_parser.add_argument('--e', metavar="E", nargs='+', type=str, default = [], help='Experiment Name List (same as experiment configuration file)')
    arg_parser.add_argument('--p', metavar="P", type=str, default = '', help='Additional experiment path')
    arg_parser.add_argument('--b', metavar="B", type=float, default = 500, help='Bin Size')
    arg_parser.add_argument('--x', metavar="X", type=float, default = None, help='X-Limit')
    arg_parser.add_argument('--y', metavar="Y", type=float, default = None, help='Y-Limit')
    args = vars(arg_parser.parse_args())
    displacement_histogram_comparison(experiment_names=args['e'], 
                                      additional_exp_path=args['p'],
                                      bin_size=args['b'], 
                                      x_limit=args['x'], 
                                      y_limit=args['y'])
    # movement_displacement_linechart(experiment_name=args['e'], bin_size=args['b'], x_limit=args['x'], y_limit=args['y'])