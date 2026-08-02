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
"""Gate regression check for chart data API 403 handling (fix 227b3a4).

The runtime regression test lives in
``tests/unit_tests/charts/data/api_test.py``; it needs the full Superset
package, which the gate environment does not install. This check therefore
parses ``superset/charts/data/api.py`` with ``ast`` and asserts that each chart
data entry point still maps ``SupersetSecurityException`` to
``self.response_403()`` instead of letting it escape as a 500.
"""

import ast
from pathlib import Path

import pytest

API_SOURCE = (
    Path(__file__).resolve().parents[1] / "superset" / "charts" / "data" / "api.py"
)

ENDPOINTS = ("get_data", "data", "data_from_cache")


def _endpoint(name: str) -> ast.FunctionDef:
    tree = ast.parse(API_SOURCE.read_text(encoding="utf-8"))
    for class_node in ast.walk(tree):
        if (
            isinstance(class_node, ast.ClassDef)
            and class_node.name == "ChartDataRestApi"
        ):
            for node in class_node.body:
                if isinstance(node, ast.FunctionDef) and node.name == name:
                    return node
    raise AssertionError(f"ChartDataRestApi.{name} not found in {API_SOURCE}")


def _validation_try_block(func: ast.FunctionDef) -> ast.Try:
    """Return the ``try`` block that wraps ``command.validate()``."""
    for node in ast.walk(func):
        if not isinstance(node, ast.Try):
            continue
        for child in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if (
                isinstance(child, ast.Call)
                and isinstance(child.func, ast.Attribute)
                and child.func.attr == "validate"
                and isinstance(child.func.value, ast.Name)
                and child.func.value.id == "command"
            ):
                return node
    raise AssertionError(f"no try block around command.validate() in {func.name}")


def _returns_403(handler: ast.ExceptHandler) -> bool:
    for node in ast.walk(handler):
        if (
            isinstance(node, ast.Return)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "response_403"
        ):
            return True
    return False


@pytest.mark.parametrize("name", ENDPOINTS)
def test_security_exception_is_mapped_to_403(name: str) -> None:
    handlers = [
        handler
        for handler in _validation_try_block(_endpoint(name)).handlers
        if isinstance(handler, ast.ExceptHandler)
        and isinstance(handler.type, ast.Name)
        and handler.type.id == "SupersetSecurityException"
    ]

    assert handlers, (
        f"ChartDataRestApi.{name} does not catch SupersetSecurityException; "
        "the endpoint would return 500 instead of 403"
    )
    assert all(_returns_403(handler) for handler in handlers)


@pytest.mark.parametrize("name", ENDPOINTS)
def test_openapi_docstring_documents_403(name: str) -> None:
    docstring = ast.get_docstring(_endpoint(name)) or ""

    assert "403:" in docstring
