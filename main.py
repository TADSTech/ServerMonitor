import os
import time
from datetime import datetime, timezone
from typing import Any

import requests
from dotenv import load_dotenv
import typer
from rich.console import Console


app = typer.Typer(help="ICTRD server monitor")
console = Console()


def _to_int(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def build_base_url() -> str:
    base_url = os.getenv("SERVER_BASE_URL")
    if base_url:
        return base_url.rstrip("/")

    server_url = os.getenv("SERVER_URL", "http://localhost").rstrip("/")
    server_port = os.getenv("SERVER_PORT", "8080")
    return f"{server_url}:{server_port}"


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    headers: dict[str, str],
    connect_timeout_seconds: int,
    read_timeout_seconds: int,
    retries: int,
    retry_backoff_seconds: float,
) -> tuple[bool, int | None, float | None, dict | str | None]:
    attempt = 0
    last_error: str | None = None

    while attempt <= retries:
        start = time.perf_counter()
        try:
            response = session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=(connect_timeout_seconds, read_timeout_seconds),
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            payload: dict | str | None
            try:
                payload = response.json()
            except ValueError:
                payload = response.text

            return response.ok, response.status_code, elapsed_ms, payload
        except requests.RequestException as exc:
            last_error = str(exc)
            if attempt >= retries:
                break
            sleep_seconds = retry_backoff_seconds * (attempt + 1)
            time.sleep(max(sleep_seconds, 0))
            attempt += 1

    return False, None, None, last_error


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def print_result(name: str, ok: bool, status: int | None, elapsed_ms: float | None, details: str) -> None:
    status_text = str(status) if status is not None else "ERR"
    elapsed_text = f"{elapsed_ms:.1f}ms" if elapsed_ms is not None else "-"
    marker = "[green]OK[/green]" if ok else "[red]FAIL[/red]"
    console.print(
        f"[dim][{timestamp()}][/dim] [cyan]{name:<14}[/cyan] {marker:<20} "
        f"status=[bold]{status_text:<4}[/bold] latency=[magenta]{elapsed_text:<8}[/magenta] {details}"
    )


def _print_skip(name: str, reason: str) -> None:
    console.print(f"[dim][{timestamp()}][/dim] [cyan]{name:<14}[/cyan] [yellow]SKIP[/yellow] {reason}")


def poll_once(
    session: requests.Session,
    base_url: str,
    connect_timeout_seconds: int,
    read_timeout_seconds: int,
    retries: int,
    retry_backoff_seconds: float,
) -> dict[str, tuple[bool, int | None, float | None, str]]:
    owner_secret = os.getenv("OWNER_ACCESS_SECRET")
    api_key = os.getenv("CENTAUR_API_KEY") or os.getenv("API_KEY")
    admin_key = os.getenv("ADMIN_API_KEY")
    results: dict[str, tuple[bool, int | None, float | None, str]] = {}

    health_ok, health_status, health_ms, health_payload = request_json(
        session=session,
        method="GET",
        url=f"{base_url}/health",
        headers={},
        connect_timeout_seconds=connect_timeout_seconds,
        read_timeout_seconds=read_timeout_seconds,
        retries=retries,
        retry_backoff_seconds=retry_backoff_seconds,
    )
    health_detail = str(health_payload)
    print_result("health", health_ok, health_status, health_ms, health_detail)
    results["health"] = (health_ok, health_status, health_ms, health_detail)

    if api_key:
        headers = {"X-API-Key": api_key}
        if owner_secret:
            headers["X-Owner-Secret"] = owner_secret

        me_ok, me_status, me_ms, me_payload = request_json(
            session=session,
            method="GET",
            url=f"{base_url}/v1/me",
            headers=headers,
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
            retries=retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )
        me_detail = str(me_payload)
        print_result("identity", me_ok, me_status, me_ms, me_detail)
        results["identity"] = (me_ok, me_status, me_ms, me_detail)
    else:
        _print_skip("identity", "no CENTAUR_API_KEY/API_KEY found (set one in .env to enable /v1/me checks)")
        results["identity"] = (False, None, None, "SKIPPED")

    if admin_key:
        headers = {"X-Admin-Key": admin_key}
        if owner_secret:
            headers["X-Owner-Secret"] = owner_secret

        keys_ok, keys_status, keys_ms, keys_payload = request_json(
            session=session,
            method="GET",
            url=f"{base_url}/v1/auth/keys",
            headers=headers,
            connect_timeout_seconds=connect_timeout_seconds,
            read_timeout_seconds=read_timeout_seconds,
            retries=retries,
            retry_backoff_seconds=retry_backoff_seconds,
        )

        detail = str(keys_payload)
        if isinstance(keys_payload, dict) and "keys" in keys_payload and isinstance(keys_payload["keys"], list):
            detail = f"total_keys={len(keys_payload['keys'])}"
        print_result("admin_keys", keys_ok, keys_status, keys_ms, detail)
        results["admin_keys"] = (keys_ok, keys_status, keys_ms, detail)
    else:
        _print_skip("admin_keys", "no ADMIN_API_KEY found")
        results["admin_keys"] = (False, None, None, "SKIPPED")

    return results


