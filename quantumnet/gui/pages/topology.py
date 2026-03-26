from __future__ import annotations

import streamlit as st

from quantumnet.gui.topology import (
    default_topology_path,
    render_topology_editor,
    topology_file_selector,
)


def render_topology_page() -> None:
    st.title("Topology")
    topology_path = topology_file_selector(default_topology_path())
    st.caption(f"Topology file: `{topology_path}`")
    render_topology_editor(topology_path)
