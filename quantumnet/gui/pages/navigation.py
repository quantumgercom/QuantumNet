from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import streamlit as st

from quantumnet.gui.pages.parameters import render_parameters_page
from quantumnet.gui.pages.version import render_version_page


def _render_sidebar_brand() -> None:
    logo_path = (Path(__file__).resolve().parents[1] / "img" / "logoquantumnet.png").resolve()
    logo_base64 = base64.b64encode(logo_path.read_bytes()).decode("utf-8")

    with st.sidebar:
        st.markdown(
            f"""
            <div class="qn-sidebar-brand-wrap" style="margin:0;padding:20px 0 0 0;">
                <div class="qn-sidebar-brand-row" style="margin:0 0 20px 0;padding:0 2rem 0 0;">
                    <img src="data:image/png;base64,{logo_base64}" alt="QuantumNet logo" width="40" height="40" />
                    <span>QuantumNet</span>
                </div>
                <div class="qn-sidebar-divider" style="margin:0 0 20px 0;"></div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def build_navigation(config_path: Path) -> Any:
    def _parameters_page() -> None:
        render_parameters_page(config_path)

    def _version_page() -> None:
        render_version_page(config_path)

    _render_sidebar_brand()

    return st.navigation(
        [
            st.Page(_parameters_page, title="Parameters", url_path="parameters", default=True),
            st.Page(_version_page, title="Version", url_path="version"),
        ],
        position="sidebar",
    )
