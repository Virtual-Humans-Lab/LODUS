import sys

sys.path.append('../')

import argparse

from pathlib import Path

import pandas as pd

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy.stats import levy as scipy_levy

def create_experiment_levy_sample_figure(experiment_name:str,
                                         bin_start:float, 
                                         bin_stop: float, 
                                         bin_step:float) -> None:
    '''
    This function generates plots from the Levy samples logged during an experiment (required a loaded levy_walk_sample_logger).

    Parameters:
    ----------
    experiment_name: name of the experiment where data will be searched (from 'outuput_logs' folder).
    bin_start: a float representing the starting point of the range of values to plot.
    bin_stop: a float representing the stopping point of the range of values to plot.
    bin_step: a float representing the size of each bin in the histogram.
    
    Returns:
    ----------
    None.

    The function generates two images: a histogram of the frequency of values in the given range, and a histogram of the cumulative frequency of values up to that range.
    '''
    # Creates the directory if necessary
    __header:str = "Experiment Levy Samples:"
    dir_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "data_frames"
    output_path = Path(__file__).parent.parent / "output_logs" / experiment_name / "results"
    output_path.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(dir_path / "levy_samples.csv", sep=';')

    # Creates a histogram of frequencies
    dist = df.to_numpy()
    bins = np.arange(bin_start, bin_stop, bin_step)
    s = sns.histplot(df, bins=bins) # type: ignore
    fig_path = output_path / f"levy-samples-Step{bin_step}-Q{dist.size}.png"
    print(__header, f'Creating Levy Sample Figure: Quant{dist.size}, Mean {dist.mean()}, Max {dist.max()}')
    plt.savefig(fig_path, dpi=400)
    plt.clf()

    # Creates a second histogram with the cumulative values of frequencies
    dist = df.to_numpy()
    bins = np.arange(bin_start, bin_stop/2.0, bin_step)
    s = sns.histplot(dist, bins=bins, cumulative=True) # type: ignore
    fig_path = output_path / f"levy-samples-Step{bin_step}-Q{dist.size}cumulative.png"
    plt.savefig(fig_path, dpi=400)
    plt.clf()

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Create Node Distante Distribution Figure.")
    arg_parser.add_argument('--e', metavar="E", type=str, default = None, help='Experiment Name (same as experiment configuration file)')
    arg_parser.add_argument('--b', metavar="B", type=float, default = 0.0, help='Histogram Bins Begin/Start.')
    arg_parser.add_argument('--s', metavar="E", type=float, default = 40000, help='Histogram Bins End/Stop.')
    arg_parser.add_argument('--w', metavar="T", type=float, default = 500, help='Histogram Bins Width/Step/Size.')
    args = vars(arg_parser.parse_args())
    create_experiment_levy_sample_figure(experiment_name=args['e'],
                                    bin_start=args['b'], bin_stop=args['s'], bin_step=args['w'])