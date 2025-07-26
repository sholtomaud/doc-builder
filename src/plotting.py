"""
This module provides plotting functions for the document generator.
"""
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def create_placeholder(data: pd.DataFrame, text: str, **kwargs):
    """Creates a placeholder image with text."""
    plt.figure()
    # The text might contain a study name placeholder, which we can't resolve here.
    # We'll just display the raw text.
    plt.text(0.5, 0.5, text, ha="center", va="center", wrap=True)
    return plt.gcf()


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
    "placeholder": create_placeholder,
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

    # Remove legacy keys that are not valid plot arguments
    params.pop("data_source", None)

    # Generate the plot
    plot = PLOT_REGISTRY[plot_type](data=data, **params)

    # Save the plot
    output_path = output_dir / f"{key}.png"
    plot.savefig(output_path)

    # Close the plot to free memory, handling the special case for pairplot
    if isinstance(plot, plt.Figure):
        plt.close(plot)
    else:
        # For seaborn PairGrid objects, which don't have a direct close method
        plt.close()

    return output_path
