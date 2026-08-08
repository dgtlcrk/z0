import tomllib
from pathlib import Path

ROOT = Path(__file__).parent

DEFAULT = ROOT / "default.toml"

with DEFAULT.open("rb") as f:
    config = tomllib.load(f)
