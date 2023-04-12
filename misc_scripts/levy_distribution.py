import sys

sys.path.append('../')

import argparse

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns
from scipy.stats import levy as scipy_levy

def create_levy_distribution_figure(location: float, scale: float, sample_size: int,
                        bin_start:float, bin_stop: float, bin_step:float) -> None:
    '''
    This function generates a plot of the Levy distribution using the given parameters. The plot shows the frequency of occurrence of values in a given range, as well as the cumulative frequency of values up to that range.

    Parameters:
    ----------
    dir_path: a Path object representing the directory in which to save the generated image.
    location: an integer representing the location parameter of the Levy distribution.
    scale: a float representing the scale parameter of the Levy distribution.
    size: a float representing the size of the sample to draw from the Levy distribution.
    bin_start: a float representing the starting point of the range of values to plot.
    bin_stop: a float representing the stopping point of the range of values to plot.
    bin_step: a float representing the size of each bin in the histogram.
    
    Returns:
    ----------
    None.

    The function generates two images: a histogram of the frequency of values in the given range, and a histogram of the cumulative frequency of values up to that range.
    '''
    # Setup
    __header:str = "Levy Distribution:"
    print(__header, f'Location: {location}, Scale: {scale}, Sample Size: {sample_size}',
          f'Hist Bin Start: {bin_start}, Hist Bin Stop: {bin_stop}, Hist Bin Step: {bin_step}')
     # Creates the directory if necessary
    dir_path = Path() / "levy_distribution"
    dir_path.mkdir(parents=True, exist_ok=True)

    # Creates a distribution using the function parameters
    dist = np.array(scipy_levy.rvs(loc=location, scale= scale, size = sample_size))
    print(f'\tMean {dist.mean()}, Max {dist.max()}')
    # Creates a histogram of frequencies
    bins = np.arange(bin_start, bin_stop, bin_step)
    sns.set_theme()
    s = sns.histplot(dist, bins=bins) # type: ignore
    fig_path = dir_path / f"levy-distribution-L{location}-S{scale}-Step{bin_step}-Q{sample_size}.png"
    print(__header, f'Saving levy distribution figure to:\n\t', fig_path)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=400)
    plt.clf()

    # Creates a second histogram with the cumulative values of frequencies
    bins = np.arange(bin_start, bin_stop/2.0, bin_step)
    s = sns.histplot(dist, bins=bins, cumulative=True) # type: ignore
    fig_path = dir_path / f"levy-distribution-L{location}-S{scale}-Step{bin_step}-Q{sample_size}-cumulative.png"
    print(__header, f'Saving cumulative levy distribution figure to:\n\t', fig_path)
    plt.ylim(0, sample_size)
    plt.tight_layout()
    plt.savefig(fig_path, dpi=400)
    plt.clf()

if __name__ == '__main__':
    arg_parser = argparse.ArgumentParser(description="Create Node Distante Distribution Figure.")
    arg_parser.add_argument('--l', metavar="L", type=float, default = 0.0, help='Distribution location parameter')
    arg_parser.add_argument('--s', metavar="S", type=float, default = 0.005, help='Distribution scale parameter.')
    arg_parser.add_argument('--q', metavar="Q", type=int, default = 10000, help='Sample quantity.')
    arg_parser.add_argument('--b', metavar="B", type=float, default = 0.0, help='Histogram Bins Begin/Start.')
    arg_parser.add_argument('--e', metavar="E", type=float, default = 0.4, help='Histogram Bins End/Stop.')
    arg_parser.add_argument('--t', metavar="T", type=float, default = 0.005, help='Histogram Bins Step.')
    args = vars(arg_parser.parse_args())
    create_levy_distribution_figure(location=args['l'], scale=args['s'], sample_size=args['q'],
                                    bin_start=args['b'], bin_stop=args['e'], bin_step=args['t'])