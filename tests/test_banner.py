from z0.botops.git import collect_git_info
from z0.botops.node import detect_node
from z0.botops.render import PROJECT_ROOT, render_banner
from z0.botops.system import collect_system_info


def test_banner_contains_branding() -> None:
    banner = render_banner()

    assert "z0_n3t" in banner
    assert "Network Automation Platform" in banner
    assert "IRC • Discord • AWS • Linux • Python" in banner


def test_system_collector_returns_hostname() -> None:
    info = collect_system_info()

    assert info.hostname
    assert info.python_version


def test_git_collector_returns_repository_name() -> None:
    info = collect_git_info(PROJECT_ROOT)

    assert info.repository == "z0"


def test_node_detection_returns_role() -> None:
    node = detect_node()

    assert node.platform
    assert node.role
    assert node.status == "ONLINE"
