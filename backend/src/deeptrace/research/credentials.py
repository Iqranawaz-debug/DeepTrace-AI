"""Write-only provider key storage. Keys never reach SQLite, responses, logs or reports."""

import ctypes
import os
import re
import sys
from typing import Any, Protocol

ENV_NAMES = {"tavily": "TAVILY_API_KEY", "gemini": "GEMINI_API_KEY"}
KEY = re.compile(r"^[\x21-\x7e]{8,512}$")


class CredentialStore(Protocol):
    available: bool

    def get(self, provider: str) -> str | None: ...

    def put(self, provider: str, value: str) -> None: ...

    def delete(self, provider: str) -> None: ...


class MemoryCredentialStore:
    """Process-local store for tests."""

    available = True

    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    def get(self, provider: str) -> str | None:
        return self.values.get(provider)

    def put(self, provider: str, value: str) -> None:
        self.values[provider] = value

    def delete(self, provider: str) -> None:
        self.values.pop(provider, None)


class WindowsCredentialStore:
    """Windows Credential Manager through advapi32; no third-party keyring package."""

    available = sys.platform == "win32"

    def __init__(self, prefix: str = "DeepTraceAI/"):
        self.prefix = prefix

    @staticmethod
    def _api() -> tuple[Any, Any]:
        from ctypes import wintypes

        class Credential(ctypes.Structure):
            _fields_ = [
                ("Flags", wintypes.DWORD),
                ("Type", wintypes.DWORD),
                ("TargetName", wintypes.LPWSTR),
                ("Comment", wintypes.LPWSTR),
                ("LastWritten", wintypes.FILETIME),
                ("CredentialBlobSize", wintypes.DWORD),
                ("CredentialBlob", ctypes.POINTER(ctypes.c_ubyte)),
                ("Persist", wintypes.DWORD),
                ("AttributeCount", wintypes.DWORD),
                ("Attributes", ctypes.c_void_p),
                ("TargetAlias", wintypes.LPWSTR),
                ("UserName", wintypes.LPWSTR),
            ]

        api: Any = getattr(ctypes, "WinDLL")("advapi32", use_last_error=True)  # noqa: B009
        api.CredReadW.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.POINTER(ctypes.POINTER(Credential)),
        ]
        api.CredWriteW.argtypes = [ctypes.POINTER(Credential), wintypes.DWORD]
        api.CredDeleteW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD]
        api.CredFree.argtypes = [ctypes.c_void_p]
        return api, Credential

    def get(self, provider: str) -> str | None:
        if not self.available:
            return None
        api, credential = self._api()
        pointer = ctypes.POINTER(credential)()
        if not api.CredReadW(self.prefix + provider, 1, 0, ctypes.byref(pointer)):
            return None
        try:
            item = pointer.contents
            return ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize).decode("utf-8")
        finally:
            api.CredFree(pointer)

    def put(self, provider: str, value: str) -> None:
        if not self.available:
            raise OSError("Credential store unavailable")
        api, credential = self._api()
        blob = value.encode("utf-8")
        buffer = (ctypes.c_ubyte * len(blob)).from_buffer_copy(blob)
        item = credential()
        item.Type = 1  # CRED_TYPE_GENERIC
        item.TargetName = self.prefix + provider
        item.CredentialBlobSize = len(blob)
        item.CredentialBlob = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte))
        item.Persist = 2  # CRED_PERSIST_LOCAL_MACHINE
        item.UserName = "deeptrace"
        if not api.CredWriteW(ctypes.byref(item), 0):
            raise OSError("Credential store write failed")

    def delete(self, provider: str) -> None:
        if self.available:
            self._api()[0].CredDeleteW(self.prefix + provider, 1, 0)


def resolve_key(store: CredentialStore, provider: str) -> str | None:
    """The OS store wins; the documented process-environment fallback is for development."""
    return store.get(provider) or os.environ.get(ENV_NAMES[provider]) or None
