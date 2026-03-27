from __future__ import annotations

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import networkx as nx

from ..exceptions import TopologyError


def _to_int(value: Any, field_name: str) -> int:
    """Convert values to int with a clear topology error message."""
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise TopologyError(f"Invalid value for {field_name}: {value!r}.") from exc


class BaseTopology(ABC):
    """Base class for all topology implementations."""

    @property
    def name(self) -> str:
        return self.__class__.__name__.removesuffix("Topology")

    @abstractmethod
    def build_graph(self) -> nx.Graph:
        """Build and return a networkx graph representing the topology."""


class LineTopology(BaseTopology):
    def __init__(self, num_hosts: Any) -> None:
        n = _to_int(num_hosts, "num_hosts")
        if n < 1:
            raise TopologyError("Line topology requires num_hosts >= 1.")
        self.num_hosts = n

    def build_graph(self) -> nx.Graph:
        return nx.path_graph(self.num_hosts)


class RingTopology(BaseTopology):
    def __init__(self, num_hosts: Any) -> None:
        n = _to_int(num_hosts, "num_hosts")
        if n < 1:
            raise TopologyError("Ring topology requires num_hosts >= 1.")
        self.num_hosts = n

    def build_graph(self) -> nx.Graph:
        return nx.cycle_graph(self.num_hosts)


class GridTopology(BaseTopology):
    def __init__(self, rows: Any, cols: Any) -> None:
        r = _to_int(rows, "rows")
        c = _to_int(cols, "cols")
        if r < 1 or c < 1:
            raise TopologyError("Grid topology requires rows >= 1 and cols >= 1.")
        self.rows = r
        self.cols = c

    def build_graph(self) -> nx.Graph:
        return nx.grid_2d_graph(self.rows, self.cols)


class StarTopology(BaseTopology):
    def __init__(self, num_hosts: Any) -> None:
        n = _to_int(num_hosts, "num_hosts")
        if n < 1:
            raise TopologyError("Star topology requires num_hosts >= 1.")
        self.num_hosts = n

    def build_graph(self) -> nx.Graph:
        # networkx.star_graph(n) creates n+1 nodes with node 0 as center.
        return nx.star_graph(self.num_hosts - 1)


