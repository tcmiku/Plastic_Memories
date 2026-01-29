from ..interfaces import EventSink


class NoopEventSink:
    def emit(self, event: str, payload: dict) -> None:
        return None
