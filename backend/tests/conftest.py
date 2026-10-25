import socket
import sys

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    original_connect = socket.socket.connect

    def denied(*args, **kwargs):
        raise AssertionError("Network is disabled during tests")

    def guarded_connect(sock, address):
        # Windows asyncio uses a loopback socket pair for its internal wakeup pipe.
        caller = sys._getframe(1).f_code
        if caller.co_name == "_fallback_socketpair" and caller.co_filename == socket.__file__:
            return original_connect(sock, address)
        return denied()

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    monkeypatch.setattr(socket, "create_connection", denied)
