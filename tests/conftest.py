"""Shared test setup that keeps the tests off NOAA's real website."""

import datetime
from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"
TODAY = datetime.date(2026, 11, 18)
"""The pretend date for tests. Samples exist for the 17th (full) and the 18th (smoke is empty)."""


class FakeResponse:
    """A stand-in for a ``requests`` response."""

    def __init__(self, content: bytes = b"", status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code
        self.ok = status_code < 400

    def raise_for_status(self) -> None:
        """Raise an error like ``requests`` does for a bad status."""
        import requests

        if self.status_code >= 400:
            raise requests.HTTPError(f"status {self.status_code}")


@pytest.fixture
def fake_noaa(monkeypatch):
    """Replace ``requests.get`` with a fake that serves the saved samples.

    The file name at the end of the address picks a sample from ``tests/data``.
    A file with no sample is "not found". Every address asked for is recorded
    in ``fake_noaa.urls``. Today is pretended to be 2026-11-18.
    """
    import noaa_wildfires

    class Fake:
        urls: list[str]

    fake = Fake()
    fake.urls = []

    def get(url, *args, **kwargs):
        fake.urls.append(url)
        path = DATA / url.rsplit("/", 1)[-1]
        if not path.exists():
            return FakeResponse(status_code=404)
        return FakeResponse(path.read_bytes())

    monkeypatch.setattr(noaa_wildfires.requests, "get", get)
    monkeypatch.setattr(noaa_wildfires, "_today", lambda: TODAY)
    return fake
