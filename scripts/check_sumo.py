from __future__ import annotations

from traffic_agents.simulation import (
    SumoNotFoundError,
    UnsupportedSumoVersionError,
    detect_sumo_environment,
)


def main() -> int:
    try:
        info = detect_sumo_environment()
    except (SumoNotFoundError, UnsupportedSumoVersionError) as error:
        print(f"SUMO check failed: {error}")
        return 1

    print("SUMO detected")
    print(f"version={info.version}")
    print(f"binary={info.sumo_binary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
