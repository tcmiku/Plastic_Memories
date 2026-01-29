from ..interfaces import EventSink


class WebSocketEventSink:
    def __init__(self) -> None:
        self._listeners = []

    def emit(self, event: str, payload: dict) -> None:
        for listener in list(self._listeners):
            try:
                listener(event, payload)
            except Exception:
                continue

    def register(self, fn) -> None:
        self._listeners.append(fn)
