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
"""Regression tests for chart data API error mapping (fix 227b3a4).

``SupersetSecurityException`` raised by ``ChartDataCommand.validate`` used to
escape the chart data endpoints as a 500; the endpoints must return 403.
"""

from __future__ import annotations

import inspect
from typing import Any, Callable
from unittest.mock import MagicMock, patch

import pytest
from flask import Flask, Response

from superset.charts.data.api import ChartDataRestApi
from superset.errors import ErrorLevel, SupersetError, SupersetErrorType
from superset.exceptions import SupersetSecurityException
from superset.utils import json

QUERY_CONTEXT: dict[str, Any] = {
    "datasource": {"id": 42, "type": "table"},
    "queries": [{"columns": ["col1"], "metrics": ["count"]}],
    "result_format": "json",
    "result_type": "full",
}


def _security_exception() -> SupersetSecurityException:
    return SupersetSecurityException(
        SupersetError(
            error_type=SupersetErrorType.DATASOURCE_SECURITY_ACCESS_ERROR,
            message="You don't have access to this datasource",
            level=ErrorLevel.ERROR,
        )
    )


def _endpoint(name: str) -> Callable[..., Response]:
    """Return the undecorated view function (auth/logging decorators removed)."""
    return inspect.unwrap(getattr(ChartDataRestApi, name))


def _api() -> ChartDataRestApi:
    api = ChartDataRestApi.__new__(ChartDataRestApi)
    chart = MagicMock()
    chart.query_context = json.dumps(QUERY_CONTEXT)
    chart.params = json.dumps({})
    api.datamodel = MagicMock()
    api.datamodel.get.return_value = chart
    api._base_filters = MagicMock()
    return api


@pytest.fixture
def app_context() -> Any:
    app = Flask(__name__)
    with app.test_request_context(
        "/api/v1/chart/data",
        json=QUERY_CONTEXT,
    ):
        yield


@pytest.fixture
def failing_command() -> Any:
    with patch("superset.charts.data.api.ChartDataCommand") as command_cls:
        command_cls.return_value.validate.side_effect = _security_exception()
        yield command_cls


def test_get_data_returns_403_on_security_exception(
    app_context: Any, failing_command: Any
) -> None:
    api = _api()
    with patch.object(api, "_create_query_context_from_form", return_value=MagicMock()):
        response = _endpoint("get_data")(api, pk=1)

    assert response.status_code == 403


def test_data_returns_403_on_security_exception(
    app_context: Any, failing_command: Any
) -> None:
    api = _api()
    with patch.object(api, "_create_query_context_from_form", return_value=MagicMock()):
        response = _endpoint("data")(api)

    assert response.status_code == 403


def test_data_from_cache_returns_403_on_security_exception(
    app_context: Any, failing_command: Any
) -> None:
    api = _api()
    with (
        patch.object(api, "_create_query_context_from_form", return_value=MagicMock()),
        patch.object(
            api, "_load_query_context_form_from_cache", return_value=QUERY_CONTEXT
        ),
    ):
        response = _endpoint("data_from_cache")(api, cache_key="abc")

    assert response.status_code == 403