class JsonTopology(BaseTopology):
    """Topology loaded from a JSON file or inline JSON-like object.

    Supported formats:
      1) {"hosts": [{"id": "n1", "name": "Alice", "connections": ["n2"]}, ...]}
      2) {"hosts": [{"name": "A", "connections": ["B"]}, ...]}
      3) [{"name": "A", "connections": ["B"]}, ...]
      4) {"A": ["B", "C"], "B": ["A"], ...}
    """

    def __init__(self, source: Any, base_dir: str | Path | None = None) -> None:
        self.source = source
        self.base_dir = Path(base_dir).resolve() if base_dir is not None else None

    def _resolve_path(self, raw_path: str | Path) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path

        if self.base_dir is not None:
            candidate = (self.base_dir / path).resolve()
            if candidate.exists():
                return candidate

        return path.resolve()

    def _load_spec(self) -> Any:
        if isinstance(self.source, (dict, list)):
            return self.source

        if isinstance(self.source, (str, Path)):
            path = self._resolve_path(self.source)
            if not path.exists():
                raise TopologyError(f"JSON topology file not found: {path}")
            try:
                with path.open("r", encoding="utf-8") as file:
                    return json.load(file)
            except json.JSONDecodeError as exc:
                raise TopologyError(f"Invalid JSON topology file: {path}") from exc

        raise TopologyError(
            "JSON topology source must be a file path, dict or list."
        )

    @staticmethod
    def _extract_hosts(spec: Any) -> list[dict[str, Any]]:
        if isinstance(spec, list):
            hosts = spec
        elif isinstance(spec, dict) and "hosts" in spec:
            hosts = spec["hosts"]
        elif isinstance(spec, dict):
            hosts = [{"name": key, "connections": value} for key, value in spec.items()]
        else:
            raise TopologyError("Invalid JSON topology format.")

        if not isinstance(hosts, list) or not hosts:
            raise TopologyError("JSON topology must define at least one host.")
        return hosts

    def build_graph(self) -> nx.Graph:
        spec = self._load_spec()
        hosts = self._extract_hosts(spec)

        graph = nx.Graph()
        declared_ids: set[str] = set()
        declared_names: set[str] = set()
        name_to_id: dict[str, str] = {}
        parsed_hosts: list[tuple[str, str, list[str]]] = []

        for index, host in enumerate(hosts):
            if not isinstance(host, dict):
                raise TopologyError(
                    f"Invalid host entry at index {index}: expected object."
                )
            if "id" in host:
                host_id = str(host["id"]).strip()
                if not host_id:
                    raise TopologyError(f"Host entry at index {index} has an empty id.")
            elif "name" in host:
                host_id = str(host["name"]).strip()
                if not host_id:
                    raise TopologyError(f"Host entry at index {index} has an empty name.")
            else:
                raise TopologyError(
                    f"Host entry at index {index} must define 'id' or 'name'."
                )

            if host_id in declared_ids:
                raise TopologyError(f"Duplicate host id in JSON topology: {host_id!r}")
            declared_ids.add(host_id)

            host_name = str(host.get("name", host_id)).strip()
            if not host_name:
                raise TopologyError(f"Host entry at index {index} has an empty name.")
            if host_name in declared_names:
                raise TopologyError(f"Duplicate host name in JSON topology: {host_name!r}")
            declared_names.add(host_name)
            name_to_id[host_name] = host_id

            connections = host.get("connections", [])
            if connections is None:
                connections = []
            if not isinstance(connections, (list, tuple)):
                raise TopologyError(
                    f"Host {host_name!r} has invalid 'connections'. Expected a list."
                )
            parsed_hosts.append((host_id, host_name, [str(target).strip() for target in connections]))
            graph.add_node(host_id, label=host_name)

        for host_id, host_name, connections in parsed_hosts:
            for target in connections:
                if not target:
                    raise TopologyError(
                        f"Host {host_name!r} has an empty connection reference."
                    )

                # Prefer direct host id references; fallback to unique host name.
                resolved_target = target
                if resolved_target not in declared_ids:
                    resolved_target = name_to_id.get(target, "")
                if not resolved_target:
                    raise TopologyError(
                        f"Host {host_name!r} references unknown connection {target!r}."
                    )
                graph.add_edge(host_id, resolved_target)

        return graph


def available_topologies() -> tuple[str, ...]:
    return ("Grid", "Line", "Ring", "Star", "Json")


def create_topology(
    topology_name: Any,
    *args: Any,
    base_dir: str | Path | None = None,
) -> BaseTopology:
    raw_name = str(topology_name).strip()
    if not raw_name:
        raise TopologyError("Topology name cannot be empty.")

    normalized = raw_name.lower().replace("-", "").replace("_", "")

    if normalized in {"line", "linetopology"}:
        if len(args) != 1:
            raise TopologyError("Line topology requires one argument.")
        return LineTopology(args[0])

    if normalized in {"ring", "ringtopology"}:
        if len(args) != 1:
            raise TopologyError("Ring topology requires one argument.")
        return RingTopology(args[0])

    if normalized in {"grid", "gridtopology"}:
        if len(args) != 2:
            raise TopologyError("Grid topology requires two arguments.")
        return GridTopology(args[0], args[1])

    if normalized in {"star", "startopology"}:
        if len(args) != 1:
            raise TopologyError("Star topology requires one argument.")
        return StarTopology(args[0])

    if normalized in {"json", "jsontopology", "custom"}:
        if len(args) != 1:
            raise TopologyError(
                "Json topology requires one argument: file path or inline object."
            )
        return JsonTopology(args[0], base_dir=base_dir)

    available = ", ".join(available_topologies())
    raise TopologyError(f"Unknown topology '{raw_name}'. Available: {available}.")
