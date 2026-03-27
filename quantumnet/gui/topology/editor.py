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


def _selected_node_key(topology_path: Path) -> str:
    return f"qn_topology_selected_node_{_editor_id(topology_path)}"


def _selected_edge_key(topology_path: Path) -> str:
    return f"qn_topology_selected_edge_{_editor_id(topology_path)}"


def _last_node_click_key(topology_path: Path) -> str:
    return f"qn_topology_last_node_click_{_editor_id(topology_path)}"


def _processed_event_timestamp_key(topology_path: Path) -> str:
    return f"qn_topology_processed_ts_{_editor_id(topology_path)}"


def _suppress_next_null_event_key(topology_path: Path) -> str:
    return f"qn_topology_suppress_next_null_event_{_editor_id(topology_path)}"


def _save_button_frame_key(topology_path: Path) -> str:
    return f"qn_topology_save_button_frame_{_editor_id(topology_path)}"


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


def _inject_green_button_style(frame_key: str) -> None:
    st.markdown(
        f"""
        <style>
        .st-key-{frame_key} button {{
            background: #16a34a !important;
            color: #ffffff !important;
            border-color: #15803d !important;
        }}
        .st-key-{frame_key} button:hover {{
            background: #15803d !important;
            border-color: #166534 !important;
        }}
        .st-key-{frame_key} button:disabled {{
            background: #86efac !important;
            color: #14532d !important;
            border-color: #4ade80 !important;
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


def _node_connections(state: Any, node_id: str) -> list[str]:
    target_id = node_id.strip()
    if not target_id:
        return []

    neighbors: set[str] = set()
    for edge in state.edges:
        source = str(edge.source).strip()
        target = str(edge.target).strip()
        if source == target_id and target:
            neighbors.add(target)
        elif target == target_id and source:
            neighbors.add(source)
    return _sort_node_ids(list(neighbors))


def _delete_connection_between_nodes(state: Any, node_a: str, node_b: str) -> bool:
    left, right = _canonical_edge_pair(node_a.strip(), node_b.strip())
    if not left or not right:
        return False

    initial_edges = len(state.edges)
    state.edges = [
        edge
        for edge in state.edges
        if _canonical_edge_pair(str(edge.source).strip(), str(edge.target).strip()) != (left, right)
    ]
    return len(state.edges) != initial_edges


def _find_edge(state: Any, edge_id: str) -> Any | None:
    target_id = edge_id.strip()
    if not target_id:
        return None
    for edge in state.edges:
        if str(edge.id).strip() == target_id:
            return edge
    return None


def _reindex_edges(state: Any) -> None:
    used_ids: set[str] = set()
    for edge in state.edges:
        source = str(edge.source).strip()
        target = str(edge.target).strip()
        if not source or not target:
            continue
        left, right = _canonical_edge_pair(source, target)
        base = f"{left}<->{right}"
        candidate = base
        suffix = 1
        while candidate in used_ids:
            candidate = f"{base}#{suffix}"
            suffix += 1
        used_ids.add(candidate)
        edge.source = left
        edge.target = right
        edge.id = candidate
        edge.edge_type = "straight"


def _rename_node(state: Any, current_node_id: str, new_node_id: str) -> bool:
    old_id = current_node_id.strip()
    updated_id = new_node_id.strip()
    if not old_id or not updated_id:
        raise TopologyError("Node ID cannot be empty.")
    if old_id == updated_id:
        return False

    existing = _node_ids(state)
    if updated_id in existing:
        raise TopologyError(f"Node `{updated_id}` already exists.")

    target_node: Any | None = None
    for node in state.nodes:
        if str(node.id).strip() == old_id:
            target_node = node
            break
    if target_node is None:
        raise TopologyError(f"Node `{old_id}` was not found in the current topology.")

    target_node.id = updated_id
    target_node.data = {"content": updated_id}

    for edge in state.edges:
        if str(edge.source).strip() == old_id:
            edge.source = updated_id
        if str(edge.target).strip() == old_id:
            edge.target = updated_id

    _reindex_edges(state)
    return True


def _update_edge(state: Any, edge_id: str, source: str, target: str) -> str:
    source_id = source.strip()
    target_id = target.strip()
    if not source_id or not target_id:
        raise TopologyError("Connection endpoints cannot be empty.")
    if source_id == target_id:
        raise TopologyError("Connection source and target must be different nodes.")

    valid_nodes = _node_ids(state)
    if source_id not in valid_nodes or target_id not in valid_nodes:
        raise TopologyError("Selected connection endpoints must be existing nodes.")

    edge = _find_edge(state, edge_id)
    if edge is None:
        raise TopologyError(f"Connection `{edge_id}` was not found.")

    new_pair = _canonical_edge_pair(source_id, target_id)
    for other in state.edges:
        other_id = str(other.id).strip()
        if other_id == str(edge.id).strip():
            continue
        other_source = str(other.source).strip()
        other_target = str(other.target).strip()
        if not other_source or not other_target:
            continue
        if _canonical_edge_pair(other_source, other_target) == new_pair:
            raise TopologyError(
                f"Connection `{new_pair[0]} <-> {new_pair[1]}` already exists."
            )

    edge.source = source_id
    edge.target = target_id
    _reindex_edges(state)
    return str(edge.id).strip()


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
    selected_node_state_key = _selected_node_key(topology_path)
    selected_edge_state_key = _selected_edge_key(topology_path)
    last_node_click_state_key = _last_node_click_key(topology_path)
    processed_ts_key = _processed_event_timestamp_key(topology_path)
    suppress_next_null_event_key = _suppress_next_null_event_key(topology_path)
    double_click_ms = 450

    state = st.session_state[current_state_key]
    node_ids = _node_ids(state)
    edge_ids = _edge_ids(state)
    selected_node_state = st.session_state.get(selected_node_state_key)
    if selected_node_state not in node_ids:
        selected_node_state = None
        st.session_state[selected_node_state_key] = None
    selected_edge_state = st.session_state.get(selected_edge_state_key)
    if selected_edge_state not in edge_ids:
        selected_edge_state = None
        st.session_state[selected_edge_state_key] = None

    previous_processed_timestamp = st.session_state.get(processed_ts_key)
    event_timestamp = int(getattr(state, "timestamp", 0) or 0)
    if event_timestamp == previous_processed_timestamp:
        _apply_pending_source_style(state, selected_node_state)
        _apply_selected_edge_style(state, selected_edge_state)
        return
    st.session_state[processed_ts_key] = event_timestamp

    clicked_node_id = _selected_node_id(state, node_ids)
    clicked_edge_id = _selected_edge_id(state, edge_ids)

    if clicked_edge_id is not None:
        changed = (
            st.session_state.get(selected_edge_state_key) != clicked_edge_id
            or st.session_state.get(selected_node_state_key) is not None
        )
        st.session_state[selected_edge_state_key] = clicked_edge_id
        st.session_state[selected_node_state_key] = None
        st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
        st.session_state[suppress_next_null_event_key] = False
        _clear_component_selection(state)
        _apply_pending_source_style(state, None)
        _apply_selected_edge_style(state, clicked_edge_id)
        if changed:
            st.rerun()
        return

    if clicked_node_id is not None:
        active_source = st.session_state.get(selected_node_state_key)
        if active_source is not None:
            if clicked_node_id != active_source:
                _add_edge_by_click(state, active_source, clicked_node_id)
                st.session_state[selected_node_state_key] = None
                st.session_state[selected_edge_state_key] = None
                st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
                st.session_state[suppress_next_null_event_key] = False
                _clear_component_selection(state)
                _apply_pending_source_style(state, None)
                _apply_selected_edge_style(state, None)
                st.rerun()

            st.session_state[last_node_click_state_key] = {
                "id": active_source,
                "ts": event_timestamp,
            }
            st.session_state[suppress_next_null_event_key] = True
            _clear_component_selection(state)
            _apply_pending_source_style(state, active_source)
            _apply_selected_edge_style(state, None)
            st.rerun()

        last_click = st.session_state.get(last_node_click_state_key, {"id": None, "ts": 0})
        last_id = str(last_click.get("id") or "")
        last_ts = int(last_click.get("ts") or 0)
        is_double_click = (
            last_id == clicked_node_id and 0 < (event_timestamp - last_ts) <= double_click_ms
        )
        if is_double_click:
            st.session_state[selected_node_state_key] = clicked_node_id
            st.session_state[selected_edge_state_key] = None
            st.session_state[last_node_click_state_key] = {
                "id": clicked_node_id,
                "ts": event_timestamp,
            }
            st.session_state[suppress_next_null_event_key] = True
            _clear_component_selection(state)
            _apply_pending_source_style(state, clicked_node_id)
            _apply_selected_edge_style(state, None)
            st.rerun()

        st.session_state[last_node_click_state_key] = {
            "id": clicked_node_id,
            "ts": event_timestamp,
        }
        _apply_pending_source_style(state, st.session_state.get(selected_node_state_key))
        _apply_selected_edge_style(state, st.session_state.get(selected_edge_state_key))
        return

    active_source = st.session_state.get(selected_node_state_key)
    if active_source is not None:
        if bool(st.session_state.get(suppress_next_null_event_key)):
            st.session_state[suppress_next_null_event_key] = False
            _apply_pending_source_style(state, active_source)
            _apply_selected_edge_style(state, st.session_state.get(selected_edge_state_key))
            return

        st.session_state[selected_node_state_key] = None
        st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
        st.session_state[suppress_next_null_event_key] = False
        _clear_component_selection(state)
        _apply_pending_source_style(state, None)
        _apply_selected_edge_style(state, st.session_state.get(selected_edge_state_key))
        st.rerun()

    _clear_component_selection(state)
    _apply_pending_source_style(state, None)
    _apply_selected_edge_style(state, st.session_state.get(selected_edge_state_key))


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
    selected_node_state_key = _selected_node_key(topology_path)
    selected_edge_state_key = _selected_edge_key(topology_path)
    last_node_click_state_key = _last_node_click_key(topology_path)
    processed_ts_key = _processed_event_timestamp_key(topology_path)
    suppress_next_null_event_key = _suppress_next_null_event_key(topology_path)
    info_message: str | None = None

    if current_state_key not in st.session_state:
        loaded_state, info_message = _load_state_from_disk(topology_path)
        st.session_state[current_state_key] = loaded_state
    if selected_node_state_key not in st.session_state:
        st.session_state[selected_node_state_key] = None
    if selected_edge_state_key not in st.session_state:
        st.session_state[selected_edge_state_key] = None
    if last_node_click_state_key not in st.session_state:
        st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
    if processed_ts_key not in st.session_state:
        st.session_state[processed_ts_key] = None
    if suppress_next_null_event_key not in st.session_state:
        st.session_state[suppress_next_null_event_key] = False

    current_node_ids = _node_ids(st.session_state[current_state_key])

    selected_node = st.session_state.get(selected_node_state_key)
    if selected_node not in current_node_ids:
        selected_node = None
        st.session_state[selected_node_state_key] = None

    current_edge_ids = _edge_ids(st.session_state[current_state_key])
    selected_edge = st.session_state.get(selected_edge_state_key)
    if selected_edge not in current_edge_ids:
        selected_edge = None
        st.session_state[selected_edge_state_key] = None

    if selected_edge is not None and selected_node is not None:
        selected_node = None
        st.session_state[selected_node_state_key] = None

    _apply_pending_source_style(st.session_state[current_state_key], selected_node)
    _enforce_straight_edges(st.session_state[current_state_key])
    _apply_selected_edge_style(st.session_state[current_state_key], selected_edge)

    save_button_frame_key = _save_button_frame_key(topology_path)
    _inject_green_button_style(save_button_frame_key)

    save_button_slot: Any | None = None
    actions_col, canvas_col = st.columns([2, 5], gap="medium")
    with actions_col:
        if st.button("Add Node", type="primary", use_container_width=True):
            _add_node(st.session_state[current_state_key])
            st.session_state[processed_ts_key] = None
            st.rerun()

        if st.button("Reload from disk", type="primary", use_container_width=True):
            loaded_state, info_message = _load_state_from_disk(topology_path)
            st.session_state[current_state_key] = loaded_state
            st.session_state[selected_node_state_key] = None
            st.session_state[selected_edge_state_key] = None
            st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
            st.session_state[processed_ts_key] = None
            st.session_state[suppress_next_null_event_key] = False
            selected_node = None
            selected_edge = None
            st.rerun()

        save_button_slot = st.empty()

        st.markdown("### Selection actions")
        current_state = st.session_state[current_state_key]
        sorted_node_ids = _sort_node_ids(list(_node_ids(current_state)))

        if selected_node:
            st.info(
                f"Node `{selected_node}` selected as source. Click another node to connect, "
                "click outside to cancel, or use Apply changes below."
            )
            current_connections = _node_connections(current_state, selected_node)
            current_connections_set = set(current_connections)
            add_connection_candidates = [
                node_id
                for node_id in sorted_node_ids
                if node_id != selected_node and node_id not in current_connections_set
            ]
            new_connection_placeholder = "(none)"
            form_key = f"qn_topology_node_actions_{_editor_id(topology_path)}_{selected_node}"
            with st.form(key=form_key):
                new_node_id = st.text_input(
                    "Node ID",
                    value=selected_node,
                    help="Rename the selected node.",
                )
                kept_connections = st.multiselect(
                    "Current connections",
                    options=current_connections,
                    default=current_connections,
                    help="Keep checked connections. Uncheck to remove.",
                )
                new_connection_target = st.selectbox(
                    "Add new connection",
                    options=[new_connection_placeholder, *add_connection_candidates],
                    help="Only nodes not already connected are listed.",
                )
                delete_on_apply = st.checkbox(
                    "Delete this node on apply",
                    value=False,
                    help="If checked, this node and all its connections will be removed.",
                )
                apply_changes = st.form_submit_button(
                    "Apply changes",
                    type="primary",
                    use_container_width=True,
                )

            if apply_changes:
                desired_node_id = new_node_id.strip()
                existing_node_ids = _node_ids(current_state)
                if delete_on_apply:
                    if _delete_node(current_state, selected_node):
                        st.session_state[selected_node_state_key] = None
                        st.session_state[selected_edge_state_key] = None
                        st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
                        st.session_state[processed_ts_key] = None
                        st.session_state[suppress_next_null_event_key] = False
                        _clear_component_selection(current_state)
                        _apply_pending_source_style(current_state, None)
                        _apply_selected_edge_style(current_state, None)
                        st.rerun()
                    else:
                        st.warning("Could not delete the selected node.")
                elif not desired_node_id:
                    st.warning("Node ID cannot be empty.")
                elif desired_node_id != selected_node and desired_node_id in existing_node_ids:
                    st.warning(f"Node `{desired_node_id}` already exists.")
                else:
                    keep_set = set(kept_connections)
                    for neighbor in current_connections:
                        if neighbor not in keep_set:
                            _delete_connection_between_nodes(current_state, selected_node, neighbor)

                    if new_connection_target != new_connection_placeholder:
                        _add_edge_by_click(current_state, selected_node, new_connection_target)

                    if desired_node_id != selected_node:
                        _rename_node(current_state, selected_node, desired_node_id)

                    st.session_state[selected_node_state_key] = None
                    st.session_state[selected_edge_state_key] = None
                    st.session_state[last_node_click_state_key] = {"id": None, "ts": 0}
                    st.session_state[processed_ts_key] = None
                    st.session_state[suppress_next_null_event_key] = False
                    _clear_component_selection(current_state)
                    _apply_pending_source_style(current_state, None)
                    _apply_selected_edge_style(current_state, None)
                    st.rerun()
        elif selected_edge:
            st.info(f"Connection `{selected_edge}` selected.")
            if st.button("Delete connection", type="primary", use_container_width=True):
                if _delete_edge(current_state, selected_edge):
                    st.session_state[selected_edge_state_key] = None
                    st.session_state[processed_ts_key] = None
                    st.session_state[suppress_next_null_event_key] = False
                    _clear_component_selection(current_state)
                    _apply_selected_edge_style(current_state, None)
                    st.rerun()
        else:
            st.caption(
                "Double click a node to open node edit mode. Click one connection to show connection actions."
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
                height=560,
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

    with st.expander("JSON preview", expanded=False):
        st.json(spec)

    if save_button_slot is not None:
        with save_button_slot:
            with st.container(key=save_button_frame_key):
                if st.button(
                    "Save JSON",
                    type="secondary",
                    disabled=not save_ready,
                    use_container_width=True,
                ):
                    save_topology_json(topology_path, spec)
                    st.success(f"Topology saved to `{topology_path}`")
    else:
        with st.container(key=save_button_frame_key):
            if st.button(
                "Save JSON",
                type="secondary",
                disabled=not save_ready,
                use_container_width=True,
            ):
                save_topology_json(topology_path, spec)
                st.success(f"Topology saved to `{topology_path}`")

    st.caption(
        "After saving this file, use Topology type = Json in Parameters and set the same JSON filename."
    )
