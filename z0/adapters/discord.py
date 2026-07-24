"""Discord adapter implementation."""

from __future__ import annotations

from z0.adapters.base import Adapter, AdapterStatus


class DiscordAdapter(Adapter):
    """Discord adapter scaffold.

    Token values are never included in status output.
    """

    name = "discord"

    def __init__(
        self,
        token: str = "",
        *,
        enabled: bool = False,
    ) -> None:
        super().__init__(enabled=enabled)
        self.token = token
        self._connected = False

    def connect(self) -> None:
        if not self.enabled:
            return

        if not self.token:
            raise RuntimeError("Discord token is not configured")

        raise NotImplementedError(
            "Discord transport requires the Discord client dependency"
        )

    def disconnect(self) -> None:
        self._connected = False

    def send(self, destination: str, message: str) -> None:
        if not self._connected:
            raise RuntimeError("Discord adapter is not connected")

        raise NotImplementedError("Discord message transport is not active")

    def status(self) -> AdapterStatus:
        if not self.enabled:
            state = "DISABLED"
        elif not self.token:
            state = "UNCONFIGURED"
        elif self._connected:
            state = "CONNECTED"
        else:
            state = "CONFIGURED"

        return AdapterStatus(
            name=self.name,
            enabled=self.enabled,
            connected=self._connected,
            state=state,
        )
