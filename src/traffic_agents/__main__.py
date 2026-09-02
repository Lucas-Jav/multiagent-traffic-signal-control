from __future__ import annotations

from traffic_agents.config import get_settings


def main() -> None:
    settings = get_settings()
    print("Traffic Multi-Agent Control")
    print(f"environment={settings.app_env}")


if __name__ == "__main__":
    main()
