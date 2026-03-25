from __future__ import annotations

from pathlib import Path

import streamlit as st

from quantumnet.gui.core.config import normalize_custom_filename


def setup_page() -> None:
    st.set_page_config(page_title="QuantumNet GUI", layout="wide", initial_sidebar_state="expanded")
    st.markdown(
        """
        <style>
        div[data-testid="stNumberInput"] input:invalid,
        div[data-testid="stTextInput"] input:invalid {
            border: 2px solid #2563eb !important;
            box-shadow: 0 0 0 1px #2563eb !important;
        }
        section[data-testid="stSidebar"] * {
            text-align: left !important;
        }
        div[data-testid="stForm"] * {
            text-align: left !important;
        }
        button[kind="primary"] {
            background-color: #2563eb !important;
            border-color: #2563eb !important;
        }
        button[kind="primary"]:hover {
            background-color: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
        }
        button[kind="secondary"] {
            color: #1d4ed8 !important;
            border-color: #2563eb !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def config_selector(default_config_path: Path) -> Path:
    mode = st.radio(
        "Config source",
        ["Default", "Custom"],
        key="qn_config_mode",
        horizontal=True,
    )

    if mode == "Default":
        return default_config_path

    if "qn_custom_filename" not in st.session_state:
        st.session_state["qn_custom_filename"] = "custom_config.yaml"

    custom_name_input = st.text_input(
        "Filename",
        key="qn_custom_filename",
        help="File saved in the same folder as default_config.yaml.",
    )
    custom_name = normalize_custom_filename(custom_name_input)
    return (default_config_path.parent / custom_name).resolve()

