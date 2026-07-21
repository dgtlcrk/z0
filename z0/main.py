from __future__ import annotations

from z0.config import config


def main() -> None:
    print("=== z0 ===")
    print(f"server: {config.server}:{config.port}")
    print(f"nickname: {config.nickname}")
    print(f"channel: {config.channel}")


if __name__ == "__main__":
    main()
