"""Shared test setup that keeps the tests off NOAA's real website."""

from pathlib import Path

import pytest

DATA = Path(__file__).parent / "data"


class FakeResponse:
    """A stand-in for a ``requests`` response."""

    def __init__(self, content: bytes = b"", status_code: int = 200) -> None:
        self.content = content
        self.status_code = status_code
        self.ok = status_code < 400


@pytest.fixture
def sample():
    """Return a function that reads a saved sample file as bytes."""

    def read(name: str) -> bytes:
        return (DATA / name).read_bytes()

    return read


@pytest.fixture
def fake_noaa(monkeypatch, sample):
    """Replace ``requests.get`` with a fake that serves the saved samples.

    The fake records every address that was asked for in ``fake_noaa.urls``.
    The file name at the end of the address picks the sample.
    """
    import noaa_wildfires

    class Fake:
        urls: list[str]

    fake = Fake()
    fake.urls = []

    def get(url, *args, **kwargs):
        fake.urls.append(url)
        return FakeResponse(sample(url.rsplit("/", 1)[-1]))

    monkeypatch.setattr(noaa_wildfires.requests, "get", get)
    return fake
