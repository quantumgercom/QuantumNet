from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import networkx as nx
import streamlit as st

from quantumnet.exceptions import TopologyError
from quantumnet.gui.topology.io import load_topology_json, save_topology_json
from quantumnet.topology.topologies import JsonTopology

try:
    from streamlit_flow import streamlit_flow
    from streamlit_flow.elements import StreamlitFlowEdge, StreamlitFlowNode
    from streamlit_flow.state import StreamlitFlowState
except Exception:  # pragma: no cover - runtime dependency guard
    streamlit_flow = None
    StreamlitFlowEdge = None
    StreamlitFlowNode = None
    StreamlitFlowState = None


def _sort_node_ids(values: list[str]) -> list[str]:
    def _key(value: str) -> tuple[int, int | str]:
        stripped = value.strip()
        if stripped.isdigit():
            return (0, int(stripped))
        return (1, stripped.lower())

    return sorted(values, key=_key)


def _editor_id(topology_path: Path) -> str:
    digest = hashlib.sha1(str(topology_path).encode("utf-8")).hexdigest()[:10]
    return digest


def _state_key(topology_path: Path) -> str:
    return f"qn_topology_flow_state_{_editor_id(topology_path)}"


def _canvas_key(topology_path: Path) -> str:
    return f"qn_topology_flow_canvas_{_editor_id(topology_path)}"


def _pending_source_key(topology_path: Path) -> str:
    return f"qn_topology_pending_source_{_editor_id(topology_path)}"


def _processed_event_timestamp_key(topology_path: Path) -> str:
    return f"qn_topology_processed_ts_{_editor_id(topology_path)}"


def _base_node_style() -> dict[str, Any]:
    return {
        "width": 56,
        "height": 56,
        "borderRadius": "50%",
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "center",
        "padding": 0,
        "fontWeight": 600,
        "border": "2px solid #64748b",
        "background": "#ffffff",
        "transition": "border-color 120ms ease, box-shadow 120ms ease",
    }


def _node_style(is_pending_source: bool) -> dict[str, Any]:
    style = _base_node_style()
    if is_pending_source:
        style["border"] = "2px solid #2563eb"
        style["boxShadow"] = "0 0 0 4px rgba(37, 99, 235, 0.25)"
    return style


def _default_node(node_id: str, position: tuple[float, float]) -> Any:
    return StreamlitFlowNode(
        id=node_id,
        pos=position,
        data={"content": node_id},
        node_type="default",
        source_position="bottom",
        target_position="top",
        connectable=False,
        selectable=True,
        deletable=True,
        draggable=True,
        style=_node_style(False),
    )


def _build_default_state() -> Any:
    return StreamlitFlowState(nodes=[_default_node("0", (0.0, 0.0))], edges=[])


def _state_from_json_spec(spec: Any) -> Any:
    graph = JsonTopology(spec).build_graph()
    if graph.number_of_nodes() == 0:
        return _build_default_state()

    positions = nx.spring_layout(graph, seed=42, scale=1.0)
    ordered_nodes = _sort_node_ids([str(node) for node in graph.nodes])
    nodes: list[Any] = []
    for node_id in ordered_nodes:
        x, y = positions.get(node_id, (0.0, 0.0))
        nodes.append(_default_node(node_id, (float(x) * 350.0, float(y) * 260.0)))

    edges: list[Any] = []
    for source, target in graph.edges:
        source_id = str(source)
        target_id = str(target)
        edge_id = f"{source_id}->{target_id}"
        edges.append(
            StreamlitFlowEdge(
                id=edge_id,
                source=source_id,
                target=target_id,
                deletable=True,
            )
        )
    return StreamlitFlowState(nodes=nodes, edges=edges)


