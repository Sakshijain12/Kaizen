import math

import pandas as pd

from analytics.stats import add_sale, column_summary, normalize, to_float_array


def test_to_float_array_maps_none_to_nan():
    arr = to_float_array([1, None, 3])
    assert arr.dtype.kind == "f"
    assert math.isnan(arr[1])


def test_normalize():
    assert list(normalize([0, 5, 10])) == [0.0, 0.5, 1.0]


def test_add_sale():
    df = pd.DataFrame([{"item": "tea", "amount": 3.0}])
    df = add_sale(df, {"item": "mochi", "amount": 5.0})
    assert len(df) == 2
    assert df.iloc[-1]["item"] == "mochi"


def test_column_summary():
    df = pd.DataFrame([{"item": "tea", "amount": 3.0}, {"item": "mochi", "amount": 5.0}])
    assert column_summary(df) == {"amount": 8.0}
