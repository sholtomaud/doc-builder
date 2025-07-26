"""
This module provides statistical analysis functions for the document generator.
"""
import pandas as pd
from scipy import stats


def run_ttest_ind(data: pd.DataFrame, series1_name: str, series2_name: str, **kwargs):
    """
    Performs an independent t-test on two series.
    """
    series1 = data[series1_name]
    series2 = data[series2_name]
    t_stat, p_value = stats.ttest_ind(series1, series2, **kwargs)
    return {"t_statistic": t_stat, "p_value": p_value}

def run_chi2_contingency(data: pd.DataFrame, x_name: str, y_name: str, **kwargs):
    """
    Performs a Chi-squared test on a contingency table.
    """
    contingency_table = pd.crosstab(data[x_name], data[y_name])
    chi2, p, dof, expected = stats.chi2_contingency(contingency_table, **kwargs)
    return {"chi2_statistic": chi2, "p_value": p, "degrees_of_freedom": dof}

# A registry of available statistical tests
STATS_REGISTRY = {
    "ttest_ind": run_ttest_ind,
    "chi2_contingency": run_chi2_contingency,
}

def run_analysis(analysis_config: dict, data: pd.DataFrame):
    """
    Runs a statistical analysis based on the provided configuration.
    """
    analysis_type = analysis_config.get("type")
    if analysis_type not in STATS_REGISTRY:
        raise ValueError(f"Unknown analysis type: {analysis_type}")

    # Pass all other config keys as arguments to the analysis function
    params = analysis_config.copy()
    del params["type"]
    del params["key"] # key is for the template, not the function

    return STATS_REGISTRY[analysis_type](data, **params)
