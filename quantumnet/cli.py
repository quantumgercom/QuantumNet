from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quantumnet", description="CLI utilities for QuantumNet")
    subparsers = parser.add_subparsers(dest="command")

    gui = subparsers.add_parser("gui", help="Run the QuantumNet Streamlit configuration interface")
    gui.add_argument("--host", default="127.0.0.1", help="Host for Streamlit server")
    gui.add_argument("--port", type=int, default=8501, help="Port for Streamlit server")
    gui.add_argument(
        "--config-path",
        default=str(Path(__file__).resolve().parent / "config" / "default_config.yaml"),
        help="Path for the YAML config edited by the GUI",
    )

    return parser


def _run_gui(args: argparse.Namespace) -> int:
    app_path = Path(__file__).resolve().parent / "gui" / "app.py"
    package_root = Path(__file__).resolve().parent
    legacy_default = (package_root / "default_config.yaml").resolve()
    new_default = (package_root / "config" / "default_config.yaml").resolve()
    selected_config = Path(args.config_path).resolve()
    if selected_config == legacy_default:
        selected_config = new_default

    env = os.environ.copy()
    env["QUANTUMNET_CONFIG_PATH"] = str(selected_config)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=true",
        f"--server.address={args.host}",
        f"--server.port={args.port}",
    ]
    return subprocess.call(cmd, env=env)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "gui":
        return _run_gui(args)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
