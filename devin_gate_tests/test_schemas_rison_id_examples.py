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
"""Regression tests for rison id-array Swagger examples (fix d41f0fe, #42265).

``get_export_ids_schema`` / ``get_delete_ids_schema`` / ``get_fav_star_ids_schema``
had no ``example``, so Swagger UI's "Try it out" pre-filled an empty/invalid
value for the rison query parameter and the request 400'd.

The gate environment installs pytest only, so the schema dicts are read from
source with ``ast`` instead of importing the ``superset`` package.
"""

import ast
from pathlib import Path
from typing import Any

import pytest

SUPERSET_ROOT = Path(__file__).resolve().parents[1] / "superset"

SCHEMA_TARGETS = [
    ("annotation_layers/annotations/schemas.py", "get_delete_ids_schema"),
    ("annotation_layers/schemas.py", "get_delete_ids_schema"),
    ("charts/schemas.py", "get_delete_ids_schema"),
    ("charts/schemas.py", "get_export_ids_schema"),
    ("charts/schemas.py", "get_fav_star_ids_schema"),
    ("css_templates/schemas.py", "get_delete_ids_schema"),
    ("dashboards/schemas.py", "get_delete_ids_schema"),
    ("dashboards/schemas.py", "get_export_ids_schema"),
    ("dashboards/schemas.py", "get_fav_star_ids_schema"),
    ("databases/schemas.py", "get_export_ids_schema"),
    ("datasets/schemas.py", "get_delete_ids_schema"),
    ("datasets/schemas.py", "get_export_ids_schema"),
    ("queries/saved_queries/schemas.py", "get_delete_ids_schema"),
    ("queries/saved_queries/schemas.py", "get_export_ids_schema"),
    ("reports/schemas.py", "get_delete_ids_schema"),
    ("row_level_security/schemas.py", "get_delete_ids_schema"),
    ("tasks/schemas.py", "get_delete_ids_schema"),
    ("themes/schemas.py", "get_delete_ids_schema"),
    ("themes/schemas.py", "get_export_ids_schema"),
]

ITEM_TYPES = {"integer": int, "string": str}


def _load_schema(relative_path: str, name: str) -> dict[str, Any]:
    """Evaluate the literal dict assigned to ``name`` in a schemas module."""
    source_path = SUPERSET_ROOT / relative_path
    tree = ast.parse(source_path.read_text(), filename=str(source_path))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return ast.literal_eval(node.value)
    raise AssertionError(f"{relative_path} does not define {name}")


@pytest.mark.parametrize(
    "relative_path, name",
    SCHEMA_TARGETS,
    ids=[f"{path}:{name}" for path, name in SCHEMA_TARGETS],
)
def test_id_rison_schema_declares_swagger_example(
    relative_path: str, name: str
) -> None:
    schema = _load_schema(relative_path, name)
    example = schema.get("example")
    message = (
        f"superset/{relative_path}:{name} is missing a non-empty 'example'; "
        "Swagger UI cannot pre-fill a valid rison array without it"
    )
    assert isinstance(example, list), message
    assert example, message
    item_type = ITEM_TYPES[schema["items"]["type"]]
    assert all(isinstance(item, item_type) for item in example)
