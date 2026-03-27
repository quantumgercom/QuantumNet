from __future__ import annotations

import streamlit as st

from quantumnet.metadata import REPOSITORY_URL, SIMULATOR_VERSION


def render_version_page() -> None:
    st.title("Version")
    st.markdown(f"- **Simulator version**: `{SIMULATOR_VERSION}`")
    st.markdown(f"- **Repository**: {REPOSITORY_URL}")
