from __future__ import annotations

import platform
import socket


def main() -> None:
    print("z0 online")
    print(f"host: {socket.gethostname()}")
    print(f"platform: {platform.platform()}")


if __name__ == "__main__":
    main()