def _state_to_json_spec(state: Any) -> dict[str, Any]:
    node_ids: list[str] = []
    seen: set[str] = set()
    for node in state.nodes:
        node_id = str(node.id).strip()
        if not node_id or node_id in seen:
            continue
        seen.add(node_id)
        node_ids.append(node_id)

    if not node_ids:
        raise TopologyError("Topology editor needs at least one node before saving.")

    ordered_nodes = _sort_node_ids(node_ids)
    neighbors: dict[str, set[str]] = {node_id: set() for node_id in ordered_nodes}

    for edge in state.edges:
        source = str(edge.source).strip()
        target = str(edge.target).strip()
        if source not in neighbors or target not in neighbors:
            continue
        neighbors[source].add(target)
        if source != target:
            neighbors[target].add(source)

    hosts = []
    for node_id in ordered_nodes:
        connections = _sort_node_ids(list(neighbors[node_id]))
        hosts.append({"name": node_id, "connections": connections})
    return {"hosts": hosts}


def _canonical_edge_pair(source: str, target: str) -> tuple[str, str]:
    ordered = _sort_node_ids([source, target])
    return ordered[0], ordered[1]


def _edge_exists_undirected(state: Any, source: str, target: str) -> bool:
    pair = _canonical_edge_pair(source, target)
    for edge in state.edges:
        edge_source = str(edge.source).strip()
        edge_target = str(edge.target).strip()
        if not edge_source or not edge_target:
            continue
        if _canonical_edge_pair(edge_source, edge_target) == pair:
            return True
    return False


def _next_edge_id(state: Any, source: str, target: str) -> str:
    base = f"{source}<->{target}"
    existing = {str(edge.id).strip() for edge in state.edges}
    if base not in existing:
        return base

    suffix = 1
    while True:
        candidate = f"{base}#{suffix}"
        if candidate not in existing:
            return candidate
        suffix += 1


def _add_edge_by_click(state: Any, source: str, target: str) -> bool:
    source_id = source.strip()
    target_id = target.strip()
    if not source_id or not target_id or source_id == target_id:
        return False
    if _edge_exists_undirected(state, source_id, target_id):
        return False

    left, right = _canonical_edge_pair(source_id, target_id)
    state.edges.append(
        StreamlitFlowEdge(
            id=_next_edge_id(state, left, right),
            source=left,
            target=right,
            deletable=True,
        )
    )
    return True


def _node_ids(state: Any) -> set[str]:
    return {str(node.id).strip() for node in state.nodes if str(node.id).strip()}


def _apply_pending_source_style(state: Any, pending_source: str | None) -> None:
    highlighted = pending_source.strip() if pending_source else None
    for node in state.nodes:
        node_id = str(node.id).strip()
        node.style = _node_style(highlighted is not None and node_id == highlighted)


def _handle_click_to_connect(topology_path: Path) -> None:
    current_state_key = _state_key(topology_path)
    pending_source_key = _pending_source_key(topology_path)
    processed_ts_key = _processed_event_timestamp_key(topology_path)

    state = st.session_state[current_state_key]
    ids = _node_ids(state)

    pending_source = st.session_state.get(pending_source_key)
    if pending_source not in ids:
        pending_source = None
        st.session_state[pending_source_key] = None

    event_timestamp = int(getattr(state, "timestamp", 0) or 0)
    if event_timestamp == st.session_state.get(processed_ts_key):
        _apply_pending_source_style(state, pending_source)
        return
    st.session_state[processed_ts_key] = event_timestamp

    selected_raw = getattr(state, "selected_id", None)
    selected_id = str(selected_raw).strip() if selected_raw is not None else ""
    if selected_id not in ids:
        _apply_pending_source_style(state, pending_source)
        return

    if pending_source is None:
        st.session_state[pending_source_key] = selected_id
    elif selected_id == pending_source:
        st.session_state[pending_source_key] = None
    else:
        _add_edge_by_click(state, pending_source, selected_id)
        st.session_state[pending_source_key] = None

    _apply_pending_source_style(state, st.session_state.get(pending_source_key))
    st.rerun()


def _next_node_id(existing_ids: list[str]) -> str:
    if not existing_ids:
        return "0"
    if all(node_id.isdigit() for node_id in existing_ids):
        return str(max(int(node_id) for node_id in existing_ids) + 1)

    candidate = 1
    existing = set(existing_ids)
    while True:
        value = f"node_{candidate}"
        if value not in existing:
            return value
        candidate += 1


