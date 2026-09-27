# Wrapper for running Python code in the Nebius Token Factory sandbox.

import base64
import time

import requests

import config

HEADERS = {
    "Authorization": f"Bearer {config.NEBIUS_API_KEY}",
    "Project": config.NEBIUS_PROJECT_ID,
    "Content-Type": "application/json",
}

PYTHON_IMAGE = "tag:python:3.11-slim"


def run_python(source_code: str, timeout: int = 30, poll_interval: float = 1.0) -> dict:
    """Run `source_code` as a Python script inside a fresh sandbox instance.

    Returns {"exit_code": int, "stdout": str, "stderr": str}.
    Raises RuntimeError if the sandbox doesn't finish within `timeout` seconds.
    """
    stdin_b64 = base64.b64encode(source_code.encode("utf-8")).decode("ascii")

    spawn_response = requests.post(
        f"{config.SANDBOX_BASE_URL}/instances",
        headers=HEADERS,
        json={
            "command": "python3",
            "args": ["-"],
            "shell": False,
            "image": PYTHON_IMAGE,
            "stdin": {"value": stdin_b64, "encoding": "base64", "close": True},
        },
    )
    spawn_response.raise_for_status()
    operation_path = spawn_response.headers["Location"]
    operation_url = f"https://api.tokenfactory.nebius.com{operation_path}"

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        op_response = requests.get(operation_url, headers=HEADERS)
        op_response.raise_for_status()
        operation = op_response.json()
        result = (operation.get("metadata") or {}).get("result")
        if result is not None:
            return {
                "exit_code": result["state"]["exit_code"],
                "stdout": result["stdout"]["value"],
                "stderr": result["stderr"]["value"],
            }
        time.sleep(poll_interval)

    raise RuntimeError(f"Sandbox execution did not finish within {timeout} seconds")
