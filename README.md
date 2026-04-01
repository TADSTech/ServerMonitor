# ServerMonitor

Lightweight ICTRD API monitor with a Typer CLI, colored terminal output, and tests.

## Features

- Periodic health and auth endpoint checks
- Rich-colored status output (OK / FAIL / SKIP)
- Environment-variable driven configuration
- Retry + timeout support for unstable network conditions
- Unit tests with pytest

## Project Structure

- `main.py` - Typer CLI monitor
- `tests/test_main.py` - unit tests
- `ICTRD_API_DOCS.md` - API reference notes
- `requirements.txt` - Python dependencies

## Requirements

- Python 3.10+

## Install

```bash
python -m pip install -r requirements.txt
```

## Environment Variables

Core settings:

- `SERVER_BASE_URL` (preferred), for example `https://ictrd.onrender.com`
- Or use `SERVER_URL` + `SERVER_PORT` (defaults to `http://localhost:8080`)

Auth headers used by checks:

- `CENTAUR_API_KEY` or `API_KEY` -> used for `/v1/me`
- `ADMIN_API_KEY` -> used for `/v1/auth/keys`
- `OWNER_ACCESS_SECRET` (optional in private mode) -> added when present

Polling and request tuning:

- `CHECK_INTERVAL_SECONDS` (default: `60`)
- `REQUEST_CONNECT_TIMEOUT_SECONDS` (default: `6`)
- `REQUEST_READ_TIMEOUT_SECONDS` (default: `30`)
- `REQUEST_RETRIES` (default: `1`)
- `REQUEST_RETRY_BACKOFF_SECONDS` (default: `2.0`)

## Usage

Single run:

```bash
python main.py once
```

Continuous polling:

```bash
python main.py run
```

Override interval and base URL from CLI:

```bash
python main.py run --interval 30 --base-url https://ictrd.onrender.com
```

## Tests

```bash
python -m pytest -q
```

## Notes

- `health` checks `GET /health`
- `identity` checks `GET /v1/me` (skips if no API key)
- `admin_keys` checks `GET /v1/auth/keys` (skips if no admin key)