def _add_node(state: Any) -> None:
    existing_ids = [str(node.id).strip() for node in state.nodes]
    new_id = _next_node_id([node_id for node_id in existing_ids if node_id])
    new_index = len(existing_ids)
    x = float((new_index % 4) * 240)
    y = float((new_index // 4) * 140)
    state.nodes.append(_default_node(new_id, (x, y)))


def _load_state_from_disk(topology_path: Path) -> tuple[Any, str | None]:
    if not topology_path.exists():
        return _build_default_state(), (
            "Topology file not found yet. Start from node `0` and save to create it."
        )

    try:
        spec = load_topology_json(topology_path)
    except json.JSONDecodeError:
        return _build_default_state(), "Invalid JSON file. Starting from a clean editor state."

    if spec is None:
        return _build_default_state(), (
            "Topology file not found yet. Start from node `0` and save to create it."
        )

    try:
        return _state_from_json_spec(spec), None
    except TopologyError:
        return _build_default_state(), (
            "Could not parse the topology JSON with QuantumNet rules. Starting from a clean editor state."
        )


def render_topology_editor(topology_path: Path) -> None:
    if streamlit_flow is None:
        st.error(
            "Missing dependency `streamlit-flow-component`. "
            "Install requirements and restart the app."
        )
        return

    current_state_key = _state_key(topology_path)
    pending_source_key = _pending_source_key(topology_path)
    processed_ts_key = _processed_event_timestamp_key(topology_path)
    info_message: str | None = None

    if current_state_key not in st.session_state:
        loaded_state, info_message = _load_state_from_disk(topology_path)
        st.session_state[current_state_key] = loaded_state
    if pending_source_key not in st.session_state:
        st.session_state[pending_source_key] = None
    if processed_ts_key not in st.session_state:
        st.session_state[processed_ts_key] = None

    pending_source = st.session_state.get(pending_source_key)
    if pending_source and pending_source not in _node_ids(st.session_state[current_state_key]):
        pending_source = None
        st.session_state[pending_source_key] = None

    _apply_pending_source_style(st.session_state[current_state_key], pending_source)

    actions_col, canvas_col = st.columns([1, 6], gap="small")
    with actions_col:
        if st.button("Add node", use_container_width=True):
            _add_node(st.session_state[current_state_key])
            st.session_state[processed_ts_key] = None

        if st.button("Reload from disk", use_container_width=True):
            loaded_state, info_message = _load_state_from_disk(topology_path)
            st.session_state[current_state_key] = loaded_state
            st.session_state[pending_source_key] = None
            st.session_state[processed_ts_key] = None
            pending_source = None

        if pending_source:
            st.info(
                f"Node `{pending_source}` selected. Click another node to create an edge, "
                "or click the same node to cancel."
            )
        else:
            st.caption(
                "Click one node (blue) and then another to connect."
            )

        if info_message:
            st.info(info_message)

    with canvas_col:
        updated_state = streamlit_flow(
            _canvas_key(topology_path),
            st.session_state[current_state_key],
            height=640,
            fit_view=True,
            show_controls=True,
            show_minimap=False,
            allow_new_edges=False,
            animate_new_edges=False,
            get_node_on_click=True,
            enable_pane_menu=True,
            enable_node_menu=True,
            enable_edge_menu=True,
        )
    if updated_state is not None:
        st.session_state[current_state_key] = updated_state

    _handle_click_to_connect(topology_path)

    save_ready = True
    try:
        spec = _state_to_json_spec(st.session_state[current_state_key])
    except TopologyError as exc:
        save_ready = False
        spec = {}
        st.warning(str(exc))

    st.subheader("JSON preview")
    st.json(spec)

    if st.button("Save topology JSON", type="primary", disabled=not save_ready):
        save_topology_json(topology_path, spec)
        st.success(f"Topology saved to `{topology_path}`")
    st.caption(
        "After saving this file, use Topology type = Json in Parameters and set the same JSON filename."
    )
