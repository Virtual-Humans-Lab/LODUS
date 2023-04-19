import sys

sys.path.append('../')

import argparse
from pathlib import Path

import pandas as pd
import plotly.express as px


def node_population_linechart(experiment_name:str, 
                              additional_exp_path:str = '', 
                              columns: list[str] = None,
                              cycle_steps: list[int] = None,
                              node_types:list[str] = None,
                              nodes_in_regions:list[str] = None,
                              x_label: str = '',
                              y_label: str = '',
                              title: str = '',
                              show_figures:bool = False):
    __header:str = "Experiment Node Population:"
    
    # Setup
    # Creates the output directory if necessary
    source_path = Path(__file__).parent.parent / "output_logs" / additional_exp_path / experiment_name
    output_path = source_path / "results"
    output_path.mkdir(parents=True, exist_ok=True)

    # Load population data and filter columns and entries accordingly
    df = pd.read_csv(source_path / "nodes.csv", sep = ';')
    if cycle_steps: df = df[df['Hour'].isin(cycle_steps)].reset_index(drop = True)
    if node_types: df = df[df['Node'].str.contains('//' + '|//'.join(node_types))].reset_index(drop = True)
    if nodes_in_regions: df = df[df['Node'].str.contains('//|'.join(nodes_in_regions) + '//')].reset_index(drop = True)

    # Creates one line plot for each Node and each column selected
    data_to_track = []
    df2 = pd.DataFrame()
    for r in df['Node'].unique():
        for c in columns:
            df2[r + ": " + c] =  df[df['Node'] == r].reset_index()[c]
            data_to_track.append(r + ": " + c)

    fig = px.line(df2, y = data_to_track,
                  labels={'index': x_label, 'value': y_label, 'variable': 'Legend'}, 
                  title=title, markers=bool(cycle_steps))
    # xaxes_upt = {"tickmode": "linear", "tick0": 0, "dtick": 24}
    # fig.update_xaxes(xaxes_upt)

    if show_figures: fig.show()

    file_name = fig.layout.title.text.replace(" ","")
    print(__header, f'Saving PNG figure and HTML at:\n{output_path / file_name}')
    fig.write_image(output_path / (file_name + ".png"), format = 'png')
    fig.write_html(output_path / (file_name + ".html"))


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Create Node Distante Distribution Figure.")
    arg_parser.add_argument('--e', metavar="E", type=str, default = None, help='Experiment Name (same as experiment configuration file)')
    arg_parser.add_argument('--p', metavar="P", type=str, default = '', help='Additional experiment path')
    arg_parser.add_argument('--c', metavar="C", nargs='+', type=str, default = ['Total'], help='Columns in data frame')
    arg_parser.add_argument('--n', metavar="N", nargs='+', type=str, default = [], help='Node Types to be presented.')
    arg_parser.add_argument('--r', metavar="R", nargs='+', type=str, default = [], help='Regions to be presented.')
    arg_parser.add_argument('--s', metavar="S", nargs='+', type=int, default = [], help='Cycle Steps to be presented.')
    arg_parser.add_argument('--x', metavar="X", type=str, default = 'Time', help='X-Label')
    arg_parser.add_argument('--y', metavar="Y", type=str, default = 'Population', help='Y-Label')
    arg_parser.add_argument('--t', metavar="T", type=str, default = 'Node Population', help='Figure Title')
    arg_parser.add_argument('--f', metavar="F", type=bool, default = False, help='Show Figure')
    args = vars(arg_parser.parse_args())
    node_population_linechart(experiment_name=args['e'], 
                              additional_exp_path=args['p'],
                              columns=args['c'],
                              node_types=args['n'],
                              nodes_in_regions=args['r'],
                              cycle_steps=args['s'],
                              x_label=args['x'],
                              y_label=args['y'],
                              title=args['t'],
                              show_figures=args['f'])