from __future__ import annotations

from pathlib import Path
from typing import Any

import streamlit as st

from quantumnet.gui.pages.parameters import render_parameters_page
from quantumnet.gui.pages.version import render_version_page


def build_navigation(config_path: Path) -> Any:
    def _parameters_page() -> None:
        render_parameters_page(config_path)

    def _version_page() -> None:
        render_version_page(config_path)

    return st.navigation(
        [
            st.Page(_parameters_page, title="Parameters", url_path="parameters", default=True),
            st.Page(_version_page, title="Version", url_path="version"),
        ],
        position="sidebar",
    )