def _load_runtime_defaults() -> dict[str, Any]:
    load_dotenv()
    return {
        "base_url": build_base_url(),
        "interval_seconds": _to_int(os.getenv("CHECK_INTERVAL_SECONDS"), 60),
        "connect_timeout_seconds": _to_int(os.getenv("REQUEST_CONNECT_TIMEOUT_SECONDS"), 6),
        "read_timeout_seconds": _to_int(os.getenv("REQUEST_READ_TIMEOUT_SECONDS"), 30),
        "retries": _to_int(os.getenv("REQUEST_RETRIES"), 1),
        "retry_backoff_seconds": float(os.getenv("REQUEST_RETRY_BACKOFF_SECONDS", "2.0")),
    }


@app.command()
def run(
    interval: int | None = typer.Option(None, "--interval", help="Polling interval in seconds"),
    base_url: str | None = typer.Option(None, "--base-url", help="API base URL override"),
) -> None:
    cfg = _load_runtime_defaults()
    active_base_url = (base_url or cfg["base_url"]).rstrip("/")
    active_interval = interval if interval is not None else cfg["interval_seconds"]

    console.print(
        f"[bold green]Polling[/bold green] {active_base_url} every {max(active_interval, 1)}s "
        f"(connect={cfg['connect_timeout_seconds']}s read={cfg['read_timeout_seconds']}s retries={cfg['retries']})"
    )

    with requests.Session() as session:
        while True:
            poll_once(
                session=session,
                base_url=active_base_url,
                connect_timeout_seconds=cfg["connect_timeout_seconds"],
                read_timeout_seconds=cfg["read_timeout_seconds"],
                retries=cfg["retries"],
                retry_backoff_seconds=cfg["retry_backoff_seconds"],
            )
            time.sleep(max(active_interval, 1))


@app.command()
def once(
    base_url: str | None = typer.Option(None, "--base-url", help="API base URL override"),
) -> None:
    cfg = _load_runtime_defaults()
    active_base_url = (base_url or cfg["base_url"]).rstrip("/")
    console.print(f"[bold blue]Single check[/bold blue] against {active_base_url}")

    with requests.Session() as session:
        poll_once(
            session=session,
            base_url=active_base_url,
            connect_timeout_seconds=cfg["connect_timeout_seconds"],
            read_timeout_seconds=cfg["read_timeout_seconds"],
            retries=cfg["retries"],
            retry_backoff_seconds=cfg["retry_backoff_seconds"],
        )


if __name__ == "__main__":
    try:
        app()
    except KeyboardInterrupt:
        console.print("[yellow]Stopped.[/yellow]")