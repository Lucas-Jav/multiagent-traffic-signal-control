import pytest

from traffic_agents.__main__ import main
from traffic_agents.config import get_settings


def test_main_prints_application_name_and_environment(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()

    main()

    assert capsys.readouterr().out == "Traffic Multi-Agent Control\nenvironment=test\n"
    get_settings.cache_clear()
