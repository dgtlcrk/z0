"""Shared API snapshot creation."""

from __future__ import annotations

from typing import Any

from z0.adapters.registry import build_adapter_registry
from z0.botops.config import load_config
from z0.botops.git import collect_git_info
from z0.botops.health import collect_health
from z0.botops.inventory import collect_inventory
from z0.botops.node import detect_node
from z0.botops.render import PROJECT_ROOT
from z0.botops.services import collect_services
from z0.botops.system import collect_system_info
from z0.plugins.registry import build_plugin_registry
from z0.scheduler.engine import Scheduler


def build_snapshot() -> dict[str, Any]:
    config = load_config()
    plugins = build_plugin_registry()

    return {
        "platform": {
            "name": "z0_n3t",
            "description": "Network Automation Platform",
        },
        "node": detect_node(config).to_dict(),
        "system": collect_system_info().to_dict(),
        "inventory": collect_inventory().to_dict(),
        "services": [
            service.to_dict()
            for service in collect_services(config)
        ],
        "infrastructure": [
            status.to_dict()
            for status in collect_health(config)
        ],
        "adapters": [
            status.to_dict()
            for status in build_adapter_registry(config).statuses()
        ],
        "plugins": [
            metadata.to_dict()
            for metadata in plugins.metadata()
        ],
        "jobs": [
            job.to_dict()
            for job in Scheduler(plugins=plugins).list_jobs()
        ],
        "project": collect_git_info(PROJECT_ROOT).to_dict(),
    }
