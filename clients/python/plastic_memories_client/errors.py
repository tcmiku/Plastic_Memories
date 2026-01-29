from __future__ import annotations

from typing import Any, Optional


class PlasticMemoriesError(Exception):
    def __init__(self, code: str, message: str, details: Any = None, request_id: Optional[str] = None, status_code: Optional[int] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details
        self.request_id = request_id
        self.status_code = status_code


class PlasticMemoriesTransportError(Exception):
    def __init__(self, original: Exception, request_id: Optional[str] = None):
        super().__init__(str(original))
        self.original = original
        self.request_id = request_id


class PlasticMemoriesProtocolError(Exception):
    def __init__(self, message: str, request_id: Optional[str] = None):
        super().__init__(message)
        self.request_id = request_id
