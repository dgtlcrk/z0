"""Command-line entry point for the z0_n3t BotOps banner."""

from __future__ import annotations

from z0.botops.render import render_banner


def main() -> None:
    print(render_banner())


if __name__ == "__main__":
    main()
