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
"""Regression test for boxplot MINMAX whiskers (fix e075133, upstream #42272).

Under MINMAX, ``whisker_high``/``whisker_low`` are plain ``np.max``/``np.min``;
passing those callables to ``GroupBy.agg`` makes pandas emit a FutureWarning.
The fix passes the string forms instead.

The gate environment installs pytest, pandas and numpy only, so
``superset.utils.pandas_postprocessing.boxplot`` is loaded directly from source
with stub modules standing in for the Flask-dependent imports.
"""

import enum
import importlib.util
import sys
import types
import warnings
from pathlib import Path

import pandas as pd

SUPERSET_ROOT = Path(__file__).resolve().parents[1] / "superset"
POSTPROCESSING_ROOT = SUPERSET_ROOT / "utils" / "pandas_postprocessing"


class _WhiskerType(str, enum.Enum):
    TUKEY = "tukey"
    MINMAX = "min/max"
    PERCENTILE = "percentile"


def _package(name: str, path: Path) -> types.ModuleType:
    module = types.ModuleType(name)
    module.__path__ = [str(path)]
    return module


def _stub_modules() -> dict[str, types.ModuleType]:
    flask_babel = types.ModuleType("flask_babel")
    flask_babel.gettext = lambda message, **kwargs: message

    exceptions = types.ModuleType("superset.exceptions")
    exceptions.InvalidPostProcessingError = type(
        "InvalidPostProcessingError", (Exception,), {}
    )

    core = types.ModuleType("superset.utils.core")
    core.PostProcessingBoxplotWhiskerType = _WhiskerType

    return {
        "flask_babel": flask_babel,
        "superset": _package("superset", SUPERSET_ROOT),
        "superset.exceptions": exceptions,
        "superset.utils": _package("superset.utils", SUPERSET_ROOT / "utils"),
        "superset.utils.core": core,
        "superset.utils.pandas_postprocessing": _package(
            "superset.utils.pandas_postprocessing", POSTPROCESSING_ROOT
        ),
    }


def _load_boxplot():
    originals = {name: sys.modules.get(name) for name in _stub_modules()}
    sys.modules.update(_stub_modules())
    loaded = []
    try:
        for name in ("utils", "aggregate", "boxplot"):
            full_name = f"superset.utils.pandas_postprocessing.{name}"
            spec = importlib.util.spec_from_file_location(
                full_name, POSTPROCESSING_ROOT / f"{name}.py"
            )
            module = importlib.util.module_from_spec(spec)
            sys.modules[full_name] = module
            loaded.append(full_name)
            spec.loader.exec_module(module)
        return module.boxplot
    finally:
        for name in loaded:
            del sys.modules[name]
        for name, original in originals.items():
            if original is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = original


boxplot = _load_boxplot()

names_df = pd.DataFrame(
    {
        "region": ["EU", "EU", "EU", "US", "US", "US"],
        "cars": [1.0, 2.0, 30.0, 4.0, 5.0, 60.0],
    }
)


def test_boxplot_minmax_does_not_raise_future_warning() -> None:
    expected = names_df.groupby("region")["cars"].agg(["max", "min"])

    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        df = boxplot(
            df=names_df,
            groupby=["region"],
            whisker_type=_WhiskerType.MINMAX,
            metrics=["cars"],
        )

    df = df.set_index("region")
    assert df["cars__max"].tolist() == expected["max"].tolist() == [30.0, 60.0]
    assert df["cars__min"].tolist() == expected["min"].tolist() == [1.0, 4.0]
    assert df["cars__outliers"].tolist() == [[], []]


def test_boxplot_percentile_whiskers_keep_callable_operators() -> None:
    """The string shortcut must stay scoped to MINMAX: percentile whiskers are
    closures and have to keep clipping outliers."""
    df = boxplot(
        df=names_df,
        groupby=["region"],
        whisker_type=_WhiskerType.PERCENTILE,
        metrics=["cars"],
        percentiles=[10, 90],
    ).set_index("region")

    assert df["cars__max"].tolist() != [30.0, 60.0]
