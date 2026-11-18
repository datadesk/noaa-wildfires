"""Offline tests of timeouts, retries and errors, with fake replies."""

import pytest
import requests
from click.testing import CliRunner

import noaa_wildfires
from noaa_wildfires import NOAADataError, NOAAError, fetch
from noaa_wildfires.cli import cmd

from .conftest import DATA, FakeResponse

GOOD = (DATA / "hms_fire20261117.txt").read_bytes()


class Recorder:
    """A fake ``requests.get`` that plays back replies and remembers each call."""

    def __init__(self, *replies) -> None:
        self.replies = list(replies)
        self.urls: list[str] = []
        self.timeouts: list[float] = []

    def __call__(self, url: str, timeout: float) -> FakeResponse:
        self.urls.append(url)
        self.timeouts.append(timeout)
        reply = self.replies[min(len(self.urls), len(self.replies)) - 1]
        if isinstance(reply, Exception):
            raise reply
        return reply


def use(monkeypatch, *replies) -> Recorder:
    """Replace ``requests.get`` with a recorder."""
    recorder = Recorder(*replies)
    monkeypatch.setattr(fetch.requests, "get", recorder)
    return recorder


def test_default_timeout(monkeypatch):
    """Every request has a 60 second timeout unless you choose another."""
    recorder = use(monkeypatch, FakeResponse(GOOD))
    noaa_wildfires.get_hms_fires("2026-11-17")
    noaa_wildfires.get_hms_fires("2026-11-17", timeout=5)
    assert recorder.timeouts == [60.0, 5]


@pytest.mark.parametrize(
    "failure",
    [
        requests.ConnectionError("no route"),
        requests.Timeout("too slow"),
        FakeResponse(status_code=500),
        FakeResponse(status_code=429),
    ],
)
def test_retries_then_succeeds(monkeypatch, failure):
    """A network problem or a busy server is tried again."""
    recorder = use(monkeypatch, failure, FakeResponse(GOOD))
    assert len(noaa_wildfires.get_hms_fires("2026-11-17")["features"]) == 7
    assert len(recorder.urls) == 2


def test_gives_up_with_noaa_error(monkeypatch):
    """After every try fails a NOAAError says what happened last."""
    recorder = use(monkeypatch, FakeResponse(status_code=503))
    with pytest.raises(NOAAError, match="status 503") as caught:
        noaa_wildfires.get_hms_fires("2026-11-17")
    assert caught.value.status_code == 503
    assert len(recorder.urls) == 4


def test_forbidden_is_not_retried(monkeypatch):
    """A 403 fails on the first try."""
    recorder = use(monkeypatch, FakeResponse(status_code=403))
    with pytest.raises(NOAAError, match="403"):
        noaa_wildfires.get_hms_fires("2026-11-17")
    assert len(recorder.urls) == 1


def test_not_found_for_a_date_is_a_data_error(monkeypatch):
    """A 404 means no file, which is a NOAADataError and also a ValueError."""
    use(monkeypatch, FakeResponse(status_code=404))
    with pytest.raises(NOAADataError, match="no fire file") as caught:
        noaa_wildfires.get_hms_fires("2026-11-17")
    assert isinstance(caught.value, ValueError)


def test_other_request_error_becomes_noaa_error(monkeypatch):
    """A requests error that is not a network problem fails right away."""
    recorder = use(monkeypatch, requests.exceptions.InvalidURL("bad"))
    with pytest.raises(NOAAError, match="failed"):
        noaa_wildfires.get_hms_fires("2026-11-17")
    assert len(recorder.urls) == 1


def test_bad_fire_file_is_a_data_error(monkeypatch):
    """A reply that is not a fire file raises NOAADataError."""
    use(monkeypatch, FakeResponse(b"<html>nope</html>"))
    with pytest.raises(NOAADataError):
        noaa_wildfires.get_hms_fires("2026-11-17")


def test_bad_smoke_file_is_a_data_error(monkeypatch):
    """A reply that is not a zipped shapefile raises NOAADataError."""
    use(monkeypatch, FakeResponse(b"<html>nope</html>"))
    with pytest.raises(NOAADataError):
        noaa_wildfires.get_hms_smoke("2026-11-17")


def test_verbose_goes_to_stderr(monkeypatch, capsys):
    """The request is printed to standard error, not standard output."""
    use(monkeypatch, FakeResponse(GOOD))
    noaa_wildfires.get_hms_fires("2026-11-17", verbose=True)
    captured = capsys.readouterr()
    assert "Requesting https://" in captured.err
    assert captured.out == ""


def test_command_keeps_json_clean(monkeypatch):
    """With --verbose the request is on stderr, so stdout is still valid JSON."""
    import json

    use(monkeypatch, FakeResponse(GOOD))
    result = CliRunner().invoke(
        cmd, ["hms-fires", "--date", "2026-11-17", "--verbose", "--timeout", "7"]
    )
    assert result.exit_code == 0
    assert len(json.loads(result.stdout)["features"]) == 7
    assert "Requesting" in result.stderr


def test_command_error_is_one_line(monkeypatch):
    """A failure prints one line starting with Error: and exits with 1."""
    use(monkeypatch, FakeResponse(status_code=403))
    result = CliRunner().invoke(cmd, ["hms-smoke"])
    assert result.exit_code == 1
    assert result.stderr.startswith("Error: NOAA sent back status 403")
    assert result.stdout == ""


def test_command_bad_date(monkeypatch):
    """A date that is not a date is a plain error."""
    result = CliRunner().invoke(cmd, ["hms-fires", "--date", "yesterday"])
    assert result.exit_code == 1
    assert result.stderr.startswith("Error:")
