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

import os
from unittest.mock import patch

from superset.app import create_app


class TestCreateAppIcon:
    """APP_ICON handling under a non-root app root in create_app."""

    @patch("superset.initialization.SupersetAppInitializer.init_app")
    def test_static_app_icon_is_prefixed_under_app_root(self, mock_init_app):
        """A "/static/..." APP_ICON is rewritten with STATIC_ASSETS_PREFIX
        (which defaults to the app root) so the brand logo resolves on
        subdirectory deployments instead of pointing at a bare "/static/"
        URL. Regression for the OAuth-login broken-logo bug (#38033)."""
        env = os.environ.copy()
        env.pop("SUPERSET_CONFIG", None)
        env["SUPERSET_APP_ROOT"] = "/myapp"
        with (
            patch.dict(os.environ, env, clear=True),
            patch(
                "superset.config.APP_ICON",
                "/static/assets/images/superset-logo-horiz.png",
                create=True,
            ),
        ):
            app = create_app()

        assert (
            app.config["APP_ICON"]
            == "/myapp/static/assets/images/superset-logo-horiz.png"
        )

    @patch("superset.initialization.SupersetAppInitializer.init_app")
    def test_non_static_app_icon_is_left_untouched(self, mock_init_app):
        """An APP_ICON that is not a "/static/..." path (e.g. an absolute
        CDN URL) must not be prefixed, so a fully-qualified logo URL keeps
        resolving as-is."""
        env = os.environ.copy()
        env.pop("SUPERSET_CONFIG", None)
        env["SUPERSET_APP_ROOT"] = "/myapp"
        with (
            patch.dict(os.environ, env, clear=True),
            patch(
                "superset.config.APP_ICON",
                "https://cdn.example.com/brand/logo.png",
                create=True,
            ),
        ):
            app = create_app()

        assert app.config["APP_ICON"] == "https://cdn.example.com/brand/logo.png"
