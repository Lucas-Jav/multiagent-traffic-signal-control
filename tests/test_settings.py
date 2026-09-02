from pathlib import Path

import pytest

from traffic_agents.config import Settings

SETTING_NAMES = (
    "APP_ENV",
    "LOG_LEVEL",
    "SUMO_BINARY",
    "SUMO_HOME",
    "ARTIFACTS_DIR",
    "DEFAULT_SEED",
)


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in SETTING_NAMES:
        monkeypatch.delenv(name, raising=False)

    settings = Settings(_env_file=None)

    assert settings.app_env == "development"
    assert settings.log_level == "INFO"
    assert settings.sumo_binary == "sumo"
    assert settings.sumo_home is None
    assert settings.artifacts_dir == Path("artifacts")
    assert settings.default_seed == 42


def test_settings_read_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("SUMO_BINARY", "sumo-gui")
    monkeypatch.setenv("SUMO_HOME", "/opt/sumo")
    monkeypatch.setenv("ARTIFACTS_DIR", "custom-artifacts")
    monkeypatch.setenv("DEFAULT_SEED", "123")

    settings = Settings(_env_file=None)

    assert settings.app_env == "production"
    assert settings.log_level == "DEBUG"
    assert settings.sumo_binary == "sumo-gui"
    assert settings.sumo_home == Path("/opt/sumo")
    assert settings.artifacts_dir == Path("custom-artifacts")
    assert settings.default_seed == 123
