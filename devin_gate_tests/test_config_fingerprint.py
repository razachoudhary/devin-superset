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
"""Regression tests for config fingerprinting (fix e0d0eb6, upstream #42154).

The gate environment installs pytest only, so ``_config_fingerprint`` is
extracted from ``superset/config.py`` by source and executed on its own rather
than importing the ``superset`` package.
"""

import ast
import hashlib
from pathlib import Path
from typing import Callable, cast

CONFIG_SOURCE = Path(__file__).resolve().parents[1] / "superset" / "config.py"


def _load_config_fingerprint() -> Callable[[bytes | None], str]:
    funcs = [
        node
        for node in ast.parse(CONFIG_SOURCE.read_text()).body
        if isinstance(node, ast.FunctionDef) and node.name == "_config_fingerprint"
    ]
    assert funcs, "superset/config.py no longer defines _config_fingerprint"
    func = funcs[0]
    namespace = {"hashlib": hashlib}
    exec(  # noqa: S102
        compile(ast.Module(body=[func], type_ignores=[]), str(CONFIG_SOURCE), "exec"),
        namespace,
    )
    return cast(Callable[[bytes | None], str], namespace["_config_fingerprint"])


def test_config_fingerprint_is_a_12_char_md5_prefix() -> None:
    source = b"SQLALCHEMY_DATABASE_URI = 'sqlite://'\n"

    digest = _load_config_fingerprint()(source)

    assert digest == hashlib.md5(source).hexdigest()[:12]  # noqa: S324
    assert len(digest) == 12


def test_config_fingerprint_differs_for_different_bytes() -> None:
    fingerprint = _load_config_fingerprint()

    assert fingerprint(b"FOO = 1\n") != fingerprint(b"FOO = 2\n")


def test_config_fingerprint_reports_unreadable_source() -> None:
    assert _load_config_fingerprint()(None) == "unreadable"


def test_config_path_load_executes_the_bytes_it_read() -> None:
    """The override module is built from bytes read once, not re-read by the loader."""
    blocks = [
        node
        for node in ast.parse(CONFIG_SOURCE.read_text()).body
        if isinstance(node, ast.If) and "CONFIG_PATH_ENV_VAR" in ast.dump(node.test)
    ]
    assert blocks, "superset/config.py no longer has a SUPERSET_CONFIG_PATH branch"
    block_source = ast.dump(blocks[0])

    assert "config_source" in block_source
    assert "exec_module" not in block_source
