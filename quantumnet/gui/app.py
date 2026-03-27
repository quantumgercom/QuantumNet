from __future__ import annotations

from quantumnet.gui.core.config import default_config_path
from quantumnet.gui.core.layout import setup_page
from quantumnet.gui.pages.navigation import build_navigation


def main() -> None:
    setup_page()
    config_path = default_config_path()
    navigation = build_navigation(config_path)
    navigation.run()


if __name__ == "__main__":
    main()
