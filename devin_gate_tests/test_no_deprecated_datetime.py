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
"""Conformance test for the datetime.utcnow()/utcfromtimestamp() sweep (034823e).

Both calls are deprecated since Python 3.12 and scheduled for removal. The
sources are read as text so this test imports nothing from ``superset``.
"""

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SWEPT_TREES = ("superset/utils", "superset/common")

DEPRECATED_CALL = re.compile(r"\butc(?:now|fromtimestamp)\s*\(")


def _offenders() -> list[str]:
    found = []
    for tree in SWEPT_TREES:
        for path in sorted((REPO_ROOT / tree).rglob("*.py")):
            for lineno, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), start=1
            ):
                if DEPRECATED_CALL.search(line):
                    rel = path.relative_to(REPO_ROOT)
                    found.append(f"{rel}:{lineno}: {line.strip()}")
    return found


def test_swept_trees_exist() -> None:
    for tree in SWEPT_TREES:
        assert (REPO_ROOT / tree).is_dir(), f"missing source tree: {tree}"
    assert any((REPO_ROOT / tree).rglob("*.py") for tree in SWEPT_TREES)


def test_no_deprecated_utc_datetime_calls() -> None:
    offenders = _offenders()
    assert not offenders, (
        "Deprecated datetime.utcnow()/utcfromtimestamp() call sites found; use "
        "datetime.now(timezone.utc) / datetime.fromtimestamp(ts, tz=timezone.utc):\n"
        + "\n".join(offenders)
    )


def test_detector_matches_deprecated_forms() -> None:
    assert DEPRECATED_CALL.search("ts = datetime.utcnow()")
    assert DEPRECATED_CALL.search("datetime.utcfromtimestamp(epoch)")
    assert not DEPRECATED_CALL.search("datetime.now(timezone.utc)")
    assert not DEPRECATED_CALL.search("datetime.fromtimestamp(ts, tz=timezone.utc)")
