"""
This module provides plotting functions for the document generator.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def create_pairplot(data: pd.DataFrame, **kwargs):
    """Creates a pairplot using seaborn."""
    plot = sns.pairplot(data, **kwargs)
    return plot

def create_scatterplot(data: pd.DataFrame, **kwargs):
    """Creates a scatterplot using seaborn."""
    plt.figure() # Create a new figure to avoid overlap
    plot = sns.scatterplot(data=data, **kwargs)
    return plot.get_figure()

def create_histogram(data: pd.DataFrame, **kwargs):
    """Creates a histogram using seaborn."""
    plt.figure()
    plot = sns.histplot(data=data, **kwargs)
    return plot.get_figure()

def create_boxplot(data: pd.DataFrame, **kwargs):
    """Creates a boxplot using seaborn."""
    plt.figure()
    plot = sns.boxplot(data=data, **kwargs)
    return plot.get_figure()


PLOT_REGISTRY = {
    "pairplot": create_pairplot,
    "scatterplot": create_scatterplot,
    "histogram": create_histogram,
    "boxplot": create_boxplot,
}

def generate_plot(plot_config: dict, data: pd.DataFrame, output_dir: Path):
    """
    Generates a plot based on the provided configuration.
    """
    plot_type = plot_config.get("type")
    if plot_type not in PLOT_REGISTRY:
        raise ValueError(f"Unknown plot type: {plot_type}")

    # Prepare params for the plotting function
    params = plot_config.copy()
    del params["type"]
    key = params.pop("key") # Use key for filename, not for plotting function

    # Generate the plot
    plot = PLOT_REGISTRY[plot_type](data=data, **params)

    # Save the plot
    output_path = output_dir / f"{key}.png"
    plot.savefig(output_path)
    plt.close(plot) # Close the plot to free memory

    return output_path
