"""Offline tests of the optional ``get`` argument, with a fake request function."""

import datetime

import pytest
import requests

import noaa_wildfires
from noaa_wildfires import NOAADataError, NOAAError, fetch

from .conftest import DATA, FakeResponse

FIRE = (DATA / "hms_fire20261117.txt").read_bytes()
SMOKE = (DATA / "hms_smoke20261117.zip").read_bytes()


class Recorder:
    """A fake request function that plays back replies and remembers each call."""

    def __init__(self, *replies) -> None:
        self.replies = list(replies)
        self.urls: list[str] = []
        self.timeouts: list[float] = []

    def __call__(self, url: str, *, timeout: float) -> FakeResponse:
        self.urls.append(url)
        self.timeouts.append(timeout)
        reply = self.replies[min(len(self.urls), len(self.replies)) - 1]
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture(autouse=True)
def no_requests(monkeypatch):
    """Fail the test if the package falls back to ``requests.get``."""

    def refuse(*args, **kwargs):
        raise AssertionError("requests.get should not be called")

    monkeypatch.setattr(fetch.requests, "get", refuse)


def test_types_are_exported():
    """The two types are part of the public package."""
    assert noaa_wildfires.Fetcher is fetch.Fetcher
    assert noaa_wildfires.Reply is fetch.Reply
    assert {"Fetcher", "Reply"} <= set(noaa_wildfires.__all__)


def test_function_is_used_instead_of_requests():
    """The caller's function makes the request, and requests is never used."""
    get = Recorder(FakeResponse(FIRE))
    data = noaa_wildfires.get_hms_fires("2026-11-17", get=get)
    assert len(data["features"]) == 7
    assert get.urls == [noaa_wildfires.fire_url(datetime.date(2026, 11, 17))]


def test_smoke_and_records_use_the_function():
    """Smoke and the typed records can use the caller's function too."""
    assert (
        len(
            noaa_wildfires.get_hms_smoke(
                "2026-11-17", get=Recorder(FakeResponse(SMOKE))
            )["features"]
        )
        == 3
    )
    assert (
        len(
            noaa_wildfires.get_hms_smoke_records(
                "2026-11-17", get=Recorder(FakeResponse(SMOKE))
            )
        )
        == 3
    )
    assert (
        len(
            noaa_wildfires.get_hms_fire_records(
                "2026-11-17", get=Recorder(FakeResponse(FIRE))
            )
        )
        == 7
    )


def test_timeout_is_passed_through():
    """The timeout reaches the caller's function, 60 seconds by default."""
    get = Recorder(FakeResponse(FIRE))
    noaa_wildfires.get_hms_fires("2026-11-17", get=get)
    noaa_wildfires.get_hms_fires("2026-11-17", timeout=5, get=get)
    assert get.timeouts == [60.0, 5]


def test_latest_day_search_uses_the_function(monkeypatch):
    """Falling back to an earlier day keeps using the caller's function."""

    monkeypatch.setattr(noaa_wildfires, "_today", lambda: datetime.date(2026, 11, 18))
    get = Recorder(FakeResponse(status_code=404), FakeResponse(FIRE))
    assert len(noaa_wildfires.get_hms_fires(get=get)["features"]) == 7
    assert len(get.urls) == 2


@pytest.mark.parametrize(
    "failure",
    [
        requests.ConnectionError("no route"),
        requests.Timeout("too slow"),
        FakeResponse(status_code=500),
        FakeResponse(status_code=429),
    ],
)
def test_retries_then_succeeds(failure):
    """A network problem or a busy server is tried again."""
    get = Recorder(failure, FakeResponse(FIRE))
    assert len(noaa_wildfires.get_hms_fires("2026-11-17", get=get)["features"]) == 7
    assert len(get.urls) == 2


def test_gives_up_with_noaa_error():
    """After every try fails a NOAAError says what happened last."""
    get = Recorder(FakeResponse(status_code=503))
    with pytest.raises(NOAAError, match="status 503") as caught:
        noaa_wildfires.get_hms_fires("2026-11-17", get=get)
    assert caught.value.status_code == 503
    assert len(get.urls) == 4


def test_other_request_error_becomes_noaa_error():
    """A requests error that is not a network problem fails right away."""
    get = Recorder(requests.exceptions.InvalidURL("bad"))
    with pytest.raises(NOAAError, match="failed"):
        noaa_wildfires.get_hms_fires("2026-11-17", get=get)
    assert len(get.urls) == 1


def test_other_errors_are_passed_on():
    """An error that is not from requests reaches the caller untouched."""
    with pytest.raises(KeyError):
        noaa_wildfires.get_hms_fires("2026-11-17", get=Recorder(KeyError("mine")))


def test_reply_without_ok_attribute():
    """A reply needs only status_code and content, not requests' ``ok``."""

    class Bare:
        status_code = 200
        content = FIRE

    data = noaa_wildfires.get_hms_fires("2026-11-17", get=Recorder(Bare()))
    assert len(data["features"]) == 7


def test_bad_file_is_a_data_error():
    """A reply that is not a fire file raises NOAADataError."""
    with pytest.raises(NOAADataError):
        noaa_wildfires.get_hms_fires(
            "2026-11-17", get=Recorder(FakeResponse(b"<html>"))
        )


def test_default_still_uses_requests(monkeypatch):
    """With no function, requests.get is used as before."""
    calls = []

    def fake(url, timeout):
        calls.append(url)
        return FakeResponse(FIRE)

    monkeypatch.setattr(fetch.requests, "get", fake)
    assert len(noaa_wildfires.get_hms_fires("2026-11-17")["features"]) == 7
    assert len(calls) == 1
