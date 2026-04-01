import requests

import main


def test_build_base_url_from_single_base_url(monkeypatch):
    monkeypatch.setenv("SERVER_BASE_URL", "https://ictrd.onrender.com/")
    monkeypatch.delenv("SERVER_URL", raising=False)
    monkeypatch.delenv("SERVER_PORT", raising=False)

    assert main.build_base_url() == "https://ictrd.onrender.com"


def test_build_base_url_from_host_port(monkeypatch):
    monkeypatch.delenv("SERVER_BASE_URL", raising=False)
    monkeypatch.setenv("SERVER_URL", "http://localhost")
    monkeypatch.setenv("SERVER_PORT", "8080")

    assert main.build_base_url() == "http://localhost:8080"


def test_request_json_retry_success_after_failure(monkeypatch):
    class FakeResponse:
        ok = True
        status_code = 200

        @staticmethod
        def json():
            return {"status": "ok"}

    class FakeSession:
        def __init__(self):
            self.calls = 0

        def request(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise requests.Timeout("timeout")
            return FakeResponse()

    monkeypatch.setattr(main.time, "sleep", lambda _: None)

    ok, status, elapsed_ms, payload = main.request_json(
        session=FakeSession(),
        method="GET",
        url="https://example.test/health",
        headers={},
        connect_timeout_seconds=1,
        read_timeout_seconds=1,
        retries=1,
        retry_backoff_seconds=0,
    )

    assert ok is True
    assert status == 200
    assert elapsed_ms is not None
    assert payload == {"status": "ok"}


def test_request_json_all_retries_fail(monkeypatch):
    class FakeSession:
        def request(self, **kwargs):
            raise requests.Timeout("timeout forever")

    monkeypatch.setattr(main.time, "sleep", lambda _: None)

    ok, status, elapsed_ms, payload = main.request_json(
        session=FakeSession(),
        method="GET",
        url="https://example.test/health",
        headers={},
        connect_timeout_seconds=1,
        read_timeout_seconds=1,
        retries=2,
        retry_backoff_seconds=0,
    )

    assert ok is False
    assert status is None
    assert elapsed_ms is None
    assert "timeout" in str(payload).lower()
