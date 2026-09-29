from __future__ import annotations

from pathlib import Path

import pytest

from traffic_agents.metrics import SumoTripMetricsError, parse_sumo_trip_metrics


def test_parse_sumo_trip_metrics_normal_trips(tmp_path: Path) -> None:
    tripinfo = tmp_path / "tripinfo.xml"
    tripinfo.write_text(
        """
<tripinfos>
  <tripinfo id="v0" duration="10.0" waitingTime="2.0" timeLoss="3.0" waitingCount="1"/>
  <tripinfo id="v1" duration="20.0" waitingTime="4.0" timeLoss="5.0" waitingCount="3"/>
</tripinfos>
""".strip(),
        encoding="utf-8",
    )

    metrics = parse_sumo_trip_metrics(tripinfo_path=tripinfo)

    assert metrics.available is True
    assert metrics.trip_count == 2
    assert metrics.mean_waiting_time_seconds == 3.0
    assert metrics.mean_time_loss_seconds == 4.0
    assert metrics.mean_travel_time_seconds == 15.0
    assert metrics.mean_stops == 2.0


def test_parse_sumo_trip_metrics_zero_trips(tmp_path: Path) -> None:
    tripinfo = tmp_path / "tripinfo.xml"
    tripinfo.write_text("<tripinfos/>", encoding="utf-8")

    metrics = parse_sumo_trip_metrics(tripinfo_path=tripinfo)

    assert metrics.available is True
    assert metrics.trip_count == 0
    assert metrics.mean_waiting_time_seconds == 0.0


def test_parse_sumo_trip_metrics_missing_waiting_count_defaults_to_zero(tmp_path: Path) -> None:
    tripinfo = tmp_path / "tripinfo.xml"
    tripinfo.write_text(
        '<tripinfos><tripinfo id="v0" duration="10" waitingTime="2" timeLoss="3"/></tripinfos>',
        encoding="utf-8",
    )

    metrics = parse_sumo_trip_metrics(tripinfo_path=tripinfo)

    assert metrics.mean_stops == 0.0


def test_parse_sumo_trip_metrics_malformed_xml_fails(tmp_path: Path) -> None:
    tripinfo = tmp_path / "tripinfo.xml"
    tripinfo.write_text("<tripinfos>", encoding="utf-8")

    with pytest.raises(SumoTripMetricsError, match="malformed"):
        parse_sumo_trip_metrics(tripinfo_path=tripinfo)


def test_parse_sumo_trip_metrics_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        parse_sumo_trip_metrics(tripinfo_path=tmp_path / "missing.xml")


def test_parse_sumo_trip_metrics_missing_required_attribute_fails(tmp_path: Path) -> None:
    tripinfo = tmp_path / "tripinfo.xml"
    tripinfo.write_text('<tripinfos><tripinfo id="v0" duration="10"/></tripinfos>')

    with pytest.raises(SumoTripMetricsError, match="waitingTime"):
        parse_sumo_trip_metrics(tripinfo_path=tripinfo)
