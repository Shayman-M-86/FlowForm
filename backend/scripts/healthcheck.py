import sys
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

HEALTHCHECK_URL = "http://127.0.0.1:5000/api/v1/health/ready"
TIMEOUT_SECONDS = 3


def main() -> int:
    try:
        with urlopen(HEALTHCHECK_URL, timeout=TIMEOUT_SECONDS) as response:
            return 0 if response.status == 200 else 1
    except HTTPError, URLError, TimeoutError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
