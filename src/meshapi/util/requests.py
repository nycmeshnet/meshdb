from requests import Session
from requests.adapters import HTTPAdapter, Retry


def get_requests_session_with_retries() -> Session:
    retries = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
    )

    session = Session()
    session.mount("http://", HTTPAdapter(max_retries=retries))
    session.mount("https://", HTTPAdapter(max_retries=retries))
    return session
