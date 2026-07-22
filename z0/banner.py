"""Backward-compatible entry point for the z0_n3t dashboard."""

from z0.botops.banner import main
from z0.botops.render import render_banner

__all__ = ["main", "render_banner"]


if __name__ == "__main__":
    main()
