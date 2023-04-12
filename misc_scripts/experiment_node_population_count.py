import sys
from time import sleep

sys.path.append('../')

import argparse

from pathlib import Path

import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy.stats import levy as scipy_levy

def node_population_linechart(experiment_name:str, create_cycle_0:bool = False, show_figures:bool = False):
    __header:str = "Experiment Node Population:"
    
    # dir_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "data_frames"
    dir_path = Path(__file__).parent.parent / "output_logs" / experiment_name
    output_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "results"
    output_path.mkdir(parents=True, exist_ok=True)

    figures = []
    xaxes_upt = {"tickmode": "linear", "tick0": 0, "dtick": 24}

    # Default Node Population Plot
    df = pd.read_csv(dir_path /  "nodes.csv", sep = ';')

    # print(df)
    fig = px.line(df, x = 'Frame',y = 'Total',color="Node", 
                    labels={'Total':'Node Population'}, 
                    title=f"Total Population - Per Node - {experiment_name}")
    fig.update_xaxes(xaxes_upt)
    figures.append(fig)
    
    # Default Node Population Plot - Hour 0
    if create_cycle_0:
        df = df[df['Hour'] == 0].reset_index(drop = True)
        df.index = range(1,len(df)+1)
        fig = px.line(df, x = 'Day',y = 'Total',color="Node", 
                        labels={'Total':'Node Population', 'Day':'Simulation Day'}, 
                        title=f"Total Population - Per Node - Hour 0 {experiment_name}", markers=True)
        figures.append(fig)


    if show_figures:
        for f in figures: 
            sleep(0.5)
            f.show()
    for f in figures:
        file_name = f.layout.title.text.replace(" ","")
        print(__header, f'Saving PNG figure and HTML at:\n{output_path / file_name}')
        f.write_image(output_path / (file_name + ".png"), format = 'png')
        f.write_html(output_path / (file_name + ".html"))


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Create Node Distante Distribution Figure.")
    arg_parser.add_argument('--e', metavar="E", type=str, default = None, help='Experiment Name (same as experiment configuration file)')
    arg_parser.add_argument('--s', metavar="S", type=bool, default = False, help='Show Figures')
    arg_parser.add_argument('--z', metavar="Z", type=bool, default = False, help='Create Cycle Step == 0')
    args = vars(arg_parser.parse_args())
    print(args)
    node_population_linechart(experiment_name=args['e'], create_cycle_0=args['z'],show_figures=args['s'])