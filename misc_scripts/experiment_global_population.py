import sys

sys.path.append('../')

import argparse
from pathlib import Path

import pandas as pd
import plotly.express as px


def global_population_linechart(experiment_name:str, 
                              additional_exp_path:str = '', 
                              columns: list[str] = None,
                              cycle_steps: list[int] = None,
                              x_label: str = '',
                              y_label: str = '',
                              title: str = '',
                              show_figures:bool = False):
    __header:str = "Experiment Global Population:"
    
    # Setup
    # Creates the output directory if necessary
    source_path = Path(__file__).parent.parent / "output_logs" / additional_exp_path / experiment_name
    output_path = source_path / "results"
    output_path.mkdir(parents=True, exist_ok=True)

    # Load population data and filter columns and entries accordingly
    df = pd.read_csv(source_path / "global.csv", sep = ';')
    if cycle_steps: df = df[df['Hour'].isin(cycle_steps)].reset_index(drop = True)
    
    # Creates one line plot for each column selected
    data_to_track = []
    df2 = pd.DataFrame()
    for c in columns:
        df2[c] =  df.reset_index()[c]
        data_to_track.append(c)

    print (df2)
    
    fig = px.line(df2, y = data_to_track,
                  labels={'index': x_label, 'value': y_label, 'variable': 'Legend'}, 
                  width=800, height=450, hover_name="variable", #hover_data=['Susceptible', 'Infected', 'Removed'],
                  title=title)#, markers=bool(cycle_steps))
    # xaxes_upt = {"tickmode": "linear", "tick0": 0, "dtick": 24}
    # fig.update_xaxes(xaxes_upt)
    sir = True
    if sir:
        fig.update_layout(hovermode="x")
    if show_figures: fig.show()

    file_name = fig.layout.title.text.replace(" ","")
    print(__header, f'Saving PNG figure and HTML at:\n{output_path / file_name}')
    fig.write_image(output_path / (file_name + ".png"), format = 'png')
    fig.write_html(output_path / (file_name + ".html"))


if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Create Region Distante Distribution Figure.")
    arg_parser.add_argument('--e', metavar="E", type=str, default = None, help='Experiment Name (same as experiment configuration file)')
    arg_parser.add_argument('--p', metavar="P", type=str, default = '', help='Additional experiment path')
    arg_parser.add_argument('--c', metavar="C", nargs='+', type=str, default = ['Total'], help='Columns in data frame')
    arg_parser.add_argument('--s', metavar="S", nargs='+', type=int, default = [], help='Cycle Steps to be presented.')
    arg_parser.add_argument('--x', metavar="X", type=str, default = 'Time', help='X-Label')
    arg_parser.add_argument('--y', metavar="Y", type=str, default = 'Population', help='Y-Label')
    arg_parser.add_argument('--t', metavar="T", type=str, default = 'SIR Population Status', help='Figure Title')
    arg_parser.add_argument('--f', metavar="F", type=bool, default = False, help='Show Figure')
    args = vars(arg_parser.parse_args())
    global_population_linechart(experiment_name=args['e'], 
                              additional_exp_path=args['p'],
                              columns=args['c'],
                              cycle_steps=args['s'],
                              x_label=args['x'],
                              y_label=args['y'],
                              title=args['t'],
                              show_figures=args['f'])