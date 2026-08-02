# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Regression tests for time-comparison offset parsing (fix 0efcd54, upstream #39344).

``get_column_groups`` assigns each contribution column to the time offset it was
generated for. Before the fix it matched with ``col.endswith(offset)``, so an
offset that is a string suffix of another offset -- offsets sharing a numeric
prefix such as ``"1 week ago"`` and ``"11 week ago"`` -- collided and columns
were attributed to the wrong offset. The fix matches on
``TIME_COMPARISON + offset`` instead.

The gate environment installs pytest, pandas and numpy only, so
``superset/utils/pandas_postprocessing/contribution.py`` is loaded directly from
source with stub modules in place of its ``flask_babel`` and ``superset``
dependencies instead of importing the ``superset`` package.
"""

import importlib.util
import sys
import types
from enum import Enum
from pathlib import Path

import pytest
from pandas import DataFrame

CONTRIBUTION_SOURCE = (
    Path(__file__).resolve().parents[1]
    / "superset"
    / "utils"
    / "pandas_postprocessing"
    / "contribution.py"
)

# superset.utils.core.TIME_COMPARISON: the separator between a metric label and
# the time offset it was shifted by.
TIME_COMPARISON = "__"


def _stub_modules() -> dict[str, types.ModuleType]:
    flask_babel = types.ModuleType("flask_babel")
    flask_babel.gettext = lambda message, **kwargs: message

    superset = types.ModuleType("superset")
    superset.__path__ = []

    exceptions = types.ModuleType("superset.exceptions")

    class InvalidPostProcessingError(Exception):
        pass

    exceptions.InvalidPostProcessingError = InvalidPostProcessingError

    utils = types.ModuleType("superset.utils")
    utils.__path__ = []

    core = types.ModuleType("superset.utils.core")

    class PostProcessingContributionOrientation(str, Enum):
        ROW = "row"
        COLUMN = "column"

    core.PostProcessingContributionOrientation = PostProcessingContributionOrientation
    core.TIME_COMPARISON = TIME_COMPARISON

    pandas_postprocessing = types.ModuleType("superset.utils.pandas_postprocessing")
    pandas_postprocessing.__path__ = []

    pp_utils = types.ModuleType("superset.utils.pandas_postprocessing.utils")
    pp_utils.validate_column_args = lambda *args, **kwargs: (lambda func: func)

    return {
        "flask_babel": flask_babel,
        "superset": superset,
        "superset.exceptions": exceptions,
        "superset.utils": utils,
        "superset.utils.core": core,
        "superset.utils.pandas_postprocessing": pandas_postprocessing,
        "superset.utils.pandas_postprocessing.utils": pp_utils,
    }


def _load_contribution_module() -> types.ModuleType:
    stubs = _stub_modules()
    originals = {name: sys.modules.get(name) for name in stubs}
    sys.modules.update(stubs)
    try:
        spec = importlib.util.spec_from_file_location(
            "devin_gate_tests._superset_contribution", CONTRIBUTION_SOURCE
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        for name, original in originals.items():
            if original is None:
                del sys.modules[name]
            else:
                sys.modules[name] = original
    return module


get_column_groups = _load_contribution_module().get_column_groups

GRAINS = ["second", "minute", "hour", "day", "week", "month", "quarter", "year"]
# Pairs (short, long) where ``str(long)`` ends with ``str(short)``: the numeric
# prefix collision class the fix addresses.
NUMERIC_SUFFIX_PAIRS = [
    (short, long)
    for short in range(1, 10)
    for long in range(10, 100)
    if str(long).endswith(str(short))
]


@pytest.mark.parametrize("grain", GRAINS)
@pytest.mark.parametrize("short,long", NUMERIC_SUFFIX_PAIRS)
def test_get_column_groups_offsets_sharing_a_numeric_prefix(
    grain: str, short: int, long: int
) -> None:
    """Every offset column is attributed to the offset that produced it."""
    offsets = [f"{short} {grain} ago", f"{long} {grain} ago"]
    metric = "SUM(num)"
    columns = [metric] + [f"{metric}{TIME_COMPARISON}{offset}" for offset in offsets]
    rename_columns = [f"{column} contribution" for column in columns]

    result = get_column_groups(
        DataFrame(columns=columns), offsets, rename_columns
    )

    assert result["non_time_shift"] == ([metric], [f"{metric} contribution"])
    assert result["time_shifts"] == {
        offset: (
            [f"{metric}{TIME_COMPARISON}{offset}"],
            [f"{metric}{TIME_COMPARISON}{offset} contribution"],
        )
        for offset in offsets
    }
