"""Offline fallback knowledge, used ONLY when partner API keys are missing.

With keys set, changelogs come from Tavily and analysis/rewrites from the
Nosana-hosted model. This module keeps the demo runnable on a laptop with no
network credentials (e.g. while waiting for credits) and is clearly labelled
"offline mode" in the UI.
"""

OFFLINE = {
    "numpy": {
        "sources": [
            {"title": "NumPy 2.0 migration guide", "url": "https://numpy.org/devdocs/numpy_2_0_migration_guide.html"},
        ],
        "text": (
            "NumPy 2.0 removed many aliases from the main namespace (NEP 52). "
            "np.float_ was removed; use np.float64. np.NaN and np.NAN were removed; use np.nan. "
            "np.Inf/np.Infinity removed; use np.inf. np.product removed; use np.prod. "
            "np.cumproduct removed; use np.cumprod. np.alltrue/np.sometrue removed; use np.all/np.any."
        ),
        "changes": [
            {"symbol": "np.float_", "search_pattern": r"\bnp\.float_\b", "replacement": "np.float64",
             "description": "np.float_ alias removed in NumPy 2.0", "rule": (r"\bnp\.float_\b", "np.float64")},
            {"symbol": "np.NaN", "search_pattern": r"\bnp\.(NaN|NAN)\b", "replacement": "np.nan",
             "description": "np.NaN / np.NAN aliases removed in NumPy 2.0", "rule": (r"\bnp\.(NaN|NAN)\b", "np.nan")},
            {"symbol": "np.product", "search_pattern": r"\bnp\.product\(", "replacement": "np.prod(",
             "description": "np.product removed in NumPy 2.0", "rule": (r"\bnp\.product\(", "np.prod(")},
        ],
    },
    "pandas": {
        "sources": [
            {"title": "What's new in pandas 2.0.0", "url": "https://pandas.pydata.org/docs/whatsnew/v2.0.0.html"},
        ],
        "text": (
            "pandas 2.0 removed DataFrame.append and Series.append (deprecated in 1.4); use pandas.concat. "
            "DataFrame.iteritems and Series.iteritems were removed; use .items(). "
            "Removed the 'line_terminator' argument of to_csv; use 'lineterminator'. "
            "pandas 3.0: string columns now default to the new 'str' dtype (StringDtype) instead of "
            "object, so numpy functions like np.issubdtype(series.dtype, ...) raise TypeError on them; "
            "use pandas.api.types.is_numeric_dtype(series) instead."
        ),
        "changes": [
            {"symbol": "DataFrame.append", "search_pattern": r"\.append\([^)]*ignore_index",
             "replacement": "pd.concat([df, pd.DataFrame([row])], ignore_index=True)",
             "description": "DataFrame.append removed in pandas 2.0",
             "rule": (r"(\w+)\.append\(([^,()]+),\s*ignore_index=True\)",
                      r"pd.concat([\1, pd.DataFrame([\2])], ignore_index=True)")},
            {"symbol": "DataFrame.iteritems", "search_pattern": r"\.iteritems\(", "replacement": ".items(",
             "description": "iteritems removed in pandas 2.0", "rule": (r"\.iteritems\(", ".items(")},
            {"symbol": "to_csv(line_terminator=)", "search_pattern": r"line_terminator=",
             "replacement": "lineterminator=", "description": "renamed in pandas 2.0",
             "rule": (r"line_terminator=", "lineterminator=")},
            {"symbol": "np.issubdtype on pandas dtypes", "search_pattern": r"np\.issubdtype\(\s*\w+\.dtype",
             "replacement": "pd.api.types.is_numeric_dtype(series)",
             "description": "pandas 3.0 default 'str' dtype is not a numpy dtype",
             "rule": (r"np\.issubdtype\(\s*(\w+)\.dtype,\s*np\.number\)", r"pd.api.types.is_numeric_dtype(\1)")},
        ],
    },
}


def offline_changelog(package: str) -> dict:
    entry = OFFLINE.get(package)
    if not entry:
        return {"sources": [], "text": ""}
    return {"sources": entry["sources"], "text": entry["text"]}


def offline_changes(package: str, version: str) -> list[dict]:
    entry = OFFLINE.get(package, {})
    out = []
    for c in entry.get("changes", []):
        c = dict(c)
        c.update(package=package, version=version,
                 source_url=entry["sources"][0]["url"] if entry.get("sources") else "")
        out.append(c)
    return out
