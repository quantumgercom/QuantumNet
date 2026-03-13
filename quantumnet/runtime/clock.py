import heapq


class Clock:
    """
    Discrete-event simulation clock for quantum network simulation.

    Responsible for:
    - Tracking the current timeslot (now)
    - Scheduling future events via schedule()
    - Advancing time event-by-event via step(), or draining via run()
    - Recording events via emit(), without advancing time
    - Maintaining a complete event history (history)
    """

    def __init__(self):
        self._timeslot = 0
        self._history = []
        self._event_queue = []   # min-heap: (timeslot, seq, callback, kwargs)
        self._seq = 0            # FIFO tie-breaker for same-timeslot events
        self._event_callbacks = {}
        self._wildcard_callbacks = []  # listen_all() subscribers

    @property
    def now(self) -> int:
        """Return the current timeslot."""
        return self._timeslot

    @property
    def history(self) -> list:
        """Return the complete event history."""
        return list(self._history)

    def schedule(self, delay: int, callback, **kwargs):
        """
        Schedule a callback to fire at (now + delay) timeslots.

        Same-timeslot events execute in FIFO order (by insertion sequence).

        Args:
            delay (int): Non-negative number of timeslots from now.
            callback: Callable to invoke. Signature: callback(**kwargs).
            **kwargs: Arguments forwarded to the callback.

        Raises:
            ValueError: If delay is negative.
        """
        if delay < 0:
            raise ValueError("delay must be >= 0")
        time = self._timeslot + delay
        heapq.heappush(self._event_queue, (time, self._seq, callback, kwargs))
        self._seq += 1

    def step(self) -> bool:
        """
        Advance time to the next scheduled timeslot and execute ALL events
        at that timeslot in FIFO order.

        Events scheduled during execution at the same timeslot (delay=0)
        are also processed within this step.

        Returns:
            bool: True if at least one event was processed, False if queue empty.
        """
        if not self._event_queue:
            return False

        next_time = self._event_queue[0][0]
        self._timeslot = next_time

        while self._event_queue and self._event_queue[0][0] == next_time:
            _, _, callback, kwargs = heapq.heappop(self._event_queue)
            callback(**kwargs)

        return True

    def run(self):
        """
        Process all scheduled events until the queue is empty.
        Equivalent to calling step() repeatedly.
        """
        while self.step():
            pass

    def emit(self, event_name: str, **data):
        """
        Record an event in the history at the current timeslot, without advancing time.
        Fires callbacks registered for the specific event and all wildcard listeners.

        Args:
            event_name (str): Event name.
            **data: Additional event data.
        """
        entry = {'timeslot': self._timeslot, 'event': event_name, **data}
        self._history.append(entry)
        if event_name in self._event_callbacks:
            for callback in self._event_callbacks[event_name]:
                callback(self, **data)
        for callback in self._wildcard_callbacks:
            callback(self, event_name, **data)

    def on(self, event_name: str, callback):

        """
        Register a callback to react to a specific event.
        The callback receives the clock and event data: callback(clock, **data).

        Args:
            event_name (str): Event name.
            callback: Function to be called when the event occurs.
        """
        if event_name not in self._event_callbacks:
            self._event_callbacks[event_name] = []
        self._event_callbacks[event_name].append(callback)

    def listen_all(self, callback):
        """
        Register a callback that fires on every emitted event.
        Signature: callback(clock, event_name, **data).

        Unlike on(), this callback receives the event name explicitly
        as a positional argument so a single handler can process all events.

        Args:
            callback: Function with signature callback(clock, event_name, **data).
        """
        self._wildcard_callbacks.append(callback)
