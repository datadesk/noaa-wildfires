"""The errors this package raises."""

from __future__ import annotations


class NOAAError(Exception):
    """Raised when NOAA cannot be reached or sends back something unusable.

    The message says in plain words what went wrong. When a download is tried
    more than once, the message describes the last problem.

    Attributes:
        url: The address that was being downloaded, if there was one.
        status_code: The HTTP status NOAA sent back, if it sent one.

    Examples:
        >>> error = NOAAError("NOAA sent back status 503", status_code=503)
        >>> str(error)
        'NOAA sent back status 503'
        >>> error.status_code
        503
    """

    def __init__(
        self,
        message: str,
        url: str | None = None,
        status_code: int | None = None,
    ) -> None:
        """Make the error.

        Args:
            message: A plain description of what went wrong.
            url: The address that was being downloaded.
            status_code: The HTTP status NOAA sent back.
        """
        super().__init__(message)
        self.url = url
        self.status_code = status_code


class NOAADataError(NOAAError, ValueError):
    """Raised when NOAA has no file for a day, or its contents cannot be read.

    This is also a ``ValueError``, so code that caught ``ValueError`` keeps
    working.

    Examples:
        >>> try:
        ...     raise NOAADataError("NOAA's row has no 'Lat' column")
        ... except ValueError as error:
        ...     print(error)
        NOAA's row has no 'Lat' column
    """
