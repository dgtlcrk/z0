"""IRC adapter implementation."""

from __future__ import annotations

import socket

from z0.adapters.base import Adapter, AdapterStatus


class IRCAdapter(Adapter):
    """Basic IRC reachability adapter.

    This first implementation verifies connectivity and provides the common
    adapter contract. The existing IRC bot can later be attached to this class.
    """

    name = "irc"

    def __init__(
        self,
        host: str,
        port: int = 6697,
        *,
        enabled: bool = True,
        timeout: float = 2.0,
    ) -> None:
        super().__init__(enabled=enabled)
        self.host = host
        self.port = port
        self.timeout = timeout
        self._connected = False

    def connect(self) -> None:
        if not self.enabled:
            return

        if not self.host:
            raise RuntimeError("IRC host is not configured")

        with socket.create_connection(
            (self.host, self.port),
            timeout=self.timeout,
        ):
            self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def send(self, destination: str, message: str) -> None:
        if not self._connected:
            raise RuntimeError("IRC adapter is not connected")

        raise NotImplementedError(
            "IRC message transport will be connected to the existing IRC "
            "service in the next adapter integration step"
        )

    def status(self) -> AdapterStatus:
        if not self.enabled:
            return AdapterStatus(
                name=self.name,
                enabled=False,
                connected=False,
                state="DISABLED",
            )

        if not self.host:
            return AdapterStatus(
                name=self.name,
                enabled=True,
                connected=False,
                state="UNCONFIGURED",
            )

        try:
            with socket.create_connection(
                (self.host, self.port),
                timeout=self.timeout,
            ):
                reachable = True
        except OSError:
            reachable = False

        return AdapterStatus(
            name=self.name,
            enabled=True,
            connected=self._connected,
            state="CONNECTED" if self._connected else (
                "REACHABLE" if reachable else "OFFLINE"
            ),
            detail=f"{self.host}:{self.port}",
        )
