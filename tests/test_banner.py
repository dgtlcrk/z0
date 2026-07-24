from pathlib import Path

from z0.botops.config import BotOpsConfig
from z0.botops.git import collect_git_info
from z0.botops.inventory import collect_inventory
from z0.botops.node import detect_node
from z0.botops.render import PROJECT_ROOT, render_banner
from z0.botops.system import collect_system_info


def make_test_config() -> BotOpsConfig:
    return BotOpsConfig(
        node_name="test-node",
        node_role="Test Automation",
        irc_host="",
        irc_port=6697,
        discord_enabled=False,
        aws_host="",
        domain="",
        health_timeout=0.25,
        github_host="github.com",
        show_health_on_login=False,
    )


def test_banner_contains_branding() -> None:
    banner = render_banner(
        include_health=False,
        config=make_test_config(),
    )

    assert "z0_n3t" in banner
    assert "Network Automation Platform" in banner
    assert "INVENTORY" in banner
    assert "SERVICES" in banner
    assert "PROJECT" in banner


def test_system_collector_returns_values() -> None:
    info = collect_system_info()

    assert info.hostname
    assert info.python_version
    assert info.cpu_count


def test_git_collector_returns_repository_name() -> None:
    info = collect_git_info(PROJECT_ROOT)

    assert info.repository == "z0"


def test_node_detection_returns_configured_values() -> None:
    node = detect_node(make_test_config())

    assert node.name == "test-node"
    assert node.role == "Test Automation"
    assert node.status == "ONLINE"


def test_inventory_returns_network_identity() -> None:
    inventory = collect_inventory()

    assert inventory.ip_address
    assert inventory.mac_address


def test_project_root_exists() -> None:
    assert isinstance(PROJECT_ROOT, Path)
    assert PROJECT_ROOT.exists()


def test_banner_can_hide_login_welcome() -> None:
    banner = render_banner(
        include_health=False,
        include_welcome=False,
        config=make_test_config(),
    )

    assert ">>> Welcome to z0_n3t" not in banner
