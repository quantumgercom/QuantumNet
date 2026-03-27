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


def _canvas_frame_key(topology_path: Path) -> str:
    return f"qn_topology_flow_frame_v3_{_editor_id(topology_path)}"


def _pending_source_key(topology_path: Path) -> str:
    return f"qn_topology_pending_source_{_editor_id(topology_path)}"


def _selected_node_key(topology_path: Path) -> str:
    return f"qn_topology_selected_node_{_editor_id(topology_path)}"


def _selected_edge_key(topology_path: Path) -> str:
    return f"qn_topology_selected_edge_{_editor_id(topology_path)}"


def _last_node_click_key(topology_path: Path) -> str:
    return f"qn_topology_last_node_click_{_editor_id(topology_path)}"


def _node_selection_set_ts_key(topology_path: Path) -> str:
    return f"qn_topology_node_selection_set_ts_{_editor_id(topology_path)}"


def _processed_event_timestamp_key(topology_path: Path) -> str:
    return f"qn_topology_processed_ts_{_editor_id(topology_path)}"


def _inject_canvas_frame_style(frame_key: str) -> None:
    st.markdown(
        f"""
        <style>
        .st-key-{frame_key} {{
            color: inherit !important;
            border: 2px solid currentColor !important;
            border-radius: 8px !important;
            overflow: hidden;
            padding: 0 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


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
                edge_type="straight",
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
            edge_type="straight",
            deletable=True,
        )
    )
    return True


def _node_ids(state: Any) -> set[str]:
    return {str(node.id).strip() for node in state.nodes if str(node.id).strip()}


def _edge_ids(state: Any) -> set[str]:
    return {str(edge.id).strip() for edge in state.edges if str(edge.id).strip()}


def _apply_pending_source_style(state: Any, pending_source: str | None) -> None:
    highlighted = pending_source.strip() if pending_source else None
    for node in state.nodes:
        node_id = str(node.id).strip()
        node.style = _node_style(highlighted is not None and node_id == highlighted)


def _enforce_straight_edges(state: Any) -> None:
    for edge in state.edges:
        edge.edge_type = "straight"


def _apply_selected_edge_style(state: Any, selected_edge_id: str | None) -> None:
    highlighted = selected_edge_id.strip() if selected_edge_id else None
    for edge in state.edges:
        edge_id = str(edge.id).strip()
        if highlighted is not None and edge_id == highlighted:
            edge.style = {"stroke": "#2563eb", "strokeWidth": 3}
        else:
            edge.style = {}


def _clear_component_selection(state: Any) -> None:
    state.selected_id = None
    for node in state.nodes:
        node.selected = False
    for edge in state.edges:
        edge.selected = False


def _delete_node(state: Any, node_id: str) -> bool:
    target_id = node_id.strip()
    if not target_id:
        return False

    initial_nodes = len(state.nodes)
    state.nodes = [node for node in state.nodes if str(node.id).strip() != target_id]
    if len(state.nodes) == initial_nodes:
        return False

    state.edges = [
        edge
        for edge in state.edges
        if str(edge.source).strip() != target_id and str(edge.target).strip() != target_id
    ]
    return True


def _delete_edge(state: Any, edge_id: str) -> bool:
    target_id = edge_id.strip()
    if not target_id:
        return False

    initial_edges = len(state.edges)
    state.edges = [edge for edge in state.edges if str(edge.id).strip() != target_id]
    return len(state.edges) != initial_edges


def _selected_id_candidates(state: Any) -> list[str]:
    selected_raw = getattr(state, "selected_id", None)
    selected_id = str(selected_raw).strip() if selected_raw is not None else ""
    if not selected_id:
        return []

    candidates: list[str] = [selected_id]
    for prefix in ("reactflow__node-", "reactflow__edge-"):
        if selected_id.startswith(prefix):
            candidates.append(selected_id[len(prefix):])

    deduped: list[str] = []
    for value in candidates:
        if value and value not in deduped:
            deduped.append(value)
    return deduped


def _selected_node_id(state: Any, ids: set[str]) -> str | None:
    for candidate in _selected_id_candidates(state):
        if candidate in ids:
            return candidate

    for node in state.nodes:
        if getattr(node, "selected", False):
            node_id = str(node.id).strip()
            if node_id in ids:
                return node_id
    return None


def _selected_edge_id(state: Any, ids: set[str]) -> str | None:
    for candidate in _selected_id_candidates(state):
        if candidate in ids:
            return candidate

    for edge in state.edges:
        if getattr(edge, "selected", False):
            edge_id = str(edge.id).strip()
            if edge_id in ids:
                return edge_id
    return None


def _handle_canvas_interaction(topology_path: Path) -> None:
    current_state_key = _state_key(topology_path)
    pending_source_key = _pending_source_key(topology_path)
    selected_node_state_key = _selected_node_key(topology_path)
    selected_edge_state_key = _selected_edge_key(topology_path)
    last_node_click_state_key = _last_node_click_key(topology_path)
    node_selection_set_ts_state_key = _node_selection_set_ts_key(topology_path)
    processed_ts_key = _processed_event_timestamp_key(topology_path)
    double_click_ms = 450
    ignore_auto_null_event_ms = 1000

    state = st.session_state[current_state_key]
    node_ids = _node_ids(state)
    edge_ids = _edge_ids(state)

    pending_source = st.session_state.get(pending_source_key)
    if pending_source not in node_ids:
        pending_source = None
        st.session_state[pending_source_key] = None
    selected_node_state = st.session_state.get(selected_node_state_key)
    if selected_node_state not in node_ids:
        st.session_state[selected_node_state_key] = None

    event_timestamp = int(getattr(state, "timestamp", 0) or 0)
    if event_timestamp == st.session_state.get(processed_ts_key):
        _apply_pending_source_style(state, pending_source)
        return
    st.session_state[processed_ts_key] = event_timestamp

    selected_node_id = _selected_node_id(state, node_ids)
    selected_edge_id = _selected_edge_id(state, edge_ids)

    if selected_node_id is None:
        if selected_edge_id is not None:
            st.session_state[selected_edge_state_key] = selected_edge_id
            st.session_state[selected_node_state_key] = None
            st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
            st.session_state[node_selection_set_ts_state_key] = 0
            if pending_source is not None:
                st.session_state[pending_source_key] = None
                _apply_pending_source_style(state, None)
            _clear_component_selection(state)
            st.rerun()
        has_active_node_selection = st.session_state.get(selected_node_state_key) is not None
        if pending_source is not None or has_active_node_selection:
            selected_set_ts = int(st.session_state.get(node_selection_set_ts_state_key) or 0)
            if (
                has_active_node_selection
                and selected_set_ts > 0
                and 0 <= (event_timestamp - selected_set_ts) <= ignore_auto_null_event_ms
            ):
                _apply_pending_source_style(state, pending_source)
                return
            st.session_state[pending_source_key] = None
            st.session_state[selected_node_state_key] = None
            st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
            st.session_state[node_selection_set_ts_state_key] = 0
            _clear_component_selection(state)
            _apply_pending_source_style(state, None)
            st.rerun()
        _apply_pending_source_style(state, pending_source)
        return

    st.session_state[selected_edge_state_key] = None

    last_click = st.session_state.get(last_node_click_state_key, {"id": None, "ts": 0})
    last_id = str(last_click.get("id") or "")
    last_ts = int(last_click.get("ts") or 0)
    is_double_click = (
        last_id == selected_node_id and 0 < (event_timestamp - last_ts) <= double_click_ms
    )

    if pending_source is not None:
        st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
        st.session_state[selected_node_state_key] = selected_node_id
        st.session_state[node_selection_set_ts_state_key] = event_timestamp

        if selected_node_id == pending_source:
            st.session_state[pending_source_key] = None
        else:
            _add_edge_by_click(state, pending_source, selected_node_id)
            st.session_state[pending_source_key] = None

        _clear_component_selection(state)
        _apply_pending_source_style(state, st.session_state.get(pending_source_key))
        st.rerun()

    if not is_double_click:
        st.session_state[last_node_click_state_key] = {
            "id": selected_node_id,
            "ts": event_timestamp,
        }
        _clear_component_selection(state)
        _apply_pending_source_style(state, st.session_state.get(pending_source_key))
        st.rerun()

    st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
    st.session_state[selected_node_state_key] = selected_node_id
    st.session_state[node_selection_set_ts_state_key] = event_timestamp

    st.session_state[pending_source_key] = selected_node_id

    _clear_component_selection(state)
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
    selected_node_state_key = _selected_node_key(topology_path)
    selected_edge_state_key = _selected_edge_key(topology_path)
    last_node_click_state_key = _last_node_click_key(topology_path)
    node_selection_set_ts_state_key = _node_selection_set_ts_key(topology_path)
    processed_ts_key = _processed_event_timestamp_key(topology_path)
    info_message: str | None = None

    if current_state_key not in st.session_state:
        loaded_state, info_message = _load_state_from_disk(topology_path)
        st.session_state[current_state_key] = loaded_state
    if pending_source_key not in st.session_state:
        st.session_state[pending_source_key] = None
    if selected_node_state_key not in st.session_state:
        st.session_state[selected_node_state_key] = None
    if selected_edge_state_key not in st.session_state:
        st.session_state[selected_edge_state_key] = None
    if last_node_click_state_key not in st.session_state:
        st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
    if node_selection_set_ts_state_key not in st.session_state:
        st.session_state[node_selection_set_ts_state_key] = 0
    if processed_ts_key not in st.session_state:
        st.session_state[processed_ts_key] = None

    current_node_ids = _node_ids(st.session_state[current_state_key])

    pending_source = st.session_state.get(pending_source_key)
    if pending_source and pending_source not in current_node_ids:
        pending_source = None
        st.session_state[pending_source_key] = None

    selected_node = st.session_state.get(selected_node_state_key)
    if selected_node not in current_node_ids:
        selected_node = None
        st.session_state[selected_node_state_key] = None
        st.session_state[node_selection_set_ts_state_key] = 0

    current_edge_ids = _edge_ids(st.session_state[current_state_key])
    selected_edge = st.session_state.get(selected_edge_state_key)
    if selected_edge not in current_edge_ids:
        selected_edge = None
        st.session_state[selected_edge_state_key] = None

    if selected_edge is not None and pending_source is not None:
        pending_source = None
        st.session_state[pending_source_key] = None
    if selected_edge is not None and selected_node is not None:
        selected_node = None
        st.session_state[selected_node_state_key] = None
        st.session_state[node_selection_set_ts_state_key] = 0

    _apply_pending_source_style(st.session_state[current_state_key], pending_source)
    _enforce_straight_edges(st.session_state[current_state_key])
    _apply_selected_edge_style(st.session_state[current_state_key], selected_edge)

    actions_col, canvas_col = st.columns([1, 6], gap="small")
    with actions_col:
        if st.button("Add node", use_container_width=True):
            _add_node(st.session_state[current_state_key])
            st.session_state[processed_ts_key] = None

        if st.button("Reload from disk", use_container_width=True):
            loaded_state, info_message = _load_state_from_disk(topology_path)
            st.session_state[current_state_key] = loaded_state
            st.session_state[pending_source_key] = None
            st.session_state[selected_node_state_key] = None
            st.session_state[selected_edge_state_key] = None
            st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
            st.session_state[node_selection_set_ts_state_key] = 0
            st.session_state[processed_ts_key] = None
            pending_source = None
            selected_node = None
            selected_edge = None

        delete_node_enabled = selected_node is not None
        delete_edge_enabled = selected_edge is not None

        delete_node_button_clicked = st.button(
            "Delete node",
            type="primary" if delete_node_enabled else "secondary",
            use_container_width=True,
            disabled=not delete_node_enabled,
        )
        delete_edge_button_clicked = st.button(
            "Delete connection",
            type="primary" if delete_edge_enabled else "secondary",
            use_container_width=True,
            disabled=not delete_edge_enabled,
        )

        if delete_node_button_clicked:
            current_state = st.session_state[current_state_key]
            current_timestamp = int(getattr(current_state, "timestamp", 0) or 0)
            node_to_delete = selected_node
            if node_to_delete is not None and _delete_node(current_state, node_to_delete):
                st.session_state[pending_source_key] = None
                st.session_state[selected_node_state_key] = None
                st.session_state[selected_edge_state_key] = None
                st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
                st.session_state[node_selection_set_ts_state_key] = 0
                st.session_state[processed_ts_key] = current_timestamp
                _clear_component_selection(current_state)
                _apply_pending_source_style(current_state, None)
                _apply_selected_edge_style(current_state, None)
                st.rerun()

        if delete_edge_button_clicked:
            current_state = st.session_state[current_state_key]
            current_timestamp = int(getattr(current_state, "timestamp", 0) or 0)
            if selected_edge is not None and _delete_edge(current_state, selected_edge):
                st.session_state[selected_edge_state_key] = None
                st.session_state[node_selection_set_ts_state_key] = 0
                st.session_state[processed_ts_key] = current_timestamp
                _clear_component_selection(current_state)
                _apply_selected_edge_style(current_state, None)
                st.rerun()

        save_button_slot = st.empty()

        if pending_source:
            st.info(
                f"Connection mode on node `{pending_source}`. "
                "Click another node to create an edge (double click also works), "
                "or click the same node to cancel."
            )
        elif selected_node:
            st.info(
                f"Node `{selected_node}` selected. Double click this node to start a new connection, "
                "or click `Delete node` to remove it."
            )
        elif selected_edge:
            st.info(
                f"Connection `{selected_edge}` selected. Click `Delete connection` to remove it."
            )
        else:
            st.caption(
                "Single click only moves/arranges nodes. Double click a node to select/connect. "
                "Select a node to enable `Delete node` or select a connection to enable `Delete connection`."
            )

        if info_message:
            st.info(info_message)

    with canvas_col:
        frame_key = _canvas_frame_key(topology_path)
        _inject_canvas_frame_style(frame_key)
        with st.container(key=frame_key):
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
                get_edge_on_click=True,
                enable_pane_menu=False,
                enable_node_menu=False,
                enable_edge_menu=False,
            )
    if updated_state is not None:
        st.session_state[current_state_key] = updated_state
        _enforce_straight_edges(st.session_state[current_state_key])
        _apply_selected_edge_style(
            st.session_state[current_state_key],
            _selected_edge_id(
                st.session_state[current_state_key],
                _edge_ids(st.session_state[current_state_key]),
            ),
        )

    _handle_canvas_interaction(topology_path)

    save_ready = True
    try:
        spec = _state_to_json_spec(st.session_state[current_state_key])
    except TopologyError as exc:
        save_ready = False
        spec = {}
        st.warning(str(exc))

    st.subheader("JSON preview")
    st.json(spec)

    with save_button_slot:
        if st.button(
            "Save JSON",
            type="primary",
            disabled=not save_ready,
            use_container_width=True,
        ):
            save_topology_json(topology_path, spec)
            st.success(f"Topology saved to `{topology_path}`")

    st.caption(
        "After saving this file, use Topology type = Json in Parameters and set the same JSON filename."
    )
