"""BGW320 device collector timeout and failure regression tests."""

from pathlib import Path
from unittest.mock import patch

import pytest

from z0.network.gateway_devices import collect_gateway_devices


def test_live_device_fetch_uses_extended_timeout():
    with patch(
        "z0.network.gateway_devices._fetch",
        return_value="<html></html>",
    ) as fetch:
        assert collect_gateway_devices() == []
    fetch.assert_called_once_with(
        "192.168.1.254", "/cgi-bin/devices.ha", timeout=30
    )


def test_live_fetch_timeout_propagates_to_cli():
    with patch(
        "z0.network.gateway_devices._fetch",
        side_effect=TimeoutError("timed out"),
    ):
        with pytest.raises(TimeoutError, match="timed out"):
            collect_gateway_devices()


def test_saved_html_does_not_contact_gateway(tmp_path: Path):
    file_path = tmp_path / "devices.html"
    file_path.write_text("<html></html>", encoding="utf-8")
    with patch("z0.network.gateway_devices._fetch") as fetch:
        assert collect_gateway_devices(html_file=file_path) == []
    fetch.assert_not_called()
