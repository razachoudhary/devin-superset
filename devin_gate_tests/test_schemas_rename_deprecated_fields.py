"""Regression test for 5bbab86a07 (#41263).

`ChartDataQueryObjectSchema.rename_deprecated_fields` used a walrus truthiness
check (`if value := data.pop(old, None)`), which silently dropped deprecated
fields whose value was `0`. The fix renames the field whenever the popped value
is truthy *or* exactly `0`.

Superset's dependencies are not installable in this environment, so the logic
under test is copied verbatim from superset/charts/schemas.py.
"""

from typing import Any

_RENAMES = (
    ("groupby", "columns"),
    ("granularity_sqla", "granularity"),
    ("timeseries_limit", "series_limit"),
    ("timeseries_limit_metric", "series_limit_metric"),
)


def rename_deprecated_fields(data: dict[str, Any]) -> dict[str, Any]:
    for old, new in _RENAMES:
        value = data.pop(old, None)
        if value or value == 0:
            data[new] = value
    return data


def test_zero_timeseries_limit_is_renamed():
    assert rename_deprecated_fields({"timeseries_limit": 0}) == {"series_limit": 0}


def test_truthy_values_are_renamed():
    data = {
        "groupby": ["a"],
        "granularity_sqla": "ds",
        "timeseries_limit": 10,
        "timeseries_limit_metric": "count",
    }
    assert rename_deprecated_fields(data) == {
        "columns": ["a"],
        "granularity": "ds",
        "series_limit": 10,
        "series_limit_metric": "count",
    }


def test_other_falsy_values_are_dropped():
    data = {
        "groupby": [],
        "granularity_sqla": "",
        "timeseries_limit": None,
        "timeseries_limit_metric": None,
    }
    assert rename_deprecated_fields(data) == {}


def test_absent_fields_are_not_added():
    assert rename_deprecated_fields({"metrics": ["count"]}) == {"metrics": ["count"]}
