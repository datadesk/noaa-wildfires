"""Download NOAA's files, with a timeout and retries."""

from __future__ import annotations

import random
import sys
import time
from typing import Protocol

import requests

from .errors import NOAAError

DEFAULT_TIMEOUT = 60.0
"""How many seconds to wait for NOAA before giving up on one attempt."""

DEFAULT_TRIES = 4
"""How many times to try before raising an error."""

RETRY_STATUS_CODES = frozenset({408, 429})
"""Statuses worth another try. Every 5xx status is also worth another try."""


class Reply(Protocol):
    """What a request function must hand back: a status code and the file's bytes.

    A ``requests.Response`` fits this.
    """

    @property
    def status_code(self) -> int:
        """The web status, such as 200 or 404."""
        ...

    @property
    def content(self) -> bytes:
        """The body of the reply, as bytes."""
        ...


class Fetcher(Protocol):
    """A function that makes a web request for this package.

    Pass one as ``get`` to add retries, logging or custom headers. ``requests.get``
    fits this, and is the default.

    Examples:
        >>> import requests
        >>> fetcher: Fetcher = requests.get
    """

    def __call__(self, url: str, *, timeout: float) -> Reply:
        """Request a web address.

        Args:
            url: The address to request.
            timeout: The seconds to wait before giving up.

        Returns:
            The reply.
        """
        ...


def download(
    url: str,
    verbose: bool = False,
    timeout: float = DEFAULT_TIMEOUT,
    tries: int = DEFAULT_TRIES,
    get: Fetcher | None = None,
) -> bytes | None:
    """Download one of NOAA's files.

    A download is tried again when NOAA cannot be reached, takes too long, or
    answers with a server error or "too many requests". The wait before each
    new try doubles, starting at 2 seconds. Any other bad status fails right
    away. A "not found" is not an error here, because NOAA has no file for a
    day until its first detections arrive.

    Args:
        url: The address of the file.
        verbose: Print each request to standard error. Defaults to False.
        timeout: Seconds to wait for NOAA on each try. Defaults to 60.
        tries: How many tries to make in all. Defaults to 4.
        get: A function that makes the web request, such as ``requests.get``
            (the default). It is called as ``get(url, timeout=seconds)`` and
            must return something with ``status_code`` and ``content``. Its
            ``requests`` errors are retried like the default's. Any other error
            it raises is passed on untouched.

    Returns:
        The bytes of the file, or None if NOAA says there is no such file.

    Raises:
        NOAAError: If every try fails, or NOAA answers with a status that is
            not worth trying again.

    Examples:
        >>> content = download(
        ...     "https://satepsanone.nesdis.noaa.gov/pub/FIRE/web/HMS/Fire_Points/Text/2026/11/hms_fire20261117.txt"
        ... )
        >>> content = download("https://example.com/file", timeout=120, tries=2)
        >>> content = download("https://example.com/file", get=my_get)
    """
    fetch: Fetcher = get or requests.get
    problem = None
    for attempt in range(max(tries, 1)):
        if attempt:
            time.sleep(2**attempt + random.random())  # noqa: S311
        if verbose:
            print(f"Requesting {url}", file=sys.stderr)
        try:
            response = fetch(url, timeout=timeout)
        except (requests.ConnectionError, requests.Timeout) as error:
            problem = NOAAError(f"Could not reach NOAA at {url}: {error}", url=url)
            continue
        except requests.RequestException as error:
            raise NOAAError(f"Request to {url} failed: {error}", url=url) from error

        status = response.status_code
        if status == 404:
            return None
        if status >= 500 or status in RETRY_STATUS_CODES:
            problem = NOAAError(
                f"NOAA sent back status {status} for {url}", url=url, status_code=status
            )
            continue
        if status >= 400:
            raise NOAAError(
                f"NOAA sent back status {status} for {url}", url=url, status_code=status
            )
        return bytes(response.content)

    assert problem is not None
    raise problem
