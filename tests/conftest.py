"""Pytest configuration and fixtures."""

import re
import shutil
import subprocess
import tempfile
import threading
from datetime import datetime
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright
from pytest_jupyter import wait_handlers


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (default: False)",
    )


@pytest.fixture(scope="session")
def jupyter_server():
    """Start JupyterLab server for tests."""
    notebook_root = tempfile.mkdtemp()

    proc = subprocess.Popen(
        [
            "jupyter",
            "lab",
            "--no-browser",
            "--ServerApp.token=''",
            "--ServerApp.password=''",
            f"--ServerApp.root_dir={notebook_root}",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    server_ready = threading.Event()
    server_url = None

    def read_output():
        nonlocal server_url
        for line in proc.stdout:
            print(line, flush=True)
            if "http://localhost:" in line:
                match = re.search(r"http://localhost:\d+", line)
                if match:
                    server_url = match.group(0)
                    server_ready.set()

    t = threading.Thread(target=read_output)
    t.daemon = True
    t.start()

    max_timeout = 15.0
    if not server_ready.wait(timeout=max_timeout):
        proc.terminate()
        proc.wait()
        raise RuntimeError("Failed to start Jupyter server within timeout.")

    if not server_url:
        proc.terminate()
        proc.wait()
        raise RuntimeError("Failed to extract Jupyter server URL from output.")

    yield (server_url, notebook_root)

    proc.terminate()
    proc.wait()

    shutil.rmtree(notebook_root, ignore_errors=True)


@pytest.fixture
def temp_notebook_dir(jupyter_server):
    """Get the notebook directory (same as server root)."""
    _, notebook_root = jupyter_server
    yield Path(notebook_root)


@pytest.fixture
def browser_context(request, jupyter_server):
    """Provide browser context."""
    headless = request.config.getoption("--headless")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        yield context
        context.close()
        browser.close()


@pytest.fixture
def page(browser_context, jupyter_server, temp_notebook_dir):
    """Provide browser page with JupyterLab."""
    page = browser_context.new_page()

    script_path = Path(__file__).parent / "pytest_jupyter" / "kernel_intercept.js"
    kernel_intercept_js = script_path.read_text()

    page.add_init_script(kernel_intercept_js)

    page.expose_binding(
        "kernel_message_handler",
        lambda source, log_entry: handle_kernel_message(log_entry),
    )

    server_url, _ = jupyter_server
    page.temp_notebook_dir = temp_notebook_dir
    page.jupyter_server = server_url

    wait_handlers.kernel_status = "idle"
    wait_handlers.last_status_change = datetime.now()

    wait_handlers.clear_callbacks()

    page.goto(server_url)

    yield page

    wait_handlers.clear_callbacks()
    page.close()


def handle_kernel_message(payload):
    wait_handlers.update_kernel_status(payload)
