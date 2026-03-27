from __future__ import annotations

from pathlib import Path

import streamlit as st

from quantumnet.gui.core.config import normalize_custom_filename


def setup_page() -> None:
    st.set_page_config(page_title="QuantumNet GUI", layout="wide", initial_sidebar_state="expanded")
    st.markdown(
        """
        <style>
        :root {
            --qn-brand-font-size: 1.25rem;
            --qn-sidebar-gap: 20px;
        }
        div[data-testid="stNumberInput"] input:invalid,
        div[data-testid="stTextInput"] input:invalid {
            border: 2px solid #2563eb !important;
            box-shadow: 0 0 0 1px #2563eb !important;
        }
        section[data-testid="stSidebar"] * {
            text-align: left !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] {
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarContent"] > div {
            margin: 0 !important;
            padding: 0 !important;
            gap: 0 !important;
        }
        section[data-testid="stSidebar"] > div:first-child {
            display: flex;
            flex-direction: column;
            position: relative;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"] {
            order: 0;
            position: absolute;
            top: var(--qn-sidebar-gap);
            right: 0;
            z-index: 2;
            min-height: 0;
            height: auto;
            margin: 0 !important;
            padding: 0 !important;
            background: transparent !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarHeader"] button {
            margin: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] {
            order: 1;
            display: flex;
            flex-direction: column;
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] > div {
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] div[data-testid="stVerticalBlock"] {
            gap: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarUserContent"] div[data-testid="stElementContainer"] {
            margin: 0 !important;
            padding: 0 !important;
        }
        section[data-testid="stSidebar"] .qn-sidebar-brand-wrap {
            order: 1;
            margin: 0 !important;
            padding: var(--qn-sidebar-gap) 0 0 0 !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {
            order: 2;
            margin-top: 0 !important;
            padding-top: 0 !important;
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
            border: 0 !important;
            box-shadow: none !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] > div {
            margin: 0 !important;
            padding: 0 !important;
            border: 0 !important;
            box-shadow: none !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] ul {
            margin-top: 0 !important;
            padding-top: 0 !important;
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        section[data-testid="stSidebar"] .qn-sidebar-brand-row {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            min-height: 2rem;
            margin: 0 0 var(--qn-sidebar-gap) 0 !important;
            padding: 0 2rem 0 0;
        }
        section[data-testid="stSidebar"] .qn-sidebar-brand-row span {
            font-size: var(--qn-brand-font-size);
            font-weight: 700;
            line-height: 1.2;
        }
        section[data-testid="stSidebar"] .qn-sidebar-brand-link {
            color: inherit !important;
            text-decoration: none !important;
        }
        section[data-testid="stSidebar"] .qn-sidebar-brand-logo-link {
            display: inline-flex;
            align-items: center;
            line-height: 0;
        }
        section[data-testid="stSidebar"] .qn-sidebar-brand-name-link {
            font-size: var(--qn-brand-font-size);
            font-weight: 700;
            line-height: 1.2;
        }
        section[data-testid="stSidebar"] .qn-sidebar-brand-link:hover {
            opacity: 0.85;
        }
        section[data-testid="stSidebar"] .qn-sidebar-divider {
            border-bottom: 1px solid rgba(128, 128, 128, 0.35);
            margin: 0 0 var(--qn-sidebar-gap) 0 !important;
        }
        section[data-testid="stSidebar"] hr {
            display: none !important;
        }
        section[data-testid="stSidebar"] div[data-testid="stSidebarNav"]::before,
        section[data-testid="stSidebar"] div[data-testid="stSidebarNav"]::after,
        section[data-testid="stSidebar"] div[data-testid="stSidebarContent"]::before,
        section[data-testid="stSidebar"] div[data-testid="stSidebarContent"]::after {
            display: none !important;
            content: none !important;
            border: 0 !important;
            box-shadow: none !important;
        }
        div[data-testid="stForm"] * {
            text-align: left !important;
        }
        button[kind="secondary"] {
            background-color: #2563eb !important;
            border-color: #2563eb !important;
            color: #ffffff !important;
        }
        button[kind="secondary"]:hover {
            background-color: #1d4ed8 !important;
            border-color: #1d4ed8 !important;
            color: #ffffff !important;
        }
        button[kind="secondary"]:active {
            background-color: #1e40af !important;
            border-color: #1e40af !important;
            color: #ffffff !important;
        }
        button[kind="primary"] {
            background-color: #16a34a !important;
            border-color: #16a34a !important;
            color: #ffffff !important;
        }
        button[kind="primary"]:hover {
            background-color: #15803d !important;
            border-color: #15803d !important;
            color: #ffffff !important;
        }
        button[kind="primary"]:active {
            background-color: #166534 !important;
            border-color: #166534 !important;
            color: #ffffff !important;
        }
        div[data-testid="stAppDeployButton"] {
            display: none;
        }
        div[data-testid="stDeployButton"] {
            display: none;
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
