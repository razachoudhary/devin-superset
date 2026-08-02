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
"""Regression tests for modify_url_query (fix 9617155, upstream #35936).

The gate environment installs pytest only, so ``superset.utils.urls`` is loaded
directly from source with a stub ``flask`` module instead of importing the
``superset`` package.
"""

import importlib.util
import sys
import types
from pathlib import Path

URLS_SOURCE = Path(__file__).resolve().parents[1] / "superset" / "utils" / "urls.py"


def _load_urls_module():
    flask_stub = types.ModuleType("flask")
    flask_stub.current_app = None
    flask_stub.has_request_context = lambda: False
    flask_stub.url_for = lambda *args, **kwargs: ""
    original_flask = sys.modules.get("flask")
    sys.modules["flask"] = flask_stub
    try:
        spec = importlib.util.spec_from_file_location(
            "devin_gate_tests._superset_utils_urls", URLS_SOURCE
        )
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    finally:
        if original_flask is None:
            del sys.modules["flask"]
        else:
            sys.modules["flask"] = original_flask
    return module


modify_url_query = _load_urls_module().modify_url_query


def test_modify_url_query_preserves_repeated_and_blank_params() -> None:
    test_url = modify_url_query(
        "http://localhost:9000/explore/?a=1&a=2&b=&c=3",
        a=[4, 5],
    )

    assert test_url == "http://localhost:9000/explore/?a=4&a=5&b=&c=3"


def test_modify_url_query_appends_new_params_after_existing_params() -> None:
    test_url = modify_url_query(
        "http://localhost:9000/explore/?a=1&a=2&b=&c=3",
        d=7,
    )

    assert test_url == "http://localhost:9000/explore/?a=1&a=2&b=&c=3&d=7"


def test_modify_url_query_preserves_standard_url_encoding_for_list_values() -> None:
    test_url = modify_url_query(
        "http://localhost:9000/explore/?existing=ok",
        tag=["alpha value", "beta/value"],
    )

    assert (
        test_url
        == "http://localhost:9000/explore/?existing=ok&tag=alpha%20value&tag=beta/value"
    )
