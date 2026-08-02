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
"""Regression tests for ChartDataQueryObjectSchema.rename_deprecated_fields
(fix 5bbab86, upstream #41263).

The gate environment installs pytest only, so ``superset.charts.schemas`` cannot
be imported. The ``rename_deprecated_fields`` hook is instead extracted from the
source file with ``ast`` and compiled on its own.
"""

import ast
from pathlib import Path
from typing import Any, Callable

SCHEMAS_SOURCE = (
    Path(__file__).resolve().parents[1] / "superset" / "charts" / "schemas.py"
)  # noqa: E501


def _load_rename_deprecated_fields() -> Callable[..., dict[str, Any]]:
    tree = ast.parse(SCHEMAS_SOURCE.read_text())
    classes = [
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ChartDataQueryObjectSchema"
    ]
    assert len(classes) == 1, "ChartDataQueryObjectSchema not found"
    functions = [
        node
        for node in classes[0].body
        if isinstance(node, ast.FunctionDef) and node.name == "rename_deprecated_fields"
    ]
    assert len(functions) == 1, "rename_deprecated_fields not found"

    function = functions[0]
    function.decorator_list = []
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    namespace: dict[str, Any] = {"Any": Any}
    exec(compile(module, str(SCHEMAS_SOURCE), "exec"), namespace)  # noqa: S102
    return namespace["rename_deprecated_fields"]


rename_deprecated_fields = _load_rename_deprecated_fields()


def _rename(data: dict[str, Any]) -> dict[str, Any]:
    return rename_deprecated_fields(None, data)


def test_zero_timeseries_limit_is_renamed_not_dropped() -> None:
    assert _rename({"timeseries_limit": 0}) == {"series_limit": 0}


def test_truthy_deprecated_fields_are_renamed() -> None:
    assert _rename({"timeseries_limit": 5, "timeseries_limit_metric": "count"}) == {
        "series_limit": 5,
        "series_limit_metric": "count",
    }


def test_absent_deprecated_fields_leave_canonical_keys_untouched() -> None:
    assert _rename({"series_limit": 10, "series_limit_metric": "count"}) == {
        "series_limit": 10,
        "series_limit_metric": "count",
    }


def test_none_valued_deprecated_fields_are_discarded() -> None:
    assert _rename({"timeseries_limit": None, "series_limit": 10}) == {
        "series_limit": 10
    }
