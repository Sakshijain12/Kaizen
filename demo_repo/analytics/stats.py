"""Tiny sales-analytics module written against numpy 1.x / pandas 1.x."""
import numpy as np
import pandas as pd


def to_float_array(values):
    """Convert raw values to a float array, mapping None to NaN."""
    cleaned = [np.NaN if v is None else v for v in values]
    return np.array(cleaned, dtype=np.float_)


def normalize(values):
    """Scale values to 0..1, ignoring NaNs."""
    arr = to_float_array(values)
    lo, hi = np.nanmin(arr), np.nanmax(arr)
    return (arr - lo) / (hi - lo)


def add_sale(df, sale):
    """Append one sale (a dict) to the sales DataFrame."""
    return df.append(sale, ignore_index=True)


def column_summary(df):
    """Return {column: total} for every numeric column."""
    summary = {}
    for name, series in df.iteritems():
        if np.issubdtype(series.dtype, np.number):
            summary[name] = float(series.sum())
    return summary
