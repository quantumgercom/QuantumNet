import csv
import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..runtime import Clock

# Types that are safe to write directly to CSV
_PRIMITIVE_TYPES = (int, float, str, bool, type(None))

# Priority-ordered keys for well-known columns
_SOURCE_KEYS = ('alice', 'host_id', 'node', 'src')
_TARGET_KEYS = ('bob', 'target', 'dst')
_VALUE_KEYS  = ('fidelity', 'key_length', 'delivered', 'requested',
                'count', 'num_qubits', 'attempt', 'size', 'route_len')


def _safe_primitive(v):
    """Return v if primitive, str(v) if tuple/list, otherwise None."""
    if isinstance(v, _PRIMITIVE_TYPES):
        return v
    if isinstance(v, (tuple, list)):
        return str(v)
    return None


class MetricsCollector:
    """Event-driven CSV metrics collector for QuantumNet simulations.

    Opens the output file exactly once at construction (O(1) memory usage
    per event) and writes one row for every clock event.  Only primitive
    values are ever retained — no object references are stored, preventing
    memory leaks.

    Schema
    ------
    clock_tick  : simulation timeslot of the event
    event_type  : name of the event (e.g. 'epr_created', 'qubit_teleported')
    source_node : originating host/node id (extracted from alice/host_id/node)
    target_node : destination host/node id (extracted from bob/target)
    value       : primary numeric payload (fidelity, count, key_length, …)
    details     : JSON string containing all remaining primitive fields

    Usage
    -----
    As a standalone object::

        collector = MetricsCollector(clock, "results.csv")
        clock.run()
        collector.close()

    As a context manager (preferred — guarantees close on exception)::

        with MetricsCollector(clock, "results.csv"):
            clock.run()
    """

    COLUMNS = ('clock_tick', 'event_type', 'source_node', 'target_node',
               'value', 'details')

    def __init__(self, clock: 'Clock', file_path: str):
        self._file = open(file_path, 'w', newline='', encoding='utf-8')
        self._writer = csv.writer(self._file)
        self._writer.writerow(self.COLUMNS)
        clock.listen_all(self._record)

    # ------------------------------------------------------------------
    # Internal callback — must never store object references
    # ------------------------------------------------------------------

    def _record(self, clock: 'Clock', event_name: str, **data):
        tick = clock.now

        # Convert every value to a CSV-safe primitive; discard object refs
        safe = {}
        for k, v in data.items():
            p = _safe_primitive(v)
            if p is not None or v is None:
                safe[k] = p

        # Extract well-known columns by priority (removes them from safe)
        source  = next((safe.pop(k) for k in _SOURCE_KEYS if k in safe), None)
        target  = next((safe.pop(k) for k in _TARGET_KEYS if k in safe), None)
        value   = next((safe.pop(k) for k in _VALUE_KEYS  if k in safe), None)
        details = json.dumps(safe, separators=(',', ':')) if safe else None

        self._writer.writerow([tick, event_name, source, target, value, details])

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self):
        """Flush OS buffers and close the CSV file."""
        self._file.flush()
        self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
