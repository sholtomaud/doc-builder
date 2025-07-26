"""
This module contains all the plotting functions for the document generator.
It uses a registry pattern to make it easy to add new plot types.
"""

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def plot_pairplot(plot_config: dict, data: pd.DataFrame, study_name: str) -> plt.Figure:
    """Generates a pairplot from the given data."""
    fig = plt.figure()
    sns.pairplot(data)
    return fig


def plot_placeholder(
    plot_config: dict, data: pd.DataFrame, study_name: str
) -> plt.Figure:
    """Generates a placeholder image with text."""
    fig = plt.figure()
    text = plot_config.get("text", "Placeholder").replace(
        "{{ study_name }}", study_name
    )
    plt.text(0.5, 0.5, text, ha="center", va="center", fontsize=20)
    return fig


# The registry that maps plot types to their corresponding functions.
# To add a new plot type, create a function and add it to this dictionary.
PLOT_REGISTRY = {
    "pairplot": plot_pairplot,
    "placeholder": plot_placeholder,
}


def generate_plot_from_config(
    plot_config: dict, data: pd.DataFrame, study_name: str
) -> plt.Figure | None:
    """
    Looks up the plot type in the registry and calls the corresponding function.
    """
    plot_type = plot_config.get("type")
    if not plot_type:
        print("Error: Plot configuration is missing the 'type' key.")
        return None

    plot_function = PLOT_REGISTRY.get(plot_type)
    if not plot_function:
        print(f"Error: Unknown plot type '{plot_type}' requested.")
        return None

    return plot_function(plot_config, data, study_name)
