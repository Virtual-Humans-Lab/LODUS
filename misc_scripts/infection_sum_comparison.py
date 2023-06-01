import sys

sys.path.append('../')

import argparse

from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
import plotly.express as px

def infection_sum_comparison(experiment_names:list[str], 
                             additional_exp_path:str = '', 
                             cycle_steps: list[int] = None,
                             x_label: str = '',
                             y_label: str = '',
                             title: str = '',
                             limit:int | None = None):
    __header:str = "Displacement Histogram Comparison:"

    # Setup
    # Creates the output directory if necessary
    dir_path = Path() / "infection_sum_comparison" / additional_exp_path
    dir_path.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame()
    for exp in experiment_names:
        _exp_path = Path(__file__).parent.parent / "output_logs" / additional_exp_path / exp / "data_frames"
        _df = pd.read_csv(_exp_path / "infection_sum.csv", sep=';')
        if cycle_steps: _df = _df[_df['Cycle Step'].isin(cycle_steps)].reset_index(drop = True)
        df[exp] = _df["Infection Sum"]

    fig = px.line(df,
                  labels={'index': x_label, 'value': y_label, 'variable': 'Legend'}, 
                  title=title) #, markers=bool(cycle_steps))

    fig_path = dir_path / f"infection_sum_comparison{experiment_names}"
    #file_name = fig.layout.title.text.replace(" ","")
    print(__header, f'Saving PNG figure and HTML at:\n{fig_path}')
    fig.write_image(str(fig_path) + ".png", format = 'png')
    fig.write_html(str(fig_path) + ".html")
    

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Create Node Distante Distribution Figure.")
    arg_parser.add_argument('--e', metavar="E", nargs='+', type=str, default = [], help='Experiment Name List (same as experiment configuration file)')
    arg_parser.add_argument('--p', metavar="P", type=str, default = '', help='Additional experiment path')
    arg_parser.add_argument('--l', metavar="L", type=float, default = None, help='X-Limit (CycleSteps)')
    arg_parser.add_argument('--s', metavar="S", nargs='+', type=int, default = [], help='Cycle Steps to be presented.')
    arg_parser.add_argument('--x', metavar="X", type=str, default = 'Time / Simulation Step', help='X-Label')
    arg_parser.add_argument('--y', metavar="Y", type=str, default = 'Population', help='Y-Label')
    args = vars(arg_parser.parse_args())
    infection_sum_comparison(experiment_names=args['e'], 
                             additional_exp_path=args['p'],
                             cycle_steps=args['s'],
                             x_label=args['x'],
                             y_label=args['y'],
                             limit=args['l'])
    # movement_displacement_linechart(experiment_name=args['e'], bin_size=args['b'], x_limit=args['x'], y_limit=args['y'])